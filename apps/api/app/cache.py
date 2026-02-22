import hashlib
import json
from collections.abc import Mapping
from datetime import date
from typing import Any

from redis.asyncio import Redis

from app.config import settings


def create_redis_client() -> Redis:
    return Redis(host=settings.redis_host, port=settings.redis_port, decode_responses=True)


def analytics_cache_key(endpoint: str, config_payload: Mapping[str, Any]) -> str:
    serialized = json.dumps(config_payload, sort_keys=True, separators=(",", ":"), default=str)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"analytics:{endpoint}:{digest}"


def analytics_cache_ttl(end_date: date, today: date) -> int:
    if end_date < today:
        return settings.redis_ttl_historical_seconds
    return settings.redis_ttl_live_seconds


async def get_cached_json(key: str) -> dict[str, Any] | None:
    client = create_redis_client()
    try:
        payload = await client.get(key)
        if payload is None:
            return None
        parsed = json.loads(payload)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None
    finally:
        await client.aclose()
    return None


async def set_cached_json(key: str, value: Mapping[str, Any], ttl_seconds: int) -> None:
    client = create_redis_client()
    try:
        serialized = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
        await client.set(key, serialized, ex=ttl_seconds)
    except Exception:
        pass
    finally:
        await client.aclose()
