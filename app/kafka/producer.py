from __future__ import annotations

import json
import logging
from typing import Any

from aiokafka import AIOKafkaProducer as _AIOKafkaProducer

from app.settings import settings

logger = logging.getLogger(__name__)


class AsyncKafkaProducer:
    """Async Kafka producer with explicit lifecycle management.

    Wraps AIOKafkaProducer with start/stop/send methods.
    Instantiate in consume() and pass to message handlers.

    Args:
        bootstrap_servers: Kafka broker address. Defaults to settings value.
    """

    def __init__(
        self, bootstrap_servers: str = settings.KAFKA_BOOTSTRAP_SERVERS
    ) -> None:
        self._bootstrap_servers = bootstrap_servers
        self._producer: _AIOKafkaProducer | None = None

    async def start(self) -> None:
        """Create and start the underlying AIOKafkaProducer.

        Raises:
            RuntimeError: If the producer is already running.
        """
        if self._producer is not None:
            raise RuntimeError("Async Kafka producer is already running")

        self._producer = _AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        )
        await self._producer.start()
        logger.info("Async Kafka producer started")

    async def stop(self) -> None:
        """Stop the producer and release resources.

        Safe to call even if the producer was never started (no-op).
        """
        if self._producer is None:
            return

        await self._producer.stop()
        self._producer = None
        logger.info("Async Kafka producer stopped")

    async def send(self, topic: str, data: dict[str, Any]) -> None:
        """Send a JSON-encoded message to a Kafka topic.

        Args:
            topic: The Kafka topic to publish to.
            data: A JSON-serializable dictionary for the message payload.

        Raises:
            RuntimeError: If the producer has not been started.
        """
        if self._producer is None:
            raise RuntimeError(
                "Async Kafka producer is not running. Call start() first."
            )

        await self._producer.send_and_wait(topic, data)
        logger.info("Posted in Topic '%s': %s", topic, data)
