from __future__ import annotations

from celery import Celery
from celery.signals import setup_logging as celery_setup_logging

import app.logging_config
from app.settings import settings

# Instantiate a Celery application
celery_app = Celery(
    "worker",
    broker=settings.REDIS_BROKER_URL,
    include=["app.worker_tasks"],
)

# Update the Celery configuration
celery_app.conf.update(
    task_track_started=True,
    task_time_limit=settings.CELERY_TASK_TIME_LIMIT,
    result_backend=settings.REDIS_BROKER_URL,
    result_expires=3600,
    worker_hijack_root_logger=False,
)


def configure_celery_logging(**_: object) -> None:
    """Keep Celery worker logs in the same JSON format as the consumer."""
    app.logging_config.setup_logging(force=True)


celery_setup_logging.connect(configure_celery_logging)
