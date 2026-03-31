# Roadmap v2.0.0

Implementation plan for all issues identified in [ISSUES.md](ISSUES.md).
Baseline: tag `v1.0.0` (commit `dc3d76b`).

---

## ~~Phase 1: Logging (H3, M1)~~ DONE ✅ `7ae64c7`

Replace all `print()` with structured `logging`. Update tests accordingly.

### ~~1.1 Add logging configuration~~ ✅

| Action | Details |
|---|---|
| CREATE | `app/logging_config.py` |

```
- Configure `logging.basicConfig` with format: timestamp, level, logger name, message
- Set default level INFO, allow override via env var LOG_LEVEL
- Add LOG_LEVEL: str = "INFO" to Settings
```

### ~~1.2 Replace print() -> logger~~ ✅

| Action | File | What |
|---|---|---|
| REPLACE | `app/kafka/consumer.py:31` | `print(f"[Kafka] Valid value: ...")` -> `logger.info(...)` |
| REPLACE | `app/kafka/consumer.py:34` | `print(f"[Kafka] Celery task_1 ...")` -> `logger.info(...)` |
| REPLACE | `app/kafka/consumer.py:37` | `print(f"[Kafka][Error] ...")` -> `logger.error(...)` |
| REPLACE | `app/kafka/consumer.py:64` | `print(f"[Kafka] Message received: ...")` -> `logger.info(...)` |
| REPLACE | `app/worker_tasks.py:45` | `print(f"[Task1] Received: ...")` -> `logger.info(...)` |
| REPLACE | `app/worker_tasks.py:52` | `print(f"[Task1] After +100: ...")` -> `logger.info(...)` |
| REPLACE | `app/worker_tasks.py:77` | `print(f"[Task2] Received: ...")` -> `logger.info(...)` |
| REPLACE | `app/worker_tasks.py:84` | `print(f"[Task2] After -1000: ...")` -> `logger.info(...)` |
| REPLACE | `app/kafka/producer.py:29` | `print(f"[Kafka] Posted in ...")` -> `logger.info(...)` |

### ~~1.3 Update tests (M1)~~ ✅

| Action | File | What |
|---|---|---|
| REPLACE | `tests/unit/test_consumer.py` | All `capsys.readouterr()` assertions -> `caplog` fixture |
| REMOVE | All tests | Dependency on exact print string format |
| KEEP | All tests | Behavioral assertions (`sent["topic"]`, `task_1.delay` calls) |

### ~~Commit: `refactor: replace print() with structured logging`~~ ✅

---

## ~~Phase 2: Error Handling (M2)~~ DONE ✅

Remove simulated failures from production code. Narrow retry scope.

### ~~2.1 Create custom exception~~ ✅

| Action | Details |
|---|---|
| CREATE | `app/exceptions.py` |

```python
class TransientProcessingError(Exception):
    """Retryable transient error in task processing."""
```

### ~~2.2 Clean up worker tasks~~ ✅

| Action | File | What |
|---|---|---|
| REMOVE | `app/worker_tasks.py:47-49` | `if random.random() < 0.3: raise Exception(...)` from `task_1` |
| REMOVE | `app/worker_tasks.py:79-81` | `if random.random() < 0.3: raise Exception(...)` from `task_2` |
| REMOVE | `app/worker_tasks.py:1` | `import random` (no longer needed) |
| REPLACE | `app/worker_tasks.py` | `autoretry_for=(Exception,)` -> `autoretry_for=(TransientProcessingError,)` in all 3 tasks |

### ~~2.3 Update tests~~ ✅

| Action | File | What |
|---|---|---|
| REMOVE | `tests/unit/test_worker_tasks.py` | `test_task_1_failure`, `test_task_2_failure` (tested simulated errors) |
| REMOVE | `tests/conftest.py` | Fixtures `random_success`, `random_fail` (no longer needed) |
| REMOVE | `tests/conftest.py` | `import random` |
| UPDATE | `tests/unit/test_worker_tasks.py` | Remove `@pytest.mark.usefixtures("random_success")` from remaining tests |

### ~~Commit: `refactor: remove simulated failures, narrow retry scope to TransientProcessingError`~~ ✅

---

