import pytest  # noqa

from app.settings import settings
from app.worker_tasks import send_kafka_task, task_1, task_2


@pytest.mark.usefixtures("random_success")
def test_task_1_success(monkeypatch):
    """When random=0.5 → no exception, value+100 is passed to task_2.delay"""
    called = {}

    def fake_delay(v):
        called["value"] = v
        return "OK"

    monkeypatch.setattr("app.worker_tasks.task_2.delay", fake_delay)

    task_1.run(value=10)
    assert called["value"] == 110


@pytest.mark.usefixtures("random_fail")
def test_task_1_failure(monkeypatch):
    """If random<0.3 → the original Exception is thrown."""
    with pytest.raises(Exception) as exc:
        task_1.run(value=5)
    assert "Accidental error in task1" in str(exc.value)


@pytest.mark.usefixtures("random_success")
def test_task_2_success(monkeypatch):
    """If random=0.5 → no exception, task_2.delay calls send_kafka_task.delay with result = value-1000."""
    called = {}

    def fake_send_kafka_task_delay(result):
        called["result"] = result

    monkeypatch.setattr(
        "app.worker_tasks.send_kafka_task.delay", fake_send_kafka_task_delay
    )
    task_2.run(value=200)
    assert called["result"] == -800


@pytest.mark.usefixtures("random_fail")
def test_task_2_failure(monkeypatch):
    """If random<0.3 → the original Exception is thrown."""
    with pytest.raises(Exception) as exc:
        task_2.run(value=100)
    assert "Accidental error in task2" in str(exc.value)


def test_send_kafka_task_invokes_coroutine(monkeypatch):
    """send_kafka_task.run should call send_to_kafka(topic, {'result': result}) via asyncio."""
    sent = {}

    async def fake_send(topic, data):
        sent["topic"] = topic
        sent["data"] = data

    # Патчим именно имя в модуле worker_tasks, откуда send_kafka_task импортирует send_to_kafka
    monkeypatch.setattr("app.worker_tasks.send_to_kafka", fake_send)

    send_kafka_task.run(result=123.45)
    assert sent["topic"] == settings.KAFKA_OUTPUT_TOPIC
    assert sent["data"] == {"result": 123.45}
