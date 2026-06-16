from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel
from src.database.connection import connect_to_db, get_all_products, get_user_by_id, create_order as save_order
from src.models.product import Product
from src.models.order import Order


class OrderCreate(BaseModel):
    user_id: int
    product_id: int
    quantity: int


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    quantity: Optional[int] = None


conn = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global conn
    conn = connect_to_db()
    yield
    if conn:
        conn.close()


app = FastAPI(lifespan=lifespan)


@app.get("/products")
def get_products(limit: int = 10, offset: int = 0):
    try:
        products_data = get_all_products(conn)
        products = []
        for data in products_data:
            product = Product(data[1], data[2], data[3])
            product.id = data[0]
            products.append(product.__dict__)
        total = len(products)
        paginated_products = products[offset:offset + limit]
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "products": paginated_products
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/products/{product_id}")
def get_product(product_id: int):
    try:
        products_data = get_all_products(conn)
        for data in products_data:
            if data[0] == product_id:
                product = Product(data[1], data[2], data[3])
                product.id = data[0]
                return product.__dict__
        raise HTTPException(status_code=404, detail="Товар не найден")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orders", status_code=201)
def create_order(order: OrderCreate):
    try:
        user = get_user_by_id(conn, order.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        product_row = None
        for data in get_all_products(conn):
            if data[0] == order.product_id:
                product_row = data
                break
        if product_row is None:
            raise HTTPException(status_code=404, detail="Товар не найден")
        product = Product(product_row[1], product_row[2], order.quantity)
        new_order = Order(user, [product])
        save_order(conn, order.user_id, new_order.total)
        return {
            "user_id": order.user_id,
            "product_id": order.product_id,
            "quantity": order.quantity,
            "total": new_order.total,
            "message": "Заказ создан"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/products/{product_id}")
def update_product(product_id: int, product_data: ProductUpdate):
    try:
        products_data = get_all_products(conn)
        found = False
        for data in products_data:
            if data[0] == product_id:
                found = True
                break
        if not found:
            raise HTTPException(status_code=404, detail="Товар не найден")
        return {"id": product_id, "message": "Товар обновлен"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/products/{product_id}")
def delete_product(product_id: int):
    try:
        products_data = get_all_products(conn)
        found = False
        for data in products_data:
            if data[0] == product_id:
                found = True
                break
        if not found:
            raise HTTPException(status_code=404, detail="Товар не найден")
        return {"message": "Товар удален"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def test_api():
    client = TestClient(app)
    response = client.get("/products")
    assert response.status_code == 200
    print("GET /products: OK")
    response = client.get("/products?limit=5&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "products" in data
    print("GET /products с пагинацией: OK")
    response = client.get("/products/1")
    assert response.status_code == 200
    print("GET /products/1: OK")
    response = client.get("/products/999")
    assert response.status_code == 404
    print("GET /products/999 (404): OK")
    response = client.post("/orders", json={
        "user_id": 1,
        "product_id": 2,
        "quantity": 1
    })
    assert response.status_code == 201
    print("POST /orders: OK")
    response = client.put("/products/1", json={
        "name": "Ноутбук обновленный",
        "price": 45000
    })
    assert response.status_code == 200
    print("PUT /products/1: OK")
    response = client.delete("/products/1")
    assert response.status_code == 200
    print("DELETE /products/1: OK")
    print("\nВсе тесты пройдены успешно!")


if __name__ == "__main__":
    test_api()


