import json
import logging
import time

import redis.asyncio as redis
from redis.exceptions import RedisError

from src.core.config import settings

logger = logging.getLogger(__name__)

PRODUCTS_TTL = 300  # 5 минут: компромисс между свежестью каталога и нагрузкой на БД
REDIS_RETRY_AFTER = 30  # если Redis упал, не дёргаем его 30 секунд

redis_client = redis.from_url(
    settings.redis_url,
    decode_responses=True,
    socket_connect_timeout=0.5,
    socket_timeout=0.5,
)

_redis_down_until = 0.0


def _redis_available() -> bool:
    return time.monotonic() >= _redis_down_until


def _mark_redis_down(error: Exception) -> None:
    """Запомнить, что Redis недоступен, и какое-то время работать без кэша"""
    global _redis_down_until
    _redis_down_until = time.monotonic() + REDIS_RETRY_AFTER
    logger.warning("Redis недоступен, работаем без кэша %s с: %s", REDIS_RETRY_AFTER, error)


async def cache_get(key: str):
    if not _redis_available():
        return None
    try:
        raw = await redis_client.get(key)
    except (RedisError, OSError) as error:
        _mark_redis_down(error)
        return None
    return json.loads(raw) if raw is not None else None


async def cache_set(key: str, value, ttl: int = PRODUCTS_TTL) -> None:
    if not _redis_available():
        return
    try:
        await redis_client.setex(key, ttl, json.dumps(value, ensure_ascii=False, default=str))
    except (RedisError, OSError) as error:
        _mark_redis_down(error)


async def invalidate_products() -> None:
    """Сбросить кэш каталога после изменения товаров"""
    if not _redis_available():
        return
    try:
        keys = [key async for key in redis_client.scan_iter(match="products:*")]
        if keys:
            await redis_client.delete(*keys)
    except (RedisError, OSError) as error:
        _mark_redis_down(error)


async def get_products_cached(repo, limit: int, offset: int) -> tuple[dict, bool]:
    """Страница каталога: сначала Redis, потом БД. Возвращает (данные, попали_в_кэш)"""
    key = f"products:list:{limit}:{offset}"
    cached = await cache_get(key)
    if cached is not None:
        return cached, True

    products = await repo.list_products(limit=limit, offset=offset)
    total = await repo.count()
    page = {"products": products, "total": total, "limit": limit, "offset": offset}
    await cache_set(key, page)
    return page, False


async def get_product_cached(repo, product_id: int) -> tuple[dict | None, bool]:
    key = f"products:item:{product_id}"
    cached = await cache_get(key)
    if cached is not None:
        return cached, True

    product = await repo.get_by_id(product_id)
    if product is not None:
        await cache_set(key, product)
    return product, False


async def close_cache() -> None:
    try:
        await redis_client.aclose()
    except (RedisError, OSError):
        pass