from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.factors import (
    factor_attribution,
    factor_correlation_matrix,
    regime_map,
    rolling_factor_exposures,
)
from app.errors import APIError
from app.ingestion.yahoo import YahooFinanceConnector
from app.models import Factor, FactorDefinition, Instrument, ReturnDaily
from app.schemas.analytics import (
    BasketConfigRequest,
    FactorAttributionPoint,
    FactorCorrelationResponse,
    FactorDefinitionResponse,
    FactorExposurePoint,
    FactorsRequest,
    FactorsResponse,
)
from app.services.analytics_api import prepare_analytics


@dataclass
class PreparedFactors:
    definitions: list[FactorDefinition]
    returns_df: pd.DataFrame


FACTOR_REGIMES: dict[str, str] = {
    "MKT": "growth",
    "SIZE": "growth",
    "VALUE": "growth",
    "MOM": "growth",
    "COMM": "inflation",
    "DEF": "risk-off",
}


async def _ensure_proxy_instrument_id(db: AsyncSession, factor: FactorDefinition) -> None:
    if factor.proxy_instrument_id is not None:
        return

    instrument_stmt = select(Instrument).where(Instrument.symbol == factor.proxy_symbol)
    instrument = (await db.execute(instrument_stmt)).scalar_one_or_none()
    if instrument is None:
        return

    factor.proxy_instrument_id = instrument.id
    await db.commit()


async def _ingest_proxy_history(
    factor: FactorDefinition,
    request: FactorsRequest,
) -> None:
    connector = YahooFinanceConnector()
    start_date = request.config.start_date - timedelta(days=365)
    await connector.ingest_instrument(
        symbol=factor.proxy_symbol,
        start_date=start_date,
        end_date=request.config.end_date,
    )


async def _fetch_factor_rows(
    db: AsyncSession,
    factor: FactorDefinition,
    request: FactorsRequest,
) -> list[ReturnDaily]:
    await _ensure_proxy_instrument_id(db=db, factor=factor)
    if factor.proxy_instrument_id is None:
        return []

    stmt = (
        select(ReturnDaily)
        .where(
            ReturnDaily.instrument_id == factor.proxy_instrument_id,
            ReturnDaily.date >= request.config.start_date,
            ReturnDaily.date <= request.config.end_date,
        )
        .order_by(ReturnDaily.date.asc())
    )
    rows = list((await db.execute(stmt)).scalars().all())
    if rows:
        return rows

    await _ingest_proxy_history(factor=factor, request=request)
    rows = list((await db.execute(stmt)).scalars().all())
    return rows


async def prepare_factors(
    db: AsyncSession,
    request: FactorsRequest,
) -> PreparedFactors:
    stmt = (
        select(FactorDefinition)
        .where(FactorDefinition.is_active.is_(True))
        .order_by(FactorDefinition.code)
    )
    definitions = list((await db.execute(stmt)).scalars().all())

    if request.factor_codes:
        selected = {code.upper() for code in request.factor_codes}
        definitions = [factor for factor in definitions if factor.code.upper() in selected]

    if not definitions:
        raise APIError("INVALID_CONFIGURATION", "No active factors available for analysis.", 422)

    rows: list[dict[str, float | object]] = []
    usable_definitions: list[FactorDefinition] = []

    for factor in definitions:
        factor_rows = await _fetch_factor_rows(db=db, factor=factor, request=request)
        if not factor_rows:
            continue

        usable_definitions.append(factor)
        for row in factor_rows:
            rows.append(
                {
                    "date": row.date,
                    "factor": factor.code,
                    "value": float(row.simple_return or 0.0),
                }
            )

    if not rows:
        raise APIError(
            "DATE_RANGE_TOO_SHORT",
            "No factor return history found for selected range.",
            422,
        )

    frame = pd.DataFrame(rows)
    returns_df = frame.pivot(index="date", columns="factor", values="value").sort_index()
    returns_df = returns_df.dropna(how="any")
    if returns_df.empty:
        raise APIError(
            "DATE_RANGE_TOO_SHORT",
            "No overlapping factor history for selected range.",
            422,
        )

    return PreparedFactors(definitions=usable_definitions, returns_df=returns_df)


