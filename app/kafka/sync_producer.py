from __future__ import annotations

import json
import logging
from typing import Any

from kafka import KafkaProducer

from app.settings import settings

logger = logging.getLogger(__name__)


class SyncKafkaProducer:
    """Synchronous Kafka producer with lazy initialization.

    The underlying KafkaProducer connection is established on the first
    send() call, not at construction time. This avoids TCP overhead at
    import time in Celery workers.

    Args:
        bootstrap_servers: Kafka broker address. Defaults to settings value.
    """

    def __init__(
        self, bootstrap_servers: str = settings.KAFKA_BOOTSTRAP_SERVERS
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer: KafkaProducer | None = None

    def _ensure_producer(self) -> KafkaProducer:
        """Return the underlying KafkaProducer, creating it on first call."""
        if self._producer is None:
            self._producer = KafkaProducer(
                bootstrap_servers=self._bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
            logger.info("Sync Kafka producer initialized")
        return self._producer

    def send(self, topic: str, data: dict[str, Any]) -> None:
        """Synchronously send a JSON-encoded message to a Kafka topic.

        Args:
            topic: The Kafka topic to publish to.
            data: A JSON-serializable dictionary for the message payload.

        Raises:
            KafkaError: If the send operation fails.
        """
        trace_id = data.get("trace_id", "")
        producer = self._ensure_producer()
        future = producer.send(topic, data)
        record_metadata = future.get(timeout=10)
        logger.info(
            "Posted in Topic '%s' [partition=%s offset=%s]: %s",
            record_metadata.topic,
            record_metadata.partition,
            record_metadata.offset,
            data,
            extra={"trace_id": trace_id},
        )

    def close(self) -> None:
        """Close the producer and release resources.

        Safe to call even if the producer was never initialized (no-op).
        """
        if self._producer is None:
            return

        self._producer.close(timeout=10)
        self._producer = None
        logger.info("Sync Kafka producer closed")


# Default instance for Celery worker tasks.
# The underlying KafkaProducer connection is deferred until the first send().
sync_producer = SyncKafkaProducer()
