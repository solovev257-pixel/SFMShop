from src.models.exceptions import NegativePriceError, InsufficientStockError, SFMShopException


class Product:

    def __init__(self, name, price, quantity):
        self.name = name
        if price < 0:
            raise NegativePriceError('Цена не может быть отрицательной')
        self.price = price
        self.quantity = quantity

    def sell(self, amount):
        if self.quantity < amount:
            raise InsufficientStockError(f'Товара недостаточно. На складе: {self.quantity}, требуется: {amount}')
        self.quantity = self.quantity - amount

    def apply_discount(self, percent):
        self.price = self.price * (1 - percent / 100)
        return self.price


def apply_discount(self, percent):
    self.price = self.price * (1 - percent / 100)
    return self.price

def get_total_price(self):
    return self.price * self.quantity

def calculate_shipping(self):
    if self.quantity > 10:
        return 0
    return 250

def get_category(self):
    if self.price > 1000:
        return "премиум"
    return "стандарт"

def get_weight(self):
    return self.quantity * 0.5
