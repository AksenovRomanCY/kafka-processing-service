# Persistence

## PostgreSQL State

- Store order/application status in PostgreSQL.
- Start with one PostgreSQL instance, but keep service schemas separate.
- Avoid cross-service writes to another service's tables.
- Keep migrations in version control and run them as part of local setup.

## State Machine

Use a small explicit state machine:

```text
received
accepted
rejected
risk_pending
risk_approved
risk_rejected
completed
failed
```

Rules:

- State transitions happen in use cases.
- The owning service is responsible for validating allowed transitions.
- State transition logs should include `old_status`, `new_status`, `order_id`,
  `event_id`, and `trace_id`.

## Unit of Work

Use the Unit of Work pattern around each state-changing operation:

```text
start transaction
load current state
validate transition
write business state
insert outbox event if needed
insert processed_event if handling Kafka input
commit once
```

This keeps state changes, idempotency records, and outgoing events consistent.

## Transactional Outbox

Use an outbox table to publish Kafka events reliably after database writes.

Minimum fields:

```text
id
event_id
topic
partition_key
event_type
payload
status
attempt_count
last_error
created_at
published_at
```

Rules:

- Business use cases create complete events.
- Outbox publisher does not contain business logic.
- Publisher reads unpublished rows, publishes to Kafka, and marks rows as
  published.
- Failed publish attempts update `attempt_count` and `last_error`.
- The publisher must be safe to restart.

## Inbox / Processed Events

Use an inbox or `processed_events` table in consumers that change durable state.

Minimum fields:

```text
event_id
event_type
consumer_group
processed_at
trace_id
```

Rules:

- Check `processed_events` inside the same transaction as the state change.
- Duplicate events should return quickly, log as duplicates, and not emit new
  downstream events.
- Do not add inbox tables to read-only consumers or components that do not
  change durable state.

## HTTP Idempotency

For intake requests, deduplicate by client idempotency key plus request owner or
source. A duplicate create request should return the same public ID and current
status instead of creating another order/application.
