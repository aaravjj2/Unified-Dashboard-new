"""
Reinforcement Learning Trading Agent
Implements #56 from ROADMAP_ULTIMATE.md

Based on: https://github.com/AI4Finance-Foundation/FinRL
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import deque
import random
import logging

logger = logging.getLogger(__name__)

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class Action(Enum):
    """Trading actions"""
    HOLD = 0
    BUY = 1
    SELL = 2


@dataclass
class TradingState:
    """Current trading state"""
    prices: np.ndarray  # Recent price history
    position: float  # Current position (-1 to 1)
    cash: float  # Available cash
    portfolio_value: float  # Total portfolio value
    unrealized_pnl: float  # Unrealized P&L
    features: np.ndarray  # Technical features
    

@dataclass
class Experience:
    """Experience tuple for replay buffer"""
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool


class ReplayBuffer:
    """Experience replay buffer"""
    def __init__(self, capacity: int = 10000):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, experience: Experience):
        self.buffer.append(experience)
    
    def sample(self, batch_size: int) -> List[Experience]:
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))
    
    def __len__(self):
        return len(self.buffer)


if HAS_TORCH:
    class DQNetwork(nn.Module):
        """Deep Q-Network for trading"""
        def __init__(self, state_dim: int, action_dim: int = 3, hidden_dim: int = 128):
            super().__init__()
            
            self.feature_net = nn.Sequential(
                nn.Linear(state_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(hidden_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.1)
            )
            
            # Dueling DQN architecture
            self.value_stream = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Linear(hidden_dim // 2, 1)
            )
            
            self.advantage_stream = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Linear(hidden_dim // 2, action_dim)
            )
        
        def forward(self, x):
            features = self.feature_net(x)
            value = self.value_stream(features)
            advantage = self.advantage_stream(features)
            
            # Combine value and advantage
            q_values = value + (advantage - advantage.mean(dim=-1, keepdim=True))
            return q_values


    class ActorCriticNetwork(nn.Module):
        """Actor-Critic network for PPO"""
        def __init__(self, state_dim: int, action_dim: int = 3, hidden_dim: int = 128):
            super().__init__()
            
            self.shared = nn.Sequential(
                nn.Linear(state_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.ReLU()
            )
            
            # Actor (policy)
            self.actor = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Linear(hidden_dim // 2, action_dim),
                nn.Softmax(dim=-1)
            )
            
            # Critic (value)
            self.critic = nn.Sequential(
                nn.Linear(hidden_dim, hidden_dim // 2),
                nn.ReLU(),
                nn.Linear(hidden_dim // 2, 1)
            )
        
        def forward(self, x):
            shared_features = self.shared(x)
            action_probs = self.actor(shared_features)
            value = self.critic(shared_features)
            return action_probs, value
        
        def get_action(self, state, deterministic: bool = False):
            with torch.no_grad():
                probs, value = self.forward(state)
                
                if deterministic:
                    action = probs.argmax(dim=-1)
                else:
                    dist = torch.distributions.Categorical(probs)
                    action = dist.sample()
                
                return action.item(), probs[0, action].item(), value.item()


class TradingEnvironment:
    """Trading environment for RL agent"""
    
    def __init__(self, df: pd.DataFrame, 
                initial_cash: float = 100000,
                transaction_cost: float = 0.001,
                max_position: float = 1.0,
                lookback: int = 30):
        self.df = df.reset_index(drop=True)
        self.initial_cash = initial_cash
        self.transaction_cost = transaction_cost
        self.max_position = max_position
        self.lookback = lookback
        
        # Prepare features
        self._prepare_features()
        
        # State
        self.current_step = None
        self.cash = None
        self.position = None
        self.entry_price = None
        self.portfolio_values = []
        
    def _prepare_features(self):
        """Calculate technical features"""
        df = self.df.copy()
        
        # Returns
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Moving averages
        df['sma_10'] = df['close'].rolling(10).mean() / df['close'] - 1
        df['sma_20'] = df['close'].rolling(20).mean() / df['close'] - 1
        df['sma_50'] = df['close'].rolling(50).mean() / df['close'] - 1
        
        # Volatility
        df['volatility'] = df['returns'].rolling(20).std()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = (100 - (100 / (1 + rs))) / 100 - 0.5
        
        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        df['macd'] = (ema12 - ema26) / df['close']
        
        # Bollinger Bands position
        bb_mid = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_position'] = (df['close'] - bb_mid) / (2 * bb_std)
        
        # Volume (if available)
        if 'volume' in df.columns:
            df['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean() - 1
        else:
            df['volume_ratio'] = 0
        
        # Momentum
        df['momentum_5'] = df['close'].pct_change(5)
        df['momentum_10'] = df['close'].pct_change(10)
        
        self.feature_columns = [
            'returns', 'log_returns', 'sma_10', 'sma_20', 'sma_50',
            'volatility', 'rsi', 'macd', 'bb_position', 'volume_ratio',
            'momentum_5', 'momentum_10'
        ]
        
        df = df.fillna(0)
        self.features = df[self.feature_columns].values
        self.prices = df['close'].values
        
    def reset(self) -> np.ndarray:
        """Reset environment"""
        self.current_step = self.lookback
        self.cash = self.initial_cash
        self.position = 0
        self.entry_price = 0
        self.portfolio_values = [self.initial_cash]
        
        return self._get_state()
    
    def _get_state(self) -> np.ndarray:
        """Get current state"""
        # Price history features
        price_features = self.features[self.current_step - self.lookback:self.current_step].flatten()
        
        # Position info
        position_info = np.array([
            self.position / self.max_position,  # Normalized position
            self.cash / self.initial_cash - 1,  # Normalized cash
            (self.portfolio_values[-1] / self.initial_cash - 1),  # Portfolio return
        ])
        
        # Recent features
        recent_features = self.features[self.current_step]
        
        state = np.concatenate([
            recent_features,
            position_info,
            price_features[-self.lookback * len(self.feature_columns) // 2:]  # Use half of lookback
        ])
        
        return state.astype(np.float32)
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """Execute action and return next state, reward, done, info"""
        current_price = self.prices[self.current_step]
        previous_portfolio = self.portfolio_values[-1]
        
        # Execute action
        reward = 0
        transaction_cost = 0
        
        if action == Action.BUY.value and self.position < self.max_position:
            # Buy
            buy_amount = min(self.cash * 0.95, self.cash)  # Use 95% of cash
            shares = buy_amount / current_price
            transaction_cost = buy_amount * self.transaction_cost
            
            self.cash -= buy_amount + transaction_cost
            self.position += shares / (self.initial_cash / current_price)  # Normalize
            self.entry_price = current_price
            
        elif action == Action.SELL.value and self.position > -self.max_position:
            # Sell/Short
            if self.position > 0:
                # Close long
                sell_value = self.position * (self.initial_cash / self.entry_price) * current_price
                transaction_cost = sell_value * self.transaction_cost
                self.cash += sell_value - transaction_cost
                self.position = 0
            else:
                # Short (simplified)
                short_amount = self.cash * 0.5
                shares = short_amount / current_price
                transaction_cost = short_amount * self.transaction_cost
                self.position -= shares / (self.initial_cash / current_price)
                self.entry_price = current_price
        
        # Move to next step
        self.current_step += 1
        done = self.current_step >= len(self.prices) - 1
        
        # Calculate portfolio value
        position_value = 0
        if self.position != 0:
            current_price = self.prices[self.current_step]
            position_value = abs(self.position) * (self.initial_cash / self.entry_price) * current_price
            if self.position < 0:  # Short position
                position_value = 2 * abs(self.position) * self.initial_cash - position_value
        
        portfolio_value = self.cash + position_value
        self.portfolio_values.append(portfolio_value)
        
        # Calculate reward
        portfolio_return = (portfolio_value - previous_portfolio) / previous_portfolio
        
        # Reward shaping
        reward = portfolio_return * 100  # Scale up
        reward -= transaction_cost / self.initial_cash * 10  # Penalize trading
        
        # Penalize large drawdowns
        max_value = max(self.portfolio_values)
        drawdown = (max_value - portfolio_value) / max_value
        if drawdown > 0.1:
            reward -= drawdown * 5
        
        info = {
            'portfolio_value': portfolio_value,
            'position': self.position,
            'cash': self.cash,
            'step': self.current_step,
            'transaction_cost': transaction_cost
        }
        
        next_state = self._get_state() if not done else np.zeros_like(self._get_state())
        
        return next_state, reward, done, info


class RLTradingAgent:
    """
    Reinforcement Learning Trading Agent
    Supports DQN and Actor-Critic methods
    """
    
    def __init__(self, state_dim: int, 
                action_dim: int = 3,
                algorithm: str = 'dqn',
                learning_rate: float = 0.0003,
                gamma: float = 0.99,
                epsilon_start: float = 1.0,
                epsilon_end: float = 0.01,
                epsilon_decay: float = 0.995,
                batch_size: int = 64,
                target_update: int = 100):
        
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.algorithm = algorithm
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.target_update = target_update
        self.device = 'cuda' if HAS_TORCH and torch.cuda.is_available() else 'cpu'
        
        if not HAS_TORCH:
            logger.warning("PyTorch not available - using random agent")
            return
        
        if algorithm == 'dqn':
            self.policy_net = DQNetwork(state_dim, action_dim).to(self.device)
            self.target_net = DQNetwork(state_dim, action_dim).to(self.device)
            self.target_net.load_state_dict(self.policy_net.state_dict())
            self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        else:  # actor-critic
            self.policy_net = ActorCriticNetwork(state_dim, action_dim).to(self.device)
            self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        
        self.replay_buffer = ReplayBuffer()
        self.training_step = 0
        self.losses = []
        
    def select_action(self, state: np.ndarray, 
                     training: bool = True) -> int:
        """Select action using epsilon-greedy or policy"""
        if not HAS_TORCH:
            return random.randint(0, self.action_dim - 1)
        
        if training and random.random() < self.epsilon:
            return random.randint(0, self.action_dim - 1)
        
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            
            if self.algorithm == 'dqn':
                q_values = self.policy_net(state_tensor)
                return q_values.argmax().item()
            else:
                action, _, _ = self.policy_net.get_action(state_tensor, deterministic=not training)
                return action
    
    def train_step(self) -> float:
        """Perform one training step"""
        if not HAS_TORCH or len(self.replay_buffer) < self.batch_size:
            return 0.0
        
        experiences = self.replay_buffer.sample(self.batch_size)
        
        states = torch.FloatTensor([e.state for e in experiences]).to(self.device)
        actions = torch.LongTensor([e.action for e in experiences]).to(self.device)
        rewards = torch.FloatTensor([e.reward for e in experiences]).to(self.device)
        next_states = torch.FloatTensor([e.next_state for e in experiences]).to(self.device)
        dones = torch.FloatTensor([e.done for e in experiences]).to(self.device)
        
        if self.algorithm == 'dqn':
            # DQN update
            current_q = self.policy_net(states).gather(1, actions.unsqueeze(1))
            
            with torch.no_grad():
                # Double DQN
                next_actions = self.policy_net(next_states).argmax(1, keepdim=True)
                next_q = self.target_net(next_states).gather(1, next_actions)
                target_q = rewards.unsqueeze(1) + self.gamma * next_q * (1 - dones.unsqueeze(1))
            
            loss = F.smooth_l1_loss(current_q, target_q)
            
        else:  # Actor-Critic
            action_probs, values = self.policy_net(states)
            _, next_values = self.policy_net(next_states)
            
            advantages = rewards + self.gamma * next_values.squeeze() * (1 - dones) - values.squeeze()
            
            # Policy loss
            dist = torch.distributions.Categorical(action_probs)
            log_probs = dist.log_prob(actions)
            policy_loss = -(log_probs * advantages.detach()).mean()
            
            # Value loss
            value_loss = F.mse_loss(values.squeeze(), rewards + self.gamma * next_values.squeeze().detach() * (1 - dones))
            
            # Entropy bonus for exploration
            entropy = dist.entropy().mean()
            
            loss = policy_loss + 0.5 * value_loss - 0.01 * entropy
        
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()
        
        self.training_step += 1
        
        # Update target network (DQN)
        if self.algorithm == 'dqn' and self.training_step % self.target_update == 0:
            self.target_net.load_state_dict(self.policy_net.state_dict())
        
        # Decay epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        
        self.losses.append(loss.item())
        return loss.item()
    
    def store_experience(self, experience: Experience):
        """Store experience in replay buffer"""
        self.replay_buffer.push(experience)
    
    def train(self, env: TradingEnvironment, 
             n_episodes: int = 100,
             verbose: bool = True) -> Dict[str, Any]:
        """Train the agent"""
        episode_rewards = []
        episode_lengths = []
        portfolio_returns = []
        
        for episode in range(n_episodes):
            state = env.reset()
            total_reward = 0
            episode_length = 0
            
            while True:
                action = self.select_action(state, training=True)
                next_state, reward, done, info = env.step(action)
                
                experience = Experience(state, action, reward, next_state, done)
                self.store_experience(experience)
                
                loss = self.train_step()
                
                state = next_state
                total_reward += reward
                episode_length += 1
                
                if done:
                    break
            
            final_return = (env.portfolio_values[-1] / env.initial_cash - 1) * 100
            episode_rewards.append(total_reward)
            episode_lengths.append(episode_length)
            portfolio_returns.append(final_return)
            
            if verbose and (episode + 1) % 10 == 0:
                avg_reward = np.mean(episode_rewards[-10:])
                avg_return = np.mean(portfolio_returns[-10:])
                logger.info(f"Episode {episode+1}: avg_reward={avg_reward:.2f}, avg_return={avg_return:.2f}%")
        
        return {
            'episode_rewards': episode_rewards,
            'episode_lengths': episode_lengths,
            'portfolio_returns': portfolio_returns,
            'final_epsilon': self.epsilon,
            'avg_loss': np.mean(self.losses[-100:]) if self.losses else 0
        }
    
    def backtest(self, env: TradingEnvironment) -> Dict[str, Any]:
        """Backtest trained agent"""
        state = env.reset()
        actions_taken = []
        portfolio_values = [env.initial_cash]
        positions = [0]
        
        while True:
            action = self.select_action(state, training=False)
            next_state, reward, done, info = env.step(action)
            
            actions_taken.append(Action(action).name)
            portfolio_values.append(info['portfolio_value'])
            positions.append(info['position'])
            
            state = next_state
            
            if done:
                break
        
        # Calculate metrics
        returns = np.diff(portfolio_values) / portfolio_values[:-1]
        
        total_return = (portfolio_values[-1] / portfolio_values[0] - 1) * 100
        sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252) if np.std(returns) > 0 else 0
        
        max_dd = 0
        peak = portfolio_values[0]
        for pv in portfolio_values:
            if pv > peak:
                peak = pv
            dd = (peak - pv) / peak
            max_dd = max(max_dd, dd)
        
        # Count trades
        n_trades = sum(1 for a in actions_taken if a != 'HOLD')
        
        return {
            'total_return': total_return,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_dd * 100,
            'n_trades': n_trades,
            'final_value': portfolio_values[-1],
            'portfolio_values': portfolio_values,
            'actions': actions_taken,
            'positions': positions
        }
    
    def save(self, path: str):
        """Save model"""
        if HAS_TORCH:
            torch.save({
                'policy_net': self.policy_net.state_dict(),
                'optimizer': self.optimizer.state_dict(),
                'epsilon': self.epsilon
            }, path)
    
    def load(self, path: str):
        """Load model"""
        if HAS_TORCH:
            checkpoint = torch.load(path)
            self.policy_net.load_state_dict(checkpoint['policy_net'])
            self.optimizer.load_state_dict(checkpoint['optimizer'])
            self.epsilon = checkpoint['epsilon']


def create_trading_agent(df: pd.DataFrame, **kwargs) -> Tuple[RLTradingAgent, TradingEnvironment]:
    """Factory function to create agent and environment"""
    env = TradingEnvironment(df, **kwargs)
    state = env.reset()
    state_dim = len(state)
    
    agent = RLTradingAgent(state_dim=state_dim, **kwargs)
    
    return agent, env


# Singleton instance
_rl_agent = None
_trading_env = None

def get_rl_agent() -> Optional[RLTradingAgent]:
    return _rl_agent

def set_rl_agent(agent: RLTradingAgent, env: TradingEnvironment):
    global _rl_agent, _trading_env
    _rl_agent = agent
    _trading_env = env
