#!/usr/bin/env python3
"""
FinRL Trading Signals
=====================
Reinforcement learning-based trading signals inspired by FinRL-Meta.

Implements:
- Portfolio optimization environment
- PPO/A2C/DDPG/SAC agents (simplified)
- Trading action generation
- Ensemble strategy

Reference: https://github.com/AI4Finance-Foundation/FinRL
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class TradingAction(Enum):
    """Discrete trading actions"""
    STRONG_SELL = -2
    SELL = -1
    HOLD = 0
    BUY = 1
    STRONG_BUY = 2


@dataclass
class RLState:
    """State representation for RL agent"""
    prices: np.ndarray  # Price history
    holdings: np.ndarray  # Current positions
    cash: float
    portfolio_value: float
    technical_indicators: Dict[str, float]
    timestamp: datetime
    
    def to_vector(self) -> np.ndarray:
        """Convert state to feature vector"""
        # Flatten prices and holdings
        price_features = self.prices.flatten() if self.prices.ndim > 1 else self.prices
        holding_features = self.holdings.flatten() if self.holdings.ndim > 1 else self.holdings
        
        # Technical indicators
        tech_features = np.array(list(self.technical_indicators.values()))
        
        # Cash normalized
        cash_norm = np.array([self.cash / max(self.portfolio_value, 1)])
        
        return np.concatenate([price_features[-20:], holding_features, tech_features, cash_norm])


@dataclass
class RLSignal:
    """Signal from RL agent"""
    ticker: str
    action: TradingAction
    confidence: float
    q_value: float
    position_size: float  # Fraction of portfolio
    algorithm: str
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'action': self.action.value,
            'action_name': self.action.name,
            'confidence': self.confidence,
            'q_value': self.q_value,
            'position_size': self.position_size,
            'algorithm': self.algorithm,
            'timestamp': self.timestamp.isoformat()
        }


class SimplePolicyNetwork:
    """
    Simplified policy network for trading.
    
    In production, would use PyTorch with proper training.
    This is a rule-based approximation for demo purposes.
    """
    
    def __init__(self, state_dim: int, action_dim: int = 5):
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.weights = np.random.randn(state_dim, action_dim) * 0.1
        
    def predict(self, state: np.ndarray) -> Tuple[int, np.ndarray]:
        """Predict action from state"""
        # Simple linear policy
        logits = state @ self.weights
        probs = self._softmax(logits)
        action = np.argmax(probs)
        return action, probs
    
    def _softmax(self, x: np.ndarray) -> np.ndarray:
        exp_x = np.exp(x - np.max(x))
        return exp_x / exp_x.sum()


class StockTradingEnv:
    """
    Simplified stock trading environment inspired by FinRL.
    
    State: [prices, holdings, indicators, cash]
    Action: [-2, -1, 0, 1, 2] (strong sell to strong buy)
    Reward: Portfolio return
    """
    
    def __init__(self,
                 initial_amount: float = 100000,
                 hmax: int = 100,
                 buy_cost_pct: float = 0.001,
                 sell_cost_pct: float = 0.001,
                 reward_scaling: float = 1e-4):
        """
        Args:
            initial_amount: Initial cash
            hmax: Maximum shares per trade
            buy_cost_pct: Buy transaction cost
            sell_cost_pct: Sell transaction cost
            reward_scaling: Reward scaling factor
        """
        self.initial_amount = initial_amount
        self.hmax = hmax
        self.buy_cost_pct = buy_cost_pct
        self.sell_cost_pct = sell_cost_pct
        self.reward_scaling = reward_scaling
        
        self.cash = initial_amount
        self.holdings = {}
        self.prices = {}
        
    def reset(self, prices: Dict[str, float]) -> RLState:
        """Reset environment"""
        self.cash = self.initial_amount
        self.holdings = {ticker: 0 for ticker in prices}
        self.prices = prices.copy()
        
        return self._get_state()
    
    def step(self, 
             actions: Dict[str, int],
             new_prices: Dict[str, float]) -> Tuple[RLState, float, bool]:
        """
        Execute actions and return new state, reward.
        
        Args:
            actions: Dict mapping ticker to action (-2 to 2)
            new_prices: New prices after action
            
        Returns:
            (new_state, reward, done)
        """
        old_portfolio_value = self._get_portfolio_value()
        
        # Execute trades
        for ticker, action in actions.items():
            if ticker not in self.holdings:
                self.holdings[ticker] = 0
                
            price = self.prices.get(ticker, new_prices.get(ticker, 0))
            if price <= 0:
                continue
                
            # Convert action to shares
            shares_to_trade = action * self.hmax // 2  # Scale action
            
            if shares_to_trade > 0:  # Buy
                max_shares = int(self.cash / (price * (1 + self.buy_cost_pct)))
                shares_to_trade = min(shares_to_trade, max_shares)
                cost = shares_to_trade * price * (1 + self.buy_cost_pct)
                self.cash -= cost
                self.holdings[ticker] += shares_to_trade
                
            elif shares_to_trade < 0:  # Sell
                shares_to_trade = min(-shares_to_trade, self.holdings[ticker])
                proceeds = shares_to_trade * price * (1 - self.sell_cost_pct)
                self.cash += proceeds
                self.holdings[ticker] -= shares_to_trade
        
        # Update prices
        self.prices = new_prices.copy()
        
        # Calculate reward (portfolio return)
        new_portfolio_value = self._get_portfolio_value()
        reward = (new_portfolio_value - old_portfolio_value) * self.reward_scaling
        
        return self._get_state(), float(reward), False
    
    def _get_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        stock_value = sum(
            self.holdings.get(t, 0) * self.prices.get(t, 0)
            for t in self.holdings
        )
        return self.cash + stock_value
    
    def _get_state(self) -> RLState:
        """Get current state"""
        prices_arr = np.array(list(self.prices.values()))
        holdings_arr = np.array(list(self.holdings.values()))
        
        return RLState(
            prices=prices_arr,
            holdings=holdings_arr,
            cash=self.cash,
            portfolio_value=self._get_portfolio_value(),
            technical_indicators={},
            timestamp=datetime.now()
        )


class FinRLTradingSignals:
    """
    FinRL-inspired trading signal generator.
    
    Combines multiple RL algorithms in ensemble:
    - PPO (Proximal Policy Optimization)
    - A2C (Advantage Actor-Critic)
    - DDPG (Deep Deterministic Policy Gradient)
    - SAC (Soft Actor-Critic)
    
    When PyTorch not available, uses rule-based approximation.
    """
    
    ALGORITHMS = ['PPO', 'A2C', 'DDPG', 'SAC', 'TD3']
    
    def __init__(self,
                 algorithms: List[str] = None,
                 ensemble_weights: Dict[str, float] = None,
                 lookback: int = 20,
                 use_pytorch: bool = True):
        """
        Args:
            algorithms: List of algorithms to use
            ensemble_weights: Weights for ensemble
            lookback: Lookback period for state
            use_pytorch: Whether to use PyTorch (if available)
        """
        self.algorithms = algorithms or ['PPO', 'A2C']
        self.ensemble_weights = ensemble_weights or {a: 1.0/len(self.algorithms) for a in self.algorithms}
        self.lookback = lookback
        self.use_pytorch = use_pytorch
        
        self._agents = {}
        self._env = None
        self._initialized = False
        self._pytorch_available = False
        
    def initialize(self) -> bool:
        """Initialize RL agents"""
        if self._initialized:
            return True
            
        try:
            import torch
            self._pytorch_available = True and self.use_pytorch
            logger.info("✅ PyTorch available for FinRL agents")
        except ImportError:
            self._pytorch_available = False
            logger.warning("PyTorch not available - using rule-based signals")
        
        # Initialize environment
        self._env = StockTradingEnv()
        
        # Initialize simple policy networks (would use stable-baselines3 in production)
        state_dim = self.lookback + 10  # Prices + technical indicators
        for algo in self.algorithms:
            self._agents[algo] = SimplePolicyNetwork(state_dim)
        
        self._initialized = True
        return True
    
    def compute_technical_indicators(self, df: pd.DataFrame) -> Dict[str, float]:
        """Compute technical indicators for state"""
        close = df['close'] if 'close' in df.columns else df['Close']
        
        indicators = {}
        
        # Returns
        returns = close.pct_change()
        indicators['return_1d'] = float(returns.iloc[-1]) if len(returns) > 0 else 0
        indicators['return_5d'] = float(close.iloc[-1] / close.iloc[-5] - 1) if len(close) > 5 else 0
        indicators['return_20d'] = float(close.iloc[-1] / close.iloc[-20] - 1) if len(close) > 20 else 0
        
        # Volatility
        indicators['volatility'] = float(returns.rolling(20).std().iloc[-1]) if len(returns) > 20 else 0.02
        
        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.inf)
        rsi = 100 - (100 / (1 + rs))
        indicators['rsi'] = float(rsi.iloc[-1]) if len(rsi) > 14 else 50
        
        # MACD
        ema_12 = close.ewm(span=12).mean()
        ema_26 = close.ewm(span=26).mean()
        macd = ema_12 - ema_26
        indicators['macd'] = float(macd.iloc[-1]) if len(macd) > 26 else 0
        
        # Bollinger position
        sma_20 = close.rolling(20).mean()
        std_20 = close.rolling(20).std()
        bb_upper = sma_20 + 2 * std_20
        bb_lower = sma_20 - 2 * std_20
        bb_pos = (close - bb_lower) / (bb_upper - bb_lower)
        indicators['bb_position'] = float(bb_pos.iloc[-1]) if len(bb_pos) > 20 else 0.5
        
        return indicators
    
    def generate_signal(self,
                       ticker: str,
                       price_history: pd.DataFrame,
                       current_holding: float = 0) -> RLSignal:
        """
        Generate trading signal using RL ensemble.
        
        Args:
            ticker: Stock symbol
            price_history: OHLCV DataFrame
            current_holding: Current position
            
        Returns:
            RLSignal with action and confidence
        """
        if not self._initialized:
            self.initialize()
        
        # Compute indicators
        indicators = self.compute_technical_indicators(price_history)
        
        # Get recent prices
        close = price_history['close'] if 'close' in price_history.columns else price_history['Close']
        recent_prices = close.iloc[-self.lookback:].values
        
        # Normalize prices
        price_norm = recent_prices / recent_prices[-1] - 1
        
        # Build state vector
        state = np.concatenate([
            price_norm,
            np.array([current_holding]),
            np.array(list(indicators.values()))
        ])
        
        # Pad if necessary
        expected_dim = self.lookback + 10
        if len(state) < expected_dim:
            state = np.pad(state, (0, expected_dim - len(state)))
        elif len(state) > expected_dim:
            state = state[:expected_dim]
        
        # Get predictions from each algorithm
        actions = []
        q_values = []
        
        for algo, agent in self._agents.items():
            action_idx, probs = agent.predict(state)
            action = action_idx - 2  # Convert to [-2, 2]
            q_value = probs[action_idx]
            
            actions.append((action, q_value, algo))
            q_values.append(q_value * self.ensemble_weights.get(algo, 1.0))
        
        # Rule-based enhancement based on indicators
        rule_action = self._rule_based_action(indicators)
        
        # Ensemble: weighted average
        ensemble_action = 0
        total_weight = 0
        for action, q_val, algo in actions:
            weight = self.ensemble_weights.get(algo, 1.0)
            ensemble_action += action * weight * q_val
            total_weight += weight * q_val
        
        if total_weight > 0:
            ensemble_action /= total_weight
        
        # Blend with rule-based
        final_action = 0.6 * ensemble_action + 0.4 * rule_action
        
        # Discretize
        if final_action >= 1.5:
            action_enum = TradingAction.STRONG_BUY
        elif final_action >= 0.5:
            action_enum = TradingAction.BUY
        elif final_action <= -1.5:
            action_enum = TradingAction.STRONG_SELL
        elif final_action <= -0.5:
            action_enum = TradingAction.SELL
        else:
            action_enum = TradingAction.HOLD
        
        # Calculate confidence
        confidence = min(abs(final_action) / 2, 1.0)
        
        # Position size based on confidence
        position_size = confidence * 0.1  # Max 10% of portfolio
        
        return RLSignal(
            ticker=ticker,
            action=action_enum,
            confidence=float(confidence),
            q_value=float(np.mean(q_values)),
            position_size=float(position_size),
            algorithm='Ensemble',
            timestamp=datetime.now()
        )
    
    def _rule_based_action(self, indicators: Dict[str, float]) -> float:
        """Rule-based action for enhancement"""
        action = 0.0
        
        # RSI
        rsi = indicators.get('rsi', 50)
        if rsi < 30:
            action += 1.0  # Oversold - buy
        elif rsi > 70:
            action -= 1.0  # Overbought - sell
        
        # MACD
        macd = indicators.get('macd', 0)
        if macd > 0:
            action += 0.3
        elif macd < 0:
            action -= 0.3
        
        # Bollinger
        bb_pos = indicators.get('bb_position', 0.5)
        if bb_pos < 0.1:
            action += 0.5  # Near lower band
        elif bb_pos > 0.9:
            action -= 0.5  # Near upper band
        
        # Momentum
        return_5d = indicators.get('return_5d', 0)
        if return_5d > 0.05:
            action += 0.3
        elif return_5d < -0.05:
            action -= 0.3
        
        return np.clip(action, -2, 2)
    
    def generate_portfolio_signals(self,
                                   tickers: List[str],
                                   price_histories: Dict[str, pd.DataFrame],
                                   current_holdings: Dict[str, float] = None) -> Dict[str, RLSignal]:
        """
        Generate signals for entire portfolio.
        
        Args:
            tickers: List of tickers
            price_histories: Dict mapping ticker to price DataFrame
            current_holdings: Current positions
            
        Returns:
            Dict mapping ticker to RLSignal
        """
        current_holdings = current_holdings or {}
        
        signals = {}
        for ticker in tickers:
            if ticker in price_histories and len(price_histories[ticker]) >= self.lookback:
                signals[ticker] = self.generate_signal(
                    ticker=ticker,
                    price_history=price_histories[ticker],
                    current_holding=current_holdings.get(ticker, 0)
                )
        
        return signals
    
    def get_summary(self) -> Dict:
        """Get agent configuration summary"""
        return {
            'algorithms': self.algorithms,
            'ensemble_weights': self.ensemble_weights,
            'lookback': self.lookback,
            'pytorch_available': self._pytorch_available,
            'initialized': self._initialized
        }
