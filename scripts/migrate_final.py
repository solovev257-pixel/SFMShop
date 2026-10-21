import asyncio

import asyncpg

from src.database.async_repository import DB_CONFIG

MIGRATIONS = [
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(200)",
    "ALTER TABLE orders ADD COLUMN IF NOT EXISTS status VARCHAR(30) NOT NULL DEFAULT 'created'",
]


async def main():
    conn = await asyncpg.connect(**DB_CONFIG)
    try:
        for sql in MIGRATIONS:
            await conn.execute(sql)
            print(f"OK: {sql}")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())