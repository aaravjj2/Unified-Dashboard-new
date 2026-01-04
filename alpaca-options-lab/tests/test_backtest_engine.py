"""
Tests for src.backtesting.engine - Event-Driven Backtest Engine

Tests cover:
- Event handling and priority queue
- Position tracking
- Order management
- Callback system
- Configuration
- Result generation
"""
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
import numpy as np

from src.backtesting.engine import (
    BacktestEngine,
    BacktestConfig,
    BacktestResult,
    Event,
    EventType,
    Position,
    Order,
    OrderType,
    OrderSide,
)


class TestEventType:
    """Test EventType enum."""
    
    def test_event_types_defined(self):
        """Test all event types are defined."""
        expected_types = [
            "MARKET_DATA",
            "BAR",
            "QUOTE",
            "TRADE",
            "ORDER_SUBMITTED",
            "ORDER_FILLED",
            "ORDER_CANCELLED",
            "POSITION_OPENED",
            "POSITION_CLOSED",
            "EXPIRATION",
            "ASSIGNMENT",
            "DIVIDEND",
            "MARGIN_CALL",
            "END_OF_DAY",
            "END_OF_BACKTEST",
        ]
        
        for type_name in expected_types:
            assert hasattr(EventType, type_name)


class TestEvent:
    """Test Event dataclass."""
    
    def test_event_creation(self):
        """Test creating event."""
        event = Event(
            event_type=EventType.BAR,
            timestamp=datetime(2024, 1, 15, 10, 0),
            symbol="AAPL",
            data={"open": 150, "high": 151, "low": 149, "close": 150.5},
        )
        
        assert event.event_type == EventType.BAR
        assert event.symbol == "AAPL"
        assert event.data["close"] == 150.5
    
    def test_event_priority(self):
        """Test event priority ordering."""
        # Expiration should have higher priority than bar data
        expiration = Event(
            event_type=EventType.EXPIRATION,
            timestamp=datetime(2024, 1, 15, 10, 0),
            priority=1,
        )
        
        bar = Event(
            event_type=EventType.BAR,
            timestamp=datetime(2024, 1, 15, 10, 0),
            priority=5,
        )
        
        assert expiration.priority < bar.priority
    
    def test_event_comparison(self):
        """Test event comparison for priority queue."""
        e1 = Event(EventType.BAR, datetime(2024, 1, 15, 10, 0), priority=1)
        e2 = Event(EventType.BAR, datetime(2024, 1, 15, 10, 0), priority=2)
        
        # Lower priority number = higher priority
        assert e1 < e2


class TestPosition:
    """Test Position class."""
    
    def test_position_creation(self):
        """Test creating position."""
        pos = Position(
            symbol="AAPL240119C00150000",
            quantity=10,
            entry_price=3.50,
            entry_time=datetime(2024, 1, 10, 10, 0),
        )
        
        assert pos.symbol == "AAPL240119C00150000"
        assert pos.quantity == 10
        assert pos.entry_price == 3.50
    
    def test_position_pnl(self):
        """Test position P&L calculation."""
        pos = Position(
            symbol="AAPL240119C00150000",
            quantity=10,
            entry_price=3.50,
            entry_time=datetime(2024, 1, 10, 10, 0),
        )
        
        pos.current_price = 4.20
        
        # P&L = (4.20 - 3.50) * 10 * 100 = 700
        assert abs(pos.unrealized_pnl - 700.0) < 0.01
    
    def test_position_cost_basis(self):
        """Test position cost basis."""
        pos = Position(
            symbol="AAPL240119C00150000",
            quantity=10,
            entry_price=3.50,
            entry_time=datetime(2024, 1, 10, 10, 0),
        )
        
        # Cost = 3.50 * 10 * 100 = 3500
        assert abs(pos.cost_basis - 3500.0) < 0.01
    
    def test_short_position_pnl(self):
        """Test short position P&L."""
        pos = Position(
            symbol="AAPL240119P00145000",
            quantity=-5,  # Short
            entry_price=2.00,
            entry_time=datetime(2024, 1, 10, 10, 0),
        )
        
        pos.current_price = 1.50  # Price dropped, profit for short
        
        # P&L = (2.00 - 1.50) * 5 * 100 = 250
        assert pos.unrealized_pnl > 0


