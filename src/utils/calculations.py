# def calculate_discount(price, discount_rate):
#     return price * discount_rate
#
# def calculate_delivery(weight, base_cost=100):
#     return base_cost + weight * 10
#
# def calculate_final_price(price, discount, delivery):
#     return price - discount + delivery
#
# import time
#
# class Product:
#     def __init__(self, id, name, price):
#         self.id = id
#         self.name = name
#         self.price = price
#
# def find_product_in_list(products, product_id):
#     for product in products:
#          if product.id == product_id:
#             return product
#     return None
#
# def create_products_index(products):
#     return {product.id: product for product in products}
#
# def find_product_in_dict(products_dict, product_id):
#     return products_dict.get(product_id)
#
# def benchmark_search(products, product_id, repeats=100000):
#     start_time = time.perf_counter()
#     for _ in range(repeats):
#         result_list = find_product_in_list(products, product_id)
#     time_list = (time.perf_counter() - start_time) / repeats
#
#     products_dict = create_products_index(products)
#     start_time = time.perf_counter()
#     for _ in range(repeats):
#         result_dict = find_product_in_dict(products_dict, product_id)
#     time_dict = (time.perf_counter() - start_time) / repeats
#
#     speedup = time_list / time_dict
#     print(f"Поиск в списке: {time_list:.9f} секунд")
#     print(f"Поиск в словаре: {time_dict:.9f} секунд")
#     print(f"Ускорение: {speedup:.2f}x")
#     print(f"Результаты совпадают: {result_list == result_dict}")
#
# if __name__ == "__main__":
#     products = [Product(i, f"Товар {i}", i * 100) for i in range(10000)]
#     product_id = 5000
#     benchmark_search(products, product_id)

# подключаем модуль time чтобы замерять скорость функции
import time

# создаем шаблон товара с параметрами  id, name, price
class Product:
    def __init__(self, id, name, price):
        self.id = id
        self.name = name
        self.price = price

# создаем шаблон для заказа с параметрами id, created_at, total, user_id=0(значение по умолчанию)
class Order:
    def __init__(self, id, created_at, total, user_id=0):
        self.id = id
        self.created_at = created_at
        self.total = total
        self.user_id = user_id

# превращаем список товаров в словарь
def create_products_catalog(products):
    return {product.id: product for product in products}

# ищем товар в словаре по ID.
def find_product_fast(products_dict, product_id):
    return products_dict.get(product_id)

# считаем общую сумму всех заказов
def calculate_total_orders(orders):
    return sum(order.total for order in orders)

# сортируем заказы по дате создания
def sort_orders_by_date(orders):
    return sorted(orders, key=lambda x: x.created_at)

# группируем заказы по пользователям
def group_orders_by_user(orders):
    grouped = {}
    for order in orders:
        user_id = order.user_id
        if user_id not in grouped:
            grouped[user_id] = []
        grouped[user_id].append(order)
    return grouped

# создаем список тестовых товаров для бэнчмарка
def create_test_products(count):
    return [Product(i, f"Товар {i}", i * 100) for i in range(count)]

# создаем список тестовых заказов для бенчмарка
def create_test_orders(count):
    from datetime import datetime, timedelta # подключаем инструмент для работы с датами
    base_date = datetime(2026, 1, 1)
    return [
        Order(i, base_date + timedelta(days=i % 365), 1000 + i * 100)
        for i in range(count)
    ]

# измеряем скорость поиска в списке и словаре
def benchmark_search():
    products = create_test_products(1000)
    product_id = 500

    # замеряем медленный поиск в списке
    start_time = time.time()
    result_list = None
    for product in products:
        if product.id == product_id:
            result_list = product
            break
    time_list = time.time() - start_time

    # измеряем быстрый поиск в словаре
    products_dict = create_products_catalog(products)
    start_time = time.time()
    result_dict = products_dict.get(product_id)
    time_dict = time.time() - start_time

    # считаем ускорение и выводим результаты
    speedup = time_list / time_dict if time_dict > 0 else 0

    print("=== Тест поиска товара ===")
    print(f"Поиск в списке: {time_list:.6f} сек")
    print(f"Поиск в словаре: {time_dict:.6f} сек")
    print(f"Ускорение: {speedup:.2f}x")
    print()

    return {
        "time_list": time_list,
        "time_dict": time_dict,
        "speedup": speedup
    }

# измеряем производительность сортировки
def benchmark_sorting():
    import random
    orders = create_test_orders(1000)
    random.shuffle(orders)

    # Ручная сортировка (медленная, O(n²))
    def bubble_sort(items):
        items = items.copy()
        n = len(items)
        for i in range(n):
            for j in range(0, n - i - 1):
                if items[j].created_at > items[j + 1].created_at:
                    items[j], items[j + 1] = items[j + 1], items[j]
        return items

    start_time = time.time()
    sorted_manual = bubble_sort(orders)
    time_manual = time.time() - start_time

    # Сортировка через sorted() (быстрая, O(n log n))
    start_time = time.time()
    sorted_fast = sort_orders_by_date(orders)
    time_fast = time.time() - start_time
    speedup = time_manual / time_fast if time_fast > 0 else 0

    # вывод результатов
    print("=== Тест сортировки заказов ===")
    print(f"Ручная сортировка: {time_manual:.4f} сек")
    print(f"Сортировка через sorted(): {time_fast:.4f} сек")
    print(f"Ускорение: {speedup:.2f}x")
    print()

    return {
        "time_manual": time_manual,
        "time_fast": time_fast,
        "speedup": speedup
    }


# функция которая запускает все тесты и выводит результат
def benchmark_optimizations():
    print("=" * 50)
    print("БЕНЧМАРК ОПТИМИЗАЦИЙ")
    print("=" * 50)
    print()

    # запускаем все тесты и сохраняем результаты
    results = {}
    results["search"] = benchmark_search()
    results["sorting"] = benchmark_sorting()

    # сравниваем медленный цикл и быстрый с генератором
    orders = create_test_orders(10000)

    start_time = time.time()
    total_slow = 0
    for order in orders:
        total_slow += order.total
    time_slow = time.time() - start_time

    start_time = time.time()
    total_fast = calculate_total_orders(orders)
    time_fast = time.time() - start_time
    speedup = time_slow / time_fast if time_fast > 0 else 0

    # вывод результатов
    print("=== Тест расчета суммы заказов ===")
    print(f"Цикл: {time_slow:.6f} сек")
    print(f"sum() с генератором: {time_fast:.6f} сек")
    print(f"Ускорение: {speedup:.2f}x")
    print()

    results["sum"] = {
        "time_slow": time_slow,
        "time_fast": time_fast,
        "speedup": speedup
    }

    print("=" * 50)
    print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ")
    print("=" * 50)
    for test_name, metrics in results.items():
        if "speedup" in metrics:
            print(f"{test_name}: ускорение {metrics['speedup']:.2f}x")

    return results


if __name__ == "__main__":
    benchmark_optimizations()