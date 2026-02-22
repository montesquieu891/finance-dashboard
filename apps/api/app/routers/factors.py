from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache import get_cached_json, set_cached_json
from app.db import get_db
from app.models import FactorDefinition
from app.schemas.analytics import (
    FactorDefinitionResponse,
    FactorsExposuresRequest,
    FactorsRequest,
    FactorsResponse,
)
from app.services.factors_api import build_factors_exposures_by_ids, build_factors_response

router = APIRouter(prefix="/analytics/factors", tags=["factors"])


@router.get("/definitions", response_model=list[FactorDefinitionResponse])
async def list_factor_definitions(
    db: AsyncSession = Depends(get_db),
) -> list[FactorDefinitionResponse]:
    stmt = (
        select(FactorDefinition)
        .where(FactorDefinition.is_active.is_(True))
        .order_by(FactorDefinition.code)
    )
    factors = list((await db.execute(stmt)).scalars().all())
    return [
        FactorDefinitionResponse(
            code=factor.code,
            name=factor.name,
            category=factor.category,
            proxy_symbol=factor.proxy_symbol,
        )
        for factor in factors
    ]


@router.post("", response_model=FactorsResponse)
async def analytics_factors(
    request: FactorsRequest,
    db: AsyncSession = Depends(get_db),
) -> FactorsResponse:
    cache_key = (
        f"analytics:factors:{request.config.basket_id}:{request.config.start_date}:{request.config.end_date}:"
        + (
            f"{request.config.weight_method}:{request.rolling_window}:"
            f"{','.join(sorted(request.factor_codes or []))}"
        )
    )
    cached = await get_cached_json(cache_key)
    if cached is not None:
        return FactorsResponse.model_validate(cached)

    response = await build_factors_response(db=db, request=request)
    await set_cached_json(cache_key, response.model_dump(mode="json"), ttl_seconds=3600)
    return response


@router.post("/exposures", response_model=FactorsResponse)
async def analytics_factors_exposures(
    request: FactorsExposuresRequest,
    db: AsyncSession = Depends(get_db),
) -> FactorsResponse:
    factor_id_key = ",".join(sorted(str(factor_id) for factor_id in request.factor_ids))
    cache_key = (
        f"analytics:factors:exposures:{request.config.basket_id}:{request.config.start_date}:"
        f"{request.config.end_date}:{request.rolling_window}:{factor_id_key}"
    )
    cached = await get_cached_json(cache_key)
    if cached is not None:
        return FactorsResponse.model_validate(cached)

    response = await build_factors_exposures_by_ids(
        db=db,
        factor_ids=request.factor_ids,
        rolling_window=request.rolling_window,
        request_config=request.config,
    )
    await set_cached_json(cache_key, response.model_dump(mode="json"), ttl_seconds=3600)
    return response
