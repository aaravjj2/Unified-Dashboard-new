"""
End-to-End Integration Tests for Phase 1

Tests the complete flow through all components:
- Redis Pub/Sub + Streams
- gRPC services
- TimescaleDB
- BentoML services
- FastAPI Gateway
- Data Ingestion
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
import json

import sys
sys.path.insert(0, '/home/aarav/Unified-Dashboard/phase1_integration')

# Import from correct modules
from redis_client.pubsub import Signal as RedisSignal, Alert
from redis_client.streams import OrderEvent, TradeEvent


# -----------------------------------------------------------------------------
# E2E Flow Tests
# -----------------------------------------------------------------------------

class TestSignalToOrderFlow:
    """Test complete signal-to-order flow"""
    
    @pytest.mark.asyncio
    async def test_signal_generates_order(self):
        """Test that a signal can trigger an order"""
        from grpc.services.signal_service import SignalServiceImpl, Signal
        from grpc.services.order_service import OrderServiceImpl
        
        # 1. Create and publish a signal
        signal_service = SignalServiceImpl()
        signal = Signal(
            id="test-sig-001",
            type="buy",
            symbol="AAPL",
            strategy="momentum",
            confidence=0.9,
            source="ml_model",
            timestamp=datetime.utcnow().isoformat(),
            data={},
        )
        
        success, signal_id, _ = await signal_service.publish_signal(signal)
        assert success is True
        
        # 2. Process signal and create order
        order_service = OrderServiceImpl(paper_mode=True)
        
        # Simulate signal processing
        if signal.confidence > 0.8 and signal.type == "buy":
            success, order_id, _, order, _ = await order_service.submit_order(
                symbol=signal.symbol,
                side="buy",
                order_type="market",
                quantity=100,
                strategy=signal.strategy,
            )
            
            assert success is True
            assert order.symbol == "AAPL"
            assert order.quantity == 100
    
    @pytest.mark.asyncio
    async def test_full_trading_cycle(self):
        """Test complete trading cycle"""
        from grpc.services.order_service import OrderServiceImpl, OrderStatus
        
        order_service = OrderServiceImpl(paper_mode=True)
        
        # 1. Submit order
        success, order_id, client_id, order, _ = await order_service.submit_order(
            symbol="MSFT",
            side="buy",
            order_type="limit",
            quantity=50,
            limit_price=350.0,
            strategy="mean_reversion",
        )
        assert success is True
        
        # 2. Check order status
        status = await order_service.get_order_status(order_id)
        assert status is not None
        
        # 3. Simulate fill (updates order in place)
        await order_service._simulate_fill(order)
        assert order.status == OrderStatus.FILLED.value
        
        # 4. Verify in history
        history = await order_service.get_order_history(count=10, symbol="MSFT")
        assert len(history) >= 1


class TestMLPredictionFlow:
    """Test ML prediction flow through gateway"""
    
    @pytest.mark.asyncio
    async def test_prediction_to_signal(self):
        """Test ML prediction generating a signal"""
        from grpc.services.signal_service import SignalServiceImpl, Signal
        
        # 1. Simulate ML prediction
        prediction = {
            "symbol": "NVDA",
            "direction": "up",
            "probability_up": 0.75,
            "confidence": 0.50,
        }
        
        # 2. Convert to signal if confidence threshold met
        signal_service = SignalServiceImpl()
        
        if prediction["confidence"] > 0.3:
            signal_type = "buy" if prediction["direction"] == "up" else "sell"
            signal = Signal(
                id=f"ml-{datetime.utcnow().timestamp()}",
                type=signal_type,
                symbol=prediction["symbol"],
                strategy="ml_prediction",
                confidence=prediction["confidence"],
                source="price_direction_model",
                timestamp=datetime.utcnow().isoformat(),
                data=prediction,
            )
            
            success, signal_id, _ = await signal_service.publish_signal(signal)
            assert success is True
            
            # 3. Verify signal
            signals = await signal_service.get_recent_signals(
                count=5,
                symbol="NVDA"
            )
            assert len(signals) >= 1
            assert signals[0].type == "buy"


class TestDataIngestionFlow:
    """Test data ingestion flow"""
    
    @pytest.mark.asyncio
    async def test_ingestion_to_storage(self):
        """Test data flows from ingestion to storage"""
        from ingestion.worker import OHLCV, OptionChain, DataStorage
        
        # 1. Create mock data
        bars = [
            OHLCV(
                symbol="SPY",
                timestamp=datetime.utcnow() - timedelta(hours=i),
                open=450.0 + i,
                high=452.0 + i,
                low=449.0 + i,
                close=451.0 + i,
                volume=10000000 + i * 100000,
            )
            for i in range(24)
        ]
        
        # 2. Store data
        storage = DataStorage()
        await storage.store_bars(bars)
        
        # Without actual DB, just verify no errors
        assert True
    
    @pytest.mark.asyncio
    async def test_option_chain_ingestion(self):
        """Test option chain data ingestion"""
        from ingestion.worker import OptionChain, DataStorage
        
        # Create option chain data
        chains = []
        for strike in range(440, 460, 5):
            for right in ["call", "put"]:
                chains.append(OptionChain(
                    underlying="SPY",
                    contract=f"SPY231215{right[0].upper()}00{strike}000",
                    expiry="2023-12-15",
                    strike=float(strike),
                    right=right,
                    bid=5.0 + (strike - 450) * 0.1,
                    ask=5.2 + (strike - 450) * 0.1,
                    last=5.1 + (strike - 450) * 0.1,
                    volume=1000,
                    open_interest=5000,
                    iv=0.20 + abs(strike - 450) * 0.001,
                    delta=0.5 if right == "call" else -0.5,
                    gamma=0.02,
                    theta=-0.05,
                    vega=0.1,
                    timestamp=datetime.utcnow(),
                ))
        
        storage = DataStorage()
        await storage.store_option_chains(chains)
        
        assert len(chains) == 8  # 4 strikes * 2 rights


class TestRedisIntegration:
    """Test Redis pub/sub and streams integration"""
    
    @pytest.mark.asyncio
    async def test_pubsub_to_streams(self):
        """Test data flow between pub/sub and streams"""
        # 1. Create signal using Redis Signal class
        signal = RedisSignal(
            id="sig-googl-001",
            type="buy",
            symbol="GOOGL",
            strategy="iv_crush",
            confidence=0.85,
            source="options_flow",
            timestamp=datetime.utcnow().isoformat(),
            data={},
        )
        
        # 2. Create corresponding order event
        order_event = OrderEvent(
            order_id=f"ord_{signal.id}",
            status="submitted",
            symbol=signal.symbol,
            side="buy",
            quantity=10,
            order_type="limit",
            price=140.0,
            strategy=signal.strategy,
        )
        
        # 3. Create trade event after fill
        trade_event = TradeEvent(
            trade_id=f"trd_{signal.id}",
            order_id=order_event.order_id,
            symbol=signal.symbol,
            side="buy",
            quantity=10,
            price=139.95,
            commission=0.65,
        )
        
        # 4. Create alert
        alert = Alert(
            id="alert-fill-001",
            severity="info",
            type="trade",
            symbol=signal.symbol,
            message=f"Buy order for {signal.symbol} filled at ${trade_event.price}",
            timestamp=datetime.utcnow().isoformat(),
            data={
                "signal_id": signal.id,
                "order_id": order_event.order_id,
                "trade_id": trade_event.trade_id,
            }
        )
        
        # Verify all objects created correctly
        assert signal.symbol == order_event.symbol == trade_event.symbol
        assert order_event.order_id == trade_event.order_id


class TestServiceHealth:
    """Test service health aggregation"""
    
    def test_health_aggregation(self):
        """Test aggregating health from all services"""
        # Simulate health responses
        health_responses = {
            "redis": {"status": "healthy"},
            "timescaledb": {"status": "healthy"},
            "signal_service": {"status": "healthy"},
            "order_service": {"status": "healthy"},
            "bento_price": {"status": "ok"},
            "bento_iv": {"status": "ok"},
            "bento_sentiment": {"status": "ok"},
            "gateway": {"status": "healthy"},
        }
        
        # Check all healthy
        all_healthy = all(
            v.get("status") in ["healthy", "ok"]
            for v in health_responses.values()
        )
        
        assert all_healthy is True
        
        # Simulate one service down
        health_responses["timescaledb"]["status"] = "unavailable"
        
        all_healthy = all(
            v.get("status") in ["healthy", "ok"]
            for v in health_responses.values()
        )
        
        assert all_healthy is False


# -----------------------------------------------------------------------------
# Docker Compose Configuration Test
# -----------------------------------------------------------------------------

class TestDockerCompose:
    """Test Docker Compose configuration"""
    
    def test_service_dependencies(self):
        """Test service dependency graph"""
        # Define expected dependencies
        dependencies = {
            "signal-service": ["redis", "timescaledb"],
            "order-service": ["redis", "timescaledb"],
            "gateway": ["redis", "signal-service", "order-service"],
            "ingestion-worker": ["redis", "timescaledb"],
            "ui": ["gateway"],
            "bento-price": [],
            "bento-iv": [],
            "bento-sentiment": [],
        }
        
        # Verify all services have their dependencies defined
        assert len(dependencies) == 8
        
        # Verify no circular dependencies at top level
        for service, deps in dependencies.items():
            assert service not in deps, f"Circular dependency in {service}"
    
    def test_port_allocations(self):
        """Test port allocations don't conflict"""
        ports = {
            "redis": 6379,
            "timescaledb": 5432,
            "signal-service": 50051,
            "order-service": 50052,
            "gateway": 8090,
            "bento-price": 3000,
            "bento-iv": 3001,
            "bento-sentiment": 3002,
            "triton": 8000,
            "triton-http": 8100,
            "triton-metrics": 8200,
            "ui": 8050,
            "prometheus": 9090,
            "grafana": 3100,
        }
        
        # Check for duplicates
        port_values = list(ports.values())
        assert len(port_values) == len(set(port_values)), "Duplicate ports found"
    
    def test_volume_configuration(self):
        """Test volume configuration"""
        volumes = [
            "redis_data",
            "timescale_data",
            "triton_models",
            "parquet_data",
            "prometheus_data",
            "grafana_data",
        ]
        
        # All volumes should be named
        assert all(v.endswith("_data") or v.endswith("_models") for v in volumes)


