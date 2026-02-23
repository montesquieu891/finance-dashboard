from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from app.config import settings
from app.main import app
from app.models import (
    AlertRule,
    Base,
    Basket,
    BasketLeg,
    Factor,
    FactorDefinition,
    IngestionLog,
    Instrument,
    PriceDaily,
    RealPosition,
    ReturnDaily,
)


def _sync_dsn() -> str:
    return (
        f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


@pytest.fixture(scope="session", autouse=True)
def setup_schema() -> None:
    engine = create_engine(_sync_dsn())
    Base.metadata.create_all(bind=engine)
    engine.dispose()


@pytest.fixture
def db_seed() -> dict[str, str]:
    engine = create_engine(_sync_dsn())
    with Session(engine) as session:
        session.execute(delete(IngestionLog))
        session.execute(delete(AlertRule))
        session.execute(delete(RealPosition))
        session.execute(delete(Factor))
        session.execute(delete(FactorDefinition))
        session.execute(delete(BasketLeg))
        session.execute(delete(Basket))
        session.execute(delete(ReturnDaily))
        session.execute(delete(PriceDaily))
        session.execute(delete(Instrument))

        base_day = date.today() - timedelta(days=180)
        aapl_id = uuid.uuid4()
        msft_id = uuid.uuid4()
        spy_id = uuid.uuid4()

        session.add_all(
            [
                Instrument(
                    id=aapl_id,
                    symbol="AAPL",
                    name="Apple",
                    asset_class="equity",
                    exchange="NASDAQ",
                    currency="USD",
                    is_active=True,
                ),
                Instrument(
                    id=msft_id,
                    symbol="MSFT",
                    name="Microsoft",
                    asset_class="equity",
                    exchange="NASDAQ",
                    currency="USD",
                    is_active=True,
                ),
                Instrument(
                    id=spy_id,
                    symbol="SPY",
                    name="SPDR S&P 500 ETF",
                    asset_class="etf",
                    exchange="NYSEARCA",
                    currency="USD",
                    is_active=True,
                ),
            ]
        )

        for idx in range(150):
            trade_day = base_day + timedelta(days=idx)
            if trade_day.weekday() >= 5:
                continue

            session.add_all(
                [
                    ReturnDaily(
                        instrument_id=aapl_id,
                        date=trade_day,
                        simple_return=0.001 + (idx % 5) * 0.0002,
                    ),
                    ReturnDaily(
                        instrument_id=msft_id,
                        date=trade_day,
                        simple_return=0.0008 + (idx % 3) * 0.00015,
                    ),
                    ReturnDaily(
                        instrument_id=spy_id,
                        date=trade_day,
                        simple_return=0.0006 + (idx % 4) * 0.0001,
                    ),
                ]
            )

        session.commit()
    engine.dispose()

    return {
        "aapl_id": str(aapl_id),
        "msft_id": str(msft_id),
        "spy_id": str(spy_id),
        "start_date": str(base_day),
        "end_date": str(base_day + timedelta(days=149)),
    }


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client
