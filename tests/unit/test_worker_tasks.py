import pytest  # noqa

from app.worker_tasks import task_1, task_2


@pytest.mark.usefixtures("random_success")
def test_task_1_success(monkeypatch):
    """When random=0.5 → no exception, value+100 is passed to task_2.delay"""
    called = {}

    def fake_delay(v):
        called["value"] = v
        return "OK"

    monkeypatch.setattr("app.worker_tasks.task_2.delay", fake_delay)

    result = task_1.run(value=10)
    assert called["value"] == 110
    assert result == "OK"


@pytest.mark.usefixtures("random_fail")
def test_task_1_failure(monkeypatch):
    """If random<0.3 → the original Exception is thrown."""
    with pytest.raises(Exception) as exc:
        task_1.run(value=5)
    assert "Accidental error in task1" in str(exc.value)


@pytest.mark.usefixtures("random_success")
def test_task_2_success(monkeypatch):
    """
    If random=0.5 → no exception, inside task_2
    send_to_kafka should be called with a result = value-1000.
    """
    sent = {}

    async def fake_send(topic, data):
        sent["topic"] = topic
        sent["data"] = data

    monkeypatch.setattr("app.worker_tasks.send_to_kafka", fake_send)

    task_2.run(value=200)
    assert sent["topic"] == "output"
    assert sent["data"] == {"result": -800}


@pytest.mark.usefixtures("random_fail")
def test_task_2_failure(monkeypatch):
    """If random<0.3 → the original Exception is thrown."""
    with pytest.raises(Exception) as exc:
        task_2.run(value=100)
    assert "Accidental error in task2" in str(exc.value)
