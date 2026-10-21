import asyncio
import os
from dataclasses import dataclass
from decimal import Decimal

import asyncpg
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "database": os.getenv("DB_NAME", "sfmshop"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
}


def _row_to_dict(row) -> dict:
    """Строка из БД -> словарь; Decimal превращаем в float, чтобы JSON и кэш работали одинаково"""
    return {
        key: float(value) if isinstance(value, Decimal) else value
        for key, value in dict(row).items()
    }


class ProductRepository:
    """Асинхронная работа с таблицей products через пул соединений"""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_by_id(self, product_id: int) -> dict | None:
        row = await self.pool.fetchrow(
            "SELECT id, name, price, quantity FROM products WHERE id = $1",
            product_id,
        )
        return _row_to_dict(row) if row else None

    async def list_products(self, limit: int = 20, offset: int = 0) -> list[dict]:
        rows = await self.pool.fetch(
            "SELECT id, name, price, quantity FROM products ORDER BY id LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
        return [_row_to_dict(row) for row in rows]

    async def count(self) -> int:
        return await self.pool.fetchval("SELECT COUNT(*) FROM products")

    async def create(self, name: str, price: float, quantity: int = 0) -> int:
        return await self.pool.fetchval(
            "INSERT INTO products (name, price, quantity) VALUES ($1, $2, $3) RETURNING id",
            name,
            price,
            quantity,
        )

    async def update(self, product_id: int, fields: dict) -> dict | None:
        """Обновить только переданные поля; None, если товара нет"""
        allowed = {"name", "price", "quantity"}
        fields = {key: value for key, value in fields.items() if key in allowed}
        if not fields:
            return await self.get_by_id(product_id)

        columns = list(fields)
        set_clause = ", ".join(f"{column} = ${index}" for index, column in enumerate(columns, start=1))
        row = await self.pool.fetchrow(
            f"UPDATE products SET {set_clause} WHERE id = ${len(columns) + 1} "
            "RETURNING id, name, price, quantity",
            *fields.values(),
            product_id,
        )
        return _row_to_dict(row) if row else None

    async def update_price(self, product_id: int, new_price: float) -> bool:
        status = await self.pool.execute(
            "UPDATE products SET price = $1 WHERE id = $2",
            new_price,
            product_id,
        )
        return status == "UPDATE 1"

    async def delete(self, product_id: int) -> bool:
        status = await self.pool.execute("DELETE FROM products WHERE id = $1", product_id)
        return status == "DELETE 1"


class UserRepository:
    """Пользователи: регистрация и поиск для входа"""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def create(self, name: str, email: str, password_hash: str) -> int:
        return await self.pool.fetchval(
            "INSERT INTO users (name, email, password_hash) VALUES ($1, $2, $3) RETURNING id",
            name,
            email,
            password_hash,
        )

    async def get_by_email(self, email: str) -> dict | None:
        row = await self.pool.fetchrow(
            "SELECT id, name, email, password_hash FROM users WHERE email = $1",
            email,
        )
        return dict(row) if row else None

    async def get_by_id(self, user_id: int) -> dict | None:
        row = await self.pool.fetchrow(
            "SELECT id, name, email FROM users WHERE id = $1",
            user_id,
        )
        return dict(row) if row else None


@dataclass
class OrderRecord:
    id: int
    user_id: int
    total: float
    status: str


class OrderRepository:
    """Заказы: создание с позициями и чтение"""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_by_id(self, order_id: int) -> OrderRecord | None:
        row = await self.pool.fetchrow(
            "SELECT id, user_id, total, status FROM orders WHERE id = $1",
            order_id,
        )
        if row is None:
            return None
        return OrderRecord(id=row["id"], user_id=row["user_id"], total=float(row["total"]), status=row["status"])

    async def list_by_user(self, user_id: int) -> list[dict]:
        rows = await self.pool.fetch(
            "SELECT id, total, status, created_at FROM orders WHERE user_id = $1 ORDER BY id DESC",
            user_id,
        )
        return [_row_to_dict(row) for row in rows]

    async def create(self, user_id: int, items: list[dict]) -> OrderRecord:
        """Создать заказ в одной транзакции: проверить остатки, списать их, записать позиции"""
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                total = Decimal("0")
                for item in items:
                    product = await conn.fetchrow(
                        "SELECT price, quantity FROM products WHERE id = $1 FOR UPDATE",
                        item["product_id"],
                    )
                    if product is None:
                        raise LookupError(f"Товар {item['product_id']} не найден")
                    if product["quantity"] < item["quantity"]:
                        raise ValueError(f"Товара {item['product_id']} недостаточно на складе")
                    total += product["price"] * item["quantity"]
                    await conn.execute(
                        "UPDATE products SET quantity = quantity - $1 WHERE id = $2",
                        item["quantity"],
                        item["product_id"],
                    )

                order_id = await conn.fetchval(
                    "INSERT INTO orders (user_id, total) VALUES ($1, $2) RETURNING id",
                    user_id,
                    total,
                )
                for item in items:
                    await conn.execute(
                        "INSERT INTO order_items (order_id, product_id, quantity) VALUES ($1, $2, $3)",
                        order_id,
                        item["product_id"],
                        item["quantity"],
                    )
        return OrderRecord(id=order_id, user_id=user_id, total=float(total), status="created")


async def demo():
    """Проверка репозитория: создать, прочитать, обновить, удалить"""
    pool = await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=5)
    try:
        repository = ProductRepository(pool)

        new_id = await repository.create("Тестовый товар", 999.0, 3)
        print(f"Создан товар #{new_id}: {await repository.get_by_id(new_id)}")

        await repository.update_price(new_id, 1299.0)
        print(f"После смены цены: {await repository.get_by_id(new_id)}")

        print(f"Удалён: {await repository.delete(new_id)}")
        print(f"Первые товары: {await repository.list_products(limit=3)}")
    finally:
        await pool.close()


if __name__ == "__main__":
    asyncio.run(demo())