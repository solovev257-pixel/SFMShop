# from src.models.exceptions import NegativePriceError, InsufficientStockError, SFMShopException
#
#
# class Product:
#
#     def __init__(self, name, price, quantity):
#         self.name = name
#         if price < 0:
#             raise NegativePriceError('Цена не может быть отрицательной')
#         self.price = price
#         self.quantity = quantity
#
#     def sell(self, amount):
#         if self.quantity < amount:
#             raise InsufficientStockError(f'Товара недостаточно. На складе: {self.quantity}, требуется: {amount}')
#         self.quantity = self.quantity - amount
#
#     def apply_discount(self, percent):
#         self.price = self.price * (1 - percent / 100)
#         return self.price
#
#
# def apply_discount(self, percent):
#     self.price = self.price * (1 - percent / 100)
#     return self.price
#
# def get_total_price(self):
#     return self.price * self.quantity
#
# def calculate_shipping(self):
#     if self.quantity > 10:
#         return 0
#     return 250
#
# def get_weight(self):
#     return self.quantity * 0.5

# from dataclasses import dataclass
#
# @dataclass
#
# class Product:
#     name: str
#     price: float
#     quantity: int = 0
#
#     def __post_init__(self):
#         if self.price < 0:
#             raise ValueError("Цена не может быть отрицательной")
#         if self.quantity < 0:
#             raise ValueError("Количество не может быть отрицательным")
#
#     @classmethod
#     def from_dict(cls, data):
#         return cls(
#             name=data["name"],
#             price=data["price"],
#             quantity=data["quantity"]
#                 )
#
#     @staticmethod
#     def calculate_discount(price, discount_percent):
#         return price * (1 - discount_percent / 100)
#
# product1 = Product("Ноутбук", 1000, 10)
# print(product1)
# data = {"name": "Мышь", "price": 500, "quantity": 20}
# product2 = Product.from_dict(data)
# print(product2)
# result = Product.calculate_discount(1000, 10)
# print(result)

# from src.models.mixins import LoggableMixin, ValidatableMixin, SerializableMixin
#
# class Product(LoggableMixin, ValidatableMixin, SerializableMixin):
#     def __init__(self, name, price, quantity):
#         self.name = name
#         self.price = price
#         self.quantity = quantity
#         self.log(f"Создан товар: {name}")
#
#     def validate(self):
#         if self.price < 0:
#             raise ValueError('цена не отрицательная')
#         if self.quantity < 0:
#             raise ValueError('Количество должно быть положитиельное')
#         return True

# from abc import ABC, abstractmethod
#
#
# class DiscountStrategy(ABC):
#     @abstractmethod
#     def apply(self, price: float) -> float:
#         pass
#
#
# class PercentDiscount(DiscountStrategy):
#     def __init__(self, percent: float):
#         self.percent = percent
#
#     def apply(self, price: float) -> float:
#         return price * (1 - self.percent / 100)
#
#
# class FixedDiscount(DiscountStrategy):
#     def __init__(self, amount: float):
#         self.amount = amount
#
#     def apply(self, price: float) -> float:
#         return max(0, price - self.amount)
#
#
# class Product:
#     def __init__(self, name: str, price: float):
#         self.name = name
#         self.price = price
#
#     def calculate_price(self, discount: DiscountStrategy = None) -> float:
#         if discount is None:
#             return self.price
#         return discount.apply(self.price)
#
#
# product = Product('Ноутбук', 1000)
# percent_discount = PercentDiscount(10)
# fixed_discount = FixedDiscount(100)
# print(product.calculate_price())
# print(product.calculate_price(percent_discount))
# print(product.calculate_price(fixed_discount))
#
#
# class SeasonalDiscount(DiscountStrategy):
#     def __init__(self, percent: float):
#         self.percent = percent
#
#     def apply(self, price: float) -> float:
#         return price * (1 - self.percent / 100)
#
# seasonal_discount = SeasonalDiscount(15)
# print(product.calculate_price(seasonal_discount))

# from src.models.metaclasses import ModelMeta
#
# class Product(metaclass = ModelMeta):
#     def __init__(self, name, price, quantity):
#         self.name = name
#         self.price = price
#         self.quantity = quantity

from src.models.descriptors import PositiveNumber, CachedProperty


class Product:
    price = PositiveNumber("_price")
    quantity = PositiveNumber("_quantity")

    def __init__(self, name, price, quantity):
        self.name = name
        self.price = price
        self.quantity = quantity

    @CachedProperty
    def total_value(self):
        print("Вычисление total_value...")
        return self.price * self.quantity

product = Product("Ноутбук", 1000, 10)
print(product.total_value)
print(product.total_value)