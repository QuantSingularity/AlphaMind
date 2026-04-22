"""
Tests for AlphaMind API endpoints — updated to match v2 API contracts.
"""

import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    def test_health_check(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "alphamind-api"
        assert "version" in data

    def test_root_endpoint(self):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestTradingEndpoints:
    def test_create_order(self):
        """Order creation — uses camelCase field names matching TypeScript types."""
        order_data = {
            "ticker": "AAPL",
            "side": "BUY",
            "quantity": 100.0,
            "orderType": "MARKET",
            "price": None,
        }
        response = client.post("/api/v1/trading/orders", json=order_data)
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["ticker"] == "AAPL"
        assert data["quantity"] == 100.0
        assert data["status"] == "pending"

    def test_get_orders(self):
        response = client.get("/api/v1/trading/orders")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_order_not_found(self):
        response = client.get("/api/v1/trading/orders/invalid-id")
        assert response.status_code == 404


class TestPortfolioEndpoints:
    def test_get_portfolio(self):
        response = client.get("/api/v1/portfolio/")
        assert response.status_code == 200
        data = response.json()
        # v2 API uses camelCase keys matching the TypeScript Portfolio interface
        assert "totalValue" in data
        assert "cash" in data
        assert "dailyPnL" in data
        assert "totalPnL" in data
        assert "allocation" in data
        assert isinstance(data["allocation"], list)

    def test_get_performance(self):
        response = client.get("/api/v1/portfolio/performance")
        assert response.status_code == 200
        data = response.json()
        # v2 performance endpoint returns equityCurve + metrics object
        assert "equityCurve" in data
        assert "metrics" in data
        metrics = data["metrics"]
        assert "sharpeRatio" in metrics
        assert "maxDrawdown" in metrics
        assert "annualisedReturn" in metrics
        assert "volatility" in metrics

    def test_get_positions(self):
        response = client.get("/api/v1/portfolio/positions")
        assert response.status_code == 200
        positions = response.json()
        assert isinstance(positions, list)
        assert len(positions) > 0
        pos = positions[0]
        assert "id" in pos
        assert "ticker" in pos
        assert "quantity" in pos
        assert "unrealizedPnL" in pos


class TestMarketDataEndpoints:
    def test_get_quote(self):
        response = client.get("/api/v1/market-data/quote/AAPL")
        assert response.status_code == 200
        data = response.json()
        # v2 uses 'ticker' not 'symbol', and 'last' not 'price'
        assert data["ticker"] == "AAPL"
        assert "last" in data
        assert "volume" in data
        assert "timestamp" in data

    def test_get_historical_data(self):
        response = client.get("/api/v1/market-data/historical/AAPL?days=30")
        assert response.status_code == 200
        data = response.json()
        # v2 returns a list of OHLCV records directly
        assert isinstance(data, list)
        assert len(data) == 30
        record = data[0]
        assert "timestamp" in record
        assert "open" in record
        assert "high" in record
        assert "low" in record
        assert "close" in record
        assert "volume" in record


class TestStrategyEndpoints:
    def test_get_strategies(self):
        response = client.get("/api/v1/strategies/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0
        s = data[0]
        assert "id" in s
        assert "name" in s
        assert "performance" in s

    def test_run_backtest(self):
        """Backtest is a dedicated endpoint at /api/v1/backtest/ in v2."""
        backtest_data = {
            "strategyId": "strat-001",
            "startDate": "2023-01-01",
            "endDate": "2023-12-31",
            "initialCapital": 100000.0,
        }
        response = client.post("/api/v1/backtest/", json=backtest_data)
        assert response.status_code == 201
        data = response.json()
        assert data["strategyId"] == "strat-001"
        assert "totalReturn" in data
        assert "sharpeRatio" in data
        assert "maxDrawdown" in data
        assert "totalTrades" in data


class TestRiskEndpoints:
    def test_get_risk_metrics(self):
        response = client.get("/api/v1/risk/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "var" in data
        assert "cvar" in data
        assert "sharpeRatio" in data
        assert "maxDrawdown" in data

    def test_get_stress_scenarios(self):
        response = client.get("/api/v1/risk/stress-scenarios")
        assert response.status_code == 200
        scenarios = response.json()
        assert isinstance(scenarios, list)
        assert len(scenarios) > 0

    def test_get_correlation_matrix(self):
        response = client.get("/api/v1/risk/correlation-matrix")
        assert response.status_code == 200
        matrix = response.json()
        assert isinstance(matrix, list)
        assert len(matrix) > 0


class TestAlternativeDataEndpoints:
    def test_get_sources(self):
        response = client.get("/api/v1/alternative-data/sources")
        assert response.status_code == 200
        sources = response.json()
        assert isinstance(sources, list)
        assert len(sources) > 0
        src = sources[0]
        assert "id" in src
        assert "name" in src
        assert "type" in src
        assert "status" in src
