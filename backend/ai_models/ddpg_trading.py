import json
import logging
import os
import random
from collections import deque, namedtuple
from datetime import datetime
from typing import Any, List, Optional

import gym
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from gym import spaces

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

Experience = namedtuple(
    "Experience", ["state", "action", "reward", "next_state", "done"]
)


class ReplayBuffer:
    """Experience replay buffer to store and sample trading experiences"""

    def __init__(self, capacity: Any = 100000) -> None:
        self.buffer = deque(maxlen=capacity)

    def add(
        self, state: Any, action: Any, reward: Any, next_state: Any, done: Any
    ) -> Any:
        """Add experience to buffer"""
        experience = Experience(state, action, reward, next_state, done)
        self.buffer.append(experience)

    def sample(self, batch_size: Any) -> Any:
        """Sample random batch of experiences"""
        experiences = random.sample(self.buffer, k=min(batch_size, len(self.buffer)))
        states = torch.FloatTensor(
            [self._flatten_dict_state(e.state) for e in experiences]
        )
        actions = torch.FloatTensor([e.action for e in experiences])
        rewards = torch.FloatTensor([e.reward for e in experiences]).unsqueeze(-1)
        next_states = torch.FloatTensor(
            [self._flatten_dict_state(e.next_state) for e in experiences]
        )
        dones = torch.FloatTensor([float(e.done) for e in experiences]).unsqueeze(-1)
        return (states, actions, rewards, next_states, dones)

    def _flatten_dict_state(self, state: Any) -> Any:
        """Flatten dictionary state for neural network input"""
        if isinstance(state, dict):
            prices = np.array(state["prices"]).flatten()
            volumes = np.array(state["volumes"]).flatten()
            macro = np.array(state["macro"]).flatten()
            return np.concatenate([prices, volumes, macro])
        return state

    def __len__(self) -> Any:
        return len(self.buffer)


class OUNoise:
    """Ornstein-Uhlenbeck process for exploration noise"""

    def __init__(
        self, size: Any, mu: Any = 0.0, theta: Any = 0.15, sigma: Any = 0.2
    ) -> None:
        self.mu = mu * np.ones(size)
        self.theta = theta
        self.sigma = sigma
        self.size = size
        self.reset()

    def reset(self) -> Any:
        """Reset the internal state"""
        self.state = np.copy(self.mu)

    def sample(self) -> Any:
        """Update internal state and return noise sample"""
        x = self.state
        dx = self.theta * (self.mu - x) + self.sigma * np.random.standard_normal(
            self.size
        )
        self.state = x + dx
        return self.state


class Actor(nn.Module):
    """Actor network for DDPG that determines the action policy"""

    def __init__(
        self,
        state_dim: Any,
        action_dim: Any,
        hidden_dims: Any = (256, 128),
        init_w: Any = 0.003,
    ) -> None:
        super(Actor, self).__init__()
        self.layers = nn.ModuleList()
        prev_dim = state_dim
        for hidden_dim in hidden_dims:
            self.layers.append(nn.Linear(prev_dim, hidden_dim))
            prev_dim = hidden_dim
        self.output_layer = nn.Linear(prev_dim, action_dim)
        self.output_layer.weight.data.uniform_(-init_w, init_w)
        self.output_layer.bias.data.uniform_(-init_w, init_w)

    def forward(self, state: Any) -> Any:
        """Forward pass through the network"""
        x = state
        for layer in self.layers:
            x = F.relu(layer(x))
        return torch.tanh(self.output_layer(x))


class Critic(nn.Module):
    """Critic network for DDPG that estimates Q-values"""

    def __init__(
        self,
        state_dim: Any,
        action_dim: Any,
        hidden_dims: Any = (256, 128),
        init_w: Any = 0.003,
    ) -> None:
        super(Critic, self).__init__()
        self.fc1 = nn.Linear(state_dim, hidden_dims[0])
        self.fc2 = nn.Linear(hidden_dims[0] + action_dim, hidden_dims[1])
        self.output_layer = nn.Linear(hidden_dims[1], 1)
        self.output_layer.weight.data.uniform_(-init_w, init_w)
        self.output_layer.bias.data.uniform_(-init_w, init_w)

    def forward(self, state: Any, action: Any) -> Any:
        """Forward pass through the network"""
        x = F.relu(self.fc1(state))
        x = torch.cat([x, action], dim=1)
        x = F.relu(self.fc2(x))
        return self.output_layer(x)


