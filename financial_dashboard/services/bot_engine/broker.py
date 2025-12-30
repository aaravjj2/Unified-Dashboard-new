"""
Alpaca Broker Bridge
====================

Paper trading integration with Alpaca Markets.
FORCE_PLACE_LIVE=false ensures paper trading only.

Author: Bot Engine Team
Date: December 2025
"""

import os
import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path

# Load environment variables from keys.env
try:
    from dotenv import load_dotenv
    _project_root = Path(__file__).parent.parent.parent.parent
    _keys_env = _project_root / 'keys.env'
    if _keys_env.exists():
        load_dotenv(_keys_env, override=True)
        logging.getLogger(__name__).debug(f"Loaded keys from {_keys_env}")
except ImportError:
    pass

# alpaca-py imports
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import (
        MarketOrderRequest,
        LimitOrderRequest,
        GetOrdersRequest
    )
    from alpaca.trading.enums import (
        OrderSide,
        TimeInForce,
        OrderStatus,
        QueryOrderStatus
    )
    from alpaca.common.exceptions import APIError
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    TradingClient = None

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order type enum."""
    MARKET = "market"
    LIMIT = "limit"


class Side(Enum):
    """Order side enum."""
    BUY = "buy"
    SELL = "sell"


@dataclass
class OrderResult:
    """Result of an order submission."""
    success: bool
    order_id: Optional[str] = None
    ticker: str = ""
    side: str = ""
    quantity: float = 0.0
    order_type: str = ""
    status: str = ""
    filled_price: Optional[float] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'order_id': self.order_id,
            'ticker': self.ticker,
            'side': self.side,
            'quantity': self.quantity,
            'order_type': self.order_type,
            'status': self.status,
            'filled_price': self.filled_price,
            'error': self.error,
            'timestamp': self.timestamp
        }


@dataclass
class Position:
    """Position data class."""
    ticker: str
    quantity: float
    market_value: float
    avg_entry_price: float
    current_price: float
    unrealized_pl: float
    unrealized_pl_pct: float
    side: str  # 'long' or 'short'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'ticker': self.ticker,
            'quantity': self.quantity,
            'market_value': self.market_value,
            'avg_entry_price': self.avg_entry_price,
            'current_price': self.current_price,
            'unrealized_pl': self.unrealized_pl,
            'unrealized_pl_pct': self.unrealized_pl_pct,
            'side': self.side
        }


class AlpacaBroker:
    """
    Alpaca Trading Bridge for Paper Trading.
    
    Features:
    - Paper trading only (FORCE_PLACE_LIVE safety)
    - Market and limit orders
    - Position tracking
    - Order history
    - Deterministic mode for testing
    
    Usage:
        broker = AlpacaBroker()
        result = broker.submit_order('AAPL', Side.BUY, 10)
        positions = broker.get_positions()
    """
    
    PAPER_BASE_URL = "https://paper-api.alpaca.markets"
    LIVE_BASE_URL = "https://api.alpaca.markets"
    
    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        paper: bool = True,
        deterministic: bool = None
    ):
        """
        Initialize Alpaca broker.
        
        Args:
            api_key: Alpaca API key (checks multiple env vars)
            api_secret: Alpaca API secret (checks multiple env vars)
            paper: Force paper trading (default True)
            deterministic: Return mock data for testing
        """
        # Try multiple environment variable names for API key
        self.api_key = api_key or self._get_api_key()
        self.api_secret = api_secret or self._get_api_secret()
        
        # SAFETY: Check FORCE_PLACE_LIVE flag
        force_live = os.environ.get('FORCE_PLACE_LIVE', 'false').lower() == 'true'
        if force_live and not paper:
            logger.warning("FORCE_PLACE_LIVE=true but paper=True was specified. Using paper trading.")
        
        # ALWAYS use paper unless explicitly allowed
        self.paper = paper or not force_live
        
        # Deterministic mode
        if deterministic is None:
            deterministic = os.environ.get('BOT_DETERMINISTIC', '0') == '1'
        self.deterministic = deterministic
        
        # Mock state for deterministic mode
        self._mock_positions: Dict[str, Dict] = {}
        self._mock_orders: List[Dict] = []
        self._mock_cash = 100000.0
        self._mock_order_counter = 0
        
        # Initialize Alpaca client
        self._client: Optional[TradingClient] = None
        if not self.deterministic and ALPACA_AVAILABLE and self.api_key:
            try:
                self._client = TradingClient(
                    api_key=self.api_key,
                    secret_key=self.api_secret,
                    paper=self.paper
                )
                logger.info(f"✅ AlpacaBroker connected (paper={self.paper}, key={self.api_key[:8]}...)")
            except Exception as e:
                logger.error(f"Failed to initialize Alpaca client: {e}")
                self._client = None
        else:
            if self.deterministic:
                logger.info("AlpacaBroker in deterministic (mock) mode")
            elif not self.api_key:
                logger.warning("AlpacaBroker: No API key found - orders will not execute")
            else:
                logger.info("AlpacaBroker in mock mode (alpaca-py not available)")
    
    @staticmethod
    def _get_api_key() -> str:
        """Get Alpaca API key from available environment variables."""
        key_vars = [
            'STRATEGY_LAB_ALPACA_KEY',  # Bot-specific key
            'ALPACA_KEY_WEEKLY',         # Weekly trading key
            'ALPACA_API_KEY',            # Standard name
            'APCA_API_KEY_ID',           # Alternate name
            'ALPACA2_KEY',               # Numbered keys
            'ALPACA3_KEY',
        ]
        for var in key_vars:
            key = os.environ.get(var, '')
            if key:
                logger.debug(f"Using Alpaca API key from {var}")
                return key
        return ''
    
    @staticmethod
    def _get_api_secret() -> str:
        """Get Alpaca API secret from available environment variables."""
        secret_vars = [
            'STRATEGY_LAB_ALPACA_SECRET',  # Bot-specific secret
            'ALPACA_SECRET_WEEKLY',         # Weekly trading secret
            'ALPACA_API_SECRET',            # Standard name
            'APCA_API_SECRET_KEY',          # Alternate name
            'ALPACA2_SECRET',               # Numbered secrets
            'ALPACA3_SECRET',
        ]
        for var in secret_vars:
            secret = os.environ.get(var, '')
            if secret:
                logger.debug(f"Using Alpaca API secret from {var}")
                return secret
        return ''
    
    @property
    def is_connected(self) -> bool:
        """Check if broker is connected."""
        if self.deterministic:
            return True
        return self._client is not None
    
    def submit_order(
        self,
        ticker: str,
        side: Side,
        quantity: float,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        time_in_force: str = "day"
    ) -> OrderResult:
        """
        Submit an order.
        
        Args:
            ticker: Stock symbol
            side: BUY or SELL
            quantity: Number of shares
            order_type: MARKET or LIMIT
            limit_price: Price for limit orders
            time_in_force: Order duration
            
        Returns:
            OrderResult with success status and details
        """
        ticker = ticker.upper().strip()
        
        logger.info(f"Submitting order: {side.value} {quantity} {ticker} ({order_type.value})")
        
        # Deterministic mode - mock order
        if self.deterministic:
            return self._mock_submit_order(ticker, side, quantity, order_type, limit_price)
        
        # Check client connection
        if not self._client:
            return OrderResult(
                success=False,
                ticker=ticker,
                side=side.value,
                quantity=quantity,
                order_type=order_type.value,
                error="Alpaca client not connected"
            )
        
        try:
            # Create order request
            if order_type == OrderType.MARKET:
                order_request = MarketOrderRequest(
                    symbol=ticker,
                    qty=quantity,
                    side=OrderSide.BUY if side == Side.BUY else OrderSide.SELL,
                    time_in_force=TimeInForce.DAY if time_in_force == "day" else TimeInForce.GTC
                )
            else:
                if limit_price is None:
                    return OrderResult(
                        success=False,
                        ticker=ticker,
                        error="Limit price required for limit orders"
                    )
                order_request = LimitOrderRequest(
                    symbol=ticker,
                    qty=quantity,
                    side=OrderSide.BUY if side == Side.BUY else OrderSide.SELL,
                    time_in_force=TimeInForce.DAY if time_in_force == "day" else TimeInForce.GTC,
                    limit_price=limit_price
                )
            
            # Submit order
            order = self._client.submit_order(order_request)
            
            return OrderResult(
                success=True,
                order_id=str(order.id),
                ticker=ticker,
                side=side.value,
                quantity=quantity,
                order_type=order_type.value,
                status=str(order.status.value),
                filled_price=float(order.filled_avg_price) if order.filled_avg_price else None
            )
            
        except APIError as e:
            logger.error(f"Alpaca API error: {e}")
            return OrderResult(
                success=False,
                ticker=ticker,
                side=side.value,
                quantity=quantity,
                error=str(e)
            )
        except Exception as e:
            logger.error(f"Order submission failed: {e}")
            return OrderResult(
                success=False,
                ticker=ticker,
                side=side.value,
                quantity=quantity,
                error=str(e)
            )
    
    def _mock_submit_order(
        self,
        ticker: str,
        side: Side,
        quantity: float,
        order_type: OrderType,
        limit_price: Optional[float]
    ) -> OrderResult:
        """Submit mock order in deterministic mode."""
        import hashlib
        
        # Generate deterministic price
        hash_val = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
        price = 100 + (hash_val % 400)
        
        if order_type == OrderType.LIMIT and limit_price:
            price = limit_price
        
        self._mock_order_counter += 1
        order_id = f"mock-{self._mock_order_counter:06d}"
        
        # Update mock positions
        if side == Side.BUY:
            if ticker in self._mock_positions:
                pos = self._mock_positions[ticker]
                total_qty = pos['quantity'] + quantity
                total_cost = pos['quantity'] * pos['avg_price'] + quantity * price
                pos['quantity'] = total_qty
                pos['avg_price'] = total_cost / total_qty
            else:
                self._mock_positions[ticker] = {
                    'quantity': quantity,
                    'avg_price': price
                }
            self._mock_cash -= quantity * price
        else:
            if ticker in self._mock_positions:
                pos = self._mock_positions[ticker]
                pos['quantity'] -= quantity
                self._mock_cash += quantity * price
                if pos['quantity'] <= 0:
                    del self._mock_positions[ticker]
        
        # Record order
        order_record = {
            'order_id': order_id,
            'ticker': ticker,
            'side': side.value,
            'quantity': quantity,
            'price': price,
            'status': 'filled',
            'timestamp': datetime.now().isoformat()
        }
        self._mock_orders.append(order_record)
        
        return OrderResult(
            success=True,
            order_id=order_id,
            ticker=ticker,
            side=side.value,
            quantity=quantity,
            order_type=order_type.value,
            status='filled',
            filled_price=price
        )
    
    def get_positions(self) -> List[Position]:
        """
        Get current positions.
        
        Returns:
            List of Position objects
        """
        if self.deterministic:
            return self._mock_get_positions()
        
        if not self._client:
            logger.warning("Cannot get positions: client not connected")
            return []
        
        try:
            positions = self._client.get_all_positions()
            return [
                Position(
                    ticker=p.symbol,
                    quantity=float(p.qty),
                    market_value=float(p.market_value),
                    avg_entry_price=float(p.avg_entry_price),
                    current_price=float(p.current_price),
                    unrealized_pl=float(p.unrealized_pl),
                    unrealized_pl_pct=float(p.unrealized_plpc) * 100,
                    side='long' if float(p.qty) > 0 else 'short'
                )
                for p in positions
            ]
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            return []
    
    def _mock_get_positions(self) -> List[Position]:
        """Get mock positions in deterministic mode."""
        import hashlib
        positions = []
        
        for ticker, data in self._mock_positions.items():
            hash_val = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
            current_price = data['avg_price'] * (1 + (hash_val % 20 - 10) / 100)
            quantity = data['quantity']
            market_value = quantity * current_price
            unrealized_pl = (current_price - data['avg_price']) * quantity
            
            positions.append(Position(
                ticker=ticker,
                quantity=quantity,
                market_value=market_value,
                avg_entry_price=data['avg_price'],
                current_price=current_price,
                unrealized_pl=unrealized_pl,
                unrealized_pl_pct=(unrealized_pl / (data['avg_price'] * quantity)) * 100,
                side='long' if quantity > 0 else 'short'
            ))
        
        return positions
    
    def get_buying_power(self) -> float:
        """
        Get available buying power.
        
        Returns:
            Available cash for trading
        """
        if self.deterministic:
            return self._mock_cash
        
        if not self._client:
            return 0.0
        
        try:
            account = self._client.get_account()
            return float(account.buying_power)
        except Exception as e:
            logger.error(f"Failed to get buying power: {e}")
            return 0.0
    
    def get_account_info(self) -> Dict[str, Any]:
        """
        Get account information.
        
        Returns:
            Dict with account details
        """
        if self.deterministic:
            total_value = self._mock_cash + sum(
                pos['quantity'] * pos['avg_price']
                for pos in self._mock_positions.values()
            )
            return {
                'cash': self._mock_cash,
                'buying_power': self._mock_cash,
                'portfolio_value': total_value,
                'equity': total_value,
                'paper': True,
                'status': 'ACTIVE',
                'source': 'mock'
            }
        
        if not self._client:
            return {'error': 'Client not connected'}
        
        try:
            account = self._client.get_account()
            return {
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'portfolio_value': float(account.portfolio_value),
                'equity': float(account.equity),
                'paper': self.paper,
                'status': account.status.value,
                'source': 'alpaca'
            }
        except Exception as e:
            logger.error(f"Failed to get account info: {e}")
            return {'error': str(e)}
    
    def get_orders(self, status: str = 'all', limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get order history.
        
        Args:
            status: Filter by status ('all', 'open', 'closed')
            limit: Max orders to return
            
        Returns:
            List of order dicts
        """
        if self.deterministic:
            return self._mock_orders[-limit:]
        
        if not self._client:
            return []
        
        try:
            if status == 'open':
                query_status = QueryOrderStatus.OPEN
            elif status == 'closed':
                query_status = QueryOrderStatus.CLOSED
            else:
                query_status = QueryOrderStatus.ALL
            
            request = GetOrdersRequest(status=query_status, limit=limit)
            orders = self._client.get_orders(request)
            
            return [
                {
                    'order_id': str(o.id),
                    'ticker': o.symbol,
                    'side': o.side.value,
                    'quantity': float(o.qty),
                    'filled_qty': float(o.filled_qty) if o.filled_qty else 0,
                    'order_type': o.order_type.value,
                    'status': o.status.value,
                    'filled_price': float(o.filled_avg_price) if o.filled_avg_price else None,
                    'submitted_at': o.submitted_at.isoformat() if o.submitted_at else None
                }
                for o in orders
            ]
        except Exception as e:
            logger.error(f"Failed to get orders: {e}")
            return []
    
    def close_position(self, ticker: str) -> OrderResult:
        """
        Close a position completely.
        
        Args:
            ticker: Stock symbol
            
        Returns:
            OrderResult
        """
        ticker = ticker.upper().strip()
        
        if self.deterministic:
            if ticker in self._mock_positions:
                qty = self._mock_positions[ticker]['quantity']
                return self.submit_order(ticker, Side.SELL, qty)
            return OrderResult(success=False, ticker=ticker, error="No position found")
        
        if not self._client:
            return OrderResult(success=False, error="Client not connected")
        
        try:
            self._client.close_position(ticker)
            return OrderResult(success=True, ticker=ticker, status='closed')
        except Exception as e:
            logger.error(f"Failed to close position {ticker}: {e}")
            return OrderResult(success=False, ticker=ticker, error=str(e))
    
    def close_all_positions(self) -> List[OrderResult]:
        """
        Close all open positions.
        
        Returns:
            List of OrderResults
        """
        if self.deterministic:
            results = []
            for ticker in list(self._mock_positions.keys()):
                results.append(self.close_position(ticker))
            return results
        
        if not self._client:
            return []
        
        try:
            self._client.close_all_positions(cancel_orders=True)
            return [OrderResult(success=True, status='all_closed')]
        except Exception as e:
            logger.error(f"Failed to close all positions: {e}")
            return [OrderResult(success=False, error=str(e))]


# Module-level singleton
_broker: Optional[AlpacaBroker] = None


def get_broker(deterministic: bool = None) -> AlpacaBroker:
    """Get or create the Alpaca broker singleton."""
    global _broker
    if _broker is None:
        _broker = AlpacaBroker(deterministic=deterministic)
    return _broker
