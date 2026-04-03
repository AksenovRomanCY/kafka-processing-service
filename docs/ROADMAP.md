# Roadmap v3.0.0

Implementation plan for improvements identified during codebase audit.
Baseline: tag `v2.0.0` (commit `a013abe`).

---

## Phase 1: Kafka Client Migration ✅

Replace archived `kafka-python-ng` with the original `kafka-python`, which resumed active development. The `kafka-python-ng` repository was archived in July 2025 and no longer receives updates or security patches.

### 1.1 Swap dependency

| Action | File | What |
|---|---|---|
| REPLACE | `requirements.txt` | `kafka-python-ng==2.2.3` -> `kafka-python>=2.3.0` |

No code changes required: both packages use the same module name `kafka`, so all imports (`from kafka import KafkaProducer`) remain valid.

### 1.2 Verify Kafka 4.0 compatibility notes

| Item | Status | Detail |
|---|---|---|
| `classic` consumer protocol | Required | `KAFKA_GROUP_COORDINATOR_REBALANCE_PROTOCOLS: classic,consumer` must stay in `docker-compose.yml` — aiokafka does not support KIP-848 |
| MetadataRequest V0-V3 | OK | Kafka 4.0 GA restored support (KAFKA-18648) for aiokafka/kafka-python compatibility |
| `linger.ms` default | Changed | 0 -> 5ms in Kafka 4.0; no action needed but worth noting for latency-sensitive scenarios |
| aiokafka 0.14.0 | Watch | Will add proper API version negotiation; upgrade when released |

### 1.3 Verification

| Step | Command | Expected |
|---|---|---|
| 1 | `pip install kafka-python>=2.3.0` | No errors, no conflicts |
| 2 | `pytest` | All tests pass |
| 3 | `docker compose build && docker compose up -d` | All services healthy |
| 4 | Send message to `input` topic | Result appears on `output` topic |

### Commit: `chore: replace archived kafka-python-ng with kafka-python`

---

## Phase 2: Linting & Type Checking

Migrate from black+isort to ruff. Add mypy strict. Fix missing `from __future__ import annotations`.

### 2.1 Migrate to ruff

| Action | File | What |
|---|---|---|
| REMOVE | `requirements.dev.txt` | `black`, `isort` |
| ADD | `requirements.dev.txt` | `ruff` |
| CREATE | `pyproject.toml` or `ruff.toml` | Ruff configuration: `line-length = 88`, `select = ["E", "F", "I", "UP"]` |
| UPDATE | `.pre-commit-config.yaml` | Replace `black` and `isort` hooks with single `ruff` hook (`ruff check --fix` + `ruff format`) |
| RUN | `ruff format .` | Reformat entire codebase |
| RUN | `ruff check --fix .` | Auto-fix lint issues |

### 2.2 Add mypy

| Action | File | What |
|---|---|---|
| ADD | `requirements.dev.txt` | `mypy` |
| ADD | `pyproject.toml` | `[tool.mypy]` section: `strict = true`, `plugins = ["pydantic.mypy"]` |
| ADD | `.pre-commit-config.yaml` | `mypy` hook |
| FIX | `app/` | Resolve any type errors reported by `mypy --strict` |

### 2.3 Add missing `from __future__ import annotations`

| Action | File | What |
|---|---|---|
| ADD | `app/kafka/consumer.py` | `from __future__ import annotations` at top |
| ADD | `app/settings.py` | `from __future__ import annotations` at top |
| ADD | `app/celery_app.py` | `from __future__ import annotations` at top |
| ADD | `app/logging_config.py` | `from __future__ import annotations` at top |
| ADD | `app/__init__.py` | `from __future__ import annotations` at top |
| ADD | `app/kafka/__init__.py` | `from __future__ import annotations` at top |

### 2.4 Verification

| Step | Command | Expected |
|---|---|---|
| 1 | `ruff check .` | No errors |
| 2 | `ruff format --check .` | No changes needed |
| 3 | `mypy app/` | No errors |
| 4 | `pytest` | All tests pass |

### Commit: `refactor: migrate to ruff, add mypy strict`

---

## Phase 3: Poetry Migration

Replace `requirements.txt` / `requirements.dev.txt` with Poetry. Separate direct dependencies from transitive ones.

### 3.1 Initialize Poetry

| Action | File | What |
|---|---|---|
| RUN | `poetry init` | Create `pyproject.toml` with project metadata |
| ADD | `pyproject.toml` | `[tool.poetry.dependencies]` — only direct deps: `aiokafka`, `kafka-python`, `celery`, `redis`, `pydantic-settings` |
| ADD | `pyproject.toml` | `[tool.poetry.group.dev.dependencies]` — `ruff`, `mypy`, `pytest`, `pytest-asyncio`, `pre-commit` |
| RUN | `poetry lock` | Generate `poetry.lock` with pinned transitive deps |
| REMOVE | `requirements.txt` | Replaced by `pyproject.toml` |
| REMOVE | `requirements.dev.txt` | Replaced by `[tool.poetry.group.dev]` |

