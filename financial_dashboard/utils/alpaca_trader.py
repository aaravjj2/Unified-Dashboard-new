"""
Alpaca Trading Client
Handles all trade execution and position management via Alpaca API.
Supports both paper and live trading modes.
"""

import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest, StopOrderRequest, StopLimitOrderRequest
from alpaca.trading.enums import OrderSide as AlpacaOrderSide, TimeInForce, OrderType as AlpacaOrderType
from alpaca.data.models import Bar, Quote
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

# Import our broker interface
from trading.base_broker import BaseBroker, OrderSide, OrderType, OrderStatus


class AlpacaTrader(BaseBroker):
    """
    Alpaca broker implementation.
    
    Implements the BaseBroker interface for Alpaca trading API.
    Supports both paper and live trading modes.
    """
    
    def __init__(self, paper_mode: bool = True, config: Optional[Dict] = None):
        """
        Initialize Alpaca trading client.
        
        Args:
            paper_mode: If True, use paper trading. If False, use live trading.
            config: Optional configuration dictionary (can include api_key, api_secret)
        """
        # Call parent constructor
        super().__init__(paper_mode=paper_mode, config=config)
        
        # Try multiple environment variable names for Alpaca
        api_key = self.config.get('api_key') or os.getenv('ALPACA_API_KEY') or os.getenv("APCA_API_KEY_ID")
        api_secret = self.config.get('api_secret') or os.getenv('ALPACA_API_SECRET') or os.getenv("APCA_API_SECRET_KEY")
        
        if not api_key or not api_secret:
            raise ValueError("Alpaca credentials not provided and environment variables not set")
        
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Initialize Alpaca client
        self.client = TradingClient(
            api_key=self.api_key,
            secret_key=self.api_secret,
            paper=self.paper_mode
        )
        
        # Initialize data client for quotes
        self.data_client = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.api_secret
        )
        
        print(f"Alpaca client initialized in {'PAPER' if self.paper_mode else 'LIVE'} mode")
    
    def _map_order_side(self, side: OrderSide) -> AlpacaOrderSide:
        """Map BaseBroker OrderSide to Alpaca OrderSide."""
        return AlpacaOrderSide.BUY if side == OrderSide.BUY else AlpacaOrderSide.SELL
    
    def _map_order_type(self, order_type: OrderType) -> AlpacaOrderType:
        """Map BaseBroker OrderType to Alpaca OrderType."""
        type_map = {
            OrderType.MARKET: AlpacaOrderType.MARKET,
            OrderType.LIMIT: AlpacaOrderType.LIMIT,
            OrderType.STOP: AlpacaOrderType.STOP,
            OrderType.STOP_LIMIT: AlpacaOrderType.STOP_LIMIT
        }
        return type_map[order_type]
    
    def _map_order_status(self, alpaca_status: str) -> OrderStatus:
        """Map Alpaca order status to BaseBroker OrderStatus."""
        status_map = {
            'new': OrderStatus.PENDING,
            'partially_filled': OrderStatus.PENDING,
            'filled': OrderStatus.FILLED,
            'done_for_day': OrderStatus.FILLED,
            'canceled': OrderStatus.CANCELLED,
            'expired': OrderStatus.CANCELLED,
            'replaced': OrderStatus.CANCELLED,
            'pending_cancel': OrderStatus.PENDING,
            'pending_replace': OrderStatus.PENDING,
            'accepted': OrderStatus.PENDING,
            'pending_new': OrderStatus.PENDING,
            'accepted_for_bidding': OrderStatus.PENDING,
            'stopped': OrderStatus.CANCELLED,
            'rejected': OrderStatus.REJECTED,
            'suspended': OrderStatus.REJECTED,
            'calculated': OrderStatus.PENDING
        }
        return status_map.get(alpaca_status.lower(), OrderStatus.PENDING)
    
    def get_account_details(self) -> Dict[str, Any]:
        """
        Get account information.
        
        Returns:
            Dict with account balance, buying power, etc. matching BaseBroker interface:
            - account_id: str
            - buying_power: float
            - cash: float
            - portfolio_value: float
            - equity: float
            - currency: str
        """
        try:
            account = self.client.get_account()
            return {
                'account_id': account.account_number,
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'buying_power': float(account.buying_power),
                'equity': float(account.equity),
                'currency': 'USD',
                # Additional Alpaca-specific fields
                'last_equity': float(account.last_equity),
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'account_blocked': account.account_blocked
            }
        except Exception as e:
            print(f"Error fetching account details: {e}")
            raise
    
    def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get all current positions.
        
        Returns:
            List of position dicts matching BaseBroker interface:
            - symbol: str
            - quantity: int
            - market_value: float
            - cost_basis: float
            - unrealized_pl: float
            - unrealized_plpc: float (percent)
            - current_price: float
            - avg_entry_price: float
        """
        try:
            positions = self.client.get_all_positions()
            return [
                {
                    'symbol': pos.symbol,
                    'quantity': int(float(pos.qty)),
                    'market_value': float(pos.market_value),
                    'cost_basis': float(pos.cost_basis),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc),
                    'current_price': float(pos.current_price),
                    'avg_entry_price': float(pos.avg_entry_price),
                    # Additional Alpaca-specific fields
                    'side': pos.side,
                    'asset_class': pos.asset_class
                }
                for pos in positions
            ]
        except Exception as e:
            print(f"Error fetching positions: {e}")
            raise
    
    def get_position(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get specific position by symbol.
        
        Args:
            symbol: Symbol to get position for
        
        Returns:
            Position dict or None if no position
        """
        try:
            pos = self.client.get_open_position(symbol)
            return {
                'symbol': pos.symbol,
                'quantity': int(float(pos.qty)),
                'market_value': float(pos.market_value),
                'cost_basis': float(pos.cost_basis),
                'unrealized_pl': float(pos.unrealized_pl),
                'unrealized_plpc': float(pos.unrealized_plpc),
                'current_price': float(pos.current_price),
                'avg_entry_price': float(pos.avg_entry_price),
                'side': pos.side
            }
        except Exception as e:
            # Position doesn't exist
            return None
    
    def place_order(
        self,
        symbol: str,
        quantity: int,
        side: OrderSide,
        order_type: OrderType = OrderType.MARKET,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        time_in_force: str = "day"
    ) -> Dict[str, Any]:
        """
        Place an order.
        
        Args:
            symbol: Symbol to trade (e.g., 'SPY', 'AAPL251024C00450000')
            quantity: Quantity (number of shares or contracts)
            side: OrderSide enum (BUY or SELL)
            order_type: OrderType enum (MARKET, LIMIT, STOP, STOP_LIMIT)
            limit_price: Required if order_type is LIMIT or STOP_LIMIT
            stop_price: Required if order_type is STOP or STOP_LIMIT
            time_in_force: Order duration (day, gtc, etc.)
        
        Returns:
            Order details dict matching BaseBroker interface:
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
        try:
            # Validate order
            is_valid, error_msg = self.validate_order(symbol, quantity, side, order_type, limit_price)
            if not is_valid:
                raise ValueError(error_msg)
            
            # Convert enums
            side_enum = self._map_order_side(side)
            tif_enum = TimeInForce.DAY  # Default to day orders
            
            # Create order request based on type
            if order_type == OrderType.MARKET:
                order_data = MarketOrderRequest(
                    symbol=symbol,
                    qty=int(quantity),
                    side=side_enum,
                    time_in_force=tif_enum
                )
            elif order_type == OrderType.LIMIT:
                order_data = LimitOrderRequest(
                    symbol=symbol,
                    qty=int(quantity),
                    side=side_enum,
                    time_in_force=tif_enum,
                    limit_price=limit_price
                )
            elif order_type == OrderType.STOP:
                order_data = StopOrderRequest(
                    symbol=symbol,
                    qty=int(quantity),
                    side=side_enum,
                    time_in_force=tif_enum,
                    stop_price=stop_price
                )
            elif order_type == OrderType.STOP_LIMIT:
                order_data = StopLimitOrderRequest(
                    symbol=symbol,
                    qty=int(quantity),
                    side=side_enum,
                    time_in_force=tif_enum,
                    limit_price=limit_price,
                    stop_price=stop_price
                )
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            # Submit order
            order = self.client.submit_order(order_data)
            
            return {
                'order_id': order.id,
                'symbol': order.symbol,
                'quantity': int(float(order.qty)),
                'side': side.value,  # Use our enum
                'order_type': order_type.value,  # Use our enum
                'status': self._map_order_status(order.status.value).value,  # Map to our enum
                'filled_quantity': int(float(order.filled_qty)) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'submitted_at': str(order.submitted_at),
                'limit_price': limit_price,
                'stop_price': stop_price
            }
        except Exception as e:
            print(f"Error placing order: {e}")
            raise
    
    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """
        Get status of an order.
        
        Args:
            order_id: Order ID to check
        
        Returns:
            Order status dict with standardized status enum
        """
        try:
            order = self.client.get_order_by_id(order_id)
            return {
                'order_id': order.id,
                'symbol': order.symbol,
                'quantity': int(float(order.qty)),
                'side': order.side.value,
                'order_type': order.order_type.value,
                'status': self._map_order_status(order.status.value).value,  # Map to our enum
                'filled_quantity': int(float(order.filled_qty)) if order.filled_qty else 0,
                'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                'submitted_at': str(order.submitted_at),
                'filled_at': str(order.filled_at) if order.filled_at else None
            }
        except Exception as e:
            print(f"Error fetching order status: {e}")
            raise
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.
        
        Args:
            order_id: Order ID to cancel
        
        Returns:
            True if successful
        """
        try:
            self.client.cancel_order_by_id(order_id)
            return True
        except Exception as e:
            print(f"Error canceling order: {e}")
            return False
    
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
            List of order dicts with standardized status enums
        """
        try:
            # Map our OrderStatus enum to Alpaca status string
            alpaca_status = None
            if status == OrderStatus.PENDING:
                alpaca_status = 'open'
            elif status == OrderStatus.FILLED:
                alpaca_status = 'closed'
            elif status == OrderStatus.CANCELLED:
                alpaca_status = 'closed'
            # If status is None, get all orders
            
            orders = self.client.get_orders(status=alpaca_status, limit=limit)
            return [
                {
                    'order_id': order.id,
                    'symbol': order.symbol,
                    'quantity': int(float(order.qty)),
                    'side': order.side.value,
                    'order_type': order.order_type.value,
                    'status': self._map_order_status(order.status.value).value,  # Map to our enum
                    'filled_quantity': int(float(order.filled_qty)) if order.filled_qty else 0,
                    'filled_avg_price': float(order.filled_avg_price) if order.filled_avg_price else None,
                    'submitted_at': str(order.submitted_at)
                }
                for order in orders
            ]
        except Exception as e:
            print(f"Error fetching orders: {e}")
            raise
    
    def close_position(self, symbol: str) -> Dict:
        """
        Close an entire position.
        
        Args:
            symbol: Symbol to close
        
        Returns:
            Order details
        """
        try:
            order = self.client.close_position(symbol)
            return {
                'order_id': order.id,
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side.value,
                'status': order.status.value
            }
        except Exception as e:
            print(f"Error closing position: {e}")
            raise
    
    def close_all_positions(self) -> List[Dict]:
        """
        Close all positions.
        
        Returns:
            List of order dicts
        """
        try:
            orders = self.client.close_all_positions(cancel_orders=True)
            return [
                {
                    'order_id': order.id,
                    'symbol': order.symbol,
                    'qty': float(order.qty),
                    'side': order.side.value,
                    'status': order.status.value
                }
                for order in orders
            ]
        except Exception as e:
            print(f"Error closing all positions: {e}")
            raise
    
    def get_quote(self, symbol: str) -> Dict[str, Any]:
        """
        Get current quote for a symbol.
        
        Args:
            symbol: Symbol to get quote for
        
        Returns:
            Quote dict with bid, ask, last price matching BaseBroker interface:
            - symbol: str
            - bid: float
            - ask: float
            - last: float
            - bid_size: int
            - ask_size: int
            - timestamp: str (ISO timestamp)
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quotes = self.data_client.get_stock_latest_quote(request)
            quote = quotes[symbol]
            
            return {
                'symbol': symbol,
                'bid': float(quote.bid_price) if quote.bid_price else None,
                'ask': float(quote.ask_price) if quote.ask_price else None,
                'bid_size': int(quote.bid_size) if quote.bid_size else None,
                'ask_size': int(quote.ask_size) if quote.ask_size else None,
                'last': float(quote.ask_price) if quote.ask_price else None,  # Use ask as fallback
                'timestamp': str(quote.timestamp) if hasattr(quote, 'timestamp') else None
            }
        except Exception as e:
            print(f"Error fetching quote for {symbol}: {e}")
            raise
    
    def is_market_open(self) -> bool:
        """
        Check if the market is currently open.
        
        Returns:
            True if market is open, False otherwise
        """
        try:
            clock = self.client.get_clock()
            return clock.is_open
        except Exception as e:
            print(f"Error checking market status: {e}")
            return False
    
    def get_market_hours(self, date: Optional[str] = None) -> Dict[str, Any]:
        """
        Get market hours for a specific date.
        
        Args:
            date: Date string in YYYY-MM-DD format (None = today)
        
        Returns:
            Dict with open/close times and current status matching BaseBroker interface:
            - is_open: bool
            - open_time: str (ISO timestamp)
            - close_time: str (ISO timestamp)
        """
        try:
            clock = self.client.get_clock()
            return {
                'is_open': clock.is_open,
                'open_time': str(clock.next_open),
                'close_time': str(clock.next_close),
                'timestamp': str(clock.timestamp)
            }
        except Exception as e:
            print(f"Error fetching market hours: {e}")
            raise
    
    def get_buying_power(self) -> float:
        """
        Get available buying power.
        
        Returns:
            Available buying power as float
        """
        try:
            account = self.client.get_account()
            return float(account.buying_power)
        except Exception as e:
            print(f"Error fetching buying power: {e}")
            raise
    
    def get_portfolio_value(self) -> float:
        """
        Get total portfolio value.
        
        Returns:
            Total portfolio value as float
        """
        try:
            account = self.client.get_account()
            return float(account.portfolio_value)
        except Exception as e:
            print(f"Error fetching portfolio value: {e}")
            raise
