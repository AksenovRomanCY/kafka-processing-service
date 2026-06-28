from __future__ import annotations

import asyncio
import json
import logging
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.kafka.consumer import _heartbeat_loop, consume, handle_message
from app.settings import settings

# ── helpers ──────────────────────────────────────────────────────


class _LoopProxy:
    """Wraps the real event loop, intercepting add_signal_handler for tests."""

    def __init__(self, real_loop, callbacks=None):
        self._real_loop = real_loop
        self.signal_callbacks = callbacks if callbacks is not None else {}

    def add_signal_handler(self, sig, callback, *args):
        self.signal_callbacks[sig] = callback

    def __getattr__(self, name):
        return getattr(self._real_loop, name)


class MockConsumer:
    """Fake AIOKafkaConsumer that yields predefined messages via async for."""

    def __init__(self, messages):
        self._messages = iter(messages)
        self.start = AsyncMock()
        self.stop = AsyncMock()
        self.commit = AsyncMock()

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._messages)
        except StopIteration:
            raise StopAsyncIteration


def _make_msg(value: str) -> MagicMock:
    msg = MagicMock()
    msg.value = value
    return msg


def _loop_proxy(callbacks=None):
    """Create a patch for asyncio.get_running_loop returning a _LoopProxy."""
    loop = asyncio.get_running_loop()
    return patch("asyncio.get_running_loop", return_value=_LoopProxy(loop, callbacks))


@pytest.fixture
def mock_producer():
    """Mock AsyncKafkaProducer for handle_message tests."""
    producer = AsyncMock()
    producer.send = AsyncMock()
    return producer


def _noop_heartbeat():
    """Patch _heartbeat_loop to a no-op so consume tests don't touch the filesystem."""

    async def noop(stop_event, path=None, interval_seconds=20):  # type: ignore[assignment]
        await stop_event.wait()

    return patch("app.kafka.consumer._heartbeat_loop", side_effect=noop)


def _mock_producer_class():
    """Patch AsyncKafkaProducer to return a mock with start/stop/send."""
    mock_instance = AsyncMock()
    mock_instance.start = AsyncMock()
    mock_instance.stop = AsyncMock()
    mock_instance.send = AsyncMock()
    mock_cls = MagicMock(return_value=mock_instance)
    return patch("app.kafka.consumer.AsyncKafkaProducer", mock_cls), mock_instance


# ── handle_message() ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_handle_message_passes_trace_id_to_chain(monkeypatch, mock_producer):
    """handle_message generates a trace_id and passes it to all tasks in the chain."""
    mock_chain_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.id = "chain-id"
    mock_chain_instance.apply_async.return_value = mock_result

    mock_chain_fn = MagicMock(return_value=mock_chain_instance)
    monkeypatch.setattr("app.kafka.consumer.chain", mock_chain_fn)

    fixed_uuid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
    monkeypatch.setattr("app.kafka.consumer.uuid.uuid4", lambda: fixed_uuid)

    await handle_message(json.dumps({"value": 42}), mock_producer)

    args = mock_chain_fn.call_args[0]
    for sig in args:
        assert sig.kwargs.get("trace_id") == fixed_uuid


@pytest.mark.asyncio
async def test_handle_message_passes_demo_failure_to_chain(monkeypatch, mock_producer):
    """handle_message passes optional demo failure flag to all tasks."""
    mock_chain_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.id = "chain-id"
    mock_chain_instance.apply_async.return_value = mock_result

    mock_chain_fn = MagicMock(return_value=mock_chain_instance)
    monkeypatch.setattr("app.kafka.consumer.chain", mock_chain_fn)

    await handle_message(json.dumps({"value": 42, "fail": "task_2"}), mock_producer)

    args = mock_chain_fn.call_args[0]
    for sig in args:
        assert sig.kwargs.get("fail") == "task_2"


@pytest.mark.asyncio
async def test_handle_message_includes_trace_id_in_logs(
    monkeypatch, mock_producer, caplog
):
    """Log records from handle_message carry trace_id in extra fields."""
    mock_chain_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.id = "chain-id"
    mock_chain_instance.apply_async.return_value = mock_result
    mock_chain_fn = MagicMock(return_value=mock_chain_instance)
    monkeypatch.setattr("app.kafka.consumer.chain", mock_chain_fn)

    with caplog.at_level(logging.INFO):
        await handle_message(json.dumps({"value": 42}), mock_producer)

    traced = [r for r in caplog.records if hasattr(r, "trace_id")]
    assert len(traced) >= 2
    trace_ids = {r.trace_id for r in traced}
    assert len(trace_ids) == 1
    assert len(trace_ids.pop()) == 36


