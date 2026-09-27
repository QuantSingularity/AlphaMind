# Backtests

This document explains how backtests work in AlphaMind and how to read the output. It deliberately does not publish a performance track record, because the default data is synthetic (seeded and reproducible, not fetched from a real market-data provider); any numbers you see are illustrative of the mechanics, not evidence of real-world returns.

## Running a backtest

Via the API:

```bash
curl -s -X POST http://localhost:8000/api/v1/backtest/ \
  -H 'Content-Type: application/json' \
  -d '{
    "strategyId": "<id from /api/v1/strategies/>",
    "startDate": "2023-01-01",
    "endDate": "2024-01-01",
    "initialCapital": 100000
  }'
```

Via the UI: open Backtest, pick a strategy, set the date range and initial capital, and run.

This runs synchronously: for `momentum`/`mean_reversion` strategies it typically returns in well under a second; for `rl_agent`/`ml_alpha` strategies (see below) it trains a small model first, which usually takes a few seconds. For a fire-and-forget alternative that returns immediately with `status: "pending"` and lets you poll for the result instead, use `POST /api/v1/strategies/backtest` (see [API.md](API.md)).

## What actually runs, by strategy type

A strategy's `type` (`momentum` | `mean_reversion` | `ml_alpha` | `rl_agent`) decides what `app/services/backtest_runner.py` does:

| Type             | What runs                                                                                                                                                                                                     |
| :--------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `rl_agent`       | Trains an `ai_models.agents` RL agent (DDPG by default, PPO if requested and `stable-baselines3` is installed) against `ai_models.environments.TradingEnvironment`, then evaluates it over one clean episode. |
| `ml_alpha`       | Trains `ai_models.forecasting.AdvancedTimeSeriesForecaster` on 80% of the window and trades its predicted-return signal over the held-out 20%, via `backend/market_data/backtesting.py`'s `BacktestEngine`.   |
| `momentum`       | An N-day momentum rule (buy/sell when the trailing return crosses a threshold), via the same `BacktestEngine`.                                                                                                |
| `mean_reversion` | A rolling z-score rule (buy/sell when price deviates from its rolling mean), via the same `BacktestEngine`.                                                                                                   |

All four run against a synthetic, seeded GBM price series (`app/services/synthetic_market_data.py`) rather than a real market-data connector, so a backtest is fully reproducible given the same strategy parameters and date range - none of the connectors in `backend/market_data/connectors/` work without real API credentials, and this codebase has no other built-in historical data source.

## Reading the result

The response is a flat object:

| Field                    | Meaning                                                                                                                                    |
| :----------------------- | :----------------------------------------------------------------------------------------------------------------------------------------- |
| `id`                     | Backtest run ID.                                                                                                                           |
| `strategyId`             | The strategy that was run.                                                                                                                 |
| `startDate`/`endDate`    | The requested date range.                                                                                                                  |
| `initialCapital`         | Starting capital.                                                                                                                          |
| `finalCapital`           | Ending capital.                                                                                                                            |
| `totalReturn`            | Total return over the period.                                                                                                              |
| `annualisedReturn`       | Return scaled to a yearly rate.                                                                                                            |
| `sharpeRatio`            | Excess return per unit of total volatility.                                                                                                |
| `sortinoRatio`           | Excess return per unit of downside volatility.                                                                                             |
| `calmarRatio`            | Annualised return divided by max drawdown.                                                                                                 |
| `maxDrawdown`            | Largest peak-to-trough decline (fraction).                                                                                                 |
| `maxDrawdownDuration`    | Longest run of consecutive days spent below a prior equity peak.                                                                           |
| `winRate`                | Share of winning periods (fraction).                                                                                                       |
| `profitFactor`           | Gross profit divided by gross loss.                                                                                                        |
| `totalTrades`            | Number of days a position changed.                                                                                                         |
| `avgWin`/`avgLoss`       | Average daily return on winning/losing days.                                                                                               |
| `bestMonth`/`worstMonth` | Best/worst calendar-month return.                                                                                                          |
| `equityCurve`            | `[{date, equity, benchmark, drawdown}]` - `benchmark` is an equal-weight buy-and-hold of the same simulated instrument(s), for comparison. |

## Interpreting metrics responsibly

- A backtest is a hypothesis about the past, not a promise about the future.
- The default series are synthetic and deterministic, so results are reproducible but not market-realistic.
- `rl_agent`/`ml_alpha` backtests train a genuinely new model on every run (unless you fix the `seed` parameter), so results will vary run to run - the point is to exercise the real training/evaluation pipeline, not to produce a tuned, production-grade model in a few seconds.
- To run against real history, wire up one of the connectors in `backend/market_data/connectors/` with real API credentials and swap `synthetic_market_data.generate_ohlcv` for it in `backtest_runner.py`.

## Where the logic lives

- `app/api/v1/routers/backtest.py` - the live `POST /api/v1/backtest/` endpoint the web/mobile frontends call.
- `app/api/v1/routers/strategies.py` + `app/services/strategy_service.py` - the async "submit and poll" alternative.
- `app/services/backtest_runner.py` - dispatches by strategy type and computes every metric above from a shared equity-curve trajectory.
- `app/services/synthetic_market_data.py` - the synthetic price generator used by `momentum`/`mean_reversion`/`ml_alpha`.
- `backend/market_data/backtesting.py` - the underlying order/portfolio simulator (`BacktestEngine`) that `momentum`/`mean_reversion`/`ml_alpha` strategies run through.
- `code/ai_models/agents`, `code/ai_models/environments`, `code/ai_models/forecasting` - the actual model code `rl_agent`/`ml_alpha` strategies train and evaluate.
