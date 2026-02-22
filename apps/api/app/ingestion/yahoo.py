from __future__ import annotations

import argparse
import asyncio
from datetime import date
from decimal import Decimal
from typing import SupportsInt

import pandas as pd
import yfinance as yf  # type: ignore[import-untyped]
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.returns import rebuild_returns_for_instrument
from app.db import create_session_factory
from app.ingestion.base import BaseConnector, IngestionResult
from app.models import IngestionLog, Instrument, PriceDaily


class YahooFinanceConnector(BaseConnector):
    source = "yahoo_finance"

    async def fetch_raw(self, symbol: str, start_date: date, end_date: date) -> pd.DataFrame:
        return await asyncio.to_thread(
            yf.download,
            symbol,
            start=start_date.isoformat(),
            end=end_date.isoformat(),
            progress=False,
            auto_adjust=True,
            interval="1d",
        )

    def normalize(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        if raw_data.empty:
            return pd.DataFrame(
                columns=[
                    "date",
                    "px_open",
                    "px_high",
                    "px_low",
                    "px_close",
                    "px_adj_close",
                    "volume",
                ]
            )

        normalized = raw_data.reset_index()
        if isinstance(normalized.columns, pd.MultiIndex):
            normalized.columns = [
                str(column[0]) if isinstance(column, tuple) else str(column)
                for column in normalized.columns
            ]

        normalized = normalized.rename(
            columns={
                "Date": "date",
                "index": "date",
                "Open": "px_open",
                "High": "px_high",
                "Low": "px_low",
                "Close": "px_close",
                "Adj Close": "px_adj_close",
                "Volume": "volume",
            }
        )

        normalized["date"] = pd.to_datetime(normalized["date"]).dt.date
        if "px_adj_close" not in normalized.columns:
            normalized["px_adj_close"] = normalized["px_close"]
        return normalized[
            ["date", "px_open", "px_high", "px_low", "px_close", "px_adj_close", "volume"]
        ]

    def validate(self, normalized_data: pd.DataFrame) -> None:
        required_columns = {
            "date",
            "px_open",
            "px_high",
            "px_low",
            "px_close",
            "px_adj_close",
            "volume",
        }
        missing_columns = required_columns.difference(normalized_data.columns)
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Missing required columns: {missing}")

        if normalized_data.empty:
            raise ValueError("No price rows returned by source")

        if normalized_data["date"].isna().any():
            raise ValueError("Date contains null values")

        if normalized_data["px_close"].isna().any():
            raise ValueError("Close contains null values")

    async def upsert(
        self,
        session: AsyncSession,
        instrument: Instrument,
        normalized_data: pd.DataFrame,
    ) -> int:
        await session.execute(delete(PriceDaily).where(PriceDaily.instrument_id == instrument.id))

        for row in normalized_data.itertuples(index=False):
            volume_value = row.volume
            volume = int(volume_value) if isinstance(volume_value, SupportsInt) else None

            session.add(
                PriceDaily(
                    instrument_id=instrument.id,
                    date=row.date,
                    px_open=Decimal(str(row.px_open)) if pd.notna(row.px_open) else None,
                    px_high=Decimal(str(row.px_high)) if pd.notna(row.px_high) else None,
                    px_low=Decimal(str(row.px_low)) if pd.notna(row.px_low) else None,
                    px_close=Decimal(str(row.px_close)),
                    px_adj_close=Decimal(str(row.px_adj_close))
                    if pd.notna(row.px_adj_close)
                    else None,
                    volume=volume,
                )
            )

        return len(normalized_data.index)

    async def ingest_instrument(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        exchange: str | None = None,
    ) -> IngestionResult:
        session_factory = create_session_factory()
        async with session_factory() as session:
            instrument_query = select(Instrument).where(Instrument.symbol == symbol)
            if exchange is not None:
                instrument_query = instrument_query.where(Instrument.exchange == exchange)

            instrument_result = await session.execute(instrument_query)
            instrument = instrument_result.scalar_one_or_none()
            if instrument is None:
                session.add(
                    IngestionLog(
                        source=self.source,
                        instrument_id=None,
                        status="failed",
                        rows_inserted=0,
                        error_message=(
                            f"Instrument not found for symbol={symbol} "
                            f"exchange={exchange}"
                        ),
                    )
                )
                await session.commit()
                return IngestionResult(
                    rows_inserted=0, status="failed", error_message="Instrument not found"
                )

            try:
                raw_data = await self.fetch_raw(symbol, start_date, end_date)
                normalized = self.normalize(raw_data)
                self.validate(normalized)
                rows_inserted = await self.upsert(session, instrument, normalized)
                await rebuild_returns_for_instrument(session, instrument.id)
                session.add(
                    IngestionLog(
                        source=self.source,
                        instrument_id=instrument.id,
                        status="success",
                        rows_inserted=rows_inserted,
                        error_message=None,
                    )
                )
                await session.commit()
                return IngestionResult(rows_inserted=rows_inserted, status="success")
            except Exception as exc:
                session.add(
                    IngestionLog(
                        source=self.source,
                        instrument_id=instrument.id,
                        status="failed",
                        rows_inserted=0,
                        error_message=str(exc),
                    )
                )
                await session.commit()
                return IngestionResult(rows_inserted=0, status="failed", error_message=str(exc))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch daily prices from Yahoo Finance")
    parser.add_argument("--symbols", nargs="+", required=True)
    parser.add_argument("--from", dest="from_date", required=True)
    parser.add_argument("--to", dest="to_date", default=date.today().isoformat())
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    connector = YahooFinanceConnector()
    start_date = date.fromisoformat(args.from_date)
    end_date = date.fromisoformat(args.to_date)

    for symbol in args.symbols:
        result = await connector.ingest_instrument(
            symbol=symbol, start_date=start_date, end_date=end_date
        )
        print(f"{symbol}: status={result.status} rows_inserted={result.rows_inserted}")
        await asyncio.sleep(0.5)


if __name__ == "__main__":
    asyncio.run(main())
