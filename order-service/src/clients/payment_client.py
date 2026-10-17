import os

import httpx


class PaymentServiceUnavailable(Exception):
    """payment-service не ответил или вернул ошибку сервера"""


class PaymentClient:
    """HTTP-клиент для payment-service"""

    def __init__(self, base_url: str | None = None, timeout: float = 3.0):
        # Адрес берётся из окружения; в docker-compose это имя сервиса-соседа
        self.base_url = base_url or os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8002")
        self.timeout = httpx.Timeout(timeout, connect=2.0)

    async def pay(self, order_id: int, amount: float) -> dict:
        """Отправить платёж; ключ идемпотентности защищает от двойного списания при повторе"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/payments",
                    json={"order_id": order_id, "amount": amount},
                    headers={"Idempotency-Key": f"order-{order_id}"},
                )
        except httpx.HTTPError as error:
            # Таймаут, отказ в соединении, неизвестный хост
            raise PaymentServiceUnavailable(str(error)) from error

        if response.status_code >= 500:
            raise PaymentServiceUnavailable(f"payment-service ответил {response.status_code}")
        if response.status_code >= 400:
            return {"status": "declined", "reason": response.text}
        return response.json()
