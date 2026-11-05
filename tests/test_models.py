from src.models.order import Order
from src.models.user import User
from src.models.product import Product


def test_create_order():
    buyer = User(1, "Пётр", "petr@mail.ru", 30, 5000)
    items = [Product("Монитор", 15000, 1)]
    order = Order(7, items, buyer)

    assert order.order_id == 7
    assert order.user.name == "Пётр"
    assert len(order.items) == 1
    assert order.items[0].name == "Монитор"


def test_calculate_total():
    buyer = User(1, "Пётр", "petr@mail.ru", 30, 5000)
    items = [
        Product("Наушники", 1000, 2),
        Product("Коврик", 500, 1),
    ]
    order = Order(8, items, buyer)

    assert order.calculate_total() == 2500


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


def test_create_product(sample_product):
    assert sample_product.name == "Клавиатура"
    assert sample_product.price == 2000
    assert sample_product.quantity == 3


def test_product_negative_price():
    with pytest.raises(ValueError):
        Product("Сломанный товар", -100, 1)


def test_create_user(sample_user):
    assert sample_user.name == "Анна"
    assert sample_user.email == "anna@mail.ru"
    assert sample_user.is_active is True


def test_user_bad_email():
    with pytest.raises(ValueError):
        User(2, "Олег", "oleg.mail.ru", 30, 100)


def test_user_to_json(sample_user):
    data = sample_user.to_json()
    assert data["name"] == "Анна"
    assert data["orders_count"] == 0


def test_create_order(sample_order, sample_user):
    assert sample_order.order_id == 1
    assert sample_order.user.name == sample_user.name
    assert len(sample_order) == 1


def test_order_contains(sample_order, sample_product):
    assert sample_product in sample_order


def test_calculate_total():
    buyer = User(3, "Пётр", "petr@mail.ru", 30, 5000)
    items = [
        Product("Наушники", 1000, 2),
        Product("Коврик", 500, 1),
    ]
    order = Order(8, items, buyer)
    assert order.calculate_total() == 2500