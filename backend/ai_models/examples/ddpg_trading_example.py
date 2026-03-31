"""
## Example script demonstrating the DDPG trading module functionality.
## This script shows how to create a trading environment, train a DDPG agent,
## and backtest the trained agent on market data.
"""

import logging
import os
import sys
from typing import Any, Dict

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
from backend.ai_models.ddpg_trading import BacktestEngine, DDPGAgent, TradingGymEnv


def generate_sample_market_data(
    n_assets: Any = 3, n_days: Any = 252, seed: Any = 42
) -> Any:
    """
    Generate sample market data for testing

    Args:
        n_assets: Number of assets
        n_days: Number of trading days
        seed: Random seed for reproducibility

    Returns:
        DataFrame with asset prices
    """
    np.random.seed(seed)
    prices: Dict[str, Any] = {}
    prices["Asset1"] = np.cumprod(1 + np.random.normal(0.001, 0.01, n_days))
    noise = np.random.normal(0, 0.02, n_days)
    prices["Asset2"] = 100 + np.cumsum(noise - 0.3 * np.sign(np.cumsum(noise)))
    t = np.linspace(0, 4 * np.pi, n_days)
    prices["Asset3"] = (
        100 + 10 * np.sin(t) + np.cumsum(np.random.normal(0, 0.01, n_days))
    )
    for i in range(4, n_assets + 1):
        drift = np.random.uniform(-0.0005, 0.0015)
        vol = np.random.uniform(0.01, 0.02)
        prices[f"Asset{i}"] = np.cumprod(1 + np.random.normal(drift, vol, n_days))
    df = pd.DataFrame(prices)
    return df


def train_and_backtest_ddpg_agent() -> Any:
    """
    Train a DDPG agent and backtest its performance

    Returns:
        Backtest results
    """
    logger.info("Generating sample market data...")
    data = generate_sample_market_data(n_assets=4, n_days=504)
    logger.info("Creating trading environment...")
    env = TradingGymEnv(
        data_stream=data,
        window_size=10,
        transaction_cost=0.001,
        reward_scaling=1.0,
        max_steps=252,
    )
    logger.info("Initializing DDPG agent...")
    agent_config = {
        "actor_lr": 0.0001,
        "critic_lr": 0.001,
        "actor_hidden_dims": (256, 128),
        "critic_hidden_dims": (256, 128),
        "gamma": 0.99,
        "tau": 0.005,
        "batch_size": 64,
        "buffer_capacity": 100000,
        "noise_sigma": 0.2,
        "use_cuda": True,
        "log_interval": 10,
        "save_interval": 50,
        "eval_interval": 50,
        "warmup_steps": 1000,
    }
    agent = DDPGAgent(env, config=agent_config)
    logger.info("Training DDPG agent...")
    logger.info("This may take a few minutes...")
    rewards = agent.train(max_episodes=50, max_steps=252)
    plt.figure(figsize=(10, 6))
    plt.plot(rewards)
    plt.title("Training Rewards")
    plt.xlabel("Episode")
    plt.ylabel("Reward")
    plt.grid(True)
    plt.savefig("training_rewards.png")
    plt.close()
    logger.info("Backtesting trained agent...")
    backtest = BacktestEngine(env, agent)
    results = backtest.run(episodes=1, render=False)
    logger.info("\nBacktest Results:")
    logger.info(f"Total Return: {results['metrics']['total_return']:.2%}")
    logger.info(f"Annual Return: {results['metrics']['annual_return']:.2%}")
    logger.info(f"Sharpe Ratio: {results['metrics']['sharpe_ratio']:.2f}")
    logger.info(f"Volatility: {results['metrics']['volatility']:.2%}")
    logger.info(f"Max Drawdown: {results['metrics']['max_drawdown']:.2%}")
    logger.info("Saving trained agent model...")
    os.makedirs("saved_models", exist_ok=True)
    agent.save_model("saved_models/ddpg_agent")
    return results


if __name__ == "__main__":
    logger.info("Starting DDPG trading module demonstration...")
    results = train_and_backtest_ddpg_agent()
    logger.info(
        "\nDemonstration complete! Results saved to 'backtest_portfolio.png' and 'training_rewards.png'"
    )
    logger.info("Trained model saved to 'saved_models/ddpg_agent'")
