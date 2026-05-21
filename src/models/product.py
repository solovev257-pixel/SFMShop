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
