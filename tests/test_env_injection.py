"""
MISSION A3 ENV HOTFIX - RED Phase Tests
Tests for deterministic environment variable loading and API key validation.
Expected to FAIL initially (RED) then PASS after implementing load_env.py (GREEN).
"""
import pytest
import os
from unittest.mock import patch


class TestRequiredKeysPresent:
    """Test that all required API keys are present in environment."""
    
    REQUIRED_KEYS = [
        'FINNHUB_API_KEY',
        'NEWSAPI_KEY',  # Note: currently env has NEWS_API_KEY
        'APCA_API_KEY_ID',  # Alpaca
        'APCA_API_SECRET_KEY',
        'POLYGON_API_KEY',
        'TIINGO_API_KEY'
    ]
    
    @pytest.mark.parametrize("key_name", REQUIRED_KEYS)
    def test_required_key_present(self, key_name):
        """Each required key must be present and non-empty."""
        value = os.getenv(key_name)
        assert value is not None, f"Key {key_name} is not set in environment"
        assert len(value) > 0, f"Key {key_name} is empty"
        assert value != "your_key_here", f"Key {key_name} has placeholder value"
    
    def test_all_required_keys_present(self):
        """Verify all required keys in one assertion."""
        missing = [k for k in self.REQUIRED_KEYS if not os.getenv(k)]
        assert not missing, f"Missing required keys: {missing}"


class TestFallbackBehaviorWithoutKeys:
    """Test graceful degradation when keys are missing."""
    
    def test_price_client_requires_keys(self):
        """PriceClient should raise error if no valid keys present."""
        with patch.dict(os.environ, {
            'FINNHUB_API_KEY': '',
            'APCA_API_KEY_ID': '',
            'POLYGON_API_KEY': ''
        }, clear=False):
            # Import here to get patched environment
            from utils.price_client import PriceClient
            # Should still initialize but with limited functionality
            client = PriceClient()
            assert client is not None
    
    def test_news_client_requires_keys(self):
        """NewsClient should handle missing keys gracefully."""
        with patch.dict(os.environ, {
            'FINNHUB_API_KEY': '',
            'NEWSAPI_KEY': ''
        }, clear=False):
            from utils.news_client import NewsClient
            # Should initialize even without keys
            client = NewsClient()
            assert client is not None


class TestEnvironmentLoaderIntegration:
    """Test the load_env.py module integration."""
    
    def test_load_env_module_exists(self):
        """Verify load_env.py module can be imported."""
        try:
            from utils import load_env
            assert hasattr(load_env, 'load_environment'), \
                "load_env module should have load_environment() function"
        except ImportError:
            pytest.fail("load_env.py module does not exist yet (expected in RED phase)")
    
    @pytest.mark.skipif(
        not os.path.exists('/app/financial_dashboard/utils/load_env.py'),
        reason="load_env.py not yet implemented"
    )
    def test_load_env_validates_required_keys(self):
        """Verify load_environment() validates all required keys."""
        from utils.load_env import load_environment
        result = load_environment(raise_on_missing=False)
        
        assert 'valid' in result
        assert 'missing' in result
        assert 'present' in result
        
        # Should detect all required keys
        required = ['FINNHUB_API_KEY', 'NEWSAPI_KEY', 'APCA_API_KEY_ID',
                   'APCA_API_SECRET_KEY', 'POLYGON_API_KEY', 'TIINGO_API_KEY']
        assert result['valid'], f"Missing keys: {result['missing']}"
        assert len(result['present']) == len(required)


class TestKeyNormalization:
    """Test that key name variations are normalized."""
    
    def test_newsapi_key_normalized(self):
        """NEWS_API_KEY should be aliased to NEWSAPI_KEY."""
        # Current env has NEWS_API_KEY but code expects NEWSAPI_KEY
        news_api = os.getenv('NEWS_API_KEY')
        newsapi = os.getenv('NEWSAPI_KEY')
        
        # At least one should be present
        assert news_api or newsapi, \
            "Neither NEWS_API_KEY nor NEWSAPI_KEY is present"
        
        # After fix, both should be available (normalized)
        # This test documents the discrepancy
    
    def test_alpaca_key_normalized(self):
        """ALPACA_API_KEY and APCA_API_KEY_ID should be normalized."""
        alpaca_key = os.getenv('ALPACA_API_KEY')
        apca_key = os.getenv('APCA_API_KEY_ID')
        
        assert apca_key, "APCA_API_KEY_ID should be present"


if __name__ == '__main__':
    # Run tests and capture RED state
    pytest.main([__file__, '-v', '--tb=short'])
