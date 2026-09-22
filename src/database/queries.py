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

# АНАЛИЗ ACID — старая версия transfer_money
# def transfer_money(from_user_id, to_user_id, amount):
#     with get_connection() as conn:
#         try:
#             with conn.cursor() as cur:
#                 # C - Consistency: проверка баланса ДО операции
#                 cur.execute("SELECT balance FROM users WHERE id = %s", (from_user_id,))
#                 balance = cur.fetchone()[0]
#                 if balance < amount:
#                     raise ValueError("Недостаточно средств для перевода")
#                 # A - Atomicity: все операции в одной транзакции
#                 cur.execute("UPDATE users SET balance = balance - %s WHERE id = %s", (amount, from_user_id))
#                 cur.execute("UPDATE users SET balance = balance + %s WHERE id = %s", (amount, to_user_id))
#                 # C - Consistency: проверка баланса ПОСЛЕ операции
#                 cur.execute("SELECT balance FROM users WHERE id = %s", (from_user_id,))
#                 if cur.fetchone()[0] < 0:
#                     raise ValueError("Баланс отрицательный")
#                 # I - Isolation: уровень изоляции не установлен
#                 # D - Durability: commit() автоматически
#                 return True
#         except Exception as e:
#             # A - Atomicity: rollback() при ошибке
#             conn.rollback()
#             raise
#
#
# import psycopg2
# from psycopg2.extensions import (
#     ISOLATION_LEVEL_READ_COMMITTED,
#     ISOLATION_LEVEL_REPEATABLE_READ,
#     ISOLATION_LEVEL_SERIALIZABLE
# )
# from src.database.connection import get_connection
#
# def read_user_balance(user_id):
#     # READ COMMITTED — достаточно для простого чтения баланса
#     with get_connection() as conn:
#         conn.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
#
#         with conn.cursor() as cur:
#             cur.execute("SELECT balance FROM users WHERE id = %s", (user_id,))
#             result = cur.fetchone()
#             return result[0] if result else 0
#
# def calculate_total_revenue(start_date, end_date):
#     # REPEATABLE READ — оба запроса должны видеть одинаковый снимок данных
#     with get_connection() as conn:
#         conn.set_isolation_level(ISOLATION_LEVEL_REPEATABLE_READ)
#
#         try:
#             with conn.cursor() as cur:
#                 cur.execute("SELECT COALESCE(SUM(total), 0) FROM orders WHERE created_at BETWEEN %s AND %s",
#                             (start_date, end_date)
#                 )
#                 total = cur.fetchone()[0]
#
#                 cur.execute("SELECT COUNT(*) FROM orders WHERE created_at BETWEEN %s AND %s",
#                             (start_date, end_date)
#                             )
#                 count = cur.fetchone()[0]
#
#                 return{
#                     "total": float(total),
#                     "count": int(count),
#                     "average": float(total) / count if count else 0
#                 }
#         except psycopg2.Error as e:
#             conn.rollback()
#             raise
#
# def critical_financial_operation(from_user_id, to_user_id, amount):
#     # SERIALIZABLE — полная изоляция для критических финансовых операций
#     # I - Isolation: установка уровня изоляции
#     with get_connection() as conn:
#         conn.set_isolation_level(ISOLATION_LEVEL_SERIALIZABLE)
#
#         try:
#             with conn.cursor() as cur:
#                 # C - Consistency: проверка согласованности ДО операци
#                 cur.execute("SELECT balance FROM users WHERE id = %s", (from_user_id,))
#                 row = cur.fetchone()
#                 if row is None:
#                     raise ValueError("нет такого пользователя")
#                 if row[0] < amount:
#                     raise ValueError("средств не достаточно")
#
#                 # A - Atomicity: все операции в одной транзакции
#
#                 cur.execute("UPDATE users SET balance = balance - %s WHERE id = %s",
#                             (amount, from_user_id))
#
#                 cur.execute("UPDATE users SET balance = balance + %s WHERE id = %s",
#                             (amount, to_user_id))
#                 # C - Consistency: проверка баланса после списания
#                 cur.execute("SELECT balance FROM users WHERE id = %s",(from_user_id,))
#                 if cur.fetchone()[0] < 0:
#                     raise ValueError("Баланс отрицательный")
#                 # D - Durability: commit() вызывается автоматически
#                 return True
#
#         except psycopg2.Error as e:
#             conn.rollback()
#             raise
#         except ValueError as e:
#             conn.rollback()
#             raise
#
# print(read_user_balance(1))

