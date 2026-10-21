import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

import asyncpg
from fastapi import Depends, FastAPI, Request, Response, status
from fastapi.responses import HTMLResponse
from openai import AsyncOpenAI

from src.api.routes import orders, products, users
from src.api.schemas import SupportRequest
from src.core.config import settings
from src.database.async_repository import DB_CONFIG
from src.dependencies import get_current_user, get_order_repository
from src.services.cache_service import close_cache, redis_client
from src.services.support_service import SupportAnswer, answer_support

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ADMIN_PAGE = Path(__file__).resolve().parents[2] / "templates" / "admin.html"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Пул соединений с БД живёт всё время работы приложения"""
    app.state.pool = await asyncpg.create_pool(**DB_CONFIG, min_size=1, max_size=10)
    yield
    await app.state.pool.close()
    await close_cache()


app = FastAPI(title="SFMShop API", lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Пишет в лог каждый запрос: метод, путь, статус и длительность"""
    started_at = time.perf_counter()
    logger.info("-> %s %s", request.method, request.url.path)

    response = await call_next(request)

    duration = time.perf_counter() - started_at
    logger.info("<- %s %s %s за %.3f с", request.method, request.url.path, response.status_code, duration)
    response.headers["X-Process-Time"] = f"{duration:.4f}"
    return response


app.include_router(products.router, prefix="/api/v1")
app.include_router(orders.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


async def get_llm_client():
    async with AsyncOpenAI(
        api_key=settings.llm_api_key or "no-key",
        base_url=settings.llm_base_url,
        max_retries=0,
    ) as client:
        yield client


@app.post("/api/v1/support", response_model=SupportAnswer, tags=["support"])
async def support(
    request: SupportRequest,
    current_user_id: int = Depends(get_current_user),
    order_repo=Depends(get_order_repository),
    client=Depends(get_llm_client),
):
    return await answer_support(
        question=request.question,
        current_user_id=current_user_id,
        order_repo=order_repo,
        client=client,
    )


@app.get("/admin", response_class=HTMLResponse, include_in_schema=False)
async def admin_page():
    return ADMIN_PAGE.read_text(encoding="utf-8")


@app.get("/health/live", tags=["health"])
async def liveness():
    return {"status": "alive"}


@app.get("/health/ready", tags=["health"])
async def readiness(response: Response):
    checks = {"database": False, "redis": False}
    try:
        await app.state.pool.fetchval("SELECT 1")
        checks["database"] = True
    except Exception:
        logger.warning("Readiness: база недоступна")
    try:
        checks["redis"] = bool(await redis_client.ping())
    except Exception:
        logger.info("Readiness: Redis недоступен, приложение работает без кэша")

    if not checks["database"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready", "checks": checks}
    return {"status": "ready", "checks": checks}