@pytest.mark.asyncio
async def test_handle_message_error_includes_trace_id(mock_producer, caplog):
    """Error path includes trace_id in the Kafka error message."""
    with caplog.at_level(logging.ERROR):
        await handle_message("not-json", mock_producer)

    sent_call = mock_producer.send.call_args
    assert sent_call[1]["data"]["trace_id"]
    assert len(sent_call[1]["data"]["trace_id"]) == 36


@pytest.mark.asyncio
async def test_handle_message_valid(monkeypatch, mock_producer, caplog):
    mock_chain_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.id = "chain-id"
    mock_chain_instance.apply_async.return_value = mock_result

    mock_chain_fn = MagicMock(return_value=mock_chain_instance)
    monkeypatch.setattr("app.kafka.consumer.chain", mock_chain_fn)

    with caplog.at_level(logging.INFO):
        await handle_message(json.dumps({"value": 42}), mock_producer)

    assert "Valid value: 42" in caplog.text
    assert "Celery chain started with ID: chain-id" in caplog.text
    mock_chain_fn.assert_called_once()
    mock_chain_instance.apply_async.assert_called_once()


@pytest.mark.asyncio
async def test_handle_message_invalid(mock_producer, caplog):
    bad = "not-a-json"
    with caplog.at_level(logging.ERROR):
        await handle_message(bad, mock_producer)

    assert "Invalid message: not-a-json" in caplog.text
    mock_producer.send.assert_awaited_once()
    call_kwargs = mock_producer.send.call_args[1]
    assert call_kwargs["topic"] == settings.KAFKA_ERROR_TOPIC
    assert call_kwargs["data"]["error"] == bad
    assert "trace_id" in call_kwargs["data"]


@pytest.mark.asyncio
async def test_handle_message_missing_value(mock_producer, caplog):
    """If there is no 'value' field in JSON, or it is None - error and send to error."""
    with caplog.at_level(logging.ERROR):
        await handle_message(json.dumps({}), mock_producer)
    assert "Invalid message" in caplog.text
    call_kwargs = mock_producer.send.call_args[1]
    assert call_kwargs["topic"] == settings.KAFKA_ERROR_TOPIC
    assert call_kwargs["data"]["error"] == "{}"
    assert "trace_id" in call_kwargs["data"]

    mock_producer.send.reset_mock()
    caplog.clear()
    with caplog.at_level(logging.ERROR):
        await handle_message(json.dumps({"value": None}), mock_producer)
    assert "Invalid message" in caplog.text
    call_kwargs = mock_producer.send.call_args[1]
    assert call_kwargs["data"]["error"] == '{"value": null}'
    assert "trace_id" in call_kwargs["data"]


@pytest.mark.asyncio
async def test_handle_message_non_numeric_value(mock_producer, caplog):
    """If the 'value' field is not a number - also an error."""
    bad = json.dumps({"value": "foo"})
    with caplog.at_level(logging.ERROR):
        await handle_message(bad, mock_producer)
    assert "Invalid message" in caplog.text
    call_kwargs = mock_producer.send.call_args[1]
    assert call_kwargs["data"]["error"] == bad
    assert "trace_id" in call_kwargs["data"]


@pytest.mark.asyncio
async def test_handle_message_unknown_fail_flag_goes_to_error(mock_producer, caplog):
    """Unknown demo failure flags are treated as invalid messages."""
    bad = json.dumps({"value": 10, "fail": "unknown_task"})
    with caplog.at_level(logging.ERROR):
        await handle_message(bad, mock_producer)

    assert "The 'fail' field must be one of" in caplog.text
    call_kwargs = mock_producer.send.call_args[1]
    assert call_kwargs["topic"] == settings.KAFKA_ERROR_TOPIC
    assert call_kwargs["data"]["error"] == bad
    assert "trace_id" in call_kwargs["data"]


