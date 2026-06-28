#!/usr/bin/env bash
set -euo pipefail

DC="${DC:-docker compose}"
KAFKA_BIN="/opt/kafka/bin"
KAFKA_BOOTSTRAP="${KAFKA_BOOTSTRAP:-localhost:9092}"

require_healthy() {
  local service="$1"

  if ! ${DC} ps "${service}" | grep -q "(healthy)"; then
    echo "Service '${service}' is not healthy. Run 'make up' first." >&2
    ${DC} ps >&2
    exit 1
  fi
}

send_input() {
  local payload="$1"

  printf '%s\n' "${payload}" | ${DC} exec -T kafka \
    "${KAFKA_BIN}/kafka-console-producer.sh" \
    --bootstrap-server "${KAFKA_BOOTSTRAP}" \
    --topic input
}

read_topic() {
  local topic="$1"
  local timeout_ms="${2:-10000}"

  ${DC} exec -T kafka "${KAFKA_BIN}/kafka-console-consumer.sh" \
    --bootstrap-server "${KAFKA_BOOTSTRAP}" \
    --topic "${topic}" \
    --from-beginning \
    --timeout-ms "${timeout_ms}" 2>/dev/null || true
}

require_healthy kafka
require_healthy redis
require_healthy consumer
require_healthy worker

token="smoke-$(date +%s)-$$"
value="$(date +%s)"
expected_result=$((value - 900))
valid_payload="{\"value\":${value}}"
invalid_payload="{\"foo\":\"${token}\"}"

echo "Sending valid payload: ${valid_payload}"
send_input "${valid_payload}"
sleep 5

output_messages="$(read_topic output 10000)"
echo "${output_messages}"
if ! grep -Fq "\"result\": ${expected_result}" <<<"${output_messages}"; then
  echo "Expected result ${expected_result} was not found in output topic." >&2
  exit 1
fi

echo "Sending invalid payload: ${invalid_payload}"
send_input "${invalid_payload}"
sleep 3

error_messages="$(read_topic error 10000)"
echo "${error_messages}"
if ! grep -Fq "${token}" <<<"${error_messages}"; then
  echo "Expected invalid payload token '${token}' was not found in error topic." >&2
  exit 1
fi

echo "Smoke test passed."
