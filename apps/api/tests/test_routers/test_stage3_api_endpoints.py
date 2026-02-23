from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.models import IngestionLog, Instrument


def _sync_dsn() -> str:
    return (
        f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


def test_api_key_required(client):
    response = client.get("/api/v1/baskets")
    assert response.status_code == 401
    payload = response.json()
    assert payload["error"] == "UNAUTHORIZED"
    assert payload["status"] == 401


def test_create_and_get_basket(client, db_seed):
    headers = {"X-API-Key": "dev-api-key"}
    create_payload = {
        "name": "Tech Pair",
        "description": "Long AAPL short MSFT",
        "benchmark_id": db_seed["spy_id"],
        "legs": [
            {"instrument_id": db_seed["aapl_id"], "side": "long"},
            {"instrument_id": db_seed["msft_id"], "side": "short"},
        ],
    }

    created = client.post("/api/v1/baskets", headers=headers, json=create_payload)
    assert created.status_code == 201
    basket = created.json()
    assert basket["name"] == "Tech Pair"
    assert len(basket["legs"]) == 2

    fetched = client.get(f"/api/v1/baskets/{basket['id']}", headers=headers)
    assert fetched.status_code == 200
    fetched_payload = fetched.json()
    assert fetched_payload["id"] == basket["id"]
    assert fetched_payload["legs"][0]["instrument"]["symbol"] in {"AAPL", "MSFT"}


def test_analytics_endpoints(client, db_seed):
    headers = {"X-API-Key": "dev-api-key"}
    create_payload = {
        "name": "Analytics Basket",
        "legs": [
            {"instrument_id": db_seed["aapl_id"], "side": "long", "weight_override": 0.5},
            {"instrument_id": db_seed["msft_id"], "side": "short", "weight_override": 0.5},
        ],
    }
    basket_response = client.post("/api/v1/baskets", headers=headers, json=create_payload)
    assert basket_response.status_code == 201
    basket_id = basket_response.json()["id"]

    config = {
        "basket_id": basket_id,
        "weight_method": "equal",
        "gross_exposure": 1.0,
        "start_date": db_seed["start_date"],
        "end_date": db_seed["end_date"],
        "benchmark_id": db_seed["spy_id"],
        "lookback_days": 30,
        "include_funding_adj": True,
        "include_trading_costs": True,
        "fee_bps": 4.0,
        "slippage_bps": 6.0,
        "rebalance_freq": "none",
    }

    performance = client.post("/api/v1/analytics/performance", headers=headers, json=config)
    assert performance.status_code == 200
    perf_payload = performance.json()
    assert "series" in perf_payload and len(perf_payload["series"]) > 0
    assert "metrics" in perf_payload
    assert "weights" in perf_payload

    weights = client.post("/api/v1/analytics/weights", headers=headers, json=config)
    assert weights.status_code == 200
    weights_payload = weights.json()
    assert "weights" in weights_payload
    method_names = {snapshot["method"] for snapshot in weights_payload["weights"]}
    assert "equal" in method_names
    assert "manual" in method_names

    risk = client.post("/api/v1/analytics/risk", headers=headers, json=config)
    assert risk.status_code == 200
    risk_payload = risk.json()
    assert "metrics" in risk_payload
    assert "annVol" in risk_payload["metrics"]

    correlation = client.post("/api/v1/analytics/correlation", headers=headers, json=config)
    assert correlation.status_code == 200
    corr_payload = correlation.json()
    assert len(corr_payload["symbols"]) == 2
    assert len(corr_payload["matrix"]) == 2


def test_search_live_fallback_creates_instrument(client, monkeypatch):
    headers = {"X-API-Key": "dev-api-key"}

    async def fake_lookup(_query: str):
        return {
            "symbol": "NVDA",
            "name": "NVIDIA Corp",
            "exchange": "NASDAQ",
            "asset_class": "equity",
            "currency": "USD",
        }

    async def fake_ingest(_symbol: str):
        await asyncio.sleep(0)

    monkeypatch.setattr("app.routers.instruments._lookup_live_instrument", fake_lookup)
    monkeypatch.setattr("app.routers.instruments._ingest_symbol_history", fake_ingest)

    response = client.get(
        "/api/v1/instruments/search?q=NVDA&limit=5",
        headers=headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["symbol"] == "NVDA"
    assert payload[0]["ingesting"] is True


def test_search_db_only_skips_live_lookup(client, monkeypatch):
    headers = {"X-API-Key": "dev-api-key"}

    async def fail_lookup(_query: str):
        raise AssertionError("Live lookup should not run for source=db_only")

    monkeypatch.setattr("app.routers.instruments._lookup_live_instrument", fail_lookup)

    response = client.get(
        "/api/v1/instruments/search?q=NOT_IN_DB&source=db_only",
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json() == []


def test_search_cedear_symbol_sets_currency_and_asset_class(client, monkeypatch):
    headers = {"X-API-Key": "dev-api-key"}

    async def fake_lookup(_query: str):
        return {
            "symbol": "AAPL.BA",
            "name": "Apple CEDEAR",
            "exchange": "BUE",
            "asset_class": "cedear",
            "currency": "ARS",
        }

    async def fake_ingest(_symbol: str):
        await asyncio.sleep(0)

    monkeypatch.setattr("app.routers.instruments._lookup_live_instrument", fake_lookup)
    monkeypatch.setattr("app.routers.instruments._ingest_symbol_history", fake_ingest)

    response = client.get("/api/v1/instruments/search?q=AAPL.BA", headers=headers)
    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["symbol"] == "AAPL.BA"
    assert payload["asset_class"] == "cedear"
    assert payload["currency"] == "ARS"


def test_search_invalid_symbol_returns_not_found(client, monkeypatch):
    headers = {"X-API-Key": "dev-api-key"}

    async def fake_lookup(_query: str):
        return None

    monkeypatch.setattr("app.routers.instruments._lookup_live_instrument", fake_lookup)

    response = client.get("/api/v1/instruments/search?q=INVALID_XYZ", headers=headers)
    assert response.status_code == 404
    payload = response.json()
    assert payload["error"] == "INSTRUMENT_NOT_FOUND"


def test_ingestion_status_endpoint_returns_ingesting(client):
    headers = {"X-API-Key": "dev-api-key"}
    instrument_id = uuid.uuid4()

    engine = create_engine(_sync_dsn())
    with Session(engine) as session:
        session.add(
            Instrument(
                id=instrument_id,
                symbol="DYN",
                name="Dynamic",
                asset_class="equity",
                exchange="NASDAQ",
                currency="USD",
                is_active=True,
            )
        )
        session.flush()
        session.add(
            IngestionLog(
                source="yahoo_finance",
                instrument_id=instrument_id,
                status="partial",
                rows_inserted=0,
                error_message=None,
            )
        )
        session.commit()
    engine.dispose()

    response = client.get(f"/api/v1/instruments/{instrument_id}/ingestion_status", headers=headers)
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ingesting"