@pytest.mark.asyncio
async def test_handle_message_float_and_negative(monkeypatch, mock_producer, caplog):
    """Correct float and negative numbers are valid and dispatch a chain."""
    mock_chain_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.id = "chain-id"
    mock_chain_instance.apply_async.return_value = mock_result

    mock_chain_fn = MagicMock(return_value=mock_chain_instance)
    monkeypatch.setattr("app.kafka.consumer.chain", mock_chain_fn)

    for val in [3.14, -1000.5]:
        caplog.clear()
        mock_chain_fn.reset_mock()
        with caplog.at_level(logging.INFO):
            await handle_message(json.dumps({"value": val}), mock_producer)
        assert f"Valid value: {val}" in caplog.text
        assert "Celery chain started with ID: chain-id" in caplog.text
        mock_chain_fn.assert_called_once()


# ── _heartbeat_loop() ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_heartbeat_loop_touches_file(tmp_path):
    """Heartbeat creates and touches the liveness file."""
    liveness = tmp_path / "consumer-alive"
    stop_event = asyncio.Event()

    task = asyncio.create_task(
        _heartbeat_loop(stop_event, path=liveness, interval_seconds=0.05)
    )
    await asyncio.sleep(0.1)
    stop_event.set()
    await task

    assert liveness.exists()


@pytest.mark.asyncio
async def test_heartbeat_loop_stops_on_event(tmp_path):
    """Heartbeat exits promptly when stop_event is set."""
    liveness = tmp_path / "consumer-alive"
    stop_event = asyncio.Event()
    stop_event.set()

    task = asyncio.create_task(
        _heartbeat_loop(stop_event, path=liveness, interval_seconds=60)
    )
    await asyncio.wait_for(task, timeout=1.0)


@pytest.mark.asyncio
async def test_heartbeat_loop_updates_mtime(tmp_path):
    """Heartbeat updates the file mtime across iterations."""
    liveness = tmp_path / "consumer-alive"
    stop_event = asyncio.Event()

    task = asyncio.create_task(
        _heartbeat_loop(stop_event, path=liveness, interval_seconds=0.05)
    )
    await asyncio.sleep(0.08)
    first_mtime = liveness.stat().st_mtime
    await asyncio.sleep(0.08)
    second_mtime = liveness.stat().st_mtime
    stop_event.set()
    await task

    assert second_mtime >= first_mtime


# ── consume() ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_consume_processes_messages_and_commits():
    msgs = [_make_msg('{"value": 1}'), _make_msg('{"value": 2}')]
    consumer_mock = MockConsumer(msgs)
    prod_patch, prod_mock = _mock_producer_class()

    with (
        _loop_proxy(),
        prod_patch,
        _noop_heartbeat(),
        patch("app.kafka.consumer.AIOKafkaConsumer", return_value=consumer_mock),
        patch("app.kafka.consumer.handle_message", new_callable=AsyncMock) as hm,
    ):
        await consume()

        assert hm.await_count == 2
        hm.assert_any_await('{"value": 1}', prod_mock)
        hm.assert_any_await('{"value": 2}', prod_mock)
        assert consumer_mock.commit.await_count == 2


@pytest.mark.asyncio
async def test_consume_calls_stop_on_normal_exit():
    consumer_mock = MockConsumer([_make_msg('{"value": 1}')])
    prod_patch, prod_mock = _mock_producer_class()

    with (
        _loop_proxy(),
        prod_patch,
        _noop_heartbeat(),
        patch("app.kafka.consumer.AIOKafkaConsumer", return_value=consumer_mock),
        patch("app.kafka.consumer.handle_message", new_callable=AsyncMock),
    ):
        await consume()

        consumer_mock.stop.assert_awaited_once()
        prod_mock.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_consume_calls_stop_on_exception():
    consumer_mock = MockConsumer([_make_msg('{"value": 1}')])
    prod_patch, prod_mock = _mock_producer_class()

    with (
        _loop_proxy(),
        prod_patch,
        _noop_heartbeat(),
        patch("app.kafka.consumer.AIOKafkaConsumer", return_value=consumer_mock),
        patch(
            "app.kafka.consumer.handle_message",
            new_callable=AsyncMock,
            side_effect=RuntimeError("boom"),
        ),
    ):
        with pytest.raises(RuntimeError, match="boom"):
            await consume()

        consumer_mock.stop.assert_awaited_once()
        prod_mock.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_consume_starts_producer_before_consumer():
    consumer_mock = MockConsumer([])
    order: list[str] = []

    mock_prod_instance = AsyncMock()

    async def track_start():
        order.append("producer.start")

    async def track_consumer_start():
        order.append("consumer.start")

    mock_prod_instance.start = AsyncMock(side_effect=track_start)
    mock_prod_instance.stop = AsyncMock()
    mock_prod_cls = MagicMock(return_value=mock_prod_instance)
    consumer_mock.start = AsyncMock(side_effect=track_consumer_start)

    with (
        _loop_proxy(),
        patch("app.kafka.consumer.AsyncKafkaProducer", mock_prod_cls),
        _noop_heartbeat(),
        patch("app.kafka.consumer.AIOKafkaConsumer", return_value=consumer_mock),
        patch("app.kafka.consumer.handle_message", new_callable=AsyncMock),
    ):
        await consume()

    assert order == ["producer.start", "consumer.start"]


