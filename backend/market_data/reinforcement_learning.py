""""""

import logging
import random
from abc import ABC
from collections import deque
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class ActionSpace(Enum):
    """Types of action spaces for RL environments."""

    DISCRETE = "discrete"
    CONTINUOUS = "continuous"
    MIXED = "mixed"


class ObservationType(Enum):
    """Types of observations for RL environments."""

    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    IMAGE = "image"
    TEXT = "text"
    MIXED = "mixed"


class RLAlgorithm(Enum):
    """Types of reinforcement learning algorithms."""

    DQN = "dqn"
    DDPG = "ddpg"
    PPO = "ppo"
    SAC = "sac"
    A2C = "a2c"
    TD3 = "td3"
    CUSTOM = "custom"


class RewardFunction(Enum):
    """Types of reward functions for RL environments."""

    RETURNS = "returns"
    SHARPE = "sharpe"
    SORTINO = "sortino"
    CALMAR = "calmar"
    PROFIT_FACTOR = "profit_factor"
    CUSTOM = "custom"


class TradingAction(Enum):
    """Trading actions for discrete action spaces."""

    BUY = 0
    SELL = 1
    HOLD = 2


class TradingEnvironment(ABC):
    """Base class for trading environments."""

    def __init__(
        self,
        data: pd.DataFrame,
        features: List[str],
        window_size: int = 30,
        max_steps: Optional[int] = None,
        commission: float = 0.001,
        reward_function: RewardFunction = RewardFunction.RETURNS,
        initial_balance: float = 10000.0,
        action_space: ActionSpace = ActionSpace.DISCRETE,
        observation_type: ObservationType = ObservationType.NUMERIC,
        random_start: bool = True,
    ) -> None:
        """
        Initialize trading environment.

        Args:
            data: DataFrame with market data
            features: List of feature columns to use
            window_size: Size of observation window
            max_steps: Maximum number of steps per episode
            commission: Trading commission as a fraction
            reward_function: Type of reward function
            initial_balance: Initial account balance
            action_space: Type of action space
            observation_type: Type of observation
            random_start: Whether to start at a random position
        """
        self.data = data
        self.features = features
        self.window_size = window_size
        self.max_steps = max_steps or len(data) - window_size - 1
        self.commission = commission
        self.reward_function = reward_function
        self.initial_balance = initial_balance
        self.action_space_type = action_space
        self.observation_type = observation_type
        self.random_start = random_start
        self._validate_data()
        self.action_space = self._setup_action_space()
        self.observation_space = self._setup_observation_space()
        self.reset()

    def _validate_data(self) -> Any:
        """Validate input data."""
        if self.data is None or len(self.data) == 0:
            raise ValueError("Data cannot be empty")
        for feature in self.features:
            if feature not in self.data.columns:
                raise ValueError(f"Feature '{feature}' not found in data")
        if "close" not in self.data.columns and "price" not in self.data.columns:
            raise ValueError("Data must have a 'close' or 'price' column")
        self.price_col = "close" if "close" in self.data.columns else "price"

    def _setup_action_space(self) -> Dict[str, Any]:
        """
        Set up action space.

        Returns:
            Action space configuration
        """
        if self.action_space_type == ActionSpace.DISCRETE:
            return {
                "type": "discrete",
                "n": 3,
                "actions": [a.value for a in TradingAction],
            }
        elif self.action_space_type == ActionSpace.CONTINUOUS:
            return {"type": "continuous", "shape": (1,), "low": -1.0, "high": 1.0}
        elif self.action_space_type == ActionSpace.MIXED:
            return {
                "type": "mixed",
                "discrete": {"n": 3, "actions": [a.value for a in TradingAction]},
                "continuous": {"shape": (1,), "low": 0.0, "high": 1.0},
            }
        else:
            raise ValueError(f"Unsupported action space type: {self.action_space_type}")

    def _setup_observation_space(self) -> Dict[str, Any]:
        """
        Set up observation space.

        Returns:
            Observation space configuration
        """
        if self.observation_type == ObservationType.NUMERIC:
            return {
                "type": "numeric",
                "shape": (self.window_size, len(self.features) + 4),
                "features": self.features + ["position", "balance", "equity", "pnl"],
            }
        elif self.observation_type == ObservationType.IMAGE:
            return {
                "type": "image",
                "shape": (len(self.features) + 4, self.window_size, 1),
                "features": self.features + ["position", "balance", "equity", "pnl"],
            }
        else:
            raise ValueError(f"Unsupported observation type: {self.observation_type}")

    def reset(self) -> np.ndarray:
        """
        Reset environment to initial state.

        Returns:
            Initial observation
        """
        self.position = 0.0
        self.balance = self.initial_balance
        self.equity = self.initial_balance
        self.pnl = 0.0
        self.current_step = 0
        if self.random_start and len(self.data) > self.window_size + self.max_steps:
            self.start_idx = random.randint(
                0, len(self.data) - self.window_size - self.max_steps - 1
            )
        else:
            self.start_idx = 0
        self.history = {
            "positions": [],
            "balances": [],
            "equities": [],
            "returns": [],
            "actions": [],
            "rewards": [],
        }
        return self._get_observation()

    def step(
        self, action: Union[int, float, np.ndarray]
    ) -> Tuple[np.ndarray, float, bool, Dict[str, Any]]:
        """
        Take a step in the environment.

        Args:
            action: Action to take

        Returns:
            Tuple of (observation, reward, done, info)
        """
        action_taken = self._parse_action(action)
        self._execute_action(action_taken)
        self.current_step += 1
        done = self.current_step >= self.max_steps
        observation = self._get_observation()
        reward = self._calculate_reward()
        self._update_history(action_taken, reward)
        info = self._get_info()
        return (observation, reward, done, info)

    def _parse_action(self, action: Union[int, float, np.ndarray]) -> Dict[str, Any]:
        """
        Parse action based on action space.

        Args:
            action: Action from agent

        Returns:
            Parsed action
        """
        if self.action_space_type == ActionSpace.DISCRETE:
            if isinstance(action, np.ndarray):
                action = action.item()
            if action == TradingAction.BUY.value:
                return {"type": "buy", "size": 1.0}
            elif action == TradingAction.SELL.value:
                return {"type": "sell", "size": 1.0}
            else:
                return {"type": "hold", "size": 0.0}
        elif self.action_space_type == ActionSpace.CONTINUOUS:
            if isinstance(action, np.ndarray):
                action = action.item()
            action = max(min(action, 1.0), -1.0)
            if action > 0:
                return {"type": "buy", "size": action}
            elif action < 0:
                return {"type": "sell", "size": -action}
            else:
                return {"type": "hold", "size": 0.0}
        elif self.action_space_type == ActionSpace.MIXED:
            if isinstance(action, tuple):
                action_type, action_size = action
            elif isinstance(action, np.ndarray):
                action_type = int(action[0])
                action_size = float(action[1])
            else:
                raise ValueError(
                    f"Invalid action format for mixed action space: {action}"
                )
            action_size = max(min(action_size, 1.0), 0.0)
            if action_type == TradingAction.BUY.value:
                return {"type": "buy", "size": action_size}
            elif action_type == TradingAction.SELL.value:
                return {"type": "sell", "size": action_size}
            else:
                return {"type": "hold", "size": 0.0}
        else:
            raise ValueError(f"Unsupported action space type: {self.action_space_type}")

    def _execute_action(self, action: Dict[str, Any]) -> Any:
        """
        Execute trading action.

        Args:
            action: Parsed action
        """
        current_idx = self.start_idx + self.window_size + self.current_step
        current_price = self.data.iloc[current_idx][self.price_col]
        position_value = self.position * current_price
        if action["type"] == "buy":
            if self.position <= 0:
                self.balance += position_value * (1 - self.commission)
                self.position = 0
            buy_amount = self.balance * action["size"]
            buy_amount_with_commission = buy_amount * (1 + self.commission)
            if buy_amount_with_commission <= self.balance:
                self.balance -= buy_amount_with_commission
                self.position += buy_amount / current_price
        elif action["type"] == "sell":
            if self.position >= 0:
                self.balance += position_value * (1 - self.commission)
                self.position = 0
            sell_amount = self.balance * action["size"]
            sell_size = sell_amount / current_price
            self.position -= sell_size
            self.balance -= sell_amount * self.commission
        self.equity = self.balance + self.position * current_price
        if self.current_step > 0:
            prev_equity = self.history["equities"][-1]
            self.pnl = self.equity - prev_equity
        else:
            self.pnl = 0.0

    def _get_observation(self) -> np.ndarray:
        """
        Get current observation.

        Returns:
            Observation
        """
        start = self.start_idx + self.current_step
        end = start + self.window_size
        data_window = self.data.iloc[start:end].copy()
        features = data_window[self.features].values
        features = self._normalize_features(features)
        if self.current_step > 0:
            positions = np.array(
                [self.history["positions"][-self.window_size :] + [self.position]]
            )
            balances = np.array(
                [self.history["balances"][-self.window_size :] + [self.balance]]
            )
            equities = np.array(
                [self.history["equities"][-self.window_size :] + [self.equity]]
            )
            pnls = np.array([self.history["returns"][-self.window_size :] + [self.pnl]])
        else:
            positions = np.zeros((1, self.window_size))
            balances = np.ones((1, self.window_size)) * self.initial_balance
            equities = np.ones((1, self.window_size)) * self.initial_balance
            pnls = np.zeros((1, self.window_size))
        positions = positions / (np.max(np.abs(positions)) + 1e-06)
        balances = balances / self.initial_balance
        equities = equities / self.initial_balance
        pnls = pnls / (np.max(np.abs(pnls)) + 1e-06)
        if self.observation_type == ObservationType.NUMERIC:
            observation = np.column_stack(
                [features, positions.T, balances.T, equities.T, pnls.T]
            )
        elif self.observation_type == ObservationType.IMAGE:
            observation = np.vstack([features.T, positions, balances, equities, pnls])
            observation = observation.reshape(observation.shape + (1,))
        return observation

    def _normalize_features(self, features: np.ndarray) -> np.ndarray:
        """
        Normalize features.

        Args:
            features: Feature array

        Returns:
            Normalized features
        """
        for i in range(features.shape[1]):
            feature_min = np.min(features[:, i])
            feature_max = np.max(features[:, i])
            if feature_max > feature_min:
                features[:, i] = (features[:, i] - feature_min) / (
                    feature_max - feature_min
                )
            else:
                features[:, i] = 0.0
        return features

    def _calculate_reward(self) -> float:
        """
        Calculate reward based on reward function.

        Returns:
            Reward value
        """
        if self.current_step == 0:
            return 0.0
        if self.reward_function == RewardFunction.RETURNS:
            prev_equity = self.history["equities"][-1]
            return (self.equity - prev_equity) / prev_equity
        elif self.reward_function == RewardFunction.SHARPE:
            if len(self.history["returns"]) < 2:
                return 0.0
            returns = np.array(self.history["returns"]) / np.array(
                self.history["equities"][:-1]
            )
            mean_return = np.mean(returns)
            std_return = np.std(returns) + 1e-06
            return mean_return / std_return
        elif self.reward_function == RewardFunction.SORTINO:
            if len(self.history["returns"]) < 2:
                return 0.0
            returns = np.array(self.history["returns"]) / np.array(
                self.history["equities"][:-1]
            )
            mean_return = np.mean(returns)
            negative_returns = returns[returns < 0]
            if len(negative_returns) == 0:
                downside_std = 1e-06
            else:
                downside_std = np.std(negative_returns) + 1e-06
            return mean_return / downside_std
        elif self.reward_function == RewardFunction.CALMAR:
            if len(self.history["equities"]) < 2:
                return 0.0
            returns = np.array(self.history["returns"]) / np.array(
                self.history["equities"][:-1]
            )
            mean_return = np.mean(returns)
            equity_curve = np.array(self.history["equities"])
            peak = np.maximum.accumulate(equity_curve)
            drawdown = (peak - equity_curve) / peak
            max_drawdown = np.max(drawdown) + 1e-06
            return mean_return / max_drawdown
        elif self.reward_function == RewardFunction.PROFIT_FACTOR:
            if len(self.history["returns"]) < 2:
                return 0.0
            returns = np.array(self.history["returns"])
            positive_returns = np.sum(returns[returns > 0])
            negative_returns = np.abs(np.sum(returns[returns < 0])) + 1e-06
            return positive_returns / negative_returns
        else:
            prev_equity = self.history["equities"][-1]
            return (self.equity - prev_equity) / prev_equity

    def _update_history(self, action: Dict[str, Any], reward: float) -> Any:
        """
        Update history with current state.

        Args:
            action: Action taken
            reward: Reward received
        """
        self.history["positions"].append(self.position)
        self.history["balances"].append(self.balance)
        self.history["equities"].append(self.equity)
        self.history["returns"].append(self.pnl)
        self.history["actions"].append(action)
        self.history["rewards"].append(reward)

    def _get_info(self) -> Dict[str, Any]:
        """
        Get additional information.

        Returns:
            Information dictionary
        """
        current_idx = self.start_idx + self.window_size + self.current_step
        current_price = self.data.iloc[current_idx][self.price_col]
        return {
            "step": self.current_step,
            "price": current_price,
            "position": self.position,
            "balance": self.balance,
            "equity": self.equity,
            "pnl": self.pnl,
            "total_return": (self.equity - self.initial_balance) / self.initial_balance,
        }

    def render(self, mode: str = "human") -> Any:
        """
        Render the environment.

        Args:
            mode: Rendering mode
        """
        if mode == "human":
            current_idx = self.start_idx + self.window_size + self.current_step
            current_price = self.data.iloc[current_idx][self.price_col]
            logger.info(f"Step: {self.current_step}")
            logger.info(f"Price: {current_price:.2f}")
            logger.info(f"Position: {self.position:.6f}")
            logger.info(f"Balance: {self.balance:.2f}")
            logger.info(f"Equity: {self.equity:.2f}")
            logger.info(f"PnL: {self.pnl:.2f}")
            logger.info(
                f"Total Return: {(self.equity - self.initial_balance) / self.initial_balance:.2%}"
            )
            logger.info("-" * 50)

    def close(self) -> Any:
        """Close environment and release resources."""


