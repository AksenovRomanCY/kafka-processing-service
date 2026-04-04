from __future__ import annotations

import logging
import traceback
from typing import Any

from app.celery_app import celery_app
from app.exceptions import TransientProcessingError
from app.kafka.sync_producer import sync_send_to_kafka
from app.settings import settings

logger = logging.getLogger(__name__)


class DLQTask(celery_app.Task):  # type: ignore[misc]
    """Base task that sends failed messages to the Dead Letter Queue.

    When a task exhausts all retries, on_failure sends the task name,
    original arguments, and exception details to the DLQ Kafka topic.
    """

    def on_failure(
        self: Any,
        exc: BaseException,
        task_id: str,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
        einfo: Any,
    ) -> None:
        trace_id = kwargs.get("trace_id", "")
        logger.error(
            "Task %s[%s] failed permanently: %s",
            self.name,
            task_id,
            exc,
            extra={"trace_id": trace_id},
        )
        sync_send_to_kafka(
            topic=settings.KAFKA_DLQ_TOPIC,
            data={
                "task_name": self.name,
                "task_id": task_id,
                "args": list(args),
                "kwargs": kwargs,
                "exception": str(exc),
                "traceback": traceback.format_exception(exc),
                "trace_id": trace_id,
            },
        )


@celery_app.task(
    bind=True,
    base=DLQTask,
    autoretry_for=(TransientProcessingError,),
    retry_backoff=True,
    max_retries=settings.CELERY_MAX_RETRIES,
)
def task_1(self: Any, value: float, *, trace_id: str = "") -> float:
    """Process the input value by adding 100.

    Returns the new value for the next task in the chain.

    Args:
        self: The bound task instance providing access to retry context.
        value: Numeric input to be processed.
        trace_id: Correlation ID for tracing the message through the pipeline.
    """
    logger.info("Received: %s", value, extra={"trace_id": trace_id})

    new_value = value + 100
    logger.info("After +100: %s", new_value, extra={"trace_id": trace_id})

    return new_value


@celery_app.task(
    bind=True,
    base=DLQTask,
    autoretry_for=(TransientProcessingError,),
    retry_backoff=True,
    max_retries=settings.CELERY_MAX_RETRIES,
)
def task_2(self: Any, value: float, *, trace_id: str = "") -> float:
    """Process the input value by subtracting 1000.

    Returns the result for the next task in the chain.

    Args:
        self: The bound task instance providing access to retry context.
        value: Numeric input from the preceding task.
        trace_id: Correlation ID for tracing the message through the pipeline.
    """
    logger.info("Received: %s", value, extra={"trace_id": trace_id})

    result = value - 1000
    logger.info("After -1000: %s", result, extra={"trace_id": trace_id})

    return result


@celery_app.task(
    bind=True,
    base=DLQTask,
    autoretry_for=(TransientProcessingError,),
    retry_backoff=True,
    max_retries=settings.CELERY_MAX_RETRIES,
)
def send_kafka_task(self: Any, result: float, *, trace_id: str = "") -> None:
    """Send computed result to the Kafka output topic.

    Uses a synchronous KafkaProducer singleton to avoid event loop
    creation overhead in the Celery worker process.
    """
    sync_send_to_kafka(
        topic=settings.KAFKA_OUTPUT_TOPIC,
        data={"result": result, "trace_id": trace_id},
    )
