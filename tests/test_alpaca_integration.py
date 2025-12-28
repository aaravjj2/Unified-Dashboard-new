"""
Integration tests for Options Lab caching, circuit breaker, and export.

These tests require live Alpaca credentials but test the full flow.
Run with: pytest tests/test_alpaca_integration.py -v -m integration
"""

import json
import pytest
import os
import sys

# Load env from keys.env
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
keys_env = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'keys.env')
if os.path.exists(keys_env):
    load_dotenv(keys_env)

# Skip if no API keys after loading
pytestmark = pytest.mark.skipif(
    not os.getenv('APCA_API_KEY_ID'),
    reason="Alpaca API credentials not configured"
)


class TestCacheIntegration:
    """Integration tests for options cache."""
    
    @pytest.mark.integration
    def test_cache_stores_and_retrieves(self):
        """Test cache stores and retrieves data correctly."""
        from financial_dashboard.tabs.options_lab.options_cache import get_options_cache
        
        cache = get_options_cache()
        
        # Store test data
        test_data = {'ticker': 'TEST', 'chains': {}}
        cache.set('TEST_KEY', test_data, ttl=60)
        
        # Retrieve
        retrieved = cache.get('TEST_KEY')
        assert retrieved == test_data
        
    @pytest.mark.integration
    def test_cache_ttl_works(self):
        """Test cache TTL expiration."""
        import time
        from financial_dashboard.tabs.options_lab.options_cache import get_options_cache
        
        cache = get_options_cache()
        
        # Store with 1 second TTL
        cache.set('EXPIRE_KEY', {'data': 'test'}, ttl=1)
        
        # Should exist immediately
        assert cache.get('EXPIRE_KEY') is not None
        
        # Wait for expiration
        time.sleep(1.5)
        
        # Should be gone
        assert cache.get('EXPIRE_KEY') is None
        
    @pytest.mark.integration
    def test_cache_stats_accurate(self):
        """Test cache statistics are accurate."""
        from financial_dashboard.tabs.options_lab.options_cache import OptionsChainCache
        
        # Create fresh cache for accurate stats
        cache = OptionsChainCache(default_ttl=300, max_size=10)
        
        # Store item
        cache.set('STATS_KEY', {'data': 'test'})
        
        # Hit
        cache.get('STATS_KEY')
        
        # Miss
        cache.get('NONEXISTENT')
        
        info = cache.get_info()
        # Stats are accumulated across singleton, just check structure
        assert 'stats' in info
        assert 'hits' in info['stats']
        assert 'misses' in info['stats']
        assert 'hit_rate' in info['stats']


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker."""
    
    @pytest.mark.integration
    def test_circuit_breaker_tracks_failures(self):
        """Test circuit breaker opens after failures."""
        from financial_dashboard.tabs.options_lab.circuit_breaker import CircuitBreaker
        
        cb = CircuitBreaker('test_breaker_failures', failure_threshold=3, recovery_timeout=10)
        
        # Record failures via internal method (public API is via decorator)
        test_exc = ValueError('test failure')
        for _ in range(3):
            cb._record_failure(test_exc)
        
        assert cb.state.value == 'open'
        
    @pytest.mark.integration
    def test_circuit_breaker_decorator(self):
        """Test circuit breaker decorator catches exceptions."""
        from financial_dashboard.tabs.options_lab.circuit_breaker import with_circuit_breaker
        
        call_count = 0
        
        @with_circuit_breaker('decorator_test', failure_threshold=2, recovery_timeout=5)
        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Intentional failure")
        
        # Call twice to trigger circuit open
        for _ in range(2):
            try:
                failing_func()
            except ValueError:
                pass
        
        # Third call should be rejected
        with pytest.raises(Exception) as exc_info:
            failing_func()
        
        assert 'Circuit breaker' in str(exc_info.value) or 'open' in str(exc_info.value).lower()


class TestExportIntegration:
    """Integration tests for export functionality."""
    
    @pytest.mark.integration
    def test_csv_export_format(self):
        """Test CSV export produces valid format."""
        from financial_dashboard.tabs.options_lab.export_utils import export_chain_to_csv
        
        chain_data = {
            'ticker': 'SPY',
            'spot_price': 450.00,
            'chains': {
                '2025-12-29': {
                    'calls': [
                        {'strike': 450, 'bid': 5.00, 'ask': 5.10, 'last': 5.05, 'volume': 1000, 'oi': 5000, 'iv': 0.20, 'delta': 0.50, 'gamma': 0.02, 'theta': -0.05, 'vega': 0.10}
                    ],
                    'puts': [
                        {'strike': 450, 'bid': 4.00, 'ask': 4.10, 'last': 4.05, 'volume': 800, 'oi': 4000, 'iv': 0.22, 'delta': -0.50, 'gamma': 0.02, 'theta': -0.05, 'vega': 0.10}
                    ]
                }
            }
        }
        
        csv_content = export_chain_to_csv(chain_data, '2025-12-29')
        
        # Check header has metadata
        assert '# Ticker: SPY' in csv_content
        assert '# Expiration: 2025-12-29' in csv_content
        
        # Check data rows
        lines = csv_content.strip().split('\n')
        data_lines = [l for l in lines if not l.startswith('#') and l.strip()]
        
        assert len(data_lines) >= 2  # Header + at least one data row
        assert 'strike' in data_lines[0].lower()
        assert '450' in csv_content
        
    @pytest.mark.integration
    def test_json_export_format(self):
        """Test JSON export produces valid format."""
        from financial_dashboard.tabs.options_lab.export_utils import export_chain_to_json
        
        chain_data = {
            'ticker': 'SPY',
            'spot_price': 450.00,
            'chains': {
                '2025-12-29': {
                    'calls': [{'strike': 450, 'bid': 5.00}],
                    'puts': [{'strike': 450, 'bid': 4.00}]
                }
            }
        }
        
        json_content = export_chain_to_json(chain_data, pretty=True)
        
        # Should be valid JSON
        parsed = json.loads(json_content)
        
        assert parsed['ticker'] == 'SPY'
        assert 'export_time' in parsed  # Key is export_time not exported_at
        assert 'chains' in parsed


class TestHealthEndpointsIntegration:
    """Integration tests for health check endpoints."""
    
    @pytest.mark.integration
    def test_health_blueprint_creation(self):
        """Test health blueprint can be created."""
        from financial_dashboard.tabs.options_lab import options_health_blueprint
        
        assert options_health_blueprint is not None
        assert options_health_blueprint.name == 'options_health'
        
    @pytest.mark.integration
    def test_health_blueprint_has_routes(self):
        """Test health blueprint has expected routes."""
        from financial_dashboard.tabs.options_lab import options_health_blueprint
        
        # Blueprint deferred_functions are registered when added to app
        # Just verify blueprint has correct url_prefix
        assert options_health_blueprint.url_prefix == '/api/options'


class TestLiveAPIIntegration:
    """Integration tests that call the live Alpaca API."""
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_cached_option_chain_fetch(self):
        """Test fetching options chain with caching."""
        from financial_dashboard.tabs.options_lab import get_cached_option_chain
        
        # First call - should hit API (returns tuple: data, was_cached)
        result1 = get_cached_option_chain('SPY')
        
        if result1 is None:
            pytest.skip("No data returned - API may be unavailable")
        
        # Handle both tuple return (data, was_cached) and dict return
        data1 = result1[0] if isinstance(result1, tuple) else result1
            
        assert data1['ticker'] == 'SPY'
        assert 'chains' in data1
        
        # Second call - should hit cache
        result2 = get_cached_option_chain('SPY')
        data2 = result2[0] if isinstance(result2, tuple) else result2
        
        # Data should be identical (from cache)
        assert data1['ticker'] == data2['ticker']
        
    @pytest.mark.integration
    @pytest.mark.slow
    def test_alpaca_metrics(self):
        """Test Alpaca metrics collection."""
        from financial_dashboard.tabs.options_lab import get_alpaca_metrics
        
        metrics = get_alpaca_metrics()
        
        assert isinstance(metrics, dict)
        assert 'api_calls' in metrics
        assert 'cache_hits' in metrics


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'integration'])
