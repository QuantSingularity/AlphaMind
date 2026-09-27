# Example: Reinforcement-Learning Trading (DDPG)

AlphaMind includes a DDPG agent and a trading environment in the research library under `code/ai_models`. This example trains the agent against the environment. It is a research workflow and is independent of the live API.

Requires the ML dependencies (`torch`, `gymnasium`) from `code/backend/requirements.txt`. Run from the `code` directory so `ai_models` is importable.

## Components

- `ai_models.environments.trading_env.TradingEnvironment` - a Gymnasium environment with a continuous action space `Box(-1, 1, (n_assets,))` (target weights) and a dictionary observation space.
- `ai_models.agents.ddpg.DDPGTradingAgent` - a DDPG agent (`Actor` / `Critic` networks) with `select_action` and `train`.
- `TradingEnvConfig` and `DDPGConfig` - configuration dataclasses.

## Minimal training loop

```python
from ai_models.environments.trading_env import TradingEnvironment, TradingEnvConfig
from ai_models.agents.ddpg import DDPGTradingAgent, DDPGConfig

# 1) Build the environment
env = TradingEnvironment(TradingEnvConfig())

# 2) Build the agent against that environment
agent = DDPGTradingAgent(env, DDPGConfig())

# 3) Interact
episodes = 10
for episode in range(episodes):
    obs, _ = env.reset()
    done = False
    total_reward = 0.0
    while not done:
        action = agent.select_action(obs)          # target weights in [-1, 1]
        obs, reward, terminated, truncated, info = env.step(action)
        done = terminated or truncated
        total_reward += reward
    agent.train()                                  # update from collected experience
    print(f"episode {episode}: reward={total_reward:.4f}")
```

The exact configuration fields and training cadence are defined in the agent and environment source. Check `code/ai_models/agents/ddpg.py` and `code/ai_models/environments/trading_env.py` for the parameters available on `DDPGConfig` and `TradingEnvConfig`.

## Notes

- The environment uses synthetic or supplied price series; results are for research and are not a market track record.
- A PPO agent is also available at `ai_models.agents.ppo`.
- Portfolio-level experiments can use `ai_models.environments.portfolio_env`.
