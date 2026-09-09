

from database.connection import (
    connect_to_db,
    create_user,
    get_user_by_id,
    get_all_products,
    add_product,
    create_order,
    get_user_orders,
    delete_order
)
from database.queries import (
    get_user_order_history,
    get_order_statistics,
    get_top_products
)


def main():
    conn = connect_to_db()
    if not conn:
        return

    try:
        # Создаём пользователя
        create_user(conn, "Тест", "test@1.ru")

        # Получаем пользователя по id
        user = get_user_by_id(conn, 1)
        print(f"Пользователь найден: {user}")

        # Получаем все товары
        products = get_all_products(conn)
        print(f"Все товары: {products}")

        # Создаём заказ
        create_order(conn, 1, 50000.00)

        # Получаем заказы пользователя
        orders = get_user_orders(conn, 1)
        print(f"Заказы пользователя: {orders}")

        # История заказов с товарами
        history = get_user_order_history(conn, 1)
        print(f"История заказов: {history}")

        # Статистика по пользователям
        stats = get_order_statistics(conn)
        print(f"Статистика: {stats}")

        # Топ-5 товаров
        top = get_top_products(conn)
        print(f"Топ товаров: {top}")

        # Удаляем заказ
        deleted = delete_order(conn, 1)
        print(f"Удалено заказов: {deleted}")

    finally:
        conn.close()
        print("Соединение закрыто!")


if __name__ == "__main__":
    main()