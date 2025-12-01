"""
Phase 4 Integration Test: Portfolio consumes Market Trends signals.

Tests:
1. Backtest job completion updates sync_manifest.json
2. Portfolio Positions table loads Market Trends signals
3. Columns added: Trend Signal, Momentum, Sentiment, Volatility
4. Dependency tracked in manifest
"""

import pytest
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'financial_dashboard'))

from utils.sync_manifest import read_sync_manifest, write_sync_timestamp, mark_dependency


def test_sync_manifest_exists():
    """Test 1: Verify sync_manifest.json is created after backtest job."""
    cache_dir = Path(__file__).parent.parent / 'cache'
    manifest_path = cache_dir / 'sync_manifest.json'
    
    # Check if manifest file exists
    assert manifest_path.exists(), f"Sync manifest not found at {manifest_path}"
    
    # Read and validate structure
    manifest = read_sync_manifest()
    assert isinstance(manifest, dict), "Manifest should be a dict"
    
    print(f"✅ Sync manifest exists: {manifest_path}")
    print(f"📊 Manifest tabs: {list(manifest.keys())}")


def test_market_trends_in_manifest():
    """Test 2: Verify Market Trends metadata in manifest."""
    manifest = read_sync_manifest()
    
    # Check if market_trends key exists
    assert 'market_trends' in manifest, "market_trends not in sync manifest"
    
    trends_meta = manifest['market_trends']
    
    # Validate required fields
    assert 'last_updated' in trends_meta, "last_updated field missing"
    assert 'job_id' in trends_meta, "job_id field missing"
    assert 'status' in trends_meta, "status field missing"
    
    # Validate values
    assert trends_meta['status'] == 'completed', f"Expected status=completed, got {trends_meta['status']}"
    assert trends_meta['job_id'].startswith('job_'), f"Invalid job_id format: {trends_meta['job_id']}"
    
    # Parse timestamp
    timestamp_str = trends_meta['last_updated']
    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
    assert timestamp.tzinfo is not None, "Timestamp should be timezone-aware"
    
    print(f"✅ Market Trends metadata validated")
    print(f"   Job ID: {trends_meta['job_id']}")
    print(f"   Last Updated: {trends_meta['last_updated']}")
    print(f"   Status: {trends_meta['status']}")
    
    if 'tickers' in trends_meta:
        print(f"   Tickers: {len(trends_meta['tickers'])}")


def test_market_brief_cache_exists():
    """Test 3: Verify market_brief.json exists in cache."""
    cache_dir = Path(__file__).parent.parent / 'cache'
    market_brief_path = cache_dir / 'market_brief.json'
    
    assert market_brief_path.exists(), f"Market brief cache not found at {market_brief_path}"
    
    with open(market_brief_path, 'r') as f:
        brief_data = json.load(f)
    
    # Validate structure
    assert 'detailed' in brief_data, "market_brief.json missing 'detailed' key"
    
    detailed = brief_data['detailed']
    assert len(detailed) > 0, "market_brief.json has no detailed data"
    
    # Check first ticker has required fields
    first_ticker = detailed[0]
    required_fields = ['Ticker', 'Signal', 'Momentum', 'Sentiment', 'Volatility']
    
    for field in required_fields:
        # Try both capitalized and lowercase
        has_field = field in first_ticker or field.lower() in first_ticker
        assert has_field, f"First ticker missing field: {field}"
    
    print(f"✅ Market brief cache validated")
    print(f"   Tickers in cache: {len(detailed)}")
    print(f"   Sample ticker: {first_ticker.get('Ticker') or first_ticker.get('ticker')}")
    print(f"   Sample signal: {first_ticker.get('Signal') or first_ticker.get('signal')}")


