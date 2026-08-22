from abc import ABC, abstractmethod


class DiscountStrategy(ABC):
    @abstractmethod
    def apply(self, price):
        pass


class PercentDiscount(DiscountStrategy):
    def __init__(self, percent):
        self.percent = percent

    def apply(self, price):
        return price * (1 - self.percent / 100)


class OrderCalculator:
    @staticmethod
    def calculate_total(order):
        total = 0
        for item in order.items:
            total += item.price * item.quantity
        return total

    @staticmethod
    def apply_discount(order, discount):
        total = OrderCalculator.calculate_total(order)
        new_total = discount.apply(total)
        return new_total