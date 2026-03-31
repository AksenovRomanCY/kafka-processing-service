from celery import Celery

import app.logging_config  # noqa: F401
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
    task_time_limit=300,
    result_backend=None,
)
