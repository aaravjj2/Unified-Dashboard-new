"""
Unit tests for AlphaSim schema module.
"""
import pytest
import pandas as pd
from datetime import datetime

from financial_dashboard.services.alpha_sim.schema import (
    build_meta_data,
    build_time_series_daily,
    build_sma_response,
    build_error_response,
    build_rate_limit_response
)


# ---------- build_meta_data Tests ----------

class TestBuildMetaData:
    """Tests for build_meta_data function."""
    
    def test_build_meta_data_basic(self):
        """Test basic meta data building."""
        meta = build_meta_data(
            information="Daily Prices (AlphaSim)",
            symbol="AAPL"
        )
        
        assert "1. Information" in meta
        assert "2. Symbol" in meta
        assert meta["2. Symbol"] == "AAPL"
    
    def test_build_meta_data_with_output_size(self):
        """Test meta data with output_size."""
        meta = build_meta_data(
            information="Daily Prices",
            symbol="MSFT",
            output_size="full"
        )
        
        assert "2. Symbol" in meta
        assert meta["2. Symbol"] == "MSFT"
        assert meta["4. Output Size"] == "full"
    
    def test_build_meta_data_with_extra(self):
        """Test meta data with extra parameters."""
        meta = build_meta_data(
            information="SMA",
            symbol="GOOGL",
            extra={"Indicator": "SMA", "Time Period": 20}
        )
        
        assert "2. Symbol" in meta
        assert meta["2. Symbol"] == "GOOGL"


# ---------- build_time_series_daily Tests ----------

class TestBuildTimeSeriesDaily:
    """Tests for build_time_series_daily function."""
    
    def test_build_time_series_daily_basic(self):
        """Test basic time series daily response."""
        df = pd.DataFrame({
            "Open": [100.0],
            "High": [105.0],
            "Low": [99.0],
            "Close": [104.0],
            "Volume": [1000000]
        }, index=pd.to_datetime(["2024-01-15"]))
        
        response = build_time_series_daily("AAPL", df)
        
        assert "Meta Data" in response
        assert "Time Series (Daily)" in response
        assert "2024-01-15" in response["Time Series (Daily)"]
    
    def test_build_time_series_daily_format(self):
        """Test time series daily has correct field format."""
        df = pd.DataFrame({
            "Open": [100.0],
            "High": [105.0],
            "Low": [99.0],
            "Close": [104.0],
            "Volume": [1000000]
        }, index=pd.to_datetime(["2024-01-15"]))
        
        response = build_time_series_daily("AAPL", df)
        entry = response["Time Series (Daily)"]["2024-01-15"]
        
        # Alpha Vantage format uses numbered prefixes
        assert "1. open" in entry
        assert "2. high" in entry
        assert "3. low" in entry
        assert "4. close" in entry
        assert "5. volume" in entry
    
    def test_build_time_series_daily_multiple_dates(self):
        """Test time series daily with multiple dates."""
        df = pd.DataFrame({
            "Open": [100, 99, 98],
            "High": [105, 101, 100],
            "Low": [99, 98, 97],
            "Close": [104, 100, 99],
            "Volume": [1000000, 900000, 800000]
        }, index=pd.to_datetime(["2024-01-15", "2024-01-14", "2024-01-13"]))
        
        response = build_time_series_daily("AAPL", df)
        
        assert len(response["Time Series (Daily)"]) == 3
    
    def test_build_time_series_daily_empty(self):
        """Test time series daily with empty data."""
        response = build_time_series_daily("AAPL", pd.DataFrame())
        
        assert "Meta Data" in response
        assert "Time Series (Daily)" in response
        assert len(response["Time Series (Daily)"]) == 0


# ---------- build_sma_response Tests ----------

