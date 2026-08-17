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

from src.models.metaclasses import ModelMeta

class Order(metaclass = ModelMeta):
    def __init__(self, order_id, total):
        self.order_id = order_id
        self.total = total

