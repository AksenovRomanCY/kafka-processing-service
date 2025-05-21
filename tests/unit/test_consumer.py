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
    assert "[Kafka] Валидное значение: 42" in out
    assert "Celery task_1 запущена с ID: dummy-id" in out


@pytest.mark.asyncio
async def test_handle_message_invalid(monkeypatch, capsys):
    # Локально подменяем send_to_kafka, чтобы засечь его вызов
    sent = {}

    async def fake_send(topic, data):
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.kafka.consumer.send_to_kafka", fake_send)

    bad = "not-a-json"
    await handle_message(bad)

    out = capsys.readouterr().out
    assert "[Kafka][Ошибка] Невалидное сообщение: not-a-json" in out
    # Убедимся, что отправили именно в error-топик
    assert sent["topic"] == settings.KAFKA_ERROR_TOPIC
    assert sent["data"] == {"error": bad}


@pytest.mark.asyncio
async def test_handle_message_missing_value(monkeypatch, capsys):
    """
    Если в JSON нет поля 'value' или оно None — ошибка и отправка в error.
    """
    sent = {}

    async def fake_send(topic, data):
        sent["topic"] = topic
        sent["data"] = data

    # Патчим отправку в Kafka
    monkeypatch.setattr("app.kafka.consumer.send_to_kafka", fake_send)

    # Пустой объект
    await handle_message(json.dumps({}))
    out = capsys.readouterr().out
    assert "[Kafka][Ошибка] Невалидное сообщение" in out
    assert sent["topic"] == settings.KAFKA_ERROR_TOPIC
    assert sent["data"] == {"error": "{}"}

    # Явно null
    sent.clear()
    await handle_message(json.dumps({"value": None}))
    out = capsys.readouterr().out
    assert "[Kafka][Ошибка] Невалидное сообщение" in out
    assert sent["data"] == {"error": '{"value": null}'}


@pytest.mark.asyncio
async def test_handle_message_non_numeric_value(monkeypatch, capsys):
    """
    Если поле 'value' не число — тоже ошибка.
    """
    sent = {}

    async def fake_send(topic, data):
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.kafka.consumer.send_to_kafka", fake_send)

    # Строка вместо числа
    bad = json.dumps({"value": "foo"})
    await handle_message(bad)
    out = capsys.readouterr().out
    assert "[Kafka][Ошибка] Невалидное сообщение" in out
    assert sent["data"] == {"error": bad}


@pytest.mark.asyncio
async def test_handle_message_float_and_negative(monkeypatch, capsys):
    """
    Правильные float и отрицательные числа валидны и идут в task_1.
    """
    monkeypatch.setattr(task_1, "delay", DummyTask.delay)

    for val in [3.14, -1000.5]:
        await handle_message(json.dumps({"value": val}))
        out = capsys.readouterr().out
        assert f"[Kafka] Валидное значение: {val}" in out
        assert "Celery task_1 запущена с ID: dummy-id" in out
