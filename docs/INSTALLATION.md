# Installation

## 📋 Preliminary requirements

- Docker & Docker Compose
- (Optional) Python 3.12 and pip for local development

## 📦 Cloning and customization

```bash
git clone https://github.com/AksenovRomanCY/kafka-processing-service.git
cd kafka-processing-service
cp .env.example .env
```

Modify `.env` if necessary (e.g. `KAFKA_BOOTSTRAP_SERVERS`, `REDIS_HOST`, `KAFKA_INPUT_TOPIC`, etc.).

## 🚀 First launch

```bash
docker-compose up -d --build
```

It will be launched:
- Kafka + Zookeeper
- Redis
- Consumer
- Celery Worker
- init-kafka-topics (creates `input`, `output`, `error`)

Status check:
```bash
docker-compose ps
```

## 🧹 Stopping and cleaning

```bash
docker-compose down -v
```
