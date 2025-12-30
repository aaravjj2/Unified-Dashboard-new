"""
Unit Tests for Redis Pub/Sub and Streams

Tests the Redis wrapper implementations for:
- Signal/Alert dataclasses
- Order/Trade event dataclasses
"""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import json

# Add phase1 to path
sys.path.insert(0, '/home/aarav/Unified-Dashboard/phase1_integration')

from redis_client.pubsub import Signal, Alert, SignalChannel
from redis_client.streams import OrderEvent, TradeEvent


# -----------------------------------------------------------------------------
# Signal/Alert Dataclass Tests
# -----------------------------------------------------------------------------

class TestSignalDataclass:
    """Test Signal dataclass"""
    
    def test_signal_creation(self):
        """Test creating a Signal"""
        signal = Signal(
            id="test-123",
            type="buy",
            symbol="AAPL",
            strategy="momentum",
            confidence=0.85,
            source="ml_model",
            timestamp=datetime.utcnow().isoformat(),
            data={},
        )
        
        assert signal.type == "buy"
        assert signal.symbol == "AAPL"
        assert signal.strategy == "momentum"
        assert signal.confidence == 0.85
        assert signal.source == "ml_model"
        assert signal.id == "test-123"
        assert signal.timestamp is not None
    
    def test_signal_to_json(self):
        """Test Signal serialization"""
        signal = Signal(
            id="test-456",
            type="sell",
            symbol="MSFT",
            strategy="mean_reversion",
            confidence=0.75,
            source="test",
            timestamp=datetime.utcnow().isoformat(),
            data={},
        )
        
        json_str = signal.to_json()
        d = json.loads(json_str)
        assert d["type"] == "sell"
        assert d["symbol"] == "MSFT"
        assert "id" in d
        assert "timestamp" in d
    
    def test_signal_from_json(self):
        """Test Signal deserialization"""
        data = {
            "id": "test-789",
            "type": "hold",
            "symbol": "GOOGL",
            "strategy": "test",
            "confidence": 0.5,
            "timestamp": datetime.utcnow().isoformat(),
            "source": "test",
            "data": {},
        }
        
        json_str = json.dumps(data)
        signal = Signal.from_json(json_str)
        assert signal.id == "test-789"
        assert signal.symbol == "GOOGL"
    
    def test_signal_channels(self):
        """Test signal channel enum"""
        assert SignalChannel.SIGNALS.value == "alpaca:signals"
        assert SignalChannel.ALERTS.value == "alpaca:alerts"
        assert SignalChannel.PRICES.value == "alpaca:prices"


class TestAlertDataclass:
    """Test Alert dataclass"""
    
    def test_alert_creation(self):
        """Test creating an Alert"""
        alert = Alert(
            id="alert-123",
            severity="warning",
            type="risk",
            symbol="AAPL",
            message="High Exposure",
            timestamp=datetime.utcnow().isoformat(),
            data={},
        )
        
        assert alert.severity == "warning"
        assert alert.type == "risk"
        assert alert.id == "alert-123"
    
    def test_alert_to_json(self):
        """Test Alert serialization"""
        alert = Alert(
            id="alert-456",
            severity="critical",
            type="system",
            symbol="",
            message="Connection Lost",
            timestamp=datetime.utcnow().isoformat(),
            data={},
        )
        
        json_str = alert.to_json()
        d = json.loads(json_str)
        assert d["severity"] == "critical"
        assert "id" in d
    
    def test_alert_from_json(self):
        """Test Alert deserialization"""
        data = {
            "id": "alert-789",
            "severity": "info",
            "type": "trade",
            "symbol": "SPY",
            "message": "Order filled",
            "timestamp": datetime.utcnow().isoformat(),
            "data": {"fill_price": 450.0},
        }
        
        json_str = json.dumps(data)
        alert = Alert.from_json(json_str)
        assert alert.id == "alert-789"
        assert alert.data["fill_price"] == 450.0


# -----------------------------------------------------------------------------
# Order/Trade Event Tests
# -----------------------------------------------------------------------------

class TestOrderEvent:
    """Test OrderEvent dataclass"""
    
    def test_order_event_creation(self):
        """Test creating an OrderEvent"""
        event = OrderEvent(
            order_id="order-123",
            status="pending",
            symbol="AAPL",
            side="buy",
            quantity=100,
            order_type="limit",
            price=150.0,
        )
        
        assert event.order_id == "order-123"
        assert event.symbol == "AAPL"
        assert event.quantity == 100
    
    def test_order_event_to_dict(self):
        """Test OrderEvent serialization"""
        event = OrderEvent(
            order_id="order-456",
            status="filled",
            symbol="MSFT",
            side="sell",
            quantity=50,
            order_type="market",
        )
        
        d = event.to_dict()
        assert d["order_id"] == "order-456"
        assert d["status"] == "filled"
    
    def test_order_event_from_dict(self):
        """Test OrderEvent deserialization"""
        data = {
            "order_id": "order-789",
            "status": "submitted",
            "symbol": "GOOGL",
            "side": "buy",
            "quantity": "25",
            "order_type": "market",
            "price": "None",
            "filled_qty": "0",
            "avg_fill_price": "None",
            "strategy": "test",
            "legs": "[]",
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": "{}",
        }
        
        event = OrderEvent.from_dict(data)
        assert event.order_id == "order-789"


class TestTradeEvent:
    """Test TradeEvent dataclass"""
    
    def test_trade_event_creation(self):
        """Test creating a TradeEvent"""
        event = TradeEvent(
            trade_id="trade-123",
            order_id="order-123",
            symbol="NVDA",
            side="buy",
            quantity=25,
            price=450.0,
            commission=1.0,
        )
        
        assert event.trade_id == "trade-123"
        assert event.price == 450.0
        assert event.commission == 1.0
    
    def test_trade_event_to_dict(self):
        """Test TradeEvent serialization"""
        event = TradeEvent(
            trade_id="trade-456",
            order_id="order-456",
            symbol="TSLA",
            side="sell",
            quantity=10,
            price=200.0,
        )
        
        d = event.to_dict()
        assert d["trade_id"] == "trade-456"
        assert d["price"] == "200.0"


# -----------------------------------------------------------------------------
# Run Tests
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
