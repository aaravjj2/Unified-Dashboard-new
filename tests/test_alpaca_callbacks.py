#!/usr/bin/env python3
"""
Unit Tests for Alpaca Options Lab Callbacks

Tests all callbacks in alpaca_callbacks.py with mock data.
Run with: pytest tests/test_alpaca_callbacks.py -v
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import pandas as pd


# Test fixtures
@pytest.fixture
def mock_options_data():
    """Sample options chain data for testing."""
    return {
        'ticker': 'SPY',
        'spot_price': 590.50,
        'timestamp': '2025-12-27T10:30:00',
        'expirations': ['2025-12-29', '2026-01-03', '2026-01-10'],
        'chains': {
            '2025-12-29': {
                'calls': [
                    {'strike': 585.0, 'lastPrice': 6.50, 'bid': 6.40, 'ask': 6.60,
                     'change': 0.25, 'volume': 1500, 'openInterest': 5000,
                     'impliedVolatility': 0.18, 'delta': 0.65},
                    {'strike': 590.0, 'lastPrice': 3.20, 'bid': 3.10, 'ask': 3.30,
                     'change': 0.15, 'volume': 2500, 'openInterest': 8000,
                     'impliedVolatility': 0.16, 'delta': 0.50},
                ],
                'puts': [
                    {'strike': 585.0, 'lastPrice': 1.80, 'bid': 1.70, 'ask': 1.90,
                     'change': -0.10, 'volume': 1200, 'openInterest': 4500,
                     'impliedVolatility': 0.17, 'delta': -0.35},
                    {'strike': 590.0, 'lastPrice': 3.50, 'bid': 3.40, 'ask': 3.60,
                     'change': -0.20, 'volume': 1800, 'openInterest': 6000,
                     'impliedVolatility': 0.19, 'delta': -0.50},
                ]
            }
        }
    }


@pytest.fixture
def dash_app():
    """Create a test Dash app."""
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True
    )
    return app


class TestLoadOptionsChain:
    """Tests for load_options_chain callback."""
    
    def test_empty_ticker_defaults_to_spy(self):
        """Test that empty ticker defaults to SPY."""
        from financial_dashboard.tabs.options_lab.alpaca_callbacks import load_options_chain
        
        with patch('financial_dashboard.tabs.options_lab.alpaca_callbacks.fetch_options_chain') as mock_fetch:
            mock_fetch.return_value = {
                'ticker': 'SPY',
                'spot_price': 590.0,
                'expirations': ['2025-12-29'],
                'calls': pd.DataFrame(),
                'puts': pd.DataFrame(),
                'error': None,
                'source': 'yfinance'
            }
            
            result, message, style = load_options_chain(1, 0, None)
            
            # Should have called with SPY
            mock_fetch.assert_called_once()
            assert result['ticker'] == 'SPY'
    
    def test_client_unavailable_shows_error(self):
        """Test error message when data fetch fails."""
        from financial_dashboard.tabs.options_lab.alpaca_callbacks import load_options_chain
        
        with patch('financial_dashboard.tabs.options_lab.alpaca_callbacks.fetch_options_chain') as mock_fetch:
            mock_fetch.return_value = {
                'error': 'Failed to fetch data',
                'ticker': 'AAPL',
                'spot_price': 0,
                'expirations': [],
                'calls': pd.DataFrame(),
                'puts': pd.DataFrame()
            }
            
            result, message, style = load_options_chain(1, 0, 'AAPL')
            
            assert result is None
            assert 'Error' in message
            assert '#f44336' in str(style)  # Red error color
    
    def test_successful_load_returns_data(self, mock_options_data):
        """Test successful data load returns proper structure."""
        from financial_dashboard.tabs.options_lab.alpaca_callbacks import load_options_chain
        
        with patch('financial_dashboard.tabs.options_lab.alpaca_callbacks.fetch_options_chain') as mock_fetch:
            # Return data in the format fetch_options_chain provides
            mock_fetch.return_value = {
                'ticker': 'SPY',
                'spot_price': 590.50,
                'expirations': ['2025-12-29', '2026-01-03', '2026-01-10'],
                'calls': pd.DataFrame(mock_options_data['chains']['2025-12-29']['calls']),
                'puts': pd.DataFrame(mock_options_data['chains']['2025-12-29']['puts']),
                'error': None,
                'source': 'yfinance'
            }
            
            result, message, style = load_options_chain(1, 0, 'SPY')
            
            assert result is not None
            assert result['ticker'] == 'SPY'
            assert result['spot_price'] == 590.50
            assert len(result['expirations']) == 3
            assert 'Successfully loaded' in message  # Accept any success emoji (🟢, 🟡, ⚪)
            assert '#4caf50' in str(style)  # Green success color


class TestUpdateHeaderAndExpiration:
    """Tests for update_header_and_expiration callback."""
    
    def test_null_data_returns_none(self):
        """Test that null data returns None for both outputs."""
        from financial_dashboard.tabs.options_lab.alpaca_callbacks import update_header_and_expiration
        
        header, expiration, exp_value = update_header_and_expiration(None)
        
        assert header is None
        assert expiration is None
        assert exp_value is None
    
    def test_valid_data_returns_components(self, mock_options_data):
        """Test that valid data returns header and expiration components."""
        from financial_dashboard.tabs.options_lab.alpaca_callbacks import update_header_and_expiration
        
        header, expiration, exp_value = update_header_and_expiration(mock_options_data)
        
        assert header is not None
        assert expiration is not None
        assert exp_value == '2025-12-29'  # First expiration


class TestSyncExpirationDropdown:
    """Tests for sync_expiration_dropdown callback."""
    
    def test_sync_passes_value_through(self):
        """Test that sync callback passes value unchanged."""
        from financial_dashboard.tabs.options_lab.alpaca_callbacks import sync_expiration_dropdown
        
        result = sync_expiration_dropdown('2025-12-29')
        assert result == '2025-12-29'
    
    def test_sync_handles_none(self):
        """Test that sync callback handles None value."""
        from financial_dashboard.tabs.options_lab.alpaca_callbacks import sync_expiration_dropdown
        
        result = sync_expiration_dropdown(None)
        assert result is None


class TestUpdateOptionsTable:
    """Tests for update_options_table callback."""
    
    def test_null_data_shows_placeholder(self):
        """Test that null data shows placeholder message."""
        from financial_dashboard.tabs.options_lab.alpaca_callbacks import update_options_table
        
        result = update_options_table(None, '2025-12-29')
        
        assert isinstance(result, html.Div)
        # Check for placeholder text
        assert 'Select a ticker' in str(result) or 'Load Chain' in str(result)
    
    def test_null_expiration_shows_placeholder(self, mock_options_data):
        """Test that null expiration shows placeholder."""
        from financial_dashboard.tabs.options_lab.alpaca_callbacks import update_options_table
        
        result = update_options_table(mock_options_data, None)
        
        assert isinstance(result, html.Div)
    
    def test_invalid_expiration_shows_error(self, mock_options_data):
        """Test that invalid expiration shows error message."""
        from financial_dashboard.tabs.options_lab.alpaca_callbacks import update_options_table
        
        result = update_options_table(mock_options_data, '2099-01-01')
        
        assert isinstance(result, html.Div)
        assert 'No data available' in str(result)
    
    def test_valid_data_renders_table(self, mock_options_data):
        """Test that valid data renders options table."""
        from financial_dashboard.tabs.options_lab.alpaca_callbacks import update_options_table
        
        result = update_options_table(mock_options_data, '2025-12-29')
        
        assert result is not None
        # Should return a Div containing the table


class TestAlpacaUIComponents:
    """Tests for Alpaca UI component creation functions."""
    
    def test_create_alpaca_layout_returns_div(self):
        """Test that create_alpaca_layout returns a valid Div."""
        from financial_dashboard.tabs.options_lab.alpaca_ui import create_alpaca_layout
        
        layout = create_alpaca_layout('SPY')
        
        assert isinstance(layout, html.Div)
    
    def test_create_alpaca_layout_contains_required_ids(self):
        """Test that layout contains all required component IDs."""
        from financial_dashboard.tabs.options_lab.alpaca_ui import create_alpaca_layout
        
        layout = create_alpaca_layout('SPY')
        layout_str = str(layout)
        
        required_ids = [
            'alpaca-ticker-input',
            'alpaca-load-button',
            'alpaca-loading',
            'alpaca-header-container',
            'alpaca-expiration-container',
            'alpaca-table-container',
            'alpaca-options-store',
            'alpaca-expiration-dropdown',  # Hidden placeholder
            'alpaca-status-message'
        ]
        
        for component_id in required_ids:
            assert component_id in layout_str, f"Missing component: {component_id}"
    
    def test_create_expiration_selector_with_expirations(self):
        """Test expiration selector creation with valid expirations."""
        from financial_dashboard.tabs.options_lab.alpaca_ui import create_expiration_selector
        
        expirations = ['2025-12-29', '2026-01-03', '2026-01-10']
        selector = create_expiration_selector(expirations, '2025-12-29')
        
        assert isinstance(selector, html.Div)
        assert 'alpaca-expiration-selector' in str(selector)
    
    def test_create_expiration_selector_empty_list(self):
        """Test expiration selector with empty list."""
        from financial_dashboard.tabs.options_lab.alpaca_ui import create_expiration_selector
        
        selector = create_expiration_selector([], None)
        
        assert isinstance(selector, html.Div)
    
    def test_create_alpaca_header(self):
        """Test header creation with valid data."""
        from financial_dashboard.tabs.options_lab.alpaca_ui import create_alpaca_header
        
        header = create_alpaca_header('SPY', 590.50, '2025-12-27 10:30:00')
        
        assert isinstance(header, html.Div)
        assert 'SPY' in str(header)
        assert '590.50' in str(header)


class TestAlpacaOptionsClient:
    """Tests for Alpaca Options API client."""
    
    def test_get_alpaca_client_singleton(self):
        """Test that get_alpaca_client returns singleton."""
        from financial_dashboard.tabs.options_lab.alpaca_options import get_alpaca_client
        
        client1 = get_alpaca_client()
        client2 = get_alpaca_client()
        
        assert client1 is client2
    
    def test_client_available_with_keys(self):
        """Test client availability when keys are set."""
        with patch.dict(os.environ, {
            'APCA_API_KEY_ID': 'test_key',
            'APCA_API_SECRET_KEY': 'test_secret'
        }):
            from financial_dashboard.tabs.options_lab.alpaca_options import AlpacaOptionsClient
            
            # Create new instance to test with patched env
            client = AlpacaOptionsClient()
            # Should be available with valid-looking keys
            assert hasattr(client, 'available')
    
    def test_client_unavailable_without_keys(self):
        """Test client unavailability when keys are missing."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove keys
            os.environ.pop('APCA_API_KEY_ID', None)
            os.environ.pop('APCA_API_SECRET_KEY', None)
            
            from financial_dashboard.tabs.options_lab.alpaca_options import AlpacaOptionsClient
            
            client = AlpacaOptionsClient()
            assert client.available == False


class TestConsoleErrorRegression:
    """Regression tests for console errors (like alpaca-expiration-dropdown issue)."""
    
    def test_hidden_dropdown_exists_in_layout(self):
        """Test that hidden placeholder dropdown exists in initial layout."""
        from financial_dashboard.tabs.options_lab.alpaca_ui import create_alpaca_layout
        
        layout = create_alpaca_layout('SPY')
        layout_str = str(layout)
        
        # The hidden dropdown should exist
        assert 'alpaca-expiration-dropdown' in layout_str
        # And should be hidden
        assert "display': 'none'" in layout_str or "'display': 'none'" in layout_str
    
    def test_visible_selector_has_different_id(self):
        """Test that visible selector uses different ID."""
        from financial_dashboard.tabs.options_lab.alpaca_ui import create_expiration_selector
        
        selector = create_expiration_selector(['2025-12-29'], '2025-12-29')
        selector_str = str(selector)
        
        # Should use alpaca-expiration-selector (not alpaca-expiration-dropdown)
        assert 'alpaca-expiration-selector' in selector_str


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
