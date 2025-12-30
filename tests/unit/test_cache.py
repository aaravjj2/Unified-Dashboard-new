"""
Unit tests for Phase 1 Cache Manager with Redis support.

Tests RedisCacheBackend with local fallback mode.
"""

import pytest
import os
import time

# Set deterministic mode
os.environ['PHASE1_DETERMINISTIC'] = '1'

from financial_dashboard.utils.cache_manager import (
    RedisCacheBackend,
    get_redis_cache,
    cache_key_optimization,
    cache_key_macro,
    cache_key_frontier
)


class TestRedisCacheBackend:
    """Test Redis cache with local fallback."""
    
    def test_singleton_pattern(self):
        """Cache backend should be singleton."""
        cache1 = get_redis_cache()
        cache2 = get_redis_cache()
        assert cache1 is cache2
    
    def test_set_and_get(self):
        """Test basic set and get operations."""
        cache = RedisCacheBackend(prefix='test_phase1:')
        
        # Set value
        result = cache.set('test_key', {'value': 42, 'data': [1, 2, 3]})
        assert result is True
        
        # Get value
        retrieved = cache.get('test_key')
        assert retrieved is not None
        assert retrieved['value'] == 42
        assert retrieved['data'] == [1, 2, 3]
    
    def test_ttl_expiration(self):
        """Test TTL expiration in local fallback."""
        cache = RedisCacheBackend(prefix='test_ttl:')
        
        # Set with 1 second TTL
        cache.set('expiring_key', 'test_value', ttl=1)
        
        # Should exist immediately
        assert cache.get('expiring_key') == 'test_value'
        
        # Wait for expiration (only works reliably in local mode)
        if cache._redis_client is None:
            time.sleep(1.5)
            assert cache.get('expiring_key') is None
    
    def test_delete(self):
        """Test delete operation."""
        cache = RedisCacheBackend(prefix='test_delete:')
        
        cache.set('to_delete', 'value')
        assert cache.exists('to_delete')
        
        cache.delete('to_delete')
        assert not cache.exists('to_delete')
    
    def test_exists(self):
        """Test exists check."""
        cache = RedisCacheBackend(prefix='test_exists:')
        
        assert not cache.exists('nonexistent')
        cache.set('existing', 'value')
        assert cache.exists('existing')
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        cache = get_redis_cache()
        stats = cache.get_stats()
        
        assert 'backend' in stats
        assert stats['backend'] in ['redis', 'local']
        assert 'local_cache_size' in stats
        assert 'prefix' in stats


class TestCacheKeyGenerators:
    """Test cache key generation functions."""
    
    def test_optimization_key(self):
        """Test optimization cache key generation."""
        key1 = cache_key_optimization(['AAPL', 'MSFT'], 'CDaR')
        key2 = cache_key_optimization(['MSFT', 'AAPL'], 'CDaR')  # Different order
        key3 = cache_key_optimization(['AAPL', 'MSFT'], 'EVaR')  # Different measure
        
        # Same tickers (different order) should produce same key
        assert key1 == key2
        
        # Different risk measure should produce different key
        assert key1 != key3
        
        # Key should contain expected prefix
        assert 'riskfolio:opt:CDaR:' in key1
    
    def test_macro_key(self):
        """Test macro data cache key generation."""
        key_gdp = cache_key_macro('gdp', 'USA')
        key_cpi = cache_key_macro('cpi', 'USA')
        key_gdp_eu = cache_key_macro('gdp', 'EU')
        
        assert key_gdp != key_cpi
        assert key_gdp != key_gdp_eu
        assert 'openbb:macro:USA:gdp' in key_gdp
    
    def test_frontier_key(self):
        """Test frontier cache key generation."""
        key = cache_key_frontier(['AAPL', 'GOOGL', 'TSLA'], 'CDaR')
        
        assert 'riskfolio:frontier:CDaR:' in key
        
        # Order shouldn't matter
        key2 = cache_key_frontier(['TSLA', 'GOOGL', 'AAPL'], 'CDaR')
        assert key == key2


class TestCacheIntegration:
    """Integration tests for cache with portfolio data."""
    
    def test_cache_portfolio_weights(self):
        """Test caching portfolio optimization weights."""
        cache = RedisCacheBackend(prefix='test_portfolio:')
        
        tickers = ['AAPL', 'MSFT', 'GOOGL']
        weights = {'AAPL': 0.4, 'MSFT': 0.35, 'GOOGL': 0.25}
        
        key = cache_key_optimization(tickers, 'CDaR')
        cache.set(key, {'weights': weights, 'risk': 0.15, 'return': 0.12})
        
        retrieved = cache.get(key)
        assert retrieved is not None
        assert retrieved['weights'] == weights
        assert abs(sum(retrieved['weights'].values()) - 1.0) < 0.01
    
    def test_cache_macro_data(self):
        """Test caching macro economic data."""
        cache = RedisCacheBackend(prefix='test_macro:')
        
        gdp_data = {
            'dates': ['2024-Q1', '2024-Q2', '2024-Q3'],
            'values': [3.1, 2.8, 3.0],
            'source': 'openbb'
        }
        
        key = cache_key_macro('gdp', 'USA')
        cache.set(key, gdp_data, ttl=86400)  # 24 hour TTL
        
        retrieved = cache.get(key)
        assert retrieved is not None
        assert retrieved['values'] == [3.1, 2.8, 3.0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
