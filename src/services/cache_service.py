import json
import redis
import secrets
from datetime import datetime
from src.database.queries import get_all_products_from_db, get_product_by_id_from_db

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

def get_cached_products():
    cache_key = "products:all"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    products = get_all_products_from_db()
    redis_client.setex(cache_key, 3600, json.dumps(products))
    return products

def get_cached_product(product_id):
    cache_key = f"product:{product_id}"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)
    product = get_product_by_id_from_db(product_id)
    if product:
        redis_client.setex(cache_key, 3600, json.dumps(product))
    return product

def create_user_session(user_id):
    session_token = secrets.token_urlsafe(32)
    session_key = f"session:{session_token}"
    session_data = {"user_id": user_id, "created_at": datetime.now().isoformat()}
    redis_client.setex(session_key, 86400, json.dumps(session_data))
    return session_token

def get_user_session(session_token):
    session_key = f"session:{session_token}"
    cached = redis_client.get(session_key)
    if cached:
        return json.loads(cached)
    return None

def delete_user_session(session_token):
    session_key = f"session:{session_token}"
    redis_client.delete(session_key)


if __name__ == "__main__":
    session_token = create_user_session(user_id=1)
    print(f"Сессия создана: {session_token}")

    session = get_user_session(session_token)
    print(f"Сессия: {session}")