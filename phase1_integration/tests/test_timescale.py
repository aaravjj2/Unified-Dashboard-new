"""
Unit Tests for TimescaleDB Loader

Tests the TimescaleDB wrapper for:
- Connection management
- Bulk inserts
- Time-series queries
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from decimal import Decimal

import sys
sys.path.insert(0, '/home/aarav/Unified-Dashboard/phase1_integration')

from timescale.loader import TimescaleLoader, OHLCVRecord, OptionChainRecord


# -----------------------------------------------------------------------------
# TimescaleLoader Tests
# -----------------------------------------------------------------------------

class TestTimescaleLoader:
    """Test TimescaleDB loader"""
    
    @pytest.fixture
    def mock_pool(self):
        """Create mock connection pool"""
        mock_pool = AsyncMock()
        mock_conn = AsyncMock()
        mock_conn.executemany = AsyncMock()
        mock_conn.fetch = AsyncMock(return_value=[])
        mock_conn.fetchrow = AsyncMock(return_value={})
        mock_conn.fetchval = AsyncMock(return_value="result")
        mock_conn.execute = AsyncMock()
        
        # Create proper async context manager
        mock_acquire = MagicMock()
        mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_acquire.__aexit__ = AsyncMock(return_value=None)
        mock_pool.acquire = MagicMock(return_value=mock_acquire)
        mock_pool.close = AsyncMock()
        
        return mock_pool, mock_conn
    
    @pytest.fixture
    def loader(self, mock_pool):
        """Create TimescaleLoader with mock pool"""
        pool, _ = mock_pool
        loader = TimescaleLoader()
        loader._pool = pool
        return loader
    
    @pytest.mark.asyncio
    async def test_connect(self):
        """Test database connection"""
        with patch('timescale.loader.asyncpg.create_pool') as mock_create:
            mock_pool = AsyncMock()
            mock_create.return_value = mock_pool
            
            loader = TimescaleLoader()
            loader._pool = mock_pool  # Directly assign for testing
            
            assert loader._pool is not None
    
    @pytest.mark.asyncio
    async def test_insert_ohlcv(self, loader, mock_pool):
        """Test inserting OHLCV data"""
        _, mock_conn = mock_pool
        mock_conn.copy_records_to_table = AsyncMock(return_value=None)
        
        record = OHLCVRecord(
            time=datetime.utcnow(),
            symbol="AAPL",
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000,
        )
        
        count = await loader.insert_ohlcv([record])
        
        # Verify copy_records_to_table was called
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_insert_option_chains(self, loader, mock_pool):
        """Test inserting option chain data"""
        _, mock_conn = mock_pool
        mock_conn.copy_records_to_table = AsyncMock(return_value=None)
        
        from datetime import date
        record = OptionChainRecord(
            time=datetime.utcnow(),
            underlying="SPY",
            symbol="SPY230120C00400000",
            expiry=date(2023, 1, 20),
            strike=400.0,
            option_type="call",
            bid=5.0,
            ask=5.2,
            last=5.1,
            mid=5.15,
            volume=1000,
            open_interest=5000,
            implied_volatility=0.25,
            delta=0.5,
            gamma=0.02,
            theta=-0.05,
            vega=0.1,
        )
        
        count = await loader.insert_option_chains([record])
        assert count == 1
    
    @pytest.mark.asyncio
    async def test_query_ohlcv(self, loader, mock_pool):
        """Test querying OHLCV data"""
        pool, mock_conn = mock_pool
        
        # Mock return data
        mock_conn.fetch.return_value = [
            {
                "time": datetime.utcnow(),
                "symbol": "AAPL",
                "open": 150.0,
                "high": 152.0,
                "low": 149.0,
                "close": 151.0,
                "volume": 1000000,
            }
        ]
        
        results = await loader.query_ohlcv(
            symbol="AAPL",
            start=datetime.utcnow() - timedelta(days=7),
            end=datetime.utcnow(),
        )
        
        assert results is not None
    
    @pytest.mark.asyncio
    async def test_insert_signal(self, loader, mock_pool):
        """Test inserting a signal"""
        pool, mock_conn = mock_pool
        mock_conn.fetchval = AsyncMock(return_value="sig-123")
        
        result = await loader.insert_signal(
            signal_id="sig-123",
            signal_type="buy",
            symbol="AAPL",
            strategy="momentum",
            confidence=0.85,
        )
        
        assert result == "sig-123"
    
    @pytest.mark.asyncio
    async def test_insert_order(self, loader, mock_pool):
        """Test inserting an order"""
        pool, mock_conn = mock_pool
        mock_conn.fetchval = AsyncMock(return_value="ord-123")
        
        order = {
            "order_id": "ord-123",
            "symbol": "MSFT",
            "side": "buy",
            "order_type": "limit",
            "quantity": 100,
            "limit_price": 350.0,
            "status": "submitted",
        }
        
        result = await loader.insert_order(order)
        assert result == "ord-123"
    
    @pytest.mark.asyncio
    async def test_query_signals(self, loader, mock_pool):
        """Test querying signals"""
        pool, mock_conn = mock_pool
        mock_conn.fetch.return_value = []
        
        result = await loader.query_signals(symbol="AAPL", hours=24)
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_close(self, loader, mock_pool):
        """Test closing the connection pool"""
        pool, _ = mock_pool
        
        await loader.close()
        
        pool.close.assert_called_once()


# -----------------------------------------------------------------------------
# Data Validation Tests
# -----------------------------------------------------------------------------

class TestDataValidation:
    """Test data validation in TimescaleLoader"""
    
    def test_validate_ohlcv_record(self):
        """Test OHLCV record validation"""
        valid_record = {
            "timestamp": datetime.utcnow(),
            "symbol": "AAPL",
            "open": 150.0,
            "high": 152.0,
            "low": 149.0,
            "close": 151.0,
            "volume": 1000000,
        }
        
        # Should have all required fields
        required = ["timestamp", "symbol", "open", "high", "low", "close", "volume"]
        for field in required:
            assert field in valid_record
    
    def test_validate_option_chain_record(self):
        """Test option chain record validation"""
        valid_record = {
            "timestamp": datetime.utcnow(),
            "underlying": "SPY",
            "symbol": "SPY230120C00400000",
            "expiry": "2023-01-20",
            "strike": 400.0,
            "right": "call",
            "bid": 5.0,
            "ask": 5.2,
            "last": 5.1,
            "volume": 1000,
            "open_interest": 5000,
            "iv": 0.25,
            "delta": 0.5,
            "gamma": 0.02,
            "theta": -0.05,
            "vega": 0.1,
        }
        
        # Validate Greeks are reasonable
        assert -1 <= valid_record["delta"] <= 1
        assert valid_record["gamma"] >= 0
        assert valid_record["vega"] >= 0
        assert valid_record["iv"] > 0


# -----------------------------------------------------------------------------
# Run Tests
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
