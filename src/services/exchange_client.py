import asyncio
import logging
import time
from typing import Optional

import httpx
import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

logger = logging.getLogger(__name__)


class ExchangeClient:
    """Клиент для работы с API курсов валют"""

    def __init__(self, base_url: str = "https://api.exchangerate-api.com/v4/latest"):
        self.base_url = base_url
        self.timeout = 5
        self.max_retries = 3

    def get_exchange_rate(self, base_currency: str, target_currency: str) -> Optional[float]:
        for attempt in range(self.max_retries):
            try:
                response = requests.get(f"{self.base_url}/{base_currency}", timeout=self.timeout)
                response.raise_for_status()
                rates = response.json().get("rates", {})
                if target_currency not in rates:
                    print(f"Валюта {target_currency} не найдена")
                    return None
                return rates[target_currency]
            except (Timeout, ConnectionError):
                if attempt < self.max_retries - 1:
                    delay = 2 ** attempt
                    print(f"Ошибка сети, повтор через {delay} сек...")
                    time.sleep(delay)
                else:
                    print("API недоступен после всех попыток")
                    return None
            except RequestException as error:
                print(f"Ошибка запроса: {error}")
                return None
        return None


class AsyncExchangeClient:
    """Асинхронный клиент курсов валют на httpx: не блокирует event loop"""

    def __init__(
        self,
        base_url: str = "https://api.exchangerate-api.com/v4/latest",
        timeout: float = 5.0,
        max_retries: int = 3,
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries

    async def get_exchange_rate(self, base: str, target: str) -> Optional[float]:
        """Курс base -> target; повтор с паузой 1, 2, 4 с при сетевых ошибках и 5xx"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(self.max_retries):
                try:
                    response = await client.get(f"{self.base_url}/{base.upper()}")
                    if response.status_code >= 500:
                        raise httpx.HTTPStatusError("ошибка сервера", request=response.request, response=response)
                    response.raise_for_status()
                    rates = response.json().get("rates", {})
                    rate = rates.get(target.upper())
                    if rate is None:
                        logger.warning("Валюта %s не найдена в ответе", target)
                    return rate
                except (httpx.TimeoutException, httpx.TransportError, httpx.HTTPStatusError) as error:
                    is_client_error = (
                        isinstance(error, httpx.HTTPStatusError) and error.response.status_code < 500
                    )
                    if is_client_error or attempt == self.max_retries - 1:
                        logger.warning("Курс %s->%s не получен: %s", base, target, error)
                        return None
                    delay = 2 ** attempt
                    logger.info("Попытка %d не удалась, повтор через %d с", attempt + 1, delay)
                    await asyncio.sleep(delay)
                except ValueError as error:
                    logger.warning("Ответ API не разобран: %s", error)
                    return None
        return None

    async def convert(self, amount: float, base: str, target: str) -> Optional[float]:
        if base.upper() == target.upper():
            return round(amount, 2)
        rate = await self.get_exchange_rate(base, target)
        return round(amount * rate, 2) if rate is not None else None