"""
Alpaca Trading Client for Options Orders

Handles order placement, position tracking, and order lifecycle management.
Paper trading by default; requires explicit opt-in for live trading.
"""

import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import requests

logger = logging.getLogger(__name__)


class TradingEnvironment(Enum):
    """Trading environment selection."""
    PAPER = "paper"
    LIVE = "live"


class OrderType(Enum):
    """Order types supported."""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Order side."""
    BUY = "buy"
    SELL = "sell"


class TimeInForce(Enum):
    """Time in force options."""
    DAY = "day"
    GTC = "gtc"
    IOC = "ioc"
    FOK = "fok"


class OrderStatus(Enum):
    """Order status values."""
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    DONE_FOR_DAY = "done_for_day"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REPLACED = "replaced"
    PENDING_CANCEL = "pending_cancel"
    PENDING_REPLACE = "pending_replace"
    PENDING_NEW = "pending_new"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass
class OrderRequest:
    """Order request parameters."""
    symbol: str  # Option contract symbol (e.g., SPY251231C00450000)
    qty: int
    side: OrderSide
    order_type: OrderType = OrderType.MARKET
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    client_order_id: Optional[str] = None
    
    def to_alpaca_params(self) -> Dict[str, Any]:
        """Convert to Alpaca API parameters."""
        params = {
            "symbol": self.symbol,
            "qty": str(self.qty),
            "side": self.side.value,
            "type": self.order_type.value,
            "time_in_force": self.time_in_force.value,
        }
        if self.limit_price is not None:
            params["limit_price"] = str(self.limit_price)
        if self.stop_price is not None:
            params["stop_price"] = str(self.stop_price)
        if self.client_order_id:
            params["client_order_id"] = self.client_order_id
        return params


@dataclass
class Order:
    """Order response/status."""
    id: str
    client_order_id: str
    symbol: str
    qty: int
    filled_qty: int
    side: str
    order_type: str
    status: str
    time_in_force: str
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_avg_price: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    submitted_at: Optional[str] = None
    filled_at: Optional[str] = None
    
    @classmethod
    def from_alpaca(cls, data: Dict) -> 'Order':
        """Create from Alpaca API response."""
        return cls(
            id=data.get('id', ''),
            client_order_id=data.get('client_order_id', ''),
            symbol=data.get('symbol', ''),
            qty=int(data.get('qty', 0)),
            filled_qty=int(data.get('filled_qty', 0)),
            side=data.get('side', ''),
            order_type=data.get('type', ''),
            status=data.get('status', ''),
            time_in_force=data.get('time_in_force', ''),
            limit_price=float(data['limit_price']) if data.get('limit_price') else None,
            stop_price=float(data['stop_price']) if data.get('stop_price') else None,
            filled_avg_price=float(data['filled_avg_price']) if data.get('filled_avg_price') else None,
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            submitted_at=data.get('submitted_at'),
            filled_at=data.get('filled_at'),
        )


@dataclass
class Position:
    """Position data."""
    symbol: str
    qty: int
    avg_entry_price: float
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_plpc: float
    current_price: float
    side: str  # 'long' or 'short'
    
    @classmethod
    def from_alpaca(cls, data: Dict) -> 'Position':
        """Create from Alpaca API response."""
        return cls(
            symbol=data.get('symbol', ''),
            qty=int(data.get('qty', 0)),
            avg_entry_price=float(data.get('avg_entry_price', 0)),
            market_value=float(data.get('market_value', 0)),
            cost_basis=float(data.get('cost_basis', 0)),
            unrealized_pl=float(data.get('unrealized_pl', 0)),
            unrealized_plpc=float(data.get('unrealized_plpc', 0)),
            current_price=float(data.get('current_price', 0)),
            side=data.get('side', 'long'),
        )


@dataclass
class RiskLimits:
    """Trading risk limits."""
    max_position_qty: int = 100
    max_order_value: float = 50000.0
    max_daily_loss: float = 5000.0
    max_positions: int = 20
    require_confirmation: bool = True


class AlpacaTradingClient:
    """
    Alpaca Trading Client for options orders.
    
    Default: Paper trading only. Live trading requires explicit opt-in.
    """
    
    def __init__(self, environment: TradingEnvironment = TradingEnvironment.PAPER):
        """Initialize trading client."""
        self.environment = environment
        self.api_key = os.getenv('APCA_API_KEY_ID')
        self.api_secret = os.getenv('APCA_API_SECRET_KEY')
        
        # Set base URL based on environment
        if environment == TradingEnvironment.LIVE:
            self.base_url = os.getenv('APCA_LIVE_URL', 'https://api.alpaca.markets')
            logger.warning("⚠️ LIVE TRADING ENABLED - Real money at risk!")
        else:
            self.base_url = os.getenv('APCA_API_BASE_URL', 'https://paper-api.alpaca.markets')
            logger.info("📝 Paper trading mode active")
        
        self.headers = {
            'APCA-API-KEY-ID': self.api_key or '',
            'APCA-API-SECRET-KEY': self.api_secret or '',
            'Content-Type': 'application/json'
        }
        
        self.available = bool(self.api_key and self.api_secret)
        self.risk_limits = RiskLimits()
        
        # Order history (in-memory for now)
        self._order_history: List[Order] = []
        self._daily_pnl: float = 0.0
        
        if not self.available:
            logger.warning("⚠️ Alpaca trading credentials not configured")
    
    def set_risk_limits(self, limits: RiskLimits) -> None:
        """Update risk limits."""
        self.risk_limits = limits
        logger.info(f"🛡️ Risk limits updated: max_qty={limits.max_position_qty}, max_value=${limits.max_order_value}")
    
    def validate_order(self, request: OrderRequest, current_price: float) -> tuple[bool, str]:
        """
        Validate order against risk limits.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check position quantity limit
        if request.qty > self.risk_limits.max_position_qty:
            return False, f"Order qty {request.qty} exceeds max {self.risk_limits.max_position_qty}"
        
        # Check order value limit
        order_value = request.qty * current_price * 100  # Options are per 100 shares
        if order_value > self.risk_limits.max_order_value:
            return False, f"Order value ${order_value:.2f} exceeds max ${self.risk_limits.max_order_value:.2f}"
        
        # Check daily loss limit
        if self._daily_pnl < -self.risk_limits.max_daily_loss:
            return False, f"Daily loss limit reached (${self._daily_pnl:.2f})"
        
        # Check limit price for limit orders
        if request.order_type == OrderType.LIMIT and request.limit_price is None:
            return False, "Limit price required for limit orders"
        
        if request.order_type == OrderType.STOP and request.stop_price is None:
            return False, "Stop price required for stop orders"
        
        return True, ""
    
    def place_order(self, request: OrderRequest, current_price: float = 0.0, 
                   confirmed: bool = False) -> tuple[Optional[Order], str]:
        """
        Place an options order.
        
        Args:
            request: Order request parameters
            current_price: Current option price for validation
            confirmed: User has confirmed the order (required if risk_limits.require_confirmation)
            
        Returns:
            Tuple of (Order if successful, status_message)
        """
        if not self.available:
            return None, "❌ Trading credentials not configured"
        
        # Require confirmation for paper/live
        if self.risk_limits.require_confirmation and not confirmed:
            return None, "⚠️ Order requires confirmation"
        
        # Validate against risk limits
        is_valid, error_msg = self.validate_order(request, current_price)
        if not is_valid:
            logger.warning(f"❌ Order validation failed: {error_msg}")
            return None, f"❌ {error_msg}"
        
        try:
            url = f"{self.base_url}/v2/orders"
            params = request.to_alpaca_params()
            
            logger.info(f"📤 Placing {self.environment.value} order: {params}")
            
            response = requests.post(url, headers=self.headers, json=params, timeout=30)
            
            if response.status_code in (200, 201):
                order = Order.from_alpaca(response.json())
                self._order_history.append(order)
                logger.info(f"✅ Order placed: {order.id} ({order.status})")
                return order, f"✅ Order {order.id} submitted ({order.status})"
            else:
                error = response.json().get('message', response.text)
                logger.error(f"❌ Order failed: {error}")
                return None, f"❌ Order failed: {error}"
                
        except Exception as e:
            logger.error(f"❌ Order error: {e}")
            return None, f"❌ Error: {str(e)}"
    
    def cancel_order(self, order_id: str) -> tuple[bool, str]:
        """Cancel an open order."""
        if not self.available:
            return False, "❌ Trading credentials not configured"
        
        try:
            url = f"{self.base_url}/v2/orders/{order_id}"
            response = requests.delete(url, headers=self.headers, timeout=30)
            
            if response.status_code in (200, 204):
                logger.info(f"✅ Order {order_id} canceled")
                return True, f"✅ Order {order_id} canceled"
            else:
                error = response.json().get('message', response.text)
                return False, f"❌ Cancel failed: {error}"
                
        except Exception as e:
            logger.error(f"❌ Cancel error: {e}")
            return False, f"❌ Error: {str(e)}"
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID."""
        if not self.available:
            return None
        
        try:
            url = f"{self.base_url}/v2/orders/{order_id}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return Order.from_alpaca(response.json())
            return None
            
        except Exception as e:
            logger.error(f"❌ Get order error: {e}")
            return None
    
    def get_orders(self, status: Optional[str] = None, limit: int = 50) -> List[Order]:
        """Get orders list."""
        if not self.available:
            return []
        
        try:
            url = f"{self.base_url}/v2/orders"
            params = {"limit": limit}
            if status:
                params["status"] = status
            
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                return [Order.from_alpaca(o) for o in response.json()]
            return []
            
        except Exception as e:
            logger.error(f"❌ Get orders error: {e}")
            return []
    
    def get_positions(self) -> List[Position]:
        """Get all positions."""
        if not self.available:
            return []
        
        try:
            url = f"{self.base_url}/v2/positions"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return [Position.from_alpaca(p) for p in response.json()]
            return []
            
        except Exception as e:
            logger.error(f"❌ Get positions error: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for specific symbol."""
        if not self.available:
            return None
        
        try:
            url = f"{self.base_url}/v2/positions/{symbol}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return Position.from_alpaca(response.json())
            return None
            
        except Exception as e:
            logger.error(f"❌ Get position error: {e}")
            return None
    
    def close_position(self, symbol: str) -> tuple[bool, str]:
        """Close position for symbol."""
        if not self.available:
            return False, "❌ Trading credentials not configured"
        
        try:
            url = f"{self.base_url}/v2/positions/{symbol}"
            response = requests.delete(url, headers=self.headers, timeout=30)
            
            if response.status_code in (200, 204):
                logger.info(f"✅ Position {symbol} closed")
                return True, f"✅ Position {symbol} closed"
            else:
                error = response.json().get('message', response.text)
                return False, f"❌ Close failed: {error}"
                
        except Exception as e:
            logger.error(f"❌ Close position error: {e}")
            return False, f"❌ Error: {str(e)}"
    
    def get_account(self) -> Optional[Dict]:
        """Get account information."""
        if not self.available:
            return None
        
        try:
            url = f"{self.base_url}/v2/account"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.error(f"❌ Get account error: {e}")
            return None
    
    def get_order_history(self) -> List[Order]:
        """Get local order history."""
        return self._order_history.copy()


