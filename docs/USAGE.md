# Usage

## Startup and shutdown

```bash
docker compose up -d
```
```bash
docker compose down
```

## Sending data to Kafka `input`

```bash
docker compose exec kafka /opt/kafka/bin/kafka-console-producer.sh \
  --bootstrap-server localhost:9092 \
  --topic input
```

Examples of messages:
```json
{"value": 10}
{"value": 42.5}
{"foo": "bar"}
```
The first two are valid and will be processed. The third is invalid and goes to the `error` topic.

## Reading from Kafka `output`

```bash
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic output \
  --from-beginning \
  --timeout-ms 10000
```

Expected output:
```json
{"result": -890, "trace_id": "a1b2c3d4-..."}
{"result": -857.5, "trace_id": "e5f6a7b8-..."}
```

## Reading errors from Kafka `error`

```bash
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic error \
  --from-beginning \
  --timeout-ms 10000
```

Expected output:
```json
{"error": "{\"foo\":\"bar\"}", "trace_id": "d4c3b2a1-..."}
```

## Reading from Dead Letter Queue

Failed tasks (after all retries exhausted) are sent to the `dead-letter` topic:

```bash
docker compose exec kafka /opt/kafka/bin/kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic dead-letter \
  --from-beginning \
  --timeout-ms 10000
```

## Checking service health

```bash
docker compose ps
```

All services should show `healthy` status. The consumer uses a liveness file (`/tmp/consumer-alive`), the worker uses `celery inspect ping`.

## Viewing logs

Logs are in JSON format with `trace_id` correlation:

```bash
docker compose logs consumer
docker compose logs worker
```

To trace a specific message across all components:
```bash
docker compose logs | grep "<trace_id>"
```
