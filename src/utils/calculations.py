def calculate_discount(price, discount_rate):
    return price * discount_rate

def calculate_delivery(weight, base_cost=100):
    return base_cost + weight * 10

def calculate_final_price(price, discount, delivery):
    return price - discount + delivery

import time

class Product:
    def __init__(self, id, name, price):
        self.id = id
        self.name = name
        self.price = price

def find_product_in_list(products, product_id):
    for product in products:
         if product.id == product_id:
            return product
    return None

def create_products_index(products):
    return {product.id: product for product in products}

def find_product_in_dict(products_dict, product_id):
    return products_dict.get(product_id)

def benchmark_search(products, product_id, repeats=100000):
    start_time = time.perf_counter()
    for _ in range(repeats):
        result_list = find_product_in_list(products, product_id)
    time_list = (time.perf_counter() - start_time) / repeats

    products_dict = create_products_index(products)
    start_time = time.perf_counter()
    for _ in range(repeats):
        result_dict = find_product_in_dict(products_dict, product_id)
    time_dict = (time.perf_counter() - start_time) / repeats

    speedup = time_list / time_dict
    print(f"Поиск в списке: {time_list:.9f} секунд")
    print(f"Поиск в словаре: {time_dict:.9f} секунд")
    print(f"Ускорение: {speedup:.2f}x")
    print(f"Результаты совпадают: {result_list == result_dict}")

if __name__ == "__main__":
    products = [Product(i, f"Товар {i}", i * 100) for i in range(10000)]
    product_id = 5000
    benchmark_search(products, product_id)