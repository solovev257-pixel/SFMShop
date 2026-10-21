import asyncpg
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.auth import decode_access_token
from src.database.async_repository import OrderRepository, ProductRepository, UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


def get_pool(request: Request) -> asyncpg.Pool:
    """Пул соединений создаётся в lifespan и лежит в app.state"""
    return request.app.state.pool


def get_product_repository(pool: asyncpg.Pool = Depends(get_pool)) -> ProductRepository:
    return ProductRepository(pool)


def get_order_repository(pool: asyncpg.Pool = Depends(get_pool)) -> OrderRepository:
    return OrderRepository(pool)


def get_user_repository(pool: asyncpg.Pool = Depends(get_pool)) -> UserRepository:
    return UserRepository(pool)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    """Достаёт токен из Authorization: Bearer ..., возвращает id пользователя из sub"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Нужен заголовок Authorization: Bearer <токен>",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Токен недействителен или истёк",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id