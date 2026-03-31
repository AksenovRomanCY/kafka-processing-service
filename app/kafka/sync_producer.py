from __future__ import annotations

import json
import logging

from kafka import KafkaProducer

from app.settings import settings

logger = logging.getLogger(__name__)

_producer: KafkaProducer | None = None


def _get_producer() -> KafkaProducer:
    """Return the module-level sync KafkaProducer, creating it on first call.

    Uses lazy initialization so the TCP connection is established only
    when the first message is actually sent, not at module import time.
    """
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        logger.info("Sync Kafka producer initialized")
    return _producer


def sync_send_to_kafka(topic: str, data: dict) -> None:
    """Synchronously send a JSON-encoded message to a Kafka topic.

    Uses a persistent KafkaProducer singleton. Intended for use in
    synchronous contexts such as Celery worker tasks.

    Args:
        topic: The Kafka topic to publish to.
        data: A JSON-serializable dictionary for the message payload.

    Raises:
        KafkaError: If the send operation fails.
    """
    producer = _get_producer()
    future = producer.send(topic, data)
    record_metadata = future.get(timeout=10)
    logger.info(
        "Posted in Topic '%s' [partition=%s offset=%s]: %s",
        record_metadata.topic,
        record_metadata.partition,
        record_metadata.offset,
        data,
    )


def close_sync_producer() -> None:
    """Close the sync producer and release resources.

    Safe to call even if the producer was never initialized (no-op).
    """
    global _producer
    if _producer is None:
        return

    _producer.close(timeout=10)
    _producer = None
    logger.info("Sync Kafka producer closed")
