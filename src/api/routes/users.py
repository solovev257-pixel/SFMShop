import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from src.api.auth import create_access_token, hash_password, verify_password
from src.api.schemas import TokenResponse, UserLogin, UserRegister
from src.database.async_repository import UserRepository
from src.dependencies import get_current_user, get_user_repository

router = APIRouter(tags=["users"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, users: UserRepository = Depends(get_user_repository)):
    try:
        user_id = await users.create(data.name, data.email, hash_password(data.password))
    except asyncpg.UniqueViolationError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email уже зарегистрирован")
    return {"id": user_id, "email": data.email}


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, users: UserRepository = Depends(get_user_repository)):
    user = await users.get_by_email(data.email)
    # Одинаковый ответ для "нет пользователя" и "неверный пароль": не подсказываем, какие email есть в базе
    if user is None or not user["password_hash"] or not verify_password(data.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный email или пароль")
    return TokenResponse(access_token=create_access_token(user["id"]))


@router.get("/users/me")
async def read_me(
    current_user_id: int = Depends(get_current_user),
    users: UserRepository = Depends(get_user_repository),
):
    user = await users.get_by_id(current_user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пользователь не найден")
    return user