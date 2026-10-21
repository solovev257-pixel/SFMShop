import logging

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status

from src.api.schemas import ProductCreate, ProductUpdate
from src.database.async_repository import ProductRepository
from src.dependencies import get_current_user, get_product_repository
from src.services.cache_service import get_product_cached, get_products_cached, invalidate_products
from src.services.exchange_client import AsyncExchangeClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/products", tags=["products"])

exchange_client = AsyncExchangeClient()


def log_catalog_change(action: str, product_id: int, user_id: int) -> None:
    """Фоновая задача: запись в журнал после ответа клиенту"""
    logger.info("Каталог: %s товара %s пользователем %s", action, product_id, user_id)


@router.get("")
async def list_products(
    response: Response,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repo: ProductRepository = Depends(get_product_repository),
):
    page, from_cache = await get_products_cached(repo, limit, offset)
    response.headers["X-Cache"] = "HIT" if from_cache else "MISS"
    response.headers["Cache-Control"] = "public, max-age=60"
    return page


@router.get("/{product_id}")
async def get_product(
    product_id: int,
    response: Response,
    repo: ProductRepository = Depends(get_product_repository),
):
    product, from_cache = await get_product_cached(repo, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
    response.headers["X-Cache"] = "HIT" if from_cache else "MISS"
    return product


@router.get("/{product_id}/price")
async def get_product_price(
    product_id: int,
    currency: str = Query("USD", min_length=3, max_length=3),
    repo: ProductRepository = Depends(get_product_repository),
):
    """Цена товара в другой валюте через внешний API курсов"""
    product, _ = await get_product_cached(repo, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")

    converted = await exchange_client.convert(product["price"], "RUB", currency)
    if converted is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Сервис курсов валют недоступен, попробуйте позже",
        )
    return {"id": product_id, "price_rub": product["price"], "currency": currency.upper(), "price": converted}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(
    data: ProductCreate,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user),
    repo: ProductRepository = Depends(get_product_repository),
):
    product_id = await repo.create(data.name, data.price, data.quantity)
    await invalidate_products()
    background_tasks.add_task(log_catalog_change, "создание", product_id, current_user_id)
    return {"id": product_id, **data.model_dump()}


@router.patch("/{product_id}")
async def update_product(
    product_id: int,
    data: ProductUpdate,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user),
    repo: ProductRepository = Depends(get_product_repository),
):
    product = await repo.update(product_id, data.model_dump(exclude_unset=True, exclude_none=True))
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
    await invalidate_products()
    background_tasks.add_task(log_catalog_change, "изменение", product_id, current_user_id)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user),
    repo: ProductRepository = Depends(get_product_repository),
):
    try:
        deleted = await repo.delete(product_id)
    except asyncpg.ForeignKeyViolationError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Товар есть в заказах, удалить нельзя")
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Товар не найден")
    await invalidate_products()
    background_tasks.add_task(log_catalog_change, "удаление", product_id, current_user_id)