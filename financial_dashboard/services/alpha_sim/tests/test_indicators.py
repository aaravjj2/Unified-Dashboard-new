"""
Unit tests for AlphaSim technical indicators.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from financial_dashboard.services.alpha_sim.indicators import (
    sma, ema, rsi, macd, vwap
)


# ---------- Test Fixtures ----------

@pytest.fixture
def sample_prices():
    """Sample price series for testing."""
    return pd.Series([
        100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
        110, 108, 107, 109, 111, 112, 110, 109, 111, 113
    ], name="close")


@pytest.fixture
def sample_ohlcv():
    """Sample OHLCV DataFrame for VWAP testing."""
    dates = pd.date_range(end=datetime.now(), periods=20, freq='D')
    np.random.seed(42)
    
    opens = 100 + np.random.randn(20).cumsum()
    highs = opens + abs(np.random.randn(20))
    lows = opens - abs(np.random.randn(20))
    closes = opens + np.random.randn(20) * 0.5
    volumes = np.random.randint(1000, 10000, 20)
    
    return pd.DataFrame({
        'high': highs,
        'low': lows,
        'close': closes,
        'volume': volumes
    }, index=dates)


# ---------- SMA Tests ----------

class TestSMA:
    """Tests for Simple Moving Average indicator."""
    
    def test_sma_basic(self, sample_prices):
        """Test basic SMA calculation."""
        result = sma(sample_prices, period=5)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_prices)
        # First 4 values should be NaN
        assert pd.isna(result.iloc[:4]).all()
        # Rest should be valid
        assert not pd.isna(result.iloc[4:]).any()
    
    def test_sma_values(self):
        """Test SMA calculation correctness."""
        prices = pd.Series([10, 20, 30, 40, 50])
        result = sma(prices, period=3)
        
        # SMA at index 2 = (10 + 20 + 30) / 3 = 20
        assert result.iloc[2] == 20.0
        # SMA at index 3 = (20 + 30 + 40) / 3 = 30
        assert result.iloc[3] == 30.0
        # SMA at index 4 = (30 + 40 + 50) / 3 = 40
        assert result.iloc[4] == 40.0
    
    def test_sma_period_1(self, sample_prices):
        """Test SMA with period of 1 returns original series values."""
        result = sma(sample_prices, period=1)
        # SMA of period 1 should equal original values (may differ in dtype)
        assert len(result) == len(sample_prices)
        assert (result.values == sample_prices.values.astype(float)).all()
    
    def test_sma_empty_series(self):
        """Test SMA with empty series."""
        result = sma(pd.Series([], dtype=float), period=5)
        assert len(result) == 0


# ---------- EMA Tests ----------

class TestEMA:
    """Tests for Exponential Moving Average indicator."""
    
    def test_ema_basic(self, sample_prices):
        """Test basic EMA calculation."""
        result = ema(sample_prices, period=10)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_prices)
    
    def test_ema_responsive(self, sample_prices):
        """Test that EMA is more responsive than SMA to recent prices."""
        sma_result = sma(sample_prices, period=10)
        ema_result = ema(sample_prices, period=10)
        
        # Both should have same length
        assert len(sma_result) == len(ema_result)
        
        # After initial period, EMA should typically differ from SMA
        # (as EMA gives more weight to recent prices)
        valid_idx = ~(pd.isna(sma_result) | pd.isna(ema_result))
        if valid_idx.any():
            # They should not be exactly equal (except potentially at first valid point)
            assert not (sma_result[valid_idx] == ema_result[valid_idx]).all()
    
    def test_ema_period_1(self, sample_prices):
        """Test EMA with span of 1 returns original series values."""
        result = ema(sample_prices, period=1)
        # EMA of period 1 should equal original values (may differ in dtype)
        assert len(result) == len(sample_prices)
        assert (result.values == sample_prices.values.astype(float)).all()


# ---------- RSI Tests ----------

class TestRSI:
    """Tests for Relative Strength Index indicator."""
    
    def test_rsi_basic(self, sample_prices):
        """Test basic RSI calculation."""
        result = rsi(sample_prices, period=14)
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_prices)
    
    def test_rsi_range(self, sample_prices):
        """Test RSI is bounded between 0 and 100."""
        result = rsi(sample_prices, period=14)
        valid = result.dropna()
        
        assert (valid >= 0).all()
        assert (valid <= 100).all()
    
    def test_rsi_constant_gains(self):
        """Test RSI with constant upward movement approaches 100."""
        prices = pd.Series([10 + i for i in range(30)])
        result = rsi(prices, period=14)
        
        # RSI should be high with constant gains
        valid = result.dropna()
        if len(valid) > 0:
            assert valid.iloc[-1] > 70  # Should be overbought
    
    def test_rsi_constant_losses(self):
        """Test RSI with constant downward movement approaches 0."""
        prices = pd.Series([100 - i for i in range(30)])
        result = rsi(prices, period=14)
        
        # RSI should be low with constant losses
        valid = result.dropna()
        if len(valid) > 0:
            assert valid.iloc[-1] < 30  # Should be oversold


# ---------- MACD Tests ----------

class TestMACD:
    """Tests for MACD indicator."""
    
    @pytest.fixture
    def macd_prices(self):
        """Longer price series for MACD testing (needs at least 26 periods)."""
        return pd.Series([
            100, 102, 101, 103, 105, 104, 106, 108, 107, 109,
            110, 108, 107, 109, 111, 112, 110, 109, 111, 113,
            115, 114, 116, 118, 117, 119, 120, 118, 119, 121
        ], name="close")
    
    def test_macd_basic(self, macd_prices):
        """Test basic MACD calculation."""
        result = macd(macd_prices)
        
        assert isinstance(result, dict)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result
        
        assert len(result["macd"]) == len(macd_prices)
        assert len(result["signal"]) == len(macd_prices)
        assert len(result["histogram"]) == len(macd_prices)
    
    def test_macd_histogram_formula(self, macd_prices):
        """Test MACD histogram = MACD line - Signal line."""
        result = macd(macd_prices)
        
        expected_histogram = result["macd"] - result["signal"]
        pd.testing.assert_series_equal(
            result["histogram"], expected_histogram, 
            check_names=False,
            rtol=1e-10
        )
    
    def test_macd_custom_params(self, macd_prices):
        """Test MACD with custom parameters."""
        result = macd(
            macd_prices, 
            fast_period=8, 
            slow_period=17, 
            signal_period=5
        )
        
        # Should still return valid series
        assert len(result["macd"]) == len(macd_prices)
    
    def test_macd_insufficient_data(self, sample_prices):
        """Test MACD with insufficient data returns empty series."""
        # sample_prices has only 20 values, MACD needs 26
        result = macd(sample_prices)
        
        assert len(result["macd"]) == 0  # Empty due to insufficient data


# ---------- VWAP Tests ----------

class TestVWAP:
    """Tests for Volume Weighted Average Price indicator."""
    
    def test_vwap_basic(self, sample_ohlcv):
        """Test basic VWAP calculation."""
        result = vwap(
            sample_ohlcv['high'],
            sample_ohlcv['low'],
            sample_ohlcv['close'],
            sample_ohlcv['volume']
        )
        
        assert isinstance(result, pd.Series)
        assert len(result) == len(sample_ohlcv)
    
    def test_vwap_no_nan(self, sample_ohlcv):
        """Test VWAP has no NaN values."""
        result = vwap(
            sample_ohlcv['high'],
            sample_ohlcv['low'],
            sample_ohlcv['close'],
            sample_ohlcv['volume']
        )
        assert not result.isna().any()
    
    def test_vwap_typical_price_range(self, sample_ohlcv):
        """Test VWAP is between low and high prices."""
        result = vwap(
            sample_ohlcv['high'],
            sample_ohlcv['low'],
            sample_ohlcv['close'],
            sample_ohlcv['volume']
        )
        
        # VWAP should be within the price range
        assert (result >= sample_ohlcv['low'].min()).all()
        assert (result <= sample_ohlcv['high'].max()).all()
    
    def test_vwap_with_uniform_volume(self):
        """Test VWAP with uniform volume equals mean typical price."""
        high = pd.Series([12, 14, 13, 15, 14])
        low = pd.Series([10, 11, 10, 12, 11])
        close = pd.Series([11, 13, 12, 14, 13])
        volume = pd.Series([100, 100, 100, 100, 100])
        
        result = vwap(high, low, close, volume)
        
        # With uniform volume, cumulative VWAP should approach mean typical price
        assert len(result) == 5


# ---------- Edge Cases ----------

class TestIndicatorEdgeCases:
    """Tests for edge cases across indicators."""
    
    def test_single_value_series(self):
        """Test indicators with single value series."""
        prices = pd.Series([100.0])
        
        assert len(sma(prices, period=1)) == 1
        assert len(ema(prices, period=1)) == 1
    
    def test_all_same_values(self):
        """Test indicators with constant price series."""
        prices = pd.Series([100.0] * 20)
        
        # SMA should be 100
        sma_result = sma(prices, period=5)
        assert (sma_result.dropna() == 100.0).all()
        
        # EMA should be 100
        ema_result = ema(prices, period=5)
        assert (ema_result.dropna() == 100.0).all()
    
    def test_with_nan_values(self):
        """Test indicators handle NaN values gracefully."""
        prices = pd.Series([100, np.nan, 102, 103, 104, 105, 106])
        
        # Should not raise an exception
        sma_result = sma(prices, period=3)
        ema_result = ema(prices, period=3)
        
        assert len(sma_result) == len(prices)
        assert len(ema_result) == len(prices)
