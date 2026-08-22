class OrderValidator:
    @staticmethod
    def validate(order):
        if not order.items:
            raise ValueError("Заказ не может быть пустым")
        if not order.user:
            raise ValueError("Заказ должен иметь пользователя")
        return True