# Singleton instance
_trading_client: Optional[AlpacaTradingClient] = None


def get_trading_client(environment: TradingEnvironment = TradingEnvironment.PAPER) -> AlpacaTradingClient:
    """Get or create singleton trading client."""
    global _trading_client
    if _trading_client is None or _trading_client.environment != environment:
        _trading_client = AlpacaTradingClient(environment)
    return _trading_client


def place_option_order(
    symbol: str,
    qty: int,
    side: str,  # 'buy' or 'sell'
    order_type: str = 'market',
    limit_price: Optional[float] = None,
    current_price: float = 0.0,
    confirmed: bool = False
) -> tuple[Optional[Order], str]:
    """
    Convenience function to place an option order.
    
    Args:
        symbol: Option contract symbol
        qty: Number of contracts
        side: 'buy' or 'sell'
        order_type: 'market', 'limit', 'stop', 'stop_limit'
        limit_price: Price for limit orders
        current_price: Current option price for validation
        confirmed: User has confirmed the order
        
    Returns:
        Tuple of (Order if successful, status_message)
    """
    client = get_trading_client()
    
    request = OrderRequest(
        symbol=symbol,
        qty=qty,
        side=OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL,
        order_type=OrderType(order_type.lower()),
        limit_price=limit_price,
    )
    
    return client.place_order(request, current_price, confirmed)
