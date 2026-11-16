import asyncpg
from src.dependencies import get_user_repository
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.dependencies import get_current_user, get_order_repository, get_product_repository

# Без "with" lifespan не запускается: пул к PostgreSQL не создаётся
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_overrides():
    """После каждого теста убираем подменённые зависимости"""
    yield
    app.dependency_overrides.clear()


# products.py делает from cache_service import get_products_cached,
# поэтому патчим по месту использования: src.api.routes.products
@patch("src.api.routes.products.get_products_cached", new_callable=AsyncMock)
def test_get_products(mock_get_cached):
    """GET /api/v1/products: Redis и база подменены моками"""
    page = {
        "products": [
            {"id": 1, "name": "Ноутбук", "price": 50000.0, "quantity": 3},
            {"id": 2, "name": "Мышь", "price": 1500.0, "quantity": 10},
            {"id": 3, "name": "Клавиатура", "price": 3000.0, "quantity": 5},
        ],
        "total": 3,
        "limit": 20,
        "offset": 0,
    }
    mock_get_cached.return_value = (page, True)
    app.dependency_overrides[get_product_repository] = lambda: MagicMock()

    response = client.get("/api/v1/products")

    assert response.status_code == 200
    data = response.json()
    assert len(data["products"]) == 3
    assert data["products"][0]["name"] == "Ноутбук"
    assert response.headers["X-Cache"] == "HIT"
    mock_get_cached.assert_awaited_once()


# orders.py импортирует invalidate_products и создаёт producer у себя,
# поэтому оба патчим в src.api.routes.orders
@patch("src.api.routes.orders.producer")
@patch("src.api.routes.orders.invalidate_products", new_callable=AsyncMock)
def test_create_order(mock_invalidate, mock_producer):
    """POST /api/v1/orders: база, Redis и RabbitMQ подменены моками"""
    repo = MagicMock()
    repo.create = AsyncMock(return_value=SimpleNamespace(id=5, total=1500.0, status="new"))
    app.dependency_overrides[get_order_repository] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: 1

    response = client.post("/api/v1/orders", json={"items": [{"product_id": 2, "quantity": 1}]})

    assert response.status_code == 201
    assert response.json() == {"id": 5, "total": 1500.0, "status": "new"}
    repo.create.assert_awaited_once_with(1, [{"product_id": 2, "quantity": 1}])
    mock_invalidate.assert_awaited_once()
    assert mock_producer.send_order_task.call_count == 3

# Фикстуры для тестирования товаров

@pytest.fixture
def product_repo():
    repo = MagicMock()
    app.dependency_overrides[get_product_repository] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: 1
    return repo


@pytest.fixture
def sample_product():
    return {
        "id": 1,
        "name": "Ноутбук",
        "price": 50000.0,
        "quantity": 3,
    }


# Получение списка товаров без кеша

@patch("src.api.routes.products.get_products_cached", new_callable=AsyncMock)
def test_get_products_cache_miss(mock_cached, product_repo):
    mock_cached.return_value = (
        {"products": [], "total": 0, "limit": 10, "offset": 0},
        False,
    )

    response = client.get("/api/v1/products?limit=10")

    assert response.status_code == 200
    assert response.json()["products"] == []
    assert response.headers["X-Cache"] == "MISS"
    assert response.headers["Cache-Control"] == "public, max-age=60"

    mock_cached.assert_awaited_once_with(product_repo, 10, 0)


@pytest.mark.parametrize("params", [
    "?limit=0",
    "?limit=101",
    "?offset=-1",
])
def test_get_products_invalid_params(product_repo, params):
    response = client.get(f"/api/v1/products{params}")

    assert response.status_code == 422


# Получение отдельного товара

@pytest.mark.parametrize("from_cache, expected_header", [
    (True, "HIT"),
    (False, "MISS"),
])
@patch("src.api.routes.products.get_product_cached", new_callable=AsyncMock)
def test_get_product(
    mock_cached, product_repo, sample_product,
    from_cache, expected_header
):
    mock_cached.return_value = (sample_product, from_cache)

    response = client.get("/api/v1/products/1")

    assert response.status_code == 200
    assert response.json() == sample_product
    assert response.headers["X-Cache"] == expected_header

    mock_cached.assert_awaited_once_with(product_repo, 1)


@patch("src.api.routes.products.get_product_cached", new_callable=AsyncMock)
def test_get_product_not_found(mock_cached, product_repo):
    mock_cached.return_value = (None, False)

    response = client.get("/api/v1/products/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Товар не найден"


# Конвертация цены товара

@patch("src.api.routes.products.exchange_client.convert", new_callable=AsyncMock)
@patch("src.api.routes.products.get_product_cached", new_callable=AsyncMock)
def test_get_product_price(
    mock_cached, mock_convert, product_repo, sample_product
):
    mock_cached.return_value = (sample_product, True)
    mock_convert.return_value = 500.0

    response = client.get("/api/v1/products/1/price?currency=USD")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "price_rub": 50000.0,
        "currency": "USD",
        "price": 500.0,
    }

    mock_convert.assert_awaited_once_with(50000.0, "RUB", "USD")


