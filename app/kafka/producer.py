from __future__ import annotations

import json
import logging

from aiokafka import AIOKafkaProducer

from app.settings import settings

logger = logging.getLogger(__name__)

_producer: AIOKafkaProducer | None = None


async def start_producer() -> None:
    """Initialize and start the module-level async Kafka producer.

    Must be called once before any send_to_kafka() calls.
    Typically called at consumer startup.

    Raises:
        RuntimeError: If the producer is already running.
    """
    global _producer
    if _producer is not None:
        raise RuntimeError("Async Kafka producer is already running")

    _producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await _producer.start()
    logger.info("Async Kafka producer started")


async def stop_producer() -> None:
    """Stop and release the module-level async Kafka producer.

    Safe to call even if the producer was never started (no-op).
    """
    global _producer
    if _producer is None:
        return

    await _producer.stop()
    _producer = None
    logger.info("Async Kafka producer stopped")


async def send_to_kafka(topic: str, data: dict) -> None:
    """Send a JSON-encoded message to a Kafka topic using the persistent producer.

    Args:
        topic: The Kafka topic to publish to.
        data: A JSON-serializable dictionary for the message payload.

    Raises:
        RuntimeError: If the producer has not been started.
        KafkaError: If the send operation fails.
    """
    if _producer is None:
        raise RuntimeError(
            "Async Kafka producer is not running. Call start_producer() first."
        )

    await _producer.send_and_wait(topic, data)
    logger.info("Posted in Topic '%s': %s", topic, data)
