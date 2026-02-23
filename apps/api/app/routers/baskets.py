import csv
import uuid
from datetime import date
from decimal import Decimal
from io import StringIO
from typing import Literal, cast

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import get_db
from app.errors import APIError
from app.models import AlertRule, Basket, BasketLeg, Instrument, PriceDaily, RealPosition
from app.schemas.baskets import (
    BasketCreateRequest,
    BasketLegResponse,
    BasketResponse,
)
from app.schemas.instruments import InstrumentResponse
from app.schemas.live import (
    AlertRuleCreateRequest,
    AlertRuleResponse,
    PositionSnapshot,
    PositionsResponse,
    PositionsSummary,
)

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


def _alert_rule_response(rule: AlertRule) -> AlertRuleResponse:
    return AlertRuleResponse(
        id=rule.id,
        basket_id=rule.basket_id,
        instrument_id=rule.instrument_id,
        name=rule.name,
        rule_type=cast(Literal["drawdown", "leg_stop"], rule.rule_type),
        threshold=rule.threshold,
        cooldown_minutes=rule.cooldown_minutes,
        is_active=rule.is_active,
        last_triggered_at=rule.last_triggered_at,
        created_at=rule.created_at,
    )


def _model_signed_weights(legs: list[BasketLeg]) -> dict[uuid.UUID, float]:
    if not legs:
        return {}

    has_overrides = all(leg.weight_override is not None for leg in legs)
    if has_overrides:
        gross = sum(abs(float(leg.weight_override or 0)) for leg in legs)
        gross = gross if gross > 0 else 1.0
        return {
            leg.instrument_id: (float(leg.weight_override or 0) / gross)
            * (1.0 if leg.side == "long" else -1.0)
            for leg in legs
        }

    base = 1.0 / len(legs)
    return {
        leg.instrument_id: base * (1.0 if leg.side == "long" else -1.0)
        for leg in legs
    }


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


