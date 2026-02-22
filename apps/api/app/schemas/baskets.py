from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.instruments import InstrumentResponse


class BasketLegCreate(BaseModel):
    instrument_id: uuid.UUID
    side: Literal["long", "short"]
    weight_override: Decimal | None = Field(default=None, ge=0)


class BasketCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    benchmark_id: uuid.UUID | None = None
    legs: list[BasketLegCreate] = Field(min_length=1, max_length=50)


class BasketLegResponse(BaseModel):
    id: uuid.UUID
    side: Literal["long", "short"]
    weight_override: Decimal | None
    instrument: InstrumentResponse


class BasketResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    benchmark_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    legs: list[BasketLegResponse]
