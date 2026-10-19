import time
from typing import Optional

import requests
from requests.exceptions import ConnectionError, RequestException, Timeout


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