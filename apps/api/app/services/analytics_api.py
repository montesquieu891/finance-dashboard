from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.analytics.correlation import pairwise_correlation
from app.analytics.returns import basket_returns
from app.analytics.risk import compute_risk_metrics
from app.analytics.weights import (
    beta_adjusted_weights,
    equal_weights,
    inverse_corr_weights,
    inverse_vol_weights,
    risk_parity_weights,
)
from app.errors import APIError
from app.models import Basket, BasketLeg, ReturnDaily
from app.schemas.analytics import BasketConfigRequest, RiskMetrics, WeightMethod, WeightSnapshot


@dataclass
class PreparedAnalytics:
    symbols: list[str]
    signed_weights: dict[str, float]
    benchmark_series: pd.Series | None
    basket_series: pd.Series
    returns_for_weights: pd.DataFrame
    method_weights: list[WeightSnapshot]


def _manual_weights(legs: list[BasketLeg], gross_exposure: float) -> pd.Series:
    overrides: dict[str, float] = {}
    for leg in legs:
        if leg.weight_override is None:
            raise APIError(
                "INVALID_CONFIGURATION",
                "Manual weights require weight_override for every leg.",
                422,
            )
        overrides[leg.instrument.symbol] = float(leg.weight_override)

    raw = pd.Series(overrides, dtype=float).abs()
    total = float(raw.sum())
    if total <= 0.0:
        raise APIError("INVALID_CONFIGURATION", "Manual weights must sum to a positive value.", 422)
    return raw / total * gross_exposure


def _market_cap_weights(symbols: list[str], gross_exposure: float) -> pd.Series:
    return equal_weights(symbols=symbols, gross_exposure=gross_exposure)


def _compute_method_weights(
    config: BasketConfigRequest,
    returns_for_weights: pd.DataFrame,
    legs: list[BasketLeg],
    benchmark_series: pd.Series | None,
) -> list[WeightSnapshot]:
    symbols = [leg.instrument.symbol for leg in legs]
    all_methods: dict[WeightMethod, pd.Series] = {
        "equal": equal_weights(symbols=symbols, gross_exposure=config.gross_exposure),
        "inverse_vol": inverse_vol_weights(
            returns_df=returns_for_weights,
            gross_exposure=config.gross_exposure,
            lookback=config.lookback_days,
        ),
        "inverse_corr": inverse_corr_weights(
            returns_df=returns_for_weights,
            gross_exposure=config.gross_exposure,
            lookback=config.lookback_days,
        ),
        "risk_parity": risk_parity_weights(
            returns_df=returns_for_weights,
            gross_exposure=config.gross_exposure,
            lookback=config.lookback_days,
        ),
        "market_cap": _market_cap_weights(symbols=symbols, gross_exposure=config.gross_exposure),
        "manual": _manual_weights(legs=legs, gross_exposure=config.gross_exposure),
    }

    if benchmark_series is None:
        all_methods["beta_adjusted"] = all_methods["equal"]
    else:
        all_methods["beta_adjusted"] = beta_adjusted_weights(
            returns_df=returns_for_weights,
            benchmark_returns=benchmark_series,
            gross_exposure=config.gross_exposure,
            lookback=config.lookback_days,
        )

    return [
        WeightSnapshot(
            method=method_name,
            weights=cast(dict[str, float], weights_series.to_dict()),
        )
        for method_name, weights_series in all_methods.items()
    ]


def _resolve_selected_weights(
    selected_method: str,
    method_weights: list[WeightSnapshot],
) -> dict[str, float]:
    for snapshot in method_weights:
        if snapshot.method == selected_method:
            return snapshot.weights
    raise APIError("INVALID_CONFIGURATION", f"Unsupported weighting method: {selected_method}", 422)


