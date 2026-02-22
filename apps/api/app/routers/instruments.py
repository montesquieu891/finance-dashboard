import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Instrument, PriceDaily
from app.schemas.instruments import InstrumentResponse, PriceDailyResponse

router = APIRouter(prefix="/instruments", tags=["instruments"])


@router.get("/search", response_model=list[InstrumentResponse])
async def search_instruments(
    q: str = Query(min_length=1),
    asset_class: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[InstrumentResponse]:
    query_filters = [
        Instrument.is_active.is_(True),
        or_(
            Instrument.symbol.ilike(f"%{q}%"),
            Instrument.name.ilike(f"%{q}%"),
        ),
    ]
    if asset_class is not None:
        query_filters.append(Instrument.asset_class == asset_class)

    result = await db.execute(
        select(Instrument)
        .where(and_(*query_filters))
        .order_by(Instrument.symbol.asc())
        .limit(limit)
    )
    rows = result.scalars().all()
    return [
        InstrumentResponse(
            id=row.id,
            symbol=row.symbol,
            name=row.name,
            asset_class=row.asset_class,
            exchange=row.exchange,
            currency=row.currency,
        )
        for row in rows
    ]


@router.get("/{instrument_id}/prices", response_model=list[PriceDailyResponse])
async def get_instrument_prices(
    instrument_id: uuid.UUID,
    from_date: date = Query(alias="from"),
    to_date: date = Query(alias="to"),
    db: AsyncSession = Depends(get_db),
) -> list[PriceDailyResponse]:
    result = await db.execute(
        select(PriceDaily)
        .where(
            PriceDaily.instrument_id == instrument_id,
            PriceDaily.date >= from_date,
            PriceDaily.date <= to_date,
        )
        .order_by(PriceDaily.date.asc())
    )
    rows = result.scalars().all()
    return [
        PriceDailyResponse(
            date=row.date,
            px_open=row.px_open,
            px_high=row.px_high,
            px_low=row.px_low,
            px_close=row.px_close,
            px_adj_close=row.px_adj_close,
            volume=row.volume,
        )
        for row in rows
    ]
