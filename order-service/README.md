# order-service

Микросервис заказов SFMShop. Создаёт заказ и оплачивает его через payment-service по HTTP.

## Структура

```
src/api/main.py                 FastAPI-приложение
src/api/routes/orders.py        эндпоинты заказов
src/models/order.py             модели и статусы заказа
src/services/order_service.py   бизнес-логика
src/clients/payment_client.py   HTTP-клиент payment-service
```

## Эндпоинты

- `POST /api/v1/orders` — создать заказ и отправить оплату в payment-service
- `GET /api/v1/orders/{id}` — получить заказ, 404 если его нет

## Статусы заказа

`pending` → `paid` (оплата прошла) или `cancelled` (оплата отклонена).
`payment_unavailable` — payment-service не ответил; заказ сохранён, POST возвращает 503.

## Запуск

```
cd order-service
pip install -r requirements.txt
uvicorn src.api.main:app --port 8001
```

Адрес payment-service задаётся переменной окружения `PAYMENT_SERVICE_URL`
(по умолчанию `http://payment-service:8002`).
