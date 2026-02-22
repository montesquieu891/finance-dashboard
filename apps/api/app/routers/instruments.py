import asyncio
import uuid
from datetime import date, timedelta
from typing import Literal

import yfinance as yf  # type: ignore[import-untyped]
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.errors import APIError
from app.ingestion.yahoo import YahooFinanceConnector
from app.models import IngestionLog, Instrument, PriceDaily
from app.schemas.instruments import (
    InstrumentIngestionStatusResponse,
    InstrumentResponse,
    PriceDailyResponse,
)

router = APIRouter(prefix="/instruments", tags=["instruments"])


def _instrument_response(row: Instrument, ingesting: bool = False) -> InstrumentResponse:
    return InstrumentResponse(
        id=row.id,
        symbol=row.symbol,
        name=row.name,
        asset_class=row.asset_class,
        exchange=row.exchange,
        currency=row.currency,
        ingesting=ingesting,
    )


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    if not isinstance(value, (int, float, str, bytes, bytearray)):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


async def _lookup_live_instrument(symbol_query: str) -> dict[str, str | None] | None:
    try:
        ticker_data = await asyncio.to_thread(lambda: yf.Ticker(symbol_query))
        info = await asyncio.to_thread(lambda: ticker_data.info)
    except Exception:
        return None

    if not isinstance(info, dict):
        return None

    has_price = (
        _safe_float(info.get("regularMarketPrice"))
        or _safe_float(info.get("currentPrice"))
        or _safe_float(info.get("previousClose"))
    )
    if has_price is None:
        return None

    upper_symbol = symbol_query.upper()
    is_cedear = upper_symbol.endswith(".BA")

    name = info.get("shortName") or info.get("longName") or upper_symbol
    exchange = info.get("exchange")
    quote_type = str(info.get("quoteType") or "").lower()
    asset_class = "cedear" if is_cedear else ("etf" if quote_type == "etf" else "equity")
    currency = "ARS" if is_cedear else str(info.get("currency") or "USD")

    return {
        "symbol": upper_symbol,
        "name": str(name),
        "exchange": str(exchange) if exchange else None,
        "asset_class": asset_class,
        "currency": currency,
    }


async def _ingest_symbol_history(symbol: str) -> None:
    connector = YahooFinanceConnector()
    end_date = date.today()
    start_date = end_date - timedelta(days=730)
    await connector.ingest_instrument(symbol=symbol, start_date=start_date, end_date=end_date)


@router.get("/search", response_model=list[InstrumentResponse])
async def search_instruments(
    background_tasks: BackgroundTasks,
    q: str = Query(min_length=1),
    asset_class: str | None = Query(default=None),
    source: Literal["auto", "db_only"] = Query(default="auto"),
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
    if rows:
        return [_instrument_response(row) for row in rows]

    if source == "db_only":
        return []

    live_lookup = await _lookup_live_instrument(q)
    if live_lookup is None:
        raise APIError("INSTRUMENT_NOT_FOUND", "Instrument was not found from data source.", 404)

    symbol = live_lookup["symbol"]
    name = live_lookup["name"]
    asset_class_value = live_lookup["asset_class"]
    currency = live_lookup["currency"]
    exchange = live_lookup["exchange"]
    if symbol is None or name is None or asset_class_value is None or currency is None:
        raise APIError("INSTRUMENT_NOT_FOUND", "Instrument was not found from data source.", 404)

    existing = await db.execute(
        select(Instrument).where(
            Instrument.symbol == symbol,
            Instrument.exchange == exchange,
        )
    )
    instrument = existing.scalar_one_or_none()

    if instrument is None:
        instrument = Instrument(
            symbol=symbol,
            name=name,
            asset_class=asset_class_value,
            exchange=exchange,
            currency=currency,
            is_active=True,
        )
        db.add(instrument)
        await db.flush()

        db.add(
            IngestionLog(
                source="yahoo_finance",
                instrument_id=instrument.id,
                status="partial",
                rows_inserted=0,
                error_message=None,
            )
        )
        await db.commit()
        background_tasks.add_task(_ingest_symbol_history, symbol)
        await db.refresh(instrument)
        return [_instrument_response(instrument, ingesting=True)]

    return [_instrument_response(instrument)]


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


@router.get("/{instrument_id}/ingestion_status", response_model=InstrumentIngestionStatusResponse)
async def get_instrument_ingestion_status(
    instrument_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InstrumentIngestionStatusResponse:
    instrument = await db.get(Instrument, instrument_id)
    if instrument is None:
        raise APIError("INSTRUMENT_NOT_FOUND", "Instrument not found.", 404)

    latest_log_query = await db.execute(
        select(IngestionLog)
        .where(
            IngestionLog.instrument_id == instrument_id,
            IngestionLog.source == "yahoo_finance",
        )
        .order_by(IngestionLog.run_at.desc(), IngestionLog.id.desc())
        .limit(1)
    )
    latest_log = latest_log_query.scalar_one_or_none()

    rows_query = await db.execute(
        select(func.count())
        .select_from(PriceDaily)
        .where(PriceDaily.instrument_id == instrument_id)
    )
    rows_count = int(rows_query.scalar_one())

    if latest_log is None:
        status = "complete" if rows_count > 0 else "failed"
        last_updated = (
            instrument.created_at.isoformat() if instrument.created_at is not None else None
        )
    elif latest_log.status == "success":
        status = "complete"
        last_updated = latest_log.run_at.isoformat() if latest_log.run_at is not None else None
    elif latest_log.status == "failed":
        status = "failed"
        last_updated = latest_log.run_at.isoformat() if latest_log.run_at is not None else None
    else:
        status = "ingesting"
        last_updated = latest_log.run_at.isoformat() if latest_log.run_at is not None else None

    return InstrumentIngestionStatusResponse(
        status=status,
        rows=rows_count,
        last_updated=last_updated,
    )