@patch("src.api.routes.products.exchange_client.convert", new_callable=AsyncMock)
@patch("src.api.routes.products.get_product_cached", new_callable=AsyncMock)
def test_get_product_price_not_found(
    mock_cached, mock_convert, product_repo
):
    mock_cached.return_value = (None, False)

    response = client.get("/api/v1/products/999/price")

    assert response.status_code == 404
    mock_convert.assert_not_awaited()


@patch("src.api.routes.products.exchange_client.convert", new_callable=AsyncMock)
@patch("src.api.routes.products.get_product_cached", new_callable=AsyncMock)
def test_get_product_price_service_unavailable(
    mock_cached, mock_convert, product_repo, sample_product
):
    mock_cached.return_value = (sample_product, True)
    mock_convert.return_value = None

    response = client.get("/api/v1/products/1/price")

    assert response.status_code == 503


# Создание товара

@patch("src.api.routes.products.invalidate_products", new_callable=AsyncMock)
def test_create_product(mock_invalidate, product_repo):
    product_repo.create = AsyncMock(return_value=1)

    payload = {
        "name": "Ноутбук",
        "price": 50000.0,
        "quantity": 3,
    }

    response = client.post("/api/v1/products", json=payload)

    assert response.status_code == 201
    assert response.json() == {"id": 1, **payload}

    product_repo.create.assert_awaited_once_with(
        "Ноутбук", 50000.0, 3
    )
    mock_invalidate.assert_awaited_once()


# Изменение товара

@patch("src.api.routes.products.invalidate_products", new_callable=AsyncMock)
def test_update_product(
    mock_invalidate, product_repo, sample_product
):
    updated_product = {**sample_product, "price": 45000.0}
    product_repo.update = AsyncMock(return_value=updated_product)

    response = client.patch(
        "/api/v1/products/1",
        json={"price": 45000.0},
    )

    assert response.status_code == 200
    assert response.json()["price"] == 45000.0

    product_repo.update.assert_awaited_once_with(
        1, {"price": 45000.0}
    )
    mock_invalidate.assert_awaited_once()


@patch("src.api.routes.products.invalidate_products", new_callable=AsyncMock)
def test_update_product_not_found(mock_invalidate, product_repo):
    product_repo.update = AsyncMock(return_value=None)

    response = client.patch(
        "/api/v1/products/999",
        json={"price": 1000.0},
    )

    assert response.status_code == 404
    mock_invalidate.assert_not_awaited()


# Удаление товара

@patch("src.api.routes.products.invalidate_products", new_callable=AsyncMock)
def test_delete_product(mock_invalidate, product_repo):
    product_repo.delete = AsyncMock(return_value=True)

    response = client.delete("/api/v1/products/1")

    assert response.status_code == 204
    assert response.content == b""

    product_repo.delete.assert_awaited_once_with(1)
    mock_invalidate.assert_awaited_once()


@patch("src.api.routes.products.invalidate_products", new_callable=AsyncMock)
def test_delete_product_not_found(mock_invalidate, product_repo):
    product_repo.delete = AsyncMock(return_value=False)

    response = client.delete("/api/v1/products/999")

    assert response.status_code == 404
    mock_invalidate.assert_not_awaited()


@patch("src.api.routes.products.invalidate_products", new_callable=AsyncMock)
def test_delete_product_in_order(mock_invalidate, product_repo):
    product_repo.delete = AsyncMock(
        side_effect=asyncpg.ForeignKeyViolationError()
    )

    response = client.delete("/api/v1/products/1")

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Товар есть в заказах, удалить нельзя"
    )
    mock_invalidate.assert_not_awaited()


# Ошибка при получении списка товаров

@patch("src.api.routes.products.get_products_cached", new_callable=AsyncMock)
def test_get_products_error(mock_cached, product_repo):
    mock_cached.side_effect = RuntimeError("Database unavailable")

    with pytest.raises(RuntimeError, match="Database unavailable"):
        client.get("/api/v1/products")


# Фикстура репозитория заказов

@pytest.fixture
def order_repo():
    repo = MagicMock()
    app.dependency_overrides[get_order_repository] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: 1
    return repo


# Ошибки при создании заказа

