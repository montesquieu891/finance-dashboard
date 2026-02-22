from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class InstrumentResponse(BaseModel):
    id: uuid.UUID
    symbol: str
    name: str | None
    asset_class: str
    exchange: str | None
    currency: str


class PriceDailyResponse(BaseModel):
    date: date
    px_open: Decimal | None
    px_high: Decimal | None
    px_low: Decimal | None
    px_close: Decimal
    px_adj_close: Decimal | None
    volume: int | None
