from enum import Enum

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    PENDING = "pending"                          # создан, оплата ещё не подтверждена
    PAID = "paid"                                # payment-service подтвердил оплату
    CANCELLED = "cancelled"                      # payment-service отклонил оплату
    PAYMENT_UNAVAILABLE = "payment_unavailable"  # payment-service не ответил, нужна повторная попытка


class OrderItem(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0)
    price: float = Field(gt=0)


class OrderCreate(BaseModel):
    user_id: int = Field(gt=0)
    items: list[OrderItem] = Field(min_length=1)


class Order(BaseModel):
    id: int
    user_id: int
    items: list[OrderItem]
    total: float
    status: OrderStatus
    payment_id: str | None = None
