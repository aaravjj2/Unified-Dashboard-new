"""
Stock Trading Environment - Gymnasium Environment for RL Trading
=================================================================

Based on AI4Finance-Foundation/FinRL and TensorTrade patterns:
- Multi-asset portfolio management
- Transaction costs modeling
- Risk-adjusted rewards
- Position limits
- Technical indicator state
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
import logging

# Try to import gymnasium (preferred) or gym (fallback)
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

logger = logging.getLogger(__name__)


@dataclass
class TradeRecord:
    """Record of a trade execution."""
    timestamp: int
    symbol_idx: int
    action: str
    shares: float
    price: float
    cost: float
    portfolio_value: float


class StockTradingEnv:
    """
    Gymnasium environment for stock trading.
    
    Based on FinRL's StockTradingEnv with improvements:
    - Multi-asset portfolio management
    - Transaction costs modeling
    - Risk-adjusted rewards (Sharpe-like)
    - Position limits
    - Turbulence-based risk management
    
    State Space:
        [cash, stock_prices, holdings, tech_indicators]
        
    Action Space:
        Continuous [-1, 1] for each stock representing position change
        -1 = max sell, 0 = hold, 1 = max buy
    """
    
    # Gym metadata
    metadata = {'render_modes': ['human', 'rgb_array']}
    
    def __init__(
        self,
        df: pd.DataFrame,
        stock_dim: int = 1,
        hmax: int = 100,
        initial_amount: float = 1_000_000,
        transaction_cost_pct: float = 0.001,
        reward_scaling: float = 1e-4,
        state_space: int = None,
        tech_indicator_list: List[str] = None,
        turbulence_threshold: float = None,
        make_plots: bool = False,
        print_verbosity: int = 0,
        risk_free_rate: float = 0.0,
        **kwargs
    ):
        """
        Initialize trading environment.
        
        Args:
            df: DataFrame with OHLCV and technical indicators
            stock_dim: Number of stocks to trade
            hmax: Maximum shares per trade
            initial_amount: Starting cash
            transaction_cost_pct: Transaction cost as percentage
            reward_scaling: Scale factor for rewards
            state_space: Override state space dimension
            tech_indicator_list: List of technical indicator columns
            turbulence_threshold: Threshold for risk management
            make_plots: Whether to generate plots
            print_verbosity: Logging verbosity level
            risk_free_rate: Annual risk-free rate for Sharpe calculation
        """
        if not GYM_AVAILABLE:
            raise ImportError("gymnasium or gym package is required")
        
        self.df = df
        self.stock_dim = stock_dim
        self.hmax = hmax
        self.initial_amount = initial_amount
        self.transaction_cost_pct = transaction_cost_pct
        self.reward_scaling = reward_scaling
        self.make_plots = make_plots
        self.print_verbosity = print_verbosity
        self.risk_free_rate = risk_free_rate
        
        # Tech indicators
        self.tech_indicator_list = tech_indicator_list or []
        
        # State space dimensions
        # State: cash (1) + prices (stock_dim) + holdings (stock_dim) + tech_indicators
        n_tech = len(self.tech_indicator_list) * stock_dim
        self.state_space_dim = state_space or (1 + stock_dim + stock_dim + n_tech)
        
        # Define spaces
        self.action_space = spaces.Box(
            low=-1.0,
            high=1.0,
            shape=(stock_dim,),
            dtype=np.float32
        )
        
        self.observation_space = spaces.Box(
            low=-np.inf,
            high=np.inf,
            shape=(self.state_space_dim,),
            dtype=np.float32
        )
        
        # Risk management
        self.turbulence_threshold = turbulence_threshold
        
        # Episode state
        self.day = 0
        self.terminal = False
        self.data = None
        
        # Portfolio state
        self.cash = initial_amount
        self.holdings = np.zeros(stock_dim, dtype=np.float32)
        self.state = None
        
        # Tracking
        self.asset_memory = [initial_amount]
        self.rewards_memory = []
        self.actions_memory = []
        self.trades = 0
        self.trade_records: List[TradeRecord] = []
        
        # Performance tracking
        self.portfolio_return_memory = []
        self.date_memory = []
        
        # Prepare data index
        if isinstance(df.index, pd.DatetimeIndex):
            self.dates = df.index.unique()
        elif 'date' in df.columns:
            self.dates = df['date'].unique()
        else:
            self.dates = np.arange(len(df))
    
    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict] = None
    ) -> Tuple[np.ndarray, Dict]:
        """
        Reset environment to initial state.
        
        Args:
            seed: Random seed
            options: Additional options
            
        Returns:
            Initial state and info dict
        """
        # Set seed if provided
        if seed is not None:
            np.random.seed(seed)
        
        self.day = 0
        self.terminal = False
        self.trades = 0
        
        # Reset portfolio
        self.cash = self.initial_amount
        self.holdings = np.zeros(self.stock_dim, dtype=np.float32)
        
        # Reset tracking
        self.asset_memory = [self.initial_amount]
        self.rewards_memory = []
        self.actions_memory = []
        self.trade_records = []
        self.portfolio_return_memory = []
        self.date_memory = []
        
        # Get initial data
        self.data = self._get_data_for_day(self.day)
        
        # Construct state
        self.state = self._get_state()
        
        return self.state, self._get_info()
    
    def step(self, actions: np.ndarray) -> Tuple[np.ndarray, float, bool, bool, Dict]:
        """
        Execute one step in the environment.
        
        Args:
            actions: Array of actions for each stock [-1, 1]
            
        Returns:
            Tuple of (state, reward, terminated, truncated, info)
        """
        # Check terminal
        self.terminal = self.day >= len(self.dates) - 1
        
        if self.terminal:
            return self.state, 0.0, True, False, self._get_info()
        
        # Record beginning value
        begin_total_asset = self._get_total_asset()
        
        # Execute trades
        actions = np.clip(actions, -1, 1)
        self._execute_trades(actions)
        
        # Move to next day
        self.day += 1
        self.data = self._get_data_for_day(self.day)
        
        # Get new state
        self.state = self._get_state()
        
        # Calculate reward
        end_total_asset = self._get_total_asset()
        reward = self._compute_reward(begin_total_asset, end_total_asset)
        
        # Track
        self.rewards_memory.append(reward)
        self.actions_memory.append(actions.copy())
        self.asset_memory.append(end_total_asset)
        
        # Track return
        daily_return = (end_total_asset - begin_total_asset) / begin_total_asset
        self.portfolio_return_memory.append(daily_return)
        
        # Check terminal
        self.terminal = self.day >= len(self.dates) - 1
        
        return self.state, reward, self.terminal, False, self._get_info()
    
    def _get_data_for_day(self, day: int) -> pd.DataFrame:
        """Get data for a specific day."""
        if day >= len(self.dates):
            day = len(self.dates) - 1
        
        date = self.dates[day]
        
        if isinstance(self.df.index, pd.DatetimeIndex):
            data = self.df.loc[date]
        elif 'date' in self.df.columns:
            data = self.df[self.df['date'] == date]
        else:
            data = self.df.iloc[[day]]
        
        # Ensure DataFrame format
        if isinstance(data, pd.Series):
            data = data.to_frame().T
        
        return data
    
    def _get_state(self) -> np.ndarray:
        """Construct state vector."""
        state = []
        
        # Cash (normalized)
        state.append(self.cash / self.initial_amount)
        
        # Stock prices (normalized by first price)
        prices = self._get_prices()
        initial_price = prices[0] if len(prices) > 0 else 1.0
        state.extend(prices / (initial_price + 1e-10))
        
        # Holdings (normalized by hmax)
        state.extend(self.holdings / self.hmax)
        
        # Technical indicators
        for tech in self.tech_indicator_list:
            if tech in self.data.columns:
                values = self.data[tech].values
                if len(values) < self.stock_dim:
                    values = np.pad(values, (0, self.stock_dim - len(values)))
                state.extend(values[:self.stock_dim])
            else:
                state.extend([0.0] * self.stock_dim)
        
        state = np.array(state, dtype=np.float32)
        
        # Pad or trim to expected state space
        if len(state) < self.state_space_dim:
            state = np.pad(state, (0, self.state_space_dim - len(state)))
        elif len(state) > self.state_space_dim:
            state = state[:self.state_space_dim]
        
        return state
    
    def _get_prices(self) -> np.ndarray:
        """Get current prices for all stocks."""
        if 'close' in self.data.columns:
            prices = self.data['close'].values
        elif 'y' in self.data.columns:
            prices = self.data['y'].values
        else:
            prices = np.array([100.0])  # Default
        
        # Ensure correct size
        if len(prices) < self.stock_dim:
            prices = np.pad(prices, (0, self.stock_dim - len(prices)), constant_values=prices[-1])
        
        return prices[:self.stock_dim].astype(np.float32)
    
    def _execute_trades(self, actions: np.ndarray):
        """Execute buy/sell orders with transaction costs."""
        prices = self._get_prices()
        
        for i, action in enumerate(actions):
            if i >= len(prices):
                break
            
            price = prices[i]
            
            if action > 0:  # Buy
                # Calculate max shares we can buy
                max_buy = int(self.cash / (price * (1 + self.transaction_cost_pct)))
                shares_to_buy = min(int(action * self.hmax), max_buy)
                
                if shares_to_buy > 0:
                    cost = shares_to_buy * price * (1 + self.transaction_cost_pct)
                    self.cash -= cost
                    self.holdings[i] += shares_to_buy
                    self.trades += 1
                    
                    self.trade_records.append(TradeRecord(
                        timestamp=self.day,
                        symbol_idx=i,
                        action='buy',
                        shares=shares_to_buy,
                        price=price,
                        cost=cost,
                        portfolio_value=self._get_total_asset()
                    ))
                    
            elif action < 0:  # Sell
                shares_to_sell = min(int(-action * self.hmax), int(self.holdings[i]))
                
                if shares_to_sell > 0:
                    revenue = shares_to_sell * price * (1 - self.transaction_cost_pct)
                    self.cash += revenue
                    self.holdings[i] -= shares_to_sell
                    self.trades += 1
                    
                    self.trade_records.append(TradeRecord(
                        timestamp=self.day,
                        symbol_idx=i,
                        action='sell',
                        shares=shares_to_sell,
                        price=price,
                        cost=-revenue,
                        portfolio_value=self._get_total_asset()
                    ))
    
    def _get_total_asset(self) -> float:
        """Calculate total portfolio value."""
        prices = self._get_prices()
        holdings_value = np.sum(self.holdings[:len(prices)] * prices)
        return self.cash + holdings_value
    
    def _compute_reward(self, begin_value: float, end_value: float) -> float:
        """
        Compute reward with risk adjustment.
        
        Reward = scaled return + Sharpe-like bonus
        """
        # Basic return
        portfolio_return = (end_value - begin_value) / begin_value
        reward = portfolio_return * self.reward_scaling
        
        # Sharpe-like bonus based on recent returns
        if len(self.portfolio_return_memory) > 1:
            returns = np.array(self.portfolio_return_memory[-20:])
            if returns.std() > 0:
                sharpe_bonus = returns.mean() / returns.std() * 0.01
                reward += sharpe_bonus
        
        return float(reward)
    
    def _get_info(self) -> Dict:
        """Return info dict for debugging."""
        return {
            'total_asset': self._get_total_asset(),
            'cash': self.cash,
            'holdings': self.holdings.copy(),
            'trades': self.trades,
            'day': self.day,
            'terminal': self.terminal
        }
    
    def get_portfolio_stats(self) -> Dict:
        """Get portfolio performance statistics."""
        if len(self.asset_memory) < 2:
            return {}
        
        assets = np.array(self.asset_memory)
        returns = np.diff(assets) / assets[:-1]
        
        total_return = (assets[-1] / assets[0]) - 1
        
        # Annualized metrics
        n_days = len(returns)
        annual_return = (1 + total_return) ** (252 / max(n_days, 1)) - 1
        
        volatility = returns.std() * np.sqrt(252) if len(returns) > 1 else 0
        
        sharpe = 0
        if volatility > 0:
            excess_return = annual_return - self.risk_free_rate
            sharpe = excess_return / volatility
        
        # Max drawdown
        cummax = np.maximum.accumulate(assets)
        drawdowns = (assets - cummax) / cummax
        max_drawdown = drawdowns.min()
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe,
            'max_drawdown': max_drawdown,
            'total_trades': self.trades,
            'final_value': assets[-1]
        }
    
    def render(self, mode: str = 'human'):
        """Render the environment."""
        if mode == 'human':
            info = self._get_info()
            print(f"Day: {self.day}, Asset: ${info['total_asset']:,.2f}, "
                  f"Cash: ${info['cash']:,.2f}, Trades: {info['trades']}")
    
    def close(self):
        """Clean up resources."""
        pass


def create_trading_env(
    df: pd.DataFrame,
    tech_indicators: List[str] = None,
    **kwargs
) -> StockTradingEnv:
    """
    Convenience function to create a trading environment.
    
    Args:
        df: Price DataFrame
        tech_indicators: List of technical indicator column names
        **kwargs: Additional arguments to StockTradingEnv
        
    Returns:
        Configured StockTradingEnv
    """
    # Determine stock dimension
    if 'tic' in df.columns or 'ticker' in df.columns:
        ticker_col = 'tic' if 'tic' in df.columns else 'ticker'
        stock_dim = df[ticker_col].nunique()
    else:
        stock_dim = 1
    
    # Default tech indicators
    if tech_indicators is None:
        tech_indicators = [col for col in df.columns if col.startswith(('rsi', 'macd', 'sma', 'ema'))]
    
    return StockTradingEnv(
        df=df,
        stock_dim=stock_dim,
        tech_indicator_list=tech_indicators,
        **kwargs
    )
