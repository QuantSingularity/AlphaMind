import json
import logging
import os
import random
from collections import deque, namedtuple
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

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

StateDict = Dict[str, np.ndarray]
State = Union[StateDict, np.ndarray]


class ReplayBuffer:
    """Experience replay buffer to store and sample trading experiences"""

    def __init__(self, capacity: int = 100000) -> None:
        self.buffer: deque = deque(maxlen=capacity)

    def add(
        self,
        state: State,
        action: np.ndarray,
        reward: float,
        next_state: State,
        done: bool,
    ) -> None:
        """Add experience to buffer"""
        experience = Experience(state, action, reward, next_state, done)
        self.buffer.append(experience)

    def sample(self, batch_size: int) -> Tuple[
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
        torch.Tensor,
    ]:
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

    def _flatten_dict_state(self, state: State) -> np.ndarray:
        """Flatten dictionary state for neural network input"""
        if isinstance(state, dict):
            prices = np.array(state["prices"]).flatten()
            volumes = np.array(state["volumes"]).flatten()
            macro = np.array(state["macro"]).flatten()
            return np.concatenate([prices, volumes, macro])
        return np.asarray(state)

    def __len__(self) -> int:
        return len(self.buffer)


class OUNoise:
    """Ornstein-Uhlenbeck process for exploration noise"""

    def __init__(
        self,
        size: int,
        mu: float = 0.0,
        theta: float = 0.15,
        sigma: float = 0.2,
    ) -> None:
        self.mu = mu * np.ones(size)
        self.theta = theta
        self.sigma = sigma
        self.size = size
        self.state: np.ndarray = np.zeros(size)
        self.reset()

    def reset(self) -> None:
        """Reset noise to mean"""
        self.state = np.copy(self.mu)

    def sample(self) -> np.ndarray:
        """Sample noise"""
        dx = self.theta * (self.mu - self.state) + self.sigma * np.random.randn(
            self.size
        )
        self.state += dx
        return self.state


class Actor(nn.Module):
    """Actor network that maps states to actions"""

    def __init__(
        self, state_dim: int, action_dim: int, hidden_dims: List[int] = [256, 256]
    ) -> None:
        super().__init__()
        layers: List[nn.Module] = []
        in_dim = state_dim
        for h in hidden_dims:
            layers += [nn.Linear(in_dim, h), nn.ReLU()]
            in_dim = h
        layers.append(nn.Linear(in_dim, action_dim))
        layers.append(nn.Tanh())
        self.net = nn.Sequential(*layers)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        return self.net(state)


