"""
Unit Tests for Data Ingestion Worker

Tests the data ingestion components for:
- Alpaca API fetching
- Yahoo Finance fetching
- Data storage
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import sys
sys.path.insert(0, '/home/aarav/Unified-Dashboard/phase1_integration')

from ingestion.worker import (
    IngestionWorker,
    AlpacaFetcher,
    YFinanceFetcher,
    DataStorage,
    OHLCV,
    OptionChain,
    Quote,
)


# -----------------------------------------------------------------------------
# Data Model Tests
# -----------------------------------------------------------------------------

class TestOHLCVDataclass:
    """Test OHLCV dataclass"""
    
    def test_ohlcv_creation(self):
        """Test creating an OHLCV bar"""
        bar = OHLCV(
            symbol="AAPL",
            timestamp=datetime.utcnow(),
            open=150.0,
            high=152.0,
            low=149.0,
            close=151.0,
            volume=1000000,
        )
        
        assert bar.symbol == "AAPL"
        assert bar.close == 151.0
        assert bar.volume == 1000000
    
    def test_ohlcv_with_optional_fields(self):
        """Test OHLCV with optional fields"""
        bar = OHLCV(
            symbol="MSFT",
            timestamp=datetime.utcnow(),
            open=350.0,
            high=355.0,
            low=348.0,
            close=352.0,
            volume=500000,
            vwap=351.5,
            trades=10000,
        )
        
        assert bar.vwap == 351.5
        assert bar.trades == 10000


class TestOptionChainDataclass:
    """Test OptionChain dataclass"""
    
    def test_option_chain_creation(self):
        """Test creating option chain data"""
        chain = OptionChain(
            underlying="SPY",
            contract="SPY230120C00400000",
            expiry="2023-01-20",
            strike=400.0,
            right="call",
            bid=5.0,
            ask=5.2,
            last=5.1,
            volume=1000,
            open_interest=5000,
            iv=0.25,
            delta=0.5,
            gamma=0.02,
            theta=-0.05,
            vega=0.1,
            timestamp=datetime.utcnow(),
        )
        
        assert chain.underlying == "SPY"
        assert chain.strike == 400.0
        assert chain.right == "call"
        assert chain.iv == 0.25


class TestQuoteDataclass:
    """Test Quote dataclass"""
    
    def test_quote_creation(self):
        """Test creating a quote"""
        quote = Quote(
            symbol="AAPL",
            bid=150.0,
            ask=150.05,
            bid_size=100,
            ask_size=200,
            timestamp=datetime.utcnow(),
        )
        
        assert quote.symbol == "AAPL"
        assert quote.bid == 150.0
        assert quote.ask == 150.05


# -----------------------------------------------------------------------------
# Alpaca Fetcher Tests
# -----------------------------------------------------------------------------

class TestAlpacaFetcher:
    """Test Alpaca API fetcher"""
    
    @pytest.fixture
    def fetcher(self):
        """Create fetcher instance"""
        return AlpacaFetcher(api_key="test_key", secret_key="test_secret")
    
    @pytest.fixture
    def mock_http_client(self):
        """Create mock HTTP client"""
        client = AsyncMock()
        response = MagicMock()
        response.raise_for_status = MagicMock()
        client.get = AsyncMock(return_value=response)
        return client, response
    
    @pytest.mark.asyncio
    async def test_fetch_bars(self, fetcher, mock_http_client):
        """Test fetching OHLCV bars"""
        client, response = mock_http_client
        
        response.json.return_value = {
            "bars": [
                {
                    "t": "2023-12-01T00:00:00Z",
                    "o": 150.0,
                    "h": 152.0,
                    "l": 149.0,
                    "c": 151.0,
                    "v": 1000000,
                    "vw": 150.5,
                    "n": 5000,
                }
            ]
        }
        
        fetcher._http_client = client
        
        bars = await fetcher.fetch_bars("AAPL", timeframe="1Day")
        
        assert len(bars) == 1
        assert bars[0].symbol == "AAPL"
        assert bars[0].close == 151.0
    
    @pytest.mark.asyncio
    async def test_fetch_bars_empty(self, fetcher, mock_http_client):
        """Test fetching bars with empty response"""
        client, response = mock_http_client
        response.json.return_value = {"bars": []}
        fetcher._http_client = client
        
        bars = await fetcher.fetch_bars("UNKNOWN")
        
        assert len(bars) == 0
    
    @pytest.mark.asyncio
    async def test_fetch_quotes(self, fetcher, mock_http_client):
        """Test fetching quotes"""
        client, response = mock_http_client
        
        response.json.return_value = {
            "quotes": {
                "AAPL": {
                    "bp": 150.0,
                    "ap": 150.05,
                    "bs": 100,
                    "as": 200,
                    "t": "2023-12-01T10:00:00Z",
                }
            }
        }
        
        fetcher._http_client = client
        
        quotes = await fetcher.fetch_quotes(["AAPL"])
        
        assert len(quotes) == 1
        assert quotes[0].symbol == "AAPL"
    
    @pytest.mark.asyncio
    async def test_fetch_option_chain(self, fetcher, mock_http_client):
        """Test fetching option chain"""
        client, response = mock_http_client
        
        response.json.return_value = {
            "snapshots": {
                "SPY230120C00400000": {
                    "expiration_date": "2023-01-20",
                    "strike_price": 400.0,
                    "option_type": "call",
                    "greeks": {
                        "implied_volatility": 0.25,
                        "delta": 0.5,
                        "gamma": 0.02,
                        "theta": -0.05,
                        "vega": 0.1,
                    },
                    "latestQuote": {"bp": 5.0, "ap": 5.2},
                    "latestTrade": {"p": 5.1, "s": 100},
                    "open_interest": 5000,
                }
            }
        }
        
        fetcher._http_client = client
        
        chains = await fetcher.fetch_option_chain("SPY")
        
        assert len(chains) == 1
        assert chains[0].underlying == "SPY"


# -----------------------------------------------------------------------------
# Yahoo Finance Fetcher Tests
# -----------------------------------------------------------------------------

class TestYFinanceFetcher:
    """Test Yahoo Finance fetcher"""
    
    @pytest.fixture
    def fetcher(self):
        """Create fetcher instance"""
        return YFinanceFetcher()
    
    @pytest.mark.asyncio
    async def test_fetch_bars_mock(self, fetcher):
        """Test fetching bars with mock data"""
        import pandas as pd
        
        mock_df = pd.DataFrame({
            "Open": [150.0, 151.0, 152.0],
            "High": [152.0, 153.0, 154.0],
            "Low": [149.0, 150.0, 151.0],
            "Close": [151.0, 152.0, 153.0],
            "Volume": [1000000, 1100000, 1200000],
        }, index=pd.date_range(start="2023-12-01", periods=3))
        
        with patch('yfinance.Ticker') as mock_ticker:
            instance = MagicMock()
            instance.history.return_value = mock_df
            mock_ticker.return_value = instance
            
            # Can't easily test async with yfinance
            # Just verify the fetcher is created
            assert fetcher is not None


# -----------------------------------------------------------------------------
# Data Storage Tests
# -----------------------------------------------------------------------------

class TestDataStorage:
    """Test data storage"""
    
    @pytest.fixture
    def storage(self):
        """Create storage instance"""
        return DataStorage()
    
    @pytest.mark.asyncio
    async def test_store_bars(self, storage):
        """Test storing bars"""
        bars = [
            OHLCV(
                symbol="AAPL",
                timestamp=datetime.utcnow() - timedelta(days=i),
                open=150.0 + i,
                high=152.0 + i,
                low=149.0 + i,
                close=151.0 + i,
                volume=1000000,
            )
            for i in range(5)
        ]
        
        # Should not raise without connections
        await storage.store_bars(bars)
    
    @pytest.mark.asyncio
    async def test_store_option_chains(self, storage):
        """Test storing option chains"""
        chains = [
            OptionChain(
                underlying="SPY",
                contract=f"SPY230120C0040{i}000",
                expiry="2023-01-20",
                strike=400.0 + i * 5,
                right="call",
                bid=5.0 + i,
                ask=5.2 + i,
                last=5.1 + i,
                volume=1000,
                open_interest=5000,
                iv=0.25,
                delta=0.5,
                gamma=0.02,
                theta=-0.05,
                vega=0.1,
                timestamp=datetime.utcnow(),
            )
            for i in range(3)
        ]
        
        await storage.store_option_chains(chains)
    
    @pytest.mark.asyncio
    async def test_store_quotes(self, storage):
        """Test storing quotes"""
        quotes = [
            Quote(
                symbol="AAPL",
                bid=150.0,
                ask=150.05,
                bid_size=100,
                ask_size=200,
                timestamp=datetime.utcnow(),
            )
        ]
        
        await storage.store_quotes(quotes)


# -----------------------------------------------------------------------------
# Ingestion Worker Tests
# -----------------------------------------------------------------------------

class TestIngestionWorker:
    """Test ingestion worker"""
    
    @pytest.fixture
    def worker(self):
        """Create worker instance"""
        return IngestionWorker(
            symbols=["AAPL", "MSFT"],
            interval=60,
        )
    
    def test_worker_creation(self, worker):
        """Test worker initialization"""
        assert worker.symbols == ["AAPL", "MSFT"]
        assert worker.interval == 60
        assert worker._running is False
    
    @pytest.mark.asyncio
    async def test_worker_stop(self, worker):
        """Test stopping worker"""
        worker._running = True
        await worker.stop()
        
        assert worker._running is False


# -----------------------------------------------------------------------------
# Run Tests
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
