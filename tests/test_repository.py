from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.database.async_repository import (
    ProductRepository,
    UserRepository,
    OrderRepository,
    OrderRecord,
    _row_to_dict,
    demo,
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
def pool():
    pool = MagicMock()
    pool.fetchrow = AsyncMock()
    pool.fetch = AsyncMock()
    pool.fetchval = AsyncMock()
    pool.execute = AsyncMock()
    pool.close = AsyncMock()
    return pool


@pytest.fixture
def product_repo(pool):
    return ProductRepository(pool)


@pytest.fixture
def user_repo(pool):
    return UserRepository(pool)


@pytest.fixture
def order_repo(pool):
    return OrderRepository(pool)


@pytest.fixture
def product_row():
    return {
        "id": 1,
        "name": "Клавиатура",
        "price": Decimal("2000.00"),
        "quantity": 5,
    }


@pytest.fixture
def user_row():
    return {
        "id": 1,
        "name": "Анна",
        "email": "anna@mail.ru",
        "password_hash": "test_hash",
    }


@pytest.fixture
def connection(pool):
    conn = MagicMock()
    conn.fetchrow = AsyncMock()
    conn.fetchval = AsyncMock()
    conn.execute = AsyncMock()

    pool.acquire.return_value.__aenter__ = AsyncMock(
        return_value=conn
    )
    pool.acquire.return_value.__aexit__ = AsyncMock(
        return_value=False
    )

    conn.transaction.return_value.__aenter__ = AsyncMock()
    conn.transaction.return_value.__aexit__ = AsyncMock(
        return_value=False
    )

    return conn


# Преобразование данных


def test_row_to_dict(product_row):
    result = _row_to_dict(product_row)

    assert result == {
        "id": 1,
        "name": "Клавиатура",
        "price": 2000.0,
        "quantity": 5,
    }
    assert isinstance(result["price"], float)


# ProductRepository


@pytest.mark.anyio
async def test_product_get_by_id(
    product_repo, pool, product_row
):
    pool.fetchrow.return_value = product_row

    result = await product_repo.get_by_id(1)

    assert result == _row_to_dict(product_row)

    pool.fetchrow.assert_awaited_once_with(
        "SELECT id, name, price, quantity FROM products WHERE id = $1",
        1,
    )


@pytest.mark.anyio
async def test_product_not_found(product_repo, pool):
    pool.fetchrow.return_value = None

    result = await product_repo.get_by_id(999)

    assert result is None


@pytest.mark.anyio
async def test_list_products(
    product_repo, pool, product_row
):
    pool.fetch.return_value = [product_row]

    result = await product_repo.list_products(
        limit=10,
        offset=5,
    )

    assert result == [_row_to_dict(product_row)]

    pool.fetch.assert_awaited_once_with(
        "SELECT id, name, price, quantity FROM products ORDER BY id LIMIT $1 OFFSET $2",
        10,
        5,
    )


@pytest.mark.anyio
async def test_list_products_empty(product_repo, pool):
    pool.fetch.return_value = []

    result = await product_repo.list_products()

    assert result == []


@pytest.mark.anyio
async def test_count_products(product_repo, pool):
    pool.fetchval.return_value = 15

    result = await product_repo.count()

    assert result == 15

    pool.fetchval.assert_awaited_once_with(
        "SELECT COUNT(*) FROM products"
    )


@pytest.mark.anyio
async def test_create_product(product_repo, pool):
    pool.fetchval.return_value = 10

    result = await product_repo.create(
        "Мышь", 1500.0, 3
    )

    assert result == 10

    pool.fetchval.assert_awaited_once_with(
        "INSERT INTO products (name, price, quantity) VALUES ($1, $2, $3) RETURNING id",
        "Мышь",
        1500.0,
        3,
    )


@pytest.mark.anyio
async def test_create_product_default_quantity(
    product_repo, pool
):
    pool.fetchval.return_value = 10

    result = await product_repo.create(
        "Мышь", 1500.0
    )

    assert result == 10
    assert pool.fetchval.call_args.args[-1] == 0


@pytest.mark.anyio
async def test_update_product(
    product_repo, pool, product_row
):
    updated_row = {
        **product_row,
        "price": Decimal("2500.00"),
        "quantity": 10,
    }

    pool.fetchrow.return_value = updated_row

    result = await product_repo.update(
        1,
        {
            "price": 2500.0,
            "quantity": 10,
        },
    )

    assert result["price"] == 2500.0
    assert result["quantity"] == 10

    pool.fetchrow.assert_awaited_once_with(
        "UPDATE products SET price = $1, quantity = $2 WHERE id = $3 "
        "RETURNING id, name, price, quantity",
        2500.0,
        10,
        1,
    )


@pytest.mark.anyio
async def test_update_ignores_forbidden_fields(
    product_repo, pool, product_row
):
    pool.fetchrow.return_value = product_row

    await product_repo.update(
        1,
        {
            "price": 2000.0,
            "id": 999,
            "unknown_field": "value",
        },
    )

    pool.fetchrow.assert_awaited_once_with(
        "UPDATE products SET price = $1 WHERE id = $2 "
        "RETURNING id, name, price, quantity",
        2000.0,
        1,
    )


@pytest.mark.anyio
@pytest.mark.parametrize("fields", [
    {},
    {"unknown_field": "value"},
])
async def test_update_without_allowed_fields(
    product_repo, pool, product_row, fields
):
    pool.fetchrow.return_value = product_row

    result = await product_repo.update(1, fields)

    assert result == _row_to_dict(product_row)

    pool.fetchrow.assert_awaited_once_with(
        "SELECT id, name, price, quantity FROM products WHERE id = $1",
        1,
    )


@pytest.mark.anyio
async def test_update_product_not_found(
    product_repo, pool
):
    pool.fetchrow.return_value = None

    result = await product_repo.update(
        999, {"price": 2500.0}
    )

    assert result is None


@pytest.mark.anyio
@pytest.mark.parametrize("status, expected", [
    ("UPDATE 1", True),
    ("UPDATE 0", False),
])
async def test_update_price(
    product_repo, pool, status, expected
):
    pool.execute.return_value = status

    result = await product_repo.update_price(
        1, 2500.0
    )

    assert result is expected

    pool.execute.assert_awaited_once_with(
        "UPDATE products SET price = $1 WHERE id = $2",
        2500.0,
        1,
    )


@pytest.mark.anyio
@pytest.mark.parametrize("status, expected", [
    ("DELETE 1", True),
    ("DELETE 0", False),
])
async def test_delete_product(
    product_repo, pool, status, expected
):
    pool.execute.return_value = status

    result = await product_repo.delete(1)

    assert result is expected

    pool.execute.assert_awaited_once_with(
        "DELETE FROM products WHERE id = $1",
        1,
    )


# UserRepository


@pytest.mark.anyio
async def test_create_user(user_repo, pool):
    pool.fetchval.return_value = 1

    result = await user_repo.create(
        "Анна",
        "anna@mail.ru",
        "test_hash",
    )

    assert result == 1

    pool.fetchval.assert_awaited_once_with(
        "INSERT INTO users (name, email, password_hash) VALUES ($1, $2, $3) RETURNING id",
        "Анна",
        "anna@mail.ru",
        "test_hash",
    )


@pytest.mark.anyio
async def test_user_get_by_email(
    user_repo, pool, user_row
):
    pool.fetchrow.return_value = user_row

    result = await user_repo.get_by_email(
        "anna@mail.ru"
    )

    assert result == user_row

    pool.fetchrow.assert_awaited_once_with(
        "SELECT id, name, email, password_hash FROM users WHERE email = $1",
        "anna@mail.ru",
    )


@pytest.mark.anyio
async def test_user_email_not_found(user_repo, pool):
    pool.fetchrow.return_value = None

    result = await user_repo.get_by_email(
        "unknown@mail.ru"
    )

    assert result is None


@pytest.mark.anyio
async def test_user_get_by_id(
    user_repo, pool, user_row
):
    public_user = {
        key: value
        for key, value in user_row.items()
        if key != "password_hash"
    }

    pool.fetchrow.return_value = public_user

    result = await user_repo.get_by_id(1)

    assert result == public_user
    assert "password_hash" not in result

    pool.fetchrow.assert_awaited_once_with(
        "SELECT id, name, email FROM users WHERE id = $1",
        1,
    )


@pytest.mark.anyio
async def test_user_id_not_found(user_repo, pool):
    pool.fetchrow.return_value = None

    result = await user_repo.get_by_id(999)

    assert result is None


# OrderRepository


@pytest.mark.anyio
async def test_order_get_by_id(order_repo, pool):
    pool.fetchrow.return_value = {
        "id": 5,
        "user_id": 1,
        "total": Decimal("4000.00"),
        "status": "created",
    }

    result = await order_repo.get_by_id(5)

    assert result == OrderRecord(
        id=5,
        user_id=1,
        total=4000.0,
        status="created",
    )

    assert isinstance(result.total, float)

    pool.fetchrow.assert_awaited_once_with(
        "SELECT id, user_id, total, status FROM orders WHERE id = $1",
        5,
    )


@pytest.mark.anyio
async def test_order_not_found(order_repo, pool):
    pool.fetchrow.return_value = None

    result = await order_repo.get_by_id(999)

    assert result is None


@pytest.mark.anyio
async def test_list_orders_by_user(order_repo, pool):
    pool.fetch.return_value = [
        {
            "id": 5,
            "total": Decimal("4000.00"),
            "status": "created",
            "created_at": "2026-11-16",
        }
    ]

    result = await order_repo.list_by_user(1)

    assert len(result) == 1
    assert result[0]["total"] == 4000.0
    assert result[0]["status"] == "created"

    pool.fetch.assert_awaited_once_with(
        "SELECT id, total, status, created_at FROM orders WHERE user_id = $1 ORDER BY id DESC",
        1,
    )


@pytest.mark.anyio
async def test_list_orders_empty(order_repo, pool):
    pool.fetch.return_value = []

    result = await order_repo.list_by_user(1)

    assert result == []


@pytest.mark.anyio
async def test_create_order(
    order_repo, pool, connection
):
    connection.fetchrow.return_value = {
        "price": Decimal("2000.00"),
        "quantity": 5,
    }

    connection.fetchval.return_value = 10

    result = await order_repo.create(
        user_id=1,
        items=[
            {"product_id": 2, "quantity": 2},
        ],
    )

    assert result == OrderRecord(
        id=10,
        user_id=1,
        total=4000.0,
        status="created",
    )

    pool.acquire.assert_called_once()
    connection.transaction.assert_called_once()

    connection.fetchrow.assert_awaited_once_with(
        "SELECT price, quantity FROM products WHERE id = $1 FOR UPDATE",
        2,
    )

    connection.fetchval.assert_awaited_once_with(
        "INSERT INTO orders (user_id, total, status) VALUES ($1, $2, 'created') RETURNING id",
        1,
        Decimal("4000.00"),
    )

    assert connection.execute.await_count == 2

    connection.execute.assert_any_await(
        "UPDATE products SET quantity = quantity - $1 WHERE id = $2",
        2,
        2,
    )

    connection.execute.assert_any_await(
        "INSERT INTO order_items (order_id, product_id, quantity) VALUES ($1, $2, $3)",
        10,
        2,
        2,
    )

    connection.transaction.return_value.__aexit__.assert_awaited_once_with(
        None, None, None
    )


@pytest.mark.anyio
async def test_create_order_multiple_products(
    order_repo, connection
):
    connection.fetchrow.side_effect = [
        {
            "price": Decimal("1000.00"),
            "quantity": 5,
        },
        {
            "price": Decimal("500.00"),
            "quantity": 10,
        },
    ]

    connection.fetchval.return_value = 11

    result = await order_repo.create(
        user_id=1,
        items=[
            {"product_id": 2, "quantity": 2},
            {"product_id": 3, "quantity": 3},
        ],
    )

    assert result.total == 3500.0
    assert result.id == 11
    assert connection.fetchrow.await_count == 2
    assert connection.execute.await_count == 4


@pytest.mark.anyio
async def test_create_order_product_not_found(
    order_repo, connection
):
    connection.fetchrow.return_value = None

    with pytest.raises(
        LookupError,
        match="Товар 999 не найден",
    ):
        await order_repo.create(
            user_id=1,
            items=[
                {"product_id": 999, "quantity": 1},
            ],
        )

    connection.execute.assert_not_awaited()
    connection.fetchval.assert_not_awaited()

    transaction = connection.transaction.return_value

    assert transaction.__aexit__.await_args.args[0] is LookupError


@pytest.mark.anyio
async def test_create_order_insufficient_stock(
    order_repo, connection
):
    connection.fetchrow.return_value = {
        "price": Decimal("2000.00"),
        "quantity": 1,
    }

    with pytest.raises(
        ValueError,
        match="недостаточно на складе",
    ):
        await order_repo.create(
            user_id=1,
            items=[
                {"product_id": 2, "quantity": 5},
            ],
        )

    connection.execute.assert_not_awaited()
    connection.fetchval.assert_not_awaited()

    transaction = connection.transaction.return_value

    assert transaction.__aexit__.await_args.args[0] is ValueError


@pytest.mark.anyio
async def test_create_order_error_after_first_product(
    order_repo, connection
):
    connection.fetchrow.side_effect = [
        {
            "price": Decimal("1000.00"),
            "quantity": 5,
        },
        None,
    ]

    with pytest.raises(LookupError):
        await order_repo.create(
            user_id=1,
            items=[
                {"product_id": 2, "quantity": 1},
                {"product_id": 999, "quantity": 1},
            ],
        )

    assert connection.execute.await_count == 1
    connection.fetchval.assert_not_awaited()

    transaction = connection.transaction.return_value

    assert transaction.__aexit__.await_args.args[0] is LookupError


# Демонстрационная функция


@pytest.mark.anyio
async def test_repository_demo(pool, product_row):
    pool.fetchval.return_value = 1
    pool.fetchrow.return_value = product_row
    pool.fetch.return_value = [product_row]

    pool.execute.side_effect = [
        "UPDATE 1",
        "DELETE 1",
    ]

    with patch(
        "src.database.async_repository.asyncpg.create_pool",
        new_callable=AsyncMock,
        return_value=pool,
    ):
        await demo()

    pool.close.assert_awaited_once()


@pytest.mark.anyio
async def test_repository_demo_closes_pool_on_error(pool):
    pool.fetchval.side_effect = RuntimeError(
        "Database error"
    )

    with patch(
        "src.database.async_repository.asyncpg.create_pool",
        new_callable=AsyncMock,
        return_value=pool,
    ):
        with pytest.raises(RuntimeError):
            await demo()

    pool.close.assert_awaited_once()
