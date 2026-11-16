import json

import pytest

from src.models.order import Order
from src.models.user import User
from src.models.product import Product


@pytest.fixture
def sample_product():
    return Product("Клавиатура", 2000, 3)


@pytest.fixture
def sample_user():
    return User(1, "Анна", "anna@mail.ru", 25, 3000)


@pytest.fixture
def sample_order(sample_user, sample_product):
    return Order(1, [sample_product], sample_user)


# Тесты Product

def test_create_product(sample_product):
    assert sample_product.name == "Клавиатура"
    assert sample_product.price == 2000
    assert sample_product.quantity == 3


@pytest.mark.parametrize("price", [-100, -1, -5000])
def test_product_negative_price(price):
    with pytest.raises(ValueError):
        Product("Товар", price, 1)


# Тесты User

def test_create_user(sample_user):
    assert sample_user.name == "Анна"
    assert sample_user.email == "anna@mail.ru"
    assert sample_user.is_active is True


@pytest.mark.parametrize("email", [
    "oleg.mail.ru",
    "invalid",
    "",
])
def test_user_bad_email(email):
    with pytest.raises(ValueError):
        User(2, "Олег", email, 30, 100)


def test_user_to_json(sample_user):
    data = sample_user.to_json()

    assert data["name"] == "Анна"
    assert data["orders_count"] == 0


# Тесты Order

def test_create_order(sample_order, sample_user):
    assert sample_order.order_id == 1
    assert sample_order.user.name == sample_user.name
    assert len(sample_order) == 1
    assert sample_order.items[0].name == "Клавиатура"


def test_order_contains(sample_order, sample_product):
    assert sample_product in sample_order


def test_order_not_contains(sample_order):
    another_product = Product("Мышь", 1000, 1)

    assert another_product not in sample_order


@pytest.mark.parametrize("price, quantity, expected", [
    (1000, 2, 2000),
    (500, 3, 1500),
    (2000, 1, 2000),
])
def test_calculate_total(sample_user, price, quantity, expected):
    items = [Product("Товар", price, quantity)]
    order = Order(8, items, sample_user)

    assert order.calculate_total() == expected


def test_calculate_total_multiple_products(sample_user):
    items = [
        Product("Наушники", 1000, 2),
        Product("Коврик", 500, 1),
    ]
    order = Order(8, items, sample_user)

    assert order.calculate_total() == 2500


def test_order_add_preserves_user_and_original_items(sample_user, sample_product):
    left = Order(1, [sample_product], sample_user)
    right = Order(2, [sample_product], sample_user)

    combined = left + right

    assert combined.user is sample_user
    assert combined.order_id == left.order_id
    assert combined.calculate_total() == 12000
    assert len(combined) == 2
    assert len(left) == len(right) == 1
    assert combined.items is not left.items


def test_product_total_value_is_cached(sample_product):
    assert sample_product.total_value == 6000
    sample_product.price = 1000
    assert sample_product.total_value == 6000
    assert Product.total_value.name == "total_value"


@pytest.mark.parametrize("field, value", [("quantity", -1), ("price", -1)])
def test_product_rejects_negative_updates(sample_product, field, value):
    with pytest.raises(ValueError):
        setattr(sample_product, field, value)


@pytest.mark.parametrize("field, value", [("age", 17), ("balance", -1), ("user_id", -1)])
def test_user_rejects_invalid_updates(sample_user, field, value):
    with pytest.raises(ValueError):
        setattr(sample_user, field, value)


def test_product_serialization(sample_product):
    data = json.loads(sample_product.to_json())
    assert data["class"] == "Product"
    assert data["data"]["name"] == "Клавиатура"
    assert data["data"]["_price"] == 2000


def test_orders_compare_by_id(sample_user):
    assert Order(1, [], sample_user) < Order(2, [], sample_user)
    assert not Order(2, [], sample_user) < Order(1, [], sample_user)


def test_cart_addition_keeps_original(sample_product):
    from src.models.cart import ShoppingCart

    original = ShoppingCart()
    updated = original + sample_product
    assert len(original) == 0
    assert len(updated) == 1
    assert list(updated) == [sample_product]
    assert list(updated) == list(updated)
    assert str(updated) == "Корзина: 1 товаров"


@pytest.mark.parametrize("strategy, expected", [("StandardDelivery", 100), ("ExpressDelivery", 200)])
def test_delivery_strategies(strategy, expected):
    from src.models import delivery_strategy

    assert getattr(delivery_strategy, strategy)().calculate_cost(10) == expected


def test_card_payment(capsys):
    from src.models.payment import CardPayment

    payment = CardPayment(100)
    assert payment.process() is True
    assert "Обработка платежа" in capsys.readouterr().out


def test_order_factory_validates_input(sample_user, sample_product):
    from src.models.order_factory import OrderFactory

    order = OrderFactory.create_order_from_dict({
        "order_id": 10, "items": [sample_product], "user": sample_user,
    })
    assert order.user is sample_user
    assert order.calculate_total() == 6000
    with pytest.raises(ValueError, match="пустым"):
        OrderFactory.create_order(10, [], sample_user)
    with pytest.raises(ValueError, match="пользователя"):
        OrderFactory.create_order(10, [sample_product], None)
