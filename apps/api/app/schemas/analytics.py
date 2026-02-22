from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

WeightMethod = Literal[
    "equal",
    "inverse_vol",
    "inverse_corr",
    "risk_parity",
    "beta_adjusted",
    "market_cap",
    "manual",
]


class BasketConfigRequest(BaseModel):
    basket_id: uuid.UUID
    weight_method: WeightMethod
    gross_exposure: float = Field(1.0, gt=0, le=20)
    start_date: date
    end_date: date
    benchmark_id: uuid.UUID | None = None
    lookback_days: int = Field(90, ge=20, le=504)
    include_funding_adj: bool = True
    include_trading_costs: bool = True
    fee_bps: float = Field(4.0, ge=0)
    slippage_bps: float = Field(6.0, ge=0)
    rebalance_freq: Literal["none", "daily", "weekly", "monthly"] = "none"


class PerformancePoint(BaseModel):
    date: date
    basket_return: float
    benchmark_return: float
    drawdown: float


class WeightSnapshot(BaseModel):
    method: WeightMethod
    weights: dict[str, float]


class RiskMetrics(BaseModel):
    annVol: float
    sharpe: float
    maxDrawdown: float
    calmar: float
    sortino: float
    beta: float
    netExposure: float
    grossExposure: float
    fundingDrag: float
    totalReturn: float
    vsbenchmark: float


class PerformanceResponse(BaseModel):
    series: list[PerformancePoint]
    metrics: RiskMetrics
    weights: list[WeightSnapshot]


class WeightsResponse(BaseModel):
    weights: list[WeightSnapshot]


class RiskResponse(BaseModel):
    metrics: RiskMetrics


class CorrelationResponse(BaseModel):
    symbols: list[str]
    matrix: list[list[float]]


class FactorDefinitionResponse(BaseModel):
    code: str
    name: str
    category: str
    proxy_symbol: str


class FactorResponse(BaseModel):
    id: uuid.UUID
    code: str
    name: str
    category: str
    factor_type: str
    proxy_symbol: str
    is_active: bool


class FactorsRequest(BaseModel):
    config: BasketConfigRequest
    factor_codes: list[str] | None = None
    rolling_window: int = Field(63, ge=20, le=252)


class FactorsExposuresRequest(BaseModel):
    config: BasketConfigRequest
    factor_ids: list[uuid.UUID] = Field(min_length=1)
    rolling_window: int = Field(63, ge=20, le=252)


class FactorExposurePoint(BaseModel):
    date: date
    exposures: dict[str, float]
    alpha: float
    r2: float
    regime: str


class FactorAttributionPoint(BaseModel):
    factor: str
    contribution: float


class FactorCorrelationResponse(BaseModel):
    factors: list[str]
    matrix: list[list[float]]


class FactorsResponse(BaseModel):
    factors: list[FactorDefinitionResponse]
    exposures: list[FactorExposurePoint]
    attribution: list[FactorAttributionPoint]
    factor_correlation: FactorCorrelationResponse