class TestOrder:
    """Test Order class."""
    
    def test_order_creation(self):
        """Test creating order."""
        order = Order(
            order_id="ORD-001",
            symbol="AAPL240119C00150000",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=10,
            limit_price=3.50,
        )
        
        assert order.order_id == "ORD-001"
        assert order.order_type == OrderType.LIMIT
        assert order.side == OrderSide.BUY
    
    def test_order_is_buy(self):
        """Test is_buy property."""
        buy_order = Order(
            order_id="ORD-001",
            symbol="AAPL",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=10,
        )
        
        sell_order = Order(
            order_id="ORD-002",
            symbol="AAPL",
            order_type=OrderType.MARKET,
            side=OrderSide.SELL,
            quantity=10,
        )
        
        assert buy_order.is_buy is True
        assert sell_order.is_buy is False


class TestBacktestConfig:
    """Test BacktestConfig."""
    
    def test_config_creation(self):
        """Test creating config."""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=100000.0,
        )
        
        assert config.start_date == datetime(2023, 1, 1)
        assert config.initial_capital == 100000.0
    
    def test_config_defaults(self):
        """Test config defaults."""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
        )
        
        assert config.initial_capital == 100000.0
        assert config.commission_per_contract == 0.65
        assert config.slippage_model == "proportional"
    
    def test_config_with_custom_settings(self):
        """Test config with custom settings."""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 12, 31),
            initial_capital=500000.0,
            commission_per_contract=0.50,
            margin_requirement=0.25,
        )
        
        assert config.initial_capital == 500000.0
        assert config.commission_per_contract == 0.50
        assert config.margin_requirement == 0.25


class TestBacktestEngine:
    """Test BacktestEngine class."""
    
    @pytest.fixture
    def config(self):
        """Create test config."""
        return BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 3, 31),
            initial_capital=100000.0,
        )
    
    @pytest.fixture
    def engine(self, config):
        """Create test engine."""
        return BacktestEngine(config)
    
    def test_engine_creation(self, engine):
        """Test engine creation."""
        assert engine is not None
        assert engine.equity == 100000.0
    
    def test_submit_order(self, engine):
        """Test order submission."""
        order = Order(
            order_id="ORD-001",
            symbol="AAPL240119C00150000",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=10,
        )
        
        engine.submit_order(order)
        
        assert "ORD-001" in engine.pending_orders
    
    def test_cancel_order(self, engine):
        """Test order cancellation."""
        order = Order(
            order_id="ORD-001",
            symbol="AAPL240119C00150000",
            order_type=OrderType.LIMIT,
            side=OrderSide.BUY,
            quantity=10,
            limit_price=3.50,
        )
        
        engine.submit_order(order)
        engine.cancel_order("ORD-001")
        
        assert "ORD-001" not in engine.pending_orders
    
    def test_add_event(self, engine):
        """Test adding event to queue."""
        event = Event(
            event_type=EventType.BAR,
            timestamp=datetime(2023, 1, 2, 10, 0),
            symbol="AAPL",
            data={"close": 150.0},
        )
        
        engine.add_event(event)
        
        assert len(engine.event_queue) > 0
    
    def test_process_event(self, engine):
        """Test processing event."""
        callback = MagicMock()
        engine.on_bar(callback)
        
        event = Event(
            event_type=EventType.BAR,
            timestamp=datetime(2023, 1, 2, 10, 0),
            symbol="AAPL",
            data={"close": 150.0},
        )
        
        engine.process_event(event)
        
        callback.assert_called_once()