class TestBuildSMAResponse:
    """Tests for build_sma_response function."""
    
    def test_build_sma_response_basic(self):
        """Test basic SMA response building."""
        sma_series = pd.Series(
            [102.5, 101.0, 100.0],
            index=pd.to_datetime(["2024-01-15", "2024-01-14", "2024-01-13"])
        )
        
        response = build_sma_response(
            symbol="AAPL",
            sma_series=sma_series,
            time_period=10,
            series_type="close"
        )
        
        assert "Meta Data" in response
        assert "Technical Analysis: SMA" in response
    
    def test_build_sma_response_format(self):
        """Test SMA response has correct format."""
        sma_series = pd.Series(
            [102.5],
            index=pd.to_datetime(["2024-01-15"])
        )
        
        response = build_sma_response(
            symbol="AAPL",
            sma_series=sma_series,
            time_period=10,
            series_type="close"
        )
        
        entry = response["Technical Analysis: SMA"]["2024-01-15"]
        assert "SMA" in entry
    
    def test_build_sma_response_multiple_dates(self):
        """Test SMA response with multiple dates."""
        sma_series = pd.Series(
            [102.5, 101.0, 100.0, 99.5, 99.0],
            index=pd.to_datetime(["2024-01-15", "2024-01-14", "2024-01-13", "2024-01-12", "2024-01-11"])
        )
        
        response = build_sma_response(
            symbol="MSFT",
            sma_series=sma_series,
            time_period=20,
            series_type="close"
        )
        
        assert len(response["Technical Analysis: SMA"]) == 5


# ---------- build_error_response Tests ----------

class TestBuildErrorResponse:
    """Tests for build_error_response function."""
    
    def test_build_error_response_basic(self):
        """Test basic error response."""
        response = build_error_response("Something went wrong")
        
        assert "Error" in response
        assert response["Error"] == "Something went wrong"
    
    def test_build_error_response_with_note(self):
        """Test error response with note."""
        response = build_error_response(
            "Invalid function",
            note="Supported functions: TIME_SERIES_DAILY, SMA"
        )
        
        assert "Error" in response
        assert "Note" in response
        assert "Supported functions" in response["Note"]


# ---------- build_rate_limit_response Tests ----------

class TestBuildRateLimitResponse:
    """Tests for build_rate_limit_response function."""
    
    def test_build_rate_limit_response_basic(self):
        """Test basic rate limit response."""
        response = build_rate_limit_response(retry_after_seconds=60)
        
        assert "Note" in response
        assert "60" in response["Note"]
    
    def test_build_rate_limit_response_contains_retry(self):
        """Test rate limit response contains retry information."""
        response = build_rate_limit_response(retry_after_seconds=120)
        
        # Should contain information about retry
        assert "Note" in response
        assert "120" in response["Note"]


# ---------- Integration Tests ----------

class TestSchemaIntegration:
    """Integration tests for schema module."""
    
    def test_full_time_series_response(self):
        """Test building a complete time series response."""
        # Simulate real-world data
        dates = pd.to_datetime([f"2024-01-{15-i:02d}" for i in range(5)])
        df = pd.DataFrame({
            "Open": [100.0 + i for i in range(5)],
            "High": [105.0 + i for i in range(5)],
            "Low": [99.0 + i for i in range(5)],
            "Close": [104.0 + i for i in range(5)],
            "Volume": [1000000 + i * 100000 for i in range(5)]
        }, index=dates)
        
        response = build_time_series_daily("AAPL", df)
        
        # Verify structure matches Alpha Vantage format
        assert "Meta Data" in response
        assert "Time Series (Daily)" in response
        
        meta = response["Meta Data"]
        assert "1. Information" in meta
        assert "2. Symbol" in meta
        
        ts = response["Time Series (Daily)"]
        assert len(ts) == 5
        
        # Check first entry
        first_date = list(ts.keys())[0]
        first_entry = ts[first_date]
        assert "1. open" in first_entry
        assert "2. high" in first_entry
        assert "3. low" in first_entry
        assert "4. close" in first_entry
        assert "5. volume" in first_entry
    
    def test_full_sma_response(self):
        """Test building a complete SMA response."""
        dates = pd.to_datetime([f"2024-01-{15-i:02d}" for i in range(10)])
        sma_series = pd.Series(
            [100.0 + i * 0.5 for i in range(10)],
            index=dates
        )
        
        response = build_sma_response(
            symbol="MSFT",
            sma_series=sma_series,
            time_period=14,
            series_type="close"
        )
        
        # Verify structure
        assert "Meta Data" in response
        assert "Technical Analysis: SMA" in response
        
        ta = response["Technical Analysis: SMA"]
        assert len(ta) == 10
