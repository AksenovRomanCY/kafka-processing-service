# Roadmap: Event-Driven Processing Platform

This roadmap is split into focused documents so implementation agents can load
only the context they need.

## Start Here

- [Overview](roadmap/overview.md) - product goal, target architecture, service
  boundaries, and internal service shape.
- [Architecture Decisions](roadmap/architecture-decisions.md) - fixed decisions
  that should guide implementation.
- [Kafka](roadmap/kafka.md) - event contracts, topic strategy, topology, commit
  strategy, DLQ, and replay.
- [Persistence](roadmap/persistence.md) - PostgreSQL state, Transactional
  Outbox, idempotency, and minimal table shapes.
- [Observability](roadmap/observability.md) - logs, tracing, metrics, health,
  and readiness.
- [Implementation Phases](roadmap/phases.md) - staged rollout with definitions
  of done.
- [Non-Goals](roadmap/non-goals.md) - things intentionally excluded for now.

## Current Direction

Evolve the project from a demo Kafka/Celery pipeline into a small practical
event-driven platform for processing orders, payments, or applications.

The platform should demonstrate service boundaries, Kafka contracts,
at-least-once processing, idempotency, Transactional Outbox, DLQ/replay,
observability, and integration testing without pretending to be a full
production platform from day one.