## ~~Phase 3: Settings & Configuration (M4)~~ DONE ✅

Expand, validate, and centralize all configuration.

### ~~3.1 Extend Settings class~~ ✅

| Action | File | What |
|---|---|---|
| ADD | `app/settings.py` | `LOG_LEVEL: str = "INFO"` |
| ADD | `app/settings.py` | `KAFKA_GROUP_ID: str = "kafka-handler-group"` |
| ADD | `app/settings.py` | `REDIS_PASSWORD: str \| None = None` |
| ADD | `app/settings.py` | `CELERY_TASK_TIME_LIMIT: int = 300` |
| ADD | `app/settings.py` | Pydantic `field_validator` for `REDIS_PORT` (range 1-65535) |
| UPDATE | `app/settings.py` | `REDIS_BROKER_URL` property: include password when set (`redis://:pass@host:port/0`) |

### ~~3.2 Use settings in code (remove hardcoded values)~~ ✅

| Action | File | What |
|---|---|---|
| REPLACE | `app/kafka/consumer.py:57` | `group_id="kafka-handler-group"` -> `group_id=settings.KAFKA_GROUP_ID` |
| REPLACE | `app/celery_app.py:15` | `task_time_limit=300` -> `task_time_limit=settings.CELERY_TASK_TIME_LIMIT` |
| REPLACE | `app/logging_config.py` | Use `settings.LOG_LEVEL` for configuring log level |

### ~~3.3 Environment template~~ ✅

| Action | File | What |
|---|---|---|
| UPDATE | `.env.example` | Add all new variables with comments and defaults |

### ~~Commit: `feat: centralize configuration, add validation and new settings`~~ ✅

---

## ~~Phase 4: Producer Refactor (H1, H2)~~ DONE ✅

Eliminate per-message connection overhead. Remove async/sync mixing.

### ~~4.1 Split producer into async and sync implementations~~ ✅

| Action | File | What |
|---|---|---|
| REWRITE | `app/kafka/producer.py` | Persistent async producer: init once, reuse. Functions: `start_producer()`, `stop_producer()`, `send_to_kafka()` |
| CREATE | `app/kafka/sync_producer.py` | Sync producer using `kafka-python` library: module-level `KafkaProducer` singleton, `sync_send_to_kafka(topic, data)` |

### ~~4.2 Update consumer to manage producer lifecycle~~ ✅

| Action | File | What |
|---|---|---|
| UPDATE | `app/kafka/consumer.py` | Call `start_producer()` before consumer loop, `stop_producer()` in `finally` block |

### ~~4.3 Update worker tasks to use sync producer~~ ✅

| Action | File | What |
|---|---|---|
| REPLACE | `app/worker_tasks.py` | `send_kafka_task`: replace `asyncio.run(send_to_kafka(...))` with `sync_send_to_kafka(...)` |
| REMOVE | `app/worker_tasks.py` | `import asyncio` (no longer needed) |
| REMOVE | `app/worker_tasks.py` | Import of async `send_to_kafka` |

### ~~4.4 Update dependencies~~ ✅

| Action | File | What |
|---|---|---|
| ADD | `requirements.txt` | `kafka-python-ng` (maintained fork of `kafka-python`) |

### ~~4.5 Update tests~~ ✅

| Action | File | What |
|---|---|---|
| UPDATE | `tests/conftest.py` | Patch `sync_send_to_kafka` instead of `send_to_kafka` in worker context |
| UPDATE | `tests/unit/test_worker_tasks.py` | Adapt `test_send_kafka_task_invokes_coroutine` for sync producer |

### ~~Commit: `refactor: persistent async producer for consumer, sync producer for worker`~~ ✅

---

## ~~Phase 5: Test Coverage (M5, L1)~~ DONE ✅

Cover untested modules and paths.

### ~~5.1 Producer tests~~ ✅

| Action | File | What |
|---|---|---|
| CREATE | `tests/unit/test_producer.py` | Test async `send_to_kafka`: mock `AIOKafkaProducer`, verify `send_and_wait` called with correct topic/data |
| ADD | `tests/unit/test_producer.py` | Test producer `stop()` called in `finally` even on exception |
| ADD | `tests/unit/test_producer.py` | Test JSON serialization of data |

