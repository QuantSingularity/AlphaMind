"""
Basic API functionality tests — updated to match v2 API contracts.
"""

from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "alphamind-api"
    assert "version" in data


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_docs_available():
    response = client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert "openapi" in schema
    assert schema["info"]["title"] == "AlphaMind API"


def test_trading_orders_endpoint():
    """v2: field names are camelCase; status code is 201 Created."""
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


def test_get_orders_endpoint():
    response = client.get("/api/v1/trading/orders")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_portfolio_endpoint():
    """v2: portfolio uses camelCase keys; no 'positions' at top level."""
    response = client.get("/api/v1/portfolio/")
    assert response.status_code == 200
    data = response.json()
    assert "totalValue" in data
    assert "cash" in data
    assert "dailyPnL" in data
    assert "allocation" in data
    assert isinstance(data["allocation"], list)


def test_portfolio_positions_endpoint():
    """v2: positions are at /portfolio/positions."""
    response = client.get("/api/v1/portfolio/positions")
    assert response.status_code == 200
    positions = response.json()
    assert isinstance(positions, list)
    assert len(positions) > 0
    assert "ticker" in positions[0]


def test_portfolio_performance_endpoint():
    """v2: performance returns equityCurve + metrics object."""
    response = client.get("/api/v1/portfolio/performance")
    assert response.status_code == 200
    data = response.json()
    assert "equityCurve" in data
    assert "metrics" in data
    assert "sharpeRatio" in data["metrics"]
    assert "maxDrawdown" in data["metrics"]


def test_market_data_quote_endpoint():
    """v2: uses 'ticker' and 'last' instead of 'symbol' and 'price'."""
    response = client.get("/api/v1/market-data/quote/AAPL")
    assert response.status_code == 200
    data = response.json()
    assert data["ticker"] == "AAPL"
    assert "last" in data
    assert "volume" in data
    assert "timestamp" in data


def test_market_data_historical_endpoint():
    """v2: returns a list of OHLCV records directly."""
    response = client.get("/api/v1/market-data/historical/AAPL?days=30")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 30
    assert "timestamp" in data[0]
    assert "close" in data[0]


def test_strategies_endpoint():
    response = client.get("/api/v1/strategies/")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0


def test_backtest_endpoint():
    """v2: backtest is at /api/v1/backtest/ — dedicated router."""
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


def test_risk_metrics_endpoint():
    response = client.get("/api/v1/risk/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "var" in data
    assert "sharpeRatio" in data


def test_invalid_endpoint():
    response = client.get("/api/v1/invalid/endpoint")
    assert response.status_code == 404


def test_cors_headers():
    response = client.get("/health")
    assert response.status_code == 200
