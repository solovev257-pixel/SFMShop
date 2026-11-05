import pytest

from src.utils.calculations import calculate_discount, calculate_total


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