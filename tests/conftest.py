import random

import pytest  # noqa

from app.celery_app import celery_app


@pytest.fixture(autouse=True)
def celery_eager():
    """All Celery-tasks are executed synchronously and without a broker."""
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


@pytest.fixture(autouse=True)
def patch_send_to_kafka(monkeypatch):
    """Replace all calls to send_to_kafka with a stub.
    So that there would be no need to connect anywhere during unit tests.
    """

    async def dummy_send(topic: str, data: dict):  # noqa
        return None

    monkeypatch.setattr("app.kafka.producer.send_to_kafka", dummy_send)
    monkeypatch.setattr("app.worker_tasks.send_to_kafka", dummy_send)
    monkeypatch.setattr("app.kafka.consumer.send_to_kafka", dummy_send)


@pytest.fixture
def random_success(monkeypatch):
    """Determine random.random() → always 0.5 (success)."""
    monkeypatch.setattr(random, "random", lambda: 0.5)


@pytest.fixture
def random_fail(monkeypatch):
    """Determine random.random() → always 0.0 (error)."""
    monkeypatch.setattr(random, "random", lambda: 0.0)
