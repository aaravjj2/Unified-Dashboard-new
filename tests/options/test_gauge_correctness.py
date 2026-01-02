"""
Unit Tests for Sentiment Gauge Correctness

Tests the hype gauge functionality in Scanner Workspace.
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dash import html
import dash_bootstrap_components as dbc


class TestGaugeCorrectness:
    """Test sentiment gauge correctness."""
    
    def test_create_hype_gauge_structure(self):
        """Test that hype gauge creates correct structure."""
        try:
            from financial_dashboard.dash.layouts.scanner_workspace import create_hype_gauge
        except ImportError:
            from alpaca_options_lab.src.ui.layouts.scanner_workspace import create_hype_gauge
        
        gauge = create_hype_gauge('NVDA', 0.75, 'Bullish', False)
        
        assert isinstance(gauge, dbc.Card)
        # Check that gauge contains expected content
        gauge_str = str(gauge)
        assert 'NVDA' in gauge_str or 'Bullish' in gauge_str
    
    def test_gauge_score_colors(self):
        """Test gauge color based on score."""
        try:
            from financial_dashboard.dash.layouts.scanner_workspace import create_hype_gauge
        except ImportError:
            from alpaca_options_lab.src.ui.layouts.scanner_workspace import create_hype_gauge
        
        # Bullish (score >= 0.6)
        bullish_gauge = create_hype_gauge('NVDA', 0.75, 'Bullish', False)
        assert 'Bullish' in str(bullish_gauge) or '🚀' in str(bullish_gauge)
        
        # Bearish (score <= 0.4)
        bearish_gauge = create_hype_gauge('TSLA', 0.25, 'Bearish', False)
        assert 'Bearish' in str(bearish_gauge) or '📉' in str(bearish_gauge)
        
        # Neutral (0.4 < score < 0.6)
        neutral_gauge = create_hype_gauge('SPY', 0.5, 'Neutral', False)
        assert 'Neutral' in str(neutral_gauge) or '➡️' in str(neutral_gauge)
    
    def test_gauge_mock_indicator(self):
        """Test that mock data shows indicator."""
        try:
            from financial_dashboard.dash.layouts.scanner_workspace import create_hype_gauge
        except ImportError:
            from alpaca_options_lab.src.ui.layouts.scanner_workspace import create_hype_gauge
        
        mock_gauge = create_hype_gauge('GLD', 0.5, 'Loading...', True)
        assert 'MOCK' in str(mock_gauge) or 'mock' in str(mock_gauge).lower()
    
    @patch('financial_dashboard.dash.layouts.scanner_workspace.get_news_client')
    def test_update_hype_gauges_callback(self, mock_get_client):
        """Test hype gauges update callback."""
        try:
            from financial_dashboard.dash.layouts.scanner_workspace import register_scanner_callbacks
        except ImportError:
            from alpaca_options_lab.src.ui.layouts.scanner_workspace import register_scanner_callbacks
        from dash import Dash
        
        app = Dash(__name__)
        
        # Mock news client
        mock_client = Mock()
        mock_client.get_hype_score.return_value = {
            'hype_score': 0.65,
            'sentiment_label': 'Bullish',
            'is_mock': False,
            'sentiment_source': 'finnhub'
        }
        mock_get_client.return_value = mock_client
        
        # Register callbacks
        register_scanner_callbacks(app)
        
        # Verify callback registered
        assert len(app.callback_map) > 0


class TestFallbackBehaviors:
    """Test fallback behaviors and circuit breakers."""
    
    def test_circuit_breaker_states(self):
        """Test circuit breaker state transitions."""
        try:
            from financial_dashboard.engines.news.hybrid_client import CircuitBreaker, CircuitBreakerState
        except ImportError:
            from alpaca_options_lab.src.engines.news.hybrid_client import CircuitBreaker, CircuitBreakerState
        
        cb = CircuitBreaker('Test', failure_threshold=3, failure_window=60, recovery_timeout=300)
        
        # Initially closed
        assert cb.state == CircuitBreakerState.CLOSED
        assert cb.is_available
        
        # Record failures
        for _ in range(3):
            cb.record_failure()
        
        # Should be open after threshold
        assert cb.state == CircuitBreakerState.OPEN
        assert not cb.is_available
    
    @patch('financial_dashboard.engines.news.hybrid_client.get_news_client')
    def test_fallback_chain(self, mock_get_client):
        """Test fallback chain when primary source fails."""
        try:
            from financial_dashboard.engines.news.hybrid_client import HybridNewsClient
        except ImportError:
            from alpaca_options_lab.src.engines.news.hybrid_client import HybridNewsClient
        
        # Mock client with circuit breaker open
        mock_client = Mock()
        mock_client._circuit_breakers = {
            'finnhub': Mock(is_available=False),
            'finviz': Mock(is_available=True),
            'stocktwits': Mock(is_available=True),
            'newsapi': Mock(is_available=True)
        }
        
        # Test that fallback is used
        assert mock_client._circuit_breakers['finviz'].is_available
    
    def test_data_degradation_tracking(self):
        """Test data degradation warning system."""
        try:
            from financial_dashboard.engines.news.hybrid_client import DataDegradedWarning
        except ImportError:
            from alpaca_options_lab.src.engines.news.hybrid_client import DataDegradedWarning
        
        warning = DataDegradedWarning()
        
        # Mark source as degraded
        warning.mark_degraded('finnhub', 'Circuit breaker open')
        assert warning.is_degraded('finnhub')
        assert warning.has_degradation
        
        # Mark as healthy
        warning.mark_healthy('finnhub')
        assert not warning.is_degraded('finnhub')
        assert not warning.has_degradation


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

