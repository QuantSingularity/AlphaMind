"""
Backtest execution engine.

Bridges the API layer to real simulation logic backed by ai_models and
backend.market_data.backtesting.BacktestEngine. Two live endpoints use this:

    POST /api/v1/backtest/            (app/api/v1/routers/backtest.py)
        The endpoint the web/mobile frontends actually call. Previously
        this returned entirely canned numbers from a hardcoded per-strategy
        lookup table - no simulation of any kind ran. Uses run_backtest_detailed.

    POST /api/v1/strategies/backtest  (app/api/v1/routers/strategies.py)
        A separate, DB-backed async "submit and poll" flow. Previously
        StrategyService.create_backtest only ever wrote a "pending" row -
        its own docstring said a background worker "should pick this
        up... (not yet wired to a live execution engine)", but no such
        worker existed. Uses the simpler run_backtest.

Neither endpoint, nor anything else in the backend, imported ai_models
before this module existed - grep the codebase for "from ai_models" and
this file is the only hit outside ai_models/ itself.

Dispatches by Strategy.strategy_type (see db/models/strategy.py):

    rl_agent        Trains an ai_models.agents RL agent (DDPG by default,
                     PPO if requested and stable-baselines3 is installed)
                     against ai_models.environments.TradingEnvironment,
                     then evaluates it to build an equity curve.
    ml_alpha         Trains ai_models.forecasting.AdvancedTimeSeriesForecaster
                     on a synthetic price series and trades its predicted-
                     return signal through backend.market_data.backtesting.
    momentum         Simple N-day-momentum rule, via the same BacktestEngine.
    mean_reversion   Simple z-score mean-reversion rule, ditto.

All synthetic-data paths are seeded by (symbol, start_date, end_date) so a
backtest is reproducible given the same inputs.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, TypedDict

import numpy as np
import pandas as pd
from app.services.synthetic_market_data import generate_ohlcv
from backend.market_data.backtesting import (
    BacktestEngine,
    BacktestOrder,
    OrderSide,
    Portfolio,
)

logger = logging.getLogger(__name__)

_TRADING_DAYS_PER_YEAR = 252


class Trajectory(TypedDict):
    """A day-by-day equity path, the common currency every strategy
    handler below produces and every metric is derived from."""

    dates: List[str]  # length N+1; dates[0] is the start date
    equity: List[float]  # length N+1; equity[0] == initial_capital
    benchmark: List[float]  # length N+1; buy-and-hold reference, same scale
    trade_flags: List[bool]  # length N+1; True on days a trade executed


def _business_dates(start_date: str, n: int) -> List[str]:
    return [d.strftime("%Y-%m-%d") for d in pd.bdate_range(start=start_date, periods=n)]


# ---------------------------------------------------------------------------
# Strategy handlers - each returns a Trajectory
# ---------------------------------------------------------------------------


def _run_rl_agent_trajectory(
    parameters: Dict[str, Any], initial_capital: float, start_date: str
) -> Trajectory:
    """Train an ai_models RL agent and evaluate it for one episode."""
    from ai_models.config import DDPGConfig, TradingEnvConfig
    from ai_models.environments import TradingEnvironment

    algorithm = str(parameters.get("algorithm", "ddpg")).lower()
    n_assets = int(parameters.get("n_assets", 5))
    # Defaults are deliberately small - this runs synchronously inside an
    # HTTP request (see app/api/v1/routers/backtest.py); a strategy that
    # wants a more thorough (and slower) training run can override these.
    max_steps = int(parameters.get("max_steps", 60))
    episodes = int(parameters.get("episodes", 10))
    transaction_cost = float(parameters.get("transaction_cost", 0.001))
    seed = parameters.get("seed")

    env_config = TradingEnvConfig(
        n_assets=n_assets, max_steps=max_steps, transaction_cost=transaction_cost
    )
    env = TradingEnvironment(env_config)

    from ai_models.agents import DDPGTradingAgent

    agent = None
    if algorithm == "ppo":
        try:
            from ai_models.agents import PPOAgent

            agent = PPOAgent(env)
            agent.learn(total_timesteps=episodes * max_steps)
        except ImportError:
            logger.warning(
                "PPO requested but stable-baselines3 is not installed; "
                "falling back to DDPG"
            )
            algorithm = "ddpg"

    if agent is None:
        agent_config = DDPGConfig(use_cuda=False)
        agent = DDPGTradingAgent(env, config=agent_config)
        agent.train(num_episodes=episodes, max_steps=max_steps)

    # One clean (noise-free) evaluation episode drives the reported equity curve.
    state, _ = env.reset(seed=seed if seed is not None else 0)
    equity = [initial_capital]
    trade_flags = [False]
    prev_weights = env.current_weights.copy()
    t = 0
    done = False
    while not done:
        action = agent.select_action(state, add_noise=False)
        state, reward, done, truncated, _ = env.step(action)
        equity.append(equity[-1] * float(np.exp(reward)))
        trade_flags.append(
            not np.allclose(env.current_weights, prev_weights, atol=1e-3)
        )
        prev_weights = env.current_weights.copy()
        t += 1
        done = done or truncated

    # Equal-weight buy-and-hold of the same simulated assets as a benchmark.
    asset_prices = env.prices[: t + 1]  # shape (t+1, n_assets)
    asset_returns = asset_prices / asset_prices[0]
    benchmark = (initial_capital * asset_returns.mean(axis=1)).tolist()

    return Trajectory(
        dates=_business_dates(start_date, len(equity)),
        equity=equity,
        benchmark=benchmark,
        trade_flags=trade_flags,
    )


def _run_ml_alpha_trajectory(
    parameters: Dict[str, Any],
    symbol: str,
    start_date: str,
    end_date: str,
    initial_capital: float,
) -> Trajectory:
    """Train an ai_models forecaster and trade its directional signal."""
    from ai_models.config import TransformerConfig
    from ai_models.forecasting import AdvancedTimeSeriesForecaster

    prices = generate_ohlcv(symbol, start_date, end_date, seed=parameters.get("seed"))
    closes = prices["close"].to_numpy(dtype=np.float32)

    input_len = int(parameters.get("input_seq_length", 20))
    output_len = 1  # next-step direction is all we need for a trade signal
    n_features = 1
    min_required = input_len + output_len + 5
    if len(closes) < min_required:
        raise ValueError(
            f"Date range too short for ml_alpha: need at least {min_required} "
            f"trading days, got {len(closes)}"
        )

    returns = np.diff(closes) / closes[:-1]
    X, y = [], []
    for i in range(len(returns) - input_len - output_len + 1):
        X.append(returns[i : i + input_len])
        y.append(returns[i + input_len : i + input_len + output_len])
    X = np.asarray(X, dtype=np.float32).reshape(-1, input_len, n_features)
    y = np.asarray(y, dtype=np.float32)

    split = max(1, int(len(X) * 0.8))
    x_train, y_train = X[:split], y[:split]
    x_test = X[split:]
    if len(x_test) == 0:
        raise ValueError(
            "Date range too short for ml_alpha: no out-of-sample days left "
            "after the 80/20 train/test split"
        )

    config = TransformerConfig(
        input_seq_length=input_len,
        output_seq_length=output_len,
        num_layers=int(parameters.get("num_layers", 2)),
        d_model=int(parameters.get("d_model", 32)),
        num_heads=int(parameters.get("num_heads", 2)),
        dff=int(parameters.get("dff", 64)),
    )
    forecaster = AdvancedTimeSeriesForecaster(config)
    epochs = int(parameters.get("epochs", 5))
    forecaster.train(x_train, y_train, epochs=epochs, batch_size=16)

    # Only trade on the held-out test window - predicting on x_train too
    # would let the strategy "trade" on days the model already memorised.
    predicted_returns = forecaster.predict(x_test).reshape(-1)
    threshold = float(parameters.get("signal_threshold", 0.0))
    signal_dates = prices.index[
        input_len + split : input_len + split + len(predicted_returns)
    ]
    signals = {
        d: ("buy" if r > threshold else "sell" if r < -threshold else "flat")
        for d, r in zip(signal_dates, predicted_returns)
    }

    def strategy_fn(
        bar: Dict[str, Any], portfolio: Portfolio, engine: BacktestEngine
    ) -> None:
        if symbol not in bar:
            return
        signal = signals.get(engine.current_time, "flat")
        position = portfolio.get_position(symbol)
        price = float(bar[symbol]["close"])
        if signal == "buy" and position.quantity <= 0:
            qty = (portfolio.cash * 0.95) / price
            if qty > 0:
                engine.place_order(BacktestOrder(symbol, OrderSide.BUY, qty))
        elif signal == "sell" and position.quantity > 0:
            engine.place_order(BacktestOrder(symbol, OrderSide.SELL, position.quantity))

    engine = BacktestEngine(
        {symbol: prices},
        initial_cash=initial_capital,
        start_date=str(signal_dates[0].date()) if len(signal_dates) else start_date,
        end_date=end_date,
    )
    engine.run(strategy_fn)
    return _trajectory_from_engine(engine, prices, symbol, initial_capital)


def _run_rule_based_trajectory(
    strategy_type: str,
    parameters: Dict[str, Any],
    symbol: str,
    start_date: str,
    end_date: str,
    initial_capital: float,
) -> Trajectory:
    """Simple, real momentum / mean-reversion rules (no ai_models needed)."""
    prices = generate_ohlcv(symbol, start_date, end_date, seed=parameters.get("seed"))
    lookback = int(parameters.get("lookback", 20))
    closes = prices["close"]

    if strategy_type == "momentum":
        threshold = float(parameters.get("threshold", 0.02))
        momentum = closes.pct_change(lookback)

        def signal_for(date: Any) -> str:
            m = momentum.get(date)
            if m is None or np.isnan(m):
                return "flat"
            return "buy" if m > threshold else "sell" if m < -threshold else "flat"

    else:  # mean_reversion
        z_threshold = float(parameters.get("z_threshold", 1.0))
        rolling_mean = closes.rolling(lookback).mean()
        rolling_std = closes.rolling(lookback).std()
        zscore = (closes - rolling_mean) / rolling_std.replace(0, np.nan)

        def signal_for(date: Any) -> str:
            z = zscore.get(date)
            if z is None or np.isnan(z):
                return "flat"
            # Price far below its rolling mean -> expect reversion upward.
            return "buy" if z < -z_threshold else "sell" if z > z_threshold else "flat"

    def strategy_fn(
        bar: Dict[str, Any], portfolio: Portfolio, engine: BacktestEngine
    ) -> None:
        if symbol not in bar:
            return
        signal = signal_for(engine.current_time)
        position = portfolio.get_position(symbol)
        price = float(bar[symbol]["close"])
        if signal == "buy" and position.quantity <= 0:
            qty = (portfolio.cash * 0.95) / price
            if qty > 0:
                engine.place_order(BacktestOrder(symbol, OrderSide.BUY, qty))
        elif signal == "sell" and position.quantity > 0:
            engine.place_order(BacktestOrder(symbol, OrderSide.SELL, position.quantity))

    engine = BacktestEngine(
        {symbol: prices},
        initial_cash=initial_capital,
        start_date=start_date,
        end_date=end_date,
    )
    engine.run(strategy_fn)
    return _trajectory_from_engine(engine, prices, symbol, initial_capital)


def _trajectory_from_engine(
    engine: BacktestEngine, prices: pd.DataFrame, symbol: str, initial_capital: float
) -> Trajectory:
    """Convert BacktestEngine's own equity_curve (already correctly
    date-stamped - see backend/market_data/backtesting.py:Portfolio.update)
    into a Trajectory, adding a buy-and-hold benchmark from the same
    price series."""
    points = engine.performance["equity_curve"]
    if not points:
        return Trajectory(
            dates=[str(prices.index[0].date())] if len(prices) else [],
            equity=[initial_capital],
            benchmark=[initial_capital],
            trade_flags=[False],
        )
    dates = [str(p["time"].date()) for p in points]
    equity = [float(p["equity"]) for p in points]

    aligned_close = prices["close"].reindex(pd.to_datetime(dates), method="ffill")
    first_close = float(aligned_close.iloc[0]) or 1.0
    benchmark = (initial_capital * (aligned_close / first_close)).tolist()

    equity_arr = np.array(equity)
    trade_flags = [False] + list(np.abs(np.diff(equity_arr)) > 1e-9)
    return Trajectory(
        dates=dates, equity=equity, benchmark=benchmark, trade_flags=trade_flags
    )


# ---------------------------------------------------------------------------
# Shared metric computation
# ---------------------------------------------------------------------------


def _trajectory_for(
    strategy_type: str,
    parameters: Dict[str, Any],
    start_date: str,
    end_date: str,
    initial_capital: float,
) -> Trajectory:
    symbol = str(parameters.get("symbol", "SIM"))
    if strategy_type == "rl_agent":
        return _run_rl_agent_trajectory(parameters, initial_capital, start_date)
    if strategy_type == "ml_alpha":
        return _run_ml_alpha_trajectory(
            parameters, symbol, start_date, end_date, initial_capital
        )
    if strategy_type in ("momentum", "mean_reversion"):
        return _run_rule_based_trajectory(
            strategy_type, parameters, symbol, start_date, end_date, initial_capital
        )
    raise ValueError(f"Unsupported strategy_type: {strategy_type}")


def _compute_simple_stats(
    trajectory: Trajectory, initial_capital: float
) -> Dict[str, Any]:
    """The 6-field subset app.services.strategy_service.complete_backtest
    stores (used by the async /api/v1/strategies/backtest flow)."""
    equity = np.array(trajectory["equity"])
    trade_flags = np.array(trajectory["trade_flags"])
    total_return = float(equity[-1] / initial_capital - 1) if initial_capital else 0.0
    step_returns = np.diff(equity) / np.where(equity[:-1] == 0, 1, equity[:-1])
    volatility = (
        float(np.std(step_returns) * np.sqrt(_TRADING_DAYS_PER_YEAR))
        if len(step_returns)
        else 0.0
    )
    mean_return = float(np.mean(step_returns)) if len(step_returns) else 0.0
    sharpe_ratio = (
        float((mean_return * _TRADING_DAYS_PER_YEAR) / volatility)
        if volatility > 0
        else 0.0
    )
    running_max = np.maximum.accumulate(equity)
    drawdowns = np.where(running_max > 0, (equity - running_max) / running_max, 0.0)
    max_drawdown = float(abs(drawdowns.min())) if len(drawdowns) else 0.0

    total_trades = int(trade_flags.sum())
    if total_trades > 0 and len(step_returns):
        trade_returns = step_returns[trade_flags[1:]]
        win_rate = float(np.mean(trade_returns > 0)) if len(trade_returns) else 0.0
    else:
        win_rate = 0.0

    return {
        "final_capital": float(equity[-1]),
        "total_return": total_return,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "total_trades": total_trades,
        "win_rate": win_rate,
    }


def _compute_full_stats(
    trajectory: Trajectory, initial_capital: float
) -> Dict[str, Any]:
    """The full field set app/api/v1/routers/backtest.py's BacktestResult
    needs (used by the live, frontend-facing /api/v1/backtest endpoint)."""
    dates = trajectory["dates"]
    equity = np.array(trajectory["equity"])
    benchmark = np.array(trajectory["benchmark"])
    trade_flags = np.array(trajectory["trade_flags"])

    total_return = float(equity[-1] / initial_capital - 1) if initial_capital else 0.0
    n_days = max(len(equity) - 1, 1)
    annualised_return = (
        float((1 + total_return) ** (_TRADING_DAYS_PER_YEAR / n_days) - 1)
        if total_return > -1
        else -1.0
    )

    step_returns = np.diff(equity) / np.where(equity[:-1] == 0, 1, equity[:-1])
    volatility = (
        float(np.std(step_returns) * np.sqrt(_TRADING_DAYS_PER_YEAR))
        if len(step_returns)
        else 0.0
    )
    mean_return = float(np.mean(step_returns)) if len(step_returns) else 0.0
    sharpe_ratio = (
        float((mean_return * _TRADING_DAYS_PER_YEAR) / volatility)
        if volatility > 0
        else 0.0
    )

    downside_returns = step_returns[step_returns < 0]
    downside_vol = (
        float(np.std(downside_returns) * np.sqrt(_TRADING_DAYS_PER_YEAR))
        if len(downside_returns)
        else 0.0
    )
    sortino_ratio = (
        float((mean_return * _TRADING_DAYS_PER_YEAR) / downside_vol)
        if downside_vol > 0
        else 0.0
    )

    running_max = np.maximum.accumulate(equity)
    drawdowns = np.where(running_max > 0, (equity - running_max) / running_max, 0.0)
    max_drawdown = float(abs(drawdowns.min())) if len(drawdowns) else 0.0
    calmar_ratio = float(annualised_return / max_drawdown) if max_drawdown > 0 else 0.0

    max_drawdown_duration = 0
    current_run = 0
    for d in drawdowns:
        if d < 0:
            current_run += 1
            max_drawdown_duration = max(max_drawdown_duration, current_run)
        else:
            current_run = 0

    total_trades = int(trade_flags.sum())
    wins = step_returns[step_returns > 0]
    losses = step_returns[step_returns < 0]
    win_rate = float(len(wins) / len(step_returns)) if len(step_returns) else 0.0
    gross_profit = float(wins.sum() * initial_capital)
    gross_loss = float(abs(losses.sum()) * initial_capital)
    profit_factor = (
        float(gross_profit / gross_loss)
        if gross_loss > 0
        else (0.0 if not len(wins) else 10.0)
    )
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(losses.mean()) if len(losses) else 0.0

    best_month = 0.0
    worst_month = 0.0
    if len(dates) > 1:
        equity_series = pd.Series(equity[1:], index=pd.to_datetime(dates[1:]))
        monthly = equity_series.resample("ME").last().pct_change().dropna()
        if len(monthly):
            best_month = float(monthly.max())
            worst_month = float(monthly.min())

    equity_curve = [
        {
            "date": dates[i],
            "equity": round(float(equity[i]), 2),
            "benchmark": round(float(benchmark[i]), 2),
            "drawdown": round(float(drawdowns[i]) * 100, 3),
        }
        for i in range(len(dates))
    ]

    return {
        "finalCapital": float(equity[-1]),
        "totalReturn": total_return,
        "annualisedReturn": annualised_return,
        "sharpeRatio": sharpe_ratio,
        "sortinoRatio": sortino_ratio,
        "calmarRatio": calmar_ratio,
        "maxDrawdown": max_drawdown,
        "maxDrawdownDuration": max_drawdown_duration,
        "winRate": win_rate,
        "profitFactor": profit_factor,
        "totalTrades": total_trades,
        "avgWin": avg_win,
        "avgLoss": avg_loss,
        "bestMonth": best_month,
        "worstMonth": worst_month,
        "equityCurve": equity_curve,
    }


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def run_backtest(
    strategy_type: str,
    parameters: Dict[str, Any],
    start_date: str,
    end_date: str,
    initial_capital: float,
) -> Dict[str, Any]:
    """Execute a backtest and return the 6-field result
    StrategyService.complete_backtest expects: final_capital, total_return,
    sharpe_ratio, max_drawdown, total_trades, win_rate. Used by the async
    /api/v1/strategies/backtest flow.
    """
    trajectory = _trajectory_for(
        strategy_type, parameters, start_date, end_date, initial_capital
    )
    stats = _compute_simple_stats(trajectory, initial_capital)
    if strategy_type == "rl_agent":
        stats["algorithm"] = str(parameters.get("algorithm", "ddpg")).lower()
        if stats["algorithm"] == "ppo":
            try:
                import stable_baselines3  # noqa: F401
            except ImportError:
                stats["algorithm"] = "ddpg"
    return stats


def run_backtest_detailed(
    strategy_type: str,
    parameters: Dict[str, Any],
    start_date: str,
    end_date: str,
    initial_capital: float,
) -> Dict[str, Any]:
    """Execute a backtest and return the full field set (including the
    equity curve) app/api/v1/routers/backtest.py's BacktestResult needs.
    Used by the live, frontend-facing /api/v1/backtest endpoint.
    """
    trajectory = _trajectory_for(
        strategy_type, parameters, start_date, end_date, initial_capital
    )
    return _compute_full_stats(trajectory, initial_capital)
