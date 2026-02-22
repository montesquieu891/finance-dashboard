from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import analytics_cache_key, analytics_cache_ttl, get_cached_json, set_cached_json
from app.db import get_db
from app.schemas.analytics import BasketConfigRequest, PerformancePoint, PerformanceResponse
from app.services.analytics_api import (
    build_drawdown_series,
    build_risk_metrics,
    prepare_analytics,
)

router = APIRouter(prefix="/analytics/performance", tags=["performance"])


@router.post("", response_model=PerformanceResponse)
async def analytics_performance(
    config: BasketConfigRequest,
    db: AsyncSession = Depends(get_db),
) -> PerformanceResponse:
    config_payload = config.model_dump(mode="json")
    key = analytics_cache_key("performance", config_payload)
    cached = await get_cached_json(key)
    if cached is not None:
        return PerformanceResponse.model_validate(cached)

    prepared = await prepare_analytics(db=db, config=config)
    risk_metrics = build_risk_metrics(prepared)
    drawdown = build_drawdown_series(prepared.basket_series)
    basket_index = (1.0 + prepared.basket_series).cumprod() * 100.0

    if prepared.benchmark_series is not None:
        benchmark_index = (1.0 + prepared.benchmark_series).cumprod() * 100.0
        benchmark_index = benchmark_index.reindex(basket_index.index).ffill().fillna(100.0)
    else:
        benchmark_index = basket_index * 0 + 100.0

    series = [
        PerformancePoint(
            date=index_date,
            basket_return=float(basket_index.loc[index_date]),
            benchmark_return=float(benchmark_index.loc[index_date]),
            drawdown=float(drawdown.loc[index_date]),
        )
        for index_date in basket_index.index
    ]

    response = PerformanceResponse(
        series=series, metrics=risk_metrics, weights=prepared.method_weights
    )
    ttl = analytics_cache_ttl(end_date=config.end_date, today=date.today())
    await set_cached_json(key, response.model_dump(mode="json"), ttl)
    return response
