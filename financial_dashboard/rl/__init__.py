"""
RL Module - Reinforcement Learning for Trading
==============================================

Components:
- StockTradingEnv: Gymnasium environment for stock trading
- PPOAgent: Proximal Policy Optimization agent
"""

from .trading_env import StockTradingEnv, create_trading_env
from .ppo_agent import PPOAgent, RolloutBuffer, train_ppo, evaluate_agent

# Check availability
try:
    from .ppo_agent import ActorCritic, TORCH_AVAILABLE
except ImportError:
    TORCH_AVAILABLE = False
    ActorCritic = None

__all__ = [
    'StockTradingEnv',
    'create_trading_env',
    'PPOAgent',
    'RolloutBuffer',
    'train_ppo',
    'evaluate_agent',
    'ActorCritic',
    'TORCH_AVAILABLE'
]
