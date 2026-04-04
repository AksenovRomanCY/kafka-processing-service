from __future__ import annotations

from typing import Any

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

    Patches both the async producer class (used by consumer) and the sync
    producer instance (used by worker tasks) so tests run without a Kafka broker.
    """

    async def dummy_async_send(self: Any, topic: str, data: dict[str, Any]) -> None:
        return None

    def dummy_sync_send(topic: str, data: dict[str, Any]) -> None:
        return None

    # Async producer: patch the class method so any instance's send is a no-op
    monkeypatch.setattr("app.kafka.producer.AsyncKafkaProducer.send", dummy_async_send)

    # Sync producer: patch the module-level instance's send method
    monkeypatch.setattr("app.kafka.sync_producer.sync_producer.send", dummy_sync_send)
    monkeypatch.setattr("app.worker_tasks.sync_producer.send", dummy_sync_send)