class TestCallbackDecorators:
    """Test callback decorator system."""
    
    @pytest.fixture
    def engine(self):
        """Create test engine."""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 3, 31),
        )
        return BacktestEngine(config)
    
    def test_on_bar_callback(self, engine):
        """Test on_bar callback registration."""
        calls = []
        
        @engine.on_bar
        def handle_bar(event):
            calls.append(event)
        
        event = Event(
            event_type=EventType.BAR,
            timestamp=datetime(2023, 1, 2, 10, 0),
            symbol="AAPL",
            data={"close": 150.0},
        )
        
        engine.process_event(event)
        
        assert len(calls) == 1
    
    def test_on_fill_callback(self, engine):
        """Test on_fill callback registration."""
        fills = []
        
        @engine.on_fill
        def handle_fill(event):
            fills.append(event)
        
        event = Event(
            event_type=EventType.ORDER_FILLED,
            timestamp=datetime(2023, 1, 2, 10, 0),
            symbol="AAPL",
            data={"order_id": "ORD-001", "fill_price": 3.50},
        )
        
        engine.process_event(event)
        
        assert len(fills) == 1
    
    def test_on_expiration_callback(self, engine):
        """Test on_expiration callback registration."""
        expirations = []
        
        @engine.on_expiration
        def handle_expiration(event):
            expirations.append(event)
        
        event = Event(
            event_type=EventType.EXPIRATION,
            timestamp=datetime(2023, 1, 19, 16, 0),
            symbol="AAPL240119C00150000",
            data={"final_price": 155.0},
        )
        
        engine.process_event(event)
        
        assert len(expirations) == 1
    
    def test_multiple_callbacks(self, engine):
        """Test multiple callbacks for same event type."""
        calls1 = []
        calls2 = []
        
        @engine.on_bar
        def handler1(event):
            calls1.append(event)
        
        @engine.on_bar
        def handler2(event):
            calls2.append(event)
        
        event = Event(
            event_type=EventType.BAR,
            timestamp=datetime(2023, 1, 2, 10, 0),
            symbol="AAPL",
        )
        
        engine.process_event(event)
        
        assert len(calls1) == 1
        assert len(calls2) == 1


class TestPositionTracking:
    """Test position tracking during backtest."""
    
    @pytest.fixture
    def engine(self):
        """Create test engine."""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 3, 31),
        )
        return BacktestEngine(config)
    
    def test_open_position(self, engine):
        """Test opening position."""
        engine.open_position(
            symbol="AAPL240119C00150000",
            quantity=10,
            price=3.50,
            timestamp=datetime(2023, 1, 10, 10, 0),
        )
        
        assert "AAPL240119C00150000" in engine.positions
        assert engine.positions["AAPL240119C00150000"].quantity == 10
    
    def test_close_position(self, engine):
        """Test closing position."""
        engine.open_position(
            symbol="AAPL240119C00150000",
            quantity=10,
            price=3.50,
            timestamp=datetime(2023, 1, 10, 10, 0),
        )
        
        trade = engine.close_position(
            symbol="AAPL240119C00150000",
            price=4.20,
            timestamp=datetime(2023, 1, 15, 10, 0),
        )
        
        assert "AAPL240119C00150000" not in engine.positions
        assert trade["pnl"] > 0  # Profitable trade
    
    def test_partial_close(self, engine):
        """Test partial position close."""
        engine.open_position(
            symbol="AAPL240119C00150000",
            quantity=10,
            price=3.50,
            timestamp=datetime(2023, 1, 10, 10, 0),
        )
        
        engine.close_position(
            symbol="AAPL240119C00150000",
            quantity=5,  # Partial
            price=4.20,
            timestamp=datetime(2023, 1, 15, 10, 0),
        )
        
        # Should still have 5 contracts
        assert engine.positions["AAPL240119C00150000"].quantity == 5
    
    def test_add_to_position(self, engine):
        """Test adding to existing position."""
        engine.open_position(
            symbol="AAPL240119C00150000",
            quantity=10,
            price=3.50,
            timestamp=datetime(2023, 1, 10, 10, 0),
        )
        
        engine.open_position(
            symbol="AAPL240119C00150000",
            quantity=5,  # Add more
            price=3.60,
            timestamp=datetime(2023, 1, 11, 10, 0),
        )
        
        assert engine.positions["AAPL240119C00150000"].quantity == 15


class TestEquityTracking:
    """Test equity curve tracking."""
    
    @pytest.fixture
    def engine(self):
        """Create test engine."""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 3, 31),
            initial_capital=100000.0,
        )
        return BacktestEngine(config)
    
    def test_initial_equity(self, engine):
        """Test initial equity."""
        assert engine.equity == 100000.0
    
    def test_equity_after_trade(self, engine):
        """Test equity updates after trade."""
        # Open position
        engine.open_position(
            symbol="AAPL",
            quantity=10,
            price=3.50,
            timestamp=datetime(2023, 1, 10, 10, 0),
        )
        
        # Update price
        engine.update_position_price("AAPL", 4.20)
        engine.update_equity(datetime(2023, 1, 15, 16, 0))
        
        # Equity should reflect unrealized P&L
        assert engine.equity > 100000.0
    
    def test_equity_curve_recorded(self, engine):
        """Test equity curve is recorded."""
        engine.update_equity(datetime(2023, 1, 2, 16, 0))
        engine.update_equity(datetime(2023, 1, 3, 16, 0))
        
        assert len(engine.equity_curve) >= 2


