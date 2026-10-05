import asyncio
import aiohttp
import time


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


async def main():
    urls = ["https://httpbin.org/delay/1"] * 3
    results = await compare_parallel_and_sequential(urls)
    print(f"Получено ответов: {len(results)}")


if __name__ == "__main__":
    asyncio.run(main())