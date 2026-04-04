# Installation

## Prerequisites

- Docker & Docker Compose
- (Optional) Python 3.13 and [Poetry](https://python-poetry.org/) for local development

## Cloning and customization

```bash
git clone https://github.com/AksenovRomanCY/kafka-processing-service.git
cd kafka-processing-service
cp .env.example .env
```

Modify `.env` if necessary — see [Environment Variables](#environment-variables) below.

## First launch

```bash
docker compose up -d --build
```

This will start:
- Kafka (KRaft mode, Apache Kafka 4.0)
- Redis
- Consumer
- Celery Worker
- init-kafka-topics (creates `input`, `output`, `error`, `dead-letter`)

Status check:
```bash
docker compose ps
```

All services should show `healthy` status.

## Stopping and cleaning

```bash
docker compose down -v
```

## Environment Variables

All configuration is done via `.env` file (copied from `.env.example`).

| Variable | Default | Description |
|---|---|---|
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka broker address(es), comma-separated for clusters |
| `KAFKA_INPUT_TOPIC` | `input` | Topic to consume messages from |
| `KAFKA_OUTPUT_TOPIC` | `output` | Topic to publish processing results to |
| `KAFKA_ERROR_TOPIC` | `error` | Topic for invalid messages |
| `KAFKA_DLQ_TOPIC` | `dead-letter` | Topic for permanently failed tasks (Dead Letter Queue) |
| `KAFKA_GROUP_ID` | `kafka-handler-group` | Consumer group ID for offset tracking |
| `REDIS_HOST` | `redis` | Redis host for Celery broker |
| `REDIS_PORT` | `6379` | Redis port (valid range: 1-65535) |
| `REDIS_PASSWORD` | _(empty)_ | Redis password; leave empty for local development |
| `CELERY_MAX_RETRIES` | `3` | Maximum retry attempts per task on `TransientProcessingError` |
| `CELERY_TASK_TIME_LIMIT` | `300` | Hard time limit per task in seconds (300 = 5 min) |
| `LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |

## Development

Install all dependencies (including dev tools) via Poetry:
```bash
poetry install
```
