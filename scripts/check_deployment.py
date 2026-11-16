"""Сквозная проверка API на вымышленных данных в отдельном учебном стеке."""
import argparse
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4


def check_deployment(base_url: str):
    def request(method, path, payload=None, token=None, expected=200):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        body = None if payload is None else json.dumps(payload).encode()
        req = Request(f"{base_url.rstrip('/')}{path}", data=body, headers=headers, method=method)
        try:
            response = urlopen(req, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            assert response.status == expected, f"{method} {path} returned {response.status}"
            return json.load(response)

    assert request("GET", "/health/live")["status"] == "alive"
    readiness = request("GET", "/health/ready")
    assert readiness["checks"] == {"database": True, "redis": True}
    products = request("GET", "/api/v1/products")["products"]
    assert products, "Нет товаров для проверки"
    product = next(item for item in products if item["quantity"] > 0)
    request("POST", "/api/v1/support", {"question": "Доставка?"}, expected=401)

    def register_buyer():
        credentials = {"email": f"mentor-{uuid4().hex}@example.test", "password": uuid4().hex}
        request("POST", "/api/v1/register", {"name": "Учебный покупатель", **credentials}, expected=201)
        return request("POST", "/api/v1/login", credentials)["access_token"]

    owner_token = register_buyer()
    order = request("POST", "/api/v1/orders", {
        "items": [{"product_id": product["id"], "quantity": 1}],
    }, token=owner_token, expected=201)
    assert order["total"] == product["price"]
    own_order = request("GET", f"/api/v1/orders/{order['id']}", token=owner_token)
    assert own_order["id"] == order["id"]
    assert own_order["status"] == order["status"], "Статус POST не совпадает с сохранённым статусом"
    other_token = register_buyer()
    request("GET", f"/api/v1/orders/{order['id']}", token=other_token, expected=404)
    request("GET", f"/api/v1/orders/{order['id']}", expected=401)
    updated = request("GET", f"/api/v1/products/{product['id']}")
    assert updated["quantity"] == product["quantity"] - 1
    print("OK: health, PostgreSQL, Redis, регистрация, вход, создание заказа, остатки и защита чужого заказа")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    check_deployment(parser.parse_args().base_url)
