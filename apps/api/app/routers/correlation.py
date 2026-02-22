from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import analytics_cache_key, analytics_cache_ttl, get_cached_json, set_cached_json
from app.db import get_db
from app.schemas.analytics import BasketConfigRequest, CorrelationResponse
from app.services.analytics_api import build_correlation_matrix, prepare_analytics

router = APIRouter(prefix="/analytics/correlation", tags=["correlation"])


@router.post("", response_model=CorrelationResponse)
async def analytics_correlation(
    config: BasketConfigRequest,
    db: AsyncSession = Depends(get_db),
) -> CorrelationResponse:
    config_payload = config.model_dump(mode="json")
    key = analytics_cache_key("correlation", config_payload)
    cached = await get_cached_json(key)
    if cached is not None:
        return CorrelationResponse.model_validate(cached)

    prepared = await prepare_analytics(db=db, config=config)
    response = CorrelationResponse(
        symbols=prepared.symbols,
        matrix=build_correlation_matrix(prepared, config.lookback_days),
    )
    ttl = analytics_cache_ttl(end_date=config.end_date, today=date.today())
    await set_cached_json(key, response.model_dump(mode="json"), ttl)
    return response
