"""
Property-Based Tests for Picks Pipeline

Uses Hypothesis for property-based testing of cache and enrichment invariants.

Author: Agent-1B
Date: 2025-11-21
"""

import pytest
import json
import tempfile
import pandas as pd
from hypothesis import given, strategies as st, settings
from financial_dashboard.utils.cache_manager import CacheManager
from financial_dashboard.utils.picks_fetcher import PicksFetcher


# ===== CacheManager Property Tests =====

@given(st.dictionaries(
    st.text(min_size=1, max_size=20),
    st.one_of(st.integers(), st.floats(allow_nan=False), st.text(), st.lists(st.integers()))
))
@settings(max_examples=50)
def test_cache_manager_atomic_writes(test_data):
    """Property: Cache writes should be atomic - no partial JSON corruption."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_file = f.name
    
    try:
        memory_cache = {}
        cm = CacheManager(cache_file, memory_cache, ttl_seconds=300)
        
        # Wrap data in expected structure
        wrapped_data = {'detailed': [test_data], 'summary': 'test'}
        
        # Save and immediately load
        save_success = cm.save_to_disk(wrapped_data)
        assert save_success, "Save should succeed"
        
        # File should be valid JSON
        with open(cache_file, 'r') as f:
            loaded = json.load(f)
        
        # Should contain our data
        assert 'detailed' in loaded
        assert len(loaded['detailed']) > 0
        
    finally:
        import os
        if os.path.exists(cache_file):
            os.remove(cache_file)


@given(st.integers(min_value=1, max_value=3600))
@settings(max_examples=30, deadline=None)  # No deadline - test includes sleep()
def test_cache_ttl_invariant(ttl_seconds):
    """Property: Cache TTL should be respected - fresh cache within TTL, stale after."""
    import time
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_file = f.name
    
    try:
        memory_cache = {}
        cm = CacheManager(cache_file, memory_cache, ttl_seconds=ttl_seconds)
        
        # Save some data
        test_data = {'detailed': [{'test': 'data'}], 'generated_at': time.time()}
        cm.update_cache(test_data)
        
        # Should be fresh immediately
        assert cm.is_cache_fresh(), "Cache should be fresh immediately after update"
        
        # If TTL is very short, test staleness
        if ttl_seconds <= 2:
            time.sleep(ttl_seconds + 0.5)
            assert not cm.is_cache_fresh(), "Cache should be stale after TTL expires"
        
    finally:
        import os
        if os.path.exists(cache_file):
            os.remove(cache_file)


@given(st.integers(min_value=1, max_value=100))
@settings(max_examples=20)
def test_cache_record_count_consistency(record_count):
    """Property: Record count in metadata should match actual data count."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_file = f.name
    
    try:
        memory_cache = {}
        cm = CacheManager(cache_file, memory_cache, ttl_seconds=300)
        
        # Create test data with specific record count
        test_records = [{'id': i, 'value': f'record_{i}'} for i in range(record_count)]
        test_data = {'detailed': test_records}
        
        # Save and reload
        cm.save_to_disk(test_data)
        loaded = cm.load_from_disk()
        
        # Verify count matches
        assert len(loaded['detailed']) == record_count, "Record count should match"
        
        # Check metadata
        if '_cache_metadata' in loaded:
            metadata_count = loaded['_cache_metadata'].get('record_count', 0)
            assert metadata_count == record_count, "Metadata count should match actual count"
        
    finally:
        import os
        if os.path.exists(cache_file):
            os.remove(cache_file)


# ===== PicksFetcher Property Tests =====

@given(st.lists(
    st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ', min_size=1, max_size=5),
    min_size=1,
    max_size=20,
    unique=True
))
@settings(max_examples=30)
def test_picks_enrichment_preserves_rows(tickers):
    """Property: Price enrichment should preserve all original rows."""
    import os
    os.environ['OPTIONS_DETERMINISTIC'] = '1'  # Use deterministic mode
    
    try:
        # Create DataFrame with tickers
        df = pd.DataFrame({
            'Ticker': tickers,
            'Company': [f'{t} Inc.' for t in tickers],
            'Rank': list(range(1, len(tickers) + 1))
        })
        
        original_count = len(df)
        
        # Enrich
        fetcher = PicksFetcher()
        enriched = fetcher.enrich_with_prices(df, ticker_column='Ticker', provenance=True)
        
        # Row count should be preserved
        assert len(enriched) == original_count, "Enrichment should not add or remove rows"
        
        # Original columns should still exist
        assert 'Ticker' in enriched.columns
        assert 'Company' in enriched.columns
        
        # Price columns should be added
        assert 'current_price' in enriched.columns
        assert 'price_source' in enriched.columns
        
    finally:
        del os.environ['OPTIONS_DETERMINISTIC']


