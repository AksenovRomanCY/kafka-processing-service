# Roadmap: Event-Driven Processing Platform

## Goal

Evolve this project from a demo Kafka/Celery pipeline into a small practical
event-driven platform for processing orders, payments, or applications.

The target system accepts an incoming business request, validates it, enriches
it, calculates risk, stores the processing state, emits the result, sends a mock
notification, and routes failures to a dedicated DLQ and replay flow.

The main engineering goal is to demonstrate service boundaries, event contracts,
at-least-once processing, idempotency, observability, and failure handling
without turning the project into an oversized distributed monolith.

## Target Architecture

The platform should have 3-4 independent services:

1. **Intake API**
   - FastAPI service.
   - Accepts orders/payments/applications over HTTP.
   - Validates request shape.
   - Stores initial state in PostgreSQL.
   - Publishes a domain event through a Transactional Outbox.

2. **Processing Service**
   - Consumes validated domain events from Kafka.
   - Owns orchestration of the processing pipeline.
   - Updates processing state.
   - Emits events for risk scoring and final decisions.

3. **Risk Service**
   - Consumes risk-scoring requests from Kafka.
   - Calculates a deterministic mock risk score.
   - Publishes risk results.
   - Keeps its own idempotency records for consumed event IDs.

4. **Notification Service**
   - Consumes final decision events.
   - Sends mock notifications only.
   - Does not need strict idempotency unless duplicate notifications become a
     deliberate scenario to demonstrate.

Services should interact through Kafka events and owned data stores, not by
sharing internal database tables or calling each other for core workflow state.

## Core Capabilities

### FastAPI Entry Point

- Add `POST /orders` or `POST /applications`.
- Add `GET /orders/{id}` to inspect current processing state.
- Return a stable public ID and `trace_id`.
- Keep HTTP request handling thin: accept, validate, persist, publish intent.

### PostgreSQL State and Transactional Outbox

- Store order/application status in PostgreSQL.
- Use an outbox table to publish Kafka events reliably after database writes.
- Start with one PostgreSQL instance, but keep service schemas separate.
- Avoid cross-service writes to another service's tables.

### Kafka Contracts

- Introduce explicit event contracts with Pydantic models and JSON Schema.
- Every event should include:
  - `event_id`
  - `event_type`
  - `trace_id`
  - `occurred_at`
  - `producer`
  - `payload`
- Version contracts from the beginning, for example `order.created.v1`.

### DLQ and Replay

- Invalid or unprocessable events go to a dedicated Kafka error bus.
- Store error reason, original event, source topic, consumer group, and
  timestamp.
- Add a replay command or admin endpoint that can re-publish selected DLQ
  events after inspection.
- Keep replay explicit; do not auto-retry poison messages forever.

### Idempotency

- Use at-least-once delivery where reliable processing matters.
- Store consumed `event_id` records on the receiving side for state-changing
  handlers.
- Apply idempotency to Intake, Processing, and Risk flows.
- Do not over-engineer idempotency in the mock Notification service unless it is
  useful for a specific demo scenario.

### Observability

- Keep structured JSON logs.
- Propagate `trace_id` across HTTP, Kafka, Celery, and database records.
- Add health and readiness endpoints for services.
- Add Prometheus metrics:
  - consumed events total
  - produced events total
  - processing duration
  - DLQ events total
  - replay attempts total
- Optionally add Grafana dashboards once the core flow is stable.

## Implementation Phases

### Phase 1: Domain and Contracts

- Define the order/application domain.
- Add shared event contracts.
- Document topics, event names, and ownership.
- Keep existing Kafka/Celery flow working while introducing contracts.

### Phase 2: Intake API and PostgreSQL

- Add FastAPI Intake API.
- Add PostgreSQL and migrations.
- Persist incoming requests and expose read endpoints.
- Add the Transactional Outbox table and publisher.

### Phase 3: Processing and Risk Services

- Split processing logic into independent services.
- Add risk scoring as a separate Kafka-driven service.
- Persist state transitions.
- Add idempotency records for state-changing consumers.

### Phase 4: DLQ, Error Bus, and Replay

- Add dedicated Kafka topics for error routing.
- Persist failure reasons and original events.
- Add replay command or admin endpoint.
- Cover poison-message behavior.

### Phase 5: Observability

- Add metrics, health/readiness endpoints, and trace propagation checks.
- Add optional Grafana dashboard.
- Document useful local debugging commands.

### Phase 6: Integration Tests

- Add end-to-end tests after the architecture stabilizes.
- Test happy path, invalid input, DLQ routing, replay, and idempotent duplicate
  delivery.
- Prefer Docker Compose or testcontainers-based integration tests.

## Non-Goals for Now

- Do not add Kubernetes yet.
- Do not create too many services.
- Do not promise exactly-once delivery; use honest at-least-once processing with
  idempotency.
- Do not integrate real email, SMS, or payment providers.
- Do not share internal tables between services.
- Do not turn service boundaries into a distributed monolith with synchronous
  calls for every workflow step.
