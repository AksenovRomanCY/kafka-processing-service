from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

from app.kafka.sync_producer import SyncKafkaProducer
from app.settings import settings

# ── _ensure_producer ────────────────────────────────────────────


def test_ensure_producer_creates_on_first_call():
    producer = SyncKafkaProducer()

    with patch("app.kafka.sync_producer.KafkaProducer") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        result = producer._ensure_producer()

        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["bootstrap_servers"] == settings.KAFKA_BOOTSTRAP_SERVERS
        assert callable(call_kwargs["value_serializer"])
        assert result is mock_instance


def test_ensure_producer_reuses_on_second_call():
    producer = SyncKafkaProducer()

    with patch("app.kafka.sync_producer.KafkaProducer") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        first = producer._ensure_producer()
        second = producer._ensure_producer()

        mock_cls.assert_called_once()
        assert first is second


# ── send ────────────────────────────────────────────────────────


def test_send_calls_send_and_get():
    producer = SyncKafkaProducer()
    mock_kafka = MagicMock()
    mock_future = MagicMock()
    mock_kafka.send.return_value = mock_future
    mock_future.get.return_value = MagicMock(topic="out", partition=0, offset=1)
    producer._producer = mock_kafka

    producer.send("out", {"result": 42})

    mock_kafka.send.assert_called_once_with("out", {"result": 42})
    mock_future.get.assert_called_once_with(timeout=10)


def test_send_logs_metadata(caplog):
    producer = SyncKafkaProducer()
    mock_kafka = MagicMock()
    mock_future = MagicMock()
    mock_metadata = MagicMock(topic="out-topic", partition=0, offset=5)
    mock_kafka.send.return_value = mock_future
    mock_future.get.return_value = mock_metadata
    producer._producer = mock_kafka

    with caplog.at_level(logging.INFO):
        producer.send("out-topic", {"v": 1})

    assert "Posted in Topic 'out-topic' [partition=0 offset=5]" in caplog.text


# ── close ───────────────────────────────────────────────────────


def test_close_closes_and_clears():
    producer = SyncKafkaProducer()
    mock_kafka = MagicMock()
    producer._producer = mock_kafka

    producer.close()

    mock_kafka.close.assert_called_once_with(timeout=10)
    assert producer._producer is None


def test_close_noop_when_not_initialized():
    producer = SyncKafkaProducer()

    producer.close()

    assert producer._producer is None


# ── value_serializer ────────────────────────────────────────────


def test_value_serializer_produces_valid_json():
    producer = SyncKafkaProducer()

    with patch("app.kafka.sync_producer.KafkaProducer") as mock_cls:
        mock_cls.return_value = MagicMock()

        producer._ensure_producer()

        serializer = mock_cls.call_args[1]["value_serializer"]
        assert serializer({"key": "value"}) == b'{"key": "value"}'
