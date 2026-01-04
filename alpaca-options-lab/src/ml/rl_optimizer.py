"""
Reinforcement Learning Strategy Optimizer

Uses PPO (Proximal Policy Optimization) to optimize strategy parameters.

The RL agent learns optimal parameters by:
- State space: Portfolio Greeks, market conditions, time of day
- Action space: Strategy parameters (delta targets, profit targets, etc.)
- Reward: Risk-adjusted returns (Sharpe ratio contribution)

Usage:
    from src.ml.rl_optimizer import RLStrategyOptimizer, TradingStrategyEnv
    
    optimizer = RLStrategyOptimizer(strategy_class=IronCondor0DTE)
    optimal_params = await optimizer.train(backtest_data)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Tuple, Type
import json

import numpy as np

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Try to import optional dependencies
try:
    import gymnasium as gym
    from gymnasium import spaces
    GYM_AVAILABLE = True
except ImportError:
    try:
        import gym
        from gym import spaces
        GYM_AVAILABLE = True
    except ImportError:
        GYM_AVAILABLE = False
        gym = None
        spaces = None

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.vec_env import DummyVecEnv
    from stable_baselines3.common.callbacks import EvalCallback, BaseCallback
    SB3_AVAILABLE = True
except ImportError:
    SB3_AVAILABLE = False
    PPO = None
    DummyVecEnv = None


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class StrategyConfig:
    """Strategy configuration"""
    name: str
    parameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParameterSpace:
    """Definition of a tunable parameter"""
    name: str
    min_value: float
    max_value: float
    default: float
    description: str = ""


@dataclass
class OptimizationResult:
    """Result of RL optimization"""
    optimal_parameters: Dict[str, float]
    training_sharpe: float
    test_sharpe: float
    training_episodes: int
    convergence_step: int
    parameter_history: List[Dict[str, float]]


@dataclass
class BacktestDataRow:
    """Single row of backtest data"""
    timestamp: datetime
    portfolio_delta: float
    portfolio_gamma: float
    portfolio_theta: float
    vix: float
    spy_return_5d: float
    time_of_day_normalized: float
    avg_days_to_expiration: float
    underlying_price: float
    iv_rank: float


# =============================================================================
# TRADING STRATEGY ENVIRONMENT
# =============================================================================

class TradingStrategyEnv:
    """
    OpenAI Gym-compatible environment for strategy optimization.
    
    The RL agent learns optimal strategy parameters by trading
    in a simulated environment and receiving rewards based on
    risk-adjusted returns.
    
    State Space (7 dimensions):
    - portfolio_delta: Current portfolio delta exposure
    - portfolio_gamma: Current portfolio gamma
    - portfolio_theta: Current portfolio theta
    - vix: VIX level
    - spy_return_5d: SPY 5-day return
    - time_of_day_normalized: 0-1 (9:30=0, 16:00=1)
    - avg_days_to_expiration: Average DTE of positions
    
    Action Space (3 dimensions, normalized 0-1):
    - target_delta: Target delta for new positions (scaled to 5-35)
    - profit_target: Profit target percentage (scaled to 20-100%)
    - stop_loss: Stop loss multiplier (scaled to 1x-5x)
    
    Reward:
    - Daily Sharpe contribution with drawdown penalty
    """
    
    # Default parameter ranges
    DELTA_RANGE = (5, 35)
    PROFIT_TARGET_RANGE = (0.20, 1.00)
    STOP_LOSS_RANGE = (1.0, 5.0)
    
    def __init__(
        self,
        backtest_data: List[BacktestDataRow],
        strategy_simulator: Optional[Callable] = None,
        initial_capital: float = 100000.0,
        commission_per_contract: float = 0.65,
    ):
        """
        Initialize trading environment.
        
        Args:
            backtest_data: Historical data for simulation
            strategy_simulator: Function to simulate strategy returns
            initial_capital: Starting capital
            commission_per_contract: Commission per contract
        """
        if not GYM_AVAILABLE:
            raise ImportError("gymnasium or gym is required for RL optimization")
        
        self.backtest_data = backtest_data
        self.strategy_simulator = strategy_simulator
        self.initial_capital = initial_capital
        self.commission = commission_per_contract
        
        self.current_step = 0
        self.portfolio_value = initial_capital
        self.starting_value = initial_capital
        self.daily_returns: List[float] = []
        
        # Define spaces
        self.observation_space = spaces.Box(
            low=np.array([-100, -1, -500, 10, -0.10, 0, 0]),
            high=np.array([100, 1, 0, 80, 0.10, 1, 45]),
            dtype=np.float32,
        )
        
        self.action_space = spaces.Box(
            low=np.array([0, 0, 0]),
            high=np.array([1, 1, 1]),
            dtype=np.float32,
        )
        
        logger.info(
            "trading_env_initialized",
            data_length=len(backtest_data),
            initial_capital=initial_capital,
        )
    
    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None,
    ) -> Tuple[np.ndarray, Dict]:
        """
        Reset environment to start of backtest data.
        
        Returns:
            Initial observation and info dict
        """
        self.current_step = 0
        self.portfolio_value = self.initial_capital
        self.daily_returns = []
        
        observation = self._get_observation()
        info = {'step': 0, 'portfolio_value': self.portfolio_value}
        
        return observation, info
    
    def step(self, action: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Execute one trading day with given parameters.
        
        Args:
            action: Normalized parameters [0, 1]
            
        Returns:
            observation, reward, terminated, truncated, info
        """
        # Scale actions to actual parameter ranges
        target_delta = action[0] * (self.DELTA_RANGE[1] - self.DELTA_RANGE[0]) + self.DELTA_RANGE[0]
        profit_target = action[1] * (self.PROFIT_TARGET_RANGE[1] - self.PROFIT_TARGET_RANGE[0]) + self.PROFIT_TARGET_RANGE[0]
        stop_loss = action[2] * (self.STOP_LOSS_RANGE[1] - self.STOP_LOSS_RANGE[0]) + self.STOP_LOSS_RANGE[0]
        
        # Create strategy config
        config = StrategyConfig(
            name='rl_optimized',
            parameters={
                'target_delta': target_delta,
                'profit_target': profit_target,
                'stop_loss': stop_loss,
            },
        )
        
        # Simulate trading day
        daily_pnl = self._simulate_day(config)
        
        # Update portfolio
        prev_value = self.portfolio_value
        self.portfolio_value += daily_pnl
        daily_return = daily_pnl / prev_value if prev_value > 0 else 0
        self.daily_returns.append(daily_return)
        
        # Calculate reward (Sharpe contribution)
        reward = self._calculate_reward(daily_return)
        
        # Move to next day
        self.current_step += 1
        terminated = self.current_step >= len(self.backtest_data)
        truncated = False
        
        if self.portfolio_value <= 0:
            terminated = True
            reward = -10.0  # Heavy penalty for blowing up
        
        observation = self._get_observation()
        
        info = {
            'step': self.current_step,
            'daily_pnl': daily_pnl,
            'daily_return': daily_return,
            'portfolio_value': self.portfolio_value,
            'parameters': {
                'target_delta': target_delta,
                'profit_target': profit_target,
                'stop_loss': stop_loss,
            },
        }
        
        return observation, reward, terminated, truncated, info
    
    def _get_observation(self) -> np.ndarray:
        """Get current state observation"""
        if self.current_step >= len(self.backtest_data):
            return np.zeros(self.observation_space.shape[0], dtype=np.float32)
        
        row = self.backtest_data[self.current_step]
        
        return np.array([
            row.portfolio_delta,
            row.portfolio_gamma,
            row.portfolio_theta,
            row.vix,
            row.spy_return_5d,
            row.time_of_day_normalized,
            row.avg_days_to_expiration,
        ], dtype=np.float32)
    
    def _simulate_day(self, config: StrategyConfig) -> float:
        """
        Simulate one day of trading with given parameters.
        
        Args:
            config: Strategy configuration
            
        Returns:
            Daily P&L
        """
        if self.strategy_simulator:
            row = self.backtest_data[self.current_step]
            return self.strategy_simulator(config, row)
        
        # Default simulation model (simplified)
        row = self.backtest_data[self.current_step]
        
        # Base P&L from theta decay (sell premium strategy)
        theta_pnl = abs(row.portfolio_theta) * 0.5  # Capture 50% of theta
        
        # Adjust for market conditions
        vix_adjustment = 1.0 + (row.vix - 20) / 100  # Higher VIX = more premium
        
        # Delta risk from market moves
        delta_risk = row.portfolio_delta * row.spy_return_5d * row.underlying_price
        
        # Gamma risk (convexity)
        gamma_risk = 0.5 * row.portfolio_gamma * (row.spy_return_5d * row.underlying_price) ** 2
        
        # Parameters affect outcome
        target_delta = config.parameters.get('target_delta', 20)
        profit_target = config.parameters.get('profit_target', 0.5)
        stop_loss = config.parameters.get('stop_loss', 2.0)
        
        # Higher delta = more risk but more premium
        premium_multiplier = target_delta / 20.0
        
        # Base daily P&L
        base_pnl = theta_pnl * vix_adjustment * premium_multiplier
        
        # Apply profit target (early exit reduces average)
        if np.random.random() < profit_target:
            base_pnl *= 0.8  # Take profit early
        
        # Apply stop loss effect
        if abs(delta_risk) > base_pnl * stop_loss:
            # Stop loss triggered
            base_pnl = -base_pnl * stop_loss
        else:
            base_pnl = base_pnl - delta_risk * 0.1 - gamma_risk * 0.05
        
        # Commission impact
        base_pnl -= self.commission * 2  # Entry and exit
        
        # Add some noise
        noise = np.random.normal(0, abs(base_pnl) * 0.1)
        
        return base_pnl + noise
    
    def _calculate_reward(self, daily_return: float) -> float:
        """
        Calculate reward for RL agent.
        
        Uses Sharpe-like metric with drawdown penalty.
        """
        if len(self.daily_returns) < 2:
            return daily_return * 100  # Scale up for early training
        
        # Rolling Sharpe contribution
        returns = np.array(self.daily_returns[-20:])  # Last 20 days
        mean_return = np.mean(returns)
        std_return = np.std(returns, ddof=1) if len(returns) > 1 else 1e-6
        
        sharpe_contribution = (daily_return - mean_return) / (std_return + 1e-6)
        
        # Drawdown penalty
        peak = max(self.daily_returns) if self.daily_returns else 0
        current_drawdown = (peak - daily_return) / (abs(peak) + 1e-6)
        drawdown_penalty = max(0, current_drawdown - 0.05) * 5  # Penalty for >5% drawdown
        
        # Large loss penalty
        if daily_return < -0.05:
            sharpe_contribution -= 2.0
        
        reward = sharpe_contribution - drawdown_penalty
        
        return reward
    
    @property
    def portfolio_volatility(self) -> float:
        """Calculate portfolio volatility from daily returns"""
        if len(self.daily_returns) < 2:
            return 0.01
        return np.std(self.daily_returns, ddof=1)


