"""
HTTP-level tests for the rewritten POST /api/v1/backtest/.

test_api.py and test_frontend_contracts.py already cover the happy path
against the seeded demo strategies; these tests cover the error paths and
the equity-curve field that previously existed in the response dict but
was silently dropped by FastAPI's response_model filtering (BacktestResult
didn't declare an equityCurve field) - the exact bug that made the
frontend's Backtest page chart always render empty.
"""

import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app  # noqa: E402

client = TestClient(app)


class TestBacktestErrorPaths:
    def test_unknown_strategy_returns_404(self) -> None:
        response = client.post(
            "/api/v1/backtest/",
            json={
                "strategyId": "does-not-exist",
                "startDate": "2023-01-01",
                "endDate": "2023-06-30",
                "initialCapital": 100000.0,
            },
        )
        assert response.status_code == 404

    def test_unsupported_strategy_type_returns_422(self) -> None:
        create = client.post(
            "/api/v1/strategies/",
            json={
                "name": "Bogus Strategy",
                "description": "test",
                "type": "not_a_real_type",
                "parameters": {},
            },
        )
        assert create.status_code in (200, 201), create.text
        strategy_id = create.json()["id"]

        response = client.post(
            "/api/v1/backtest/",
            json={
                "strategyId": strategy_id,
                "startDate": "2023-01-01",
                "endDate": "2023-06-30",
                "initialCapital": 100000.0,
            },
        )
        assert response.status_code == 422


class TestBacktestEquityCurve:
    def test_response_includes_equity_curve(self) -> None:
        """The exact regression this fixes: the response used to compute
        an equity curve but never actually returned it to the client."""
        strategies = client.get("/api/v1/strategies/").json()
        momentum_strategy = next(s for s in strategies if s["type"] == "momentum")

        response = client.post(
            "/api/v1/backtest/",
            json={
                "strategyId": momentum_strategy["id"],
                "startDate": "2023-01-01",
                "endDate": "2023-06-30",
                "initialCapital": 100000.0,
            },
        )
        assert response.status_code == 201
        body = response.json()
        assert "equityCurve" in body
        assert len(body["equityCurve"]) > 0
        point = body["equityCurve"][0]
        assert {"date", "equity", "benchmark", "drawdown"} == set(point.keys())
