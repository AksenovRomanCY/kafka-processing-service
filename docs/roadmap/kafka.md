# Kafka

## Event Contracts

- Introduce explicit event contracts with Pydantic models and JSON Schema.
- Use an event envelope plus typed payloads. The envelope stays stable while
  payloads evolve per event type.
- Every event should include:
  - `event_id`
  - `event_type`
  - `trace_id`
  - `occurred_at`
  - `producer`
  - `payload`
- Version contracts from the beginning, for example `order.created.v1`.
- Use `event_id` as the idempotency key for consumers.
- Use `trace_id` for observability, not for deduplication.
- Treat Kafka producers and consumers as adapters. Business logic should receive
  validated models, not raw Kafka records.

## Topic Strategy

Start with a small set of topic families:

```text
orders.events.v1
risk.events.v1
notifications.events.v1
errors.events.v1
```

Use `event_type` inside the envelope to distinguish events. Create more topics
only when a topic needs different ownership, retention, permissions, or
throughput characteristics.

## Partition Key

Use a stable business key such as `order_id` as the Kafka record key.

Do not use `event_id` as the partition key for order-related events. That would
scatter events for the same order across partitions and lose per-order ordering.

## Kafka Topology

- Keep local development on a single Kafka broker.
- Use explicit topic creation; do not rely on auto-created topics.
- Keep local topics simple:
  - `partitions=3`;
  - `replication.factor=1`;
  - `auto.create.topics.enable=false`.
- Do not do serious broker-count or capacity planning yet. There is no real
  throughput, retention, SLA, or high-availability requirement to size against.
- Design the application so it does not depend on single-broker assumptions.

Future production-like profile:

```text
brokers=3
replication.factor=3
min.insync.replicas=2
producer acks=all
producer idempotence enabled where the client supports it
```

Revisit broker count, partition count, retention, and replication only after
integration tests and realistic message-flow assumptions exist.

## Consumer Commit Strategy

State-changing consumers should commit Kafka offsets only after durable local
state changes are committed:

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

This gives at-least-once delivery with idempotent consumers. Do not promise
exactly-once delivery.

## DLQ and Replay

- Invalid or unprocessable events go to a dedicated Kafka error bus.
- Store error reason, original event, source topic, partition, offset, consumer
  group, and timestamp.
- Separate retryable errors from poison messages:
  - retry transient infrastructure failures with bounded backoff;
  - send validation and invariant failures to DLQ.
- Preserve the original `event_id` and `trace_id` in DLQ records.
- Add replay metadata such as `replay_id`, `replayed_at`, and `replayed_by`.
- On replay, publish the original event back to the source topic or a dedicated
  replay topic, depending on the consumer group being tested.
- Never delete DLQ records automatically during replay; mark the replay attempt
  and outcome instead.

Minimum DLQ payload:

```text
error_id
original_event_id
trace_id
source_topic
source_partition
source_offset
consumer_group
error_type
error_message
original_event
created_at
```