### ~~5.2 Sync producer tests~~ ✅

| Action | File | What |
|---|---|---|
| CREATE | `tests/unit/test_sync_producer.py` | Test `sync_send_to_kafka`: mock `KafkaProducer`, verify `send` called correctly |

### ~~5.3 Consumer loop tests~~ ✅

| Action | File | What |
|---|---|---|
| ADD | `tests/unit/test_consumer.py` | Test `consume()`: mock `AIOKafkaConsumer` to yield messages, verify `handle_message` called, `commit()` called after each, `stop()` called on exit |

### ~~Commit: `test: add coverage for producer module and consume() loop`~~ ✅

---

## ~~Phase 6: Documentation (M3, L5)~~ DONE ✅

Document architectural decisions and security scope.

### ~~6.1 Delivery semantics~~ ✅

| Action | File | What |
|---|---|---|
| ADD | `app/kafka/consumer.py:66` | Comment block explaining at-most-once delivery semantics and the conscious trade-off |
| UPDATE | `docs/ARCHITECTURE.md` | Section "Delivery Guarantees": explain that offset is committed after enqueue, not after task completion |

### ~~6.2 Security scope~~ ✅

| Action | File | What |
|---|---|---|
| UPDATE | `docs/ARCHITECTURE.md` | Section "Security": state this is a dev-only setup, no auth/TLS. List what would be needed for production |

### ~~6.3 Environment setup~~ ✅

| Action | File | What |
|---|---|---|
| UPDATE | `docs/INSTALLATION.md` | Document `.env.example` -> `.env` copy step, explain each variable |

### ~~Commit: `docs: document delivery semantics, security scope, env setup`~~ ✅

---

## ~~Phase 7: Infrastructure (L2, L3, L4)~~ DONE ✅

Modernize Docker setup, migrate Kafka to KRaft, add graceful shutdown.

### ~~7.1 Migrate Kafka to KRaft mode (remove Zookeeper)~~ ✅

| Action | File | What |
|---|---|---|
| REMOVE | `docker-compose.yml` | Entire `zookeeper` service (lines 6-18) |
| REMOVE | `docker-compose.yml` | Volume `zk-data` |
| UPDATE | `docker-compose.yml` | `bitnami/kafka:3.7` -> `bitnami/kafka:4.2` |
| REMOVE | `docker-compose.yml` | `KAFKA_CFG_ZOOKEEPER_CONNECT: zookeeper:2181` |
| ADD | `docker-compose.yml` | KRaft environment variables: `KAFKA_CFG_NODE_ID`, `KAFKA_CFG_PROCESS_ROLES`, `KAFKA_CFG_CONTROLLER_QUORUM_VOTERS`, `KAFKA_CFG_CONTROLLER_LISTENER_NAMES`, `KAFKA_KRAFT_CLUSTER_ID` |
| UPDATE | `docker-compose.yml` | Remove `depends_on: zookeeper` from kafka service |
| UPDATE | `docker-compose.yml` | Remove `depends_on: init-kafka-topics` from consumer (if topics auto-created by KRaft config) |

### ~~7.2 Improve Dockerfile~~ ✅

| Action | File | What |
|---|---|---|
| UPDATE | `Dockerfile` | `python:3.12-slim` -> `python:3.13-slim` |
| ADD | `Dockerfile` | `HEALTHCHECK` instruction (liveness file touch or HTTP ping) |
| UPDATE | `Dockerfile` | Pin to specific patch version: `python:3.13.x-slim` |

### ~~7.3 Add graceful shutdown to consumer~~ ✅

| Action | File | What |
|---|---|---|
| ADD | `app/kafka/consumer.py` | `import signal` |
| ADD | `app/kafka/consumer.py` | In `consume()`: register `SIGTERM`/`SIGINT` handlers via `loop.add_signal_handler(sig, stop_event.set)` |
| UPDATE | `app/kafka/consumer.py` | Replace bare `async for msg in consumer` with a loop that checks `stop_event.is_set()` |
| ADD | `app/kafka/consumer.py` | Log clean shutdown message on exit |

### ~~7.4 Update Redis image~~ ✅

| Action | File | What |
|---|---|---|
| UPDATE | `docker-compose.yml` | `redis:7` -> `redis:8` |

