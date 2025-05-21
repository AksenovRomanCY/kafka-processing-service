# Testing

## ✅ Unit Tests

### Launch:

```bash
pytest
````

### What's covered:

* **Validation of JSON** in `handle_message`:

  * valid payload
  * invalid JSON
  * missing `value` or `null` field
  * non-numeric value
  * float and negative numbers

* **Celery-task logic** `task_1` and `task_2`:

  * successful path (`value + 100 → task_2.delay`; `value - 1000 → send_to_kafka`)
  * exception branch (unpacking `random_fail`)

* **Swap all calls** of `send_to_kafka` to a stub

## 🔬 E2E (docker-compose)

```bash
docker-compose up --build --abort-on-container-exit
```

Check:
* All services are running
* Console producer/consumer is working correctly
