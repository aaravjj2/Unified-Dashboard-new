"""
Base Broker Interface
Abstract base class defining the standard interface for all broker implementations.
This enables broker-agnostic trading logic.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from enum import Enum


class OrderSide(Enum):
    """Order side enumeration."""
    BUY = "buy"
    SELL = "sell"


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class BaseBroker(ABC):
    """
    Abstract base class for all broker implementations.
    
    This interface ensures consistency across different broker APIs (Alpaca, IB, TD, etc.)
    and allows the options service to be broker-agnostic.
    """
    
    def __init__(self, paper_mode: bool = True, config: Optional[Dict] = None):
        """
        Initialize broker client.
        
        Args:
            paper_mode: If True, use paper trading. If False, use live trading.
            config: Optional configuration dictionary
        """
        self.paper_mode = paper_mode
        self.config = config or {}
    
    @abstractmethod
    def get_account_details(self) -> Dict[str, Any]:
        """
        Get account information.
        
        Returns:
            Dictionary containing:
            - account_id: str
            - buying_power: float
            - cash: float
            - portfolio_value: float
            - equity: float
            - currency: str
        """
        pass
    
    @abstractmethod
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all open positions.
        
        Returns:
            List of position dictionaries, each containing:
            - symbol: str
            - quantity: int
            - market_value: float
            - cost_basis: float
            - unrealized_pl: float
            - unrealized_plpc: float (percent)
            - current_price: float
            - avg_entry_price: float
        """
        pass
    
    @abstractmethod
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific position by symbol.
        
        Args:
            symbol: The symbol to look up
            
        Returns:
            Position dictionary or None if not found
        """
        pass
    
    @abstractmethod
    def place_order(
        self,
        symbol: str,
        quantity: int,
        side: OrderSide,
        order_type: OrderType,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day"
    ) -> Dict[str, Any]:
        """
        Place an order.
        
        Args:
            symbol: The symbol to trade
            quantity: Number of shares/contracts
            side: Buy or sell
            order_type: Market, limit, stop, etc.
            limit_price: Limit price (required for limit orders)
            stop_price: Stop price (required for stop orders)
            time_in_force: Order duration (day, gtc, etc.)
            
        Returns:
            Order details dictionary containing:
            - order_id: str
            - symbol: str
            - quantity: int
            - side: str
            - order_type: str
            - status: str
            - filled_quantity: int
            - filled_avg_price: float
            - submitted_at: str (ISO timestamp)
        """
        pass
    
    @abstractmethod
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get the status of a specific order.
        
        Args:
            order_id: The order ID to query
            
        Returns:
            Order status dictionary
        """
        pass
    
    @abstractmethod
    def get_orders(
        self, 
        status: Optional[OrderStatus] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get orders, optionally filtered by status.
        
        Args:
            status: Filter by order status (None = all)
            limit: Maximum number of orders to return
            
        Returns:
            List of order dictionaries
        """
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            order_id: The order ID to cancel
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get a real-time quote for a symbol.
        
        Args:
            symbol: The symbol to quote
            
        Returns:
            Quote dictionary containing:
            - symbol: str
            - bid: float
            - ask: float
            - last: float
            - bid_size: int
            - ask_size: int
            - timestamp: str (ISO timestamp)
        """
        pass
    
    @abstractmethod
    def is_market_open(self) -> bool:
        """
        Check if the market is currently open.
        
        Returns:
            True if market is open, False otherwise
        """
        pass
    
    @abstractmethod
    def get_market_hours(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get market hours for a specific date.
        
        Args:
            date: Date string in YYYY-MM-DD format (None = today)
            
        Returns:
            Dictionary containing:
            - is_open: bool
            - open_time: str (ISO timestamp)
            - close_time: str (ISO timestamp)
        """
        pass
    
    def validate_order(
        self,
        symbol: str,
        quantity: int,
        side: OrderSide,
        order_type: OrderType,
        limit_price: Optional[float] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Validate an order before placement (optional implementation).
        
        Args:
            symbol: The symbol to trade
            quantity: Number of shares/contracts
            side: Buy or sell
            order_type: Market, limit, etc.
            limit_price: Limit price if applicable
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic validation
        if quantity <= 0:
            return False, "Quantity must be positive"
        
        if order_type == OrderType.LIMIT and limit_price is None:
            return False, "Limit price required for limit orders"
        
        if limit_price is not None and limit_price <= 0:
            return False, "Limit price must be positive"
        
        return True, None
    
    def __repr__(self) -> str:
        """String representation."""
        mode = "PAPER" if self.paper_mode else "LIVE"
        return f"{self.__class__.__name__}(mode={mode})"
