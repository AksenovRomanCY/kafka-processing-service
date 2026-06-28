# Demo

This walkthrough demonstrates the main Kafka/Celery processing paths:

```text
input -> consumer -> Celery chain -> output
                  \-> error
                   \-> dead-letter
```

## 1. Start the stack

```bash
make up
make ps
```

All long-running services should be `healthy`:

- `kafka`
- `redis`
- `consumer`
- `worker`

## 2. Happy path

Send a valid message:

```bash
make send-valid
```

Read the output topic:

```bash
make read-output
```

Expected message shape:

```json
{"result": -890, "trace_id": "..."}
```

The result is calculated by the Celery chain:

```text
10 -> task_1 (+100) -> 110 -> task_2 (-1000) -> -890
```

## 3. Invalid input path

Send invalid messages:

```bash
make send-invalid
```

Read the error topic:

```bash
make read-error
```

Expected message shape:

```json
{"error": "{\"foo\":\"bar\"}", "trace_id": "..."}
{"error": "not-json", "trace_id": "..."}
```

## 4. Dead Letter Queue path

Send a valid message that intentionally fails `task_2`:

```bash
make send-dlq-demo
```

Payload:

```json
{"value": 10, "fail": "task_2"}
```

Wait for retries to exhaust, then read the DLQ:

```bash
make read-dlq
```

Expected message shape:

```json
{
  "task_name": "app.worker_tasks.task_2",
  "exception": "Demo failure requested for task_2",
  "trace_id": "..."
}
```

## 5. Trace a message

Copy a `trace_id` from any `output`, `error`, or `dead-letter` message:

```bash
make logs-trace TRACE_ID=<trace_id>
```

Consumer and worker logs are JSON formatted, so the same `trace_id` can be
followed across message validation, task execution, output publishing, and DLQ
routing.

## 6. Scripted run

Run the full showcase:

```bash
make demo
```

Run the executable smoke check against an already running stack:

```bash
make smoke
```
