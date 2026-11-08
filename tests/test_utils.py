import pytest

from src.utils.calculations import calculate_discount, calculate_total, calculate_delivery_discount, calculate_delivery


@pytest.mark.parametrize("price, rate, expected", [
    (500, 0, 0),
    (2000, 0.05, 100),
    (6000, 0.1, 600),
    (20000, 0.15, 3000),
])
def test_calculate_discount(price, rate, expected):
    assert calculate_discount(price, rate) == expected


@pytest.mark.parametrize("price, quantity, expected", [
    (1000, 2, 2000),
    (750, 4, 3000),
    (50000, 1, 50000),
])
def test_calculate_total(price, quantity, expected):
    assert calculate_total(price, quantity) == expected


@pytest.mark.parametrize("order_total, delivery_cost, expected", [
    (4999, 400, 400),
    (5000, 400, 0),
    (12000, 700, 0),
])
def test_calculate_delivery_discount(order_total, delivery_cost, expected):
    assert calculate_delivery_discount(order_total, delivery_cost) == expected


@pytest.mark.parametrize("weight, distance, expected", [
    (1, 10, 160),
    (5, 50, 400),
    (10, 100, 700),
])
def test_calculate_delivery(weight, distance, expected):
    assert calculate_delivery(weight, distance) == expected

