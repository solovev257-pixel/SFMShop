from src.models.order import Order
from src.services.order_validator import OrderValidator


class OrderFactory:
    @staticmethod
    def create_order(order_id, items, user):
        order = Order(order_id, items, user)
        OrderValidator.validate(order)
        return order

    @classmethod
    def create_order_from_dict(cls, data):
        return cls.create_order(
            data["order_id"],
            data["items"],
            data["user"]
        )