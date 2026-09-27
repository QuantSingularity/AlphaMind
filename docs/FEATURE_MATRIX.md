# Feature Matrix

An honest status of what exists in this repository. Three states are used:

- Implemented: wired end to end and exercised by tests or the running app.
- Library: real code exists and can be imported and run, but it is not connected to the live API responses (which are seeded by default).
- Infrastructure: configuration is present; standing it up is environment-specific.
- Planned: not in the project.

## Application

| Capability                                            | Status      | Notes                                                                                                                                                                                                                                                                                                                         |
| :---------------------------------------------------- | :---------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Auth (register, login, refresh, profile)              | Implemented | bcrypt + JWT; secret fail-closed in prod.                                                                                                                                                                                                                                                                                     |
| Portfolio (summary, positions, holdings, performance) | Implemented | Seeded data via service layer.                                                                                                                                                                                                                                                                                                |
| Strategies (list, detail, equity curve)               | Implemented | Seeded metrics.                                                                                                                                                                                                                                                                                                               |
| Risk (metrics, stress scenarios, radar)               | Implemented | Seeded metrics.                                                                                                                                                                                                                                                                                                               |
| Backtest (run, metrics)                               | Implemented | Real simulation: `rl_agent`/`ml_alpha` strategies train and run an ai_models agent/forecaster, `momentum`/`mean_reversion` run rule-based logic through `BacktestEngine` - all against a synthetic price series (see `app/services/backtest_runner.py`). Runs as a background task; poll `GET /backtest/{id}` for the result. |
| Market data (quotes, quote, history)                  | Implemented | Live via Yahoo Finance / Polygon, synthetic fallback.                                                                                                                                                                                                                                                                         |
| Trading (orders, cancel)                              | Implemented | Simulated in-process; no live broker.                                                                                                                                                                                                                                                                                         |
| Research (papers)                                     | Implemented | Static catalogue.                                                                                                                                                                                                                                                                                                             |
| Alternative data (sources)                            | Implemented | Source registry with status and latency.                                                                                                                                                                                                                                                                                      |
| Web dashboard (all screens)                           | Implemented | React 19 + Vite + Tailwind.                                                                                                                                                                                                                                                                                                   |
| Mobile app (all screens)                              | Implemented | Expo + React Navigation + Redux Toolkit.                                                                                                                                                                                                                                                                                      |
| Light / dark theme + toggle                           | Implemented | Persisted on device.                                                                                                                                                                                                                                                                                                          |
| Offline demo fallback                                 | Implemented | Both clients.                                                                                                                                                                                                                                                                                                                 |
| Contract / security / market-data tests               | Implemented | In the backend suite.                                                                                                                                                                                                                                                                                                         |
| Forecasting: transformer, attention, multi-horizon    | Implemented | `code/ai_models/forecasting`, driven by `ml_alpha` backtests via `app/services/backtest_runner.py`.                                                                                                                                                                                                                           |
| RL agents: DDPG, PPO, replay buffer                   | Implemented | `code/ai_models/agents`, driven by `rl_agent` backtests via `app/services/backtest_runner.py` (PPO falls back to DDPG if `stable-baselines3` isn't installed).                                                                                                                                                                |
| Trading / portfolio Gym environments                  | Implemented | `code/ai_models/environments`, used by `rl_agent` backtests for both training and evaluation.                                                                                                                                                                                                                                 |

## Research library

| Capability                                                          | Status  | Location                            |
| :------------------------------------------------------------------ | :------ | :---------------------------------- |
| Generative: GAN, regime model                                       | Library | `code/ai_models/generative`         |
| Bayesian Value at Risk                                              | Library | `code/backend/risk/bayesian_var.py` |
| Stress testing, counterparty, aggregation                           | Library | `code/backend/risk`                 |
| Execution: liquidity forecasting, market impact, routing, OMS       | Library | `code/backend/execution`            |
| Analytics: alpha research, A/B testing, model validation            | Library | `code/backend/analytics`            |
| Data processing: caching, monitoring, parallel, pipeline, streaming | Library | `code/backend/data_processing`      |

## Infrastructure

| Capability                                                          | Status         | Location                                |
| :------------------------------------------------------------------ | :------------- | :-------------------------------------- |
| Dockerfiles + Compose (API, Postgres, Redis, Kafka)                 | Infrastructure | `code/backend`, `infrastructure/docker` |
| Kubernetes manifests (base, environments)                           | Infrastructure | `infrastructure/kubernetes`             |
| Terraform modules (compute, database, monitoring, security, config) | Infrastructure | `infrastructure/terraform`              |
| Ansible (inventory, playbooks, roles)                               | Infrastructure | `infrastructure/ansible`                |
| GitHub Actions CI (4 jobs)                                          | Implemented    | `.github/workflows/cicd.yml`            |
