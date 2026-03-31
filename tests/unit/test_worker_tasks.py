import pytest  # noqa

from app.settings import settings
from app.worker_tasks import send_kafka_task, task_1, task_2


def test_task_1_success(monkeypatch):
    """value+100 is passed to task_2.delay"""
    called = {}

    def fake_delay(v):
        called["value"] = v
        return "OK"

    monkeypatch.setattr("app.worker_tasks.task_2.delay", fake_delay)

    task_1.run(value=10)
    assert called["value"] == 110


def test_task_2_success(monkeypatch):
    """task_2 calls send_kafka_task.delay with result = value-1000."""
    called = {}

    def fake_send_kafka_task_delay(result):
        called["result"] = result

    monkeypatch.setattr(
        "app.worker_tasks.send_kafka_task.delay", fake_send_kafka_task_delay
    )
    task_2.run(value=200)
    assert called["result"] == -800


def test_send_kafka_task_invokes_coroutine(monkeypatch):
    """send_kafka_task.run should call send_to_kafka(topic, {'result': result}) via asyncio."""
    sent = {}

    async def fake_send(topic, data):
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.worker_tasks.send_to_kafka", fake_send)

    send_kafka_task.run(result=123.45)
    assert sent["topic"] == settings.KAFKA_OUTPUT_TOPIC
    assert sent["data"] == {"result": 123.45}
