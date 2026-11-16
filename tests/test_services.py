from unittest.mock import AsyncMock, MagicMock, patch

import logging
from datetime import datetime

from src.services.log_service import (
    LogService,
    save_log,
    get_logs_by_status_code,
    get_logs_by_date_range,
    get_logs_by_ip,
    get_logs_statistics,
)
import json
import pika

from src.services.queue_producer import QueueProducer, send_message

from redis.exceptions import RedisError

from src.services import cache_service

import httpx
import pytest
from requests.exceptions import ConnectionError, RequestException, Timeout

from src.services.exchange_client import (
    ExchangeClient,
    AsyncExchangeClient,
)

from types import SimpleNamespace
from src.services.multi_exchange_client import MultiExchangeClient
from src.services import payment_service, user_service
from src.services.order_service import OrderService
from src.services.order_calculator import OrderCalculator, PercentDiscount


@pytest.mark.parametrize("success", [True, False])
def test_payment_processing(success):
    payment = SimpleNamespace(amount=100, order_id=10, status="pending")
    method, repository, notifications = MagicMock(), MagicMock(), MagicMock()
    method.process.return_value = success
    processor = payment_service.PaymentProcessor(method, repository, notifications)
    if success:
        assert processor.process_payment(payment) == "completed"
        repository.save.assert_called_once_with(payment)
        notifications.send.assert_called_once_with(payment)
    else:
        with pytest.raises(ValueError, match="Ошибка обработки"):
            processor.process_payment(payment)
        assert payment.status == "failed"
        repository.save.assert_not_called()
        notifications.send.assert_not_called()


@pytest.mark.parametrize("amount", [0, -1])
def test_payment_rejects_invalid_amount(amount):
    method, repository, notifications = MagicMock(), MagicMock(), MagicMock()
    processor = payment_service.PaymentProcessor(method, repository, notifications)
    with pytest.raises(ValueError, match="положительной"):
        processor.process_payment(SimpleNamespace(amount=amount))
    method.process.assert_not_called()


def test_user_registration_and_report():
    user = SimpleNamespace(name="Анна", email="anna@example.test", age=18, balance=100,
                           orders=[SimpleNamespace(total=300), SimpleNamespace(total=200)])
    notifications, database = MagicMock(), MagicMock()
    service = user_service.UserService(notifications, database)
    service.register_user(user)
    database.save.assert_called_once_with(user)
    notifications.send.assert_called_once_with(user, "Добро пожаловать, Анна!")
    report = service.generate_user_report(user)
    assert "Всего заказов: 2" in report
    assert "Потрачено: 500" in report
    assert user_service.FixedDiscount(50).apply(100) == 150
    assert user_service.PercentDiscount(10).apply(100) == pytest.approx(110)


@pytest.mark.parametrize("field, value", [("name", ""), ("email", "invalid"), ("age", 17), ("balance", -1)])
def test_invalid_user_is_not_saved(field, value):
    user = SimpleNamespace(name="Анна", email="a@example.test", age=18, balance=0)
    setattr(user, field, value)
    database, notifications = MagicMock(), MagicMock()
    with pytest.raises(ValueError):
        user_service.UserService(notifications, database).register_user(user)
    database.save.assert_not_called()
    notifications.send.assert_not_called()


@pytest.mark.parametrize("discount, expected", [(None, 1000), (PercentDiscount(10), 900)])
def test_order_service_validates_calculates_and_saves(discount, expected):
    order = SimpleNamespace(items=[SimpleNamespace(price=500, quantity=2)], user="buyer")
    database, notifications = MagicMock(), MagicMock()
    assert OrderService(notifications, database).process_order(order, discount) == expected
    database.save.assert_called_once_with(order)
    notifications.send.assert_called_once_with(order)
    assert OrderCalculator.apply_discount(order, PercentDiscount(10)) == 900


