# Usage

## Startup and shutdown

```bash
make up
```
```bash
make down
```

## Sending data to Kafka `input`

```bash
make send-valid
```

This sends:

```json
{"value": 10}
```

To send invalid messages:

```bash
make send-invalid
```

This sends:

```json
{"foo": "bar"}
not-json
```

Both are routed to the `error` topic.

## Reading from Kafka `output`

```bash
make read-output
```

Expected output:
```json
{"result": -890, "trace_id": "a1b2c3d4-..."}
```

## Reading errors from Kafka `error`

```bash
make read-error
```

Expected output:
```json
{"error": "{\"foo\":\"bar\"}", "trace_id": "d4c3b2a1-..."}
{"error": "not-json", "trace_id": "e5f6a7b8-..."}
```

## Dead Letter Queue demo

Send a valid message that intentionally fails `task_2`:

```bash
make send-dlq-demo
```

Payload:

```json
{"value": 10, "fail": "task_2"}
```

After Celery retries are exhausted, read the DLQ:

```bash
make read-dlq
```

Expected fields:

```json
{
  "task_name": "app.worker_tasks.task_2",
  "exception": "Demo failure requested for task_2",
  "trace_id": "..."
}
```

## Checking service health

```bash
make ps
```

All services should show `healthy` status. The consumer uses a liveness file (`/tmp/consumer-alive`), the worker uses `celery inspect ping`.

## Viewing logs

Logs are in JSON format with `trace_id` correlation:

```bash
make logs
```

To trace a specific message across all components:
```bash
make logs-trace TRACE_ID=<trace_id>
```

## Scripted showcase

Run the full demo:

```bash
make demo
```

Run the executable smoke check against an already running stack:

```bash
make smoke
```
