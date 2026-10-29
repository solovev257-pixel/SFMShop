import logging

import asyncpg
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status

from src.api.schemas import OrderCreate
from src.database.async_repository import OrderRepository
from src.dependencies import get_current_user, get_order_repository
from src.services.cache_service import invalidate_products
from src.services.queue_producer import QueueProducer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/orders", tags=["orders"])

# один producer на всё приложение: соединение открывается при первой задаче
producer = QueueProducer()


async def send_order_confirmation(order_id: int, user_id: int, total: float) -> None:
    """Фоновая задача: уведомление о заказе уходит уже после ответа клиенту"""
    logger.info("Уведомление: заказ %s на %.2f руб. оформлен для пользователя %s", order_id, total, user_id)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_order(
    data: OrderCreate,
    background_tasks: BackgroundTasks,
    current_user_id: int = Depends(get_current_user),
    orders: OrderRepository = Depends(get_order_repository),
):
    items = [item.model_dump() for item in data.items]
    try:
        order = await orders.create(current_user_id, items)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    except asyncpg.ForeignKeyViolationError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Пользователь не найден")

    await invalidate_products()
    background_tasks.add_task(send_order_confirmation, order.id, current_user_id, order.total)

    # тяжёлую работу отдаём в очередь RabbitMQ, клиенту отвечаем сразу
    producer.send_order_task(order.id, "send_email", {"user_id": current_user_id})
    producer.send_order_task(order.id, "update_stock", {"items": items})
    producer.send_order_task(order.id, "generate_report", {})

    return {"id": order.id, "total": order.total, "status": order.status}


@router.get("")
async def list_my_orders(
    current_user_id: int = Depends(get_current_user),
    orders: OrderRepository = Depends(get_order_repository),
):
    return {"orders": await orders.list_by_user(current_user_id)}


@router.get("/{order_id}")
async def get_my_order(
    order_id: int,
    current_user_id: int = Depends(get_current_user),
    orders: OrderRepository = Depends(get_order_repository),
):
    order = await orders.get_by_id(order_id)
    # Чужой и несуществующий заказ дают одинаковый ответ (защита от BOLA/IDOR)
    if order is None or order.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заказ не найден")
    return {"id": order.id, "total": order.total, "status": order.status}