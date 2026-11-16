from datetime import datetime

import pytest

from src.utils.calculations import (
    calculate_discount,
    calculate_total,
    calculate_delivery_discount,
    calculate_delivery,
    Product,
    Order,
    create_products_catalog,
    find_product_fast,
    calculate_total_orders,
    sort_orders_by_date,
    group_orders_by_user,
    create_test_products,
    create_test_orders,
    benchmark_search,
    benchmark_sorting,
    benchmark_optimizations,
)


# Тесты расчетов

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
    (1000, 0, 0),
])
def test_calculate_total(price, quantity, expected):
    assert calculate_total(price, quantity) == expected


@pytest.mark.parametrize("order_total, delivery_cost, expected", [
    (4999, 400, 400),
    (5000, 400, 0),
    (12000, 700, 0),
])
def test_calculate_delivery_discount(
    order_total, delivery_cost, expected
):
    assert calculate_delivery_discount(
        order_total, delivery_cost
    ) == expected


@pytest.mark.parametrize("weight, distance, expected", [
    (1, 10, 160),
    (5, 50, 400),
    (10, 100, 700),
    (0, 0, 100),
])
def test_calculate_delivery(weight, distance, expected):
    assert calculate_delivery(weight, distance) == expected


# Фикстуры

@pytest.fixture
def sample_products():
    return [
        Product(1, "Монитор", 15000),
        Product(2, "Мышь", 1000),
        Product(3, "Клавиатура", 2000),
    ]


@pytest.fixture
def sample_orders():
    return [
        Order(1, datetime(2026, 1, 3), 1000, 1),
        Order(2, datetime(2026, 1, 1), 2000, 2),
        Order(3, datetime(2026, 1, 2), 3000, 1),
    ]


# Тесты каталога товаров

def test_create_products_catalog(sample_products):
    catalog = create_products_catalog(sample_products)

    assert len(catalog) == 3
    assert catalog[1].name == "Монитор"
    assert catalog[2].price == 1000


def test_create_empty_catalog():
    assert create_products_catalog([]) == {}


def test_find_product_fast(sample_products):
    catalog = create_products_catalog(sample_products)

    result = find_product_fast(catalog, 2)

    assert result.name == "Мышь"
    assert result.price == 1000


def test_find_missing_product(sample_products):
    catalog = create_products_catalog(sample_products)

    assert find_product_fast(catalog, 999) is None


# Тесты обработки заказов

def test_calculate_total_orders(sample_orders):
    assert calculate_total_orders(sample_orders) == 6000


def test_calculate_empty_orders():
    assert calculate_total_orders([]) == 0


def test_sort_orders_by_date(sample_orders):
    result = sort_orders_by_date(sample_orders)

    assert [order.id for order in result] == [2, 3, 1]


def test_sort_empty_orders():
    assert sort_orders_by_date([]) == []


def test_group_orders_by_user(sample_orders):
    result = group_orders_by_user(sample_orders)

    assert len(result) == 2
    assert [order.id for order in result[1]] == [1, 3]
    assert [order.id for order in result[2]] == [2]


def test_group_empty_orders():
    assert group_orders_by_user([]) == {}


# Тесты генерации данных

def test_create_test_products():
    products = create_test_products(3)

    assert len(products) == 3
    assert products[0].id == 0
    assert products[2].name == "Товар 2"
    assert products[2].price == 200


def test_create_test_orders():
    orders = create_test_orders(3)

    assert len(orders) == 3
    assert orders[0].created_at == datetime(2026, 1, 1)
    assert orders[2].created_at == datetime(2026, 1, 3)
    assert orders[2].total == 1200
    assert orders[0].user_id == 0


# Тесты бенчмарков

def test_benchmark_search():
    result = benchmark_search()

    assert "time_list" in result
    assert "time_dict" in result
    assert "speedup" in result
    assert result["time_list"] >= 0
    assert result["time_dict"] >= 0
    assert result["speedup"] >= 0


def test_benchmark_sorting():
    result = benchmark_sorting()

    assert "time_manual" in result
    assert "time_fast" in result
    assert "speedup" in result
    assert result["time_manual"] >= 0
    assert result["time_fast"] >= 0
    assert result["speedup"] >= 0


def test_benchmark_optimizations():
    result = benchmark_optimizations()

    assert "search" in result
    assert "sorting" in result
    assert "sum" in result

    assert result["sum"]["time_slow"] >= 0
    assert result["sum"]["time_fast"] >= 0
    assert result["sum"]["speedup"] >= 0


@pytest.mark.parametrize("age, expected", [(17, False), (18, True), (30, True)])
def test_validate_age(age, expected):
    from src.utils.validators import validate_age

    assert validate_age(age) is expected


@pytest.mark.parametrize("email, expected", [("test@example.com", True), ("invalid", False)])
def test_validate_email(email, expected):
    from src.utils.validators import validate_email

    assert validate_email(email) is expected
