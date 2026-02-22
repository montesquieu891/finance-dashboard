from fastapi import FastAPI
from sqlalchemy import text

from app.cache import create_redis_client
from app.config import settings
from app.db import create_engine
from app.routers.instruments import router as instruments_router

app = FastAPI(title="Basket Monitor API", version="0.1.0")
app.include_router(instruments_router, prefix="/api/v1")


@app.get("/health")
async def health() -> dict[str, str]:
    db_status = "ok"
    redis_status = "ok"

    engine = create_engine()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
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
        await redis_client.close()

    status = "ok" if db_status == "ok" and redis_status == "ok" else "degraded"
    return {
        "status": status,
        "db": db_status,
        "redis": redis_status,
        "environment": settings.app_env,
    }
