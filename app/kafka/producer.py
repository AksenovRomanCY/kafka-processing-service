import json

from aiokafka import AIOKafkaProducer

from app.settings import settings


async def send_to_kafka(topic: str, data: dict):
    producer = AIOKafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )
    await producer.start()
    try:
        await producer.send_and_wait(topic, data)
        print(f"[Kafka] Отправлено в топик `{topic}`: {data}")
    finally:
        await producer.stop()