@patch("src.services.multi_exchange_client.time.sleep")
@patch("src.services.multi_exchange_client.requests.get")
def test_multi_exchange_falls_back_after_retries(mock_get, mock_sleep):
    response = MagicMock()
    response.json.return_value = {"rates": {"USD": "0.01"}}
    mock_get.side_effect = [Timeout(), Timeout(), response]
    client = MultiExchangeClient(["https://first.test", "https://second.test"])
    assert client.get_exchange_rate("RUB", "USD") == 0.01
    assert mock_get.call_count == 3
    mock_sleep.assert_called_once_with(1)


@pytest.mark.parametrize("data", [{"rates": {}}, None])
@patch("src.services.multi_exchange_client.requests.get")
def test_multi_exchange_returns_none_on_bad_response(mock_get, data):
    if data is None:
        mock_get.return_value.json.side_effect = ValueError("invalid JSON")
    else:
        mock_get.return_value.json.return_value = data
    assert MultiExchangeClient(["https://example.test"]).get_exchange_rate("RUB", "USD") is None
    with pytest.raises(ValueError):
        MultiExchangeClient([])


# Синхронный клиент курсов валют

@pytest.fixture
def exchange_client():
    return ExchangeClient()


@patch("src.services.exchange_client.requests.get")
def test_get_exchange_rate(mock_get, exchange_client):
    mock_get.return_value.json.return_value = {
        "rates": {"USD": 0.01}
    }

    result = exchange_client.get_exchange_rate("RUB", "USD")

    assert result == 0.01

    mock_get.assert_called_once_with(
        f"{exchange_client.base_url}/RUB",
        timeout=5,
    )


@patch("src.services.exchange_client.requests.get")
def test_exchange_currency_not_found(mock_get, exchange_client):
    mock_get.return_value.json.return_value = {
        "rates": {"EUR": 0.009}
    }

    result = exchange_client.get_exchange_rate("RUB", "USD")

    assert result is None


@pytest.mark.parametrize("error", [Timeout, ConnectionError])
@patch("src.services.exchange_client.time.sleep")
@patch("src.services.exchange_client.requests.get")
def test_exchange_network_error(
    mock_get, mock_sleep, exchange_client, error
):
    mock_get.side_effect = error("Network error")

    result = exchange_client.get_exchange_rate("RUB", "USD")

    assert result is None
    assert mock_get.call_count == 3
    assert mock_sleep.call_count == 2

    mock_sleep.assert_any_call(1)
    mock_sleep.assert_any_call(2)


@patch("src.services.exchange_client.time.sleep")
@patch("src.services.exchange_client.requests.get")
def test_exchange_retry_success(
    mock_get, mock_sleep, exchange_client
):
    response = MagicMock()
    response.json.return_value = {"rates": {"USD": 0.01}}

    mock_get.side_effect = [
        Timeout("Timeout"),
        response,
    ]

    result = exchange_client.get_exchange_rate("RUB", "USD")

    assert result == 0.01
    assert mock_get.call_count == 2
    mock_sleep.assert_called_once_with(1)


@patch("src.services.exchange_client.requests.get")
def test_exchange_request_error(mock_get, exchange_client):
    mock_get.side_effect = RequestException("Request failed")

    result = exchange_client.get_exchange_rate("RUB", "USD")

    assert result is None
    mock_get.assert_called_once()


def test_exchange_zero_retries(exchange_client):
    exchange_client.max_retries = 0

    assert exchange_client.get_exchange_rate("RUB", "USD") is None


# Асинхронный клиент курсов валют

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def async_exchange_client():
    return AsyncExchangeClient()


@pytest.fixture
def mock_httpx_client():
    with patch(
        "src.services.exchange_client.httpx.AsyncClient"
    ) as mock_client:
        client = mock_client.return_value.__aenter__.return_value
        client.get = AsyncMock()

        yield client


def make_response(status_code=200, data=None):
    return httpx.Response(
        status_code,
        json=data if data is not None else {},
        request=httpx.Request(
            "GET",
            "https://example.com/RUB",
        ),
    )


