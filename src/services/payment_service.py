from abc import ABC, abstractmethod

class PaymentValidator:
    @staticmethod
    def validate(payment):
        if payment.amount <= 0:
            raise ValueError("Сумма должна быть положительной")
        return True

class PaymentRepository(ABC):
    @abstractmethod
    def save(self, payment):
        pass

class PostgreSQLPaymentRepository(PaymentRepository):
    def save(self, payment):
        print(f"Сохранение платежа {payment.order_id} в PostgreSQL")

class NotificationService(ABC):
    @abstractmethod
    def send(self, payment):
        pass

class EmailNotificationService(NotificationService):
    def send(self, payment):
        print(f"Отправка email о платеже {payment.order_id}")

class PaymentProcessor:
    def __init__(self, payment_method, repository, notification_service):
        self.payment_method = payment_method
        self.repository = repository
        self.notification_service = notification_service
    def process_payment(self, payment):
        PaymentValidator.validate(payment)

        success = self.payment_method.process(payment.amount)
        if success:
            payment.status = "completed"
        else:
            payment.status = "failed"
            raise ValueError("Ошибка обработки платежа")

        self.repository.save(payment)
        self.notification_service.send(payment)
        return payment.status


from abc import ABC, abstractmethod

class PaymentValidator:
    @staticmethod
    def validate(payment):
        if payment.amount <= 0:
            raise ValueError("Сумма должна быть положительной")
        return True

class PaymentRepository(ABC):
    @abstractmethod
    def save(self, payment):
        pass

class PostgreSQLPaymentRepository(PaymentRepository):
    def save(self, payment):
        print(f"Сохранение платежа {payment.order_id} в PostgreSQL")

class NotificationService(ABC):
    @abstractmethod
    def send(self, payment):
        pass

class EmailNotificationService(NotificationService):
    def send(self, payment):
        print(f"Отправка email о платеже {payment.order_id}")

class PaymentProcessor:
    def __init__(self, payment_method, repository, notification_service):
        self.payment_method = payment_method
        self.repository = repository
        self.notification_service = notification_service
    def process_payment(self, payment):
        PaymentValidator.validate(payment)

        success = self.payment_method.process(payment.amount)
        if success:
            payment.status = "completed"
        else:
            payment.status = "failed"
            raise ValueError("Ошибка обработки платежа")

        self.repository.save(payment)
        self.notification_service.send(payment)
        return payment.status