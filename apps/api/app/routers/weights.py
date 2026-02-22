from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import analytics_cache_key, analytics_cache_ttl, get_cached_json, set_cached_json
from app.db import get_db
from app.schemas.analytics import BasketConfigRequest, WeightsResponse
from app.services.analytics_api import prepare_analytics

router = APIRouter(prefix="/analytics/weights", tags=["weights"])


@router.post("", response_model=WeightsResponse)
async def analytics_weights(
    config: BasketConfigRequest,
    db: AsyncSession = Depends(get_db),
) -> WeightsResponse:
    config_payload = config.model_dump(mode="json")
    key = analytics_cache_key("weights", config_payload)
    cached = await get_cached_json(key)
    if cached is not None:
        return WeightsResponse.model_validate(cached)

    prepared = await prepare_analytics(db=db, config=config)
    response = WeightsResponse(weights=prepared.method_weights)
    ttl = analytics_cache_ttl(end_date=config.end_date, today=date.today())
    await set_cached_json(key, response.model_dump(mode="json"), ttl)
    return response
