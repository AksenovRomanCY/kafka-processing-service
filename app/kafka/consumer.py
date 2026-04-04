from __future__ import annotations

import asyncio
import json
import logging
import signal
import uuid
from contextlib import suppress
from pathlib import Path

from aiokafka import AIOKafkaConsumer
from celery import chain

import app.logging_config  # noqa: F401
from app.kafka.producer import AsyncKafkaProducer
from app.settings import settings
from app.worker_tasks import send_kafka_task, task_1, task_2

logger = logging.getLogger(__name__)

LIVENESS_PATH = Path("/tmp/consumer-alive")


async def _heartbeat_loop(
    stop_event: asyncio.Event,
    path: Path = LIVENESS_PATH,
    interval_seconds: int = 20,
) -> None:
    """Touch a liveness file periodically while the consumer is running.

    The Dockerfile HEALTHCHECK verifies this file's mtime is < 1 minute,
    so the interval must be well under 60 seconds.
    """
    while not stop_event.is_set():
        path.touch()
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_seconds)
        except TimeoutError:
            pass


async def handle_message(raw_value: str, producer: AsyncKafkaProducer) -> None:
    """Validate and process a raw Kafka message.

    Parses the raw JSON string, extracts the numeric 'value' field,
    enqueues a Celery task for valid payloads, and sends invalid
    messages to the configured error topic.

    Args:
        raw_value: The raw message payload as a JSON-formatted string.
        producer: Async Kafka producer for sending error messages.
    """
    trace_id = str(uuid.uuid4())

    try:
        payload = json.loads(raw_value)
        number = payload.get("value")
        if not isinstance(number, (int, float)):
            raise ValueError("The 'value' field is missing or not a number")

        logger.info("Valid value: %s", number, extra={"trace_id": trace_id})

        res = chain(
            task_1.s(number, trace_id=trace_id),
            task_2.s(trace_id=trace_id),
            send_kafka_task.s(trace_id=trace_id),
        ).apply_async()
        logger.info(
            "Celery chain started with ID: %s", res.id, extra={"trace_id": trace_id}
        )

    except Exception as e:
        logger.error(
            "Invalid message: %s — %s", raw_value, e, extra={"trace_id": trace_id}
        )
        await producer.send(
            topic=settings.KAFKA_ERROR_TOPIC,
            data={"error": raw_value, "trace_id": trace_id},
        )


async def consume() -> None:
    """Consume messages from Kafka input topic and process them.

    Creates and starts a persistent AsyncKafkaProducer and AIOKafkaConsumer,
    iterates over incoming messages, delegates each to handle_message,
    and commits offsets manually. Handles SIGTERM/SIGINT for graceful shutdown.
    Ensures cleanup of consumer, producer, and heartbeat on exit.
    """
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop_event.set)

    producer = AsyncKafkaProducer()
    await producer.start()

    heartbeat_task = asyncio.create_task(_heartbeat_loop(stop_event))

    consumer = AIOKafkaConsumer(
        settings.KAFKA_INPUT_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: m.decode("utf-8"),
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        group_id=settings.KAFKA_GROUP_ID,
    )
    await consumer.start()

    try:
        # At-most-once delivery: the offset is committed right after
        # handle_message() enqueues a Celery task, NOT after the worker
        # finishes executing it.  If the worker crashes before the task
        # runs, the message will not be redelivered.
        #
        # This is a deliberate trade-off: simpler flow and lower latency
        # at the cost of potential message loss under worker failure.
        #
        # For at-least-once semantics, commit the offset only after the
        # task acknowledges completion (e.g. task_acks_late=True) and
        # make consumers idempotent to handle duplicates.
        async for msg in consumer:
            if stop_event.is_set():
                logger.info("Shutdown signal received, stopping consumer")
                break

            raw_value = msg.value
            logger.info("Message received: %s", raw_value)

            await handle_message(raw_value, producer)
            await consumer.commit()

    finally:
        await consumer.stop()
        await producer.stop()
        stop_event.set()
        heartbeat_task.cancel()
        with suppress(asyncio.CancelledError):
            await heartbeat_task
        LIVENESS_PATH.unlink(missing_ok=True)
        logger.info("Consumer shut down cleanly")


if __name__ == "__main__":  # pragma: no cover
    """
    Entry point for running the Kafka consumer.
    Executes the consume coroutine in the event loop.
    """
    asyncio.run(consume())
