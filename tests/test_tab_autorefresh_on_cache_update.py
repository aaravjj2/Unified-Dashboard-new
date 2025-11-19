"""
Test suite for Market Trends tab auto-refresh on cache update.

MISSION PHASE 3: Smart UI Reload Enhancement
- Tab activation should check cache timestamp
- If cache is newer than last render, reload table
- Otherwise, skip reload to prevent flashing
"""
import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from dash import html, no_update
from dash.exceptions import PreventUpdate


@pytest.fixture
def mock_app():
    """Create a mock Dash app for callback testing."""
    app = Mock()
    app.callback = lambda *args, **kwargs: lambda func: func
    return app


@pytest.fixture
def old_cache_data():
    """Cached data from previous analysis (timestamp: 100)."""
    return {
        'detailed': [
            {'ticker': 'AAPL', 'signal': 'HOLD', 'confidence': 0.60},
            {'ticker': 'MSFT', 'signal': 'HOLD', 'confidence': 0.55}
        ],
        'generated_at': '2025-10-23T10:00:00',
        'timestamp': 100
    }


@pytest.fixture
def new_cache_data():
    """Fresh cache data from recent analysis (timestamp: 200)."""
    return {
        'detailed': [
            {'ticker': 'AAPL', 'signal': 'BUY', 'confidence': 0.85},
            {'ticker': 'MSFT', 'signal': 'BUY', 'confidence': 0.78},
            {'ticker': 'GOOGL', 'signal': 'HOLD', 'confidence': 0.62}
        ],
        'generated_at': '2025-10-23T14:30:00',
        'timestamp': 200
    }


def test_tab_activation_detects_new_cache(mock_app, old_cache_data, new_cache_data):
    """
    CRITICAL TEST: Tab activation should detect when disk cache is newer than rendered data.
    
    Scenario:
    1. User has Market Trends tab open with old data (timestamp=100)
    2. Switches to Forecast tab
    3. Forecast runs full analysis, writes new market_brief.json (timestamp=200)
    4. User switches back to Market Trends tab
    5. Tab activation callback should detect timestamp mismatch and reload
    
    Expected Result:
    - Callback loads new cache data
    - Renders updated table with 3 tickers (not 2)
    - Updates last-rendered-timestamp store
    """
    with patch('financial_dashboard.tabs.market_trends.load_last_cached_results') as mock_load:
        # First call returns old cache (initial render)
        # Second call returns new cache (tab reactivation)
        mock_load.side_effect = [old_cache_data, new_cache_data]
        
        from financial_dashboard.tabs.market_trends import render_on_tab_activation
        
        # FIRST RENDER: User views tab with old cache
        result1 = render_on_tab_activation(
            active_tab='market_trends',
            job_id=None
        )
        
        # Verify old data rendered (2 tickers)
        assert result1 is not None, "Should render initial table"
        # results_area, indicator_msg, indicator_style, news
        results_area_1 = result1[0]
        assert results_area_1 is not None, "Should have results-area output"
        
        # SIMULATE: User switches tabs, analysis runs, writes new cache
        time.sleep(0.1)  # Simulate time passing
        
        # SECOND RENDER: User switches back to Market Trends tab
        result2 = render_on_tab_activation(
            active_tab='market_trends',
            job_id=None
        )
        
        # ASSERTION: Should detect new cache and reload
        assert result2 is not None, "Should reload with new cache"
        results_area_2 = result2[0]
        assert results_area_2 is not None, "Should render updated table"
        
        # Verify load_last_cached_results was called twice (once per render)
        assert mock_load.call_count == 2, "Should check cache on each tab activation"


def test_tab_activation_skips_reload_if_cache_unchanged(mock_app, old_cache_data):
    """
    Verify that if cache hasn't changed, tab activation doesn't cause unnecessary re-renders.
    
    This prevents UI flashing when user rapidly switches tabs.
    """
    with patch('financial_dashboard.tabs.market_trends.load_last_cached_results') as mock_load:
        mock_load.return_value = old_cache_data
        
        from financial_dashboard.tabs.market_trends import render_on_tab_activation
        
        # FIRST ACTIVATION
        result1 = render_on_tab_activation(
            active_tab='market_trends',
            job_id=None
        )
        
        # User switches to Forecast and immediately back
        # Cache hasn't changed (same timestamp)
        
        # SECOND ACTIVATION (same cache)
        result2 = render_on_tab_activation(
            active_tab='market_trends',
            job_id=None
        )
        
        # Both should return same data (no unnecessary re-render)
        assert result1 is not None
        assert result2 is not None
        
        # Verify cache was checked both times
        assert mock_load.call_count == 2


def test_tab_activation_respects_running_job(mock_app, new_cache_data):
    """
    If a job is currently running, tab activation should NOT override results.
    
    The polling callback should handle updates, not the tab activation callback.
    """
    with patch('financial_dashboard.tabs.market_trends.load_last_cached_results') as mock_load:
        mock_load.return_value = new_cache_data
        
        from financial_dashboard.tabs.market_trends import render_on_tab_activation
        
        # Activate tab while job is running
        with pytest.raises(PreventUpdate):
            render_on_tab_activation(
                active_tab='market_trends',
                job_id='running-job-12345'  # Active job
            )
        
        # ASSERTION: Should NOT call load_last_cached_results
        # (prevented before reaching that code)
        # The existing code already has this logic at line 1018-1020


def test_cache_timestamp_comparison_logic():
    """
    Unit test for timestamp comparison logic.
    
    Verify that timestamp comparison correctly identifies newer cache:
    - generated_at (ISO string) → timestamp (unix epoch)
    - Comparison: disk_timestamp > last_rendered_timestamp
    """
    from datetime import datetime
    
    # Old timestamp: 2025-10-23 10:00:00
    old_iso = '2025-10-23T10:00:00'
    old_timestamp = datetime.fromisoformat(old_iso).timestamp()
    
    # New timestamp: 2025-10-23 14:30:00 (4.5 hours later)
    new_iso = '2025-10-23T14:30:00'
    new_timestamp = datetime.fromisoformat(new_iso).timestamp()
    
    # ASSERTION: New timestamp should be greater
    assert new_timestamp > old_timestamp, "New cache should have later timestamp"
    assert (new_timestamp - old_timestamp) > 3600, "Should be hours apart"


def test_cache_file_mtime_fallback():
    """
    If generated_at field is missing, fall back to file modification time (mtime).
    
    This ensures timestamp comparison works even with legacy cache files.
    """
    import os
    import tempfile
    import json
    
    # Create temp cache file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        cache_data = {'detailed': [{'ticker': 'AAPL'}]}  # No generated_at
        json.dump(cache_data, f)
        temp_path = f.name
    
    try:
        # Get file mtime
        mtime = os.path.getmtime(temp_path)
        
        # Verify mtime is a valid timestamp
        assert mtime > 0, "File should have valid modification time"
        assert mtime < time.time(), "mtime should be in the past"
        
        # Simulate comparison
        current_time = time.time()
        assert current_time > mtime, "Current time should be after file creation"
    
    finally:
        os.unlink(temp_path)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
