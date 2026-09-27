# AlphaMind Backend

Institutional-grade quantitative AI trading system.

---

## Directory Structure

```
backend/
├── main.py                      # Entry point - delegates to app.main
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── pytest.ini
│
├── app/                         # FastAPI application layer
│   ├── main.py                  # FastAPI app, middleware, router registration
│   ├── api/
│   │   ├── dependencies/        # Dependency injection (auth, DB sessions)
│   │   └── v1/
│   │       └── routers/         # HTTP endpoints: health, trading, portfolio,
│   │                            #   market_data, strategies
│   ├── schemas/                 # Shared Pydantic response schemas
│   └── services/                # Business logic between routers and domain
│
├── core/                        # Domain primitives & cross-cutting concerns
│   ├── __init__.py              # MarketData, Signal, BaseModule
│   ├── config.py                # ConfigManager (YAML/JSON/ENV loading)
│   └── exceptions.py            # AlphaMindException hierarchy
│
├── analytics/                   # Research, data science, model validation
│   ├── ab_testing/              # A/B experiment framework
│   ├── alpha_research/
│   │   ├── data_processor.py
│   │   ├── portfolio_optimization.py
│   │   ├── factor_models/       # ML-based alpha factors
│   │   └── regime_detection/    # Real-time changepoint detection
│   ├── alternative_data/
│   │   ├── sentiment_analysis.py
│   │   ├── satellite_processing.py
│   │   └── scrapers/            # SEC 8-K monitor, web scrapers
│   ├── model_validation/        # Cross-validation, metrics, explainability
│   ├── visualization/           # Dash dashboard
│   └── reinforcement_learning.py
│
├── market_data/                 # Data acquisition & real-time feeds
│   ├── connectors/              # Bloomberg, Refinitiv, Yahoo, Polygon,
│   │                            #   Tiingo, Quandl, Intrinio, IEX, FRED, AV
│   ├── live_feed.py             # WebSocket & Kafka live market data
│   ├── exchange_api.py          # Exchange REST/WS integration
│   ├── backtesting.py           # Event-driven backtest engine
│   └── alternative_data.py     # Alternative data loader
│
├── execution/                   # Order execution engine
│   ├── order_management/        # OrderManager, connectivity, reconnection,
│   │                            #   strategy selector
│   ├── routing/                 # Smart Order Routing (SOR)
│   ├── liquidity_forecasting.py
│   └── market_impact.py
│
├── risk/                        # Risk management
│   ├── aggregation/             # PortfolioRisk, PositionLimits,
│   │                            #   RealTimeMonitoring
│   ├── controls/                # Circuit breakers, risk controls
│   ├── counterparty/            # CVA / credit value adjustment
│   ├── bayesian_var.py
│   └── stress_testing.py
│
├── data_processing/             # ETL, streaming, caching, parallel compute
│   ├── pipeline.py
│   ├── streaming.py
│   ├── parallel.py
│   ├── caching.py
│   └── monitoring.py
│
├── infrastructure/              # External system integrations
│   ├── auth/                    # JWT authentication (FastAPI)
│   ├── cloud/
│   │   └── gcp_vertex/          # Vertex AI pipeline orchestration
│   ├── messaging/
│   │   └── kafka/               # Confluent Kafka consumers
│   └── pricing/
│       ├── quantlib/            # Exotic option pricing (QuantLib)
│       └── volatility_surface.py
│
└── tests/                       # Backend test suite (pytest)
```

---

## Running the API

```bash
# Development
uvicorn app.main:app --reload

# Production (via Docker)
docker build -t alphamind-backend .
docker run -p 8000:8000 alphamind-backend
```

API docs available at `http://localhost:8000/docs`.

---

## Running Tests

```bash
cd backend
pytest
```

### Contract tests

`tests/test_frontend_contracts.py` pins the exact response field names that the
web and mobile clients read, so an API change that would break a client fails
in CI rather than in production. `tests/test_security.py` covers auth hardening
(bcrypt hashing, JWT signing, secret validation) and
`tests/test_market_data_service.py` covers the live-data waterfall and its
deterministic synthetic fallback.

```bash
pytest tests/test_frontend_contracts.py tests/test_security.py tests/test_market_data_service.py
```

## Security

Authentication uses bcrypt password hashing and HS256-signed JWTs. The signing
key is read from `SECRET_KEY`. In `development` the app allows a placeholder
key, but when `ENVIRONMENT` (or `APP_ENV`) is `production`, `prod`, or
`staging`, the app refuses to start unless `SECRET_KEY` is set to a strong value
of at least 32 characters. Always set a real `SECRET_KEY` before deploying.
