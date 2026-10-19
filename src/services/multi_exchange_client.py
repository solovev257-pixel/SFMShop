import logging
import time
from typing import List, Optional

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout

logger = logging.getLogger(__name__)


class MultiExchangeClient:
    """Курсы валют из нескольких API: если один недоступен, берём следующий."""

    def __init__(self, api_urls: List[str], timeout: float = 5.0, retries_per_api: int = 2):
        if not api_urls:
            raise ValueError("Нужен хотя бы один URL API")
        self.api_urls = list(api_urls)
        self.timeout = timeout
        self.retries_per_api = retries_per_api

    def _fetch_from(self, api_url: str, base: str, target: str) -> Optional[float]:
        """Один API: повторы при сетевых ошибках. None, если курс не получен."""
        url = f"{api_url}/{base}"
        for attempt in range(1, self.retries_per_api + 1):
            logger.info("Запрос к %s (попытка %d из %d)", api_url, attempt, self.retries_per_api)
            try:
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()
                rates = response.json().get("rates", {})
            except (Timeout, ConnectionError) as error:
                logger.warning("%s не отвечает: %s", api_url, error)
                if attempt < self.retries_per_api:
                    time.sleep(2 ** (attempt - 1))
                continue
            except (RequestException, ValueError) as error:
                logger.warning("%s вернул ошибку: %s", api_url, error)
                return None

            if target not in rates:
                logger.warning("В ответе %s нет валюты %s", api_url, target)
                return None
            return float(rates[target])
        return None

    def get_exchange_rate(self, base: str, target: str) -> Optional[float]:
        for api_url in self.api_urls:
            rate = self._fetch_from(api_url, base, target)
            if rate is not None:
                logger.info("Курс %s->%s = %s получен из %s", base, target, rate, api_url)
                return rate
            logger.info("%s не дал курс, пробуем следующий API", api_url)
        logger.error("Все API недоступны, курс %s->%s не получен", base, target)
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    client = MultiExchangeClient([
        "http://127.0.0.1:9",  # заведомо недоступный адрес, проверка fallback
        "https://api.exchangerate-api.com/v4/latest",
    ])
    print("USD -> RUB:", client.get_exchange_rate("USD", "RUB"))