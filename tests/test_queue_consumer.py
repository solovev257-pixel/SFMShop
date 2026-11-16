"""Подтверждение сообщений, повторы и очередь ошибок без RabbitMQ и MongoDB."""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pika
import pytest

from src.services import queue_consumer


@pytest.fixture(autouse=True)
def disable_external_logs(monkeypatch):
    monkeypatch.setattr(queue_consumer, "save_log", None)


@pytest.fixture
def consumer():
    return queue_consumer.QueueConsumer()


@patch("src.services.queue_consumer.pika.BlockingConnection")
def test_connection_declares_durable_queues(mock_connection, consumer):
    assert consumer.connect()
    channel = mock_connection.return_value.channel.return_value
    assert channel.queue_declare.call_count == 2
    channel.basic_qos.assert_called_once_with(prefetch_count=1)


@patch("src.services.queue_consumer.pika.BlockingConnection", side_effect=pika.exceptions.AMQPError())
def test_connection_failure(mock_connection, consumer):
    assert consumer.connect() is False


@pytest.mark.parametrize("task, data", [
    ("send_email", {"user_id": 1}), ("update_stock", {"items": [1]}), ("generate_report", {}),
])
def test_successful_task_acknowledges_message(consumer, task, data):
    channel = MagicMock()
    body = json.dumps({"task": task, "order_id": 101, **data}).encode()
    consumer.process_message(channel, SimpleNamespace(delivery_tag=10), SimpleNamespace(headers=None), body)
    channel.basic_ack.assert_called_once_with(delivery_tag=10)
    channel.basic_publish.assert_not_called()


@pytest.mark.parametrize("attempt, expected_queue", [(0, "order_processing"), (3, "order_processing_errors")])
@patch("src.services.queue_consumer.time.sleep")
def test_failed_task_retries_then_goes_to_error_queue(mock_sleep, consumer, attempt, expected_queue):
    channel = MagicMock()
    body = b'{"task": "unsupported", "order_id": 101}'
    consumer.process_message(channel, SimpleNamespace(delivery_tag=10),
                             SimpleNamespace(headers={"x-retry-count": attempt}), body)
    published = channel.basic_publish.call_args.kwargs
    assert published["routing_key"] == expected_queue
    assert published["body"] == body
    assert published["properties"].delivery_mode == 2
    channel.basic_ack.assert_called_once_with(delivery_tag=10)
    if attempt == 0:
        assert published["properties"].headers == {"x-retry-count": 1}
        mock_sleep.assert_called_once_with(1)


def test_worker_stops_cleanly(consumer):
    consumer.channel = MagicMock()
    consumer.connection = MagicMock()
    consumer.channel.start_consuming.side_effect = KeyboardInterrupt
    with patch.object(consumer, "connect", return_value=True):
        consumer.start_consuming()
    consumer.channel.stop_consuming.assert_called_once()
    consumer.connection.close.assert_called_once()


def test_worker_returns_if_connection_failed(consumer):
    with patch.object(consumer, "connect", return_value=False):
        consumer.start_consuming()


def test_logging_failure_does_not_break_worker(monkeypatch):
    save_log = MagicMock(side_effect=RuntimeError("Mongo unavailable"))
    monkeypatch.setattr(queue_consumer, "save_log", save_log)
    queue_consumer.log_event(20, "synthetic event")
    queue_consumer.log_event(20, "second event")
    save_log.assert_called_once()
    assert queue_consumer.save_log is None