@pytest.mark.parametrize("error, expected_status, expected_detail", [
    (LookupError("Товар не найден"), 404, "Товар не найден"),
    (ValueError("Недостаточно товара"), 409, "Недостаточно товара"),
    (
        asyncpg.ForeignKeyViolationError(),
        401,
        "Пользователь не найден",
    ),
])
@patch("src.api.routes.orders.producer")
@patch("src.api.routes.orders.invalidate_products", new_callable=AsyncMock)
def test_create_order_errors(
    mock_invalidate, mock_producer, order_repo,
    error, expected_status, expected_detail
):
    order_repo.create = AsyncMock(side_effect=error)

    response = client.post(
        "/api/v1/orders",
        json={"items": [{"product_id": 2, "quantity": 1}]},
    )

    assert response.status_code == expected_status
    assert response.json()["detail"] == expected_detail

    mock_invalidate.assert_not_awaited()
    mock_producer.send_order_task.assert_not_called()


@patch("src.api.routes.orders.producer")
@patch("src.api.routes.orders.invalidate_products", new_callable=AsyncMock)
def test_create_order_unexpected_error(
    mock_invalidate, mock_producer, order_repo
):
    order_repo.create = AsyncMock(
        side_effect=RuntimeError("Database unavailable")
    )

    with pytest.raises(RuntimeError, match="Database unavailable"):
        client.post(
            "/api/v1/orders",
            json={"items": [{"product_id": 2, "quantity": 1}]},
        )

    mock_invalidate.assert_not_awaited()
    mock_producer.send_order_task.assert_not_called()


# Получение заказов

def test_list_my_orders(order_repo):
    orders = [
        {"id": 5, "total": 1500.0, "status": "new"},
        {"id": 6, "total": 3000.0, "status": "completed"},
    ]

    order_repo.list_by_user = AsyncMock(return_value=orders)

    response = client.get("/api/v1/orders")

    assert response.status_code == 200
    assert response.json() == {"orders": orders}

    order_repo.list_by_user.assert_awaited_once_with(1)


def test_list_my_orders_empty(order_repo):
    order_repo.list_by_user = AsyncMock(return_value=[])

    response = client.get("/api/v1/orders")

    assert response.status_code == 200
    assert response.json() == {"orders": []}


def test_get_my_order(order_repo):
    order_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(
            id=5,
            user_id=1,
            total=1500.0,
            status="new",
        )
    )

    response = client.get("/api/v1/orders/5")

    assert response.status_code == 200
    assert response.json() == {
        "id": 5,
        "total": 1500.0,
        "status": "new",
    }

    order_repo.get_by_id.assert_awaited_once_with(5)


def test_get_foreign_order(order_repo):
    order_repo.get_by_id = AsyncMock(
        return_value=SimpleNamespace(
            id=5,
            user_id=2,
            total=1500.0,
            status="new",
        )
    )

    response = client.get("/api/v1/orders/5")

    assert response.status_code == 404
    assert response.json() == {"detail": "Заказ не найден"}


def test_get_missing_order(order_repo):
    order_repo.get_by_id = AsyncMock(return_value=None)

    response = client.get("/api/v1/orders/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Заказ не найден"}


# Фикстура репозитория пользователей

@pytest.fixture
def user_repo():
    repo = MagicMock()
    app.dependency_overrides[get_user_repository] = lambda: repo
    app.dependency_overrides[get_current_user] = lambda: 1
    return repo


@pytest.fixture
def user_credentials():
    return {
        "email": "test@example.com",
        "password": "StrongPassword123",
    }


# Регистрация пользователя

@patch("src.api.routes.users.hash_password")
def test_register_user(mock_hash, user_repo, user_credentials):
    mock_hash.return_value = "hashed_password"
    user_repo.create = AsyncMock(return_value=1)

    payload = {"name": "Анна", **user_credentials}

    response = client.post("/api/v1/register", json=payload)

    assert response.status_code == 201
    assert response.json() == {
        "id": 1,
        "email": "test@example.com",
    }

    mock_hash.assert_called_once_with("StrongPassword123")
    user_repo.create.assert_awaited_once_with(
        "Анна",
        "test@example.com",
        "hashed_password",
    )


