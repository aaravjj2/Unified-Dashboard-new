"""
Unit tests for sync_manifest.py - Cross-Tab Synchronization System.

Tests timestamp writing, reading, staleness detection, and dependency tracking.
"""

import pytest
import json
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Import the sync manifest utilities
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'financial_dashboard'))
from utils.sync_manifest import (
    write_sync_timestamp,
    read_sync_manifest,
    is_data_stale,
    mark_dependency,
    get_time_since_update,
    MANIFEST_PATH
)


@pytest.fixture
def clean_manifest():
    """Remove manifest file before each test."""
    if os.path.exists(MANIFEST_PATH):
        os.remove(MANIFEST_PATH)
    yield
    # Cleanup after test
    if os.path.exists(MANIFEST_PATH):
        os.remove(MANIFEST_PATH)


def test_write_creates_manifest_file(clean_manifest):
    """Test that write_sync_timestamp creates the manifest file."""
    assert not os.path.exists(MANIFEST_PATH), "Manifest should not exist before test"
    
    # Write timestamp for market_trends tab
    result = write_sync_timestamp(
        'market_trends',
        job_id='job_test_123',
        status='completed',
        metadata={'tickers': ['AAPL', 'MSFT'], 'row_count': 15}
    )
    
    assert result is True, "write_sync_timestamp should return True on success"
    assert os.path.exists(MANIFEST_PATH), "Manifest file should be created"
    
    # Verify file contents
    with open(MANIFEST_PATH, 'r') as f:
        manifest = json.load(f)
    
    assert 'market_trends' in manifest, "market_trends should be in manifest"
    assert manifest['market_trends']['job_id'] == 'job_test_123'
    assert manifest['market_trends']['status'] == 'completed'
    assert manifest['market_trends']['tickers'] == ['AAPL', 'MSFT']
    assert manifest['market_trends']['row_count'] == 15
    assert 'last_updated' in manifest['market_trends']


def test_read_returns_empty_dict_when_no_file(clean_manifest):
    """Test that read_sync_manifest returns {} when file doesn't exist."""
    manifest = read_sync_manifest()
    assert manifest == {}, "Should return empty dict when file doesn't exist"


def test_read_parses_valid_json(clean_manifest):
    """Test that read_sync_manifest correctly parses valid JSON."""
    # Manually create a manifest file
    test_data = {
        'market_trends': {
            'last_updated': '2025-01-23T20:30:00.123456+00:00',
            'job_id': 'job_456',
            'status': 'completed'
        }
    }
    
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(test_data, f)
    
    # Read it back
    manifest = read_sync_manifest()
    
    assert manifest == test_data
    assert manifest['market_trends']['job_id'] == 'job_456'


def test_is_data_stale_returns_true_when_no_metadata(clean_manifest):
    """Test that is_data_stale returns True when tab has no metadata."""
    stale = is_data_stale('market_trends', max_age_seconds=3600)
    assert stale is True, "Should be stale when no metadata exists"


def test_is_data_stale_returns_false_for_fresh_data(clean_manifest):
    """Test that is_data_stale returns False for recently updated data."""
    # Write current timestamp
    write_sync_timestamp('market_trends', job_id='job_789')
    
    # Check staleness with 1 hour threshold
    stale = is_data_stale('market_trends', max_age_seconds=3600)
    
    assert stale is False, "Should NOT be stale (just written)"


def test_is_data_stale_returns_true_for_old_data(clean_manifest):
    """Test that is_data_stale returns True for old data."""
    # Create manifest with old timestamp (6 hours ago)
    old_time = datetime.now(timezone.utc) - timedelta(hours=6)
    
    manifest = {
        'market_trends': {
            'last_updated': old_time.isoformat(),
            'job_id': 'job_old',
            'status': 'completed'
        }
    }
    
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, 'w') as f:
        json.dump(manifest, f)
    
    # Check staleness with 4 hour threshold (14400 seconds)
    stale = is_data_stale('market_trends', max_age_seconds=14400)
    
    assert stale is True, "Should be stale (6 hours > 4 hour threshold)"


