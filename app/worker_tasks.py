import asyncio
import logging

from app.celery_app import celery_app
from app.exceptions import TransientProcessingError
from app.kafka.producer import send_to_kafka
from app.settings import settings

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    autoretry_for=(TransientProcessingError,),
    retry_backoff=True,
    max_retries=settings.CELERY_MAX_RETRIES,
)
def send_kafka_task(self, result: float):
    """Asynchronously sends data to Kafka without blocking the calling shuffle."""
    return asyncio.run(
        send_to_kafka(
            topic=settings.KAFKA_OUTPUT_TOPIC,
            data={"result": result},
        )
    )


@celery_app.task(
    bind=True,
    autoretry_for=(TransientProcessingError,),
    retry_backoff=True,
    max_retries=settings.CELERY_MAX_RETRIES,
)
def task_1(self, value: float):  # noqa
    """Process the input value by adding 100 and scheduling the next task.

    Logs the received value for traceability, increments it by 100,
    and enqueues `task_2`.

    Args:
        self: The bound task instance providing access to retry context.
        value (float): Numeric input to be processed.
    """
    logger.info("Received: %s", value)

    new_value = value + 100
    logger.info("After +100: %s", new_value)

    task_2.delay(new_value)


@celery_app.task(
    bind=True,
    autoretry_for=(TransientProcessingError,),
    retry_backoff=True,
    max_retries=settings.CELERY_MAX_RETRIES,
)
def task_2(self, value: float):  # noqa
    """Process the input value by subtracting 1000 and sending the result to Kafka.

    Logs the received value, applies a subtraction of 1000, and publishes
    the result to the configured Kafka output topic.

    Args:
        self: The bound task instance providing access to retry context.
        value (float): Numeric input from the preceding task.
    """
    logger.info("Received: %s", value)

    result = value - 1000
    logger.info("After -1000: %s", result)

    # Send to Kafka asynchronously
    send_kafka_task.delay(result)