@pytest.mark.anyio
async def test_async_get_exchange_rate(
    async_exchange_client, mock_httpx_client
):
    mock_httpx_client.get.return_value = make_response(
        data={"rates": {"USD": 0.01}}
    )

    result = await async_exchange_client.get_exchange_rate(
        "rub", "usd"
    )

    assert result == 0.01

    mock_httpx_client.get.assert_awaited_once_with(
        f"{async_exchange_client.base_url}/RUB"
    )


@pytest.mark.anyio
async def test_async_currency_not_found(
    async_exchange_client, mock_httpx_client
):
    mock_httpx_client.get.return_value = make_response(
        data={"rates": {"EUR": 0.009}}
    )

    result = await async_exchange_client.get_exchange_rate(
        "RUB", "USD"
    )

    assert result is None


@pytest.mark.anyio
@pytest.mark.parametrize("error", [
    httpx.ReadTimeout,
    httpx.ConnectError,
])
async def test_async_network_error(
    async_exchange_client, mock_httpx_client, error
):
    mock_httpx_client.get.side_effect = error("Network error")

    with patch(
        "src.services.exchange_client.asyncio.sleep",
        new_callable=AsyncMock,
    ) as mock_sleep:
        result = await async_exchange_client.get_exchange_rate(
            "RUB", "USD"
        )

    assert result is None
    assert mock_httpx_client.get.await_count == 3
    assert mock_sleep.await_count == 2

    mock_sleep.assert_any_await(1)
    mock_sleep.assert_any_await(2)


@pytest.mark.anyio
async def test_async_server_error(
    async_exchange_client, mock_httpx_client
):
    mock_httpx_client.get.return_value = make_response(500)

    with patch(
        "src.services.exchange_client.asyncio.sleep",
        new_callable=AsyncMock,
    ) as mock_sleep:
        result = await async_exchange_client.get_exchange_rate(
            "RUB", "USD"
        )

    assert result is None
    assert mock_httpx_client.get.await_count == 3
    assert mock_sleep.await_count == 2


@pytest.mark.anyio
async def test_async_client_error(
    async_exchange_client, mock_httpx_client
):
    mock_httpx_client.get.return_value = make_response(404)

    with patch(
        "src.services.exchange_client.asyncio.sleep",
        new_callable=AsyncMock,
    ) as mock_sleep:
        result = await async_exchange_client.get_exchange_rate(
            "RUB", "USD"
        )

    assert result is None
    mock_httpx_client.get.assert_awaited_once()
    mock_sleep.assert_not_awaited()


@pytest.mark.anyio
async def test_async_retry_success(
    async_exchange_client, mock_httpx_client
):
    mock_httpx_client.get.side_effect = [
        make_response(503),
        make_response(data={"rates": {"USD": 0.01}}),
    ]

    with patch(
        "src.services.exchange_client.asyncio.sleep",
        new_callable=AsyncMock,
    ) as mock_sleep:
        result = await async_exchange_client.get_exchange_rate(
            "RUB", "USD"
        )

    assert result == 0.01
    assert mock_httpx_client.get.await_count == 2
    mock_sleep.assert_awaited_once_with(1)


@pytest.mark.anyio
async def test_async_invalid_json(
    async_exchange_client, mock_httpx_client
):
    mock_httpx_client.get.return_value = httpx.Response(
        200,
        content=b"invalid json",
        request=httpx.Request(
            "GET",
            "https://example.com/RUB",
        ),
    )

    result = await async_exchange_client.get_exchange_rate(
        "RUB", "USD"
    )

    assert result is None


@pytest.mark.anyio
async def test_async_zero_retries(
    async_exchange_client, mock_httpx_client
):
    async_exchange_client.max_retries = 0

    result = await async_exchange_client.get_exchange_rate(
        "RUB", "USD"
    )

    assert result is None
    mock_httpx_client.get.assert_not_awaited()


# Конвертация валют