### ~~Commit: `infra: migrate Kafka to KRaft, upgrade images, add graceful shutdown`~~ ✅

---

## ~~Phase 8: Dependency Update & Python Upgrade~~ DONE ✅

Update all packages and base image to latest compatible versions.

### ~~8.1 Python upgrade~~ ✅

| Action | File | What |
|---|---|---|
| UPDATE | `Dockerfile` | `python:3.12-slim` -> `python:3.13-slim` (done in Phase 7 if merged, otherwise here) |

### ~~8.2 Update requirements.txt~~ ✅

| Action | Package | From | To |
|---|---|---|---|
| UPDATE | aiokafka | 0.12.0 | 0.13.0 |
| UPDATE | billiard | 4.2.1 | 4.2.4 |
| UPDATE | celery | 5.5.2 | 5.6.3 |
| UPDATE | click | 8.2.0 | 8.3.1 |
| UPDATE | click-plugins | 1.1.1 | 1.1.1.2 |
| UPDATE | kombu | 5.5.3 | 5.6.2 |
| UPDATE | packaging | 25.0 | 26.0 |
| UPDATE | prompt_toolkit | 3.0.51 | 3.0.52 |
| UPDATE | redis | 6.1.0 | 7.4.0 |
| UPDATE | typing_extensions | 4.13.2 | 4.15.0 |
| UPDATE | tzdata | 2025.2 | 2025.3 |
| UPDATE | vine | 5.1.0 | 5.1.0 |
| UPDATE | wcwidth | 0.2.13 | 0.6.0 |
| UPDATE | pydantic_settings | 2.9.1 | 2.13.1 |
| REMOVE | six | 1.17.0 | (transitive, remove from direct deps) |
| REMOVE | async-timeout | 5.0.1 | (transitive, remove from direct deps) |
| ADD | kafka-python-ng | — | latest (added in Phase 4) |

### ~~8.3 Pin dev dependencies~~ ✅

| Action | File | What |
|---|---|---|
| UPDATE | `requirements.dev.txt` | Pin all versions |

```
black==26.3.1
isort==8.0.1
pre-commit==4.5.1
pytest==9.0.2
pytest-asyncio==1.3.0
```

### ~~8.4 Verification~~ ✅

| Step | Command | Expected |
|---|---|---|
| 1 | `pip install -r requirements.txt` | No errors, no conflicts |
| 2 | `pip install -r requirements.dev.txt` | No errors |
| 3 | `pytest` | All tests pass |
| 4 | `docker compose build` | Images build successfully |
| 5 | `docker compose up -d` | All services start and show healthy |
| 6 | Send test message to `input` topic | Result appears on `output` topic |

### ~~Commit: `chore: update all dependencies, upgrade to Python 3.13`~~ ✅

---

## Phase Summary

| Phase | Scope | Issues Resolved | Key Risk |
|---|---|---|---|
| 1 | Logging | H3, M1 | Low: text replacement |
| 2 | Error handling | M2 | Low: removing code |
| 3 | Settings | M4 | Low: additive changes |
| 4 | Producer refactor | H1, H2 | **Medium**: new dependency, architecture change |
| 5 | Test coverage | M5, L1 | Low: adding tests |
| 6 | Documentation | M3, L5 | None: docs only |
| 7 | Infrastructure | L2, L3, L4 | **Medium**: Kafka migration, image upgrades |
| 8 | Dependencies | All deps | **Medium**: major version bumps (redis, kafka) |

Each phase is an independent commit. Phases can be merged into a single release `v2.0.0` after all pass verification.

---

## Release Checklist (v2.0.0)

- [ ] All 8 phases committed and tested
- [ ] `pytest` passes with 100% of previous + new tests
- [ ] `docker compose up -d` starts all services healthy
- [ ] End-to-end test: message in `input` -> result in `output`
- [ ] `docker compose logs` shows structured log output
- [ ] No `print()` remaining in `app/`
- [ ] No `import random` in production code
- [ ] No Zookeeper service in docker-compose
- [ ] Python 3.13 in Dockerfile
- [ ] All deps pinned in both requirements files
- [ ] Tag `v2.0.0`, create GitHub release
