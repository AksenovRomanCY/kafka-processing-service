from __future__ import annotations

import json
import logging
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.kafka.consumer import consume, handle_message
from app.settings import settings
from app.worker_tasks import task_1


class DummyAsyncResult:
    def __init__(self, id_):
        self.id = id_


class DummyTask:
    @staticmethod
    def delay(val):  # noqa
        return DummyAsyncResult("dummy-id")


@pytest.mark.asyncio
async def test_handle_message_valid(monkeypatch, caplog):
    monkeypatch.setattr(task_1, "delay", DummyTask.delay)
    with caplog.at_level(logging.INFO):
        await handle_message(json.dumps({"value": 42}))

    assert "Valid value: 42" in caplog.text
    assert "Celery task_1 started with ID: dummy-id" in caplog.text


@pytest.mark.asyncio
async def test_handle_message_invalid(monkeypatch, caplog):
    sent = {}

    async def fake_send(topic, data):
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.kafka.consumer.send_to_kafka", fake_send)

    bad = "not-a-json"
    with caplog.at_level(logging.ERROR):
        await handle_message(bad)

    assert "Invalid message: not-a-json" in caplog.text
    assert sent["topic"] == settings.KAFKA_ERROR_TOPIC
    assert sent["data"] == {"error": bad}


@pytest.mark.asyncio
async def test_handle_message_missing_value(monkeypatch, caplog):
    """If there is no 'value' field in JSON, or it is None - error and send to error."""
    sent = {}

    async def fake_send(topic, data):
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.kafka.consumer.send_to_kafka", fake_send)

    # Empty object
    with caplog.at_level(logging.ERROR):
        await handle_message(json.dumps({}))
    assert "Invalid message" in caplog.text
    assert sent["topic"] == settings.KAFKA_ERROR_TOPIC
    assert sent["data"] == {"error": "{}"}

    # Clearly null
    sent.clear()
    caplog.clear()
    with caplog.at_level(logging.ERROR):
        await handle_message(json.dumps({"value": None}))
    assert "Invalid message" in caplog.text
    assert sent["data"] == {"error": '{"value": null}'}


@pytest.mark.asyncio
async def test_handle_message_non_numeric_value(monkeypatch, caplog):
    """If the 'value' field is not a number - also an error."""
    sent = {}

    async def fake_send(topic, data):
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.kafka.consumer.send_to_kafka", fake_send)

    bad = json.dumps({"value": "foo"})
    with caplog.at_level(logging.ERROR):
        await handle_message(bad)
    assert "Invalid message" in caplog.text
    assert sent["data"] == {"error": bad}


@pytest.mark.asyncio
async def test_handle_message_float_and_negative(monkeypatch, caplog):
    """Correct float and negative numbers are valid and go into task_1."""
    monkeypatch.setattr(task_1, "delay", DummyTask.delay)

    for val in [3.14, -1000.5]:
        caplog.clear()
        with caplog.at_level(logging.INFO):
            await handle_message(json.dumps({"value": val}))
        assert f"Valid value: {val}" in caplog.text
        assert "Celery task_1 started with ID: dummy-id" in caplog.text


# ── helpers for consume() tests ─────────────────────────────────


class MockConsumer:
    """Fake AIOKafkaConsumer that yields predefined messages via async for."""

    def __init__(self, messages):
        self._messages = iter(messages)
        self.start = AsyncMock()
        self.stop = AsyncMock()
        self.commit = AsyncMock()

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._messages)
        except StopIteration:
            raise StopAsyncIteration


def _make_msg(value: str) -> MagicMock:
    msg = MagicMock()
    msg.value = value
    return msg


# ── consume() ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_consume_processes_messages_and_commits():
    msgs = [_make_msg('{"value": 1}'), _make_msg('{"value": 2}')]
    consumer_mock = MockConsumer(msgs)

    with (
        patch("app.kafka.consumer.start_producer", new_callable=AsyncMock),
        patch("app.kafka.consumer.stop_producer", new_callable=AsyncMock),
        patch("app.kafka.consumer.AIOKafkaConsumer", return_value=consumer_mock),
        patch("app.kafka.consumer.handle_message", new_callable=AsyncMock) as hm,
    ):
        await consume()

        assert hm.await_count == 2
        hm.assert_any_await('{"value": 1}')
        hm.assert_any_await('{"value": 2}')
        assert consumer_mock.commit.await_count == 2


@pytest.mark.asyncio
async def test_consume_calls_stop_on_normal_exit():
    consumer_mock = MockConsumer([_make_msg('{"value": 1}')])

    with (
        patch("app.kafka.consumer.start_producer", new_callable=AsyncMock),
        patch("app.kafka.consumer.stop_producer", new_callable=AsyncMock) as stop_prod,
        patch("app.kafka.consumer.AIOKafkaConsumer", return_value=consumer_mock),
        patch("app.kafka.consumer.handle_message", new_callable=AsyncMock),
    ):
        await consume()

        consumer_mock.stop.assert_awaited_once()
        stop_prod.assert_awaited_once()


@pytest.mark.asyncio
async def test_consume_calls_stop_on_exception():
    consumer_mock = MockConsumer([_make_msg('{"value": 1}')])

    with (
        patch("app.kafka.consumer.start_producer", new_callable=AsyncMock),
        patch("app.kafka.consumer.stop_producer", new_callable=AsyncMock) as stop_prod,
        patch("app.kafka.consumer.AIOKafkaConsumer", return_value=consumer_mock),
        patch(
            "app.kafka.consumer.handle_message",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ),
    ):
        with pytest.raises(RuntimeError, match="boom"):
            await consume()

        consumer_mock.stop.assert_awaited_once()
        stop_prod.assert_awaited_once()


@pytest.mark.asyncio
async def test_consume_starts_producer_before_consumer():
    consumer_mock = MockConsumer([])
    order: list[str] = []

    async def track_start_producer():
        order.append("start_producer")

    async def track_consumer_start():
        order.append("consumer.start")

    consumer_mock.start = AsyncMock(side_effect=track_consumer_start)

    with (
        patch(
            "app.kafka.consumer.start_producer",
            new_callable=AsyncMock,
            side_effect=track_start_producer,
        ),
        patch("app.kafka.consumer.stop_producer", new_callable=AsyncMock),
        patch("app.kafka.consumer.AIOKafkaConsumer", return_value=consumer_mock),
        patch("app.kafka.consumer.handle_message", new_callable=AsyncMock),
    ):
        await consume()

    assert order == ["start_producer", "consumer.start"]


@pytest.mark.asyncio
async def test_consume_creates_consumer_with_correct_settings():
    consumer_mock = MockConsumer([])

    with (
        patch("app.kafka.consumer.start_producer", new_callable=AsyncMock),
        patch("app.kafka.consumer.stop_producer", new_callable=AsyncMock),
        patch(
            "app.kafka.consumer.AIOKafkaConsumer", return_value=consumer_mock
        ) as cons_cls,
        patch("app.kafka.consumer.handle_message", new_callable=AsyncMock),
    ):
        await consume()

        cons_cls.assert_called_once()
        args, kwargs = cons_cls.call_args
        assert args[0] == settings.KAFKA_INPUT_TOPIC
        assert kwargs["bootstrap_servers"] == settings.KAFKA_BOOTSTRAP_SERVERS
        assert kwargs["auto_offset_reset"] == "earliest"
        assert kwargs["enable_auto_commit"] is False
        assert kwargs["group_id"] == settings.KAFKA_GROUP_ID
