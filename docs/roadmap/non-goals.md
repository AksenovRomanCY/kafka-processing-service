# Non-Goals

These items are intentionally excluded for now.

- Do not add Kubernetes yet.
- Do not create too many services.
- Do not promise exactly-once delivery; use honest at-least-once processing with
  idempotency.
- Do not integrate real email, SMS, payment, or external KYC providers.
- Do not share internal tables between services.
- Do not turn service boundaries into a distributed monolith with synchronous
  calls for every workflow step.
- Do not add Schema Registry until Pydantic contracts and contract tests become
  insufficient.
- Do not do serious Kafka broker-count or capacity planning before realistic
  message-flow assumptions exist.
- Do not use Kafka as RPC.
- Do not put business workflows into a shared library.
