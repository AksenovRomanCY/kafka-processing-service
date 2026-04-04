from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest

from app.kafka.producer import AsyncKafkaProducer
from app.settings import settings

# Save before conftest autouse fixture patches the class method
_original_send = AsyncKafkaProducer.send


@pytest.fixture(autouse=True)
def _restore_producer_send(monkeypatch):
    """Undo the conftest autouse patch so these tests exercise real send logic."""
    monkeypatch.setattr(AsyncKafkaProducer, "send", _original_send)


# ── start ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_start_creates_and_starts_underlying_producer():
    producer = AsyncKafkaProducer()

    with patch("app.kafka.producer._AIOKafkaProducer") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value = mock_instance

        await producer.start()

        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args[1]
        assert call_kwargs["bootstrap_servers"] == settings.KAFKA_BOOTSTRAP_SERVERS
        assert callable(call_kwargs["value_serializer"])
        mock_instance.start.assert_awaited_once()
        assert producer._producer is mock_instance


@pytest.mark.asyncio
async def test_start_raises_if_already_running():
    producer = AsyncKafkaProducer()
    producer._producer = AsyncMock()

    with pytest.raises(RuntimeError, match="already running"):
        await producer.start()


# ── stop ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stop_stops_and_clears():
    producer = AsyncKafkaProducer()
    mock = AsyncMock()
    producer._producer = mock

    await producer.stop()

    mock.stop.assert_awaited_once()
    assert producer._producer is None


@pytest.mark.asyncio
async def test_stop_noop_when_not_running():
    producer = AsyncKafkaProducer()

    await producer.stop()

    assert producer._producer is None


# ── send ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_send_calls_send_and_wait():
    producer = AsyncKafkaProducer()
    mock = AsyncMock()
    producer._producer = mock

    await producer.send("test-topic", {"key": "val"})

    mock.send_and_wait.assert_awaited_once_with("test-topic", {"key": "val"})


@pytest.mark.asyncio
async def test_send_raises_if_not_started():
    producer = AsyncKafkaProducer()

    with pytest.raises(RuntimeError, match="not running"):
        await producer.send("topic", {"data": 1})


@pytest.mark.asyncio
async def test_send_logs_topic_and_data(caplog):
    producer = AsyncKafkaProducer()
    producer._producer = AsyncMock()

    with caplog.at_level(logging.INFO):
        await producer.send("my-topic", {"a": 1})

    assert "Posted in Topic 'my-topic'" in caplog.text
    assert "{'a': 1}" in caplog.text


# ── value_serializer ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_value_serializer_produces_valid_json():
    producer = AsyncKafkaProducer()

    with patch("app.kafka.producer._AIOKafkaProducer") as mock_cls:
        mock_cls.return_value = AsyncMock()

        await producer.start()

        serializer = mock_cls.call_args[1]["value_serializer"]
        assert serializer({"key": "value"}) == b'{"key": "value"}'
