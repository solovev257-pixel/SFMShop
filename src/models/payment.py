# class Payment:
#     def __init__(self, amount):
#         self.amount = amount
#
#     def process_payment(self):
#         raise NotImplementedError("Метод должен быть переопределен в дочернем классе")
#
# class CardPayment(Payment):
#     def __init__(self, amount, card_number):
#         super().__init__(amount)
#         self.__card_number = card_number  # Приватный атрибут
#
#     def process_payment(self):
#         # Маскируем номер карты для безопасности
#         masked_card = "**** " + self.__card_number[-4:]
#         return "Оплата картой " + masked_card + ": " + str(self.amount) + " руб."
#
# class PayPalPayment(Payment):
#     def __init__(self, amount, email):
#         super().__init__(amount)
#         self.email = email
#
#     def process_payment(self):
#         return "Оплата PayPal (" + self.email + "): " + str(self.amount) + " руб."

# class A:
#     def method(self):
#         print("A.method()")
#
# class B(A):
#     def method(self):
#         print("B.method()")
#         super().method()
#
# class C(A):
#     def method(self):
#         print("C.method()")
#         super().method()
#
# class D(B,C):
#     def method(self):
#         print("D.method()")
#         super().method()
#
# print("MRO для D")
# for i, cls in enumerate(D.mro(), 1):
#     print(f"{i}. {cls.__name__}")
#
# d = D()
# d.method()


from abc import ABC, abstractmethod

class Payment:
    def __init__(self,order_id, amount, payment_method):
        self.order_id = order_id
        self.amount = amount
        self.payment_method = payment_method
        self.status = "pending"

class PaymentMethod(ABC):
    @abstractmethod
    def process(self, amount):
        pass

    @abstractmethod
    def calculate_fee(self, amount):
        pass

class CardPayment(PaymentMethod):
    def calculate_fee(self, amount):
        if amount > 10000:
            return amount * 0.02
        else:
            return amount * 0.03

    def process(self, amount):
        fee = self.calculate_fee(amount)
        total = amount + fee
        print (f"Списание с карты суммы {total}")
        return True

class PayPalPayment(PaymentMethod):
    def calculate_fee(self, amount):
        return amount * 0.035

    def process(self, amount):
        fee = self.calculate_fee(amount)
        total = amount + fee
        print (f"Списание с PayPal {total}")
        return True

class BankTransferPayment(PaymentMethod):
    def calculate_fee(self, amount):
        return 50

    def process(self, amount):
        fee = self.calculate_fee(amount)
        total = amount + fee
        print(f"Банковский перевод на сумму {total}")
        return True