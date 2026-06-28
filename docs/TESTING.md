# Testing

## Unit Tests

### Launch:

```bash
make test
```

Full local CI check:

```bash
make ci
```

### What's covered:

* **Consumer (`handle_message`)**:
  * valid payload dispatches a Celery chain with `trace_id`
  * invalid JSON sends to error topic
  * missing `value` or `null` field
  * non-numeric value
  * float and negative numbers
  * `trace_id` is generated and included in log records and error messages

* **Consumer (`consume`)**:
  * processes messages and commits offsets
  * starts producer before consumer
  * creates consumer with correct settings
  * registers signal handlers (SIGTERM, SIGINT)
  * stops gracefully on shutdown signal
  * calls stop on both normal exit and exception

* **Consumer heartbeat**:
  * touches liveness file periodically
  * stops on event
  * updates mtime across iterations

* **Celery tasks** (`task_1`, `task_2`, `send_kafka_task`):
  * `task_1` returns `value + 100`
  * `task_2` returns `value - 1000`
  * `send_kafka_task` sends result with `trace_id` to output topic
  * `trace_id` propagation through all tasks

* **Dead Letter Queue**:
  * `DLQTask.on_failure` sends failure details to `dead-letter` topic

* **`AsyncKafkaProducer`**:
  * `start()` creates and starts underlying producer
  * `start()` raises if already running
  * `stop()` stops and clears
  * `send()` calls `send_and_wait`
  * `send()` raises if not started
  * value serializer produces valid JSON

* **`SyncKafkaProducer`**:
  * lazy initialization on first call
  * reuses producer on subsequent calls
  * `send()` calls `send` + `get(timeout=10)`
  * `close()` closes and clears
  * value serializer produces valid JSON

### Test isolation:

All Kafka producers are stubbed via `conftest.py` autouse fixture — no broker required. Celery tasks run in eager mode (synchronous, no Redis required).

## E2E (Docker Compose)

```bash
make up
```

Check:
* `make ps` — all services show `healthy` status
* Send a message to `input`, verify result in `output`
* Send invalid JSON to `input`, verify error in `error` topic
* Check logs for JSON format and `trace_id` correlation: `make logs`

## Smoke Test

`make smoke` verifies the main happy and error paths against an already running
Docker Compose stack:

```bash
make up
make smoke
```

It sends a unique valid payload to `input`, verifies the expected result in
`output`, sends a unique invalid payload, and verifies it in the `error` topic.

The smoke test does not start or stop Docker Compose on its own. Use
`make demo` for the full scripted showcase.
