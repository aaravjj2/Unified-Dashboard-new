"""
Unit tests for AlphaSim engine module.
"""
import pytest
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from financial_dashboard.services.alpha_sim.engine import (
    AlphaSimEngine, get_engine
)


# ---------- Mock Data ----------

def create_mock_yf_data(symbol: str, days: int = 100):
    """Create mock yfinance data."""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    np.random.seed(42)
    
    opens = 100 + np.random.randn(days).cumsum()
    highs = opens + abs(np.random.randn(days))
    lows = opens - abs(np.random.randn(days))
    closes = opens + np.random.randn(days) * 0.5
    volumes = np.random.randint(1000000, 10000000, days)
    
    df = pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes
    }, index=dates)
    
    return df


# ---------- AlphaSimEngine Tests ----------

class TestAlphaSimEngine:
    """Tests for AlphaSimEngine class."""
    
    def test_engine_creation(self):
        """Test AlphaSimEngine can be created."""
        engine = AlphaSimEngine()
        assert engine is not None
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_time_series_daily(self, mock_yf):
        """Test time_series_daily endpoint."""
        # Setup mock
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_yf_data("AAPL")
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.time_series_daily("AAPL", outputsize="compact")
        
        assert "Meta Data" in result
        assert "Time Series (Daily)" in result
        assert len(result["Time Series (Daily)"]) > 0
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_time_series_daily_full(self, mock_yf):
        """Test time_series_daily with full output."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_yf_data("AAPL", days=200)
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.time_series_daily("AAPL", outputsize="full")
        
        assert "Meta Data" in result
        assert "Time Series (Daily)" in result
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_time_series_daily_invalid_symbol(self, mock_yf):
        """Test time_series_daily with invalid symbol."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()  # Empty DataFrame
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.time_series_daily("INVALID123")
        
        # Should return error or empty time series
        assert "Error" in result or "Time Series (Daily)" in result
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_calculate_sma(self, mock_yf):
        """Test calculate_sma endpoint."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_yf_data("AAPL")
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.calculate_sma("AAPL", time_period=10, series_type="close")
        
        assert "Meta Data" in result
        assert "Technical Analysis: SMA" in result
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_calculate_sma_different_periods(self, mock_yf):
        """Test calculate_sma with different time periods."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_yf_data("MSFT")
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        
        # Test different periods
        for period in [5, 10, 20, 50]:
            result = engine.calculate_sma("MSFT", time_period=period, series_type="close")
            assert "Technical Analysis: SMA" in result
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_calculate_ema(self, mock_yf):
        """Test calculate_ema endpoint."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_yf_data("GOOGL")
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.calculate_ema("GOOGL", time_period=12, series_type="close")
        
        assert "Meta Data" in result
        assert "Technical Analysis: EMA" in result
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_calculate_rsi(self, mock_yf):
        """Test calculate_rsi endpoint."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_yf_data("AMZN")
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.calculate_rsi("AMZN", time_period=14, series_type="close")
        
        assert "Meta Data" in result
        assert "Technical Analysis: RSI" in result
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_time_series_intraday(self, mock_yf):
        """Test time_series_intraday endpoint."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_yf_data("NVDA", days=50)
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.time_series_intraday("NVDA", interval="5min")
        
        # Should return data or error (yfinance may not support intraday for all intervals)
        assert "Meta Data" in result or "Error Message" in result


# ---------- get_engine Tests ----------

class TestGetEngine:
    """Tests for get_engine singleton."""
    
    def test_get_engine_returns_instance(self):
        """Test get_engine returns AlphaSimEngine instance."""
        engine = get_engine()
        assert isinstance(engine, AlphaSimEngine)
    
    def test_get_engine_singleton(self):
        """Test get_engine returns same instance."""
        engine1 = get_engine()
        engine2 = get_engine()
        assert engine1 is engine2


# ---------- Series Type Tests ----------

class TestSeriesTypes:
    """Tests for different series types."""
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_sma_open_series(self, mock_yf):
        """Test SMA with open price series."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_yf_data("AAPL")
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.calculate_sma("AAPL", time_period=10, series_type="open")
        
        assert "Technical Analysis: SMA" in result
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_sma_high_series(self, mock_yf):
        """Test SMA with high price series."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_yf_data("AAPL")
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.calculate_sma("AAPL", time_period=10, series_type="high")
        
        assert "Technical Analysis: SMA" in result
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_sma_low_series(self, mock_yf):
        """Test SMA with low price series."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_yf_data("AAPL")
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.calculate_sma("AAPL", time_period=10, series_type="low")
        
        assert "Technical Analysis: SMA" in result


# ---------- Edge Cases ----------

class TestEngineEdgeCases:
    """Tests for engine edge cases."""
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_empty_data(self, mock_yf):
        """Test handling of empty data."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.time_series_daily("EMPTY")
        
        # Should handle gracefully
        assert isinstance(result, dict)
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_yfinance_exception(self, mock_yf):
        """Test handling of yfinance exception."""
        mock_yf.Ticker.side_effect = Exception("Network error")
        
        engine = AlphaSimEngine()
        result = engine.time_series_daily("ERROR")
        
        # Should return error response
        assert "Error" in result
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_special_characters_symbol(self, mock_yf):
        """Test handling of symbol with special characters."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_yf_data("BRK.B")
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.time_series_daily("BRK.B")
        
        assert isinstance(result, dict)
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_sma_period_larger_than_data(self, mock_yf):
        """Test SMA with period larger than available data."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_yf_data("AAPL", days=10)
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.calculate_sma("AAPL", time_period=100, series_type="close")
        
        # Should handle gracefully - may have all NaN or partial data
        assert isinstance(result, dict)


# ---------- Response Format Tests ----------

class TestResponseFormats:
    """Tests for response format compliance."""
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_time_series_daily_format(self, mock_yf):
        """Test TIME_SERIES_DAILY response matches Alpha Vantage format."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_yf_data("AAPL")
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.time_series_daily("AAPL")
        
        # Check top-level keys
        assert "Meta Data" in result
        assert "Time Series (Daily)" in result
        
        # Check Meta Data fields
        meta = result["Meta Data"]
        assert "1. Information" in meta
        assert "2. Symbol" in meta
        
        # Check time series entry format
        ts = result["Time Series (Daily)"]
        if ts:
            first_date = list(ts.keys())[0]
            entry = ts[first_date]
            
            assert "1. open" in entry
            assert "2. high" in entry
            assert "3. low" in entry
            assert "4. close" in entry
            assert "5. volume" in entry
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_sma_format(self, mock_yf):
        """Test SMA response matches Alpha Vantage format."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = create_mock_yf_data("AAPL")
        mock_yf.Ticker.return_value = mock_ticker
        
        engine = AlphaSimEngine()
        result = engine.calculate_sma("AAPL", time_period=10)
        
        # Check top-level keys
        assert "Meta Data" in result
        assert "Technical Analysis: SMA" in result
        
        # Check technical analysis entry format
        ta = result["Technical Analysis: SMA"]
        if ta:
            first_date = list(ta.keys())[0]
            entry = ta[first_date]
            
            assert "SMA" in entry