class ReplayBuffer:
    """Experience replay buffer for RL algorithms."""

    def __init__(self, capacity: int) -> None:
        """
        Initialize replay buffer.

        Args:
            capacity: Maximum buffer capacity
        """
        self.buffer = deque(maxlen=capacity)

    def push(
        self,
        state: np.ndarray,
        action: Any,
        reward: float,
        next_state: np.ndarray,
        done: bool,
    ) -> Any:
        """
        Add experience to buffer.

        Args:
            state: Current state
            action: Action taken
            reward: Reward received
            next_state: Next state
            done: Whether episode is done
        """
        self.buffer.append((state, action, reward, next_state, done))

    def sample(self, batch_size: int) -> List[Tuple]:
        """
        Sample batch of experiences.

        Args:
            batch_size: Number of experiences to sample

        Returns:
            Batch of experiences
        """
        return random.sample(self.buffer, min(len(self.buffer), batch_size))

    def __len__(self) -> int:
        """
        Get buffer length.

        Returns:
            Buffer length
        """
        return len(self.buffer)


class DQNNetwork(nn.Module):
    """Deep Q-Network for discrete action spaces."""

    def __init__(
        self, input_shape: Tuple[int, ...], num_actions: int, hidden_size: int = 128
    ) -> None:
        """
        Initialize DQN network.

        Args:
            input_shape: Shape of input observations
            num_actions: Number of discrete actions
            hidden_size: Size of hidden layers
        """
        super(DQNNetwork, self).__init__()
        if len(input_shape) == 2:
            input_size = input_shape[0] * input_shape[1]
            self.flatten = lambda x: x.view(x.size(0), -1)
            self.network = nn.Sequential(
                nn.Linear(input_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, num_actions),
            )
        elif len(input_shape) == 3:
            self.flatten = lambda x: x
            self.network = nn.Sequential(
                nn.Conv2d(input_shape[0], 32, kernel_size=3, stride=1, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(kernel_size=2, stride=2),
                nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1),
                nn.ReLU(),
                nn.MaxPool2d(kernel_size=2, stride=2),
                nn.Flatten(),
                nn.Linear(
                    64 * (input_shape[1] // 4) * (input_shape[2] // 4), hidden_size
                ),
                nn.ReLU(),
                nn.Linear(hidden_size, num_actions),
            )
        else:
            raise ValueError(f"Unsupported input shape: {input_shape}")

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input tensor

        Returns:
            Q-values for each action
        """
        x = self.flatten(x)
        return self.network(x)


class DQNAgent:
    """Deep Q-Network agent for discrete action spaces."""

    def __init__(
        self,
        input_shape: Tuple[int, ...],
        num_actions: int,
        hidden_size: int = 128,
        learning_rate: float = 0.001,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.01,
        epsilon_decay: float = 0.995,
        target_update: int = 10,
        buffer_capacity: int = 10000,
        batch_size: int = 64,
        device: str = "auto",
    ) -> None:
        """
        Initialize DQN agent.

        Args:
            input_shape: Shape of input observations
            num_actions: Number of discrete actions
            hidden_size: Size of hidden layers
            learning_rate: Learning rate
            gamma: Discount factor
            epsilon_start: Initial exploration rate
            epsilon_end: Final exploration rate
            epsilon_decay: Exploration rate decay
            target_update: Target network update frequency
            buffer_capacity: Replay buffer capacity
            batch_size: Training batch size
            device: Device to use (auto, cpu, cuda)
        """
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        self.policy_net = DQNNetwork(input_shape, num_actions, hidden_size).to(
            self.device
        )
        self.target_net = DQNNetwork(input_shape, num_actions, hidden_size).to(
            self.device
        )
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        self.replay_buffer = ReplayBuffer(buffer_capacity)
        self.num_actions = num_actions
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.target_update = target_update
        self.batch_size = batch_size
        self.steps_done = 0
        self.episodes_done = 0

    def select_action(self, state: np.ndarray, training: bool = True) -> int:
        """
        Select action using epsilon-greedy policy.

        Args:
            state: Current state
            training: Whether agent is training

        Returns:
            Selected action
        """
        if training and random.random() < self.epsilon:
            return random.randrange(self.num_actions)
        else:
            with torch.no_grad():
                state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
                q_values = self.policy_net(state_tensor)
                return q_values.max(1)[1].item()

    def update(self) -> Optional[float]:
        """
        Update agent.

        Returns:
            Loss value or None if buffer is too small
        """
        if len(self.replay_buffer) < self.batch_size:
            return None
        batch = self.replay_buffer.sample(self.batch_size)
        states, actions, rewards, next_states, dones = zip(*batch)
        states = torch.FloatTensor(np.array(states)).to(self.device)
        actions = torch.LongTensor(np.array(actions)).to(self.device)
        rewards = torch.FloatTensor(np.array(rewards)).to(self.device)
        next_states = torch.FloatTensor(np.array(next_states)).to(self.device)
        dones = torch.FloatTensor(np.array(dones)).to(self.device)
        q_values = self.policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)
        with torch.no_grad():
            next_q_values = self.target_net(next_states).max(1)[0]
            target_q_values = rewards + self.gamma * next_q_values * (1 - dones)
        loss = F.smooth_l1_loss(q_values, target_q_values)
        self.optimizer.zero_grad()
        loss.backward()
        self.optimizer.step()
        if self.steps_done % self.target_update == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        self.steps_done += 1
        return loss.item()

    def train(
        self,
        env: TradingEnvironment,
        num_episodes: int,
        max_steps_per_episode: Optional[int] = None,
        eval_interval: int = 10,
        render: bool = False,
        verbose: bool = True,
    ) -> Dict[str, List[float]]:
        """
        Train agent.

        Args:
            env: Trading environment
            num_episodes: Number of episodes
            max_steps_per_episode: Maximum steps per episode
            eval_interval: Evaluation interval
            render: Whether to render environment
            verbose: Whether to print progress

        Returns:
            Training metrics
        """
