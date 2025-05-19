import asyncio
import json

from aiokafka import AIOKafkaConsumer

from app.kafka.producer import send_to_kafka
from app.settings import settings
from app.worker_tasks import task_1


async def consume():
    consumer = AIOKafkaConsumer(
        settings.KAFKA_INPUT_TOPIC,
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: m.decode("utf-8"),
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        group_id="kafka-handler-group",
    )
    await consumer.start()

    try:
        async for msg in consumer:
            raw_value = msg.value
            print(f"[Kafka] Получено сообщение: {raw_value}")

            try:
                payload = json.loads(raw_value)
                number = payload.get("value")

                if not isinstance(number, (int, float)):
                    raise ValueError("Поле 'value' отсутствует или не число")

                print(f"[Kafka] Валидное значение: {number}")

                res = task_1.delay(number)
                print(f"[Kafka] Celery task_1 запущена с ID: {res.id}")

            except Exception as e:
                print(f"[Kafka][Ошибка] Невалидное сообщение: {raw_value} — {e}")

                await send_to_kafka(
                    topic=settings.KAFKA_ERROR_TOPIC, data={"error": raw_value}
                )

    finally:
        await consumer.stop()


if __name__ == "__main__":
    # TODO: позже можно заменить на запуск через supervisor/gunicorn
    asyncio.run(consume())
