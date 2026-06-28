from __future__ import annotations

import logging
import sys
from io import StringIO
from typing import Any

import pytest  # noqa: F401

from app.exceptions import TransientProcessingError
from app.logging_config import setup_logging
from app.settings import settings
from app.worker_tasks import DLQTask, send_kafka_task, task_1, task_2


def test_task_1_returns_value_plus_100():
    """task_1 returns input + 100."""
    result = task_1.run(value=10)
    assert result == 110


def test_task_2_returns_value_minus_1000():
    """task_2 returns input - 1000."""
    result = task_2.run(value=200)
    assert result == -800


def test_send_kafka_task_calls_sync_producer(monkeypatch):
    """send_kafka_task sends result to the configured output topic."""
    sent: dict[str, Any] = {}

    def fake_sync_send(topic: str, data: dict[str, Any]) -> None:
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.worker_tasks.sync_producer.send", fake_sync_send)

    send_kafka_task.run(result=123.45)
    assert sent["topic"] == settings.KAFKA_OUTPUT_TOPIC
    assert sent["data"]["result"] == 123.45


def test_task_1_raises_demo_failure():
    """task_1 can be failed intentionally for the DLQ demo."""
    with pytest.raises(TransientProcessingError, match="task_1"):
        task_1.run(value=10, fail="task_1")


def test_task_2_raises_demo_failure():
    """task_2 can be failed intentionally for the DLQ demo."""
    with pytest.raises(TransientProcessingError, match="task_2"):
        task_2.run(value=200, fail="task_2")


def test_send_kafka_task_raises_demo_failure(monkeypatch):
    """send_kafka_task can be failed intentionally before producing output."""
    sent: dict[str, Any] = {}

    def fake_sync_send(topic: str, data: dict[str, Any]) -> None:
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.worker_tasks.sync_producer.send", fake_sync_send)

    with pytest.raises(TransientProcessingError, match="send_kafka_task"):
        send_kafka_task.run(result=123.45, fail="send_kafka_task")

    assert sent == {}


def test_dlq_on_failure_sends_to_dlq_topic(monkeypatch):
    """on_failure handler sends task info to the DLQ topic."""
    sent: dict[str, Any] = {}

    def fake_sync_send(topic: str, data: dict[str, Any]) -> None:
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.worker_tasks.sync_producer.send", fake_sync_send)

    task_instance = DLQTask()
    task_instance.name = "app.worker_tasks.task_1"

    exc = ValueError("something broke")
    task_instance.on_failure(
        exc=exc,
        task_id="abc-123",
        args=(42.0,),
        kwargs={},
        einfo=None,
    )

    assert sent["topic"] == settings.KAFKA_DLQ_TOPIC
    assert sent["data"]["task_name"] == "app.worker_tasks.task_1"
    assert sent["data"]["task_id"] == "abc-123"
    assert sent["data"]["args"] == [42.0]
    assert "something broke" in sent["data"]["exception"]


def test_dlq_on_failure_includes_traceback(monkeypatch):
    """on_failure handler includes traceback in DLQ message."""
    sent: dict[str, Any] = {}

    def fake_sync_send(topic: str, data: dict[str, Any]) -> None:
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.worker_tasks.sync_producer.send", fake_sync_send)

    task_instance = DLQTask()
    task_instance.name = "app.worker_tasks.task_2"

    exc = RuntimeError("permanent failure")
    task_instance.on_failure(
        exc=exc,
        task_id="def-456",
        args=(99.0,),
        kwargs={},
        einfo=None,
    )

    assert sent["data"]["traceback"] is not None
    assert isinstance(sent["data"]["traceback"], list)


# ── trace_id ────────────────────────────────────────────────────


def test_task_1_logs_include_trace_id(caplog):
    """task_1 log records carry the supplied trace_id."""
    with caplog.at_level(logging.INFO):
        task_1.run(value=10, trace_id="t-123")

    for record in caplog.records:
        assert record.trace_id == "t-123"


def test_task_2_logs_include_trace_id(caplog):
    """task_2 log records carry the supplied trace_id."""
    with caplog.at_level(logging.INFO):
        task_2.run(value=200, trace_id="t-456")

    for record in caplog.records:
        assert record.trace_id == "t-456"


def test_send_kafka_task_includes_trace_id_in_message(monkeypatch):
    """send_kafka_task includes trace_id in the outgoing Kafka message."""
    sent: dict[str, Any] = {}

    def fake_sync_send(topic: str, data: dict[str, Any]) -> None:
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.worker_tasks.sync_producer.send", fake_sync_send)

    send_kafka_task.run(result=123.45, trace_id="t-789")
    assert sent["data"] == {"result": 123.45, "trace_id": "t-789"}


def test_dlq_on_failure_includes_trace_id(monkeypatch):
    """on_failure handler includes trace_id from kwargs in DLQ message."""
    sent: dict[str, Any] = {}

    def fake_sync_send(topic: str, data: dict[str, Any]) -> None:
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.worker_tasks.sync_producer.send", fake_sync_send)

    task_instance = DLQTask()
    task_instance.name = "app.worker_tasks.task_1"

    exc = ValueError("something broke")
    task_instance.on_failure(
        exc=exc,
        task_id="abc-123",
        args=(42.0,),
        kwargs={"trace_id": "t-dlq"},
        einfo=None,
    )

    assert sent["data"]["trace_id"] == "t-dlq"


def test_json_logging_formatter_includes_trace_id(monkeypatch):
    """The shared JSON formatter includes trace_id extra fields."""
    stream = StringIO()

    with monkeypatch.context() as patch_context:
        patch_context.setattr(sys, "stderr", stream)
        setup_logging(force=True)
        logging.getLogger("test-json-logger").info(
            "worker trace",
            extra={"trace_id": "t-json"},
        )

    setup_logging(force=True)

    output = stream.getvalue()
    assert '"message": "worker trace"' in output
    assert '"trace_id": "t-json"' in output