@pytest.mark.anyio
async def test_convert_same_currency(async_exchange_client):
    with patch.object(
        async_exchange_client,
        "get_exchange_rate",
        new_callable=AsyncMock,
    ) as mock_rate:
        result = await async_exchange_client.convert(
            100.126, "rub", "RUB"
        )

    assert result == 100.13
    mock_rate.assert_not_awaited()


@pytest.mark.anyio
async def test_convert_currency(async_exchange_client):
    with patch.object(
        async_exchange_client,
        "get_exchange_rate",
        new_callable=AsyncMock,
    ) as mock_rate:
        mock_rate.return_value = 0.01

        result = await async_exchange_client.convert(
            1500, "RUB", "USD"
        )

    assert result == 15.0
    mock_rate.assert_awaited_once_with("RUB", "USD")


@pytest.mark.anyio
async def test_convert_currency_unavailable(async_exchange_client):
    with patch.object(
        async_exchange_client,
        "get_exchange_rate",
        new_callable=AsyncMock,
    ) as mock_rate:
        mock_rate.return_value = None

        result = await async_exchange_client.convert(
            1500, "RUB", "USD"
        )

    assert result is None


# Сервис кеширования Redis

@pytest.fixture
def mock_redis(monkeypatch):
    client = MagicMock()

    client.get = AsyncMock()
    client.setex = AsyncMock()
    client.delete = AsyncMock()
    client.aclose = AsyncMock()

    monkeypatch.setattr(cache_service, "redis_client", client)
    monkeypatch.setattr(cache_service, "_redis_down_until", 0.0)

    return client


@pytest.fixture
def cached_product():
    return {
        "id": 1,
        "name": "Ноутбук",
        "price": 50000,
        "quantity": 3,
    }


# Получение данных из кеша

@pytest.mark.anyio
async def test_cache_get_hit(mock_redis, cached_product):
    mock_redis.get.return_value = json.dumps(cached_product)

    result = await cache_service.cache_get("products:item:1")

    assert result == cached_product
    mock_redis.get.assert_awaited_once_with("products:item:1")


@pytest.mark.anyio
async def test_cache_get_miss(mock_redis):
    mock_redis.get.return_value = None

    result = await cache_service.cache_get("products:item:1")

    assert result is None


@pytest.mark.anyio
@pytest.mark.parametrize("error", [RedisError, OSError])
async def test_cache_get_error(mock_redis, error):
    mock_redis.get.side_effect = error("Redis unavailable")

    with patch(
        "src.services.cache_service.time.monotonic",
        return_value=100.0,
    ):
        result = await cache_service.cache_get("products:item:1")

        assert result is None
        assert cache_service._redis_down_until == 130.0
        assert cache_service._redis_available() is False


@pytest.mark.anyio
async def test_cache_get_redis_down(mock_redis, monkeypatch):
    monkeypatch.setattr(
        cache_service, "_redis_down_until", float("inf")
    )

    result = await cache_service.cache_get("products:item:1")

    assert result is None
    mock_redis.get.assert_not_awaited()


def test_redis_available_after_timeout(monkeypatch):
    monkeypatch.setattr(
        cache_service, "_redis_down_until", 130.0
    )

    with patch(
        "src.services.cache_service.time.monotonic",
        return_value=131.0,
    ):
        assert cache_service._redis_available() is True


# Сохранение данных в кеш

@pytest.mark.anyio
async def test_cache_set(mock_redis, cached_product):
    await cache_service.cache_set(
        "products:item:1", cached_product
    )

    mock_redis.setex.assert_awaited_once_with(
        "products:item:1",
        300,
        json.dumps(
            cached_product,
            ensure_ascii=False,
            default=str,
        ),
    )


@pytest.mark.anyio
async def test_cache_set_custom_ttl(mock_redis):
    await cache_service.cache_set("test:key", {"value": 1}, ttl=60)

    mock_redis.setex.assert_awaited_once_with(
        "test:key",
        60,
        '{"value": 1}',
    )


