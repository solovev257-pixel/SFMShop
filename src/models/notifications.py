from abc import ABC, abstractmethod

class Notification(ABC):
    @abstractmethod
    def send(self,message):
        pass

class EmailNotification(Notification):
    def __init__(self, email):
        self.email = email
    def send(self,message):
        print(f"Отправка email на {self.email}: {message}")

class SMSNotification(Notification):
    def __init__(self, number):
        self.number = number
    def send(self,message):
        print(f"Отправка SMS на {self.number}: {message}")

def send_notifications(notifications, message):
    for notification in notifications:
        notification.send(message)

email = EmailNotification("user@example.com")
sms = SMSNotification("+7 999 123-45-67")

notifications = [email, sms]
send_notifications(notifications, "Ваш заказ готов!")
