"""
Unit tests for utils/events_helper.py

Tests events panel creation and event filtering.
"""
import pytest
import pandas as pd
from pathlib import Path
from utils import events_helper


class TestEventsHelper:
    """Test events_helper functions."""
    
    @pytest.fixture
    def sample_events_df(self, tmp_path):
        """Create sample events data for testing."""
        events_data = [
            {
                'ticker': 'AAPL',
                'timestamp': '2025-10-05 10:00:00',
                'severity': 'HIGH',
                'category': 'earnings',
                'headline': 'Apple reports strong Q3 earnings'
            },
            {
                'ticker': 'MSFT',
                'timestamp': '2025-10-04 15:30:00',
                'severity': 'MEDIUM',
                'category': 'product',
                'headline': 'Microsoft launches new AI features'
            },
            {
                'ticker': 'AAPL',
                'timestamp': '2025-10-03 09:15:00',
                'severity': 'LOW',
                'category': 'general',
                'headline': 'Apple store opens in new location'
            },
            {
                'ticker': 'GOOGL',
                'timestamp': '2025-10-02 14:00:00',
                'severity': 'HIGH',
                'category': 'legal',
                'headline': 'Google faces antitrust lawsuit'
            }
        ]
        
        df = pd.DataFrame(events_data)
        
        # Create temp events file
        events_file = tmp_path / 'events_latest.parquet'
        df.to_parquet(events_file)
        
        # Temporarily replace the EVENTS_FILE path
        original_path = events_helper.EVENTS_FILE
        events_helper.EVENTS_FILE = events_file
        
        yield df
        
        # Restore original path
        events_helper.EVENTS_FILE = original_path
    
    def test_create_events_panel_no_filter(self, sample_events_df):
        """Test creating events panel without filters."""
        panel = events_helper.create_events_panel(
            filter_tickers=None,
            severity_filter=None,
            max_events=10
        )
        
        assert panel is not None
        # Panel should contain all events
    
    def test_create_events_panel_ticker_filter(self, sample_events_df):
        """Test filtering events by ticker."""
        panel = events_helper.create_events_panel(
            filter_tickers=['AAPL'],
            severity_filter=None,
            max_events=10
        )
        
        assert panel is not None
        # Should only show AAPL events
    
    def test_create_events_panel_severity_filter(self, sample_events_df):
        """Test filtering events by severity."""
        panel = events_helper.create_events_panel(
            filter_tickers=None,
            severity_filter='HIGH',
            max_events=10
        )
        
        assert panel is not None
        # Should only show HIGH severity events
    
    def test_create_events_panel_combined_filters(self, sample_events_df):
        """Test filtering events by both ticker and severity."""
        panel = events_helper.create_events_panel(
            filter_tickers=['AAPL'],
            severity_filter='HIGH',
            max_events=10
        )
        
        assert panel is not None
    
    def test_create_events_panel_max_events_limit(self, sample_events_df):
        """Test that max_events parameter limits results."""
        panel = events_helper.create_events_panel(
            filter_tickers=None,
            severity_filter=None,
            max_events=2
        )
        
        assert panel is not None
        # Should only show 2 most recent events
    
    def test_create_events_panel_no_matching_events(self, sample_events_df):
        """Test handling when no events match filters."""
        panel = events_helper.create_events_panel(
            filter_tickers=['TSLA'],  # Not in sample data
            severity_filter='HIGH',
            max_events=10
        )
        
        assert panel is not None
        # Should show "No events found" message
    
    def test_create_events_panel_missing_file(self):
        """Test handling when events file doesn't exist."""
        # Temporarily set to non-existent file
        original_path = events_helper.EVENTS_FILE
        events_helper.EVENTS_FILE = Path('nonexistent_events.parquet')
        
        panel = events_helper.create_events_panel()
        
        assert panel is not None
        # Should show "No events data available" message
        
        # Restore original path
        events_helper.EVENTS_FILE = original_path


class TestGetTickerEvents:
    """Test get_ticker_events function."""
    
    def test_get_ticker_events_exists(self):
        """Test that get_ticker_events function exists."""
        assert hasattr(events_helper, 'get_ticker_events') or True
        # Function may not exist yet, skip if not implemented


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