async def build_factors_response(db: AsyncSession, request: FactorsRequest) -> FactorsResponse:
    prepared = await prepare_analytics(db=db, config=request.config)
    prepared_factors = await prepare_factors(db=db, request=request)

    exposures_df = rolling_factor_exposures(
        basket_returns=prepared.basket_series,
        factor_returns_df=prepared_factors.returns_df,
        window=request.rolling_window,
    )
    regimes = regime_map(exposures_df=exposures_df, factor_to_regime=FACTOR_REGIMES)
    attribution = factor_attribution(
        basket_returns=prepared.basket_series,
        factor_returns_df=prepared_factors.returns_df,
    )
    corr = factor_correlation_matrix(prepared_factors.returns_df)

    factor_definitions = [
        FactorDefinitionResponse(
            code=factor.code,
            name=factor.name,
            category=factor.category,
            proxy_symbol=factor.proxy_symbol,
        )
        for factor in prepared_factors.definitions
        if factor.code in prepared_factors.returns_df.columns
    ]

    exposures = [
        FactorExposurePoint(
            date=index_date,
            exposures={
                code: float(exposures_df.loc[index_date, code])
                for code in prepared_factors.returns_df.columns
            },
            alpha=float(exposures_df.loc[index_date, "alpha"]),
            r2=float(exposures_df.loc[index_date, "r2"]),
            regime=str(regimes.loc[index_date]),
        )
        for index_date in exposures_df.index
    ]

    attribution_rows = [
        FactorAttributionPoint(factor=name, contribution=float(value))
        for name, value in sorted(attribution.items())
    ]

    return FactorsResponse(
        factors=factor_definitions,
        exposures=exposures,
        attribution=attribution_rows,
        factor_correlation=FactorCorrelationResponse(
            factors=list(corr.columns),
            matrix=[[float(value) for value in row] for row in corr.values.tolist()],
        ),
    )


async def build_factors_exposures_by_ids(
    db: AsyncSession,
    factor_ids: list[uuid.UUID],
    rolling_window: int,
    request_config: BasketConfigRequest,
) -> FactorsResponse:
    prepared = await prepare_analytics(db=db, config=request_config)

    stmt = (
        select(Factor)
        .where(Factor.id.in_(factor_ids), Factor.is_active.is_(True))
        .order_by(Factor.code)
    )
    factors = list((await db.execute(stmt)).scalars().all())
    if not factors:
        raise APIError(
            "INVALID_CONFIGURATION",
            "No active factors available for selected factor_ids.",
            422,
        )

    rows: list[dict[str, float | object]] = []
    for factor in factors:
        factor_def = FactorDefinition(
            code=factor.code,
            name=factor.name,
            category=factor.category,
            proxy_symbol=factor.proxy_symbol,
            proxy_instrument_id=factor.proxy_instrument_id,
            is_active=factor.is_active,
        )
        factor_rows = await _fetch_factor_rows(
            db=db,
            factor=factor_def,
            request=FactorsRequest(
                config=request_config,
                factor_codes=[factor.code],
                rolling_window=rolling_window,
            ),
        )
        for row in factor_rows:
            rows.append(
                {
                    "date": row.date,
                    "factor": factor.code,
                    "value": float(row.simple_return or 0.0),
                }
            )

    if not rows:
        raise APIError(
            "DATE_RANGE_TOO_SHORT",
            "No factor return history found for selected range.",
            422,
        )

    frame = pd.DataFrame(rows)
    factor_returns_df = frame.pivot(index="date", columns="factor", values="value").sort_index()
    factor_returns_df = factor_returns_df.dropna(how="any")
    if factor_returns_df.empty:
        raise APIError(
            "DATE_RANGE_TOO_SHORT",
            "No overlapping factor history for selected range.",
            422,
        )

    exposures_df = rolling_factor_exposures(
        basket_returns=prepared.basket_series,
        factor_returns_df=factor_returns_df,
        window=rolling_window,
    )
    regimes = regime_map(exposures_df=exposures_df, factor_to_regime=FACTOR_REGIMES)
    attribution = factor_attribution(
        basket_returns=prepared.basket_series,
        factor_returns_df=factor_returns_df,
    )
    corr = factor_correlation_matrix(factor_returns_df)

    definitions = [
        FactorDefinitionResponse(
            code=factor.code,
            name=factor.name,
            category=factor.category,
            proxy_symbol=factor.proxy_symbol,
        )
        for factor in factors
        if factor.code in factor_returns_df.columns
    ]

    exposures = [
        FactorExposurePoint(
            date=index_date,
            exposures={
                code: float(exposures_df.loc[index_date, code])
                for code in factor_returns_df.columns
            },
            alpha=float(exposures_df.loc[index_date, "alpha"]),
            r2=float(exposures_df.loc[index_date, "r2"]),
            regime=str(regimes.loc[index_date]),
        )
        for index_date in exposures_df.index
    ]
    attribution_rows = [
        FactorAttributionPoint(factor=name, contribution=float(value))
        for name, value in sorted(attribution.items())
    ]

    return FactorsResponse(
        factors=definitions,
        exposures=exposures,
        attribution=attribution_rows,
        factor_correlation=FactorCorrelationResponse(
            factors=list(corr.columns),
            matrix=[[float(value) for value in row] for row in corr.values.tolist()],
        ),
    )
