from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.db import create_session_factory
from app.models import Instrument

SEED_INSTRUMENTS: list[dict[str, object]] = [
    {
        "symbol": "AAPL",
        "name": "Apple Inc.",
        "asset_class": "equity",
        "exchange": "NASDAQ",
        "currency": "USD",
    },
    {
        "symbol": "MSFT",
        "name": "Microsoft Corporation",
        "asset_class": "equity",
        "exchange": "NASDAQ",
        "currency": "USD",
    },
    {
        "symbol": "AMZN",
        "name": "Amazon.com Inc.",
        "asset_class": "equity",
        "exchange": "NASDAQ",
        "currency": "USD",
    },
    {
        "symbol": "GOOGL",
        "name": "Alphabet Inc.",
        "asset_class": "equity",
        "exchange": "NASDAQ",
        "currency": "USD",
    },
    {
        "symbol": "META",
        "name": "Meta Platforms Inc.",
        "asset_class": "equity",
        "exchange": "NASDAQ",
        "currency": "USD",
    },
    {
        "symbol": "NVDA",
        "name": "NVIDIA Corporation",
        "asset_class": "equity",
        "exchange": "NASDAQ",
        "currency": "USD",
    },
    {
        "symbol": "TSLA",
        "name": "Tesla Inc.",
        "asset_class": "equity",
        "exchange": "NASDAQ",
        "currency": "USD",
    },
    {
        "symbol": "SPY",
        "name": "SPDR S&P 500 ETF Trust",
        "asset_class": "etf",
        "exchange": "ARCA",
        "currency": "USD",
    },
    {
        "symbol": "QQQ",
        "name": "Invesco QQQ Trust",
        "asset_class": "etf",
        "exchange": "NASDAQ",
        "currency": "USD",
    },
    {
        "symbol": "IWM",
        "name": "iShares Russell 2000 ETF",
        "asset_class": "etf",
        "exchange": "ARCA",
        "currency": "USD",
    },
    {
        "symbol": "TLT",
        "name": "iShares 20+ Year Treasury Bond ETF",
        "asset_class": "etf",
        "exchange": "NASDAQ",
        "currency": "USD",
    },
    {
        "symbol": "GLD",
        "name": "SPDR Gold Shares",
        "asset_class": "etf",
        "exchange": "ARCA",
        "currency": "USD",
    },
    {
        "symbol": "USO",
        "name": "United States Oil Fund",
        "asset_class": "etf",
        "exchange": "ARCA",
        "currency": "USD",
    },
    {
        "symbol": "EEM",
        "name": "iShares MSCI Emerging Markets ETF",
        "asset_class": "etf",
        "exchange": "ARCA",
        "currency": "USD",
    },
    {
        "symbol": "XLF",
        "name": "Financial Select Sector SPDR Fund",
        "asset_class": "etf",
        "exchange": "ARCA",
        "currency": "USD",
    },
    {
        "symbol": "EURUSD=X",
        "name": "EUR/USD",
        "asset_class": "fx",
        "exchange": "FX",
        "currency": "USD",
    },
    {
        "symbol": "GBPUSD=X",
        "name": "GBP/USD",
        "asset_class": "fx",
        "exchange": "FX",
        "currency": "USD",
    },
    {
        "symbol": "JPY=X",
        "name": "USD/JPY",
        "asset_class": "fx",
        "exchange": "FX",
        "currency": "JPY",
    },
    {
        "symbol": "CHF=X",
        "name": "USD/CHF",
        "asset_class": "fx",
        "exchange": "FX",
        "currency": "CHF",
    },
    {
        "symbol": "CL=F",
        "name": "Crude Oil Futures",
        "asset_class": "future",
        "exchange": "NYMEX",
        "currency": "USD",
        "multiplier": Decimal("1000"),
    },
    {
        "symbol": "GC=F",
        "name": "Gold Futures",
        "asset_class": "future",
        "exchange": "COMEX",
        "currency": "USD",
        "multiplier": Decimal("100"),
    },
    {
        "symbol": "SI=F",
        "name": "Silver Futures",
        "asset_class": "future",
        "exchange": "COMEX",
        "currency": "USD",
        "multiplier": Decimal("5000"),
    },
    {
        "symbol": "HG=F",
        "name": "Copper Futures",
        "asset_class": "future",
        "exchange": "COMEX",
        "currency": "USD",
        "multiplier": Decimal("25000"),
    },
    {
        "symbol": "^GSPC",
        "name": "S&P 500 Index",
        "asset_class": "index",
        "exchange": "INDEX",
        "currency": "USD",
    },
]


async def main() -> None:
    session_factory = create_session_factory()
    inserted = 0
    updated = 0

    async with session_factory() as session:
        for item in SEED_INSTRUMENTS:
            multiplier_value = item.get("multiplier", Decimal("1"))
            multiplier = (
                multiplier_value
                if isinstance(multiplier_value, Decimal)
                else Decimal(str(multiplier_value))
            )

            existing_result = await session.execute(
                select(Instrument).where(
                    Instrument.symbol == item["symbol"],
                    Instrument.exchange == item["exchange"],
                )
            )
            existing = existing_result.scalar_one_or_none()

            if existing is None:
                session.add(
                    Instrument(
                        symbol=item["symbol"],
                        name=item["name"],
                        asset_class=item["asset_class"],
                        exchange=item["exchange"],
                        currency=item["currency"],
                        multiplier=multiplier,
                        is_active=True,
                    )
                )
                inserted += 1
            else:
                existing.name = str(item["name"])
                existing.asset_class = str(item["asset_class"])
                existing.currency = str(item["currency"])
                existing.multiplier = multiplier
                existing.is_active = True
                updated += 1

        await session.commit()

    print(f"seed_complete inserted={inserted} updated={updated} total={len(SEED_INSTRUMENTS)}")


if __name__ == "__main__":
    asyncio.run(main())
