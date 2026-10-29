# AlphaMind

![CI/CD Status](https://img.shields.io/github/actions/workflow/status/quantsingularity/AlphaMind/cicd.yml?branch=main&label=CI%2FCD&logo=github)

## Quantitative AI Trading Platform

AlphaMind is a full-stack quantitative trading platform: a FastAPI backend that serves portfolio, strategy, risk, backtest, market-data, trading, research, and alternative-data APIs, a React web dashboard, and a React Native (Expo) mobile app, all sharing one "Quant Terminal" design language. Alongside the application is a research codebase of machine-learning and quantitative modules (forecasting transformers, reinforcement-learning agents, generative models, Bayesian risk, and execution analytics).

<div align="center">
  <img src="docs/images/homepage.bmp" alt="AlphaMind HomePage" width="100%">
</div>

## Table of Contents

- [Overview](#overview)
- [Project Structure](#project-structure)
- [Feature Status](#feature-status)
- [Technology Stack](#technology-stack)
- [Architecture](#architecture)
- [Installation and Setup](#installation-and-setup)
- [Running the Stack](#running-the-stack)
- [API Surface](#api-surface)
- [Testing](#testing)
- [CI/CD Pipeline](#cicd-pipeline)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

## Overview

AlphaMind demonstrates an institutional-style quant workflow across a real, runnable codebase. The application tier (backend plus two clients) is fully wired and covered by tests. The research tier is a library of ML and quant modules that the application can draw on and that can be used independently for experimentation.

## Project Structure

```text
AlphaMind/
├── code/
│   ├── backend/            # FastAPI service: API, auth, services, DB, infra
│   │   ├── app/            # FastAPI app, routers (v1 API), services
│   │   ├── analytics/      # Alpha research, A/B testing, model validation, viz
│   │   ├── core/           # Config and exceptions
│   │   ├── data_processing/# Caching, monitoring, parallel, pipeline, streaming
│   │   ├── db/             # SQLAlchemy models, repositories, session
│   │   ├── execution/      # Liquidity forecasting, market impact, routing, OMS
│   │   ├── infrastructure/ # Auth system (bcrypt + JWT)
│   │   ├── market_data/    # Connectors, live feed, backtesting, exchange API
│   │   ├── risk/           # Bayesian VaR, stress testing, controls, counterparty
│   │   ├── tests/          # Backend test suite
│   │   ├── alembic/        # Database migrations
│   │   ├── docker-compose.yml
│   │   └── requirements.txt
│   └── ai_models/          # Research ML library
│       ├── agents/         # DDPG, PPO, replay buffer
│       ├── environments/   # Trading and portfolio Gym environments
│       ├── forecasting/    # Transformer, attention, multi-horizon models
│       ├── generative/     # GAN, generator, discriminator, regime models
│       ├── research/       # Factor, alpha decay, regime, execution studies
│       └── examples/       # Runnable usage examples per module
├── web-frontend/           # React + TypeScript + Vite dashboard
├── mobile-frontend/        # React Native + Expo app
├── infrastructure/         # Docker, Kubernetes, Terraform, Ansible
├── scripts/                # Build, test, deploy, and dev helper scripts
├── docs/                   # Documentation (this directory)
└── README.md
```

## Feature Status

### Application tier (wired and tested)

| Component                | Details                                                                                                                                                                                                                                                      |
| :----------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **API**                  | FastAPI backend exposing versioned endpoints under `/api/v1` (with non-versioned `/api/*` aliases) for portfolio, strategies, risk, backtest, market data, trading, research, and alternative data, plus authentication under `/api/auth` and health checks. |
| **Auth**                 | bcrypt password hashing and HS256 JSON Web Tokens with expiry. The signing key is read from `SECRET_KEY`, and the app refuses to start in production or staging if it is unset, the placeholder, or shorter than 32 characters.                              |
| **Market data**          | A live connector waterfall (Yahoo Finance, then an optional Polygon connector) backed by a deterministic synthetic fallback, so quotes and history are always available.                                                                                     |
| **Data layer**           | SQLAlchemy over SQLite in development (`alphamind.db`), with async MySQL and PostgreSQL drivers for other environments and Alembic managing migrations.                                                                                                      |
| **Web dashboard**        | React app covering Home, Dashboard, Strategies, Portfolio, Backtest, Risk, Market Data, Trading, Research, Alternative Data, Documentation, About, Settings, and authentication screens.                                                                     |
| **Mobile app**           | React Native (Expo) app covering the same functional areas through bottom-tab and stacked navigation, Redux Toolkit state, and a light/dark theme. Alternative data is surfaced inside the Research screen rather than as its own tab.                       |
| **Graceful degradation** | If the backend is unreachable, both clients fall back to a local demo session for account creation and sign-in, and data screens render empty or placeholder states instead of failing hard.                                                                 |

### Research tier (library modules)

`POST /api/v1/backtest/` genuinely trains and evaluates real models for `rl_agent` and `ml_alpha` strategies via `app/services/backtest_runner.py` - see [docs/BACKTEST_RESULTS.md](docs/BACKTEST_RESULTS.md). The rest of these modules are part of the codebase and can be imported and run, but aren't yet wired into any live API response.

| Component                  | Details                                                                                    | Connected to the live API? |
| :------------------------- | :----------------------------------------------------------------------------------------- | :------------------------- |
| **Forecasting**            | Transformer, attention, and multi-horizon model implementations (PyTorch / TensorFlow).    | Yes - `ml_alpha` backtests |
| **Reinforcement learning** | DDPG and PPO agents with replay buffers and custom trading and portfolio Gym environments. | Yes - `rl_agent` backtests |
| **Generative models**      | GAN components for synthetic series and a regime model.                                    | Not yet                    |
| **Risk**                   | Bayesian Value at Risk (PyMC), stress testing, counterparty and aggregation modules.       | Not yet                    |
| **Execution**              | Liquidity forecasting, market-impact, order management, and routing modules.               | Not yet                    |

## Technology Stack

| Area            | Technology                                                                                           |
| :-------------- | :--------------------------------------------------------------------------------------------------- |
| Backend API     | Python 3.10+, FastAPI, Uvicorn, Pydantic v2                                                          |
| Auth            | bcrypt, PyJWT / python-jose, passlib                                                                 |
| Data layer      | SQLAlchemy 2, Alembic, SQLite (dev), MySQL / PostgreSQL (async drivers), Redis                       |
| ML / Quant      | PyTorch, TensorFlow, scikit-learn, Gymnasium, Stable-Baselines3, PyMC, QuantLib, NumPy, Pandas, Dask |
| Market data     | yfinance (Yahoo Finance), optional Polygon connector                                                 |
| Web frontend    | React 19, TypeScript, Vite 7, Tailwind CSS, React Router, TanStack Query, axios, Recharts            |
| Mobile frontend | React Native, Expo, React Navigation, Redux Toolkit, React Native Paper, axios                       |
| Infrastructure  | Docker, Docker Compose, Kubernetes, Terraform, Ansible                                               |
| CI/CD           | GitHub Actions                                                                                       |
| Testing         | pytest (backend), Vitest (web), Jest (mobile)                                                        |

## Architecture

AlphaMind is organized in tiers rather than a sprawl of microservices:

```text
Clients
  ├── web-frontend (React/TS)            ── HTTP/JSON ──┐
  └── mobile-frontend (React Native)     ── HTTP/JSON ──┤
                                                        ▼
Backend (FastAPI)
  ├── Routers (/api/v1/*)  auth, portfolio, strategies, risk,
  │                        backtest, market-data, trading,
  │                        research, alternative-data, health
  ├── Services            portfolio, strategy, risk, market-data, trading,
  │                        backtest_runner (trains/evaluates ai_models
  │                        agents and forecasters for rl_agent/ml_alpha
  │                        backtests - see docs/BACKTEST_RESULTS.md)
  ├── Auth                bcrypt + JWT (HS256), fail-closed secret
  └── Data layer          SQLAlchemy + Alembic (SQLite / MySQL / PostgreSQL)
                                                        ▼
ai_models (code/ai_models)                  ◄── used by backtest_runner
  forecasting · reinforcement learning (agents + Gym environments) · generative

Research library (code/backend/{analytics,risk,execution})
  Bayesian risk · execution (liquidity, market-impact) - not yet wired in
```

The frontends are the source of presentation; the backend is the source of truth for data contracts. A dedicated contract test suite pins every response field the clients read so the tiers cannot drift apart silently.

See [docs/architecture.md](docs/architecture.md) for detail.

## Installation and Setup

Prerequisites: Python 3.10+ and Node.js 18+. Docker is optional.

```bash
git clone https://github.com/quantsingularity/AlphaMind.git
cd AlphaMind

# Backend
cd code/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Web frontend
cd ../../web-frontend
npm install

# Mobile frontend
cd ../mobile-frontend
npm install
```

Full, environment-specific instructions are in [docs/INSTALLATION.md](docs/INSTALLATION.md).

## Running the Stack

```bash
# 1) Backend (from code/backend, venv active)
python -m main                # serves http://0.0.0.0:8000, docs at /docs

# 2) Web dashboard (from web-frontend)
npm run dev                   # http://localhost:3000, proxies /api to :8000

# 3) Mobile app (from mobile-frontend)
npm start                     # press w for web, a for Android, i for iOS
```

The web dashboard proxies API calls to port 8000. The mobile app resolves the API base URL automatically: on web it uses the host the app was opened from (so opening it via a LAN IP reaches a backend on the same machine), on the Android emulator it uses `10.0.2.2:8000`, and otherwise `localhost:8000`. Override with `EXPO_PUBLIC_API_BASE_URL`.

See [docs/USAGE.md](docs/USAGE.md) and [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## API Surface

Base URL `http://localhost:8000`. Interactive docs at `/docs` (Swagger) and `/redoc`.

| Group            | Prefix                     | Highlights                                        |
| :--------------- | :------------------------- | :------------------------------------------------ |
| Health           | `/health`, `/`             | Liveness check                                    |
| Auth             | `/api/auth`                | `register`, `login`, `refresh`, `profile`         |
| Portfolio        | `/api/v1/portfolio`        | summary, `positions`, `holdings`, `performance`   |
| Strategies       | `/api/v1/strategies`       | list, detail, `{id}/equity-curve`                 |
| Risk             | `/api/v1/risk`             | `metrics`, `stress-scenarios`, `radar`            |
| Backtest         | `/api/v1/backtest`         | run a backtest (POST)                             |
| Market data      | `/api/v1/market-data`      | `quotes`, `quote/{ticker}`, `historical/{ticker}` |
| Trading          | `/api/v1/trading`          | `orders` (GET/POST/DELETE)                        |
| Research         | `/api/v1/research`         | `papers`                                          |
| Alternative data | `/api/v1/alternative-data` | `sources`                                         |

Non-versioned `/api/*` aliases exist for backward compatibility. Full request and response shapes are in [docs/API.md](docs/API.md).

## Testing

```bash
# Backend (from code/backend)
pytest

# Web (from web-frontend)
npm test

# Mobile (from mobile-frontend)
npm test
```

The backend suite includes contract tests (`tests/test_frontend_contracts.py`) that pin the API shapes the clients consume, security tests (`tests/test_security.py`) covering password hashing and secret hardening, and market-data tests (`tests/test_market_data_service.py`) covering the live and synthetic paths. Some model tests require TensorFlow and are skipped if it is not installed.

## CI/CD Pipeline

GitHub Actions (`.github/workflows/cicd.yml`) runs seven jobs on push, pull request, and manual dispatch:

| Job                          | Depends on          | What it does                                                                                                                                                                                                                                                                                                 |
| :--------------------------- | :------------------ | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Code Quality Checks          | -                   | Python formatter checks and a repository-wide Prettier check                                                                                                                                                                                                                                                 |
| Backend Test & Build         | Code Quality Checks | Runs the pytest suite, a dedicated frontend/backend contract-test step, and uploads a coverage report, then builds the backend Docker image with Buildx and uploads it as an artifact                                                                                                                        |
| Web-Frontend Test & Build    | Code Quality Checks | Runs the Vitest suite and produces the production web build                                                                                                                                                                                                                                                  |
| Mobile-Frontend Test & Build | Code Quality Checks | Runs the Jest suite and produces the Expo web export                                                                                                                                                                                                                                                         |
| Docs Validation              | Code Quality Checks | Lints the Markdown docs, checks internal links, validates the code samples, and checks `docs/CLI.md` against `scripts/`                                                                                                                                                                                      |
| Infrastructure Validation    | Code Quality Checks | Terraform fmt/validate/TFLint and toggle wiring; Kubernetes base and all environment overlays (kustomize + kubeconform + semantic checks); Ansible syntax, host matching, role template/include references and rendered templates; Docker Compose, Dockerfile lint, frontend image build, and a secrets scan |
| Scripts Validation           | Code Quality Checks | ShellCheck, syntax and shebang checks on every tracked shell script, and a `--help` smoke test for the CLI scripts                                                                                                                                                                                           |

## Documentation

| Document                                             | Contents                                |
| :--------------------------------------------------- | :-------------------------------------- |
| [docs/README.md](docs/README.md)                     | Documentation index                     |
| [docs/architecture.md](docs/architecture.md)         | System architecture                     |
| [docs/API.md](docs/API.md)                           | REST API reference                      |
| [docs/INSTALLATION.md](docs/INSTALLATION.md)         | Setup for all components                |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md)       | Environment variables and config        |
| [docs/USAGE.md](docs/USAGE.md)                       | Running and using the platform          |
| [docs/CLI.md](docs/CLI.md)                           | Helper scripts reference                |
| [docs/FEATURE_MATRIX.md](docs/FEATURE_MATRIX.md)     | Feature status, implemented vs planned  |
| [docs/BACKTEST_RESULTS.md](docs/BACKTEST_RESULTS.md) | How backtests work and how to read them |
| [docs/troubleshooting.md](docs/troubleshooting.md)   | Common issues and fixes                 |
| [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)         | Contribution guide                      |
| [docs/examples/](docs/examples/)                     | Worked examples                         |

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
