"""
Unit Tests for CacheManager and PicksFetcher

Tests STEP 2 utilities for picks pipeline.
"""

import os
import sys
import json
import tempfile
import shutil
import pytest
import pandas as pd
from pathlib import Path
from datetime import datetime, timezone

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from financial_dashboard.utils.cache_manager import CacheManager
from financial_dashboard.utils.picks_fetcher import PicksFetcher


class TestCacheManager:
    """Test CacheManager thread-safe operations and TTL validation."""
    
    def test_init_creates_directory(self):
        """Test that CacheManager creates cache directory if missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, 'subdir', 'cache.json')
            memory_cache = {}
            
            cm = CacheManager(cache_path, memory_cache, ttl_seconds=60)
            
            assert os.path.exists(os.path.dirname(cache_path))
            assert cm.cache_file_path == cache_path
            assert cm.ttl_seconds == 60
    
    def test_save_and_load_from_disk(self):
        """Test atomic save and load operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, 'test_cache.json')
            memory_cache = {}
            
            cm = CacheManager(cache_path, memory_cache)
            
            # Save data
            test_data = {
                'detailed': [
                    {'ticker': 'AAPL', 'price': 150.0},
                    {'ticker': 'GOOGL', 'price': 2800.0}
                ],
                'generated_at': datetime.now(timezone.utc).isoformat()
            }
            
            result = cm.save_to_disk(test_data)
            assert result is True
            assert os.path.exists(cache_path)
            
            # Load data
            loaded = cm.load_from_disk()
            assert 'detailed' in loaded
            assert len(loaded['detailed']) == 2
            assert loaded['detailed'][0]['ticker'] == 'AAPL'
    
    def test_load_missing_file(self):
        """Test loading from non-existent cache file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, 'missing.json')
            memory_cache = {}
            
            cm = CacheManager(cache_path, memory_cache)
            loaded = cm.load_from_disk()
            
            assert loaded == {}
    
    def test_load_corrupted_file(self):
        """Test loading from corrupted JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, 'corrupted.json')
            memory_cache = {}
            
            # Write invalid JSON
            with open(cache_path, 'w') as f:
                f.write('{ invalid json }}')
            
            cm = CacheManager(cache_path, memory_cache)
            loaded = cm.load_from_disk()
            
            assert loaded == {}
    
    def test_atomic_write(self):
        """Test that saves use atomic write (temp file + rename)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, 'atomic_test.json')
            memory_cache = {}
            
            cm = CacheManager(cache_path, memory_cache)
            
            # Initial save
            cm.save_to_disk({'version': 1})
            
            # Second save should atomically replace
            cm.save_to_disk({'version': 2})
            
            loaded = cm.load_from_disk()
            assert loaded['version'] == 2
    
    def test_is_cache_fresh(self):
        """Test TTL validation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = os.path.join(tmpdir, 'ttl_test.json')
            memory_cache = {}
            
            cm = CacheManager(cache_path, memory_cache, ttl_seconds=1)
            
            # Save fresh data
            cm.save_to_disk({'data': 'test'})
            
            # Immediately check - should be fresh
            assert cm.is_cache_fresh() is True
            
            # Wait for TTL to expire
            import time
            time.sleep(1.1)
            
            # Should be stale
            assert cm.is_cache_fresh() is False


class TestPicksFetcher:
    """Test PicksFetcher data loading and enrichment."""
    
    def test_load_from_csv(self):
        """Test loading picks from CSV file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, 'test_picks.csv')
            
            # Create test CSV
            test_df = pd.DataFrame({
                'ticker': ['AAPL', 'MSFT', 'GOOGL'],
                'score': [95, 90, 85],
                'rank': [1, 2, 3]
            })
            test_df.to_csv(csv_path, index=False)
            
            fetcher = PicksFetcher()
            loaded_df = fetcher.load_from_csv(csv_path)
            
            assert len(loaded_df) == 3
            assert 'ticker' in loaded_df.columns
            assert '_source' in loaded_df.columns
            assert loaded_df.iloc[0]['ticker'] == 'AAPL'
    
    def test_load_from_csv_missing_file(self):
        """Test loading from non-existent CSV."""
        fetcher = PicksFetcher()
        
        with pytest.raises(FileNotFoundError):
            fetcher.load_from_csv('/nonexistent/path.csv')
    
    def test_load_from_csv_required_columns(self):
        """Test CSV validation with required columns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_path = os.path.join(tmpdir, 'test.csv')
            
            # Create CSV missing required column
            test_df = pd.DataFrame({
                'ticker': ['AAPL'],
                'score': [95]
            })
            test_df.to_csv(csv_path, index=False)
            
            fetcher = PicksFetcher()
            
            # Should raise ValueError for missing 'rank'
            with pytest.raises(ValueError, match="Missing required columns"):
                fetcher.load_from_csv(csv_path, required_columns=['ticker', 'score', 'rank'])
    
    def test_load_from_fixture(self):
        """Test loading from deterministic fixture."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_path = os.path.join(tmpdir, 'weekly_fixture.json')
            
            # Create fixture
            fixture_data = {
                'run_type': 'weekly',
                'picks': [
                    {'ticker': 'NVDA', 'score': 98},
                    {'ticker': 'AAPL', 'score': 95}
                ]
            }
            
            with open(fixture_path, 'w') as f:
                json.dump(fixture_data, f)
            
            # Set deterministic mode
            os.environ['OPTIONS_DETERMINISTIC'] = '1'
            
            try:
                fetcher = PicksFetcher(fixture_path=fixture_path)
                df = fetcher.load_from_fixture()
                
                assert len(df) == 2
                assert 'ticker' in df.columns
                assert df.iloc[0]['ticker'] == 'NVDA'
            finally:
                os.environ.pop('OPTIONS_DETERMINISTIC', None)
    
    def test_enrich_with_prices(self):
        """Test price enrichment with provenance."""
        # Create test DataFrame
        test_df = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT'],
            'score': [95, 90]
        })
        
        # Mock price client
        class MockPriceClient:
            def fetch_ticker_prices(self, ticker):
                return {
                    'current_price': 150.0 if ticker == 'AAPL' else 380.0,
                    'daily_change': 1.5,
                    'source': 'mock'
                }
        
        fetcher = PicksFetcher(price_client=MockPriceClient())
        enriched = fetcher.enrich_with_prices(test_df)
        
        assert 'current_price' in enriched.columns
        assert 'price_source' in enriched.columns
        assert enriched.loc[enriched['ticker'] == 'AAPL', 'current_price'].iloc[0] == 150.0
        assert enriched.loc[enriched['ticker'] == 'MSFT', 'current_price'].iloc[0] == 380.0


def run_tests():
    """Run all unit tests and save results."""
    pytest_args = [
        __file__,
        '-v',
        '--tb=short',
        '-q'
    ]
    
    result_code = pytest.main(pytest_args)
    
    # Save test results to diagnostics
    output_path = PROJECT_ROOT / 'reports' / 'picks' / 'diagnostics' / 'pytest_units.txt'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(f"Unit tests for CacheManager and PicksFetcher\n")
        f.write(f"Run at: {datetime.now().isoformat()}\n")
        f.write(f"Result code: {result_code}\n")
        f.write(f"\nTests: {'PASSED' if result_code == 0 else 'FAILED'}\n")
    
    return result_code


if __name__ == '__main__':
    sys.exit(run_tests())
