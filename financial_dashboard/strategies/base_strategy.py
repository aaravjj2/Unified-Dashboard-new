"""
Base Strategy Interface
All trading strategies must inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""
    
    def __init__(self, name: str, config: Optional[Dict] = None):
        """
        Initialize strategy.
        
        Args:
            name: Strategy name
            config: Strategy configuration dict
        """
        self.name = name
        self.config = config or {}
        self.enabled = self.config.get('enabled', True)
    
    @abstractmethod
    def generate_signals(self, data: Dict[str, Any]) -> List[Dict]:
        """
        Generate trading signals based on market data.
        
        This is the core method that must be implemented by all strategies.
        
        Args:
            data: Market data dict containing:
                - 'symbol': Stock ticker
                - 'current_price': Current stock price
                - 'options_chain': Options chain data
                - 'quote': Quote data
                - Any other relevant market data
        
        Returns:
            List of signal dicts, each containing:
                - 'action': 'buy' or 'sell'
                - 'symbol': Options symbol (e.g., 'SPY251024C00450000')
                - 'quantity': Number of contracts
                - 'reason': Text explanation of why signal was generated
                - 'confidence': Optional confidence score (0-1)
                - 'metadata': Optional dict with additional signal data
        """
        pass
    
    def validate_signal(self, signal: Dict) -> bool:
        """
        Validate that a signal has all required fields.
        
        Args:
            signal: Signal dict to validate
        
        Returns:
            True if valid, False otherwise
        """
        required_fields = ['action', 'symbol', 'quantity', 'reason']
        for field in required_fields:
            if field not in signal:
                print(f"Invalid signal: missing field '{field}'")
                return False
        
        if signal['action'] not in ['buy', 'sell']:
            print(f"Invalid signal: action must be 'buy' or 'sell', got '{signal['action']}'")
            return False
        
        if not isinstance(signal['quantity'], (int, float)) or signal['quantity'] <= 0:
            print(f"Invalid signal: quantity must be positive number, got {signal['quantity']}")
            return False
        
        return True
    
    def preprocess_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optional preprocessing of data before signal generation.
        Override this if your strategy needs to transform/clean data.
        
        Args:
            data: Raw market data
        
        Returns:
            Processed data
        """
        return data
    
    def get_status(self) -> Dict:
        """
        Get current strategy status.
        
        Returns:
            Dict with strategy info
        """
        return {
            'name': self.name,
            'enabled': self.enabled,
            'config': self.config
        }
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', enabled={self.enabled})"
    
    def __repr__(self) -> str:
        return self.__str__()
