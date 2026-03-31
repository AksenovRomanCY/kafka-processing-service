import json
import logging

from aiokafka import AIOKafkaProducer

from app.settings import settings

logger = logging.getLogger(__name__)


async def send_to_kafka(topic: str, data: dict):
    """Asynchronously send a JSON-encoded message to a Kafka topic.

    Establishes a connection to Kafka using settings.KAFKA_BOOTSTRAP_SERVERS,
    serializes `data` to JSON, and publishes it to the given `topic`.
    The AIOKafkaProducer is started and stopped for each invocation.

    Args:
        topic (str): The Kafka topic to which the message will be published.
        data (dict): A JSON-serializable dictionary to send as the message payload.

    Raises:
        KafkaError: If the send operation fails.
    """
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    try:
        await producer.send_and_wait(topic, data)
        logger.info("Posted in Topic '%s': %s", topic, data)
    finally:
        await producer.stop()
