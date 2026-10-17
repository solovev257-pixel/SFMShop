from fastapi import APIRouter, HTTPException, Response, status

from src.models.order import Order, OrderCreate, OrderStatus
from src.services.order_service import OrderService

router = APIRouter(tags=["orders"])
order_service = OrderService()


@router.post("/orders", response_model=Order, status_code=status.HTTP_201_CREATED)
async def create_order(data: OrderCreate, response: Response):
    order = await order_service.create_order(data)
    if order.status == OrderStatus.PAYMENT_UNAVAILABLE:
        # Заказ сохранён, но оплату подтвердить не удалось: сообщаем клиенту без падения сервиса
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return order


@router.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: int):
    order = await order_service.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Заказ {order_id} не найден")
    return order
