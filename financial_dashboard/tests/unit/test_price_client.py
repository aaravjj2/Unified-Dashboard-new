"""
Unit tests for PriceClient and Market Trends analytics.

Tests cover:
- PriceClient fallback logic (Alpaca -> Finnhub -> yfinance)
- Defensive handling of missing/malformed data
- Data source metadata tracking
- yfinance batch vs single ticker handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import pandas as pd
import numpy as np


# Helper fixture to mock load_environment
@pytest.fixture
def mock_load_env():
    """Mock load_environment to avoid API key validation in tests."""
    with patch('financial_dashboard.utils.load_env.load_environment') as mock:
        mock.return_value = {
            'valid': True,
            'missing_keys': [],
            'present_keys': ['FINNHUB_API_KEY', 'APCA_API_KEY_ID', 'APCA_API_SECRET_KEY'],
            'sources': {}
        }
        yield mock


class TestPriceClientFallback:
    """Tests for PriceClient provider fallback behavior."""
    
    @pytest.fixture
    def mock_env(self, monkeypatch):
        """Set up mock environment variables for PriceClient."""
        monkeypatch.setenv('APCA_API_KEY_ID', 'test_alpaca_key')
        monkeypatch.setenv('APCA_API_SECRET_KEY', 'test_alpaca_secret')
        monkeypatch.setenv('FINNHUB_API_KEY', 'test_finnhub_key')
    
    def test_price_client_init_with_keys(self, mock_env, mock_load_env):
        """Test PriceClient initializes correctly with API keys."""
        from financial_dashboard.utils.price_client import PriceClient
        
        pc = PriceClient()
        assert pc.alpaca_available is True
        assert pc.finnhub_available is True
    
    def test_price_client_init_without_keys(self, monkeypatch, mock_load_env):
        """Test PriceClient handles missing keys gracefully."""
        monkeypatch.delenv('APCA_API_KEY_ID', raising=False)
        monkeypatch.delenv('APCA_API_SECRET_KEY', raising=False)
        monkeypatch.delenv('FINNHUB_API_KEY', raising=False)
        monkeypatch.delenv('ALPACA_API_KEY', raising=False)
        monkeypatch.delenv('FINNHUB_KEY', raising=False)
        
        from financial_dashboard.utils.price_client import PriceClient
        
        # Should not raise, but flags should be False
        pc = PriceClient()
        assert pc.alpaca_available is False
        assert pc.finnhub_available is False
    
    @patch('financial_dashboard.utils.price_client.yf')
    def test_yfinance_fallback_on_alpaca_failure(self, mock_yf, mock_env, mock_load_env):
        """Test that yfinance is used when Alpaca fails."""
        from financial_dashboard.utils.price_client import PriceClient
        
        # Create mock yfinance response
        mock_data = pd.DataFrame({
            'Open': [100.0, 101.0, 102.0],
            'Close': [101.0, 102.0, 103.0],
        }, index=pd.date_range('2025-01-01', periods=3, freq='D'))
        
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_data
        mock_yf.Ticker.return_value = mock_ticker
        mock_yf.download.return_value = mock_data
        
        pc = PriceClient()
        
        # Force Alpaca to fail by patching internal method
        with patch.object(pc, '_fetch_from_alpaca', side_effect=Exception("Alpaca failed")):
            with patch.object(pc, '_fetch_from_finnhub', side_effect=Exception("Finnhub failed")):
                results = pc.get_prices(['AAPL'], lookback_days=7)
        
        # Should have fallen back to yfinance
        assert 'AAPL' in results
        assert results['AAPL'].get('source') == 'yfinance'
    
    def test_data_source_tracking(self, mock_env, mock_load_env):
        """Test that data source is properly tracked in results."""
        from financial_dashboard.utils.price_client import PriceClient
        
        pc = PriceClient()
        
        # Mock a successful Alpaca response
        mock_result = {
            'AAPL': {
                'current_price': 150.0,
                'daily_change': 1.5,
                'start_price': 148.0,
                'profit_loss': 13.51,
                'source': 'alpaca',
                'start_date': '2025-01-01'
            }
        }
        
        with patch.object(pc, '_fetch_from_alpaca', return_value=mock_result):
            results = pc.get_prices(['AAPL'], lookback_days=7, cache_ttl=0)
        
        assert results['AAPL']['source'] == 'alpaca'


class TestYfinanceExplicitArgs:
    """Tests for explicit yfinance argument handling."""
    
    @patch('financial_dashboard.utils.price_client.yf')
    def test_yfinance_batch_uses_explicit_args(self, mock_yf, mock_load_env, monkeypatch):
        """Test that yfinance batch download uses explicit args."""
        monkeypatch.setenv('APCA_API_KEY_ID', 'test')
        monkeypatch.setenv('APCA_API_SECRET_KEY', 'test')
        monkeypatch.setenv('FINNHUB_API_KEY', 'test')
        
        from financial_dashboard.utils.price_client import PriceClient
        
        mock_data = pd.DataFrame({
            'Close': [100.0, 101.0, 102.0],
        }, index=pd.date_range('2025-01-01', periods=3, freq='D'))
        mock_yf.download.return_value = mock_data
        
        pc = PriceClient()
        pc._yfinance_batch_download(
            ['AAPL'],
            datetime.now().date() - timedelta(days=10),
            datetime.now().date(),
            lookback_days=7,
            investment_per_ticker=1000.0
        )
        
        # Verify yf.download was called with explicit args
        call_kwargs = mock_yf.download.call_args.kwargs
        assert call_kwargs.get('progress') is False
        assert call_kwargs.get('threads') is False
        assert call_kwargs.get('auto_adjust') is True
    
    @patch('financial_dashboard.utils.price_client.yf')
    def test_yfinance_single_ticker_uses_auto_adjust(self, mock_yf, mock_load_env, monkeypatch):
        """Test that single ticker fetch uses auto_adjust."""
        monkeypatch.setenv('APCA_API_KEY_ID', 'test')
        monkeypatch.setenv('APCA_API_SECRET_KEY', 'test')
        monkeypatch.setenv('FINNHUB_API_KEY', 'test')
        
        from financial_dashboard.utils.price_client import PriceClient
        
        mock_data = pd.DataFrame({
            'Close': [100.0, 101.0, 102.0],
            'Open': [99.0, 100.0, 101.0],
        }, index=pd.date_range('2025-01-01', periods=3, freq='D'))
        
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_data
        mock_yf.Ticker.return_value = mock_ticker
        
        pc = PriceClient()
        pc._yfinance_single_ticker(
            'AAPL',
            datetime.now().date() - timedelta(days=10),
            datetime.now().date(),
            lookback_days=7,
            investment_per_ticker=1000.0
        )
        
        # Verify history() was called with auto_adjust=True
        call_kwargs = mock_ticker.history.call_args.kwargs
        assert call_kwargs.get('auto_adjust') is True


class TestDefensiveHandling:
    """Tests for defensive data handling."""
    
    def test_empty_ticker_list_returns_empty(self, monkeypatch, mock_load_env):
        """Test that empty ticker list returns empty results."""
        monkeypatch.setenv('APCA_API_KEY_ID', 'test')
        monkeypatch.setenv('APCA_API_SECRET_KEY', 'test')
        
        from financial_dashboard.utils.price_client import PriceClient
        
        pc = PriceClient()
        results = pc.get_prices([], lookback_days=7)
        
        assert results == {}
    
    def test_missing_price_data_handled_gracefully(self, monkeypatch, mock_load_env):
        """Test that missing price data doesn't crash."""
        monkeypatch.setenv('APCA_API_KEY_ID', 'test')
        monkeypatch.setenv('APCA_API_SECRET_KEY', 'test')
        monkeypatch.setenv('FINNHUB_API_KEY', 'test')
        
        from financial_dashboard.utils.price_client import PriceClient
        
        pc = PriceClient()
        
        # Force all providers to fail
        with patch.object(pc, '_fetch_from_alpaca', return_value={}):
            with patch.object(pc, '_fetch_from_finnhub', return_value={}):
                with patch.object(pc, '_fetch_from_yfinance', return_value={}):
                    results = pc.get_prices(['FAKE_TICKER'], lookback_days=7, cache_ttl=0)
        
        # Should return placeholder with source='Local'
        assert 'FAKE_TICKER' in results
        assert results['FAKE_TICKER']['source'] == 'Local'
        assert results['FAKE_TICKER']['current_price'] is None


