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