# =============================================================================
# RL STRATEGY OPTIMIZER
# =============================================================================

class RLStrategyOptimizer:
    """
    Reinforcement Learning-based strategy parameter optimizer.
    
    Uses PPO (Proximal Policy Optimization) to find optimal
    strategy parameters through simulated trading.
    
    Attributes:
        strategy_class: Strategy class to optimize
        parameter_space: Tunable parameters
        total_timesteps: Training timesteps
    """
    
    DEFAULT_TIMESTEPS = 100_000
    DEFAULT_EVAL_FREQ = 10_000
    
    def __init__(
        self,
        strategy_class: Optional[Type] = None,
        parameter_space: Optional[List[ParameterSpace]] = None,
        total_timesteps: int = DEFAULT_TIMESTEPS,
        learning_rate: float = 3e-4,
        n_steps: int = 2048,
        batch_size: int = 64,
        n_epochs: int = 10,
        gamma: float = 0.99,
        verbose: int = 1,
    ):
        """
        Initialize RL optimizer.
        
        Args:
            strategy_class: Strategy class to optimize
            parameter_space: List of tunable parameters
            total_timesteps: Total training timesteps
            learning_rate: PPO learning rate
            n_steps: Steps per update
            batch_size: Mini-batch size
            n_epochs: Number of epochs per update
            gamma: Discount factor
            verbose: Verbosity level
        """
        if not SB3_AVAILABLE:
            raise ImportError("stable-baselines3 is required for RL optimization")
        
        self.strategy_class = strategy_class
        self.parameter_space = parameter_space or self._default_parameter_space()
        self.total_timesteps = total_timesteps
        
        # PPO hyperparameters
        self.learning_rate = learning_rate
        self.n_steps = n_steps
        self.batch_size = batch_size
        self.n_epochs = n_epochs
        self.gamma = gamma
        self.verbose = verbose
        
        self.model: Optional[PPO] = None
        self.env: Optional[TradingStrategyEnv] = None
        self.parameter_history: List[Dict[str, float]] = []
        
        logger.info(
            "rl_optimizer_initialized",
            timesteps=total_timesteps,
            learning_rate=learning_rate,
        )
    
    def _default_parameter_space(self) -> List[ParameterSpace]:
        """Default parameter space for options strategies"""
        return [
            ParameterSpace(
                name='target_delta',
                min_value=5,
                max_value=35,
                default=20,
                description='Target delta for short strikes',
            ),
            ParameterSpace(
                name='profit_target',
                min_value=0.20,
                max_value=1.00,
                default=0.50,
                description='Profit target as percentage of max profit',
            ),
            ParameterSpace(
                name='stop_loss',
                min_value=1.0,
                max_value=5.0,
                default=2.0,
                description='Stop loss as multiple of credit received',
            ),
        ]
    
    async def train(
        self,
        training_data: List[BacktestDataRow],
        test_data: Optional[List[BacktestDataRow]] = None,
        strategy_simulator: Optional[Callable] = None,
    ) -> OptimizationResult:
        """
        Train RL agent to optimize strategy parameters.
        
        Args:
            training_data: Historical data for training
            test_data: Optional holdout data for evaluation
            strategy_simulator: Custom strategy simulation function
            
        Returns:
            OptimizationResult with optimal parameters
        """
        logger.info(
            "starting_rl_training",
            training_samples=len(training_data),
            test_samples=len(test_data) if test_data else 0,
            timesteps=self.total_timesteps,
        )
        
        # Create training environment
        self.env = TradingStrategyEnv(
            backtest_data=training_data,
            strategy_simulator=strategy_simulator,
        )
        
        # Wrap for stable-baselines
        vec_env = DummyVecEnv([lambda: self.env])
        
        # Create PPO model
        self.model = PPO(
            "MlpPolicy",
            vec_env,
            learning_rate=self.learning_rate,
            n_steps=self.n_steps,
            batch_size=self.batch_size,
            n_epochs=self.n_epochs,
            gamma=self.gamma,
            verbose=self.verbose,
        )
        
        # Create callback to track parameters
        callback = ParameterTrackingCallback(self.parameter_history, self.env)
        
        # Train
        self.model.learn(
            total_timesteps=self.total_timesteps,
            callback=callback,
        )
        
        # Evaluate on training data
        training_sharpe = self._evaluate_policy(training_data, strategy_simulator)
        
        # Evaluate on test data
        test_sharpe = 0.0
        if test_data:
            test_sharpe = self._evaluate_policy(test_data, strategy_simulator)
        
        # Extract optimal parameters (most frequent good actions)
        optimal_params = self._extract_optimal_parameters()
        
        result = OptimizationResult(
            optimal_parameters=optimal_params,
            training_sharpe=training_sharpe,
            test_sharpe=test_sharpe,
            training_episodes=self.total_timesteps // len(training_data),
            convergence_step=len(self.parameter_history),
            parameter_history=self.parameter_history,
        )
        
        logger.info(
            "rl_training_complete",
            training_sharpe=training_sharpe,
            test_sharpe=test_sharpe,
            optimal_params=optimal_params,
        )
        
        return result
    
    def _evaluate_policy(
        self,
        data: List[BacktestDataRow],
        strategy_simulator: Optional[Callable] = None,
    ) -> float:
        """Evaluate trained policy on data"""
        if self.model is None:
            return 0.0
        
        env = TradingStrategyEnv(
            backtest_data=data,
            strategy_simulator=strategy_simulator,
        )
        
        obs, _ = env.reset()
        total_reward = 0.0
        done = False
        
        while not done:
            action, _ = self.model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward
            done = terminated or truncated
        
        # Calculate annualized Sharpe
        if len(env.daily_returns) > 1:
            returns = np.array(env.daily_returns)
            sharpe = (np.mean(returns) / (np.std(returns) + 1e-6)) * np.sqrt(252)
        else:
            sharpe = 0.0
        
        return sharpe
    
    def _extract_optimal_parameters(self) -> Dict[str, float]:
        """Extract optimal parameters from training history"""
        if not self.parameter_history:
            return {
                'target_delta': 20.0,
                'profit_target': 0.50,
                'stop_loss': 2.0,
            }
        
        # Use parameters from best performing episodes
        # (simplified - could use more sophisticated selection)
        recent_params = self.parameter_history[-100:]
        
        optimal = {}
        for key in ['target_delta', 'profit_target', 'stop_loss']:
            values = [p.get(key, 0) for p in recent_params if key in p]
            if values:
                optimal[key] = np.median(values)
            else:
                optimal[key] = self.parameter_space[0].default
        
        return optimal
    
    def save_model(self, path: str) -> None:
        """Save trained model to disk"""
        if self.model:
            self.model.save(path)
            logger.info("model_saved", path=path)
    
    def load_model(self, path: str) -> None:
        """Load trained model from disk"""
        self.model = PPO.load(path)
        logger.info("model_loaded", path=path)
    
    def predict_parameters(
        self,
        observation: np.ndarray,
    ) -> Dict[str, float]:
        """
        Predict optimal parameters for current market state.
        
        Args:
            observation: Current market state
            
        Returns:
            Recommended parameters
        """
        if self.model is None:
            raise ValueError("Model not trained - call train() first")
        
        action, _ = self.model.predict(observation, deterministic=True)
        
        # Scale actions to actual ranges
        target_delta = action[0] * 30 + 5
        profit_target = action[1] * 0.80 + 0.20
        stop_loss = action[2] * 4.0 + 1.0
        
        return {
            'target_delta': float(target_delta),
            'profit_target': float(profit_target),
            'stop_loss': float(stop_loss),
        }


