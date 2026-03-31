# Issues & Improvement Plan (v1.0.0)

Audit date: 2026-03-31
Baseline: tag `v1.0.0` (commit `dc3d76b`)

---

## 1. Dependency Audit

### 1.1 Python Packages (requirements.txt)

| Package | Pinned | Latest | Delta |
|---|---|---|---|
| aiokafka | 0.12.0 | **0.13.0** | minor |
| amqp | 5.3.1 | 5.3.1 | — |
| async-timeout | 5.0.1 | 5.0.1 | legacy |
| billiard | 4.2.1 | **4.2.4** | patch |
| celery | 5.5.2 | **5.6.3** | minor |
| click | 8.2.0 | **8.3.1** | minor |
| click-didyoumean | 0.3.1 | 0.3.1 | — |
| click-plugins | 1.1.1 | **1.1.1.2** | patch |
| click-repl | 0.3.0 | 0.3.0 | — |
| kombu | 5.5.3 | **5.6.2** | minor |
| packaging | 25.0 | **26.0** | major |
| prompt_toolkit | 3.0.51 | **3.0.52** | patch |
| python-dateutil | 2.9.0.post0 | 2.9.0.post0 | — |
| redis | 6.1.0 | **7.4.0** | **major** |
| six | 1.17.0 | 1.17.0 | legacy |
| typing_extensions | 4.13.2 | **4.15.0** | minor |
| tzdata | 2025.2 | **2025.3** | patch |
| vine | 5.1.0 | 5.1.0 | — |
| wcwidth | 0.2.13 | **0.6.0** | minor |
| pydantic_settings | 2.9.1 | **2.13.1** | minor |

**13 из 20** пакетов устарели. 1 мажорное обновление (`redis` 6→7).

### 1.2 Dev Packages (requirements.dev.txt) — NOT PINNED

| Package | Latest |
|---|---|
| black | 26.3.1 |
| isort | 8.0.1 |
| pre-commit | 4.5.1 |
| pytest | 9.0.2 |
| pytest-asyncio | 1.3.0 |

Версии не зафиксированы — сборки не воспроизводимы.

### 1.3 Infrastructure (Docker)

| Image | Current | Latest | Notes |
|---|---|---|---|
| python (base) | 3.12-slim | 3.13-slim / 3.14-slim | 3.12 в режиме security-only |
| bitnami/kafka | 3.7 | **4.2.0** | major; KRaft mode only |
| bitnami/zookeeper | 3.9 | — | **УДАЛИТЬ** (Kafka 4.0 убрал ZooKeeper) |
| redis | 7 | **8.6.2** | major |

### 1.4 Legacy / на удаление

| Item | Reason |
|---|---|
| **Zookeeper** | Kafka 4.0 полностью убрал поддержку ZooKeeper. Работает только KRaft. Сервис, volume и healthcheck нужно удалить |
| **six** | Прослойка совместимости Python 2/3. Транзитивная зависимость `python-dateutil`. Убрать из прямых зависимостей |
| **async-timeout** | Встроен в Python 3.11+ как `asyncio.timeout()`. Транзитивная зависимость, не нужен как прямой пакет |

---

## 2. Python Version Upgrade

### Current: Python 3.12-slim (security-only since March 2025)

### Target: Python 3.13

| Criteria | 3.12 | 3.13 | 3.14 |
|---|---|---|---|
| Support status | security-only | active bugfix | active bugfix |
| All deps support | yes | **yes (all 10/10)** | partial (7/10 explicit, celery/kombu/billiard without classifier) |
| asyncio breaking changes | — | minimal | **aggressive** (removed implicit loop creation, child watchers) |
| Risk for Celery stack | none | low | **medium** |

**Recommendation**: upgrade to **Python 3.13** now. Plan 3.14 migration when Celery ecosystem adds the formal 3.14 classifier.

### Risks for Python 3.14

- `asyncio.get_event_loop()` without a running loop raises `RuntimeError` (removed implicit creation)
- Removed child watcher subsystem (`FastChildWatcher`, `PidfdChildWatcher`)
- PEP 649: lazy annotation evaluation — may affect pydantic edge cases
- Celery/kombu/billiard: CI-tested on 3.14 but no formal PyPI classifier yet

---

## 3. Structural Issues

### 3.1 HIGH Priority

#### H1: Producer creates a new connection per message
- **File**: `app/kafka/producer.py`
- **Problem**: `send_to_kafka()` creates `AIOKafkaProducer`, connects, sends one message, disconnects. TCP handshake on every call. Under load — connection churn on the Kafka broker.
- **Fix**: Persistent producer singleton; start once, reuse across calls. For the sync worker context — use synchronous `kafka-python` `KafkaProducer`.

#### H2: `asyncio.run()` inside synchronous Celery tasks
- **File**: `app/worker_tasks.py:17`
- **Problem**: `send_kafka_task` calls `asyncio.run(send_to_kafka(...))`. Creates and destroys an event loop per task invocation. Incompatible with gevent/eventlet pools. No concurrency benefit — async used synchronously.
- **Fix**: Replace `aiokafka` in worker context with sync `kafka-python` `KafkaProducer`. Keep `aiokafka` only for the consumer process where the event loop is genuinely running.

#### H3: `print()` instead of `logging`
- **Files**: `app/kafka/consumer.py`, `app/worker_tasks.py`, `app/kafka/producer.py` — 9 calls total
- **Problem**: No timestamps, no log levels, no structured output. Errors logged the same way as info. No integration with Celery's logging. Not configurable.
- **Fix**: Introduce `logging` module with structured JSON formatter. Replace all `print()` with appropriate `logger.info()` / `logger.error()`. Update tests from `capsys` to `caplog`.

