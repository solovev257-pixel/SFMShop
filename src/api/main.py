from fastapi import FastAPI, HTTPException
from fastapi import FastAPI
from pydantic import BaseModel
class OrderCreate(BaseModel):
    user_id: int
    product_id: int
    quantity: int
app = FastAPI()
@app.get("/")
def read_root():
    return {"message": "Добро пожаловать в SFMShop API"}
@app.get("/products")
def get_products(limit: int = 10, offset: int = 0):
    products = [
        {"id": 1, "name": "Ноутбук", "price": 50000},
        {"id": 2, "name": "Мышь", "price": 1500}
    ]
    return {
        "limit": limit,
        "offset": offset,
        "products": products
    }
@app.get("/products/{product_id}")
def get_product(product_id: int):
    products = {
        1: {"id": 1, "name": "Ноутбук", "price": 50000},
        2: {"id": 2, "name": "Мышь", "price": 1500}
    }
    if product_id not in products:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return products[product_id]
@app.post("/orders")

def create_order(order: OrderCreate):
    return {
        "id": 5,
        "user_id": order.user_id,
        "product_id": order.product_id,
        "quantity": order.quantity,
        "message": "Заказ создан"
    }

class UserCreate(BaseModel):
    name: str
    email: str

@app.get("/users")
def get_users():
    return [
        {"id": 1, "name": "Иван", "email": "ivan@mail.ru"},
        {"id": 2, "name": "Мария", "email": "maria@mail.ru"}
    ]

@app.get("/users/{user_id}")
def get_user(user_id: int):
    users = {
        1: {"id": 1, "name": "Иван", "email": "ivan@mail.ru"},
        2: {"id": 2, "name": "Мария", "email": "maria@mail.ru"}
    }
    if user_id not in users:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return users[user_id]

@app.post("/users", status_code=201)
def create_user(user: UserCreate):
    return {
        "id": 3,
        "name": user.name,
        "email": user.email,
        "message": "Пользователь создан"
    }


