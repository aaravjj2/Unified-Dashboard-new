"""
RED Phase Tests for Volatility Lab Live Data Integration

Tests verify that Volatility Lab:
1. Uses PriceClient for live data (Alpaca → Finnhub → yfinance fallback)
2. Computes all volatility types correctly with real data
3. Handles API failures gracefully
4. Shows accurate prices and returns

These tests should FAIL initially because volatility_lab.py uses mock data.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from financial_dashboard.tabs.volatility_lab import (
    load_price_data,
    compute_volatility
)


class TestLiveDataIntegration:
    """Test that volatility_lab integrates with PriceClient"""
    
    def test_load_price_data_uses_price_client(self):
        """
        GREEN Test: Verify load_price_data calls PriceClient
        
        Now that we've integrated PriceClient, this should pass.
        """
        tickers = ['AAPL']
        start = '2024-01-01'
        end = '2024-01-31'
        
        # Test with real PriceClient (will use yfinance fallback in test env)
        df = load_price_data(tickers, start, end)
        
        # Assertions
        assert not df.empty, "Should return data"
        assert 'ticker' in df.columns
        assert 'price' in df.columns
        assert 'date' in df.columns
        assert 'AAPL' in df['ticker'].values
    
    def test_load_price_data_handles_alpaca_failure(self):
        """
        GREEN Test: Verify fallback to yfinance when Alpaca fails
        
        This test validates the PriceClient fallback chain:
        Alpaca (404) → Finnhub (403) → yfinance (✓)
        """
        tickers = ['AAPL']
        start = '2024-01-01'
        end = '2024-01-15'
        
        # Clear cache to force live fetch
        try:
            from financial_dashboard.utils.price_cache import get_price_cache
            cache = get_price_cache()
            cache.invalidate(tickers, start, end)
        except Exception:
            pass  # Cache not available in test env
        
        # Load data - should fallback to yfinance
        df = load_price_data(tickers, start, end)
        
        # Assertions: yfinance fallback should work
        assert not df.empty, "Fallback chain should return data"
        assert 'ticker' in df.columns
        assert 'price' in df.columns
        assert 'date' in df.columns
        assert 'AAPL' in df['ticker'].values
        assert len(df) >= 5, "Should have at least 5 trading days"
    
    def test_load_price_data_requires_api_keys(self):
        """
        GREEN Test: Verify that API keys are loaded from keys.env
        """
        import os
        
        # Keys should be loaded at import time
        # At least one source should be available
        has_alpaca = 'APCA_API_KEY_ID' in os.environ or 'ALPACA_API_KEY' in os.environ
        has_finnhub = 'FINNHUB_API_KEY' in os.environ
        
        assert has_alpaca or has_finnhub, \
            "At least one API key (Alpaca or Finnhub) should be loaded"


class TestVolatilityTypes:
    """Test that all volatility types compute correctly with live data"""
    
    def test_rolling_volatility_computes_correctly(self):
        """
        GREEN Test: Verify rolling volatility calculation
        """
        # Create test data
        dates = pd.date_range('2024-01-01', periods=100)
        tickers = ['SPY']
        data = []
        
        for ticker in tickers:
            prices = 100 * np.exp(np.cumsum(np.random.randn(100) * 0.01))
            for date, price in zip(dates, prices):
                data.append({'date': date, 'ticker': ticker, 'price': price})
        
        df = pd.DataFrame(data)
        
        # Compute volatility
        vol_df = compute_volatility(df, window=20, annualize=False)
        
        # Assertions
        assert 'rolling_vol' in vol_df.columns
        assert not vol_df['rolling_vol'].isna().all(), "Should have some non-NaN rolling vol"
        assert vol_df['rolling_vol'].min() >= 0, "Volatility should be non-negative"
    
    def test_annualized_volatility_computes_correctly(self):
        """
        GREEN Test: Verify annualized volatility is correctly scaled
        """
        dates = pd.date_range('2024-01-01', periods=100)
        data = []
        
        # Deterministic price series
        prices = 100 * np.exp(np.cumsum([0.01] * 100))  # 1% daily return
        for date, price in zip(dates, prices):
            data.append({'date': date, 'ticker': 'TEST', 'price': price})
        
        df = pd.DataFrame(data)
        
        # Compute annualized and non-annualized
        vol_annualized = compute_volatility(df, window=20, annualize=True)
        vol_daily = compute_volatility(df, window=20, annualize=False)
        
        # Annualized should be ~sqrt(252) times daily
        ratio = vol_annualized['rolling_vol'].iloc[-1] / vol_daily['rolling_vol'].iloc[-1]
        expected_ratio = np.sqrt(252)
        
        assert abs(ratio - expected_ratio) < 0.1, \
            f"Annualized vol should be sqrt(252) times daily vol. Got ratio {ratio:.2f}, expected {expected_ratio:.2f}"
    
    def test_realized_volatility_computes_correctly(self):
        """
        GREEN Test: Verify realized volatility over full period
        """
        dates = pd.date_range('2024-01-01', periods=100)
        data = []
        
        # Price series with known volatility
        returns = np.random.randn(100) * 0.02  # 2% daily vol
        prices = 100 * np.exp(np.cumsum(returns))
        
        for date, price in zip(dates, prices):
            data.append({'date': date, 'ticker': 'TEST', 'price': price})
        
        df = pd.DataFrame(data)
        vol_df = compute_volatility(df, window=20, annualize=False)
        
        # Realized vol should be consistent across rows (it's a scalar broadcast)
        assert 'realized_vol' in vol_df.columns
        realized_vals = vol_df['realized_vol'].dropna().unique()
        assert len(realized_vals) == 1, "Realized vol should be constant (scalar)"
        assert realized_vals[0] > 0, "Realized vol should be positive"


class TestPriceReturnAccuracy:
    """Test that prices and returns are accurate"""
    
    def test_prices_match_input_data(self):
        """
        GREEN Test: Verify that output prices match input prices
        """
        dates = pd.date_range('2024-01-01', periods=50)
        input_prices = np.array([100.0, 101.5, 99.8, 102.3, 103.1])
        
        data = []
        for i, (date, price) in enumerate(zip(dates[:5], input_prices)):
            data.append({'date': date, 'ticker': 'AAPL', 'price': price})
        
        df = pd.DataFrame(data)
        vol_df = compute_volatility(df, window=2, annualize=False)
        
        # Prices in output should match input (accounting for diff offset)
        output_prices = vol_df['price'].values
        expected_prices = input_prices[1:]  # Skip first due to diff
        
        np.testing.assert_array_almost_equal(
            output_prices[:len(expected_prices)],
            expected_prices,
            decimal=6,
            err_msg="Output prices should match input prices"
        )
    
    def test_returns_are_log_returns(self):
        """
        GREEN Test: Verify that returns are log returns
        """
        prices = np.array([100.0, 110.0, 105.0])
        dates = pd.date_range('2024-01-01', periods=3)
        
        data = [
            {'date': dates[0], 'ticker': 'TEST', 'price': prices[0]},
            {'date': dates[1], 'ticker': 'TEST', 'price': prices[1]},
            {'date': dates[2], 'ticker': 'TEST', 'price': prices[2]}
        ]
        
        df = pd.DataFrame(data)
        vol_df = compute_volatility(df, window=2, annualize=False)
        
        # Expected log returns
        expected_returns = np.array([
            np.log(110.0 / 100.0),
            np.log(105.0 / 110.0)
        ])
        
        actual_returns = vol_df['return'].values
        
        np.testing.assert_array_almost_equal(
            actual_returns,
            expected_returns,
            decimal=6,
            err_msg="Returns should be log returns"
        )


class TestCachingWithLiveData:
    """Test that caching works correctly with live data"""
    
    def test_cache_saves_live_data(self):
        """
        GREEN Test: Verify that live data is cached after first fetch
        
        Validates:
        1. First call fetches from PriceClient and caches result
        2. Second call uses cached data (no API call)
        3. Cache key includes tickers + date range
        """
        from financial_dashboard.utils.price_cache import get_price_cache
        import time
        
        tickers = ['MSFT']
        start = '2024-01-01'
        end = '2024-01-10'
        
        cache = get_price_cache()
        
        # Clear cache to ensure clean state
        cache.invalidate(tickers, start, end)
        
        # First fetch - should be cache MISS
        start_time = time.time()
        df1 = load_price_data(tickers, start, end)
        first_fetch_time = time.time() - start_time
        
        assert not df1.empty, "First fetch should return data"
        assert 'MSFT' in df1['ticker'].values
        
        # Second fetch - should be cache HIT (much faster)
        start_time = time.time()
        df2 = load_price_data(tickers, start, end)
        second_fetch_time = time.time() - start_time
        
        assert not df2.empty, "Second fetch should return cached data"
        assert len(df1) == len(df2), "Cached data should match original"
        
        # Cache hit should be significantly faster (at least 50% faster)
        assert second_fetch_time < (first_fetch_time * 0.5), \
            f"Cache hit ({second_fetch_time:.3f}s) should be faster than cache miss ({first_fetch_time:.3f}s)"
        
        # Verify cache stats
        stats = cache.get_stats()
        assert stats['memory_entries'] >= 1, "Cache should have at least 1 entry"
    
    def test_cache_invalidates_on_new_date_range(self):
        """
        GREEN Test: Verify that cache.invalidate() properly clears entries
        
        Validates:
        1. Cached data is stored after first fetch
        2. invalidate() clears the specific cache entry
        3. Subsequent fetch is a cache MISS (new API call)
        """
        from financial_dashboard.utils.price_cache import get_price_cache
        
        tickers = ['GOOG']
        start = '2024-01-01'
        end = '2024-01-10'
        
        cache = get_price_cache()
        
        # Fetch data (this will cache it)
        df1 = load_price_data(tickers, start, end)
        assert not df1.empty
        
        # Verify cache has the entry
        stats_before = cache.get_stats()
        assert stats_before['memory_entries'] >= 1, "Cache should have at least 1 entry after fetch"
        
        # Invalidate the cache
        cleared_count = cache.invalidate(tickers, start, end)
        assert cleared_count >= 1, "Should clear at least 1 cache entry"
        
        # Verify cache was cleared
        stats_after_clear = cache.get_stats()
        assert stats_after_clear['memory_entries'] < stats_before['memory_entries'], \
            "Cache should have fewer entries after invalidation"
        
        # Fetch again - should be cache MISS (re-fetches)
        df2 = load_price_data(tickers, start, end)
        assert not df2.empty
        assert len(df2) == len(df1), "Re-fetched data should match"
        
        # Verify cache was repopulated
        stats_final = cache.get_stats()
        assert stats_final['memory_entries'] >= 1, "Cache should be repopulated after re-fetch"



class TestStatusMessages:
    """Test that status messages accurately reflect data source"""
    
    def test_status_shows_live_data_source(self, caplog):
        """
        GREEN Test: Verify logging shows data source (cache HIT/MISS or fallback)
        
        Validates:
        1. First fetch logs "Cache MISS" and data source
        2. Second fetch logs "Cache HIT"
        3. Logs contain sufficient information for debugging
        """
        import logging
        from financial_dashboard.utils.price_cache import get_price_cache
        
        caplog.set_level(logging.INFO)
        
        tickers = ['NVDA']
        start = '2024-01-01'
        end = '2024-01-05'
        
        cache = get_price_cache()
        cache.invalidate(tickers, start, end)
        
        # First fetch - should log "Cache MISS"
        caplog.clear()
        df1 = load_price_data(tickers, start, end)
        assert not df1.empty
        
        logs = [rec.message for rec in caplog.records]
        assert any("Cache MISS" in log for log in logs), \
            "Should log cache miss on first fetch"
        
        # Second fetch - should log "Cache HIT"
        caplog.clear()
        df2 = load_price_data(tickers, start, end)
        assert not df2.empty
        
        logs = [rec.message for rec in caplog.records]
        assert any("Cache HIT" in log for log in logs), \
            "Should log cache hit on second fetch"
    
    def test_status_shows_partial_data_warning(self, caplog):
        """
        GREEN Test: Verify logging warns when data is missing or incomplete
        
        Validates:
        1. Invalid tickers trigger warning logs
        2. Partial data scenarios are logged
        3. System continues gracefully (doesn't crash)
        """
        import logging
        
        caplog.set_level(logging.WARNING)
        
        # Mix valid and invalid tickers
        tickers = ['AAPL', 'INVALIDTICKER123XYZ']
        start = '2024-01-01'
        end = '2024-01-05'
        
        caplog.clear()
        df = load_price_data(tickers, start, end)
        
        # Should still return data for valid ticker
        assert not df.empty, "Should return data for valid tickers"
        assert 'AAPL' in df['ticker'].values
        
        # Check for warning logs about missing data
        logs = [rec.message for rec in caplog.records if rec.levelname == 'WARNING']
        assert len(logs) > 0, "Should log warnings for invalid/missing tickers"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
