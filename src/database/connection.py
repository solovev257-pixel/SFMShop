# import pg8000
#
#
# def connect_to_db():
#     try:
#         return pg8000.connect(
#             host="localhost",
#             database="sfmshop",
#             user="postgres",
#             password="8523"
#         )
#     except Exception as e:
#         print(f"Ошибка подключения к БД: {e}")
#         return None
#
#
# def create_user(conn, name, email):
#     try:
#         cursor = conn.cursor()
#         cursor.execute(
#             "INSERT INTO users (name, email) VALUES (%s, %s)",
#             (name, email)
#         )
#         conn.commit()
#         cursor.close()
#         print(f"Пользователь создан: {name}, {email}")
#     except Exception as e:
#         conn.rollback()
#         print(f"Ошибка при создании пользователя: {e}")
#
#
# def get_user_by_id(conn, user_id):
#     try:
#         cursor = conn.cursor()
#         cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
#         user = cursor.fetchone()
#         cursor.close()
#         if user:
#             return {"id": user[0], "name": user[1], "email": user[2]}
#         return None
#     except Exception as e:
#         print(f"Ошибка при получении пользователя: {e}")
#         return None
#
#
# def get_all_products(conn):
#     cursor = conn.cursor()
#     cursor.execute("SELECT * FROM products")
#     products = cursor.fetchall()
#     cursor.close()
#     return products
#
#
# def add_product(conn, name, price, quantity):
#     try:
#         cursor = conn.cursor()
#         cursor.execute(
#             "INSERT INTO products (name, price, quantity) VALUES (%s, %s, %s)",
#             (name, price, quantity)
#         )
#         conn.commit()
#         cursor.close()
#         print(f"Товар добавлен: {name}")
#     except Exception as e:
#         conn.rollback()
#         print(f"Ошибка при добавлении товара: {e}")
#
#
# def create_order(conn, user_id, total):
#     try:
#         cursor = conn.cursor()
#         cursor.execute(
#             "INSERT INTO orders (user_id, total) VALUES (%s, %s)",
#             (user_id, total)
#         )
#         conn.commit()
#         cursor.close()
#         print(f"Заказ создан: user_id={user_id}, total={total}")
#     except Exception as e:
#         conn.rollback()
#         print(f"Ошибка при создании заказа: {e}")
#
#
# def get_user_orders(conn, user_id):
#     try:
#         cursor = conn.cursor()
#         cursor.execute(
#             "SELECT * FROM orders WHERE user_id = %s",
#             (user_id,)
#         )
#         orders = cursor.fetchall()
#         cursor.close()
#         return orders
#     except Exception as e:
#         print(f"Ошибка при получении заказов: {e}")
#         return []
#
#
# def delete_order(conn, order_id):
#     try:
#         cursor = conn.cursor()
#         # Сначала удаляем товары заказа
#         cursor.execute(
#             "DELETE FROM order_items WHERE order_id = %s",
#             (order_id,)
#         )
#         # Потом удаляем сам заказ
#         cursor.execute(
#             "DELETE FROM orders WHERE id = %s",
#             (order_id,)
#         )
#         deleted = cursor.rowcount
#         conn.commit()
#         cursor.close()
#         print(f"Заказ удалён: id={order_id}")
#         return deleted
#     except Exception as e:
#         conn.rollback()
#         print(f"Ошибка при удалении заказа: {e}")
#         return 0

import os
import psycopg2
from contextlib import contextmanager
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "sfmshop"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD")
}

@contextmanager
def get_connection():
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
        conn.commit()
    except psycopg2.Error as e:
        if conn:
            conn.rollback()
        print(f"Ошибка БД: {e}")
        raise
    finally:
        if conn:
            conn.close()


def test_connection():
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT version();")
                version = cur.fetchone()
                print(f"Подключение успешно! Версия: {version[0]}")
    except Exception as e:
        print(f"Ошибка подключения: {e}")


if __name__ == "__main__":
    test_connection()