# Architecture Decisions

These decisions are fixed for the first practical version of the platform. They
are meant to reduce ambiguity during implementation, not to increase scope.

## 1. Event Taxonomy

Use a small set of topic families and explicit event types.

```text
orders.events.v1
  order.created.v1
  order.accepted.v1
  order.rejected.v1
  order.risk_requested.v1
  order.approved.v1
  order.failed.v1

risk.events.v1
  risk.assessment_requested.v1
  risk.assessment_completed.v1
  risk.assessment_failed.v1

notifications.events.v1
  notification.requested.v1
  notification.sent.v1
  notification.failed.v1

errors.events.v1
  event.rejected.v1
  event.failed.v1
  event.replay_requested.v1
  event.replayed.v1
```

Do not create a topic per method or per tiny internal step. Split topics later
only when retention, ownership, permissions, or throughput requirements justify
it.

## 2. Order State Machine

Keep order/application status explicit and small:

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

- Only the owning service changes its own state.
- State transitions happen inside use cases, not inside Kafka adapter code.
- Every state transition should be logged with `old_status`, `new_status`,
  `order_id`, `event_id`, and `trace_id`.

## 3. Error Policy

Route errors by category:

| Error type | Handling |
|---|---|
| Request validation error | Return HTTP 4xx; do not publish domain event |
| Event contract validation error | Publish `event.rejected.v1` to `errors.events.v1` |
| Business rule violation | Move state to `rejected` and publish domain rejection event |
| Transient infrastructure error | Retry with bounded backoff |
| Poison message | Publish to DLQ/error bus and stop retry loop |
| Unexpected bug | Publish failure event, increment alert metric, keep original event for replay |

DLQ should be a diagnostic and replay mechanism, not a trash can for every
normal business rejection.

## 4. Idempotency Placement

Apply idempotency only where duplicates can change state or create downstream
effects:

| Place | Idempotency strategy |
|---|---|
| `POST /orders` | Client idempotency key plus request owner/source |
| Intake outbox publisher | Outbox row status and retry-safe publish loop |
| Processing consumer | `processed_events` table keyed by `event_id` |
| Risk consumer | `processed_events` table keyed by `event_id` |
| Notification consumer | Optional in v1; strict idempotency is not required for mock delivery |
| Replay | `replay_id` plus `original_event_id` audit records |

Do not add idempotency tables to read-only consumers or components that do not
change durable state.

## 5. Consumer Commit Strategy

State-changing Kafka consumers should follow this order:

```text
consume event
validate envelope and payload
start DB transaction
check processed_events by event_id
apply state change
insert downstream outbox event if needed
insert processed_event
commit DB transaction
commit Kafka offset
```

If the process crashes after the DB commit but before the Kafka offset commit,
the event can be consumed again. The `processed_events` check must make that
duplicate safe.

## 6. Contract Compatibility

Allowed without a new event version:

- Add optional fields.
- Add new event types.
- Let consumers ignore unknown fields.

Requires a new event version:

- Remove a field.
- Rename a field.
- Change a field type.
- Change the business meaning of a field.
- Change requiredness of a field in a way that breaks existing consumers.

Use versioned event names such as `order.created.v1`. Keep the event envelope
stable and version payloads by event type.

## 7. Transactional Outbox Shape

Minimum outbox fields:

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

- Outbox publisher does not contain business logic.
- Business use cases create complete events.
- Publisher reads pending rows, publishes to Kafka, and marks rows as
  published.
- Failed publish attempts update `attempt_count` and `last_error`.

## 8. Replay Policy

Replay must be explicit and auditable.

- Do not delete or mutate the original DLQ record.
- Store `replay_id`, `original_event_id`, `replayed_at`, `replayed_by`,
  `target_topic`, and replay result.
- Replay can publish to the original topic or to a dedicated replay topic.
- Poison messages must not loop forever.
- Replay should be available through a command first; an admin endpoint can come
  later if it adds value.

## 9. Observability Minimum

Minimum log fields:

```text
timestamp
level
service
message
trace_id
event_id
event_type
order_id
```

Minimum metrics:

```text
events_consumed_total
events_produced_total
events_failed_total
dlq_events_total
event_processing_duration_seconds
replay_attempts_total
```

Minimum endpoints:

```text
/healthz    # process is alive
/readyz     # dependencies required for real traffic are reachable
```

Do not use high-cardinality values such as `order_id`, `event_id`, or
`trace_id` as Prometheus labels.

## 10. Service Ownership Table

| Service | Owns | Does not own |
|---|---|---|
| Intake API | HTTP contract, create request idempotency, initial order row, intake outbox | Risk scoring, notification delivery |
| Processing Service | Workflow state, orchestration, processing idempotency, final decision events | Public HTTP intake, risk formula |
| Risk Service | Risk scoring rules, risk idempotency, risk result events | Order lifecycle state machine |
| Notification Service | Mock delivery, notification logs/events | Business approval/rejection decision |

If a service needs another service's internal state, prefer consuming an event
and keeping its own projection over reading another service's tables.