class Critic(nn.Module):
    """Critic network that estimates Q-values"""

    def __init__(
        self,
        state_dim: int,
        action_dim: int,
        hidden_dims: List[int] = [256, 256],
    ) -> None:
        super().__init__()
        layers: List[nn.Module] = []
        in_dim = state_dim + action_dim
        for h in hidden_dims:
            layers += [nn.Linear(in_dim, h), nn.ReLU()]
            in_dim = h
        layers.append(nn.Linear(in_dim, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, state: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        return self.net(torch.cat([state, action], dim=-1))


class DDPGTradingAgent:
    """
    Deep Deterministic Policy Gradient (DDPG) agent for continuous-action trading.
    Implements actor-critic architecture with experience replay and target networks.
    """

    def __init__(self, env: gym.Env, config: Optional[Dict] = None) -> None:
        self.env = env
        self.config = self._load_config(config)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        obs_sample = env.observation_space.sample()
        if isinstance(obs_sample, dict):
            flat = np.concatenate([np.array(v).flatten() for v in obs_sample.values()])
            state_dim = flat.shape[0]
        else:
            state_dim = int(np.prod(obs_sample.shape))

        action_dim: int = int(np.prod(env.action_space.shape))

        self.actor = Actor(state_dim, action_dim).to(self.device)
        self.actor_target = Actor(state_dim, action_dim).to(self.device)
        self.critic = Critic(state_dim, action_dim).to(self.device)
        self.critic_target = Critic(state_dim, action_dim).to(self.device)

        self._hard_update(self.actor_target, self.actor)
        self._hard_update(self.critic_target, self.critic)

        self.actor_optimizer = optim.Adam(
            self.actor.parameters(), lr=self.config["actor_lr"]
        )
        self.critic_optimizer = optim.Adam(
            self.critic.parameters(), lr=self.config["critic_lr"]
        )

        self.replay_buffer = ReplayBuffer(self.config["buffer_size"])
        self.noise = OUNoise(action_dim)

        self.episode_rewards: List[float] = []
        self.critic_losses: List[float] = []
        self.actor_losses: List[float] = []

    def _load_config(self, config: Optional[Dict]) -> Dict:
        """Load and merge configuration with defaults"""
        defaults: Dict = {
            "gamma": 0.99,
            "tau": 0.005,
            "actor_lr": 1e-4,
            "critic_lr": 1e-3,
            "batch_size": 64,
            "buffer_size": 100000,
            "warmup_steps": 1000,
            "noise_decay": 0.9995,
        }
        if config:
            defaults.update(config)
        return defaults

    def _flatten_observation(self, obs: Union[Dict, np.ndarray]) -> np.ndarray:
        """Flatten dict or array observation to 1-D numpy vector"""
        if isinstance(obs, dict):
            return np.concatenate([np.array(v).flatten() for v in obs.values()])
        return np.asarray(obs).flatten()

    def _hard_update(self, target: nn.Module, source: nn.Module) -> None:
        """Copy weights from source to target network"""
        target.load_state_dict(source.state_dict())

    def _soft_update(self, target: nn.Module, source: nn.Module) -> None:
        """Polyak-averaging soft update of target network"""
        tau = self.config["tau"]
        for tp, sp in zip(target.parameters(), source.parameters()):
            tp.data.copy_(tau * sp.data + (1 - tau) * tp.data)

    def select_action(
        self, state: Union[Dict, np.ndarray], add_noise: bool = True
    ) -> np.ndarray:
        """Select action using actor network with optional exploration noise"""
        flat_state = self._flatten_observation(state)
        state_tensor = torch.FloatTensor(flat_state).unsqueeze(0).to(self.device)
        self.actor.eval()
        with torch.no_grad():
            action: np.ndarray = self.actor(state_tensor).cpu().numpy().flatten()
        self.actor.train()
        if add_noise:
            action += self.noise.sample()
        return np.clip(action, -1.0, 1.0)

    def update(self) -> Optional[Tuple[float, float]]:
        """
        Sample from replay buffer and perform one gradient step on actor and critic.
        Returns (critic_loss, actor_loss) or None if buffer is too small.
        """
        if len(self.replay_buffer) < self.config["batch_size"]:
            return None

        states, actions, rewards, next_states, dones = self.replay_buffer.sample(
            self.config["batch_size"]
        )
        states = states.to(self.device)
        actions = actions.to(self.device)
        rewards = rewards.to(self.device)
        next_states = next_states.to(self.device)
        dones = dones.to(self.device)

        # Critic update
        with torch.no_grad():
            next_actions = self.actor_target(next_states)
            target_q = rewards + self.config["gamma"] * (
                1 - dones
            ) * self.critic_target(next_states, next_actions)
        current_q = self.critic(states, actions)
        critic_loss = F.mse_loss(current_q, target_q)
        self.critic_optimizer.zero_grad()
        critic_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.critic.parameters(), 1.0)
        self.critic_optimizer.step()

        # Actor update
        actor_loss = -self.critic(states, self.actor(states)).mean()
        self.actor_optimizer.zero_grad()
        actor_loss.backward()
        torch.nn.utils.clip_grad_norm_(self.actor.parameters(), 1.0)
        self.actor_optimizer.step()

        self._soft_update(self.actor_target, self.actor)
        self._soft_update(self.critic_target, self.critic)

        return critic_loss.item(), actor_loss.item()

    def train(
        self, num_episodes: int = 1000, max_steps: int = 1000
    ) -> Dict[str, List[float]]:
        """
        Full training loop.

        Args:
            num_episodes: Number of episodes to train.
            max_steps: Max steps per episode.

        Returns:
            Dictionary with training history (episode rewards, losses).
        """
        logger.info(f"Starting DDPG training for {num_episodes} episodes...")
        for episode in range(num_episodes):
            state, _ = self.env.reset()
            self.noise.reset()
            episode_reward = 0.0
            episode_critic_loss = 0.0
            episode_actor_loss = 0.0
            n_updates = 0

            for step in range(max_steps):
                action = self.select_action(state, add_noise=True)
                next_state, reward, done, truncated, _ = self.env.step(action)
                self.replay_buffer.add(
                    state, action, float(reward), next_state, bool(done)
                )
                state = next_state
                episode_reward += float(reward)

                losses = self.update()
                if losses is not None:
                    episode_critic_loss += losses[0]
                    episode_actor_loss += losses[1]
                    n_updates += 1

                if done or truncated:
                    break

            self.episode_rewards.append(episode_reward)
            if n_updates > 0:
                self.critic_losses.append(episode_critic_loss / n_updates)
                self.actor_losses.append(episode_actor_loss / n_updates)

            if episode % 50 == 0:
                avg_reward = np.mean(self.episode_rewards[-50:])
                logger.info(
                    f"Episode {episode}/{num_episodes} | Avg Reward: {avg_reward:.4f}"
                )

        logger.info("DDPG training complete.")
        return {
            "episode_rewards": self.episode_rewards,
            "critic_losses": self.critic_losses,
            "actor_losses": self.actor_losses,
        }

    def evaluate(self, num_episodes: int = 5) -> Dict[str, float]:
        """
        Evaluate the agent's performance without exploration noise.

        Args:
            num_episodes: Number of evaluation episodes.

        Returns:
            Dictionary with mean reward, std reward, and mean episode length.
        """
        eval_rewards: List[float] = []
        episode_lengths: List[int] = []

        for _ in range(num_episodes):
            state, _ = self.env.reset()
            episode_reward = 0.0
            steps = 0
            done = False

            while not done:
                action = self.select_action(state, add_noise=False)
                state, reward, done, truncated, _ = self.env.step(action)
                episode_reward += float(reward)
                steps += 1
                done = done or truncated

            eval_rewards.append(episode_reward)
            episode_lengths.append(steps)

        return {
            "mean_reward": float(np.mean(eval_rewards)),
            "std_reward": float(np.std(eval_rewards)),
            "mean_episode_length": float(np.mean(episode_lengths)),
        }

    def _plot_metrics(self, final: bool = False) -> None:
        """Plot training metrics"""
        fig, axes = plt.subplots(1, 3, figsize=(15, 4))
        axes[0].plot(self.episode_rewards)
        axes[0].set_title("Episode Rewards")
        axes[0].set_xlabel("Episode")
        axes[1].plot(self.critic_losses)
        axes[1].set_title("Critic Loss")
        axes[1].set_xlabel("Episode")
        axes[2].plot(self.actor_losses)
        axes[2].set_title("Actor Loss")
        axes[2].set_xlabel("Episode")
        plt.tight_layout()
        tag = "final" if final else "training"
        plt.savefig(f"ddpg_{tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png")
        plt.close()

    def save_model(self, path: str) -> None:
        """Persist actor/critic weights and config to disk"""
        os.makedirs(path, exist_ok=True)
        torch.save(self.actor.state_dict(), os.path.join(path, "actor.pth"))
        torch.save(self.critic.state_dict(), os.path.join(path, "critic.pth"))
        with open(os.path.join(path, "config.json"), "w") as f:
            json.dump(self.config, f, indent=2)
        logger.info(f"Model saved to {path}")

    def load_model(self, path: str) -> None:
        """Load actor/critic weights from disk"""
        self.actor.load_state_dict(
            torch.load(os.path.join(path, "actor.pth"), map_location=self.device)
        )
        self.critic.load_state_dict(
            torch.load(os.path.join(path, "critic.pth"), map_location=self.device)
        )
        self._hard_update(self.actor_target, self.actor)
        self._hard_update(self.critic_target, self.critic)
        logger.info(f"Model loaded from {path}")


class TradingEnvironment(gym.Env):
    """
    Custom OpenAI Gym trading environment.
    The agent observes prices, volumes, and macro features and outputs
    a continuous position weight vector.
    """

    metadata: Dict = {"render_modes": ["human"]}

    def __init__(
        self,
        n_assets: int = 5,
        window: int = 10,
        n_macro: int = 5,
        transaction_cost: float = 0.001,
    ) -> None:
        super().__init__()
        self.n_assets = n_assets
        self.window = window
        self.n_macro = n_macro
        self.transaction_cost = transaction_cost
        self.current_step: int = 0
        self.max_steps: int = 252
        self.returns: np.ndarray = np.zeros((self.max_steps, n_assets))
        self.current_weights: np.ndarray = np.ones(n_assets) / n_assets

        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(n_assets,), dtype=np.float32
        )
        self.observation_space = spaces.Dict(
            {
                "prices": spaces.Box(
                    -np.inf, np.inf, (n_assets, window), dtype=np.float32
                ),
                "volumes": spaces.Box(0, np.inf, (n_assets,), dtype=np.float32),
                "macro": spaces.Box(-np.inf, np.inf, (n_macro,), dtype=np.float32),
            }
        )

    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
    ) -> Tuple[Dict[str, np.ndarray], Dict]:
        """Reset environment to initial state"""
        super().reset(seed=seed)
        self.current_step = 0
        self.current_weights = np.ones(self.n_assets, dtype=np.float32) / self.n_assets
        self.returns = np.random.normal(
            0.0005, 0.01, (self.max_steps, self.n_assets)
        ).astype(np.float32)
        return self._get_obs(), {}

    def step(
        self, action: np.ndarray
    ) -> Tuple[Dict[str, np.ndarray], float, bool, bool, Dict]:
        """Execute one time step within the environment"""
        action = np.asarray(action, dtype=np.float32).reshape(self.n_assets)
        new_weights = self._normalize_weights(action)
        cost = self._transaction_cost(new_weights)
        reward = float(self._portfolio_return(new_weights) - cost)
        self.current_step += 1
        done = self.current_step >= self.max_steps - 1
        return self._get_obs(), reward, done, False, {}

    def _portfolio_return(self, weights: np.ndarray) -> float:
        """One-step portfolio return"""
        if self.current_step >= len(self.returns):
            return 0.0
        return float(np.dot(self.returns[self.current_step], weights))

    def _normalize_weights(self, action: np.ndarray) -> np.ndarray:
        """Map raw actions to valid portfolio weights via tanh + L1 normalization"""
        weights = np.tanh(action)
        denom = np.sum(np.abs(weights))
        if denom < 1e-8:
            return np.ones(self.n_assets, dtype=np.float32) / self.n_assets
        return (weights / denom).astype(np.float32)

    def _transaction_cost(self, new_weights: np.ndarray) -> float:
        """Proportional transaction cost based on turnover"""
        turnover = float(np.sum(np.abs(new_weights - self.current_weights)))
        self.current_weights = new_weights.copy()
        return turnover * self.transaction_cost

    def _get_obs(self) -> Dict[str, np.ndarray]:
        """Return current market observation"""
        start = max(0, self.current_step - self.window)
        price_window = self.returns[start : self.current_step + 1]
        if len(price_window) < self.window:
            pad = np.zeros(
                (self.window - len(price_window), self.n_assets), dtype=np.float32
            )
            price_window = np.vstack([pad, price_window])
        return {
            "prices": price_window[-self.window :].T.astype(np.float32),
            "volumes": np.abs(np.random.normal(1000, 500, (self.n_assets,))).astype(
                np.float32
            ),
            "macro": np.random.normal(0, 1, (self.n_macro,)).astype(np.float32),
        }
