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
    print(f"[Task1] Получено: {value}")

    # Random exception
    if random.random() < 0.3:
        raise Exception("Случайная ошибка в task1")

    new_value = value + 100
    print(f"[Task1] После +100: {new_value}")

    # TODO: можно добавить chain для явной передачи в task2
    return task_2.delay(new_value)


@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=settings.CELERY_MAX_RETRIES,
)
def task_2(self, value: float):  # noqa
    print(f"[Task2] Получено: {value}")

    # Random exception
    if random.random() < 0.3:
        raise Exception("Случайная ошибка в task2")

    result = value - 1000
    print(f"[Task2] После -1000: {result}")

    return send_to_kafka(
        topic=settings.KAFKA_OUTPUT_TOPIC,
        data={"result": result},
    )
