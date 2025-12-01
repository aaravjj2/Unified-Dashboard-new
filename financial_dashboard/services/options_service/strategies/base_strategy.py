"""
Abstract base class for all trading strategies.

This module defines the BaseStrategy ABC that all concrete strategies must implement.
Provides a common interface for signal generation, backtesting, and serialization.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import pandas as pd

# Import the metaclass for auto-registration
try:
    from .strategy_registry import StrategyRegistryMeta
except ImportError:
    # Fallback if registry not available
    from abc import ABCMeta as StrategyRegistryMeta


class BaseStrategy(ABC, metaclass=StrategyRegistryMeta):
    """
    Abstract base class for all trading strategies.
    
    All concrete strategy implementations must inherit from this class and
    implement the required abstract methods: generate_signals() and backtest().
    
    Attributes:
        name: Human-readable name for the strategy
        params: Dictionary of strategy-specific parameters
        
    Example:
        >>> class MyStrategy(BaseStrategy):
        ...     def generate_signals(self, historical_df):
        ...         return [{"ticker": "AAPL", "score": 0.8}]
        ...     def backtest(self, historical_df):
        ...         return {"sharpe_ratio": 1.5}
        ...
        >>> strategy = MyStrategy(name="my_strat", params={"threshold": 0.5})
    """
    
    def __init__(self, name: str, params: Dict[str, Any]):
        """
        Initialize the base strategy.
        
        Args:
            name: Human-readable strategy name
            params: Strategy-specific parameters as a dictionary
        """
        self.name = name
        self.params = params
        # Initialize runtime state
        self.active = False
        self.positions = []
    
    @abstractmethod
    def generate_signals(self, historical_df: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Generate trading signals based on historical data.
        
        This method must be implemented by all concrete strategies. It analyzes
        the provided historical data and returns a list of trading signals/recommendations.
        
        Args:
            historical_df: DataFrame with columns [Date, Open, High, Low, Close, Volume]
                          May contain data for single or multiple tickers
                          
        Returns:
            List of signal dictionaries, each containing:
                - ticker: Stock symbol
                - score: Signal strength/confidence score
                - recommended_strike: Recommended options strike price
                - recommendation_date: Date of the recommendation
                - Any other strategy-specific fields
                
        Example:
            >>> signals = strategy.generate_signals(price_data)
            >>> # [{"ticker": "AAPL", "score": 0.85, "recommended_strike": 175.0, ...}]
        """
        pass
    
    @abstractmethod
    def backtest(self, historical_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Run a backtest of the strategy on historical data.
        
        This method must be implemented by all concrete strategies. It simulates
        the strategy's performance on historical data and returns performance metrics.
        
        Args:
            historical_df: DataFrame with columns [Date, Open, High, Low, Close, Volume]
                          Should contain sufficient historical data for meaningful backtest
                          
        Returns:
            Dictionary of performance metrics, may include:
                - sharpe_ratio: Risk-adjusted return measure
                - total_return: Total percentage return
                - max_drawdown: Maximum peak-to-trough decline
                - win_rate: Percentage of profitable trades
                - Any other strategy-specific metrics
                
        Example:
            >>> results = strategy.backtest(historical_data)
            >>> # {"sharpe_ratio": 1.5, "total_return": 0.25, "win_rate": 0.65}
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the strategy configuration to a dictionary.
        
        Useful for saving strategy configurations to files, databases,
        or transmitting over APIs.
        
        Returns:
            Dictionary containing strategy name and parameters
            
        Example:
            >>> config = strategy.to_dict()
            >>> # {"name": "my_strategy", "params": {"threshold": 0.5}}
        """
        return {
            "name": self.name,
            "params": self.params
        }
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'BaseStrategy':
        """
        Reconstruct a strategy instance from a serialized dictionary.
        
        This is the inverse of to_dict(). Use it to restore a strategy
        from a saved configuration.
        
        Args:
            config: Dictionary with 'name' and 'params' keys
            
        Returns:
            New instance of the strategy class
            
        Example:
            >>> config = {"name": "restored", "params": {"threshold": 0.5}}
            >>> strategy = MyStrategy.from_dict(config)
        """
        return cls(
            name=config["name"],
            params=config["params"]
        )
        
    
    def validate_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Validate that a signal has all required fields.
        
        Args:
            signal: Signal dictionary to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_fields = [
            'ticker', 'signal_type', 'option_type', 
            'strike', 'expiration', 'quantity'
        ]
        
        return all(field in signal for field in required_fields)
    
    def activate(self):
        """Mark strategy as active for live trading."""
        self.active = True
    
    def deactivate(self):
        """Mark strategy as inactive (paper trading or disabled)."""
        self.active = False
    
    def add_position(self, position: Dict[str, Any]):
        """Record an opened position."""
        self.positions.append(position)
    
    def close_position(self, position_id: str):
        """Close a position by ID."""
        self.positions = [p for p in self.positions if p.get('id') != position_id]
    
    def get_open_positions(self) -> List[Dict[str, Any]]:
        """Get all currently open positions."""
        return self.positions
    
    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}', active={self.active})"
