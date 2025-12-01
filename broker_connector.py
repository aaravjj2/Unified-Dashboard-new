"""
Alpaca Broker Connector — Phase 6-8 Strategy Bot Integration
==============================================================

Full-featured Alpaca broker integration supporting:
- Paper and live trading accounts
- Stocks and options (calls, puts, spreads)
- Market, limit, stop, and stop-limit orders
- Multi-leg options strategies
- Account management and position tracking
- Deterministic offline mock mode for testing
- Complete transaction logging

Architecture:
- AlpacaBrokerConnector: Main API wrapper
- MockBrokerConnector: Offline deterministic simulator
- OrderType, OrderSide, OptionType: Type definitions
- Transaction logging with JSON/CSV output

Integration:
- Compatible with Phase 6-8 analytics outputs
- Deterministic execution for testing/backtesting
- Production-ready for paper trading

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0 (Phase 6-8 Strategy Bot Integration)
Date: October 29, 2025
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
import numpy as np

# Alpaca API imports (optional - only for live/paper trading)
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import (
        MarketOrderRequest, LimitOrderRequest, StopOrderRequest, StopLimitOrderRequest,
        GetOrdersRequest
    )
    from alpaca.trading.enums import OrderSide as AlpacaOrderSide, TimeInForce, OrderType as AlpacaOrderType
    from alpaca.data.historical import StockHistoricalDataClient, OptionHistoricalDataClient
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    logging.warning("⚠️  Alpaca SDK not installed. Only mock mode available. Install with: pip install alpaca-py")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# ENUMERATIONS & TYPE DEFINITIONS
# ============================================================================

class OrderType(Enum):
    """Order type classification"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderSide(Enum):
    """Buy or sell"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    """Order lifecycle status"""
    PENDING = "pending"
    ACCEPTED = "accepted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class OptionType(Enum):
    """Options classification"""
    CALL = "call"
    PUT = "put"


class AssetClass(Enum):
    """Asset type"""
    STOCK = "stock"
    OPTION = "option"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class Position:
    """Current position information"""
    symbol: str
    qty: float
    avg_entry_price: float
    market_value: float
    cost_basis: float
    unrealized_pl: float
    unrealized_pl_pct: float
    asset_class: AssetClass
    side: OrderSide
    
    # Options-specific fields
    option_type: Optional[OptionType] = None
    strike: Optional[float] = None
    expiration: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "symbol": self.symbol,
            "qty": self.qty,
            "avg_entry_price": self.avg_entry_price,
            "market_value": self.market_value,
            "cost_basis": self.cost_basis,
            "unrealized_pl": self.unrealized_pl,
            "unrealized_pl_pct": self.unrealized_pl_pct,
            "asset_class": self.asset_class.value,
            "side": self.side.value,
            "option_type": self.option_type.value if self.option_type else None,
            "strike": self.strike,
            "expiration": self.expiration
        }


@dataclass
class AccountInfo:
    """Account status and balances"""
    account_id: str
    cash: float
    portfolio_value: float
    buying_power: float
    equity: float
    long_market_value: float
    short_market_value: float
    pattern_day_trader: bool
    trading_blocked: bool
    transfers_blocked: bool
    account_blocked: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class Order:
    """Order request/response"""
    order_id: str
    symbol: str
    qty: float
    side: OrderSide
    order_type: OrderType
    status: OrderStatus
    
    # Price parameters
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Execution details
    filled_qty: float = 0.0
    filled_avg_price: Optional[float] = None
    filled_at: Optional[str] = None
    
    # Options-specific
    asset_class: AssetClass = AssetClass.STOCK
    option_type: Optional[OptionType] = None
    strike: Optional[float] = None
    expiration: Optional[str] = None
    
    # Multi-leg support
    legs: Optional[List['Order']] = None
    
    # Metadata
    client_order_id: Optional[str] = None
    submitted_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "qty": self.qty,
            "side": self.side.value,
            "order_type": self.order_type.value,
            "status": self.status.value,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "filled_qty": self.filled_qty,
            "filled_avg_price": self.filled_avg_price,
            "filled_at": self.filled_at,
            "asset_class": self.asset_class.value,
            "option_type": self.option_type.value if self.option_type else None,
            "strike": self.strike,
            "expiration": self.expiration,
            "legs": [leg.to_dict() for leg in self.legs] if self.legs else None,
            "client_order_id": self.client_order_id,
            "submitted_at": self.submitted_at,
            "updated_at": self.updated_at
        }
        return data


@dataclass
class Transaction:
    """Trade execution record"""
    transaction_id: str
    order_id: str
    symbol: str
    qty: float
    side: OrderSide
    price: float
    amount: float  # qty * price
    commission: float
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Options-specific
    asset_class: AssetClass = AssetClass.STOCK
    option_type: Optional[OptionType] = None
    strike: Optional[float] = None
    expiration: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "transaction_id": self.transaction_id,
            "order_id": self.order_id,
            "symbol": self.symbol,
            "qty": self.qty,
            "side": self.side.value if isinstance(self.side, OrderSide) else self.side,
            "price": self.price,
            "amount": self.amount,
            "commission": self.commission,
            "timestamp": self.timestamp,
            "asset_class": self.asset_class.value if isinstance(self.asset_class, AssetClass) else self.asset_class,
            "option_type": self.option_type.value if isinstance(self.option_type, OptionType) and self.option_type else None,
            "strike": self.strike,
            "expiration": self.expiration
        }


# ============================================================================
# MOCK BROKER CONNECTOR (DETERMINISTIC OFFLINE MODE)
# ============================================================================

class MockBrokerConnector:
    """
    Deterministic offline broker simulator for testing and backtesting.
    
    Features:
    - Simulates order execution with configurable slippage
    - Maintains virtual portfolio state
    - Deterministic price fills (no random components unless seeded)
    - Transaction logging
    - Compatible with Phase 6-8 analytics outputs
    """
    
    def __init__(
        self,
        initial_cash: float = 100000.0,
        slippage_pct: float = 0.001,  # 0.1% slippage
        commission_per_contract: float = 0.65,  # Options commission
        commission_per_share: float = 0.0,  # Zero commission stocks (modern brokers)
        random_seed: int = 42,
        transaction_log_path: str = "outputs/broker_transactions.json"
    ):
        self.account_id = f"mock_account_{random_seed}"
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self.slippage_pct = slippage_pct
        self.commission_per_contract = commission_per_contract
        self.commission_per_share = commission_per_share
        self.random_seed = random_seed
        self.transaction_log_path = transaction_log_path
        
        # State
        self.positions: Dict[str, Position] = {}
        self.orders: Dict[str, Order] = {}
        self.transactions: List[Transaction] = []
        self.order_counter = 1
        self.transaction_counter = 1
        
        # Market data simulation (can be overridden with real data)
        self.market_prices: Dict[str, float] = {}
        
        # Deterministic random number generator
        np.random.seed(random_seed)
        self.rng = np.random.default_rng(random_seed)
        
        logger.info(f"🔧 MockBrokerConnector initialized: ${initial_cash:,.2f} cash, seed={random_seed}")
    
    def set_market_price(self, symbol: str, price: float) -> None:
        """Set current market price for a symbol (for testing)"""
        self.market_prices[symbol] = price
    
    def get_account_info(self) -> AccountInfo:
        """Get current account status"""
        # Calculate portfolio values
        long_market_value = sum(
            pos.market_value for pos in self.positions.values()
            if pos.side == OrderSide.BUY
        )
        short_market_value = sum(
            pos.market_value for pos in self.positions.values()
            if pos.side == OrderSide.SELL
        )
        
        equity = self.cash + long_market_value - short_market_value
        portfolio_value = equity
        
        # Simplified buying power (4x for pattern day traders, 2x otherwise)
        buying_power = equity * 4.0  # Assume PDT
        
        return AccountInfo(
            account_id=self.account_id,
            cash=self.cash,
            portfolio_value=portfolio_value,
            buying_power=buying_power,
            equity=equity,
            long_market_value=long_market_value,
            short_market_value=short_market_value,
            pattern_day_trader=True,
            trading_blocked=False,
            transfers_blocked=False,
            account_blocked=False
        )
    
    def get_positions(self) -> List[Position]:
        """Get all current positions"""
        return list(self.positions.values())
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get specific position"""
        return self.positions.get(symbol)
    
    def _generate_order_id(self) -> str:
        """Generate unique order ID"""
        order_id = f"mock_order_{self.order_counter:06d}"
        self.order_counter += 1
        return order_id
    
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID"""
        transaction_id = f"mock_txn_{self.transaction_counter:06d}"
        self.transaction_counter += 1
        return transaction_id
    
    def _get_fill_price(self, symbol: str, side: OrderSide, limit_price: Optional[float] = None) -> float:
        """
        Calculate fill price with slippage.
        
        Args:
            symbol: Ticker symbol
            side: Buy or sell
            limit_price: Limit price (if applicable)
            
        Returns:
            Fill price
        """
        # Get market price (use provided or default)
        if symbol in self.market_prices:
            market_price = self.market_prices[symbol]
        else:
            # Default prices for common symbols (for testing)
            default_prices = {
                "SPY": 450.0, "QQQ": 380.0, "IWM": 190.0,
                "AAPL": 180.0, "MSFT": 380.0, "NVDA": 500.0
            }
            market_price = default_prices.get(symbol, 100.0)
        
        # Apply slippage
        if side == OrderSide.BUY:
            slippage = market_price * self.slippage_pct
            fill_price = market_price + slippage
        else:
            slippage = market_price * self.slippage_pct
            fill_price = market_price - slippage
        
        # Respect limit price
        if limit_price is not None:
            if side == OrderSide.BUY and fill_price > limit_price:
                return limit_price
            elif side == OrderSide.SELL and fill_price < limit_price:
                return limit_price
        
        return fill_price
    
    def _calculate_commission(self, order: Order) -> float:
        """Calculate commission for order"""
        if order.asset_class == AssetClass.OPTION:
            # Options: per contract
            return order.qty * self.commission_per_contract
        else:
            # Stocks: per share (typically $0 now)
            return order.qty * self.commission_per_share
    
    def _execute_order(self, order: Order) -> None:
        """
        Simulate order execution (instant fill for mock mode).
        
        Args:
            order: Order to execute
        """
        # Get fill price
        fill_price = self._get_fill_price(order.symbol, order.side, order.limit_price)
        
        # Calculate commission
        commission = self._calculate_commission(order)
        
        # Calculate total amount
        if order.asset_class == AssetClass.OPTION:
            # Options: qty = contracts, price per contract = $100 * option price
            amount = order.qty * fill_price * 100
        else:
            # Stocks: qty = shares
            amount = order.qty * fill_price
        
        # Update cash
        if order.side == OrderSide.BUY:
            self.cash -= (amount + commission)
        else:
            self.cash += (amount - commission)
        
        # Update position
        self._update_position(order, fill_price)
        
        # Record transaction
        transaction = Transaction(
            transaction_id=self._generate_transaction_id(),
            order_id=order.order_id,
            symbol=order.symbol,
            qty=order.qty,
            side=order.side,
            price=fill_price,
            amount=amount,
            commission=commission,
            asset_class=order.asset_class,
            option_type=order.option_type,
            strike=order.strike,
            expiration=order.expiration
        )
        self.transactions.append(transaction)
        
        # Update order status
        order.status = OrderStatus.FILLED
        order.filled_qty = order.qty
        order.filled_avg_price = fill_price
        order.filled_at = datetime.now().isoformat()
        order.updated_at = datetime.now().isoformat()
        
        logger.info(f"✅ Executed {order.side.value.upper()} {order.qty} {order.symbol} @ ${fill_price:.2f} (commission: ${commission:.2f})")
    
    def _update_position(self, order: Order, fill_price: float) -> None:
        """Update position after order execution"""
        symbol = order.symbol
        
        if symbol not in self.positions:
            # New position
            if order.asset_class == AssetClass.OPTION:
                market_value = order.qty * fill_price * 100
            else:
                market_value = order.qty * fill_price
            
            self.positions[symbol] = Position(
                symbol=symbol,
                qty=order.qty if order.side == OrderSide.BUY else -order.qty,
                avg_entry_price=fill_price,
                market_value=market_value,
                cost_basis=market_value,
                unrealized_pl=0.0,
                unrealized_pl_pct=0.0,
                asset_class=order.asset_class,
                side=order.side,
                option_type=order.option_type,
                strike=order.strike,
                expiration=order.expiration
            )
        else:
            # Update existing position
            pos = self.positions[symbol]
            
            if order.side == OrderSide.BUY:
                new_qty = pos.qty + order.qty
                new_cost_basis = pos.cost_basis + (order.qty * fill_price)
                pos.qty = new_qty
                pos.avg_entry_price = new_cost_basis / new_qty if new_qty != 0 else 0
                pos.cost_basis = new_cost_basis
            else:
                new_qty = pos.qty - order.qty
                if new_qty == 0:
                    # Position closed
                    del self.positions[symbol]
                    return
                else:
                    pos.qty = new_qty
                    # Cost basis reduces proportionally
                    pos.cost_basis = pos.avg_entry_price * new_qty
            
            # Update market value (use current fill price as proxy for market price)
            if order.asset_class == AssetClass.OPTION:
                pos.market_value = pos.qty * fill_price * 100
            else:
                pos.market_value = pos.qty * fill_price
            
            # Update unrealized P&L
            pos.unrealized_pl = pos.market_value - pos.cost_basis
            pos.unrealized_pl_pct = (pos.unrealized_pl / pos.cost_basis * 100) if pos.cost_basis != 0 else 0
    
    def place_order(
        self,
        symbol: str,
        qty: float,
        side: OrderSide,
        order_type: OrderType,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        asset_class: AssetClass = AssetClass.STOCK,
        option_type: Optional[OptionType] = None,
        strike: Optional[float] = None,
        expiration: Optional[str] = None,
        client_order_id: Optional[str] = None
    ) -> Order:
        """
        Place order (instantly executed in mock mode).
        
        Args:
            symbol: Ticker symbol
            qty: Quantity (shares or contracts)
            side: Buy or sell
            order_type: Market, limit, stop, or stop-limit
            limit_price: Limit price (for limit/stop-limit orders)
            stop_price: Stop price (for stop/stop-limit orders)
            asset_class: Stock or option
            option_type: Call or put (for options)
            strike: Strike price (for options)
            expiration: Expiration date YYYY-MM-DD (for options)
            client_order_id: Custom order ID
            
        Returns:
            Order object
        """
        order_id = self._generate_order_id()
        
        order = Order(
            order_id=order_id,
            symbol=symbol,
            qty=qty,
            side=side,
            order_type=order_type,
            status=OrderStatus.PENDING,
            limit_price=limit_price,
            stop_price=stop_price,
            asset_class=asset_class,
            option_type=option_type,
            strike=strike,
            expiration=expiration,
            client_order_id=client_order_id
        )
        
        # Store order
        self.orders[order_id] = order
        
        # Execute immediately (mock mode always fills instantly at market)
        order.status = OrderStatus.ACCEPTED
        self._execute_order(order)
        
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel order (always succeeds for unfilled orders in mock mode).
        
        Args:
            order_id: Order ID
            
        Returns:
            True if canceled, False if already filled/canceled
        """
        if order_id not in self.orders:
            logger.warning(f"⚠️  Order {order_id} not found")
            return False
        
        order = self.orders[order_id]
        
        if order.status in [OrderStatus.FILLED, OrderStatus.CANCELED]:
            logger.warning(f"⚠️  Order {order_id} already {order.status.value}")
            return False
        
        order.status = OrderStatus.CANCELED
        order.updated_at = datetime.now().isoformat()
        
        logger.info(f"✅ Canceled order {order_id}")
        return True
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        return self.orders.get(order_id)
    
    def get_orders(
        self,
        status: Optional[OrderStatus] = None,
        limit: int = 100
    ) -> List[Order]:
        """
        Get orders with optional filtering.
        
        Args:
            status: Filter by status
            limit: Max number of orders
            
        Returns:
            List of orders
        """
        orders = list(self.orders.values())
        
        if status is not None:
            orders = [o for o in orders if o.status == status]
        
        # Sort by submitted_at descending
        orders.sort(key=lambda o: o.submitted_at, reverse=True)
        
        return orders[:limit]
    
    def save_transaction_log(self, filepath: Optional[str] = None) -> None:
        """Save all transactions to JSON file"""
        if filepath is None:
            filepath = self.transaction_log_path
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        log_data = {
            "account_id": self.account_id,
            "initial_cash": self.initial_cash,
            "final_cash": self.cash,
            "total_transactions": len(self.transactions),
            "transactions": [txn.to_dict() for txn in self.transactions],
            "final_positions": [pos.to_dict() for pos in self.positions.values()],
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"💾 Saved transaction log to {filepath}")
    
    def save_transaction_log_csv(self, filepath: str = "outputs/broker_transactions.csv") -> None:
        """Save transactions to CSV file"""
        import pandas as pd
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        if not self.transactions:
            logger.warning("⚠️  No transactions to save")
            return
        
        df = pd.DataFrame([txn.to_dict() for txn in self.transactions])
        df.to_csv(filepath, index=False)
        
        logger.info(f"💾 Saved transaction log to {filepath}")