@router.get("/{basket_id}/alerts", response_model=list[AlertRuleResponse])
async def list_alert_rules(
    basket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[AlertRuleResponse]:
    basket = await db.get(Basket, basket_id)
    if basket is None:
        raise APIError("BASKET_NOT_FOUND", "Basket not found.", 404)

    result = await db.execute(
        select(AlertRule)
        .where(AlertRule.basket_id == basket_id)
        .order_by(AlertRule.created_at.desc())
    )
    rows = result.scalars().all()
    return [_alert_rule_response(row) for row in rows]


@router.post("/{basket_id}/alerts", response_model=AlertRuleResponse, status_code=201)
async def create_alert_rule(
    basket_id: uuid.UUID,
    payload: AlertRuleCreateRequest,
    db: AsyncSession = Depends(get_db),
) -> AlertRuleResponse:
    basket_result = await db.execute(
        select(Basket)
        .where(Basket.id == basket_id)
        .options(selectinload(Basket.legs).selectinload(BasketLeg.instrument))
    )
    basket = basket_result.scalar_one_or_none()
    if basket is None:
        raise APIError("BASKET_NOT_FOUND", "Basket not found.", 404)

    if payload.rule_type == "leg_stop" and payload.instrument_id is None:
        raise APIError(
            "INVALID_ALERT_RULE",
            "leg_stop alerts require instrument_id.",
            422,
        )

    if payload.instrument_id is not None:
        leg_instrument_ids = {leg.instrument_id for leg in basket.legs}
        if payload.instrument_id not in leg_instrument_ids:
            raise APIError(
                "INVALID_ALERT_RULE",
                "instrument_id must belong to the selected basket.",
                422,
            )

    rule = AlertRule(
        basket_id=basket_id,
        instrument_id=payload.instrument_id,
        name=payload.name,
        rule_type=payload.rule_type,
        threshold=payload.threshold,
        cooldown_minutes=payload.cooldown_minutes,
        is_active=payload.is_active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _alert_rule_response(rule)


@router.delete("/alerts/{alert_id}", status_code=204)
async def delete_alert_rule(
    alert_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    rule = await db.get(AlertRule, alert_id)
    if rule is None:
        raise APIError("ALERT_NOT_FOUND", "Alert rule not found.", 404)
    await db.delete(rule)
    await db.commit()


@router.post("/{basket_id}/positions/upload", status_code=204)
async def upload_real_positions(
    basket_id: uuid.UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> None:
    basket_result = await db.execute(
        select(Basket)
        .where(Basket.id == basket_id)
        .options(selectinload(Basket.legs).selectinload(BasketLeg.instrument))
    )
    basket = basket_result.scalar_one_or_none()
    if basket is None:
        raise APIError("BASKET_NOT_FOUND", "Basket not found.", 404)

    raw = await file.read()
    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise APIError("INVALID_CSV", f"CSV decode error: {exc}", 422) from exc

    reader = csv.DictReader(StringIO(decoded))
    if reader.fieldnames is None:
        raise APIError("INVALID_CSV", "CSV must include headers.", 422)

    headers = {field.lower().strip() for field in reader.fieldnames if field}
    if "symbol" not in headers or ("qty" not in headers and "quantity" not in headers):
        raise APIError("INVALID_CSV", "CSV headers must include symbol and qty/quantity.", 422)

    instrument_by_symbol = {leg.instrument.symbol.upper(): leg.instrument for leg in basket.legs}
    inserts: list[dict[str, object]] = []
    for row in reader:
        symbol = (row.get("symbol") or "").strip().upper()
        qty_value = (row.get("qty") or row.get("quantity") or "").strip()
        avg_price_raw = (row.get("avg_price") or row.get("average_price") or "").strip()
        if not symbol or not qty_value:
            continue
        instrument = instrument_by_symbol.get(symbol)
        if instrument is None:
            continue

        try:
            quantity = Decimal(qty_value)
        except Exception as exc:
            raise APIError("INVALID_CSV", f"Invalid quantity for {symbol}.", 422) from exc

        avg_price = Decimal(avg_price_raw) if avg_price_raw else None
        inserts.append(
            {
                "basket_id": basket_id,
                "instrument_id": instrument.id,
                "quantity": quantity,
                "avg_price": avg_price,
            }
        )

    if inserts:
        for payload in inserts:
            statement = insert(RealPosition).values(**payload)
            statement = statement.on_conflict_do_update(
                index_elements=["basket_id", "instrument_id"],
                set_={
                    "quantity": payload["quantity"],
                    "avg_price": payload["avg_price"],
                    "uploaded_at": func.now(),
                },
            )
            await db.execute(statement)

    await db.commit()


@router.get("/{basket_id}/positions", response_model=PositionsResponse)
async def get_real_positions(
    basket_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> PositionsResponse:
    basket_result = await db.execute(
        select(Basket)
        .where(Basket.id == basket_id)
        .options(selectinload(Basket.legs).selectinload(BasketLeg.instrument))
    )
    basket = basket_result.scalar_one_or_none()
    if basket is None:
        raise APIError("BASKET_NOT_FOUND", "Basket not found.", 404)

    positions_result = await db.execute(
        select(RealPosition)
        .where(RealPosition.basket_id == basket_id)
        .options(selectinload(RealPosition.instrument))
    )
    positions = positions_result.scalars().all()
    if not positions:
        return PositionsResponse(
            rows=[],
            summary=PositionsSummary(
                gross_notional=Decimal("0"),
                net_notional=Decimal("0"),
                drift_l1=0.0,
                daily_pnl_total=Decimal("0"),
            ),
        )

    instrument_ids = [position.instrument_id for position in positions]
    prices_result = await db.execute(
        select(PriceDaily)
        .where(
            and_(
                PriceDaily.instrument_id.in_(instrument_ids),
                PriceDaily.date <= date.today(),
            )
        )
        .order_by(PriceDaily.instrument_id.asc(), PriceDaily.date.desc())
    )
    latest_price_by_instrument: dict[uuid.UUID, Decimal] = {}
    seen: set[uuid.UUID] = set()
    for row in prices_result.scalars().all():
        if row.instrument_id is None:
            continue
        if row.instrument_id in seen:
            continue
        seen.add(row.instrument_id)
        latest_price_by_instrument[row.instrument_id] = row.px_close

    model_weights = _model_signed_weights(list(basket.legs))
    notionals: dict[uuid.UUID, Decimal] = {}
    total_abs = Decimal("0")
    for position in positions:
        latest_price = latest_price_by_instrument.get(position.instrument_id)
        if latest_price is None:
            continue
        notional = position.quantity * latest_price
        notionals[position.instrument_id] = notional
        total_abs += abs(notional)

    rows: list[PositionSnapshot] = []
    gross_notional = Decimal("0")
    net_notional = Decimal("0")
    drift_l1 = 0.0
    daily_pnl_total = Decimal("0")

    for position in positions:
        last_price = latest_price_by_instrument.get(position.instrument_id)
        notional = notionals.get(position.instrument_id, Decimal("0"))
        gross_notional += abs(notional)
        net_notional += notional

        actual_weight = float(notional / total_abs) if total_abs > 0 else 0.0
        model_weight = model_weights.get(position.instrument_id, 0.0)
        drift_bps = (actual_weight - model_weight) * 10000.0
        drift_l1 += abs(actual_weight - model_weight)

        daily_pnl = None
        if position.avg_price is not None and last_price is not None:
            daily_pnl = (last_price - position.avg_price) * position.quantity
            daily_pnl_total += daily_pnl

        rows.append(
            PositionSnapshot(
                id=position.id,
                instrument_id=position.instrument_id,
                symbol=position.instrument.symbol,
                quantity=position.quantity,
                avg_price=position.avg_price,
                last_price=last_price,
                model_signed_weight=model_weight,
                actual_signed_weight=actual_weight,
                drift_bps=drift_bps,
                daily_pnl=daily_pnl,
                uploaded_at=position.uploaded_at,
            )
        )

    return PositionsResponse(
        rows=rows,
        summary=PositionsSummary(
            gross_notional=gross_notional,
            net_notional=net_notional,
            drift_l1=drift_l1,
            daily_pnl_total=daily_pnl_total,
        ),
    )