@given(st.lists(
    st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ', min_size=1, max_size=5),
    min_size=1,
    max_size=10,
    unique=True
))
@settings(max_examples=20)
def test_picks_provenance_fields_present(tickers):
    """Property: Enriched picks should always have provenance fields when requested."""
    import os
    os.environ['OPTIONS_DETERMINISTIC'] = '1'
    
    try:
        df = pd.DataFrame({
            'Ticker': tickers,
            'Company': [f'{t} Corp.' for t in tickers]
        })
        
        fetcher = PicksFetcher()
        enriched = fetcher.enrich_with_prices(df, provenance=True)
        
        # All provenance fields should be present
        assert 'price_source' in enriched.columns, "price_source should be present"
        assert 'price_fetched_at' in enriched.columns, "price_fetched_at should be present"
        assert 'price_age_seconds' in enriched.columns, "price_age_seconds should be present"
        
        # In deterministic mode, all should have values
        assert enriched['price_source'].notna().all(), "All rows should have price_source"
        
    finally:
        del os.environ['OPTIONS_DETERMINISTIC']


@given(st.integers(min_value=1, max_value=100))
@settings(max_examples=20)
def test_deterministic_prices_are_consistent(num_picks):
    """Property: Deterministic prices should be the same for the same ticker."""
    import os
    os.environ['OPTIONS_DETERMINISTIC'] = '1'
    
    try:
        # Create two identical DataFrames
        tickers = [f'SYM{i}' for i in range(num_picks)]
        
        df1 = pd.DataFrame({'Ticker': tickers, 'Company': ['Test'] * num_picks})
        df2 = pd.DataFrame({'Ticker': tickers, 'Company': ['Test'] * num_picks})
        
        fetcher = PicksFetcher()
        
        enriched1 = fetcher.enrich_with_prices(df1, provenance=True)
        enriched2 = fetcher.enrich_with_prices(df2, provenance=True)
        
        # Prices should be identical for same tickers
        for ticker in tickers:
            price1 = enriched1[enriched1['Ticker'] == ticker]['current_price'].iloc[0]
            price2 = enriched2[enriched2['Ticker'] == ticker]['current_price'].iloc[0]
            
            assert price1 == price2, f"Deterministic prices should be consistent for {ticker}"
        
    finally:
        del os.environ['OPTIONS_DETERMINISTIC']


@given(st.text(min_size=1, max_size=100))
@settings(max_examples=20)
def test_csv_load_handles_any_path(csv_content):
    """Property: CSV loader should handle invalid paths gracefully."""
    fetcher = PicksFetcher()
    
    # Non-existent path should raise FileNotFoundError
    with pytest.raises(FileNotFoundError):
        fetcher.load_from_csv(f'/nonexistent/path/{csv_content}.csv')


def test_cache_concurrent_access():
    """Property: Concurrent cache access should not corrupt data."""
    import threading
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_file = f.name
    
    try:
        memory_cache = {}
        cm = CacheManager(cache_file, memory_cache, ttl_seconds=300)
        
        errors = []
        
        def writer(thread_id):
            try:
                for i in range(10):
                    data = {
                        'detailed': [{'thread': thread_id, 'iteration': i}],
                        'thread_id': thread_id
                    }
                    cm.save_to_disk(data)
            except Exception as e:
                errors.append(e)
        
        # Run 5 concurrent writers
        threads = [threading.Thread(target=writer, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should complete without errors
        assert len(errors) == 0, f"Concurrent access failed: {errors}"
        
        # Cache file should be valid JSON
        with open(cache_file, 'r') as f:
            final_data = json.load(f)
        
        assert 'detailed' in final_data
        
    finally:
        import os
        if os.path.exists(cache_file):
            os.remove(cache_file)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
