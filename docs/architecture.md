# Architecture

AlphaMind is a tiered system: two client applications, one backend service, and a research library. It is not a large microservice mesh; the "services" inside the backend are Python service classes, not separate deployables.

## High-level view

```text
┌─────────────────────┐     ┌─────────────────────┐
│   web-frontend      │     │   mobile-frontend   │
│ React + TS + Vite   │     │ React Native + Expo │
└──────────┬──────────┘     └──────────┬──────────┘
           │  HTTP / JSON              │  HTTP / JSON
           └─────────────┬─────────────┘
                         ▼
              ┌─────────────────────┐
              │   Backend (FastAPI) │
              │  routers → services │
              │  auth (bcrypt+JWT)  │
              │  SQLAlchemy + Alembic
              └──────────┬──────────┘
                         ▼
        ┌────────────────────────────────┐
        │  Data: SQLite (dev) / MySQL /  │
        │  PostgreSQL; Redis (optional)  │
        └────────────────────────────────┘

   code/ai_models: forecasting, RL agents (used by backtest_runner - see below),
                   generative models (not yet wired to the API)
   code/backend: analytics, Bayesian risk, execution, market_data modules
                   (library code, not yet wired to the API)
```

## Backend

The FastAPI application lives in `code/backend/app`. Routers under `app/api/v1/routers` mount at `/api/v1/<group>` with non-versioned `/api/<group>` aliases for compatibility. Each router delegates to a service class in `app/services` (portfolio, strategy, risk, market-data, trading). Authentication is a separate system in `infrastructure/auth` mounted at `/api/auth`.

Request flow:

```text
client → router (/api/v1/...) → service class → (seeded data | live connector | DB | ai_models) → JSON
```

The data routers are open (no auth gate); auth applies to the `/api/auth` endpoints. The market-data service tries live connectors (Yahoo Finance, then optional Polygon) and falls back to a deterministic synthetic generator, tagging each quote with its `source`.

## Data layer

SQLAlchemy 2 models and repositories live in `code/backend/db`. Development uses SQLite (`alphamind.db`), seeded on first run. MySQL (`PyMySQL` / `aiomysql`) and PostgreSQL (`asyncpg`) drivers are present for other environments, and Alembic (`code/backend/alembic`) manages migrations.

## Authentication

Passwords are hashed with bcrypt; sessions are HS256 JSON Web Tokens with an expiry. The signing key comes from `SECRET_KEY`. In `development` a placeholder is tolerated, but when `ENVIRONMENT` (or `APP_ENV`) is `production`, `prod`, or `staging`, the app refuses to start unless `SECRET_KEY` is set to a value of at least 32 characters. Clients store the token and attach it as a bearer token.

## Clients

Both clients render the same domain: dashboard, strategies, portfolio, backtest, risk, market data, trading, research, alternative data, plus documentation, about, and settings. The web app (React 19, Vite, Tailwind, TanStack Query) proxies `/api` to the backend in development. The mobile app (Expo, React Navigation, Redux Toolkit, React Native Paper) resolves its API base URL by platform and persists session and settings in AsyncStorage.

Both clients degrade gracefully: when the backend is unreachable, registration and login produce a local demo session, and data screens show empty or placeholder states rather than failing.

## Contract integrity

Because the clients and the API drifted in the past, the backend ships a contract test suite (`tests/test_frontend_contracts.py`) that asserts the exact field names every client screen reads. A breaking API change fails CI rather than the app at runtime. The web client mirrors this with `src/services/api.test.ts`, which pins the URLs it calls.

## Research library

`code/ai_models` contains forecasting models (transformer, attention, multi-horizon), reinforcement-learning agents (DDPG, PPO) with trading and portfolio environments, and generative models (GAN, regime). `POST /api/v1/backtest/` genuinely trains and evaluates these forecasting and RL models for `ml_alpha`/`rl_agent` strategies via `app/services/backtest_runner.py` (see [BACKTEST_RESULTS.md](BACKTEST_RESULTS.md)); the generative models are not yet wired to any endpoint. `code/backend` additionally holds analytics, Bayesian risk (`bayesian_var`), stress testing, and execution modules (liquidity forecasting, market impact, routing, order management) - these remain importable building blocks that live API responses don't yet call into.

## Infrastructure

`infrastructure/` holds Docker assets, a Kubernetes setup (`base` and `environments`), Terraform modules (compute, database, monitoring, security, config), and Ansible (inventory, playbooks, roles). `code/backend/docker-compose.yml` provisions the API along with PostgreSQL, Redis, and Kafka/Zookeeper for a fuller local environment; the API itself runs without Kafka.