### 3.2 MEDIUM Priority

#### M1: Tests assert on stdout — fragile coupling
- **File**: `tests/unit/test_consumer.py` (lines 27-28, 46, 67, 75, 94, 106)
- **Problem**: Tests capture `capsys` and assert exact print strings. Any formatting change breaks all tests. Tests verify logging format, not business logic.
- **Fix**: After migrating to `logging`, use `caplog` fixture. Assert on behavior (was `task_1.delay` called? was `send_to_kafka` called with error topic?) not on log text.

#### M2: Bare `Exception` + simulated failures in production code
- **File**: `app/worker_tasks.py:49,81`
- **Problem**: `raise Exception("Accidental error...")` with 30% probability is hardcoded in production tasks. `autoretry_for=(Exception,)` retries ALL exceptions including bugs (`TypeError`, `KeyError`), masking real errors.
- **Fix**: Remove random failure simulation from production code (move to tests). Define `class TransientProcessingError(Exception)` and use `autoretry_for=(TransientProcessingError,)`.

#### M3: Offset committed before task completes
- **File**: `app/kafka/consumer.py:66-69`
- **Problem**: `consumer.commit()` runs after `task_1.delay()` returns, but the Celery task hasn't executed yet. If the worker crashes, the message is lost. This is at-most-once delivery.
- **Fix**: Document as an explicit architectural decision. For stronger guarantees, consider `task_acks_late=True` or Kafka Streams/Faust.

#### M4: Incomplete settings / no validation
- **File**: `app/settings.py`
- **Problem**:
  - `group_id` hardcoded in `consumer.py:57`
  - No `REDIS_PASSWORD` support
  - `task_time_limit` hardcoded in `celery_app.py:16`
  - No port range validation
  - No `.env` in repo (only `.env.example`), defaults point to Docker hostnames
- **Fix**: Add `KAFKA_GROUP_ID`, `REDIS_PASSWORD`, `CELERY_TASK_TIME_LIMIT` to Settings. Add pydantic validators. Document `.env.example` → `.env` step.

#### M5: No tests for producer module
- **File**: `app/kafka/producer.py` (no corresponding test)
- **Problem**: `send_to_kafka` is monkeypatched in all tests. Zero direct coverage of serialization, `send_and_wait`, error handling, start/stop lifecycle.
- **Fix**: Add `tests/unit/test_producer.py` with mocked `AIOKafkaProducer`.

### 3.3 LOW Priority

#### L1: No tests for `consume()` loop
- **File**: `app/kafka/consumer.py:44-72`
- **Problem**: Only `handle_message` tested. Consumer startup/shutdown, commit-after-handle, and cleanup path (`finally: stop()`) are untested.
- **Fix**: Add test with mocked `AIOKafkaConsumer` yielding controlled messages.

#### L2: Dockerfile quality
- **File**: `Dockerfile`
- **Problem**: Python base not pinned to patch version. No `HEALTHCHECK`. No multi-stage build. Final image includes `pip` and build tools.
- **Fix**: Pin to `python:3.13.x-slim`. Add HEALTHCHECK. Optionally adopt multi-stage build.

#### L3: Zookeeper obsolete + broken healthcheck
- **File**: `docker-compose.yml:6-18`
- **Problem**: Kafka 4.0 removed ZooKeeper entirely. Also, the healthcheck uses `CMD` form with pipe `|` — Docker passes it as literal arg to `echo`, always exits 0 regardless of ZooKeeper state.
- **Fix**: Migrate to KRaft mode. Remove Zookeeper service, volume, and dependencies.

#### L4: No graceful shutdown signal handling
- **File**: `app/kafka/consumer.py:44-72`
- **Problem**: No SIGTERM handler. On `docker compose down`, consumer hangs until the 10-second grace period expires and Docker sends SIGKILL. Unclean shutdown = uncommitted offsets.
- **Fix**: Add `signal.SIGTERM`/`signal.SIGINT` handlers with `asyncio.Event` to break the consumer loop cleanly.

#### L5: No service authentication
- **Files**: `docker-compose.yml`, `app/settings.py`
- **Problem**: `ALLOW_ANONYMOUS_LOGIN=yes` (Zookeeper), `ALLOW_PLAINTEXT_LISTENER=yes` (Kafka), no Redis password, no Kafka SASL/SSL. All traffic unencrypted and unauthenticated.
- **Fix**: Acceptable for dev. Document in README. Add auth settings when production deployment is planned.

#### L6: Shared Docker image for consumer and worker
- **File**: `Dockerfile`, `docker-compose.yml`
- **Problem**: Consumer needs `aiokafka` but not `celery`. Worker needs `celery`+`redis` but not `aiokafka`. Both install everything.
- **Fix**: No action now. If deps grow, consider separate Dockerfile targets.

---

## 4. Recommended Execution Order

| Phase | Tasks | Scope |
|---|---|---|
| **Phase 1** | H3 → M1 | Logging: replace `print()`, update tests |
| **Phase 2** | M2 | Error handling: custom exception, remove simulated failures |
| **Phase 3** | M4 | Settings: expand, validate, document |
| **Phase 4** | H1 → H2 | Producer refactor: persistent + sync for worker |
| **Phase 5** | M5 → L1 | Test coverage: producer, consume() loop |
| **Phase 6** | M3, L5 | Documentation: delivery semantics, security |
| **Phase 7** | L2, L3, L4 | Infrastructure: Kafka KRaft, Dockerfile, graceful shutdown |
| **Phase 8** | Deps + Python | Update all dependencies, upgrade to Python 3.13 |

Each phase should be a separate commit/PR for safe rollback.