@pytest.mark.asyncio
async def test_consume_creates_consumer_with_correct_settings():
    consumer_mock = MockConsumer([])
    prod_patch, _ = _mock_producer_class()

    with (
        _loop_proxy(),
        prod_patch,
        _noop_heartbeat(),
        patch(
            "app.kafka.consumer.AIOKafkaConsumer", return_value=consumer_mock
        ) as cons_cls,
        patch("app.kafka.consumer.handle_message", new_callable=AsyncMock),
    ):
        await consume()

        cons_cls.assert_called_once()
        args, kwargs = cons_cls.call_args
        assert args[0] == settings.KAFKA_INPUT_TOPIC
        assert kwargs["bootstrap_servers"] == settings.KAFKA_BOOTSTRAP_SERVERS
        assert kwargs["auto_offset_reset"] == "earliest"
        assert kwargs["enable_auto_commit"] is False
        assert kwargs["group_id"] == settings.KAFKA_GROUP_ID


# ── graceful shutdown ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_consume_registers_signal_handlers():
    """Both SIGTERM and SIGINT handlers are registered on startup."""
    consumer_mock = MockConsumer([])
    callbacks = {}
    prod_patch, _ = _mock_producer_class()

    with (
        _loop_proxy(callbacks),
        prod_patch,
        _noop_heartbeat(),
        patch("app.kafka.consumer.AIOKafkaConsumer", return_value=consumer_mock),
        patch("app.kafka.consumer.handle_message", new_callable=AsyncMock),
    ):
        await consume()

    assert signal.SIGTERM in callbacks
    assert signal.SIGINT in callbacks


@pytest.mark.asyncio
async def test_consume_stops_on_shutdown_signal():
    """Consumer breaks out of the loop when a shutdown signal fires."""
    msgs = [_make_msg('{"value": 1}'), _make_msg('{"value": 2}')]
    consumer_mock = MockConsumer(msgs)
    callbacks = {}
    prod_patch, _ = _mock_producer_class()

    call_count = 0

    async def handle_then_signal(raw_value, producer):
        nonlocal call_count
        call_count += 1
        callbacks[signal.SIGTERM]()

    with (
        _loop_proxy(callbacks),
        prod_patch,
        _noop_heartbeat(),
        patch("app.kafka.consumer.AIOKafkaConsumer", return_value=consumer_mock),
        patch(
            "app.kafka.consumer.handle_message",
            new_callable=AsyncMock,
            side_effect=handle_then_signal,
        ),
    ):
        await consume()

    assert call_count == 1
    consumer_mock.stop.assert_awaited_once()


@pytest.mark.asyncio
async def test_consume_logs_clean_shutdown(caplog):
    """Consumer logs a clean shutdown message on exit."""
    consumer_mock = MockConsumer([])
    prod_patch, _ = _mock_producer_class()

    with (
        _loop_proxy(),
        prod_patch,
        _noop_heartbeat(),
        patch("app.kafka.consumer.AIOKafkaConsumer", return_value=consumer_mock),
        patch("app.kafka.consumer.handle_message", new_callable=AsyncMock),
    ):
        with caplog.at_level(logging.INFO):
            await consume()

    assert "Consumer shut down cleanly" in caplog.text
