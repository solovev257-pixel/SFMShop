from datetime import datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.database import queries


@pytest.fixture
def session():
    with patch(
        "src.database.queries.get_session"
    ) as mock_get_session:
        yield mock_get_session.return_value


@pytest.fixture
def cursor():
    with patch(
        "src.database.queries.get_connection"
    ) as mock_get_connection:

        conn = mock_get_connection.return_value.__enter__.return_value
        cur = conn.cursor.return_value.__enter__.return_value

        yield cur


@pytest.fixture
def sample_order():
    return SimpleNamespace(
        id=5,
        total=Decimal("2000.00"),
        created_at=datetime(2026, 11, 16, 12, 0),
        user=SimpleNamespace(
            name="Анна",
            email="anna@mail.ru",
        ),
    )


@pytest.fixture
def product_row():
    return (
        1,
        "Клавиатура",
        Decimal("2000.00"),
        5,
    )


# Получение заказов пользователя


def test_get_user_orders(session, sample_order):
    user = SimpleNamespace(
        orders=[sample_order]
    )

    session.execute.return_value.unique.return_value.scalar_one_or_none.return_value = user

    result = queries.get_user_orders(1)

    assert result == [
        {
            "id": 5,
            "total": 2000.0,
            "created_at": "2026-11-16T12:00:00",
        }
    ]

    session.execute.assert_called_once()
    session.close.assert_called_once()


def test_get_user_orders_user_not_found(session):
    session.execute.return_value.unique.return_value.scalar_one_or_none.return_value = None

    result = queries.get_user_orders(999)

    assert result == []
    session.close.assert_called_once()


def test_get_user_orders_empty(session):
    user = SimpleNamespace(orders=[])

    session.execute.return_value.unique.return_value.scalar_one_or_none.return_value = user

    result = queries.get_user_orders(1)

    assert result == []
    session.close.assert_called_once()


def test_get_user_orders_closes_session_on_error(session):
    session.execute.side_effect = RuntimeError(
        "Database error"
    )

    with pytest.raises(RuntimeError):
        queries.get_user_orders(1)

    session.close.assert_called_once()


# Создание заказа


def test_create_order(session):
    def assign_id(order):
        order.id = 10

    session.add.side_effect = assign_id

    result = queries.create_order(
        user_id=1,
        total=2000.0,
    )

    assert result == 10

    order = session.add.call_args.args[0]

    assert order.user_id == 1
    assert order.total == 2000.0

    session.commit.assert_called_once()
    session.rollback.assert_not_called()
    session.close.assert_called_once()


def test_create_order_rollback(session):
    session.commit.side_effect = RuntimeError(
        "Commit failed"
    )

    with pytest.raises(
        RuntimeError,
        match="Commit failed",
    ):
        queries.create_order(
            user_id=1,
            total=2000.0,
        )

    session.rollback.assert_called_once()
    session.close.assert_called_once()


# Получение заказов с пользователями


def test_get_all_orders_with_users(
    session, sample_order
):
    session.execute.return_value.scalars.return_value.unique.return_value.all.return_value = [
        sample_order
    ]

    result = queries.get_all_orders_with_users()

    assert result == [
        {
            "id": 5,
            "total": 2000.0,
            "user_name": "Анна",
            "user_email": "anna@mail.ru",
        }
    ]

    session.execute.assert_called_once()
    session.close.assert_called_once()


def test_get_all_orders_with_users_empty(session):
    session.execute.return_value.scalars.return_value.unique.return_value.all.return_value = []

    result = queries.get_all_orders_with_users()

    assert result == []
    session.close.assert_called_once()


def test_get_all_orders_with_users_error(session):
    session.execute.side_effect = RuntimeError(
        "Database error"
    )

    with pytest.raises(RuntimeError):
        queries.get_all_orders_with_users()

    session.close.assert_called_once()


# Получение всех товаров


def test_get_all_products_from_db(
    cursor, product_row
):
    cursor.fetchall.return_value = [product_row]

    result = queries.get_all_products_from_db()

    assert result == [
        {
            "id": 1,
            "name": "Клавиатура",
            "price": 2000.0,
            "quantity": 5,
        }
    ]

    cursor.execute.assert_called_once_with(
        "SELECT id, name, price, quantity FROM products"
    )


def test_get_all_products_empty(cursor):
    cursor.fetchall.return_value = []

    result = queries.get_all_products_from_db()

    assert result == []


# Получение товара по ID


def test_get_product_by_id_from_db(
    cursor, product_row
):
    cursor.fetchone.return_value = product_row

    result = queries.get_product_by_id_from_db(1)

    assert result == {
        "id": 1,
        "name": "Клавиатура",
        "price": 2000.0,
        "quantity": 5,
    }

    cursor.execute.assert_called_once_with(
        "SELECT id, name, price, quantity FROM products WHERE id = %s",
        (1,),
    )


def test_get_product_by_id_not_found(cursor):
    cursor.fetchone.return_value = None

    result = queries.get_product_by_id_from_db(999)

    assert result is None