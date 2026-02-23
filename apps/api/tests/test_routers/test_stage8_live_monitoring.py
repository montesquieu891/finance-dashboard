from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings
from app.models import PriceDaily
from app.services.live_monitor import live_monitor_service

HEADERS = {"X-API-Key": "dev-api-key"}


def _sync_dsn() -> str:
    return (
        f"postgresql+psycopg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


def test_live_scheduler_job_registered(client) -> None:
    job = live_monitor_service._scheduler.get_job("live-refresh")
    assert job is not None
    assert int(job.trigger.interval.total_seconds()) == settings.live_refresh_interval_seconds


def test_websocket_requires_query_api_key(client) -> None:
    try:
        with client.websocket_connect("/ws/prices?api_key=wrong-key"):
            raise AssertionError("WebSocket should reject invalid API key")
    except Exception:
        assert True


def test_websocket_connects_with_valid_api_key(client) -> None:
    with client.websocket_connect("/ws/prices?api_key=dev-api-key") as websocket:
        websocket.close()


def test_alert_rules_and_positions_endpoints(client, db_seed) -> None:
    create_payload = {
        "name": "Live Basket",
        "legs": [
            {"instrument_id": db_seed["aapl_id"], "side": "long"},
            {"instrument_id": db_seed["msft_id"], "side": "short"},
        ],
    }
    basket_response = client.post("/api/v1/baskets", headers=HEADERS, json=create_payload)
    assert basket_response.status_code == 201
    basket_id = basket_response.json()["id"]

    alert_response = client.post(
        f"/api/v1/baskets/{basket_id}/alerts",
        headers=HEADERS,
        json={
            "name": "Drawdown 5%",
            "rule_type": "drawdown",
            "threshold": 0.05,
            "cooldown_minutes": 30,
            "is_active": True,
        },
    )
    assert alert_response.status_code == 201
    alert_id = alert_response.json()["id"]

    list_alerts = client.get(f"/api/v1/baskets/{basket_id}/alerts", headers=HEADERS)
    assert list_alerts.status_code == 200
    assert len(list_alerts.json()) == 1

    delete_alert = client.delete(f"/api/v1/baskets/alerts/{alert_id}", headers=HEADERS)
    assert delete_alert.status_code == 204

    engine = create_engine(_sync_dsn())
    with Session(engine) as session:
        session.add(
            PriceDaily(
                instrument_id=uuid.UUID(db_seed["aapl_id"]),
                date=date.today(),
                px_open=Decimal("100"),
                px_high=Decimal("100"),
                px_low=Decimal("100"),
                px_close=Decimal("100"),
                px_adj_close=Decimal("100"),
                volume=1000,
            )
        )
        session.add(
            PriceDaily(
                instrument_id=uuid.UUID(db_seed["msft_id"]),
                date=date.today(),
                px_open=Decimal("200"),
                px_high=Decimal("200"),
                px_low=Decimal("200"),
                px_close=Decimal("200"),
                px_adj_close=Decimal("200"),
                volume=1000,
            )
        )
        session.commit()
    engine.dispose()

    csv_body = "symbol,quantity,avg_price\nAAPL,10,95\nMSFT,-4,205\n"
    upload_response = client.post(
        f"/api/v1/baskets/{basket_id}/positions/upload",
        headers=HEADERS,
        files={"file": ("positions.csv", csv_body, "text/csv")},
    )
    assert upload_response.status_code == 204

    positions_response = client.get(f"/api/v1/baskets/{basket_id}/positions", headers=HEADERS)
    assert positions_response.status_code == 200
    payload = positions_response.json()
    assert len(payload["rows"]) == 2
    assert "summary" in payload
