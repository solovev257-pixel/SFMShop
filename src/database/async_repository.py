import asyncio
import os

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


class ProductRepository:
    """Асинхронная работа с таблицей products через пул соединений"""

    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool

    async def get_by_id(self, product_id: int) -> dict | None:
        """Получить товар по id"""
        row = await self.pool.fetchrow(
            "SELECT id, name, price, quantity FROM products WHERE id = $1",
            product_id,
        )
        return dict(row) if row else None

    async def list_products(self, limit: int = 20, offset: int = 0) -> list[dict]:
        """Список товаров с пагинацией"""
        rows = await self.pool.fetch(
            "SELECT id, name, price, quantity FROM products ORDER BY id LIMIT $1 OFFSET $2",
            limit,
            offset,
        )
        return [dict(row) for row in rows]

    async def create(self, name: str, price: float, quantity: int = 0) -> int:
        """Создать товар, вернуть id"""
        return await self.pool.fetchval(
            "INSERT INTO products (name, price, quantity) VALUES ($1, $2, $3) RETURNING id",
            name,
            price,
            quantity,
        )

    async def update_price(self, product_id: int, new_price: float) -> bool:
        """Обновить цену товара, True если товар найден"""
        status = await self.pool.execute(
            "UPDATE products SET price = $1 WHERE id = $2",
            new_price,
            product_id,
        )
        return status == "UPDATE 1"

    async def delete(self, product_id: int) -> bool:
        """Удалить товар, True если товар найден"""
        status = await self.pool.execute(
            "DELETE FROM products WHERE id = $1",
            product_id,
        )
        return status == "DELETE 1"


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