import json

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
async def test_handle_message_valid(monkeypatch, capsys):
    monkeypatch.setattr(task_1, "delay", DummyTask.delay)
    await handle_message(json.dumps({"value": 42}))

    out = capsys.readouterr().out
    assert "[Kafka] Valid value: 42" in out
    assert "Celery task_1 started with ID: dummy-id" in out


@pytest.mark.asyncio
async def test_handle_message_invalid(monkeypatch, capsys):
    # Locally spoof send_to_kafka to catch its call
    sent = {}

    async def fake_send(topic, data):
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.kafka.consumer.send_to_kafka", fake_send)

    bad = "not-a-json"
    await handle_message(bad)

    out = capsys.readouterr().out
    assert "[Kafka][Error] Invalid message: not-a-json" in out
    # Let's make sure it's in the error-topic.
    assert sent["topic"] == settings.KAFKA_ERROR_TOPIC
    assert sent["data"] == {"error": bad}


@pytest.mark.asyncio
async def test_handle_message_missing_value(monkeypatch, capsys):
    """If there is no 'value' field in JSON, or it is None - error and send to error."""
    sent = {}

    async def fake_send(topic, data):
        sent["topic"] = topic
        sent["data"] = data

    # Patch sending to Kafka
    monkeypatch.setattr("app.kafka.consumer.send_to_kafka", fake_send)

    # Empty object
    await handle_message(json.dumps({}))
    out = capsys.readouterr().out
    assert "[Kafka][Error] Invalid message" in out
    assert sent["topic"] == settings.KAFKA_ERROR_TOPIC
    assert sent["data"] == {"error": "{}"}

    # Clearly null
    sent.clear()
    await handle_message(json.dumps({"value": None}))
    out = capsys.readouterr().out
    assert "[Kafka][Error] Invalid message" in out
    assert sent["data"] == {"error": '{"value": null}'}


@pytest.mark.asyncio
async def test_handle_message_non_numeric_value(monkeypatch, capsys):
    """If the 'value' field is not a number - also an error."""
    sent = {}

    async def fake_send(topic, data):
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.kafka.consumer.send_to_kafka", fake_send)

    # A string instead of a number
    bad = json.dumps({"value": "foo"})
    await handle_message(bad)
    out = capsys.readouterr().out
    assert "[Kafka][Error] Invalid message" in out
    assert sent["data"] == {"error": bad}


@pytest.mark.asyncio
async def test_handle_message_float_and_negative(monkeypatch, capsys):
    """Correct float and negative numbers are valid and go into task_1."""
    monkeypatch.setattr(task_1, "delay", DummyTask.delay)

    for val in [3.14, -1000.5]:
        await handle_message(json.dumps({"value": val}))
        out = capsys.readouterr().out
        assert f"[Kafka] Valid value: {val}" in out
        assert "Celery task_1 started with ID: dummy-id" in out