async def prepare_analytics(
    db: AsyncSession,
    config: BasketConfigRequest,
) -> PreparedAnalytics:
    if config.start_date > config.end_date:
        raise APIError("INVALID_DATE_RANGE", "start_date must be on or before end_date.", 422)

    basket_stmt = (
        select(Basket)
        .where(Basket.id == config.basket_id)
        .options(selectinload(Basket.legs).selectinload(BasketLeg.instrument))
    )
    basket = (await db.execute(basket_stmt)).scalar_one_or_none()
    if basket is None:
        raise APIError("BASKET_NOT_FOUND", "Basket not found.", 404)

    legs = list(basket.legs)
    if not legs:
        raise APIError("INVALID_CONFIGURATION", "Basket has no legs.", 422)

    instrument_ids = [leg.instrument_id for leg in legs]
    returns_stmt = (
        select(ReturnDaily)
        .where(
            ReturnDaily.instrument_id.in_(instrument_ids),
            ReturnDaily.date >= config.start_date,
            ReturnDaily.date <= config.end_date,
        )
        .order_by(ReturnDaily.date.asc())
    )
    return_rows = (await db.execute(returns_stmt)).scalars().all()
    if not return_rows:
        raise APIError(
            "DATE_RANGE_TOO_SHORT", "No return history found for the selected range.", 422
        )

    symbol_by_id = {leg.instrument_id: leg.instrument.symbol for leg in legs}
    dates: list[object] = []
    symbols_list: list[str] = []
    values: list[float] = []
    for row in return_rows:
        if row.instrument_id is None:
            raise APIError("INVALID_CONFIGURATION", "Return row missing instrument_id.", 422)
        dates.append(row.date)
        symbols_list.append(symbol_by_id[row.instrument_id])
        values.append(float(row.simple_return or 0.0))

    frame = pd.DataFrame(
        {
            "date": dates,
            "symbol": symbols_list,
            "value": values,
        }
    )
    returns_df = frame.pivot(index="date", columns="symbol", values="value").sort_index()

    missing_symbols = [
        symbol for symbol in symbol_by_id.values() if symbol not in returns_df.columns
    ]
    if missing_symbols:
        raise APIError(
            "DATE_RANGE_TOO_SHORT",
            f"Missing return history for symbols: {', '.join(sorted(missing_symbols))}",
            422,
        )

    aligned = returns_df.dropna(how="any")
    if aligned.empty:
        raise APIError(
            "DATE_RANGE_TOO_SHORT", "No overlapping dates for selected instruments.", 422
        )

    if len(aligned.index) < config.lookback_days:
        raise APIError(
            "DATE_RANGE_TOO_SHORT",
            (
                f"Need at least {config.lookback_days} aligned observations "
                "for selected lookback_days."
            ),
            422,
        )

    returns_for_weights = aligned.copy()
    for leg in legs:
        if leg.side == "short":
            returns_for_weights[leg.instrument.symbol] = -returns_for_weights[leg.instrument.symbol]

    benchmark_id = config.benchmark_id or basket.benchmark_id
    benchmark_series: pd.Series | None = None
    if benchmark_id is not None:
        benchmark_stmt = (
            select(ReturnDaily)
            .where(
                ReturnDaily.instrument_id == benchmark_id,
                ReturnDaily.date >= config.start_date,
                ReturnDaily.date <= config.end_date,
            )
            .order_by(ReturnDaily.date.asc())
        )
        benchmark_rows = (await db.execute(benchmark_stmt)).scalars().all()
        if benchmark_rows:
            benchmark_series = pd.Series(
                [float(row.simple_return or 0.0) for row in benchmark_rows],
                index=[row.date for row in benchmark_rows],
                dtype=float,
            ).rename("benchmark")
            benchmark_series = benchmark_series.reindex(aligned.index).dropna()
            if benchmark_series.empty:
                benchmark_series = None

    method_weights = _compute_method_weights(
        config=config,
        returns_for_weights=returns_for_weights,
        legs=legs,
        benchmark_series=benchmark_series,
    )
    selected_weights = _resolve_selected_weights(config.weight_method, method_weights)

    calc_legs = [
        {"symbol": leg.instrument.symbol, "side": "long", "currency": "USD"} for leg in legs
    ]
    basket_series = basket_returns(calc_legs, selected_weights, returns_for_weights)

    side_multiplier = {leg.instrument.symbol: (1.0 if leg.side == "long" else -1.0) for leg in legs}
    signed_weights = {
        symbol: float(weight) * side_multiplier[symbol]
        for symbol, weight in selected_weights.items()
    }

    return PreparedAnalytics(
        symbols=list(returns_for_weights.columns),
        signed_weights=signed_weights,
        benchmark_series=benchmark_series,
        basket_series=basket_series,
        returns_for_weights=returns_for_weights,
        method_weights=method_weights,
    )


def build_risk_metrics(prepared: PreparedAnalytics) -> RiskMetrics:
    metrics = compute_risk_metrics(
        returns=prepared.basket_series,
        signed_weights=prepared.signed_weights,
        benchmark_returns=prepared.benchmark_series,
    )
    return RiskMetrics(
        annVol=metrics["ann_vol"],
        sharpe=metrics["sharpe"],
        maxDrawdown=metrics["max_drawdown"],
        calmar=metrics["calmar"],
        sortino=metrics["sortino"],
        beta=metrics["beta"],
        netExposure=metrics["net_exposure"],
        grossExposure=metrics["gross_exposure"],
        fundingDrag=0.0,
        totalReturn=metrics["total_return"],
        vsbenchmark=metrics["vs_benchmark"],
    )


def build_drawdown_series(returns: pd.Series) -> pd.Series:
    indexed = (1.0 + returns).cumprod() * 100.0
    running_peak = indexed.cummax()
    return ((running_peak - indexed) / running_peak).fillna(0.0)


def build_correlation_matrix(prepared: PreparedAnalytics, lookback_days: int) -> list[list[float]]:
    corr_df = pairwise_correlation(returns_df=prepared.returns_for_weights, lookback=lookback_days)
    return [[float(value) for value in row] for row in corr_df.values.tolist()]
