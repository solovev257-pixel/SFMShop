# class User:
#     def __init__(self, name, email):
#         self.name = name
#         self.email = email
#
#     def get_info(self):
#         return "Пользователь: " + self.name + ", Email: " + self.email
#
# def validate_email(self):
#     if "@" not in self.email:
#         raise ValueError("Неверный формат email")
#     return True
# # обновлён класс User

# from src.models.metaclasses import ModelMeta
#
#
# class User(metaclass = ModelMeta):
#     def __init__(self, name, email):
#         self.name = name
#         self.email = email


from src.models.mixins import LoggableMixin, SerializableMixin
from src.models.descriptors import PositiveNumber, EmailDescriptor, AgeDescriptor


class User(LoggableMixin, SerializableMixin):
    user_id = PositiveNumber("_user_id")
    email = EmailDescriptor("_email")
    age = AgeDescriptor("_age")
    balance = PositiveNumber("_balance")

    def __init__(self, user_id, name, email, age, balance):
        self.user_id = user_id
        self.name = name
        self.email = email
        self.age = age
        self.balance = balance
        self.orders = []
        self.is_active = True
        self.log(f"Создан пользователь: {name}")

    def to_json(self):
        return {
            "user_id": self.user_id,
            "name": self.name,
            "email": self.email,
            "age": self.age,
            "balance": self.balance,
            "orders_count": len(self.orders),
            "is_active": self.is_active
        }