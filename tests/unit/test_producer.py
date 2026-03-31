from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest

import app.kafka.producer as producer_mod
from app.kafka.producer import send_to_kafka, start_producer, stop_producer
from app.settings import settings


@pytest.fixture(autouse=True)
def _reset_producer_global():
    """Ensure the module-level _producer is None before and after each test."""
    producer_mod._producer = None
    yield
    producer_mod._producer = None


# ── start_producer ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_producer_creates_and_starts():
    with patch.object(producer_mod, "AIOKafkaProducer") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value = mock_instance

        await start_producer()

        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["bootstrap_servers"] == settings.KAFKA_BOOTSTRAP_SERVERS
        assert callable(call_kwargs["value_serializer"])
        mock_instance.start.assert_awaited_once()
        assert producer_mod._producer is mock_instance


@pytest.mark.asyncio
async def test_start_producer_raises_if_already_running():
    producer_mod._producer = AsyncMock()

    with pytest.raises(RuntimeError, match="already running"):
        await start_producer()


# ── stop_producer ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stop_producer_stops_and_clears():
    mock_producer = AsyncMock()
    producer_mod._producer = mock_producer

    await stop_producer()

    mock_producer.stop.assert_awaited_once()
    assert producer_mod._producer is None


@pytest.mark.asyncio
async def test_stop_producer_noop_when_not_running():
    await stop_producer()

    assert producer_mod._producer is None


# ── send_to_kafka ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_to_kafka_calls_send_and_wait():
    mock_producer = AsyncMock()
    producer_mod._producer = mock_producer

    await send_to_kafka("test-topic", {"key": "val"})

    mock_producer.send_and_wait.assert_awaited_once_with("test-topic", {"key": "val"})


@pytest.mark.asyncio
async def test_send_to_kafka_raises_if_not_started():
    with pytest.raises(RuntimeError, match="not running"):
        await send_to_kafka("topic", {"data": 1})


@pytest.mark.asyncio
async def test_send_to_kafka_logs_topic_and_data(caplog):
    mock_producer = AsyncMock()
    producer_mod._producer = mock_producer

    with caplog.at_level(logging.INFO):
        await send_to_kafka("my-topic", {"a": 1})

    assert "Posted in Topic 'my-topic'" in caplog.text
    assert "{'a': 1}" in caplog.text


# ── value_serializer ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_value_serializer_produces_valid_json():
    with patch.object(producer_mod, "AIOKafkaProducer") as mock_cls:
        mock_cls.return_value = AsyncMock()

        await start_producer()

        serializer = mock_cls.call_args[1]["value_serializer"]
        assert serializer({"key": "value"}) == b'{"key": "value"}'