class TestSectorHeatmapDataFlow:
    """Tests for sector heatmap data processing."""
    
    def test_sector_change_calculation(self):
        """Test percent change calculation for sectors."""
        # Simulate price data as returned by PriceClient
        price_results = {
            'XLK': {
                'current_price': 200.0,
                'week_start_price': 195.0,
                'source': 'alpaca'
            },
            'XLF': {
                'current_price': 40.0,
                'week_start_price': 41.0,
                'source': 'alpaca'
            }
        }
        
        SECTOR_ETFS = {
            'Technology': 'XLK',
            'Financials': 'XLF'
        }
        
        data = []
        for sector, ticker in SECTOR_ETFS.items():
            ticker_data = price_results.get(ticker)
            if not ticker_data:
                continue
            
            current = ticker_data.get('current_price')
            prev = ticker_data.get('week_start_price') or ticker_data.get('start_price')
            
            if current is None or prev is None or prev == 0:
                continue
            
            change = ((current - prev) / prev) * 100
            data.append({
                'Sector': sector,
                'Ticker': ticker,
                'Change': change
            })
        
        assert len(data) == 2
        
        xlk_data = next(d for d in data if d['Ticker'] == 'XLK')
        assert abs(xlk_data['Change'] - 2.56) < 0.1  # ~2.56% gain
        
        xlf_data = next(d for d in data if d['Ticker'] == 'XLF')
        assert xlf_data['Change'] < 0  # Should be negative


