from src.database.connection import get_connection
import psycopg2

def create_order(user_id, items):
    """
    items = [{"product_id": 1, "quantity": 2}, ...]
    ACID: транзакция с SELECT FOR UPDATE чтобы избежать race condition
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            try:
                total = 0
                for item in items:
                    cur.execute(
                        "SELECT id, price, quantity FROM products WHERE id = %s FOR UPDATE",
                        (item["product_id"],)
                    )
                    product = cur.fetchone()
                    if not product:
                        raise ValueError(f"Товар {item['product_id']} не найден")
                    if product[2] < item["quantity"]:
                        raise ValueError(f"Недостаточно товара {item['product_id']}")
                    total += float(product[1]) * item["quantity"]

                cur.execute(
                    "INSERT INTO orders (user_id, total, status) VALUES (%s, %s, 'pending') RETURNING id",
                    (user_id, total)
                )
                order_id = cur.fetchone()[0]

                for item in items:
                    cur.execute(
                        "INSERT INTO order_items (order_id, product_id, quantity, price) "
                        "SELECT %s, %s, %s, price FROM products WHERE id = %s",
                        (order_id, item["product_id"], item["quantity"], item["product_id"])
                    )
                    cur.execute(
                        "UPDATE products SET quantity = quantity - %s WHERE id = %s",
                        (item["quantity"], item["product_id"])
                    )

                return order_id

            except Exception:
                conn.rollback()
                raise


if __name__ == "__main__":
    order_id = create_order(1, [{"product_id": 1, "quantity": 1}])
    print(f"Заказ создан: {order_id}")