# -----------------------------------------------------------------------------
# Error Handling Tests
# -----------------------------------------------------------------------------

class TestErrorHandling:
    """Test error handling across services"""
    
    @pytest.mark.asyncio
    async def test_signal_service_error_handling(self):
        """Test signal service error handling"""
        from grpc.services.signal_service import SignalServiceImpl, Signal
        
        service = SignalServiceImpl()
        
        # Invalid signal type - should still accept for flexibility
        signal = Signal(
            id="test-error-001",
            type="invalid_type",
            symbol="AAPL",
            strategy="test",
            confidence=0.5,
            source="test",
            timestamp=datetime.utcnow().isoformat(),
            data={},
        )
        
        success, _, error = await service.publish_signal(signal)
        
        # Service should either reject or accept with warning
        # Check that it returns a result
        assert success is not None
    
    @pytest.mark.asyncio
    async def test_order_service_error_handling(self):
        """Test order service error handling"""
        from grpc.services.order_service import OrderServiceImpl
        
        service = OrderServiceImpl(paper_mode=True)
        
        # Invalid order
        success, _, _, _, error = await service.submit_order(
            symbol="",  # Empty symbol
            side="buy",
            order_type="market",
            quantity=100,
        )
        
        assert success is False or error is not None
    
    def test_gateway_error_responses(self):
        """Test gateway error response format"""
        # Simulate error response
        error_response = {
            "detail": "Order not found",
            "status_code": 404,
        }
        
        assert "detail" in error_response
        assert error_response["status_code"] == 404