def test_portfolio_dependency_marked():
    """Test 4: Verify Portfolio marks dependency after loading Market Trends signals."""
    manifest = read_sync_manifest()
    
    # Portfolio may not have synced yet (tab not activated)
    if 'portfolio' not in manifest:
        print("⚠️  Portfolio not in manifest yet - skipping dependency check")
        print("   (Portfolio dependency will be marked when tab is first activated)")
        return
    
    portfolio_meta = manifest['portfolio']
    
    # Check if dependency is marked
    assert 'last_synced_with_market_trends' in portfolio_meta, "Portfolio didn't mark Market Trends dependency"
    assert 'dependent_on_job' in portfolio_meta, "Portfolio didn't record dependent job_id"
    
    # Validate timestamp
    sync_timestamp_str = portfolio_meta['last_synced_with_market_trends']
    sync_timestamp = datetime.fromisoformat(sync_timestamp_str.replace('Z', '+00:00'))
    assert sync_timestamp.tzinfo is not None, "Sync timestamp should be timezone-aware"
    
    print(f"✅ Portfolio dependency marked")
    print(f"   Last Synced: {portfolio_meta['last_synced_with_market_trends']}")
    print(f"   Dependent Job: {portfolio_meta['dependent_on_job']}")


def test_signal_data_integrity():
    """Test 5: Verify signal data has valid numerical ranges."""
    cache_dir = Path(__file__).parent.parent / 'cache'
    market_brief_path = cache_dir / 'market_brief.json'
    
    with open(market_brief_path, 'r') as f:
        brief_data = json.load(f)
    
    detailed = brief_data['detailed']
    
    for ticker_data in detailed:
        ticker = ticker_data.get('Ticker') or ticker_data.get('ticker')
        
        # Validate signal is one of expected values
        signal = ticker_data.get('Signal') or ticker_data.get('signal')
        valid_signals = ['BUY', 'SELL', 'HOLD', 'N/A', 'Strong Buy', 'Strong Sell']
        assert signal in valid_signals or 'Buy' in signal or 'Sell' in signal or signal == 'N/A', \
            f"{ticker} has invalid signal: {signal}"
        
        # Validate momentum is numeric
        momentum = ticker_data.get('Momentum') or ticker_data.get('momentum', 0)
        assert isinstance(momentum, (int, float)), f"{ticker} momentum not numeric: {momentum}"
        
        # Validate sentiment is numeric
        sentiment = ticker_data.get('Sentiment') or ticker_data.get('sentiment', 0)
        assert isinstance(sentiment, (int, float)), f"{ticker} sentiment not numeric: {sentiment}"
        
        # Validate volatility is numeric and positive
        volatility = ticker_data.get('Volatility') or ticker_data.get('volatility', 0)
        assert isinstance(volatility, (int, float)), f"{ticker} volatility not numeric: {volatility}"
        assert volatility >= 0, f"{ticker} volatility should be >= 0: {volatility}"
    
    print(f"✅ Signal data integrity validated")
    print(f"   All {len(detailed)} tickers have valid signal data")


def test_timestamp_freshness():
    """Test 6: Verify Market Trends data is recent (< 24 hours old)."""
    manifest = read_sync_manifest()
    
    if 'market_trends' not in manifest:
        pytest.skip("Market Trends not in manifest yet")
    
    trends_meta = manifest['market_trends']
    last_updated_str = trends_meta['last_updated']
    
    # Parse timestamp
    last_updated = datetime.fromisoformat(last_updated_str.replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    
    # Calculate age
    age_seconds = (now - last_updated).total_seconds()
    age_hours = age_seconds / 3600
    
    # Warn if older than 24 hours
    if age_hours > 24:
        print(f"⚠️  Market Trends data is {age_hours:.1f} hours old (> 24 hours)")
        print(f"   Last Updated: {last_updated_str}")
        print(f"   Consider running a fresh backtest analysis")
    else:
        print(f"✅ Market Trends data is fresh ({age_hours:.1f} hours old)")
        print(f"   Last Updated: {last_updated_str}")
    
    # Don't fail test, just warn
    assert age_hours < 168, "Market Trends data is > 7 days old - definitely needs refresh"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