class TestBacktestResult:
    """Test BacktestResult generation."""
    
    def test_result_creation(self):
        """Test creating backtest result."""
        result = BacktestResult(
            config=BacktestConfig(
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
            ),
            equity_curve=[(datetime(2023, 1, 1), 100000), (datetime(2023, 12, 31), 115000)],
            trades=[{"pnl": 1000}, {"pnl": -500}, {"pnl": 2000}],
            total_return=15000.0,
            total_return_pct=0.15,
        )
        
        assert result.total_return == 15000.0
        assert result.total_return_pct == 0.15
    
    def test_result_from_engine(self):
        """Test generating result from engine."""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 3, 31),
        )
        engine = BacktestEngine(config)
        
        # Simulate some activity
        engine.equity_curve.append((datetime(2023, 1, 1), 100000))
        engine.equity_curve.append((datetime(2023, 3, 31), 105000))
        engine.trades.append({"pnl": 2500, "symbol": "AAPL"})
        engine.trades.append({"pnl": 2500, "symbol": "MSFT"})
        
        result = engine.generate_result()
        
        assert result.total_return == 5000.0
        assert len(result.trades) == 2


class TestEventPriorityQueue:
    """Test event priority queue behavior."""
    
    @pytest.fixture
    def engine(self):
        """Create test engine."""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 3, 31),
        )
        return BacktestEngine(config)
    
    def test_events_processed_in_order(self, engine):
        """Test events are processed in timestamp order."""
        processed = []
        
        @engine.on_bar
        def handler(event):
            processed.append(event.timestamp)
        
        # Add events out of order
        engine.add_event(Event(EventType.BAR, datetime(2023, 1, 3, 10, 0)))
        engine.add_event(Event(EventType.BAR, datetime(2023, 1, 1, 10, 0)))
        engine.add_event(Event(EventType.BAR, datetime(2023, 1, 2, 10, 0)))
        
        engine.run()
        
        # Should be processed in timestamp order
        assert processed == sorted(processed)
    
    def test_priority_within_same_timestamp(self, engine):
        """Test priority ordering within same timestamp."""
        processed = []
        
        engine.register_callback(EventType.EXPIRATION, lambda e: processed.append("expiration"))
        engine.register_callback(EventType.BAR, lambda e: processed.append("bar"))
        
        same_time = datetime(2023, 1, 15, 16, 0)
        
        # Bar has lower priority
        engine.add_event(Event(EventType.BAR, same_time, priority=10))
        # Expiration has higher priority
        engine.add_event(Event(EventType.EXPIRATION, same_time, priority=1))
        
        engine.run()
        
        # Expiration should process first
        assert processed[0] == "expiration"


class TestCommissionsAndSlippage:
    """Test commission and slippage calculations."""
    
    @pytest.fixture
    def engine(self):
        """Create test engine with commissions."""
        config = BacktestConfig(
            start_date=datetime(2023, 1, 1),
            end_date=datetime(2023, 3, 31),
            commission_per_contract=0.65,
            slippage_bps=5,
        )
        return BacktestEngine(config)
    
    def test_commission_deducted(self, engine):
        """Test commission is deducted from trade."""
        initial = engine.equity
        
        engine.open_position(
            symbol="AAPL",
            quantity=10,
            price=3.50,
            timestamp=datetime(2023, 1, 10, 10, 0),
        )
        
        # Commission = 10 * 0.65 = 6.50
        assert engine.equity < initial
    
    def test_slippage_applied(self, engine):
        """Test slippage is applied to fill price."""
        # Submit buy order at limit 3.50
        order = Order(
            order_id="ORD-001",
            symbol="AAPL",
            order_type=OrderType.MARKET,
            side=OrderSide.BUY,
            quantity=10,
        )
        
        # Fill at market price 3.50
        fill = engine.simulate_fill(order, market_price=3.50)
        
        # Fill price should be slightly higher due to slippage
        assert fill["fill_price"] >= 3.50
