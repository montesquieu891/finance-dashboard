from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.config import settings


def postgres_dsn() -> str:
    return (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


def create_engine() -> AsyncEngine:
    return create_async_engine(postgres_dsn(), pool_pre_ping=True)
