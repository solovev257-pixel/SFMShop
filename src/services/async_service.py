import asyncio
import logging
import time

import aiohttp

from src.models.order import Order
from src.models.product import Product

logger = logging.getLogger(__name__)


async def fetch_url_async(url: str):
    """Асинхронный запрос к URL"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                return None
    except aiohttp.ClientError as error:
        print(f"Ошибка при запросе к {url}: {error}")
        return None


async def fetch_with_session(session: aiohttp.ClientSession, url: str):
    """Один запрос в уже открытой сессии"""
    try:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            return None
    except aiohttp.ClientError as error:
        print(f"Ошибка при запросе к {url}: {error}")
        return None


async def fetch_multiple_urls_async(urls: list):
    """Параллельные запросы к нескольким URL: одна сессия на всю группу"""
    async with aiohttp.ClientSession() as session:
        tasks = [fetch_with_session(session, url) for url in urls]
        return await asyncio.gather(*tasks)


async def compare_parallel_and_sequential(urls: list):
    """Замер: параллельный проход против последовательного по тем же URL"""
    start = time.time()
    results = await fetch_multiple_urls_async(urls)
    parallel_time = time.time() - start

    start = time.time()
    async with aiohttp.ClientSession() as session:
        for url in urls:
            await fetch_with_session(session, url)
    sequential_time = time.time() - start

    print(f"Параллельно: {parallel_time:.2f} секунд")
    print(f"Последовательно: {sequential_time:.2f} секунд")
    if parallel_time > 0:
        print(f"Ускорение: в {sequential_time / parallel_time:.1f} раз")
    return results


async def demo_parallel_requests():
    """Демо из урока про параллельные запросы"""
    urls = ["https://httpbin.org/delay/1"] * 3
    results = await compare_parallel_and_sequential(urls)
    print(f"Получено ответов: {len(results)}")



ORDER_DETAILS_API_URL = "https://api.orders.sfmshop.ru/order"
PROCESSING_DELAY = 0.1  # имитация обращения к базе или сервису, секунды


def build_order_items(order_id: int) -> list[Product]:
    """Тестовые позиции заказа. У каждого 25-го заказа цена отрицательная, чтобы проверить обработку ошибок"""
    price = -100 if order_id % 25 == 0 else 100 * (order_id % 7 + 1)
    return [Product("Мышь", price, 2), Product("Коврик", 300, 1)]


def finish_order(order_id: int, user: str) -> dict:
    """Собирает заказ через класс Order и считает сумму"""
    order = Order(order_id, build_order_items(order_id), user)
    total = sum(item.total_value for item in order.items)
    return {"order_id": order_id, "status": "completed", "items": len(order), "total": total}


async def process_order(order_id: int, user: str = "Покупатель SFMShop") -> dict:
    """Асинхронная обработка одного заказа"""
    try:
        await asyncio.sleep(PROCESSING_DELAY)  # здесь было бы чтение заказа из БД
        return finish_order(order_id, user)
    except Exception as error:
        logger.error("Заказ %s не обработан: %s", order_id, error)
        return {"order_id": order_id, "status": "failed", "error": str(error)}


async def process_orders_async(order_ids: list) -> list[dict]:
    """Параллельная обработка списка заказов через asyncio.gather"""
    return await asyncio.gather(*(process_order(order_id) for order_id in order_ids))


def process_orders_sync(order_ids: list, user: str = "Покупатель SFMShop") -> list[dict]:
    """Синхронная версия для сравнения: time.sleep блокирует, заказы идут строго по очереди"""
    results = []
    for order_id in order_ids:
        try:
            time.sleep(PROCESSING_DELAY)
            results.append(finish_order(order_id, user))
        except Exception as error:
            logger.error("Заказ %s не обработан: %s", order_id, error)
            results.append({"order_id": order_id, "status": "failed", "error": str(error)})
    return results


async def fetch_order_details_async(order_id: int, session: aiohttp.ClientSession | None = None) -> dict | None:
    """Дополнительные данные о заказе из внешнего API. При сетевой ошибке возвращает None"""
    own_session = session is None
    if own_session:
        session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3))
    try:
        async with session.get(f"{ORDER_DETAILS_API_URL}/{order_id}") as response:
            if response.status == 200:
                return await response.json()
            logger.warning("API деталей заказа %s ответил кодом %s", order_id, response.status)
            return None
    except (aiohttp.ClientError, asyncio.TimeoutError) as error:
        logger.warning("Не удалось получить детали заказа %s: %s", order_id, error)
        return None
    finally:
        if own_session:
            await session.close()


async def main():
    """Замер: 100 заказов синхронно и асинхронно"""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    order_ids = list(range(1, 101))

    start = time.time()
    process_orders_sync(order_ids)  # специально блокирующая версия, только для сравнения
    sync_time = time.time() - start

    start = time.time()
    results = await process_orders_async(order_ids)
    async_time = time.time() - start

    failed = [result["order_id"] for result in results if result["status"] == "failed"]
    print()
    print(f"Заказов: {len(results)}, обработано: {len(results) - len(failed)}, с ошибкой: {failed}")
    print(f"Синхронно:  {sync_time:.2f} секунд")
    print(f"Асинхронно: {async_time:.2f} секунд")
    print(f"Ускорение: в {sync_time / async_time:.0f} раз")

    details = await fetch_order_details_async(1)
    print(f"Детали заказа 1 из внешнего API: {details}")


if __name__ == "__main__":
    asyncio.run(main())
