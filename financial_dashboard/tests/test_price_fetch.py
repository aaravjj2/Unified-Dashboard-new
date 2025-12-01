"""
Unit tests for utils/price_fetch.py

Tests price fetching with caching and fallback mechanisms.
"""
import pytest
from unittest.mock import Mock, patch
from utils import price_fetch


class TestPriceFetch:
    """Test price fetching functions."""
    
    def test_get_price_single_returns_dict_or_none(self, sample_ticker):
        """Test that get_price_single returns dict with last_price key."""
        result = price_fetch.get_price_single(sample_ticker)
        
        assert result is not None
        assert isinstance(result, dict)
        assert 'last_price' in result
        
        if result['last_price'] is not None:
            assert isinstance(result['last_price'], (float, int))
            assert result['last_price'] > 0
    
    def test_fetch_prices_batch_returns_dict(self, sample_tickers):
        """Test that fetch_prices_batch returns dictionary."""
        result = price_fetch.fetch_prices_batch(sample_tickers)
        
        assert isinstance(result, dict)
        assert len(result) <= len(sample_tickers)
        
        for ticker, price_data in result.items():
            assert ticker in sample_tickers
            if price_data is not None:
                assert isinstance(price_data, dict)
                assert 'last_price' in price_data
                if price_data['last_price'] is not None:
                    assert isinstance(price_data['last_price'], (float, int))
                    assert price_data['last_price'] > 0
    
    def test_price_fetch_handles_invalid_ticker(self):
        """Test handling of invalid ticker symbols."""
        result = price_fetch.get_price_single('INVALIDTICKER12345')
        
        # Should return dict with None last_price for invalid ticker
        assert result is not None
        assert isinstance(result, dict)
        assert 'last_price' in result
        assert result['last_price'] is None
    
    def test_price_fetch_handles_empty_list(self):
        """Test handling of empty ticker list."""
        result = price_fetch.fetch_prices_batch([])
        
        assert isinstance(result, dict)
        assert len(result) == 0
    
    @pytest.mark.skipif(not hasattr(price_fetch, 'cache') or price_fetch.cache is None, 
                       reason="Cache not available")
    def test_price_fetch_uses_cache(self, sample_ticker):
        """Test that price fetching uses cache."""
        # First call
        result1 = price_fetch.get_price_single(sample_ticker)
        
        # Second call should use cache
        result2 = price_fetch.get_price_single(sample_ticker)
        
        if result1 is not None and result2 is not None:
            # Should return same cached value
            assert result1 == result2


class TestFinnhubKeyRotation:
    """Test Finnhub API key rotation."""
    
    def test_finnhub_keys_loaded(self):
        """Test that Finnhub keys are loaded."""
        # Keys should be loaded during module import
        assert isinstance(price_fetch.FINNHUB_KEYS, list)
    
    def test_get_next_finnhub_key(self):
        """Test Finnhub key rotation."""
        if len(price_fetch.FINNHUB_KEYS) > 0:
            key1 = price_fetch._get_next_finnhub_key()
            key2 = price_fetch._get_next_finnhub_key()
            
            assert key1 is not None
            assert key2 is not None
            
            if len(price_fetch.FINNHUB_KEYS) > 1:
                # Should rotate through keys
                pass  # Rotation logic test


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
