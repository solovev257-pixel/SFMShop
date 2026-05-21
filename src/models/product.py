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

# Обновлён класс Product
# Тестовое изменение для stash

def apply_discount(self, percent):
    self.price = self.price * (1 - percent / 100)
    return self.price