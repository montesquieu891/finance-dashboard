from typing import Any, cast

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text

from app.cache import create_redis_client
from app.config import settings
from app.db import create_engine
from app.errors import APIError, api_error_handler, error_payload, validation_error_handler
from app.models import ReturnDaily
from app.routers.baskets import router as baskets_router
from app.routers.correlation import router as correlation_router
from app.routers.instruments import router as instruments_router
from app.routers.performance import router as performance_router
from app.routers.risk import router as risk_router
from app.routers.weights import router as weights_router

app = FastAPI(title="Basket Monitor API", version="0.1.0")
app.include_router(instruments_router, prefix="/api/v1")
app.include_router(baskets_router, prefix="/api/v1")
app.include_router(performance_router, prefix="/api/v1")
app.include_router(weights_router, prefix="/api/v1")
app.include_router(risk_router, prefix="/api/v1")
app.include_router(correlation_router, prefix="/api/v1")

app.add_exception_handler(APIError, cast(Any, api_error_handler))
app.add_exception_handler(RequestValidationError, cast(Any, validation_error_handler))


@app.middleware("http")
async def require_api_key(request: Request, call_next):  # type: ignore[no-untyped-def]
    if request.url.path in {"/docs", "/openapi.json", "/redoc"}:
        return await call_next(request)

    api_key = request.headers.get("X-API-Key")
    if api_key != settings.api_key:
        return JSONResponse(
            status_code=401,
            content=error_payload("UNAUTHORIZED", "Invalid or missing API key.", 401),
        )

    return await call_next(request)


@app.get("/health")
async def health() -> dict[str, str | None]:
    db_status = "ok"
    redis_status = "ok"
    data_freshness: str | None = None

    engine = create_engine()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            latest_returns_date = await conn.scalar(select(func.max(ReturnDaily.date)))
            if latest_returns_date is not None:
                data_freshness = latest_returns_date.isoformat()
    except Exception:
        db_status = "error"
    finally:
        await engine.dispose()

    redis_client = create_redis_client()
    try:
        await redis_client.ping()
    except Exception:
        redis_status = "error"
    finally:
        await redis_client.aclose()

    status = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return {
        "status": status,
        "db": db_status,
        "redis": redis_status,
        "data_freshness": data_freshness,
        "environment": settings.app_env,
    }