class DDPGAgent:
    """Deep Deterministic Policy Gradient agent for trading"""

    def __init__(self, env: Any, config: Optional[Any] = None) -> None:
        """Initialize the DDPG agent with environment and optional config"""
        self.env = env
        self.config = self._load_config(config)
        if isinstance(env.observation_space, spaces.Dict):
            sample_obs = env.reset()
            if isinstance(sample_obs, tuple):
                sample_obs = sample_obs[0]
            flat_obs = self._flatten_observation(sample_obs)
            self.state_dim = len(flat_obs)
        else:
            self.state_dim = env.observation_space.shape[0]
        self.action_dim = env.action_space.shape[0]
        self.device = torch.device(
            "cuda" if torch.cuda.is_available() and self.config["use_cuda"] else "cpu"
        )
        logger.info(f"Using device: {self.device}")
        self.actor = Actor(
            self.state_dim,
            self.action_dim,
            hidden_dims=self.config["actor_hidden_dims"],
        ).to(self.device)
        self.critic = Critic(
            self.state_dim,
            self.action_dim,
            hidden_dims=self.config["critic_hidden_dims"],
        ).to(self.device)
        self.actor_target = Actor(
            self.state_dim,
            self.action_dim,
            hidden_dims=self.config["actor_hidden_dims"],
        ).to(self.device)
        self.critic_target = Critic(
            self.state_dim,
            self.action_dim,
            hidden_dims=self.config["critic_hidden_dims"],
        ).to(self.device)
        self._hard_update(self.actor_target, self.actor)
        self._hard_update(self.critic_target, self.critic)
        self.actor_optimizer = optim.Adam(
            self.actor.parameters(), lr=self.config["actor_lr"]
        )
        self.critic_optimizer = optim.Adam(
            self.critic.parameters(), lr=self.config["critic_lr"]
        )
        self.replay_buffer = ReplayBuffer(capacity=self.config["buffer_capacity"])
        self.noise = OUNoise(self.action_dim, sigma=self.config["noise_sigma"])
        self.rewards_history = []
        self.q_values_history = []
        self.actor_losses = []
        self.critic_losses = []
        self.results_dir = os.path.join(
            "results", f"ddpg_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        os.makedirs(self.results_dir, exist_ok=True)
        logger.info(
            f"DDPG Agent initialized with state_dim={self.state_dim}, action_dim={self.action_dim}"
        )

    def _load_config(self, config: Optional[Any] = None) -> Any:
        """Load configuration with defaults"""
        default_config = {
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
            "log_interval": 100,
            "save_interval": 1000,
            "eval_interval": 1000,
            "max_episodes": 10000,
            "max_steps_per_episode": 1000,
            "warmup_steps": 1000,
        }
        if config:
            default_config.update(config)
        return default_config

    def _flatten_observation(self, obs: Any) -> Any:
        """Flatten dictionary observation for neural network input"""
        if isinstance(obs, dict):
            prices = np.array(obs["prices"]).flatten()
            volumes = np.array(obs["volumes"]).flatten()
            macro = np.array(obs["macro"]).flatten()
            return np.concatenate([prices, volumes, macro])
        return obs

    def _hard_update(self, target: Any, source: Any) -> Any:
        """Hard update: target = source"""
        for target_param, param in zip(target.parameters(), source.parameters()):
            target_param.data.copy_(param.data)

    def _soft_update(self, target: Any, source: Any) -> Any:
        """Soft update: target = tau * source + (1 - tau) * target"""
        tau = self.config["tau"]
        for target_param, param in zip(target.parameters(), source.parameters()):
            target_param.data.copy_(target_param.data * (1.0 - tau) + param.data * tau)

    def select_action(self, state: Any, add_noise: Any = True) -> Any:
        """Select action based on current policy with optional exploration noise"""
        flat_state = self._flatten_observation(state)
        state_tensor = torch.FloatTensor(flat_state).unsqueeze(0).to(self.device)
        self.actor.eval()
        with torch.no_grad():
            action = self.actor(state_tensor).cpu().data.numpy().flatten()
        self.actor.train()
        if add_noise:
            action += self.noise.sample()
        return np.clip(action, -1.0, 1.0)

    def update(self) -> Any:
        """Update actor and critic networks using sampled experiences"""
        if len(self.replay_buffer) < self.config["batch_size"]:
            return (0, 0)
        states, actions, rewards, next_states, dones = self.replay_buffer.sample(
            self.config["batch_size"]
        )
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)
        with torch.no_grad():
            next_actions = self.actor_target(next_states)
            next_q_values = self.critic_target(next_states, next_actions)
            target_q = rewards + (1 - dones) * self.config["gamma"] * next_q_values
        current_q = self.critic(states, actions)
        critic_loss = F.mse_loss(current_q, target_q)
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        self.critic_optimizer.step()
        policy_actions = self.actor(states)
        actor_loss = -self.critic(states, policy_actions).mean()
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        self.actor_optimizer.step()
        self._soft_update(self.actor_target, self.actor)
        self._soft_update(self.critic_target, self.critic)
        self.q_values_history.append(current_q.mean().item())
        self.actor_losses.append(actor_loss.item())
        self.critic_losses.append(critic_loss.item())
        return (actor_loss.item(), critic_loss.item())

    def train(
        self, max_episodes: Optional[Any] = None, max_steps: Optional[Any] = None
    ) -> Any:
        """Train the agent on the environment"""
        max_episodes = max_episodes or self.config["max_episodes"]
        max_steps = max_steps or self.config["max_steps_per_episode"]
        logger.info(
            f"Starting training for {max_episodes} episodes, max {max_steps} steps per episode"
        )
        total_steps = 0
        episode_rewards: List[Any] = []
        for episode in range(1, max_episodes + 1):
            state = self.env.reset()
            self.noise.reset()
            episode_reward = 0
            for step in range(1, max_steps + 1):
                if total_steps < self.config["warmup_steps"]:
                    action = self.env.action_space.sample()
                else:
                    action = self.select_action(state, add_noise=True)
                next_state, reward, done, info = self.env.step(action)
                self.replay_buffer.add(state, action, reward, next_state, done)
                if total_steps >= self.config["warmup_steps"]:
                    actor_loss, critic_loss = self.update()
                state = next_state
                episode_reward += reward
                total_steps += 1
                if done or step == max_steps:
                    break
            episode_rewards.append(episode_reward)
            self.rewards_history.append(episode_reward)
            if episode % self.config["log_interval"] == 0:
                avg_reward = np.mean(episode_rewards[-self.config["log_interval"] :])
                logger.info(
                    f"Episode {episode}/{max_episodes} | Avg Reward: {avg_reward:.2f} | Buffer Size: {len(self.replay_buffer)}"
                )
                if len(self.rewards_history) > 0:
                    self._plot_metrics()
            if episode % self.config["save_interval"] == 0:
                self.save_model(os.path.join(self.results_dir, f"model_ep{episode}"))
            if episode % self.config["eval_interval"] == 0:
                eval_reward = self.evaluate(5)
                logger.info(
                    f"Evaluation after episode {episode}: Avg Reward = {eval_reward:.2f}"
                )
        self.save_model(os.path.join(self.results_dir, "model_final"))
        final_eval_reward = self.evaluate(10)
        logger.info(f"Final evaluation: Avg Reward = {final_eval_reward:.2f}")
        self._plot_metrics(final=True)
        return self.rewards_history

    def evaluate(self, num_episodes: Any = 5) -> Any:
        """Evaluate the agent without exploration noise"""
        logger.info(f"Evaluating agent for {num_episodes} episodes")
        eval_rewards: List[Any] = []
        for episode in range(num_episodes):
            state = self.env.reset()
            episode_reward = 0
            done = False
            while not done:
                action = self.select_action(state, add_noise=False)
                next_state, reward, done, _ = self.env.step(action)
                episode_reward += reward
                state = next_state
            eval_rewards.append(episode_reward)
        avg_reward = np.mean(eval_rewards)
        return avg_reward

    def _plot_metrics(self, final: Any = False) -> Any:
        """Plot and save training metrics"""
        plt.figure(figsize=(15, 10))
        plt.subplot(2, 2, 1)
        plt.plot(self.rewards_history)
        plt.title("Episode Rewards")
        plt.xlabel("Episode")
        plt.ylabel("Reward")
        if self.q_values_history:
            plt.subplot(2, 2, 2)
            plt.plot(self.q_values_history)
            plt.title("Average Q-values")
            plt.xlabel("Update Step")
            plt.ylabel("Q-value")
        if self.actor_losses:
            plt.subplot(2, 2, 3)
            plt.plot(self.actor_losses)
            plt.title("Actor Loss")
            plt.xlabel("Update Step")
            plt.ylabel("Loss")
        if self.critic_losses:
            plt.subplot(2, 2, 4)
            plt.plot(self.critic_losses)
            plt.title("Critic Loss")
            plt.xlabel("Update Step")
            plt.ylabel("Loss")
        plt.tight_layout()
        filename = "final_metrics.png" if final else "metrics.png"
        plt.savefig(os.path.join(self.results_dir, filename))
        plt.close()

    def save_model(self, path: Any) -> Any:
        """Save model weights and configuration"""
        os.makedirs(path, exist_ok=True)
        torch.save(self.actor.state_dict(), os.path.join(path, "actor.pth"))
        torch.save(self.critic.state_dict(), os.path.join(path, "critic.pth"))
        torch.save(
            self.actor_target.state_dict(), os.path.join(path, "actor_target.pth")
        )
        torch.save(
            self.critic_target.state_dict(), os.path.join(path, "critic_target.pth")
        )
        with open(os.path.join(path, "config.json"), "w") as f:
            json.dump(self.config, f, indent=4)
        logger.info(f"Model saved to {path}")

    def load_model(self, path: Any) -> Any:
        """Load model weights and configuration"""
        self.actor.load_state_dict(
            torch.load(os.path.join(path, "actor.pth"), map_location=self.device)
        )
        self.critic.load_state_dict(
            torch.load(os.path.join(path, "critic.pth"), map_location=self.device)
        )
        self.actor_target.load_state_dict(
            torch.load(os.path.join(path, "actor_target.pth"), map_location=self.device)
        )
        self.critic_target.load_state_dict(
            torch.load(
                os.path.join(path, "critic_target.pth"), map_location=self.device
            )
        )
        config_path = os.path.join(path, "config.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                loaded_config = json.load(f)
            self.config.update(loaded_config)
        logger.info(f"Model loaded from {path}")


class TradingGymEnv(gym.Env):
    """Custom Gym environment for trading with market data streams"""

    def __init__(
        self,
        data_stream: Any,
        features: Optional[Any] = None,
        window_size: Any = 10,
        transaction_cost: Any = 0.001,
        reward_scaling: Any = 1.0,
        max_steps: Any = 252,
    ) -> None:
        """
        Initialize the trading environment

        Args:
            data_stream: Market data stream (DataFrame or generator)
            features: List of feature columns to use (if None, use all)
            window_size: Number of past observations to include in state
            transaction_cost: Cost of trading as a fraction of trade value
            reward_scaling: Scaling factor for rewards
            max_steps: Maximum number of steps per episode
        """
        super(TradingGymEnv, self).__init__()
        self.data = data_stream
        self.features = features
        self.window_size = window_size
        self.transaction_cost = transaction_cost
        self.reward_scaling = reward_scaling
        self.max_steps = max_steps
        if hasattr(data_stream, "shape"):
            self.num_assets = data_stream.shape[1] if len(data_stream.shape) > 1 else 1
        else:
            self.num_assets = 1
        self.action_space = spaces.Box(
            low=-1, high=1, shape=(self.num_assets,), dtype=np.float32
        )
        self.observation_space = spaces.Dict(
            {
                "prices": spaces.Box(
                    low=-np.inf,
                    high=np.inf,
                    shape=(self.num_assets, window_size),
                    dtype=np.float32,
                ),
                "volumes": spaces.Box(
                    low=0, high=np.inf, shape=(self.num_assets,), dtype=np.float32
                ),
                "macro": spaces.Box(
                    low=-np.inf, high=np.inf, shape=(5,), dtype=np.float32
                ),
            }
        )
        self.current_step = 0
        self.current_weights = np.zeros(self.num_assets)
        self.price_history = np.zeros((self.num_assets, window_size))
        self.returns = np.zeros((100, self.num_assets))
        self.episode_returns = []
        self.portfolio_values = []
        self.actions_history = []

    def reset(self) -> Any:
        """Reset environment to initial state"""
        self.current_step = 0
        self.current_weights = np.zeros(self.num_assets)
        self.price_history = np.zeros((self.num_assets, self.window_size))
        self.returns = np.random.normal(0.0005, 0.01, (100, self.num_assets))
        self.episode_returns = []
        self.portfolio_values = [1.0]
        self.actions_history = []
        return self._get_observation()

    def step(self, action: Any) -> Any:
        """Execute one step in the environment"""
        self.current_step += 1
        new_weights = self._normalize_weights(action)
        cost = self._calculate_transaction_cost(new_weights)
        if self.current_step < len(self.returns):
            step_returns = self.returns[self.current_step]
        else:
            step_returns = np.random.normal(0.0005, 0.01, self.num_assets)
        portfolio_return = np.sum(new_weights * step_returns) - cost
        current_value = self.portfolio_values[-1]
        new_value = current_value * (1 + portfolio_return)
        self.portfolio_values.append(new_value)
        reward = self._calculate_reward(portfolio_return)
        self.current_weights = new_weights
        self.episode_returns.append(portfolio_return)
        self.actions_history.append(new_weights)
        new_prices = self.price_history[:, 1:].copy()
        new_prices = np.column_stack([new_prices, step_returns + 1])
        self.price_history = new_prices
        done = self.current_step >= self.max_steps
        observation = self._get_observation()
        info = {
            "portfolio_value": new_value,
            "portfolio_return": portfolio_return,
            "transaction_cost": cost,
            "weights": new_weights,
        }
        return (observation, reward, done, info)

    def _normalize_weights(self, action: Any) -> Any:
        """Normalize actions to valid portfolio weights"""
        weights = np.tanh(action)
        if np.sum(np.abs(weights)) > 0:
            weights = weights / np.sum(np.abs(weights))
        return weights

    def _calculate_transaction_cost(self, new_weights: Any) -> Any:
        """Calculate transaction costs from rebalancing"""
        turnover = np.sum(np.abs(new_weights - self.current_weights))
        cost = turnover * self.transaction_cost
        return cost

    def _calculate_reward(self, portfolio_return: Any) -> Any:
        """Calculate reward based on portfolio performance"""
        reward = portfolio_return * self.reward_scaling
        if len(self.episode_returns) > 10:
            returns_array = np.array(self.episode_returns)
            sharpe = (np.mean(returns_array) - 0.0001) / (np.std(returns_array) + 1e-06)
            reward = sharpe * self.reward_scaling
        return reward

    def _get_observation(self) -> Any:
        """Get current market observation"""
        return {
            "prices": self.price_history,
            "volumes": np.abs(np.random.normal(1000, 500, (self.num_assets,))),
            "macro": np.random.normal(0, 1, (5,)),
        }

    def render(self, mode: Any = "human") -> Any:
        """Render the environment"""
        if mode == "human":
            logger.info(f"Step: {self.current_step}")
            logger.info(f"Portfolio Value: {self.portfolio_values[-1]:.4f}")
            logger.info(f"Current Weights: {self.current_weights}")
            logger.info(
                f"Current Return: {(self.episode_returns[-1] if self.episode_returns else 0):.4f}"
            )
            logger.info("-" * 50)
        return None


class BacktestEngine:
    """Backtesting engine for evaluating trading strategies"""

    def __init__(self, env: Any, agent: Any, data: Optional[Any] = None) -> None:
        """
        Initialize backtesting engine

        Args:
            env: Trading environment
            agent: Trading agent (e.g., DDPGAgent)
            data: Optional data to use for backtesting (overrides env data)
        """
        self.env = env
        self.agent = agent
        if data is not None:
            self.env.data = data
        self.portfolio_values = []
        self.returns = []
        self.sharpe_ratio = None
        self.max_drawdown = None
        self.total_return = None
        self.annual_return = None
        self.volatility = None
        self.logger = logging.getLogger("BacktestEngine")

    def _calculate_sharpe_ratio(
        self, returns: Any, risk_free_rate: Any = 0.0001
    ) -> Any:
        """Calculate Sharpe Ratio"""
        if len(returns) < 2:
            return 0.0
        returns_array = np.array(returns)
        annualized_return = np.mean(returns_array) * 252
        annualized_volatility = np.std(returns_array) * np.sqrt(252)
        annualized_risk_free_rate = risk_free_rate * 252
        if annualized_volatility == 0:
            return 0.0
        sharpe = (annualized_return - annualized_risk_free_rate) / annualized_volatility
        return sharpe

    def _calculate_max_drawdown(self, portfolio_values: Any) -> Any:
        """Calculate Maximum Drawdown"""
        if not portfolio_values:
            return 0.0
        portfolio_values = np.array(portfolio_values)
        cumulative_max = np.maximum.accumulate(portfolio_values)
        drawdown = (cumulative_max - portfolio_values) / cumulative_max
        max_drawdown = np.max(drawdown)
        return max_drawdown

    def run(self, episodes: Any = 1, render: Any = False) -> Any:
        """Run backtest for specified number of episodes"""
        self.logger.info(f"Starting backtest for {episodes} episodes")
        all_portfolio_values: List[Any] = []
        all_returns = []
        all_actions: List[Any] = []
        for episode in range(1, episodes + 1):
            state = self.env.reset()
            done = False
            episode_values = [1.0]
            episode_returns: List[Any] = []
            episode_actions = []
            while not done:
                action = self.agent.select_action(state, add_noise=False)
                next_state, reward, done, info = self.env.step(action)
                episode_values.append(info["portfolio_value"])
                episode_returns.append(info["portfolio_return"])
                episode_actions.append(info["weights"])
                if render:
                    self.env.render()
                state = next_state
            all_portfolio_values.append(episode_values)
            all_returns.append(episode_returns)
            all_actions.append(episode_actions)
            final_value = episode_values[-1]
            episode_sharpe = self._calculate_sharpe_ratio(episode_returns)
            self.logger.info(
                f"Episode {episode}/{episodes} | Final Value: ${final_value:.2f} | Sharpe: {episode_sharpe:.2f}"
            )
        self._calculate_metrics(all_portfolio_values, all_returns, all_actions)
        self.logger.info(
            f"Backtest completed | Total Return: {self.total_return:.2%} | Sharpe: {self.sharpe_ratio:.2f} | Max Drawdown: {self.max_drawdown:.2%}"
        )
        self._plot_results(all_portfolio_values, all_returns, all_actions)
        return {
            "portfolio_values": all_portfolio_values,
            "returns": all_returns,
            "actions": all_actions,
            "metrics": {
                "total_return": self.total_return,
                "annual_return": self.annual_return,
                "sharpe_ratio": self.sharpe_ratio,
                "max_drawdown": self.max_drawdown,
                "volatility": self.volatility,
            },
        }

    def _calculate_metrics(
        self, portfolio_values: Any, returns: Any, actions: Any
    ) -> Any:
        """Calculate performance metrics"""
        longest_idx = np.argmax([len(pv) for pv in portfolio_values])
        self.portfolio_values = portfolio_values[longest_idx]
        self.returns = returns[longest_idx]
        self.total_return = self.portfolio_values[-1] / self.portfolio_values[0] - 1
        days = len(self.returns)
        if days > 0:
            self.annual_return = (1 + self.total_return) ** (252 / days) - 1
        else:
            self.annual_return = 0.0
        self.sharpe_ratio = self._calculate_sharpe_ratio(self.returns)
        self.max_drawdown = self._calculate_max_drawdown(self.portfolio_values)
        if days > 1:
            self.volatility = np.std(self.returns) * np.sqrt(252)
        else:
            self.volatility = 0.0

    def _plot_results(
        self, all_portfolio_values: Any, all_returns: Any, all_actions: Any
    ) -> Any:
        """Plot and save backtest results"""
        plt.figure(figsize=(15, 5))
        plt.plot(self.portfolio_values, label="Portfolio Value")
        plt.title("Portfolio Value Over Time")
        plt.xlabel("Step")
        plt.ylabel("Value (Starting at 1.0)")
        plt.legend()
        plt.savefig(os.path.join(self.agent.results_dir, "backtest_portfolio.png"))
        plt.close()
        self.logger.info(
            f"Backtest plot saved to {os.path.join(self.agent.results_dir, 'backtest_portfolio.png')}"
        )
