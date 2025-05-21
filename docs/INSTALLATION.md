# Installation

## 📋 Предварительные требования

- Docker & Docker Compose
- (Опционально) Python 3.12 и pip для локальной разработки

## 📦 Клонирование и настройка

```bash
git clone https://github.com/your-org/your-repo.git
cd your-repo
cp .env.example .env
```

При необходимости измените `.env` (например, `KAFKA_BOOTSTRAP_SERVERS`, `REDIS_HOST`, `KAFKA_INPUT_TOPIC` и т. д.)

## 🚀 Первый запуск

```bash
docker-compose up -d --build
```

Будут запущены:
- Kafka + Zookeeper
- Redis
- Consumer
- Celery Worker
- init-kafka-topics (создаёт `input`, `output`, `error`)

Проверка статуса:
```bash
docker-compose ps
```

## 🧹 Остановка и очистка

```bash
docker-compose down -v
```
