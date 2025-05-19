#!/bin/bash
set -e

echo "📦 Loading .env"
export $(grep -v '^#' /opt/config/.env | xargs)

TOPICS=("$KAFKA_INPUT_TOPIC" "$KAFKA_OUTPUT_TOPIC" "$KAFKA_ERROR_TOPIC")

for TOPIC in "${TOPICS[@]}"; do
  echo "🔧 Creating topic: $TOPIC"
  kafka-topics.sh \
    --bootstrap-server "${BOOTSTRAP_SERVER:-kafka:9092}" \
    --create \
    --if-not-exists \
    --topic "$TOPIC" \
    --partitions 3 \
    --replication-factor 1
done

echo "✅ All topics created."
