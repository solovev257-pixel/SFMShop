class Order:
    def __init__(self, order_id, product, quantity ):
        self.order_id = order_id
        self.product = product
        self.quantity = quantity

    def info(self):
        print(f"Заказ №{self.order_id}: {self.quantity} шт. {self.product}")
o = Order(42, "велосипед", 3)
o.info()