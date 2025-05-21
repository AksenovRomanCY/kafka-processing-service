import asyncio
import random

from app.celery_app import celery_app
from app.kafka.producer import send_to_kafka
from app.settings import settings


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=settings.CELERY_MAX_RETRIES,
)
def task_1(self, value: float):  # noqa
    """Process the input value by adding 100 and scheduling the next task.

    This Celery task logs the received value for traceability, simulates
    intermittent failures with a 30% probability to exercise retry logic,
    then increments the value by 100 and enqueues `task_2`.

    Args:
        self: The bound task instance providing access to retry context.
        value (float): Numeric input to be processed.

    Returns:
        celery.result.AsyncResult: The AsyncResult for the enqueued `task_2` task.
    """
    print(f"[Task1] Received: {value}")

    # Simulate a random failure to trigger retry behavior
    if random.random() < 0.3:
        raise Exception("Accidental error in task1")

    new_value = value + 100
    print(f"[Task1] After +100: {new_value}")

    return task_2.delay(new_value)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=settings.CELERY_MAX_RETRIES,
)
def task_2(self, value: float):  # noqa
    """Process the input value by subtracting 1000 and sending the result to Kafka.

    This Celery task logs the received value, simulates intermittent failures
    with a 30% probability, applies a subtraction of 1000, and publishes
    the result to the configured Kafka output topic.

    Args:
        self: The bound task instance providing access to retry context.
        value (float): Numeric input from the preceding task.

    Returns:
        Any: The result of the `send_to_kafka` coroutine execution.
    """
    print(f"[Task2] Received: {value}")

    # Simulate a random failure to trigger retry behavior
    if random.random() < 0.3:
        raise Exception("Accidental error in task2")

    result = value - 1000
    print(f"[Task2] After -1000: {result}")

    # Execute the Kafka send operation; blocks until completion.
    # TODO: fix flow blocking
    return asyncio.run(
        send_to_kafka(
            topic=settings.KAFKA_OUTPUT_TOPIC,
            data={"result": result},
        )
    )
