import json
import logging

import pytest  # noqa

from app.kafka.consumer import handle_message
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