### 3.2 Update Dockerfile

| Action | File | What |
|---|---|---|
| UPDATE | `Dockerfile` | Install Poetry, copy `pyproject.toml` + `poetry.lock`, run `poetry install --only main --no-root` |
| UPDATE | `Dockerfile` | Set `POETRY_VIRTUALENVS_CREATE=false` for container context |

### 3.3 Update documentation

| Action | File | What |
|---|---|---|
| UPDATE | `docs/INSTALLATION.md` | Replace `pip install -r requirements.txt` with `poetry install` |
| UPDATE | `docs/TESTING.md` | Replace `pip install -r requirements.dev.txt` with `poetry install --with dev` |

### 3.4 Verification

| Step | Command | Expected |
|---|---|---|
| 1 | `poetry install` | No errors, no conflicts |
| 2 | `poetry run pytest` | All tests pass |
| 3 | `docker compose build` | Images build successfully |
| 4 | `docker compose up -d` | All services start and show healthy |

### Commit: `chore: migrate from requirements.txt to Poetry`

---

## Phase 4: CI/CD

Add GitHub Actions workflow: lint, typecheck, test, build.

### 4.1 Create workflow

| Action | File | What |
|---|---|---|
| CREATE | `.github/workflows/ci.yml` | GitHub Actions CI pipeline |

```yaml
# Workflow steps:
# 1. Checkout code
# 2. Set up Python 3.13
# 3. Install Poetry
# 4. poetry install --with dev
# 5. ruff check .
# 6. ruff format --check .
# 7. mypy app/
# 8. pytest --tb=short
# 9. docker compose build (on push to main only)
```

### 4.2 Configure triggers

```
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
```

### 4.3 Add status badge

| Action | File | What |
|---|---|---|
| UPDATE | `README.md` | Add CI status badge at the top |

### Commit: `chore: add GitHub Actions CI pipeline`

---

## Phase 5: Celery Pipeline Reliability

Replace manual `.delay()` chaining with Celery `chain()`. Add Dead Letter Queue for failed tasks. Enable result backend.

### 5.1 Migrate to Celery chain

| Action | File | What |
|---|---|---|
| UPDATE | `app/kafka/consumer.py` | Import `chain` from celery, replace `task_1.delay(number)` with `chain(task_1.s(number), task_2.s(), send_kafka_task.s()).delay()` |
| UPDATE | `app/worker_tasks.py` | Remove `task_2.delay(new_value)` from `task_1`, remove `send_kafka_task.delay(result)` from `task_2` — each task now returns its value for the next link |
| UPDATE | `app/worker_tasks.py` | `task_1`: return `new_value`; `task_2`: return `result`; `send_kafka_task`: unchanged |

### 5.2 Add Dead Letter Queue

| Action | File | What |
|---|---|---|
| ADD | `app/settings.py` | `KAFKA_DLQ_TOPIC: str = "dead-letter"` |
| ADD | `init-topics.sh` | Create `dead-letter` topic (3 partitions) |
| ADD | `app/worker_tasks.py` | `on_failure` handler on each task: sends failed message payload + exception info to DLQ topic |
| CREATE | `app/exceptions.py` | Add `TaskFailedPermanentlyError` for non-retryable failures |

### 5.3 Enable result backend

| Action | File | What |
|---|---|---|
| UPDATE | `app/celery_app.py` | `result_backend=None` -> `result_backend=settings.REDIS_BROKER_URL` |
| ADD | `app/celery_app.py` | `result_expires=3600` — auto-cleanup results after 1 hour |

### 5.4 Update tests

| Action | File | What |
|---|---|---|
| UPDATE | `tests/unit/test_worker_tasks.py` | Adapt tests: `task_1` and `task_2` now return values instead of calling `.delay()` |
| ADD | `tests/unit/test_worker_tasks.py` | Test DLQ: simulate `max_retries` exceeded, verify message sent to DLQ topic |
| UPDATE | `tests/unit/test_consumer.py` | Adapt `handle_message` tests for `chain()` call |

### 5.5 Verification

| Step | Command | Expected |
|---|---|---|
| 1 | `pytest` | All tests pass |
| 2 | `docker compose up -d` | Services healthy |
| 3 | Send valid message to `input` | Result in `output` |
| 4 | Simulate permanent failure | Message appears in `dead-letter` topic |

### Commit: `feat: celery chain, dead letter queue, result backend`

---

## Phase 6: Structured Logging

Migrate from plain text logging to JSON format. Add correlation ID for tracing messages through the pipeline.

### 6.1 Add JSON logging

| Action | File | What |
|---|---|---|
| ADD | `pyproject.toml` | Dependency: `python-json-logger` |
| REWRITE | `app/logging_config.py` | Configure `pythonjsonlogger.json.JsonFormatter` with fields: `timestamp`, `level`, `logger`, `message` |

### 6.2 Add correlation ID

