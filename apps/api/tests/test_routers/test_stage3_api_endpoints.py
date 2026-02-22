from __future__ import annotations


def test_api_key_required(client):
    response = client.get("/health")
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
