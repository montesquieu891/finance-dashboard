from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class AlertRuleCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    rule_type: Literal["drawdown", "leg_stop"]
    threshold: Decimal = Field(gt=0)
    cooldown_minutes: int = Field(default=60, ge=1, le=1440)
    is_active: bool = True
    instrument_id: uuid.UUID | None = None


class AlertRuleResponse(BaseModel):
    id: uuid.UUID
    basket_id: uuid.UUID
    instrument_id: uuid.UUID | None
    name: str
    rule_type: Literal["drawdown", "leg_stop"]
    threshold: Decimal
    cooldown_minutes: int
    is_active: bool
    last_triggered_at: datetime | None
    created_at: datetime


class PositionSnapshot(BaseModel):
    id: uuid.UUID
    instrument_id: uuid.UUID
    symbol: str
    quantity: Decimal
    avg_price: Decimal | None
    last_price: Decimal | None
    model_signed_weight: float
    actual_signed_weight: float
    drift_bps: float
    daily_pnl: Decimal | None
    uploaded_at: datetime


class PositionsSummary(BaseModel):
    gross_notional: Decimal
    net_notional: Decimal
    drift_l1: float
    daily_pnl_total: Decimal


class PositionsResponse(BaseModel):
    rows: list[PositionSnapshot]
    summary: PositionsSummary


class LivePriceTick(BaseModel):
    symbol: str
    price: Decimal
    as_of: datetime


class LivePriceEnvelope(BaseModel):
    type: Literal["price_tick"] = "price_tick"
    basket_id: uuid.UUID | None = None
    generated_at: datetime
    data: list[LivePriceTick]
