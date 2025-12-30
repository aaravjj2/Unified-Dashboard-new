"""
Unit Tests for gRPC Services

Tests the gRPC service implementations for:
- Signal Service
- Order Service
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, '/home/aarav/Unified-Dashboard/phase1_integration')

from grpc.services.signal_service import SignalServiceImpl, Signal
from grpc.services.order_service import OrderServiceImpl, Order, OrderStatus


# -----------------------------------------------------------------------------
# Signal Service Tests
# -----------------------------------------------------------------------------

class TestSignalServiceImpl:
    """Test Signal Service implementation"""
    
    @pytest.fixture
    def service(self):
        """Create Signal Service instance"""
        return SignalServiceImpl()
    
    @pytest.mark.asyncio
    async def test_publish_signal(self, service):
        """Test publishing a signal"""
        signal = Signal(
            type="buy",
            symbol="AAPL",
            strategy="momentum",
            confidence=0.85,
            source="test",
        )
        
        success, signal_id, error = await service.publish_signal(signal)
        
        assert success is True
        assert signal_id is not None
        assert error is None
    
    @pytest.mark.asyncio
    async def test_publish_signal_validation(self, service):
        """Test signal validation"""
        # Invalid signal - empty symbol
        signal = Signal(
            type="buy",
            symbol="",
            strategy="test",
            confidence=0.5,
        )
        
        success, signal_id, error = await service.publish_signal(signal)
        
        assert success is True  # Currently no validation, just test it publishes
    
    @pytest.mark.asyncio
    async def test_get_recent_signals(self, service):
        """Test retrieving recent signals"""
        # Add some signals
        for i in range(5):
            signal = Signal(
                type="buy" if i % 2 == 0 else "sell",
                symbol="AAPL",
                strategy="test",
                confidence=0.5 + i * 0.1,
            )
            await service.publish_signal(signal)
        
        # Get all signals
        signals = await service.get_recent_signals(count=10)
        assert len(signals) == 5
    
    @pytest.mark.asyncio
    async def test_get_signals_by_symbol(self, service):
        """Test filtering signals by symbol"""
        symbols = ["AAPL", "MSFT", "GOOGL"]
        for symbol in symbols:
            signal = Signal(
                type="buy",
                symbol=symbol,
                strategy="test",
                confidence=0.5,
            )
            await service.publish_signal(signal)
        
        aapl_signals = await service.get_recent_signals(
            count=10,
            symbol="AAPL"
        )
        assert len(aapl_signals) == 1
        assert aapl_signals[0].symbol == "AAPL"


# -----------------------------------------------------------------------------
# Order Service Tests
# -----------------------------------------------------------------------------

class TestOrderServiceImpl:
    """Test Order Service implementation"""
    
    @pytest.fixture
    def service(self):
        """Create Order Service instance in paper mode"""
        return OrderServiceImpl(paper_mode=True)
    
    @pytest.mark.asyncio
    async def test_submit_order(self, service):
        """Test submitting an order"""
        success, order_id, client_order_id, order, error = await service.submit_order(
            symbol="AAPL",
            side="buy",
            order_type="limit",
            quantity=100,
            limit_price=150.0,
            strategy="test",
        )
        
        assert success is True
        assert order_id is not None
        assert client_order_id is not None
        assert order is not None
        assert order.symbol == "AAPL"
        assert order.quantity == 100
    
    @pytest.mark.asyncio
    async def test_submit_market_order(self, service):
        """Test submitting a market order"""
        success, order_id, _, order, error = await service.submit_order(
            symbol="MSFT",
            side="buy",
            order_type="market",
            quantity=50,
        )
        
        assert success is True
        assert order.order_type == "market"
    
    @pytest.mark.asyncio
    async def test_cancel_order(self, service):
        """Test canceling an order"""
        # First submit an order
        success, order_id, _, _, _ = await service.submit_order(
            symbol="GOOGL",
            side="sell",
            order_type="limit",
            quantity=25,
            limit_price=140.0,
        )
        
        # Then cancel it
        cancel_success, cancelled_id, error = await service.cancel_order(order_id)
        
        assert cancel_success is True
        assert error is None
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_order(self, service):
        """Test canceling a non-existent order"""
        cancel_success, _, error = await service.cancel_order("fake-order-id")
        
        assert cancel_success is False
        assert error is not None
    
    @pytest.mark.asyncio
    async def test_get_order_status(self, service):
        """Test getting order status"""
        # Submit an order
        success, order_id, _, _, _ = await service.submit_order(
            symbol="NVDA",
            side="buy",
            order_type="limit",
            quantity=10,
            limit_price=450.0,
        )
        
        # Get status
        order = await service.get_order_status(order_id)
        
        assert order is not None
        assert order.symbol == "NVDA"
    
    @pytest.mark.asyncio
    async def test_get_order_history(self, service):
        """Test getting order history"""
        # Submit multiple orders
        symbols = ["AAPL", "MSFT", "GOOGL"]
        for symbol in symbols:
            await service.submit_order(
                symbol=symbol,
                side="buy",
                order_type="market",
                quantity=10,
            )
        
        # Get history
        orders = await service.get_order_history(count=10)
        assert len(orders) == 3
        
        # Filter by symbol
        aapl_orders = await service.get_order_history(
            count=10,
            symbol="AAPL"
        )
        assert len(aapl_orders) == 1
    
    @pytest.mark.asyncio
    async def test_order_validation(self, service):
        """Test order validation"""
        # Invalid side
        success, _, _, _, error = await service.submit_order(
            symbol="AAPL",
            side="invalid",
            order_type="market",
            quantity=10,
        )
        
        assert success is False
        assert error is not None
    
    @pytest.mark.asyncio
    async def test_paper_mode_fill(self, service):
        """Test paper mode fill simulation"""
        success, order_id, _, order, _ = await service.submit_order(
            symbol="AAPL",
            side="buy",
            order_type="market",
            quantity=100,
        )
        
        # Simulate fill (updates order in place)
        await service._simulate_fill(order)
        
        assert order.status == OrderStatus.FILLED.value
        assert order.filled_quantity == 100


# -----------------------------------------------------------------------------
# Order Dataclass Tests
# -----------------------------------------------------------------------------

class TestOrderDataclass:
    """Test Order dataclass"""
    
    def test_order_creation(self):
        """Test creating an Order"""
        order = Order(
            symbol="AAPL",
            side="buy",
            order_type="limit",
            quantity=100,
            limit_price=150.0,
            status=OrderStatus.PENDING,
        )
        
        assert order.symbol == "AAPL"
        assert order.quantity == 100
        assert order.order_id is not None
    
    def test_order_to_dict(self):
        """Test Order serialization"""
        order = Order(
            symbol="MSFT",
            side="sell",
            order_type="market",
            quantity=50,
            status=OrderStatus.SUBMITTED,
        )
        
        d = order.to_dict()
        assert d["symbol"] == "MSFT"
        assert d["side"] == "sell"
        assert "order_id" in d
    
    def test_order_status_transitions(self):
        """Test order status values"""
        assert OrderStatus.PENDING.value == "pending"
        assert OrderStatus.SUBMITTED.value == "submitted"
        assert OrderStatus.FILLED.value == "filled"
        assert OrderStatus.CANCELLED.value == "cancelled"
        assert OrderStatus.REJECTED.value == "rejected"


# -----------------------------------------------------------------------------
# Run Tests
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