@patch("src.api.routes.users.hash_password")
def test_register_existing_email(
    mock_hash, user_repo, user_credentials
):
    mock_hash.return_value = "hashed_password"
    user_repo.create = AsyncMock(
        side_effect=asyncpg.UniqueViolationError()
    )

    response = client.post(
        "/api/v1/register",
        json={"name": "Анна", **user_credentials},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email уже зарегистрирован"


# Авторизация пользователя

@patch("src.api.routes.users.create_access_token")
@patch("src.api.routes.users.verify_password")
def test_login_success(
    mock_verify, mock_token, user_repo, user_credentials
):
    user_repo.get_by_email = AsyncMock(
        return_value={"id": 1, "password_hash": "hashed_password"}
    )

    mock_verify.return_value = True
    mock_token.return_value = "test_access_token"

    response = client.post("/api/v1/login", json=user_credentials)

    assert response.status_code == 200
    assert response.json()["access_token"] == "test_access_token"

    user_repo.get_by_email.assert_awaited_once_with(
        "test@example.com"
    )
    mock_verify.assert_called_once_with(
        "StrongPassword123", "hashed_password"
    )
    mock_token.assert_called_once_with(1)


@pytest.mark.parametrize("user", [
    None,
    {"id": 1, "password_hash": ""},
    {"id": 1, "password_hash": "hashed_password"},
])
@patch("src.api.routes.users.create_access_token")
@patch("src.api.routes.users.verify_password")
def test_login_invalid_credentials(
    mock_verify, mock_token, user_repo, user_credentials, user
):
    user_repo.get_by_email = AsyncMock(return_value=user)
    mock_verify.return_value = False

    response = client.post("/api/v1/login", json=user_credentials)

    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный email или пароль"

    mock_token.assert_not_called()


# Получение текущего пользователя

def test_read_me(user_repo):
    user = {
        "id": 1,
        "name": "Анна",
        "email": "test@example.com",
    }

    user_repo.get_by_id = AsyncMock(return_value=user)

    response = client.get("/api/v1/users/me")

    assert response.status_code == 200
    assert response.json() == user

    user_repo.get_by_id.assert_awaited_once_with(1)


def test_read_me_not_found(user_repo):
    user_repo.get_by_id = AsyncMock(return_value=None)

    response = client.get("/api/v1/users/me")

    assert response.status_code == 404
    assert response.json()["detail"] == "Пользователь не найден"


def test_password_hash_and_verification():
    from src.api.auth import hash_password, verify_password

    password_hash = hash_password("synthetic-password")
    assert password_hash != "synthetic-password"
    assert verify_password("synthetic-password", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_access_token_roundtrip():
    from src.api.auth import create_access_token, decode_access_token

    assert decode_access_token(create_access_token(42)) == 42
    assert decode_access_token("invalid-token") is None


@pytest.mark.parametrize("payload", [
    {"sub": "42", "exp": 1}, {"sub": "invalid"}, {},
])
def test_invalid_token_claims(payload):
    from jose import jwt
    from src.api.auth import decode_access_token
    from src.core.config import settings

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    assert decode_access_token(token) is None


@pytest.mark.parametrize("token", [None, "invalid-token"])
def test_support_requires_authorization(token):
    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    with patch("src.api.main.AsyncOpenAI") as mock_llm:
        response = client.post("/api/v1/support", json={"question": "Доставка?"}, headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
    mock_llm.assert_not_called()


@patch("src.api.main.answer_support", new_callable=AsyncMock)
def test_support_uses_token_identity(mock_answer):
    from src.api.auth import create_access_token
    from src.api.main import get_llm_client
    from src.services.support_service import SupportAnswer

    repo = MagicMock()
    llm = MagicMock()
    app.dependency_overrides[get_order_repository] = lambda: repo
    app.dependency_overrides[get_llm_client] = lambda: llm
    mock_answer.return_value = SupportAnswer(answer="Заказ не найден или недоступен.")
    response = client.post(
        "/api/v1/support", json={"question": "Покажи заказ 202"},
        headers={"Authorization": f"Bearer {create_access_token(1)}"},
    )
    assert response.status_code == 200
    mock_answer.assert_awaited_once_with(
        question="Покажи заказ 202", current_user_id=1, order_repo=repo, client=llm,
    )


@pytest.mark.parametrize("db_available, redis_available, expected", [
    (True, True, 200), (True, False, 200), (False, True, 503),
])
def test_readiness(db_available, redis_available, expected, monkeypatch):
    pool = SimpleNamespace(fetchval=AsyncMock(return_value=1))
    if not db_available:
        pool.fetchval.side_effect = RuntimeError("database unavailable")
    monkeypatch.setattr(app.state, "pool", pool, raising=False)
    ping = AsyncMock(return_value=True)
    if not redis_available:
        ping.side_effect = RuntimeError("redis unavailable")
    with patch("src.api.main.redis_client.ping", ping):
        response = client.get("/health/ready")
    assert response.status_code == expected
    assert response.json()["checks"] == {"database": db_available, "redis": redis_available}


def test_liveness_and_admin_page():
    assert client.get("/health/live").json() == {"status": "alive"}
    response = client.get("/admin")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_lifespan_opens_and_closes_resources():
    pool = SimpleNamespace(close=AsyncMock(), fetchval=AsyncMock(return_value=1))
    with patch("src.api.main.asyncpg.create_pool", new_callable=AsyncMock, return_value=pool), \
            patch("src.api.main.close_cache", new_callable=AsyncMock) as close_cache:
        with TestClient(app) as running_client:
            assert running_client.get("/health/live").status_code == 200
        pool.close.assert_awaited_once()
        close_cache.assert_awaited_once()
