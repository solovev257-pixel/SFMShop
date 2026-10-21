"""Замер «до и после»: синхронные запросы по очереди против асинхронных параллельно."""
import asyncio
import time

import httpx
import requests

from src.services.exchange_client import AsyncExchangeClient, ExchangeClient

CURRENCIES = ["USD", "EUR", "CNY", "KZT", "TRY"]
API_URL = "http://127.0.0.1:8000/api/v1/products?limit=10"
API_REQUESTS = 30


def external_sync() -> float:
    client = ExchangeClient()
    started = time.perf_counter()
    for currency in CURRENCIES:
        client.get_exchange_rate("RUB", currency)
    return time.perf_counter() - started


async def external_async() -> float:
    client = AsyncExchangeClient()
    started = time.perf_counter()
    await asyncio.gather(*(client.get_exchange_rate("RUB", currency) for currency in CURRENCIES))
    return time.perf_counter() - started


def api_sync() -> float:
    started = time.perf_counter()
    for _ in range(API_REQUESTS):
        requests.get(API_URL, timeout=5)
    return time.perf_counter() - started


async def api_async() -> float:
    async with httpx.AsyncClient(timeout=5) as client:
        started = time.perf_counter()
        await asyncio.gather(*(client.get(API_URL) for _ in range(API_REQUESTS)))
        return time.perf_counter() - started


def report(title: str, before: float, after: float) -> None:
    print(f"{title}")
    print(f"  до (sync, по очереди):     {before:.2f} с")
    print(f"  после (async, параллельно): {after:.2f} с")
    if after > 0:
        print(f"  ускорение: в {before / after:.1f} раза")


def main():
    report(f"Курсы {len(CURRENCIES)} валют из внешнего API", external_sync(), asyncio.run(external_async()))

    try:
        requests.get(API_URL, timeout=2)
    except requests.RequestException:
        print("Сервер SFMShop не запущен — замер API пропущен (запусти uvicorn в Local (2))")
        return
    report(f"{API_REQUESTS} запросов к GET /api/v1/products", api_sync(), asyncio.run(api_async()))


if __name__ == "__main__":
    main()