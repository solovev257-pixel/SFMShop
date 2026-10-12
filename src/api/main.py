import asyncio
import json
import logging
from contextlib import asynccontextmanager

import aiohttp
import asyncpg
import redis.asyncio as aioredis
from fastapi import APIRouter, BackgroundTasks, FastAPI, Header, HTTPException, Response, status
from pydantic import BaseModel, Field

from src.database.async_repository import DB_CONFIG, ProductRepository
from src.services.async_service import process_orders_async

logger = logging.getLogger(__name__)

REVIEWS_API_URL = "https://api.reviews.sfmshop.ru/product"
REVIEWS_CACHE_TTL = 600  # 10 минут

resources: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Открываем пул БД, Redis и HTTP-сессию на старте, закрываем при остановке"""
    resources["pool"] = await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=5)
    resources["redis"] = aioredis.from_url("redis://localhost:6379", decode_responses=True)
    resources["http"] = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3))

    yield

    await resources["http"].close()
    await resources["redis"].aclose()
    await resources["pool"].close()


app = FastAPI(lifespan=lifespan)

# Товары для GET /products живут в памяти, как просит урок
products_data = [
    {"id": 1, "name": "Ноутбук", "price": 50000, "quantity": 10},
    {"id": 2, "name": "Мышь", "price": 1500, "quantity": 20},
    {"id": 3, "name": "Клавиатура", "price": 3000, "quantity": 15},
]

# Учебный токен: настоящая проверка появится в теме про безопасность
DEMO_TOKEN = "valid_token"


async def load_product(product_id: int) -> dict | None:
    """Товар из PostgreSQL через репозиторий"""
    repository = ProductRepository(resources["pool"])
    return await repository.get_by_id(product_id)


async def load_reviews(product_id: int) -> list:
    """Отзывы: сначала ищем в кэше Redis, если нет - идём во внешний API"""
    cache_key = f"cache:reviews:{product_id}"

    cached_reviews = await resources["redis"].get(cache_key)
    if cached_reviews is not None:
        return json.loads(cached_reviews)

    try:
        async with resources["http"].get(f"{REVIEWS_API_URL}/{product_id}") as response:
            response.raise_for_status()
            reviews = await response.json()
    except (aiohttp.ClientError, asyncio.TimeoutError):
        # Сервис отзывов недоступен - отдаём товар без отзывов
        return []

    await resources["redis"].setex(cache_key, REVIEWS_CACHE_TTL, json.dumps(reviews))
    return reviews


async def count_view(product_id: int) -> int:
    """Счётчик просмотров: incr в Redis атомарный, гонки нет"""
    return await resources["redis"].incr(f"views:product:{product_id}")


@app.get("/products")
def get_products(
    response: Response,
    authorization: str | None = Header(None),
):
    """Список товаров: пускаем только с токеном и разрешаем кэшировать ответ"""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Нужен заголовок Authorization: Bearer <токен>",
        )

    token = authorization.removeprefix("Bearer ")
    if token != DEMO_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен не подошёл",
        )

    response.headers["Cache-Control"] = "max-age=3600"
    return products_data


@app.get("/products/{product_id}/full")
async def get_product_full(product_id: int):
    """Товар, отзывы и просмотры - три источника параллельно"""
    product, reviews, views = await asyncio.gather(
        load_product(product_id),
        load_reviews(product_id),
        count_view(product_id),
    )

    if product is None:
        raise HTTPException(status_code=404, detail="Товар не найден")

    product["price"] = float(product["price"])
    return {**product, "reviews": reviews, "views": views}


class OrdersRequest(BaseModel):
    """Тело запроса: список id заказов, от 1 до 1000 штук"""
    order_ids: list[int] = Field(min_length=1, max_length=1000)


@app.post("/orders/process")
async def process_orders_endpoint(request: OrdersRequest):
    """Обработать заказы параллельно и сразу вернуть итог"""
    try:
        results = await process_orders_async(request.order_ids)
    except Exception as error:
        logger.exception("Сбой при обработке заказов")
        raise HTTPException(status_code=500, detail="Не удалось обработать заказы") from error

    failed = [result for result in results if result["status"] == "failed"]
    return {
        "status": "success" if not failed else "partial",
        "processed": len(results) - len(failed),
        "failed": len(failed),
        "results": results,
    }


@app.post("/orders/process-background", status_code=status.HTTP_202_ACCEPTED)
async def process_orders_background(request: OrdersRequest, background_tasks: BackgroundTasks):
    """Принять заказы и обработать их в фоне, уже после ответа"""
    background_tasks.add_task(process_orders_async, request.order_ids)
    return {
        "status": "accepted",
        "orders": len(request.order_ids),
        "message": "Обработка заказов запущена в фоне",
    }

v1_router = APIRouter(prefix="/api/v1", tags=["v1"])
@v1_router.get("/products")

def get_products_v1():
    """Версия 1: простой ответ, только список товаров"""
    return {"products": products_data}


v2_router = APIRouter(prefix="/api/v2", tags=["v2"])

@v2_router.get("/products")
def get_products_v2():
    """Версия 2: товары внутри data и служебная информация в metadata"""
    return {
        "data": {"products": products_data}, "metadata": {
            "total": len(products_data),
            "version": "v2"
        },
    }

app.include_router(v1_router)
app.include_router(v2_router)

