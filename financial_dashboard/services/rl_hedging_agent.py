"""
Reinforcement Learning Options Hedging Service
===============================================
RL-based dynamic hedging for options positions.
Uses DQN/PPO agents to learn optimal hedge ratios.

From PDF: "Machine Learning in Quantitative Finance — Project Guide"
Topic 3: Derivative Hedging Using Reinforcement Learning
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import numpy as np
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import RL libraries
try:
    import gymnasium as gym
    from gymnasium import spaces
    GYM_AVAILABLE = True
except ImportError:
    GYM_AVAILABLE = False
    logger.warning("gymnasium not available - install with: pip install gymnasium")

try:
    from stable_baselines3 import DQN, PPO
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    logger.warning("stable-baselines3 not available for RL hedging")


class HedgeAction(Enum):
    """Discrete hedging actions."""
    REDUCE_LARGE = 0   # Reduce hedge by 20%
    REDUCE_SMALL = 1   # Reduce hedge by 5%
    HOLD = 2           # No change
    INCREASE_SMALL = 3 # Increase hedge by 5%
    INCREASE_LARGE = 4 # Increase hedge by 20%


@dataclass
class OptionPosition:
    """Represents an options position."""
    symbol: str
    option_type: str  # 'call' or 'put'
    strike: float
    days_to_expiry: int
    delta: float
    gamma: float
    theta: float
    vega: float
    position_size: int  # Number of contracts
    underlying_price: float


class HedgingEnvironment:
    """
    Simulated hedging environment for RL training.
    
    State: [delta, gamma, vega, underlying_price, days_to_expiry, current_hedge_ratio]
    Action: Discrete adjustment to hedge ratio
    Reward: -|PnL change| - transaction_cost
    """
    
    def __init__(
        self,
        initial_price: float = 100.0,
        volatility: float = 0.20,
        risk_free_rate: float = 0.05,
        days_to_expiry: int = 30,
        transaction_cost: float = 0.001
    ):
        self.initial_price = initial_price
        self.volatility = volatility
        self.risk_free_rate = risk_free_rate
        self.initial_days = days_to_expiry
        self.transaction_cost = transaction_cost
        
        self.reset()
    
    def reset(self) -> np.ndarray:
        """Reset environment to initial state."""
        self.price = self.initial_price
        self.days_remaining = self.initial_days
        self.hedge_ratio = 0.5  # Start at 50% hedged
        self.pnl = 0.0
        self.step_count = 0
        
        # Simulate initial Greeks
        self.delta = 0.5
        self.gamma = 0.05
        self.vega = 0.20
        
        return self._get_state()
    
    def _get_state(self) -> np.ndarray:
        """Get current state vector."""
        return np.array([
            self.delta,
            self.gamma,
            self.vega,
            self.price / self.initial_price,  # Normalized price
            self.days_remaining / self.initial_days,  # Normalized time
            self.hedge_ratio
        ], dtype=np.float32)
    
    def _simulate_price_move(self) -> float:
        """Simulate a daily price move."""
        daily_vol = self.volatility / np.sqrt(252)
        return self.price * np.exp(
            (self.risk_free_rate / 252 - 0.5 * daily_vol**2) + 
            daily_vol * np.random.randn()
        )
    
    def _update_greeks(self):
        """Update Greeks based on new price and time."""
        # Simplified Black-Scholes delta approximation
        moneyness = self.price / self.initial_price
        time_factor = max(self.days_remaining / 30, 0.1)
        
        self.delta = 0.5 + 0.3 * (moneyness - 1) + 0.1 * np.random.randn()
        self.delta = np.clip(self.delta, 0.01, 0.99)
        
        self.gamma = 0.05 / time_factor + 0.01 * np.random.randn()
        self.gamma = max(self.gamma, 0.01)
        
        self.vega = 0.20 * time_factor + 0.02 * np.random.randn()
        self.vega = max(self.vega, 0.01)
    
    def step(self, action: int) -> Tuple[np.ndarray, float, bool, Dict]:
        """Execute one step in the environment.
        
        Args:
            action: Hedge action (0-4)
            
        Returns:
            Tuple of (next_state, reward, done, info)
        """
        # Apply action to hedge ratio
        old_hedge = self.hedge_ratio
        
        if action == HedgeAction.REDUCE_LARGE.value:
            self.hedge_ratio -= 0.20
        elif action == HedgeAction.REDUCE_SMALL.value:
            self.hedge_ratio -= 0.05
        elif action == HedgeAction.INCREASE_SMALL.value:
            self.hedge_ratio += 0.05
        elif action == HedgeAction.INCREASE_LARGE.value:
            self.hedge_ratio += 0.20
        
        self.hedge_ratio = np.clip(self.hedge_ratio, 0, 1)
        
        # Calculate transaction cost
        hedge_change = abs(self.hedge_ratio - old_hedge)
        tx_cost = hedge_change * self.transaction_cost * self.price
        
        # Simulate price move
        old_price = self.price
        self.price = self._simulate_price_move()
        price_change = self.price - old_price
        
        # Calculate hedging PnL
        # Option value change (simplified)
        option_pnl = self.delta * price_change + 0.5 * self.gamma * price_change**2
        
        # Hedge PnL (short underlying)
        hedge_pnl = -self.hedge_ratio * price_change
        
        # Net PnL
        net_pnl = option_pnl + hedge_pnl
        
        # Reward: penalize large swings and transaction costs
        reward = -abs(net_pnl) - tx_cost - 0.001 * abs(self.hedge_ratio - self.delta)
        
        self.pnl += net_pnl
        
        # Update Greeks and time
        self._update_greeks()
        self.days_remaining -= 1
        self.step_count += 1
        
        # Episode ends when option expires or max steps
        done = self.days_remaining <= 0 or self.step_count >= 50
        
        info = {
            "pnl": self.pnl,
            "hedge_ratio": self.hedge_ratio,
            "delta": self.delta,
            "price": self.price
        }
        
        return self._get_state(), reward, done, info


class RLHedgingAgent:
    """RL agent for dynamic options hedging."""
    
    def __init__(self):
        self.env = HedgingEnvironment()
        self.model = None
        self.is_trained = False
    
    def _rule_based_action(self, state: np.ndarray) -> int:
        """Simple rule-based action selection (fallback)."""
        delta = state[0]
        hedge_ratio = state[5]
        
        # Target hedge ratio based on delta
        target_hedge = delta
        diff = target_hedge - hedge_ratio
        
        if diff > 0.15:
            return HedgeAction.INCREASE_LARGE.value
        elif diff > 0.03:
            return HedgeAction.INCREASE_SMALL.value
        elif diff < -0.15:
            return HedgeAction.REDUCE_LARGE.value
        elif diff < -0.03:
            return HedgeAction.REDUCE_SMALL.value
        else:
            return HedgeAction.HOLD.value
    
    def get_hedge_recommendation(
        self,
        position: OptionPosition
    ) -> Dict:
        """Get hedge recommendation for an options position.
        
        Args:
            position: Current options position
            
        Returns:
            Dict with recommendation
        """
        # Build state from position
        state = np.array([
            position.delta,
            position.gamma,
            position.vega,
            position.underlying_price / position.strike,
            position.days_to_expiry / 30,
            0.5  # Assume starting at 50% hedged
        ], dtype=np.float32)
        
        # Get action
        if self.model and self.is_trained:
            action, _ = self.model.predict(state)
        else:
            action = self._rule_based_action(state)
        
        # Convert action to recommendation
        action_map = {
            0: ("REDUCE", 0.20, "Reduce hedge by 20%"),
            1: ("REDUCE", 0.05, "Reduce hedge by 5%"),
            2: ("HOLD", 0.00, "Maintain current hedge"),
            3: ("INCREASE", 0.05, "Increase hedge by 5%"),
            4: ("INCREASE", 0.20, "Increase hedge by 20%"),
        }
        
        direction, magnitude, description = action_map[int(action)]
        
        # Calculate suggested position
        target_hedge = position.delta  # Delta-neutral target
        hedge_shares = int(target_hedge * position.position_size * 100)
        
        return {
            "action": direction,
            "magnitude": magnitude,
            "description": description,
            "current_delta": position.delta,
            "suggested_hedge_ratio": target_hedge,
            "hedge_shares": hedge_shares,
            "model": "rule-based" if not self.is_trained else "rl-trained",
            "timestamp": datetime.now().isoformat()
        }
    
    def simulate_hedge_performance(
        self,
        position: OptionPosition,
        num_simulations: int = 100
    ) -> Dict:
        """Simulate hedging performance.
        
        Args:
            position: Options position
            num_simulations: Number of simulations
            
        Returns:
            Performance statistics
        """
        pnls = []
        
        for _ in range(num_simulations):
            self.env.reset()
            self.env.delta = position.delta
            self.env.days_remaining = position.days_to_expiry
            
            total_pnl = 0
            state = self.env._get_state()
            
            while self.env.days_remaining > 0:
                action = self._rule_based_action(state)
                state, reward, done, info = self.env.step(action)
                total_pnl = info["pnl"]
                if done:
                    break
            
            pnls.append(total_pnl)
        
        pnls = np.array(pnls)
        
        return {
            "mean_pnl": float(np.mean(pnls)),
            "std_pnl": float(np.std(pnls)),
            "min_pnl": float(np.min(pnls)),
            "max_pnl": float(np.max(pnls)),
            "sharpe": float(np.mean(pnls) / np.std(pnls)) if np.std(pnls) > 0 else 0,
            "num_simulations": num_simulations
        }


# Module-level singleton
_hedging_agent: Optional[RLHedgingAgent] = None


def get_hedging_agent() -> RLHedgingAgent:
    """Get or create hedging agent singleton."""
    global _hedging_agent
    if _hedging_agent is None:
        _hedging_agent = RLHedgingAgent()
    return _hedging_agent


def get_hedge_recommendation(
    symbol: str,
    delta: float,
    gamma: float,
    vega: float,
    days_to_expiry: int,
    underlying_price: float,
    strike: float,
    position_size: int = 1,
    option_type: str = "call"
) -> Dict:
    """Convenience function to get hedge recommendation.
    
    Returns:
        Hedge recommendation dict
    """
    position = OptionPosition(
        symbol=symbol,
        option_type=option_type,
        strike=strike,
        days_to_expiry=days_to_expiry,
        delta=delta,
        gamma=gamma,
        theta=0.0,
        vega=vega,
        position_size=position_size,
        underlying_price=underlying_price
    )
    
    agent = get_hedging_agent()
    return agent.get_hedge_recommendation(position)
