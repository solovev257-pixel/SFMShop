from fastapi import FastAPI

from src.api.routes import orders

app = FastAPI(
    title="Order Service",
    description="Микросервис заказов SFMShop",
    version="1.0.0",
)

app.include_router(orders.router, prefix="/api/v1")
