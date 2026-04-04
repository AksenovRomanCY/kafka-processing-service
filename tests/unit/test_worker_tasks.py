from __future__ import annotations

from typing import Any

import pytest  # noqa: F401

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

    monkeypatch.setattr("app.worker_tasks.sync_send_to_kafka", fake_sync_send)

    send_kafka_task.run(result=123.45)
    assert sent["topic"] == settings.KAFKA_OUTPUT_TOPIC
    assert sent["data"] == {"result": 123.45}


def test_dlq_on_failure_sends_to_dlq_topic(monkeypatch):
    """on_failure handler sends task info to the DLQ topic."""
    sent: dict[str, Any] = {}

    def fake_sync_send(topic: str, data: dict[str, Any]) -> None:
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.worker_tasks.sync_send_to_kafka", fake_sync_send)

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

    monkeypatch.setattr("app.worker_tasks.sync_send_to_kafka", fake_sync_send)

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
