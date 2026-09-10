# import pg8000
# import sys
# import io
# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
#
#
# def get_user_order_history(conn, user_id):
#     """Получить историю заказов пользователя с товарами"""
#     cursor = conn.cursor()
#     cursor.execute("""
#         SELECT
#             orders.id,
#             products.name,
#             order_items.quantity,
#             products.price
#         FROM orders
#         INNER JOIN order_items ON orders.id = order_items.order_id
#         INNER JOIN products ON order_items.product_id = products.id
#         WHERE orders.user_id = %s
#         ORDER BY orders.id DESC
#     """, (user_id,))
#     results = cursor.fetchall()
#     cursor.close()
#     return results
#
#
# def get_order_statistics(conn):
#     """Получить статистику по пользователям (количество заказов, общая сумма)"""
#     cursor = conn.cursor()
#     cursor.execute("""
#         SELECT
#             users.id,
#             users.name,
#             COUNT(orders.id) as order_count,
#             COALESCE(SUM(orders.total), 0) as total_sum
#         FROM users
#         LEFT JOIN orders ON users.id = orders.user_id
#         GROUP BY users.id, users.name
#         ORDER BY total_sum DESC
#     """)
#     results = cursor.fetchall()
#     cursor.close()
#     return results
#
#
# def get_top_products(conn, limit=5):
#     """Получить топ товаров по количеству продаж"""
#     cursor = conn.cursor()
#     cursor.execute("""
#         SELECT
#             products.name,
#             SUM(order_items.quantity) as total_sold
#         FROM products
#         INNER JOIN order_items ON products.id = order_items.product_id
#         GROUP BY products.id, products.name
#         ORDER BY total_sold DESC
#         LIMIT %s
#     """, (limit,))
#     results = cursor.fetchall()
#     cursor.close()
#     return results
#
#
# def main():
#     conn = pg8000.connect(
#         host="localhost",
#         database="sfmshop",
#         user="postgres",
#         password="8523"
#     )
#
#     print("История заказов пользователя:")
#     history = get_user_order_history(conn, 1)
#     for h in history:
#         print(h)
#
#     print("\nСтатистика по пользователям:")
#     stats = get_order_statistics(conn)
#     for s in stats:
#         print(s)
#
#     print("\nТоп-5 товаров:")
#     top = get_top_products(conn)
#     for t in top:
#         print(t)
#
#     conn.close()
#
#
# if __name__ == "__main__":
#     main()

from src.database.connection import get_connection

def transfer_money(from_user_id, to_user_id, amount):
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                # есть ли нужная сумма на счету
                cur.execute("SELECT balance FROM users WHERE id = %s", (from_user_id,))
                balance = cur.fetchone()[0]
                if balance < amount:
                    raise ValueError("Недостаточно средств для перевода")
                # списать
                cur.execute(
                    "UPDATE users SET balance = balance - %s WHERE id = %s",
                    (amount, from_user_id)
                )
                # зачислить
                cur.execute(
                    "UPDATE users SET balance = balance + %s WHERE id = %s",
                    (amount, to_user_id)
                )

                # вторая проверка баланса что он не ущел в минус
                cur.execute("SELECT balance FROM users WHERE id = %s", (from_user_id,))
                result = cur.fetchone()
                if result[0] < 0:
                    raise ValueError("Ошибка: баланс стал отрицательным")

                return True

        except Exception as e:
            conn.rollback()
            print(f"Ошибка при переводе денег: {e}")
            raise

try:
    transfer_money(from_user_id=1, to_user_id=2, amount=500)
    print("Перевод выполнен успешно")
except ValueError as e:
    print(f"Ошибка: {e}")