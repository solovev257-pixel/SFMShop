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
