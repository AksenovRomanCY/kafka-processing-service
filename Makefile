SHELL := /bin/bash

DC ?= docker compose
KAFKA_BIN := /opt/kafka/bin
KAFKA_BOOTSTRAP ?= localhost:9092

.PHONY: help test lint format-check typecheck ci build up down down-clean restart ps logs \
	topics send-valid send-invalid send-dlq-demo read-output read-error read-dlq \
	logs-trace demo smoke

help:
	@echo "Development:"
	@echo "  make test          Run unit tests"
	@echo "  make lint          Run Ruff lint checks"
	@echo "  make format-check  Check formatting"
	@echo "  make typecheck     Run mypy"
	@echo "  make ci            Run lint, format-check, typecheck, and tests"
	@echo ""
	@echo "Docker Compose:"
	@echo "  make build         Build service images"
	@echo "  make up            Start the full stack"
	@echo "  make down          Stop the stack"
	@echo "  make down-clean    Stop the stack and remove volumes"
	@echo "  make restart       Restart the stack"
	@echo "  make ps            Show service status"
	@echo "  make logs          Follow service logs"
	@echo ""
	@echo "Demo:"
	@echo "  make topics        List Kafka topics"
	@echo "  make send-valid    Send a valid input message"
	@echo "  make send-invalid  Send an invalid input message"
	@echo "  make send-dlq-demo Send a message that fails task_2 and reaches DLQ"
	@echo "  make read-output   Read from the output topic"
	@echo "  make read-error    Read from the error topic"
	@echo "  make read-dlq      Read from the dead-letter topic"
	@echo "  make logs-trace TRACE_ID=<id>"
	@echo "  make demo          Run the scripted showcase"
	@echo "  make smoke         Verify valid and invalid paths on a running stack"

test:
	poetry run pytest

lint:
	poetry run ruff check .

format-check:
	poetry run ruff format --check .

typecheck:
	poetry run mypy app/

ci: lint format-check typecheck test

build:
	$(DC) build

up:
	$(DC) up -d --build

down:
	$(DC) down

down-clean:
	$(DC) down -v

restart: down up

ps:
	$(DC) ps

logs:
	$(DC) logs -f

topics:
	$(DC) exec -T kafka $(KAFKA_BIN)/kafka-topics.sh \
		--bootstrap-server $(KAFKA_BOOTSTRAP) \
		--list

send-valid:
	printf '%s\n' '{"value":10}' | $(DC) exec -T kafka $(KAFKA_BIN)/kafka-console-producer.sh \
		--bootstrap-server $(KAFKA_BOOTSTRAP) \
		--topic input

send-invalid:
	printf '%s\n' '{"foo":"bar"}' 'not-json' | $(DC) exec -T kafka $(KAFKA_BIN)/kafka-console-producer.sh \
		--bootstrap-server $(KAFKA_BOOTSTRAP) \
		--topic input

send-dlq-demo:
	printf '%s\n' '{"value":10,"fail":"task_2"}' | $(DC) exec -T kafka $(KAFKA_BIN)/kafka-console-producer.sh \
		--bootstrap-server $(KAFKA_BOOTSTRAP) \
		--topic input

read-output:
	-$(DC) exec -T kafka $(KAFKA_BIN)/kafka-console-consumer.sh \
		--bootstrap-server $(KAFKA_BOOTSTRAP) \
		--topic output \
		--from-beginning \
		--timeout-ms 10000

read-error:
	-$(DC) exec -T kafka $(KAFKA_BIN)/kafka-console-consumer.sh \
		--bootstrap-server $(KAFKA_BOOTSTRAP) \
		--topic error \
		--from-beginning \
		--timeout-ms 10000

read-dlq:
	-$(DC) exec -T kafka $(KAFKA_BIN)/kafka-console-consumer.sh \
		--bootstrap-server $(KAFKA_BOOTSTRAP) \
		--topic dead-letter \
		--from-beginning \
		--timeout-ms 15000

logs-trace:
	@test -n "$(TRACE_ID)" || (echo "Usage: make logs-trace TRACE_ID=<trace_id>"; exit 1)
	$(DC) logs | grep "$(TRACE_ID)"

demo:
	@echo "==> Starting stack"
	@$(MAKE) up
	@echo "==> Waiting for services"
	@sleep 10
	@$(MAKE) ps
	@echo "==> Sending valid message"
	@$(MAKE) send-valid
	@echo "==> Reading output topic"
	@$(MAKE) read-output
	@echo "==> Sending invalid messages"
	@$(MAKE) send-invalid
	@echo "==> Reading error topic"
	@$(MAKE) read-error
	@echo "==> Sending DLQ demo message"
	@$(MAKE) send-dlq-demo
	@echo "==> Waiting for Celery retries to exhaust"
	@sleep 15
	@echo "==> Reading dead-letter topic"
	@$(MAKE) read-dlq
	@echo "==> Pick a trace_id above and run: make logs-trace TRACE_ID=<trace_id>"

smoke:
	./scripts/smoke.sh
