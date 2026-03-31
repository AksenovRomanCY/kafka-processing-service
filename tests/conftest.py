from __future__ import annotations

import pytest

from app.celery_app import celery_app


@pytest.fixture(autouse=True)
def celery_eager():
    """All Celery-tasks are executed synchronously and without a broker."""
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True


@pytest.fixture(autouse=True)
def patch_kafka_producers(monkeypatch):
    """Replace all Kafka producer calls with stubs.

    Patches both the async producer (used by consumer) and the sync
    producer (used by worker tasks) so tests run without a Kafka broker.
    """

    async def dummy_async_send(topic: str, data: dict) -> None:
        return None

    def dummy_sync_send(topic: str, data: dict) -> None:
        return None

    # Async producer used by consumer's handle_message
    monkeypatch.setattr("app.kafka.producer.send_to_kafka", dummy_async_send)
    monkeypatch.setattr("app.kafka.consumer.send_to_kafka", dummy_async_send)

    # Sync producer used by worker tasks
    monkeypatch.setattr("app.worker_tasks.sync_send_to_kafka", dummy_sync_send)