| Action | File | What |
|---|---|---|
| UPDATE | `app/kafka/consumer.py` | Generate `trace_id` (UUID) per message, pass it through the task chain |
| UPDATE | `app/worker_tasks.py` | Accept `trace_id` parameter in all tasks, include in log messages via `logging.LoggerAdapter` or `extra=` |
| UPDATE | `app/kafka/sync_producer.py` | Include `trace_id` in outgoing Kafka messages |

### 6.3 Update tests

| Action | File | What |
|---|---|---|
| UPDATE | `tests/unit/test_consumer.py` | Verify `trace_id` is generated and passed to task chain |
| UPDATE | `tests/unit/test_worker_tasks.py` | Verify `trace_id` is included in log output and Kafka messages |

### 6.4 Verification

| Step | Command | Expected |
|---|---|---|
| 1 | `pytest` | All tests pass |
| 2 | `docker compose up -d && docker compose logs consumer` | JSON-formatted log lines |
| 3 | Send message, grep logs by `trace_id` | Same ID appears in consumer, task_1, task_2, send_kafka_task logs |

### Commit: `feat: structured JSON logging with correlation ID`

---

## Phase 7: Infrastructure

Fix Dockerfile healthcheck. Replace global singletons with dependency injection.

### 7.1 Meaningful HEALTHCHECK

| Action | File | What |
|---|---|---|
| UPDATE | `app/kafka/consumer.py` | Touch a liveness file (`/tmp/consumer-alive`) after each successful message or on a timer |
| UPDATE | `Dockerfile` | Replace `python -c "import os; os.getpid()"` with `test -f /tmp/consumer-alive && find /tmp/consumer-alive -mmin -1` |
| ADD | `docker-compose.yml` | Worker healthcheck: `celery -A app.celery_app:celery_app inspect ping` |

### 7.2 Dependency injection for producers

| Action | File | What |
|---|---|---|
| REFACTOR | `app/kafka/producer.py` | Wrap async producer in a class `AsyncKafkaProducer` with `start()`, `stop()`, `send()` methods |
| REFACTOR | `app/kafka/sync_producer.py` | Wrap sync producer in a class `SyncKafkaProducer` with `send()`, `close()` methods |
| UPDATE | `app/kafka/consumer.py` | Instantiate `AsyncKafkaProducer` in `consume()`, pass to `handle_message()` |
| UPDATE | `app/worker_tasks.py` | Accept producer as parameter or use Celery `app.conf` to hold producer instance |
| REMOVE | `app/kafka/producer.py` | `global _producer` — replaced by instance |
| REMOVE | `app/kafka/sync_producer.py` | `global _producer` — replaced by instance |

### 7.3 Update tests

| Action | File | What |
|---|---|---|
| UPDATE | `tests/conftest.py` | Create mock producer instances instead of patching module-level functions |
| UPDATE | `tests/unit/test_producer.py` | Test `AsyncKafkaProducer` class methods |
| UPDATE | `tests/unit/test_sync_producer.py` | Test `SyncKafkaProducer` class methods |

### 7.4 Verification

| Step | Command | Expected |
|---|---|---|
| 1 | `pytest` | All tests pass |
| 2 | `docker compose up -d` | All services healthy |
| 3 | `docker compose ps` | Consumer and worker show `healthy` status |
| 4 | `docker compose stop worker && docker compose ps` | Worker shows `unhealthy` after timeout |

### Commit: `refactor: meaningful healthcheck, dependency injection for producers`

---

## Phase Summary

| Phase | Scope | Key Risk |
|---|---|---|
| 1 | Kafka client migration | Low: dependency swap, no code changes |
| 2 | Linting & type checking | Low: tooling swap, no logic changes |
| 3 | Poetry migration | **Medium**: build system change, Dockerfile update |
| 4 | CI/CD | Low: additive, no code changes |
| 5 | Celery pipeline reliability | **High**: architecture change in task flow |
| 6 | Structured logging | **Medium**: logging format change, new parameter threading |
| 7 | Infrastructure | **Medium**: producer API change, healthcheck rework |

Each phase is an independent commit. Phases can be merged into a single release `v3.0.0` after all pass verification.

---

## Release Checklist (v3.0.0)

- [ ] All 7 phases committed and tested
- [ ] `kafka-python-ng` replaced with `kafka-python` — no archived dependencies
- [ ] `poetry run pytest` passes all tests
- [ ] `poetry run mypy app/` passes strict mode
- [ ] `poetry run ruff check .` — no errors
- [ ] `docker compose up -d` starts all services healthy
- [ ] End-to-end test: message in `input` -> result in `output`
- [ ] Failed task -> message in `dead-letter` topic
- [ ] `docker compose logs` shows JSON-formatted output with `trace_id`
- [ ] CI pipeline green on GitHub Actions
- [ ] No `global` mutable state in producer modules
- [ ] No `requirements.txt` / `requirements.dev.txt` in repo
- [ ] Tag `v3.0.0`, create GitHub release
