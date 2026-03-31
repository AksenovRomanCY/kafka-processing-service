import asyncio
import json
import logging

from aiokafka import AIOKafkaConsumer

import app.logging_config  # noqa: F401
from app.kafka.producer import send_to_kafka, start_producer, stop_producer
from app.settings import settings
from app.worker_tasks import task_1

logger = logging.getLogger(__name__)


async def handle_message(raw_value: str) -> None:
    """Validate and process a raw Kafka message.

    Parses the raw JSON string, extracts the numeric 'value' field,
    enqueues a Celery task for valid payloads, and sends invalid
    messages to the configured error topic.

    Args:
        raw_value (str): The raw message payload as a JSON-formatted string.

    Raises:
        ValueError: If the 'value' field is missing or not a number.
        json.JSONDecodeError: If the raw_value is not valid JSON.
    """
    try:
        payload = json.loads(raw_value)
        number = payload.get("value")
        if not isinstance(number, (int, float)):
            raise ValueError("The 'value' field is missing or not a number")

        logger.info("Valid value: %s", number)

        res = task_1.delay(number)
        logger.info("Celery task_1 started with ID: %s", res.id)

    except Exception as e:
        logger.error("Invalid message: %s — %s", raw_value, e)
        await send_to_kafka(
            topic=settings.KAFKA_ERROR_TOPIC,
            data={"error": raw_value},
        )


async def consume():
    """Consume messages from Kafka input topic and process them.

    Creates and starts a persistent AIOKafkaProducer and an AIOKafkaConsumer,
    iterates over incoming messages, delegates each message to `handle_message`,
    and commits offsets manually. Ensures graceful shutdown of both consumer
    and producer on exit.
    """
    await start_producer()

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
            raw_value = msg.value
            logger.info("Message received: %s", raw_value)

            await handle_message(raw_value)
            await consumer.commit()

    finally:
        await consumer.stop()
        await stop_producer()


if __name__ == "__main__":  # pragma: no cover
    """
    Entry point for running the Kafka consumer.
    Executes the consume coroutine in the event loop.
    """
    asyncio.run(consume())
