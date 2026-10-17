import logging
from itertools import count

from src.clients.payment_client import PaymentClient, PaymentServiceUnavailable
from src.models.order import Order, OrderCreate, OrderStatus

logger = logging.getLogger(__name__)


class OrderService:
    """Бизнес-логика заказов; хранилище в памяти вместо отдельной БД сервиса"""

    def __init__(self, payment_client: PaymentClient | None = None):
        self.payment_client = payment_client or PaymentClient()
        self._orders: dict[int, Order] = {}
        self._ids = count(1)

    async def create_order(self, data: OrderCreate) -> Order:
        total = round(sum(item.price * item.quantity for item in data.items), 2)
        order = Order(
            id=next(self._ids),
            user_id=data.user_id,
            items=data.items,
            total=total,
            status=OrderStatus.PENDING,
        )
        # Заказ сохраняется до вызова оплаты, чтобы его статус был виден при любом исходе
        self._orders[order.id] = order

        try:
            payment = await self.payment_client.pay(order.id, order.total)
        except PaymentServiceUnavailable as error:
            logger.warning("Заказ %s: payment-service недоступен (%s)", order.id, error)
            order.status = OrderStatus.PAYMENT_UNAVAILABLE
            return order

        if payment.get("status") == "success":
            order.status = OrderStatus.PAID
            order.payment_id = str(payment.get("id")) if payment.get("id") is not None else None
        else:
            # Компенсация: оплата отклонена, заказ отменяется
            order.status = OrderStatus.CANCELLED
        return order

    async def get_order(self, order_id: int) -> Order | None:
        return self._orders.get(order_id)