def test_mark_dependency_creates_sync_record(clean_manifest):
    """Test that mark_dependency updates dependent tab metadata."""
    # First, create market_trends data
    write_sync_timestamp('market_trends', job_id='job_source_123')
    
    # Mark portfolio as dependent on market_trends
    result = mark_dependency('portfolio', 'market_trends', source_job_id='job_source_123')
    
    assert result is True
    
    # Verify manifest
    manifest = read_sync_manifest()
    
    assert 'portfolio' in manifest
    assert 'last_synced_with_market_trends' in manifest['portfolio']
    assert manifest['portfolio']['dependent_on_job'] == 'job_source_123'


def test_get_time_since_update_returns_none_for_missing_tab(clean_manifest):
    """Test that get_time_since_update returns None when tab not found."""
    age = get_time_since_update('nonexistent_tab')
    assert age is None


def test_get_time_since_update_returns_timedelta_for_valid_tab(clean_manifest):
    """Test that get_time_since_update returns timedelta for valid tab."""
    # Write timestamp
    write_sync_timestamp('market_trends', job_id='job_age_test')
    
    # Small delay to ensure measurable time difference
    time.sleep(0.5)
    
    # Get age
    age = get_time_since_update('market_trends')
    
    assert age is not None
    assert isinstance(age, timedelta)
    assert age.total_seconds() >= 0.5, "Age should be at least 0.5 seconds"


def test_multiple_tabs_in_manifest(clean_manifest):
    """Test that multiple tabs can coexist in manifest."""
    # Write timestamps for different tabs
    write_sync_timestamp('market_trends', job_id='job_mt')
    write_sync_timestamp('portfolio', job_id='job_pf')
    write_sync_timestamp('volatility_lab', job_id='job_vl')
    
    # Read manifest
    manifest = read_sync_manifest()
    
    assert len(manifest) == 3
    assert 'market_trends' in manifest
    assert 'portfolio' in manifest
    assert 'volatility_lab' in manifest
    assert manifest['market_trends']['job_id'] == 'job_mt'
    assert manifest['portfolio']['job_id'] == 'job_pf'
    assert manifest['volatility_lab']['job_id'] == 'job_vl'


def test_write_updates_existing_tab_entry(clean_manifest):
    """Test that writing to same tab updates (doesn't duplicate)."""
    # First write
    write_sync_timestamp('market_trends', job_id='job_v1')
    
    # Second write (should update, not create duplicate)
    write_sync_timestamp('market_trends', job_id='job_v2')
    
    # Read manifest
    manifest = read_sync_manifest()
    
    assert len(manifest) == 1, "Should only have one market_trends entry"
    assert manifest['market_trends']['job_id'] == 'job_v2', "Should have latest job_id"


def test_corrupted_json_returns_empty_dict(clean_manifest):
    """Test that corrupted JSON file returns empty dict gracefully."""
    # Write invalid JSON
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, 'w') as f:
        f.write("{ invalid json here }")
    
    # Should not crash, return empty dict
    manifest = read_sync_manifest()
    
    assert manifest == {}, "Should return {} for corrupted JSON"


def test_metadata_preserves_all_fields(clean_manifest):
    """Test that metadata dict preserves all custom fields."""
    custom_meta = {
        'tickers': ['AAPL', 'MSFT', 'GOOGL'],
        'row_count': 25,
        'analysis_type': 'backtest',
        'duration_seconds': 45.3,
        'custom_flag': True
    }
    
    write_sync_timestamp('market_trends', job_id='job_meta', metadata=custom_meta)
    
    manifest = read_sync_manifest()
    
    for key, value in custom_meta.items():
        assert manifest['market_trends'][key] == value, f"Metadata field {key} should be preserved"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