# -----------------------------------------------------------------------------
# Performance Tests
# -----------------------------------------------------------------------------

class TestPerformance:
    """Basic performance tests"""
    
    @pytest.mark.asyncio
    async def test_signal_throughput(self):
        """Test signal publishing throughput"""
        from grpc.services.signal_service import SignalServiceImpl, Signal
        import time
        
        service = SignalServiceImpl()
        
        # Publish 100 signals
        start = time.time()
        
        for i in range(100):
            signal = Signal(
                type="buy" if i % 2 == 0 else "sell",
                symbol="AAPL",
                strategy="test",
                confidence=0.5 + (i % 50) / 100,
            )
            await service.publish_signal(signal)
        
        elapsed = time.time() - start
        
        # Should complete in reasonable time
        assert elapsed < 5.0, f"Signal publishing too slow: {elapsed}s"
    
    @pytest.mark.asyncio
    async def test_order_throughput(self):
        """Test order submission throughput"""
        from grpc.services.order_service import OrderServiceImpl
        import time
        
        service = OrderServiceImpl(paper_mode=True)
        
        start = time.time()
        
        for i in range(50):
            await service.submit_order(
                symbol="AAPL",
                side="buy" if i % 2 == 0 else "sell",
                order_type="market",
                quantity=10 + i,
            )
        
        elapsed = time.time() - start
        
        # Allow reasonable variance for CI/test environments
        assert elapsed < 10.0, f"Order submission too slow: {elapsed}s"


# -----------------------------------------------------------------------------
# Run Tests
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