class TestCacheIntegration:
    """Tests for PriceClient caching behavior."""
    
    def test_cache_hit_returns_cached_data(self, monkeypatch, mock_load_env):
        """Test that cache hit returns cached data without API call."""
        monkeypatch.setenv('APCA_API_KEY_ID', 'test')
        monkeypatch.setenv('APCA_API_SECRET_KEY', 'test')
        monkeypatch.setenv('FINNHUB_API_KEY', 'test')
        
        from financial_dashboard.utils.price_client import PriceClient
        
        pc = PriceClient()
        
        # Pre-populate cache
        cached_result = {
            'AAPL': {
                'current_price': 999.99,
                'source': 'cached_test'
            }
        }
        import time
        with pc._cache_lock:
            pc._cache[(('AAPL',), 7, 1000.0)] = (time.time(), cached_result)
        
        # Should return cached result without calling providers
        with patch.object(pc, '_fetch_from_alpaca') as mock_alpaca:
            results = pc.get_prices(['AAPL'], lookback_days=7, cache_ttl=300)
        
        mock_alpaca.assert_not_called()
        assert results['AAPL']['current_price'] == 999.99
    
    def test_cache_miss_calls_providers(self, monkeypatch, mock_load_env):
        """Test that cache miss triggers provider calls."""
        monkeypatch.setenv('APCA_API_KEY_ID', 'test')
        monkeypatch.setenv('APCA_API_SECRET_KEY', 'test')
        monkeypatch.setenv('FINNHUB_API_KEY', 'test')
        
        from financial_dashboard.utils.price_client import PriceClient
        
        pc = PriceClient()
        
        # Clear cache
        with pc._cache_lock:
            pc._cache.clear()
        
        mock_result = {
            'AAPL': {
                'current_price': 150.0,
                'source': 'alpaca'
            }
        }
        
        with patch.object(pc, '_fetch_from_alpaca', return_value=mock_result) as mock_alpaca:
            results = pc.get_prices(['AAPL'], lookback_days=7, cache_ttl=0)
        
        mock_alpaca.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
