# Implementation Phases

## Phase 1: Domain and Contracts

- Define the order/application domain.
- Add shared event contracts.
- Document topics, event names, and ownership.
- Keep existing Kafka/Celery flow working while introducing contracts.

Definition of done:

- Contracts are typed and unit-tested.
- Topic ownership is documented.
- At least one existing message flow uses the new envelope.

## Phase 2: Intake API and PostgreSQL

- Add FastAPI Intake API.
- Add PostgreSQL and migrations.
- Persist incoming requests and expose read endpoints.
- Add the Transactional Outbox table and publisher.

Definition of done:

- Duplicate create requests are idempotent.
- Database write and outbox insert happen in one transaction.
- Outbox publisher can be restarted safely.

## Phase 3: Processing and Risk Services

- Split processing logic into independent services.
- Add risk scoring as a separate Kafka-driven service.
- Persist state transitions.
- Add idempotency records for state-changing consumers.

Definition of done:

- Consumers can process duplicate events safely.
- Each service owns its persistence boundary.
- Workflow progress is visible through stored state and logs.

## Phase 4: DLQ, Error Bus, and Replay

- Add dedicated Kafka topics for error routing.
- Persist failure reasons and original events.
- Add replay command or admin endpoint.
- Cover poison-message behavior.

Definition of done:

- Invalid events are not lost.
- Replay attempts are auditable.
- Poison messages do not loop forever.

## Phase 5: Observability

- Add metrics, health/readiness endpoints, and trace propagation checks.
- Add optional Grafana dashboard.
- Document useful local debugging commands.

Definition of done:

- A single `trace_id` can follow a request across services.
- Prometheus exposes useful counters and durations.
- Health and readiness endpoints have different responsibilities.

## Phase 6: Integration Tests

- Add end-to-end tests after the architecture stabilizes.
- Test happy path, invalid input, DLQ routing, replay, and idempotent duplicate
  delivery.
- Prefer Docker Compose or testcontainers-based integration tests.

Definition of done:

- Tests cover the critical end-to-end flows.
- Tests can run locally with one command.
- Failures point to a service boundary or contract mismatch.