@pytest.mark.anyio
async def test_cache_set_error(mock_redis):
    mock_redis.setex.side_effect = RedisError("Redis unavailable")

    await cache_service.cache_set("test:key", {"value": 1})

    assert cache_service._redis_available() is False


@pytest.mark.anyio
async def test_cache_set_redis_down(mock_redis, monkeypatch):
    monkeypatch.setattr(
        cache_service, "_redis_down_until", float("inf")
    )

    await cache_service.cache_set("test:key", {"value": 1})

    mock_redis.setex.assert_not_awaited()


# Инвалидация кеша

async def async_keys(keys):
    for key in keys:
        yield key


@pytest.mark.anyio
async def test_invalidate_products(mock_redis):
    keys = ["products:list:20:0", "products:item:1"]

    mock_redis.scan_iter.return_value = async_keys(keys)

    await cache_service.invalidate_products()

    mock_redis.scan_iter.assert_called_once_with(
        match="products:*"
    )
    mock_redis.delete.assert_awaited_once_with(*keys)


@pytest.mark.anyio
async def test_invalidate_products_empty(mock_redis):
    mock_redis.scan_iter.return_value = async_keys([])

    await cache_service.invalidate_products()

    mock_redis.delete.assert_not_awaited()


@pytest.mark.anyio
async def test_invalidate_products_error(mock_redis):
    mock_redis.scan_iter.side_effect = RedisError(
        "Redis unavailable"
    )

    await cache_service.invalidate_products()

    assert cache_service._redis_available() is False


@pytest.mark.anyio
async def test_invalidate_products_redis_down(
    mock_redis, monkeypatch
):
    monkeypatch.setattr(
        cache_service, "_redis_down_until", float("inf")
    )

    await cache_service.invalidate_products()

    mock_redis.scan_iter.assert_not_called()
    mock_redis.delete.assert_not_awaited()


# Кеширование списка товаров

@pytest.mark.anyio
async def test_get_products_cached_hit(mock_redis, cached_product):
    repo = MagicMock()
    repo.list_products = AsyncMock()
    repo.count = AsyncMock()

    page = {
        "products": [cached_product],
        "total": 1,
        "limit": 20,
        "offset": 0,
    }

    mock_redis.get.return_value = json.dumps(page)

    result, cache_hit = await cache_service.get_products_cached(
        repo, 20, 0
    )

    assert result == page
    assert cache_hit is True

    repo.list_products.assert_not_awaited()
    repo.count.assert_not_awaited()


@pytest.mark.anyio
async def test_get_products_cached_miss(mock_redis, cached_product):
    repo = MagicMock()
    repo.list_products = AsyncMock(return_value=[cached_product])
    repo.count = AsyncMock(return_value=1)

    mock_redis.get.return_value = None

    result, cache_hit = await cache_service.get_products_cached(
        repo, 20, 0
    )

    assert result == {
        "products": [cached_product],
        "total": 1,
        "limit": 20,
        "offset": 0,
    }
    assert cache_hit is False

    repo.list_products.assert_awaited_once_with(
        limit=20, offset=0
    )
    repo.count.assert_awaited_once()

    mock_redis.setex.assert_awaited_once_with(
        "products:list:20:0",
        300,
        json.dumps(result, ensure_ascii=False, default=str),
    )


# Кеширование отдельного товара

@pytest.mark.anyio
async def test_get_product_cached_hit(mock_redis, cached_product):
    repo = MagicMock()
    repo.get_by_id = AsyncMock()

    mock_redis.get.return_value = json.dumps(cached_product)

    result, cache_hit = await cache_service.get_product_cached(
        repo, 1
    )

    assert result == cached_product
    assert cache_hit is True

    repo.get_by_id.assert_not_awaited()


@pytest.mark.anyio
async def test_get_product_cached_miss(mock_redis, cached_product):
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=cached_product)

    mock_redis.get.return_value = None

    result, cache_hit = await cache_service.get_product_cached(
        repo, 1
    )

    assert result == cached_product
    assert cache_hit is False

    repo.get_by_id.assert_awaited_once_with(1)

    mock_redis.setex.assert_awaited_once_with(
        "products:item:1",
        300,
        json.dumps(
            cached_product,
            ensure_ascii=False,
            default=str,
        ),
    )


