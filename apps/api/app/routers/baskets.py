import uuid
from typing import Literal, cast

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.errors import APIError
from app.models import Basket, BasketLeg, Instrument
from app.schemas.baskets import (
    BasketCreateRequest,
    BasketLegResponse,
    BasketResponse,
)
from app.schemas.instruments import InstrumentResponse

router = APIRouter(prefix="/baskets", tags=["baskets"])


def _instrument_response(instrument: Instrument) -> InstrumentResponse:
    return InstrumentResponse(
        id=instrument.id,
        symbol=instrument.symbol,
        name=instrument.name,
        asset_class=instrument.asset_class,
        exchange=instrument.exchange,
        currency=instrument.currency,
    )


def _basket_response(basket: Basket) -> BasketResponse:
    return BasketResponse(
        id=basket.id,
        name=basket.name,
        description=basket.description,
        benchmark_id=basket.benchmark_id,
        created_at=basket.created_at,
        updated_at=basket.updated_at,
        legs=[
            BasketLegResponse(
                id=leg.id,
                side=cast(Literal["long", "short"], leg.side),
                weight_override=leg.weight_override,
                instrument=_instrument_response(leg.instrument),
            )
            for leg in basket.legs
        ],
    )


@router.post("", response_model=BasketResponse, status_code=201)
async def create_basket(
    payload: BasketCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> BasketResponse:
    instrument_ids = [leg.instrument_id for leg in payload.legs]
    instruments = (
        (
            await db.execute(
                select(Instrument).where(
                    Instrument.id.in_(instrument_ids),
                    Instrument.is_active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )
    instrument_by_id = {instrument.id: instrument for instrument in instruments}
    missing = [
        instrument_id for instrument_id in instrument_ids if instrument_id not in instrument_by_id
    ]
    if missing:
        raise APIError("INSTRUMENT_NOT_FOUND", "One or more instruments were not found.", 404)

    basket = Basket(
        name=payload.name,
        description=payload.description,
        benchmark_id=payload.benchmark_id,
        legs=[
            BasketLeg(
                instrument_id=leg.instrument_id,
                side=leg.side,
                weight_override=leg.weight_override,
            )
            for leg in payload.legs
        ],
    )
    db.add(basket)
    await db.commit()

    result = await db.execute(
        select(Basket)
        .where(Basket.id == basket.id)
        .options(selectinload(Basket.legs).selectinload(BasketLeg.instrument))
    )
    created = result.scalar_one()
    return _basket_response(created)


@router.get("", response_model=list[BasketResponse])
async def list_baskets(db: AsyncSession = Depends(get_db)) -> list[BasketResponse]:
    result = await db.execute(
        select(Basket)
        .order_by(Basket.created_at.desc())
        .options(selectinload(Basket.legs).selectinload(BasketLeg.instrument))
    )
    baskets = result.scalars().all()
    return [_basket_response(basket) for basket in baskets]


@router.get("/{basket_id}", response_model=BasketResponse)
async def get_basket(
    basket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> BasketResponse:
    result = await db.execute(
        select(Basket)
        .where(Basket.id == basket_id)
        .options(selectinload(Basket.legs).selectinload(BasketLeg.instrument))
    )
    basket = result.scalar_one_or_none()
    if basket is None:
        raise APIError("BASKET_NOT_FOUND", "Basket not found.", 404)

    return _basket_response(basket)