# =============================================================================
# CALLBACK FOR TRACKING
# =============================================================================

class ParameterTrackingCallback:
    """Callback to track parameters during training"""
    
    def __init__(
        self,
        parameter_history: List[Dict[str, float]],
        env: TradingStrategyEnv,
    ):
        self.parameter_history = parameter_history
        self.env = env
    
    def __call__(self, locals_dict: Dict, globals_dict: Dict) -> bool:
        # Track parameters from recent steps
        if 'infos' in locals_dict:
            for info in locals_dict['infos']:
                if 'parameters' in info:
                    self.parameter_history.append(info['parameters'])
        
        return True  # Continue training


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def create_backtest_data_from_df(df) -> List[BacktestDataRow]:
    """Convert pandas DataFrame to BacktestDataRow list"""
    rows = []
    for _, row in df.iterrows():
        rows.append(BacktestDataRow(
            timestamp=row.get('timestamp', datetime.now()),
            portfolio_delta=row.get('portfolio_delta', 0),
            portfolio_gamma=row.get('portfolio_gamma', 0),
            portfolio_theta=row.get('portfolio_theta', 0),
            vix=row.get('vix', 20),
            spy_return_5d=row.get('spy_return_5d', 0),
            time_of_day_normalized=row.get('time_of_day_normalized', 0.5),
            avg_days_to_expiration=row.get('avg_days_to_expiration', 7),
            underlying_price=row.get('underlying_price', 500),
            iv_rank=row.get('iv_rank', 50),
        ))
    return rows


async def quick_optimize(
    backtest_data: List[BacktestDataRow],
    timesteps: int = 50000,
) -> Dict[str, float]:
    """
    Quick optimization with default settings.
    
    Args:
        backtest_data: Historical data
        timesteps: Training timesteps
        
    Returns:
        Optimal parameters
    """
    optimizer = RLStrategyOptimizer(total_timesteps=timesteps, verbose=0)
    result = await optimizer.train(backtest_data)
    return result.optimal_parameters