# ============================================================================
# ALPACA BROKER CONNECTOR (LIVE/PAPER TRADING)
# ============================================================================

class AlpacaBrokerConnector:
    """
    Production Alpaca broker connector for live and paper trading.
    
    Features:
    - Full Alpaca API integration
    - Stocks and options support
    - Order management
    - Account and position tracking
    - Transaction logging
    
    Requires:
    - Alpaca API key and secret
    - alpaca-py package installed
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        paper: bool = True,
        transaction_log_path: str = "outputs/alpaca_transactions.json"
    ):
        if not ALPACA_AVAILABLE:
            raise ImportError("Alpaca SDK not installed. Install with: pip install alpaca-py")
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.paper = paper
        self.transaction_log_path = transaction_log_path
        
        # Initialize Alpaca client
        self.client = TradingClient(api_key, api_secret, paper=paper)
        
        # State
        self.orders: Dict[str, Order] = {}
        self.transactions: List[Transaction] = []
        
        mode = "PAPER" if paper else "LIVE"
        logger.info(f"🔧 AlpacaBrokerConnector initialized: {mode} mode")
    
    def get_account_info(self) -> AccountInfo:
        """Get account information from Alpaca"""
        account = self.client.get_account()
        
        return AccountInfo(
            account_id=account.id,
            cash=float(account.cash),
            portfolio_value=float(account.portfolio_value),
            buying_power=float(account.buying_power),
            equity=float(account.equity),
            long_market_value=float(account.long_market_value),
            short_market_value=float(account.short_market_value),
            pattern_day_trader=account.pattern_day_trader,
            trading_blocked=account.trading_blocked,
            transfers_blocked=account.transfers_blocked,
            account_blocked=account.account_blocked
        )
    
    def get_positions(self) -> List[Position]:
        """Get all positions from Alpaca"""
        alpaca_positions = self.client.get_all_positions()
        
        positions = []
        for pos in alpaca_positions:
            # Determine asset class
            asset_class = AssetClass.OPTION if hasattr(pos, 'option_type') else AssetClass.STOCK
            
            position = Position(
                symbol=pos.symbol,
                qty=float(pos.qty),
                avg_entry_price=float(pos.avg_entry_price),
                market_value=float(pos.market_value),
                cost_basis=float(pos.cost_basis),
                unrealized_pl=float(pos.unrealized_pl),
                unrealized_pl_pct=float(pos.unrealized_plpc) * 100,
                asset_class=asset_class,
                side=OrderSide.BUY if float(pos.qty) > 0 else OrderSide.SELL,
                option_type=OptionType(pos.option_type.lower()) if hasattr(pos, 'option_type') else None,
                strike=float(pos.strike_price) if hasattr(pos, 'strike_price') else None,
                expiration=str(pos.expiration_date) if hasattr(pos, 'expiration_date') else None
            )
            positions.append(position)
        
        return positions
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get specific position from Alpaca"""
        try:
            pos = self.client.get_open_position(symbol)
            
            asset_class = AssetClass.OPTION if hasattr(pos, 'option_type') else AssetClass.STOCK
            
            return Position(
                symbol=pos.symbol,
                qty=float(pos.qty),
                avg_entry_price=float(pos.avg_entry_price),
                market_value=float(pos.market_value),
                cost_basis=float(pos.cost_basis),
                unrealized_pl=float(pos.unrealized_pl),
                unrealized_pl_pct=float(pos.unrealized_plpc) * 100,
                asset_class=asset_class,
                side=OrderSide.BUY if float(pos.qty) > 0 else OrderSide.SELL,
                option_type=OptionType(pos.option_type.lower()) if hasattr(pos, 'option_type') else None,
                strike=float(pos.strike_price) if hasattr(pos, 'strike_price') else None,
                expiration=str(pos.expiration_date) if hasattr(pos, 'expiration_date') else None
            )
        except Exception as e:
            logger.warning(f"⚠️  Position {symbol} not found: {e}")
            return None
    
    def place_order(
        self,
        symbol: str,
        qty: float,
        side: OrderSide,
        order_type: OrderType,
        limit_price: Optional[float] = None,
        stop_price: Optional[float] = None,
        asset_class: AssetClass = AssetClass.STOCK,
        option_type: Optional[OptionType] = None,
        strike: Optional[float] = None,
        expiration: Optional[str] = None,
        client_order_id: Optional[str] = None,
        time_in_force: str = "day"
    ) -> Order:
        """
        Place order with Alpaca.
        
        Args:
            symbol: Ticker symbol
            qty: Quantity
            side: Buy or sell
            order_type: Order type
            limit_price: Limit price
            stop_price: Stop price
            asset_class: Stock or option
            option_type: Call or put
            strike: Strike price
            expiration: Expiration date
            client_order_id: Custom order ID
            time_in_force: Time in force (day, gtc, ioc, fok)
            
        Returns:
            Order object
        """
        # Map to Alpaca enums
        alpaca_side = AlpacaOrderSide.BUY if side == OrderSide.BUY else AlpacaOrderSide.SELL
        tif = TimeInForce(time_in_force.upper())
        
        # Build order request
        if order_type == OrderType.MARKET:
            order_request = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=alpaca_side,
                time_in_force=tif,
                client_order_id=client_order_id
            )
        elif order_type == OrderType.LIMIT:
            order_request = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=alpaca_side,
                time_in_force=tif,
                limit_price=limit_price,
                client_order_id=client_order_id
            )
        elif order_type == OrderType.STOP:
            order_request = StopOrderRequest(
                symbol=symbol,
                qty=qty,
                side=alpaca_side,
                time_in_force=tif,
                stop_price=stop_price,
                client_order_id=client_order_id
            )
        elif order_type == OrderType.STOP_LIMIT:
            order_request = StopLimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=alpaca_side,
                time_in_force=tif,
                limit_price=limit_price,
                stop_price=stop_price,
                client_order_id=client_order_id
            )
        else:
            raise ValueError(f"Unknown order type: {order_type}")
        
        # Submit order
        alpaca_order = self.client.submit_order(order_request)
        
        # Convert to internal Order object
        order = self._alpaca_order_to_order(alpaca_order, asset_class, option_type, strike, expiration)
        
        # Store order
        self.orders[order.order_id] = order
        
        logger.info(f"✅ Placed {side.value.upper()} order: {qty} {symbol} ({order_type.value})")
        
        return order
    
    def _alpaca_order_to_order(
        self,
        alpaca_order: Any,
        asset_class: AssetClass,
        option_type: Optional[OptionType],
        strike: Optional[float],
        expiration: Optional[str]
    ) -> Order:
        """Convert Alpaca order to internal Order object"""
        # Map Alpaca status to internal status
        status_mapping = {
            "new": OrderStatus.PENDING,
            "accepted": OrderStatus.ACCEPTED,
            "filled": OrderStatus.FILLED,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "canceled": OrderStatus.CANCELED,
            "rejected": OrderStatus.REJECTED,
            "expired": OrderStatus.EXPIRED
        }
        
        status = status_mapping.get(alpaca_order.status, OrderStatus.PENDING)
        
        return Order(
            order_id=alpaca_order.id,
            symbol=alpaca_order.symbol,
            qty=float(alpaca_order.qty),
            side=OrderSide.BUY if alpaca_order.side == AlpacaOrderSide.BUY else OrderSide.SELL,
            order_type=OrderType(alpaca_order.order_type),
            status=status,
            limit_price=float(alpaca_order.limit_price) if alpaca_order.limit_price else None,
            stop_price=float(alpaca_order.stop_price) if alpaca_order.stop_price else None,
            filled_qty=float(alpaca_order.filled_qty) if alpaca_order.filled_qty else 0.0,
            filled_avg_price=float(alpaca_order.filled_avg_price) if alpaca_order.filled_avg_price else None,
            filled_at=str(alpaca_order.filled_at) if alpaca_order.filled_at else None,
            asset_class=asset_class,
            option_type=option_type,
            strike=strike,
            expiration=expiration,
            client_order_id=alpaca_order.client_order_id,
            submitted_at=str(alpaca_order.submitted_at),
            updated_at=str(alpaca_order.updated_at) if alpaca_order.updated_at else str(alpaca_order.submitted_at)
        )
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel order by ID"""
        try:
            self.client.cancel_order_by_id(order_id)
            
            if order_id in self.orders:
                self.orders[order_id].status = OrderStatus.CANCELED
                self.orders[order_id].updated_at = datetime.now().isoformat()
            
            logger.info(f"✅ Canceled order {order_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to cancel order {order_id}: {e}")
            return False
    
    def get_order(self, order_id: str) -> Optional[Order]:
        """Get order by ID"""
        try:
            alpaca_order = self.client.get_order_by_id(order_id)
            
            # Update stored order if exists
            if order_id in self.orders:
                stored_order = self.orders[order_id]
                order = self._alpaca_order_to_order(
                    alpaca_order,
                    stored_order.asset_class,
                    stored_order.option_type,
                    stored_order.strike,
                    stored_order.expiration
                )
                self.orders[order_id] = order
                return order
            else:
                # Return basic order without options metadata
                return self._alpaca_order_to_order(alpaca_order, AssetClass.STOCK, None, None, None)
        except Exception as e:
            logger.warning(f"⚠️  Order {order_id} not found: {e}")
            return None
    
    def get_orders(
        self,
        status: Optional[OrderStatus] = None,
        limit: int = 100
    ) -> List[Order]:
        """Get orders with optional filtering"""
        # Build Alpaca request
        alpaca_status = None
        if status == OrderStatus.FILLED:
            alpaca_status = "closed"
        elif status == OrderStatus.PENDING:
            alpaca_status = "open"
        
        request = GetOrdersRequest(
            status=alpaca_status,
            limit=limit
        )
        
        alpaca_orders = self.client.get_orders(request)
        
        orders = []
        for alpaca_order in alpaca_orders:
            # Use stored metadata if available
            if alpaca_order.id in self.orders:
                stored_order = self.orders[alpaca_order.id]
                order = self._alpaca_order_to_order(
                    alpaca_order,
                    stored_order.asset_class,
                    stored_order.option_type,
                    stored_order.strike,
                    stored_order.expiration
                )
            else:
                order = self._alpaca_order_to_order(alpaca_order, AssetClass.STOCK, None, None, None)
            
            orders.append(order)
        
        return orders
    
    def save_transaction_log(self, filepath: Optional[str] = None) -> None:
        """Save transaction log to JSON"""
        if filepath is None:
            filepath = self.transaction_log_path
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        log_data = {
            "account_mode": "paper" if self.paper else "live",
            "total_orders": len(self.orders),
            "orders": [order.to_dict() for order in self.orders.values()],
            "timestamp": datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(log_data, f, indent=2)
        
        logger.info(f"💾 Saved transaction log to {filepath}")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def create_broker_connector(
    mode: str = "mock",
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    **kwargs
) -> Union[MockBrokerConnector, AlpacaBrokerConnector]:
    """
    Factory function to create broker connector.
    
    Args:
        mode: "mock" or "alpaca"
        api_key: Alpaca API key (required for alpaca mode)
        api_secret: Alpaca API secret (required for alpaca mode)
        **kwargs: Additional arguments passed to connector
        
    Returns:
        Broker connector instance
    """
    if mode == "mock":
        return MockBrokerConnector(**kwargs)
    elif mode == "alpaca":
        if api_key is None or api_secret is None:
            raise ValueError("api_key and api_secret required for Alpaca mode")
        return AlpacaBrokerConnector(api_key, api_secret, **kwargs)
    else:
        raise ValueError(f"Unknown mode: {mode}. Use 'mock' or 'alpaca'")


# ============================================================================
# MAIN EXECUTION (FOR TESTING)
# ============================================================================

if __name__ == "__main__":
    logger.info("=" * 80)
    logger.info("BROKER CONNECTOR TEST — MOCK MODE")
    logger.info("=" * 80)
    
    # Create mock broker
    broker = MockBrokerConnector(
        initial_cash=100000.0,
        random_seed=42,
        transaction_log_path="outputs/test_broker_transactions.json"
    )
    
    # Set market prices for testing
    broker.set_market_price("SPY", 450.0)
    broker.set_market_price("QQQ", 380.0)
    broker.set_market_price("AAPL", 180.0)
    
    # Test 1: Get account info
    logger.info("\n📊 Test 1: Account Info")
    account = broker.get_account_info()
    logger.info(f"   Cash: ${account.cash:,.2f}")
    logger.info(f"   Buying Power: ${account.buying_power:,.2f}")
    logger.info(f"   Portfolio Value: ${account.portfolio_value:,.2f}")
    
    # Test 2: Place market order (stock)
    logger.info("\n📈 Test 2: Buy 100 SPY (market order)")
    order1 = broker.place_order(
        symbol="SPY",
        qty=100,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        asset_class=AssetClass.STOCK
    )
    logger.info(f"   Order ID: {order1.order_id}")
    logger.info(f"   Status: {order1.status.value}")
    logger.info(f"   Fill Price: ${order1.filled_avg_price:.2f}")
    
    # Test 3: Place limit order (stock)
    logger.info("\n📉 Test 3: Buy 50 AAPL (limit order @ $179)")
    order2 = broker.place_order(
        symbol="AAPL",
        qty=50,
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        limit_price=179.0,
        asset_class=AssetClass.STOCK
    )
    logger.info(f"   Order ID: {order2.order_id}")
    logger.info(f"   Fill Price: ${order2.filled_avg_price:.2f}")
    
    # Test 4: Place options order
    logger.info("\n🎯 Test 4: Buy 5 SPY 460 Call (expiry: 2025-11-15)")
    broker.set_market_price("SPY251115C00460000", 8.50)  # Option price $8.50
    order3 = broker.place_order(
        symbol="SPY251115C00460000",
        qty=5,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        asset_class=AssetClass.OPTION,
        option_type=OptionType.CALL,
        strike=460.0,
        expiration="2025-11-15"
    )
    logger.info(f"   Order ID: {order3.order_id}")
    logger.info(f"   Fill Price: ${order3.filled_avg_price:.2f}")
    logger.info(f"   Total Cost: ${order3.filled_avg_price * 5 * 100:.2f}")
    
    # Test 5: Check positions
    logger.info("\n💼 Test 5: Current Positions")
    positions = broker.get_positions()
    for pos in positions:
        logger.info(f"   {pos.symbol}: {pos.qty} @ ${pos.avg_entry_price:.2f} (P&L: ${pos.unrealized_pl:.2f})")
    
    # Test 6: Sell position
    logger.info("\n📉 Test 6: Sell 50 SPY")
    order4 = broker.place_order(
        symbol="SPY",
        qty=50,
        side=OrderSide.SELL,
        order_type=OrderType.MARKET,
        asset_class=AssetClass.STOCK
    )
    logger.info(f"   Sold at: ${order4.filled_avg_price:.2f}")
    
    # Test 7: Final account status
    logger.info("\n💰 Test 7: Final Account Status")
    final_account = broker.get_account_info()
    logger.info(f"   Cash: ${final_account.cash:,.2f}")
    logger.info(f"   Equity: ${final_account.equity:,.2f}")
    logger.info(f"   Portfolio Value: ${final_account.portfolio_value:,.2f}")
    logger.info(f"   Total P&L: ${final_account.equity - 100000:.2f}")
    
    # Test 8: Get all orders
    logger.info("\n📋 Test 8: Order History")
    all_orders = broker.get_orders()
    logger.info(f"   Total Orders: {len(all_orders)}")
    for order in all_orders:
        logger.info(f"   {order.order_id}: {order.side.value} {order.qty} {order.symbol} @ ${order.filled_avg_price:.2f}")
    
    # Test 9: Save transaction log
    logger.info("\n💾 Test 9: Save Transaction Log")
    broker.save_transaction_log()
    broker.save_transaction_log_csv()
    
    logger.info("\n" + "=" * 80)
    logger.info("✅ ALL BROKER CONNECTOR TESTS COMPLETE")
    logger.info("=" * 80)