@pytest.mark.anyio
async def test_get_product_cached_not_found(mock_redis):
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)

    mock_redis.get.return_value = None

    result, cache_hit = await cache_service.get_product_cached(
        repo, 999
    )

    assert result is None
    assert cache_hit is False

    mock_redis.setex.assert_not_awaited()


@pytest.mark.anyio
async def test_get_product_cached_redis_unavailable(
    mock_redis, cached_product
):
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=cached_product)

    mock_redis.get.side_effect = RedisError("Redis unavailable")

    result, cache_hit = await cache_service.get_product_cached(
        repo, 1
    )

    assert result == cached_product
    assert cache_hit is False

    repo.get_by_id.assert_awaited_once_with(1)
    mock_redis.setex.assert_not_awaited()


# Закрытие соединения

@pytest.mark.anyio
async def test_close_cache(mock_redis):
    await cache_service.close_cache()

    mock_redis.aclose.assert_awaited_once()


@pytest.mark.anyio
async def test_close_cache_error(mock_redis):
    mock_redis.aclose.side_effect = RedisError("Connection error")

    await cache_service.close_cache()

    mock_redis.aclose.assert_awaited_once()


# RabbitMQ

@pytest.fixture
def queue_producer():
    return QueueProducer()


@pytest.fixture
def mock_rabbitmq():
    with patch(
        "src.services.queue_producer.pika.BlockingConnection"
    ) as mock_connection:
        connection = mock_connection.return_value
        channel = connection.channel.return_value

        connection.is_closed = False

        yield mock_connection, connection, channel


# Отправка отдельного сообщения

def test_send_message(mock_rabbitmq):
    mock_connection, connection, channel = mock_rabbitmq

    message = {"test": "message"}

    send_message("test_queue", message)

    mock_connection.assert_called_once()

    channel.queue_declare.assert_called_once_with(
        queue="test_queue",
        durable=True,
    )

    channel.basic_publish.assert_called_once()

    kwargs = channel.basic_publish.call_args.kwargs

    assert kwargs["exchange"] == ""
    assert kwargs["routing_key"] == "test_queue"
    assert json.loads(kwargs["body"]) == message
    assert kwargs["properties"].delivery_mode == 2

    connection.close.assert_called_once()


# Подключение к RabbitMQ

def test_queue_connect(queue_producer, mock_rabbitmq):
    mock_connection, connection, channel = mock_rabbitmq

    result = queue_producer.connect()

    assert result is True
    assert queue_producer.connection is connection
    assert queue_producer.channel is channel

    channel.queue_declare.assert_called_once_with(
        queue="order_processing",
        durable=True,
    )


def test_queue_connect_error(queue_producer, mock_rabbitmq):
    mock_connection, _, _ = mock_rabbitmq

    mock_connection.side_effect = pika.exceptions.AMQPError(
        "Connection failed"
    )

    result = queue_producer.connect()

    assert result is False
    assert queue_producer.channel is None


# Отправка задач

def test_send_order_task(queue_producer, mock_rabbitmq):
    mock_connection, connection, channel = mock_rabbitmq

    result = queue_producer.send_order_task(
        order_id=5,
        task_type="send_email",
        data={"user_id": 1},
    )

    assert result is True

    mock_connection.assert_called_once()
    channel.basic_publish.assert_called_once()

    kwargs = channel.basic_publish.call_args.kwargs

    assert kwargs["exchange"] == ""
    assert kwargs["routing_key"] == "order_processing"
    assert json.loads(kwargs["body"]) == {
        "task": "send_email",
        "order_id": 5,
        "user_id": 1,
    }
    assert kwargs["properties"].delivery_mode == 2


