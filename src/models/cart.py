class ShoppingCart:  # ShoppingCart = корзина покупок
    def __init__(self):  # конструктор — создаём пустую корзину
        self.items = []  # items = список товаров, пока пустой

    def __add__(self, item):
        new_cart = ShoppingCart()
        new_cart.items = self.items.copy()
        new_cart.items.append(item)
        return new_cart

    def __len__(self):
        """Возвращает количество товаров в корзине"""
        return len(self.items)

    def __iter__(self):
        """Каждый вызов создает НОВЫЙ итератор"""
        return iter(self.items)

    def __str__(self):  # str = string = строка — вызывается при print(объект)
        return f"Корзина: {len(self.items)} товаров"  # возвращаем читаемый текст

cart = ShoppingCart()
cart = cart + "Ноутбук"
cart = cart + "Мышь"
cart = cart + "Клавиатура"

print(len(cart))   # __len__ → 3

for item in cart:  # __iter__ → перебираем товары
    print(item)
print(cart)  # __str__ → Корзина: 3 товаров