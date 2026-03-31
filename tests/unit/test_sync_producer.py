from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest

import app.kafka.sync_producer as sync_mod
from app.settings import settings


@pytest.fixture(autouse=True)
def _reset_sync_producer_global():
    """Ensure the module-level _producer is None before and after each test."""
    sync_mod._producer = None
    yield
    sync_mod._producer = None


# ── _get_producer ───────────────────────────────────────────────


def test_get_producer_creates_on_first_call():
    with patch.object(sync_mod, "KafkaProducer") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        result = sync_mod._get_producer()

        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["bootstrap_servers"] == settings.KAFKA_BOOTSTRAP_SERVERS
        assert callable(call_kwargs["value_serializer"])
        assert result is mock_instance


def test_get_producer_returns_existing_on_second_call():
    with patch.object(sync_mod, "KafkaProducer") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        first = sync_mod._get_producer()
        second = sync_mod._get_producer()

        mock_cls.assert_called_once()
        assert first is second


# ── sync_send_to_kafka ──────────────────────────────────────────


def test_sync_send_to_kafka_calls_send_and_get():
    mock_producer = MagicMock()
    mock_future = MagicMock()
    mock_producer.send.return_value = mock_future
    mock_future.get.return_value = MagicMock(topic="out", partition=0, offset=1)
    sync_mod._producer = mock_producer

    sync_mod.sync_send_to_kafka("out", {"result": 42})

    mock_producer.send.assert_called_once_with("out", {"result": 42})
    mock_future.get.assert_called_once_with(timeout=10)


def test_sync_send_to_kafka_logs_metadata(caplog):
    mock_producer = MagicMock()
    mock_future = MagicMock()
    mock_metadata = MagicMock(topic="out-topic", partition=0, offset=5)
    mock_producer.send.return_value = mock_future
    mock_future.get.return_value = mock_metadata
    sync_mod._producer = mock_producer

    with caplog.at_level(logging.INFO):
        sync_mod.sync_send_to_kafka("out-topic", {"v": 1})

    assert "Posted in Topic 'out-topic' [partition=0 offset=5]" in caplog.text


# ── close_sync_producer ─────────────────────────────────────────


def test_close_sync_producer_closes_and_clears():
    mock_producer = MagicMock()
    sync_mod._producer = mock_producer

    sync_mod.close_sync_producer()

    mock_producer.close.assert_called_once_with(timeout=10)
    assert sync_mod._producer is None


def test_close_sync_producer_noop_when_not_initialized():
    sync_mod.close_sync_producer()

    assert sync_mod._producer is None


# ── value_serializer ────────────────────────────────────────────


def test_value_serializer_produces_valid_json():
    with patch.object(sync_mod, "KafkaProducer") as mock_cls:
        mock_cls.return_value = MagicMock()

        sync_mod._get_producer()

        serializer = mock_cls.call_args[1]["value_serializer"]
        assert serializer({"key": "value"}) == b'{"key": "value"}'
