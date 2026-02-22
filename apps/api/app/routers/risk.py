from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import analytics_cache_key, analytics_cache_ttl, get_cached_json, set_cached_json
from app.db import get_db
from app.schemas.analytics import BasketConfigRequest, RiskResponse
from app.services.analytics_api import build_risk_metrics, prepare_analytics

router = APIRouter(prefix="/analytics/risk", tags=["risk"])


@router.post("", response_model=RiskResponse)
async def analytics_risk(
    config: BasketConfigRequest,
    db: AsyncSession = Depends(get_db),
) -> RiskResponse:
    config_payload = config.model_dump(mode="json")
    key = analytics_cache_key("risk", config_payload)
    cached = await get_cached_json(key)
    if cached is not None:
        return RiskResponse.model_validate(cached)

    prepared = await prepare_analytics(db=db, config=config)
    response = RiskResponse(metrics=build_risk_metrics(prepared))
    ttl = analytics_cache_ttl(end_date=config.end_date, today=date.today())
    await set_cached_json(key, response.model_dump(mode="json"), ttl)
    return response