def test_send_order_task_reuse_connection(
    queue_producer, mock_rabbitmq
):
    mock_connection, connection, channel = mock_rabbitmq

    first = queue_producer.send_order_task(
        5, "send_email", {"user_id": 1}
    )

    second = queue_producer.send_order_task(
        5, "generate_report", {}
    )

    assert first is True
    assert second is True

    mock_connection.assert_called_once()
    assert channel.basic_publish.call_count == 2


def test_send_order_task_connection_error(
    queue_producer, mock_rabbitmq
):
    mock_connection, _, channel = mock_rabbitmq

    mock_connection.side_effect = pika.exceptions.AMQPError(
        "Connection failed"
    )

    result = queue_producer.send_order_task(
        5, "send_email", {}
    )

    assert result is False
    channel.basic_publish.assert_not_called()


def test_send_order_task_publish_error(
    queue_producer, mock_rabbitmq
):
    _, _, channel = mock_rabbitmq

    channel.basic_publish.side_effect = pika.exceptions.AMQPError(
        "Publish failed"
    )

    result = queue_producer.send_order_task(
        5, "send_email", {}
    )

    assert result is False
    assert queue_producer.channel is None


def test_send_order_task_reconnect(
    queue_producer, mock_rabbitmq
):
    mock_connection, _, channel = mock_rabbitmq

    channel.basic_publish.side_effect = [
        pika.exceptions.AMQPError("Publish failed"),
        None,
    ]

    first = queue_producer.send_order_task(
        5, "send_email", {}
    )

    second = queue_producer.send_order_task(
        5, "generate_report", {}
    )

    assert first is False
    assert second is True

    assert mock_connection.call_count == 2
    assert channel.basic_publish.call_count == 2


# Закрытие соединения

def test_queue_close(queue_producer, mock_rabbitmq):
    _, connection, _ = mock_rabbitmq

    queue_producer.connect()
    queue_producer.close()

    connection.close.assert_called_once()


def test_queue_close_already_closed(
    queue_producer, mock_rabbitmq
):
    _, connection, _ = mock_rabbitmq

    queue_producer.connect()
    connection.is_closed = True

    queue_producer.close()

    connection.close.assert_not_called()


def test_queue_close_without_connection(queue_producer):
    queue_producer.close()

    assert queue_producer.connection is None

# Логирование в MongoDB

@pytest.fixture
def mock_logs_collection():
    with patch(
        "src.services.log_service.logs_collection"
    ) as collection:
        yield collection


def test_save_log(mock_logs_collection):
    mock_logs_collection.insert_one.return_value.inserted_id = "log_1"

    log_data = {
        "type": "request",
        "status_code": 200,
    }

    result = save_log(log_data)

    assert result == "log_1"
    assert isinstance(log_data["timestamp"], datetime)

    mock_logs_collection.insert_one.assert_called_once_with(
        log_data
    )


def test_save_log_existing_timestamp(mock_logs_collection):
    timestamp = datetime(2026, 1, 1)

    log_data = {
        "type": "request",
        "timestamp": timestamp,
    }

    save_log(log_data)

    assert log_data["timestamp"] == timestamp

    mock_logs_collection.insert_one.assert_called_once_with(
        log_data
    )


def test_get_logs_by_status_code(mock_logs_collection):
    logs = [
        {"status_code": 400},
        {"status_code": 404},
    ]

    mock_logs_collection.find.return_value = logs

    result = get_logs_by_status_code(400, 500)

    assert result == logs

    mock_logs_collection.find.assert_called_once_with({
        "status_code": {"$gte": 400, "$lt": 500}
    })


def test_get_logs_by_date_range(mock_logs_collection):
    start = datetime(2026, 1, 1)
    end = datetime(2026, 1, 31)

    logs = [{"timestamp": start}]

    mock_logs_collection.find.return_value = logs

    result = get_logs_by_date_range(start, end)

    assert result == logs

    mock_logs_collection.find.assert_called_once_with({
        "timestamp": {"$gte": start, "$lte": end}
    })


