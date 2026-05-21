class SFMShopException(Exception):
    """Базовое исключение для проекта SFMShop"""


class InsufficientStockError(SFMShopException):
    """Товара недостаточно на складе"""


class InvalidOrderError(SFMShopException):
    """Заказ невалиден"""


class NegativePriceError(Exception):
    """Цена не может быть отрицательной"""


class ValidationError(SFMShopException):
    """Ошибка валидации данных"""


class BusinessLogicError(SFMShopException):
    """Ошибка бизнес-логики"""


class DatabaseError(SFMShopException):
    """Ошибка базы данных"""
