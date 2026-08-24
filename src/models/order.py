# class Order:
#
#     def __init__(self, user, products, order_id=None):
#         self.user = user
#         self.products = products
#         self.order_id = order_id
#         self.total = self.calculate_total()
#
#     def calculate_total(self):
#         total = 0
#         for product in self.products:
#             total = total + product.get_total_price()
#         return total
#
#     def __str__(self):
#         user_name = self.user.name if hasattr(self.user, 'name') else str(self.user)
#         if self.order_id:
#             return 'Заказ #' + str(self.order_id) + ' на сумму ' + str(self.total) + ' руб. (Пользователь: ' + user_name + ')'
#         return 'Заказ на сумму ' + str(self.total) + ' руб. (Пользователь: ' + user_name + ')'

# from src.models.mixins import LoggableMixin, ValidatableMixin, SerializableMixin
#
# class Order(ValidatableMixin, LoggableMixin, SerializableMixin):
#     def __init__(self, order_id, total):
#         self.order_id = order_id
#         self.total = total
#         self.log(f"Создан заказ: {order_id}")
#     def validate(self):
#         if self.total < 0:
#             raise ValueError('Сумма не может быть отрицательной')
#         return True

# from src.models.metaclasses import ModelMeta
#
# class Order(metaclass = ModelMeta):
#     def __init__(self, order_id, total):
#         self.order_id = order_id
#         self.total = total

# from src.models.mixins import LoggableMixin, SerializableMixin
# from src.models.descriptors import PositiveNumber
#
#
# class Order(LoggableMixin, SerializableMixin):
#     order_id = PositiveNumber("_order_id")
#
#     def __init__(self, order_id, items, user):
#         self.order_id = order_id
#         self.items = items
#         self.user = user

from src.models.mixins import LoggableMixin, SerializableMixin
from src.models.descriptors import PositiveNumber

class Order(LoggableMixin, SerializableMixin):
    order_id = PositiveNumber("_order_id")

    def __init__(self, order_id, items, user):
        self.order_id = order_id
        self.items = items
        self.user = user
        self.log(f"Создан заказ: {order_id}")

    def __len__(self):
        return len(self.items)

    def __contains__(self, item):
        return item in self.items

    def __add__(self, other):
        new_items = self.items + other.items
        return Order(self.order_id, new_items)

    def __lt__(self, other):
        return self.order_id < other.order_id