def test_get_logs_by_ip(mock_logs_collection):
    logs = [{"ip": "127.0.0.1"}]

    mock_logs_collection.find.return_value = logs

    result = get_logs_by_ip("127.0.0.1")

    assert result == logs

    mock_logs_collection.find.assert_called_once_with({
        "ip": "127.0.0.1"
    })


def test_get_logs_statistics(mock_logs_collection):
    type_stats = [{"_id": "request", "count": 5}]
    status_stats = [{"_id": 200, "count": 5}]

    mock_logs_collection.aggregate.side_effect = [
        type_stats,
        status_stats,
    ]

    mock_logs_collection.count_documents.return_value = 5

    result = get_logs_statistics()

    assert result == {
        "by_type": type_stats,
        "by_status": status_stats,
        "total": 5,
    }

    assert mock_logs_collection.aggregate.call_count == 2

    mock_logs_collection.aggregate.assert_any_call([
        {"$group": {"_id": "$type", "count": {"$sum": 1}}}
    ])

    mock_logs_collection.aggregate.assert_any_call([
        {"$group": {"_id": "$status_code", "count": {"$sum": 1}}}
    ])

    mock_logs_collection.count_documents.assert_called_once_with({})


# Сервис логирования приложения

@pytest.fixture
def isolated_log_service(tmp_path):
    logger = logging.Logger("test_sfmshop")

    with patch(
        "src.services.log_service.logging.getLogger",
        return_value=logger,
    ):
        service = LogService(
            log_file=str(tmp_path / "test.log")
        )

    yield service

    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)


def test_log_service_init(isolated_log_service):
    logger = isolated_log_service.logger

    assert logger.level == logging.DEBUG
    assert logger.propagate is False
    assert len(logger.handlers) == 2

    assert isinstance(
        logger.handlers[0], logging.FileHandler
    )

    assert isinstance(
        logger.handlers[1], logging.StreamHandler
    )


def test_log_service_no_duplicate_handlers(
    isolated_log_service, tmp_path
):
    logger = isolated_log_service.logger

    with patch(
        "src.services.log_service.logging.getLogger",
        return_value=logger,
    ):
        second_service = LogService(
            log_file=str(tmp_path / "second.log")
        )

    assert second_service.logger is logger
    assert len(logger.handlers) == 2


@pytest.mark.parametrize("level", [
    "debug",
    "info",
    "warning",
    "error",
    "exception",
])
def test_log_service_levels(isolated_log_service, level):
    with patch.object(
        isolated_log_service.logger, level
    ) as mock_log:
        log_method = getattr(isolated_log_service, level)

        log_method("Тестовое сообщение", user_id=1)

        mock_log.assert_called_once_with(
            "Тестовое сообщение | {'user_id': 1}"
        )


def test_log_service_critical(isolated_log_service):
    with patch.object(
        isolated_log_service.logger, "critical"
    ) as mock_critical:
        with patch.object(
            isolated_log_service, "send_alert"
        ) as mock_alert:

            isolated_log_service.critical(
                "Ошибка сервера", status_code=500
            )

    mock_critical.assert_called_once_with(
        "АЛЕРТ: Ошибка сервера | {'status_code': 500}"
    )

    mock_alert.assert_called_once_with(
        "Ошибка сервера", status_code=500
    )


def test_log_service_send_alert(isolated_log_service, capsys):
    isolated_log_service.send_alert(
        "Ошибка сервера", status_code=500
    )

    captured = capsys.readouterr()

    assert "[ALERT] Ошибка сервера" in captured.out
    assert "'status_code': 500" in captured.out


def test_log_service_writes_to_file(
    isolated_log_service, tmp_path
):
    isolated_log_service.info(
        "Заказ создан", order_id=5
    )

    log_file = tmp_path / "test.log"
    content = log_file.read_text(encoding="utf-8")

    assert "INFO" in content
    assert "Заказ создан" in content
    assert "'order_id': 5" in content
