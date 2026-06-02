# Overview

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

## Design Rules

- Prefer event-driven collaboration over synchronous service-to-service calls.
- Each service owns its write model and database schema.
- Shared code is limited to contracts, logging, tracing, and small technical
  helpers. Do not share business workflows through a common library.
- Keep service internals replaceable: HTTP handlers, Kafka consumers, database
  repositories, and producers are adapters around use-case functions.
- Use explicit state transitions instead of hidden side effects.
- Make retry and replay behavior visible in data, logs, and metrics.
- Optimize for understandable local development before production-style
  platform tooling.

## Service Boundaries

| Service | Owns | Does not own |
|---|---|---|
| Intake API | HTTP intake, initial validation, public request status, order creation | Risk scoring, workflow orchestration |
| Processing Service | Workflow state transitions, orchestration, final decision events | HTTP intake, risk formula, notification delivery |
| Risk Service | Risk rules, deterministic score calculation, risk result events | Order lifecycle, public status API |
| Notification Service | Mock notification delivery and notification result events | Business decisions, real email/SMS delivery |

## FastAPI Entry Point

- Add `POST /orders` or `POST /applications`.
- Add `GET /orders/{id}` to inspect current processing state.
- Return a stable public ID and `trace_id`.
- Keep HTTP request handling thin: accept, validate, persist, publish intent.
- Use a controller/use-case/repository split:
  - FastAPI route: HTTP parsing and response mapping only.
  - Use case: business decision and state transition.
  - Repository: PostgreSQL access.
- Return `202 Accepted` for asynchronous processing, with a response containing
  the public ID, current status, and `trace_id`.
- Support an idempotency key on create requests so repeated HTTP submissions can
  return the same public ID instead of creating duplicates.

## Recommended Internal Structure

Each service should follow the same lightweight shape:

```text
service/
  api/          # FastAPI routes, request/response schemas
  consumers/    # Kafka consumer entrypoints
  producers/    # Kafka producer adapters
  domain/       # domain models, state transitions, business rules
  use_cases/    # application use cases
  persistence/  # repositories, Unit of Work, migrations
  settings.py
```

This is not strict Clean Architecture ceremony. It is a practical way to keep
I/O code at the edges and business behavior easy to test.
