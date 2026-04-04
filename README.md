<!-- README.md -->
[![CI](https://github.com/AksenovRomanCY/kafka-processing-service/actions/workflows/ci.yml/badge.svg)](https://github.com/AksenovRomanCY/kafka-processing-service/actions/workflows/ci.yml)

# Kafka Processing Service

Background task processing pipeline built with Kafka, Celery, and Redis.

1. **Consumer** (aiokafka): reads from Kafka `input`, validates JSON, sends invalid messages to `error` topic, dispatches a Celery chain for valid ones.
2. **Celery chain** (Redis broker):
   - `task_1`: adds 100 to the input value
   - `task_2`: subtracts 1000
   - `send_kafka_task`: publishes `{"result": <number>, "trace_id": "<uuid>"}` to Kafka `output`

   Each task retries on `TransientProcessingError` with exponential backoff. Permanently failed tasks are sent to a Dead Letter Queue (`dead-letter` topic).
3. **Observability**: structured JSON logging with per-message `trace_id` correlation across all components.

Documentation:
- [INSTALLATION](docs/INSTALLATION.md)
- [USAGE](docs/USAGE.md)
- [ARCHITECTURE](docs/ARCHITECTURE.md)
- [TESTING](docs/TESTING.md)
