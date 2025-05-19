from celery import Celery

from app.settings import settings

celery_app = Celery(
    "worker",
    broker=settings.REDIS_BROKER_URL,
    include=["app.worker_tasks"],
)

celery_app.conf.update(
    task_track_started=True,
    task_time_limit=300,
    result_backend=None,
)
