from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Factor
from app.schemas.analytics import FactorResponse

router = APIRouter(prefix="/factors", tags=["factors"])


@router.get("", response_model=list[FactorResponse])
async def list_factors(db: AsyncSession = Depends(get_db)) -> list[FactorResponse]:
    stmt = select(Factor).where(Factor.is_active.is_(True)).order_by(Factor.code)
    factors = list((await db.execute(stmt)).scalars().all())
    return [
        FactorResponse(
            id=factor.id,
            code=factor.code,
            name=factor.name,
            category=factor.category,
            factor_type=factor.factor_type,
            proxy_symbol=factor.proxy_symbol,
            is_active=bool(factor.is_active),
        )
        for factor in factors
    ]