# индексы для ускорения запросов
# idx_products_name на products(name) — для поиска товаров по названию
# idx_orders_user_id на orders(user_id) — для поиска заказов по пользователю
# idx_order_items_order_id и idx_order_items_product_id — для JOIN через order_items
# отдельный индекс на products.id не нужен — PRIMARY KEY уже создаёт его автоматически

# import time
# from src.database.connection import get_connection
#
# def measure_index_performance():
#
# # Измерение производительности запросов с индексами
#
#     with get_connection() as conn:
#         with conn.cursor() as cur:
#             print("Тест 1 поиск товара по названию")
#
#         # Без индекса
#
#             start_time = time.perf_counter()
#             cur.execute("SELECT * FROM products WHERE name = %s", ("Ноутбук",))
#             result = cur.fetchone()
#             time_without_index = time.perf_counter() - start_time
#
#             # Создание индекса
#
#             cur.execute("CREATE INDEX IF NOT EXISTS index_product_name ON products(name)")
#             conn.commit()
#
#             # С индексом
#
#             start_time = time.perf_counter()
#             cur.execute("SELECT * FROM products WHERE name = %s", ("Ноутбук",))
#             result = cur.fetchone()
#             time_with_index = time.perf_counter() - start_time
#
#             # Результаты
#
#             print(f"без индекса: {time_without_index:.6f} c")
#             print(f"с индексом: {time_with_index:.6f} с")
#             if time_with_index > 0:
#                 speedup = time_without_index / time_with_index
#                 print(f"ускорение: {speedup:.2f}x")
#
#             print("Тест 2: Поиск заказов по пользователю")
#
#             # Без индекса
#             start_time = time.perf_counter()
#             cur.execute("SELECT * FROM orders WHERE user_id = %s", (1,))
#             results = cur.fetchall()
#             time_without_index = time.perf_counter() - start_time
#
#             # Создание индекса
#             cur.execute("CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id)")
#             conn.commit()
#
#             # С индексом
#             start_time = time.perf_counter()
#             cur.execute("SELECT * FROM orders WHERE user_id = %s", (1,))
#             results = cur.fetchall()
#             time_with_index = time.perf_counter() - start_time
#
#             print(f"без индекса: {time_without_index:.6f} с")
#             print(f"с индексом: {time_with_index:.6f} с")
#             if time_with_index > 0:
#                 speedup = time_without_index / time_with_index
#                 print(f"ускорение: {speedup:.2f}x")
#
# # тест
# if __name__ == "__main__":
#     measure_index_performance()


# def get_user_orders_with_products(user_id):
#     with get_connection() as conn:
#         with conn.cursor() as cur:
#             # Запрос использует индексы для быстрого выполнения
#             cur.execute("""
#                 SELECT o.id, o.total, p.name, p.price
#                 FROM orders o
#                 JOIN order_items oi ON o.id = oi.order_id
#                 JOIN products p ON oi.product_id = p.id
#                 WHERE o.user_id = %s
#             """, (user_id,))
#             return cur.fetchall()
# print(get_user_orders_with_products(1))



from sqlalchemy import select
from sqlalchemy.orm import joinedload
from src.database.models import User, Order, get_session

def get_user_orders(user_id):
    session = get_session()
    try:
        stmt = select(User).options(joinedload(User.orders)).where(User.id == user_id)
        user = session.execute(stmt).unique().scalar_one_or_none()
        if user:
            return [{
                "id": order.id,
                "total": float(order.total),
                "created_at": order.created_at.isoformat()
            } for order in user.orders]
        return []
    finally:
        session.close()


def create_order(user_id, total):
    session = get_session()
    try:
        order = Order(user_id=user_id, total=total)
        session.add(order)
        session.commit()
        order_id = order.id
        return order_id
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()


def get_all_orders_with_users():
    session = get_session()
    try:
        stmt = select(Order).options(joinedload(Order.user))
        orders = session.execute(stmt).scalars().unique().all()
        return [{
            "id": order.id,
            "total": float(order.total),
            "user_name": order.user.name,
            "user_email": order.user.email
        } for order in orders]
    finally:
        session.close()

def get_all_products_from_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, price, quantity FROM products")
            rows = cur.fetchall()
            return [{"id": r[0], "name": r[1], "price": float(r[2]), "quantity": r[3]} for r in rows]

def get_product_by_id_from_db(product_id):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, name, price, quantity FROM products WHERE id = %s", (product_id,))
            r = cur.fetchone()
            if r:
                return {"id": r[0], "name": r[1], "price": float(r[2]), "quantity": r[3]}
            return None







