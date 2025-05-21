import random

import pytest  # noqa

from app.celery_app import celery_app


@pytest.fixture(autouse=True)
def celery_eager():
    """
    Все Celery-таски выполняются синхронно и без брокера.
    """
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


@pytest.fixture(autouse=True)
def patch_send_to_kafka(monkeypatch):
    """
    Подменяем все вызовы send_to_kafka на заглушку,
    чтобы никуда не коннектиться из unit-тестов.
    """

    async def dummy_send(topic: str, data: dict):  # noqa
        return None

    monkeypatch.setattr("app.kafka.producer.send_to_kafka", dummy_send)
    monkeypatch.setattr("app.worker_tasks.send_to_kafka", dummy_send)
    monkeypatch.setattr("app.kafka.consumer.send_to_kafka", dummy_send)


@pytest.fixture
def random_success(monkeypatch):
    """
    Детерминируем random.random() → всегда 0.5 (успех).
    """
    monkeypatch.setattr(random, "random", lambda: 0.5)


@pytest.fixture
def random_fail(monkeypatch):
    """
    Детерминируем random.random() → всегда 0.0 (ошибка).
    """
    monkeypatch.setattr(random, "random", lambda: 0.0)
