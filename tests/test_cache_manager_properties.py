"""
Property-Based Tests for Cache Manager

Feature: market-trends-fix, Property 4: Cache Persistence Round Trip
Validates: Requirements 6.1, 6.2, 6.3

Uses Hypothesis to generate random analysis results and verify that
save_to_disk followed by load_from_disk preserves all data.
"""

import pytest
import tempfile
import os
import json
from hypothesis import given, strategies as st, settings
from financial_dashboard.utils.cache_manager import CacheManager


# Strategy for generating ticker symbols
ticker_strategy = st.text(
    alphabet=st.characters(whitelist_categories=('Lu',), max_codepoint=90),
    min_size=1,
    max_size=5
)

# Strategy for generating price data
price_strategy = st.one_of(
    st.floats(min_value=0.01, max_value=10000.0, allow_nan=False, allow_infinity=False),
    st.none()
)

# Strategy for generating a single ticker record
ticker_record_strategy = st.fixed_dictionaries({
    'ticker': ticker_strategy,
    'current_price': price_strategy,
    'week_start_price': price_strategy,
    'month_start_price': price_strategy,
    'daily_change': st.one_of(
        st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        st.none()
    ),
    'profit_loss': st.one_of(
        st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False),
        st.none()
    ),
    'data_source': st.one_of(st.just('yfinance'), st.just('alpaca'), st.just('cached'), st.none())
})

# Strategy for generating analysis results
analysis_result_strategy = st.fixed_dictionaries({
    'detailed': st.lists(ticker_record_strategy, min_size=0, max_size=20),
    'market_trend': st.fixed_dictionaries({
        'label': st.one_of(
            st.just('Strong Bull'),
            st.just('Bull'),
            st.just('Neutral'),
            st.just('Bear'),
            st.just('Strong Bear')
        ),
        'composite': st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        'scores': st.dictionaries(
            keys=st.text(min_size=1, max_size=10),
            values=st.floats(min_value=-1.0, max_value=1.0, allow_nan=False, allow_infinity=False),
            min_size=0,
            max_size=5
        )
    }),
    'tickers': st.lists(ticker_strategy, min_size=0, max_size=20)
})


class TestCacheManagerProperties:
    """Property-based tests for CacheManager"""
    
    @given(analysis_result_strategy)
    @settings(max_examples=100, deadline=None)
    def test_cache_persistence_round_trip(self, analysis_result):
        """
        **Feature: market-trends-fix, Property 4: Cache Persistence Round Trip**
        
        Property: For any analysis result, saving to disk and then loading
        should produce equivalent data (all fields preserved).
        
        This test generates random analysis results and verifies that the
        round-trip (save → load) preserves all data correctly.
        """
        # Create temporary cache file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
        
        try:
            # Create cache manager with empty memory cache
            memory_cache = {}
            cache_manager = CacheManager(cache_file, memory_cache)
            
            # Save data to disk
            success = cache_manager.save_to_disk(analysis_result)
            assert success, "save_to_disk should succeed"
            
            # Load data from disk
            loaded_data = cache_manager.load_from_disk()
            
            # Verify all fields are preserved
            assert 'detailed' in loaded_data, "detailed field should be present"
            assert 'market_trend' in loaded_data, "market_trend field should be present"
            assert 'tickers' in loaded_data, "tickers field should be present"
            
            # Verify detailed records
            assert len(loaded_data['detailed']) == len(analysis_result['detailed']), \
                "Number of detailed records should match"
            
            for original, loaded in zip(analysis_result['detailed'], loaded_data['detailed']):
                assert loaded['ticker'] == original['ticker'], "Ticker should match"
                
                # Handle None values and float comparison
                for field in ['current_price', 'week_start_price', 'month_start_price', 
                             'daily_change', 'profit_loss']:
                    if original[field] is None:
                        assert loaded[field] is None, f"{field} should be None"
                    else:
                        assert loaded[field] is not None, f"{field} should not be None"
                        assert abs(loaded[field] - original[field]) < 0.01, \
                            f"{field} should match within tolerance"
                
                assert loaded.get('data_source') == original.get('data_source'), \
                    "data_source should match"
            
            # Verify market trend
            assert loaded_data['market_trend']['label'] == analysis_result['market_trend']['label'], \
                "Market trend label should match"
            assert abs(loaded_data['market_trend']['composite'] - 
                      analysis_result['market_trend']['composite']) < 0.01, \
                "Market trend composite should match within tolerance"
            
            # Verify tickers list
            assert loaded_data['tickers'] == analysis_result['tickers'], \
                "Tickers list should match"
            
            # Verify timestamp was added
            assert 'generated_at' in loaded_data, "generated_at timestamp should be added"
            
        finally:
            # Clean up temp file
            if os.path.exists(cache_file):
                os.remove(cache_file)
    
    @given(st.lists(ticker_record_strategy, min_size=1, max_size=10))
    @settings(max_examples=100, deadline=None)
    def test_cache_preserves_none_values(self, ticker_records):
        """
        Property: None values in price fields should be preserved through
        save/load cycle.
        
        This is important because missing price data should remain as None,
        not be converted to 0 or empty string.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
        
        try:
            memory_cache = {}
            cache_manager = CacheManager(cache_file, memory_cache)
            
            data = {
                'detailed': ticker_records,
                'market_trend': {'label': 'Neutral', 'composite': 0.0, 'scores': {}},
                'tickers': [r['ticker'] for r in ticker_records]
            }
            
            cache_manager.save_to_disk(data)
            loaded = cache_manager.load_from_disk()
            
            for original, loaded_record in zip(ticker_records, loaded['detailed']):
                for field in ['current_price', 'week_start_price', 'month_start_price']:
                    if original[field] is None:
                        assert loaded_record[field] is None, \
                            f"{field} None value should be preserved"
        
        finally:
            if os.path.exists(cache_file):
                os.remove(cache_file)
    
    @given(analysis_result_strategy)
    @settings(max_examples=50, deadline=None)
    def test_update_cache_syncs_memory_and_disk(self, analysis_result):
        """
        Property: update_cache should synchronize both memory and disk cache.
        
        After calling update_cache, both get_cached_data (memory) and
        load_from_disk should return the same data.
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            cache_file = f.name
        
        try:
            memory_cache = {}
            cache_manager = CacheManager(cache_file, memory_cache)
            
            # Update cache
            success = cache_manager.update_cache(analysis_result)
            assert success, "update_cache should succeed"
            
            # Get from memory
            memory_data = cache_manager.get_cached_data()
            
            # Load from disk
            disk_data = cache_manager.load_from_disk()
            
            # Verify they match
            assert len(memory_data.get('detailed', [])) == len(disk_data.get('detailed', [])), \
                "Memory and disk should have same number of records"
            
            assert memory_data.get('tickers') == disk_data.get('tickers'), \
                "Memory and disk should have same tickers"
        
        finally:
            if os.path.exists(cache_file):
                os.remove(cache_file)
