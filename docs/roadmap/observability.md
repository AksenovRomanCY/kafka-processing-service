# Observability

## Logs

- Keep structured JSON logs.
- Propagate `trace_id` across HTTP, Kafka, Celery, and database records.
- Log state transitions as first-class events.

Minimum fields:

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

## Tracing Context

- Add request middleware in FastAPI to create or accept `trace_id`.
- Add Kafka producer/consumer helpers that copy `trace_id` into event envelopes.
- Use `trace_id` for correlation only. Do not use it for deduplication.

## Metrics

Add Prometheus metrics:

```text
events_consumed_total
events_produced_total
events_failed_total
dlq_events_total
event_processing_duration_seconds
replay_attempts_total
```

Keep metric labels low-cardinality. Do not use `order_id`, `event_id`, or
`trace_id` as labels.

## Health and Readiness

Expose:

```text
/healthz    # process is alive
/readyz     # dependencies required for real traffic are reachable
```

Readiness should check dependencies needed to serve real traffic. Liveness
should only prove the process is alive.

## Grafana

Grafana dashboards are optional and should come only after the core flow,
metrics, and integration tests are stable.
