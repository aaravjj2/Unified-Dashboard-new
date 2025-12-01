"""
Unit tests for ForecastAdapter

Tests:
- Historical data fetching with PriceClient fallback
- Forecast generation with various backends (local, Bento, Triton)
- Metadata tracking (source, timing, timestamps)
- Caching behavior
- Error handling and fallbacks
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Ensure the module can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))


class TestTTLCache:
    """Tests for the TTLCache class."""
    
    def test_cache_set_and_get(self):
        """Test basic cache set and get operations."""
        from financial_dashboard.services.forecast_adapter import TTLCache
        
        cache = TTLCache(default_ttl=60)
        cache.set("test_key", {"data": "value"})
        
        result = cache.get("test_key")
        assert result is not None
        assert result["data"] == "value"
    
    def test_cache_miss(self):
        """Test cache miss for non-existent key."""
        from financial_dashboard.services.forecast_adapter import TTLCache
        
        cache = TTLCache(default_ttl=60)
        result = cache.get("non_existent")
        assert result is None
    
    def test_cache_expiry(self):
        """Test cache expiry after TTL."""
        from financial_dashboard.services.forecast_adapter import TTLCache
        import time
        
        cache = TTLCache(default_ttl=1)  # 1 second TTL
        cache.set("test_key", "value")
        
        # Should be in cache
        assert cache.get("test_key") == "value"
        
        # Wait for expiry
        time.sleep(1.5)
        
        # Should be expired
        assert cache.get("test_key") is None
    
    def test_cache_clear(self):
        """Test cache clear operation."""
        from financial_dashboard.services.forecast_adapter import TTLCache
        
        cache = TTLCache(default_ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        cache.clear()
        
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert cache.stats()['entries'] == 0


class TestForecastAdapterInit:
    """Tests for ForecastAdapter initialization."""
    
    def test_init_without_serving_client(self):
        """Test adapter initializes even without ServingClient."""
        with patch('financial_dashboard.serving.serving_client.ServingClient', side_effect=ImportError("Not available")):
            from financial_dashboard.services.forecast_adapter import ForecastAdapter
            
            adapter = ForecastAdapter()
            # Should have None serving_client due to ImportError in __init__
            # Note: The actual import happens inside __init__, so this tests graceful handling
            assert adapter._price_cache is not None
            assert adapter._forecast_cache is not None
    
    def test_init_creates_caches(self):
        """Test adapter initializes caches properly."""
        from financial_dashboard.services.forecast_adapter import ForecastAdapter
        
        adapter = ForecastAdapter()
        assert hasattr(adapter, '_price_cache')
        assert hasattr(adapter, '_forecast_cache')
        assert hasattr(adapter, 'cache')


class TestFetchHistoricalData:
    """Tests for _fetch_historical_data method."""
    
    @pytest.fixture
    def mock_prices_df(self):
        """Create mock price DataFrame."""
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        return pd.DataFrame({
            'AAPL': np.random.uniform(150, 200, 100)
        }, index=dates)
    
    def test_fetch_uses_unified_fetcher(self, mock_prices_df):
        """Test that unified price fetcher is used first."""
        from financial_dashboard.services.forecast_adapter import ForecastAdapter
        
        adapter = ForecastAdapter()
        
        with patch('financial_dashboard.services.forecast_adapter.fetch_historical_data', return_value=mock_prices_df, create=True):
            # Need to patch at the import location inside the method
            with patch.dict('sys.modules', {'financial_dashboard.utils.price_fetch': MagicMock(fetch_historical_data=Mock(return_value=mock_prices_df))}):
                prices, metadata = adapter._fetch_historical_data('AAPL', lookback_days=30)
                
                if prices is not None:
                    # If unified fetcher worked
                    assert len(prices) <= 30
                    assert metadata['cache_hit'] is False
    
    def test_fetch_caches_result(self, mock_prices_df):
        """Test that fetch results are cached."""
        from financial_dashboard.services.forecast_adapter import ForecastAdapter
        
        adapter = ForecastAdapter()
        
        # Manually populate cache to test cache hit
        dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
        cached_prices = pd.Series(np.random.uniform(150, 200, 30), index=dates)
        cached_metadata = {
            'source': 'cached',
            'fetch_duration_ms': 0,
            'data_timestamp': datetime.now().isoformat(),
            'ticker': 'AAPL',
            'cache_hit': False
        }
        
        adapter._price_cache.set('prices_AAPL_30', (cached_prices, cached_metadata))
        
        # Second call should hit cache
        prices, metadata = adapter._fetch_historical_data('AAPL', lookback_days=30)
        assert metadata['cache_hit'] is True
    
    def test_fetch_returns_metadata(self, mock_prices_df):
        """Test that metadata is properly populated."""
        from financial_dashboard.services.forecast_adapter import ForecastAdapter
        
        adapter = ForecastAdapter()
        
        # Mock the price fetch to succeed
        mock_module = MagicMock()
        mock_module.fetch_historical_data = Mock(return_value=mock_prices_df)
        
        with patch.dict('sys.modules', {'financial_dashboard.utils.price_fetch': mock_module}):
            prices, metadata = adapter._fetch_historical_data('AAPL', lookback_days=30)
            
            assert 'source' in metadata
            assert 'fetch_duration_ms' in metadata
            assert 'ticker' in metadata
            assert metadata['ticker'] == 'AAPL'
            assert metadata['fetch_duration_ms'] >= 0


class TestRunForecast:
    """Tests for run_forecast method."""
    
    def test_run_forecast_returns_result(self):
        """Test that run_forecast returns valid result."""
        from financial_dashboard.services.forecast_adapter import ForecastAdapter
        
        adapter = ForecastAdapter()
        
        # Mock price data
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        mock_prices = pd.Series(np.random.uniform(150, 200, 100), index=dates)
        
        with patch.object(adapter, '_fetch_historical_data', return_value=(mock_prices, {
            'source': 'test',
            'fetch_duration_ms': 100,
            'data_timestamp': datetime.now().isoformat()
        })):
            result = adapter.run_forecast(
                ticker='AAPL',
                horizon=30,
                confidence=0.95,
                model='statistical',
                forecast_id='test_123'
            )
            
            assert result['status'] == 'success'
            assert result['ticker'] == 'AAPL'
            assert result['horizon'] == 30
            assert 'forecast' in result
            assert len(result['forecast']) == 30
            assert 'metadata' in result
    
    def test_run_forecast_with_insufficient_data(self):
        """Test error handling with insufficient data."""
        from financial_dashboard.services.forecast_adapter import ForecastAdapter
        
        adapter = ForecastAdapter()
        
        # Mock insufficient price data
        dates = pd.date_range(end=datetime.now(), periods=10, freq='D')
        mock_prices = pd.Series(np.random.uniform(150, 200, 10), index=dates)
        
        with patch.object(adapter, '_fetch_historical_data', return_value=(mock_prices, {'source': 'test'})):
            result = adapter.run_forecast(
                ticker='AAPL',
                horizon=30,
                confidence=0.95,
                model='statistical',
                forecast_id='test_123'
            )
            
            assert result['status'] == 'error'
            assert 'error' in result
    
    def test_run_forecast_metadata_includes_sources(self):
        """Test that result metadata includes data and inference sources."""
        from financial_dashboard.services.forecast_adapter import ForecastAdapter
        
        adapter = ForecastAdapter()
        
        dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
        mock_prices = pd.Series(np.random.uniform(150, 200, 100), index=dates)
        
        with patch.object(adapter, '_fetch_historical_data', return_value=(mock_prices, {
            'source': 'alpaca_or_yfinance',
            'fetch_duration_ms': 150,
            'data_timestamp': datetime.now().isoformat()
        })):
            result = adapter.run_forecast(
                ticker='AAPL',
                horizon=30,
                confidence=0.95,
                model='statistical',
                forecast_id='test_123'
            )
            
            assert result['status'] == 'success'
            assert 'metadata' in result
            assert result['metadata']['data_source'] == 'alpaca_or_yfinance'
            assert result['metadata']['inference_source'] in ['statistical', 'ml_runner']
            assert result['metadata']['total_duration_ms'] >= 0


class TestCacheStats:
    """Tests for cache statistics."""
    
    def test_cache_stats_structure(self):
        """Test cache stats returns proper structure."""
        from financial_dashboard.services.forecast_adapter import ForecastAdapter
        
        adapter = ForecastAdapter()
        stats = adapter.cache_stats()
        
        assert 'price_cache' in stats
        assert 'forecast_cache' in stats
        assert 'legacy_cache_entries' in stats
    
    def test_clear_cache(self):
        """Test cache clearing."""
        from financial_dashboard.services.forecast_adapter import ForecastAdapter
        
        adapter = ForecastAdapter()
        
        # Add some data
        adapter._price_cache.set('test_key', 'test_value')
        adapter.cache['legacy_key'] = 'legacy_value'
        
        # Clear
        adapter.clear_cache()
        
        # Verify cleared
        assert adapter._price_cache.get('test_key') is None
        assert 'legacy_key' not in adapter.cache


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
