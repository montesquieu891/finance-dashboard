from redis.asyncio import Redis

from app.config import settings


def create_redis_client() -> Redis:
    return Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)
