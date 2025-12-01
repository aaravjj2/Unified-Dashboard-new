"""
RED Phase Unit Tests for Volatility Lab Computation Library

All tests are designed to fail initially because volatility_lib.py doesn't exist yet.
Tests verify:
- Log returns calculation
- Rolling volatility
- Annualized volatility
- Realized volatility
- Edge cases (NaN, short series, insufficient history)
"""

import pytest
import numpy as np
import pandas as pd
from financial_dashboard.tabs.volatility_lib import (
    compute_log_returns,
    rolling_volatility,
    realized_vol,
    annualized_vol
)


class TestLogReturns:
    """Test log returns calculation"""
    
    def test_compute_log_returns_happy_path(self):
        """Test log returns on simple price series"""
        prices = pd.Series([100, 110, 105, 115], index=pd.date_range('2024-01-01', periods=4))
        returns = compute_log_returns(prices)
        
        # Expected: ln(110/100), ln(105/110), ln(115/105)
        expected = np.array([np.log(1.1), np.log(105/110), np.log(115/105)])
        
        assert len(returns) == 3, "Returns should have n-1 elements"
        np.testing.assert_array_almost_equal(returns.values, expected, decimal=6)
    
    def test_compute_log_returns_with_nan(self):
        """Test log returns handling NaN values"""
        prices = pd.Series([100, np.nan, 105, 115])
        returns = compute_log_returns(prices)
        
        # Should handle NaN gracefully (drop or forward-fill)
        assert not returns.isna().all(), "Should handle NaN values"
    
    def test_compute_log_returns_single_value(self):
        """Test log returns with single price (edge case)"""
        prices = pd.Series([100])
        returns = compute_log_returns(prices)
        
        assert len(returns) == 0, "Single value should produce empty returns"


class TestRollingVolatility:
    """Test rolling volatility calculation"""
    
    def test_rolling_volatility_happy_path(self):
        """Test rolling vol on known data"""
        # Create known returns
        returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.015, -0.015, 0.01, -0.01])
        window = 4
        
        vol = rolling_volatility(returns, window=window, annualize=False)
        
        # First 3 values should be NaN (window=4)
        assert vol.iloc[:window-1].isna().all(), f"First {window-1} values should be NaN"
        
        # 4th value onwards should have vol
        assert not vol.iloc[window-1:].isna().any(), "Should have vol values after window"
        
        # Verify calculation manually for 4th value
        first_window = returns.iloc[:window]
        expected_vol = first_window.std(ddof=1)
        np.testing.assert_almost_equal(vol.iloc[window-1], expected_vol, decimal=6)
    
    def test_rolling_volatility_annualized(self):
        """Test annualized rolling vol"""
        returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.015, -0.015, 0.01, -0.01])
        window = 4
        periods_per_year = 252
        
        vol = rolling_volatility(returns, window=window, annualize=True, periods_per_year=periods_per_year)
        vol_unannnualized = rolling_volatility(returns, window=window, annualize=False)
        
        # Annualized should be unannnualized * sqrt(252)
        expected = vol_unannnualized * np.sqrt(periods_per_year)
        pd.testing.assert_series_equal(vol, expected, check_names=False)
    
    def test_rolling_volatility_insufficient_data(self):
        """Test rolling vol with data shorter than window"""
        returns = pd.Series([0.01, 0.02])
        window = 10
        
        vol = rolling_volatility(returns, window=window, annualize=False)
        
        # All values should be NaN
        assert vol.isna().all(), "Should return all NaN when data < window"
    
    def test_rolling_volatility_edge_window_sizes(self):
        """Test edge cases for window size"""
        returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.015])
        
        # Window = 1 should give zero vol
        vol_1 = rolling_volatility(returns, window=1, annualize=False)
        assert (vol_1.fillna(0) == 0).all(), "Window=1 should give zero vol"
        
        # Window = 2 (minimum meaningful)
        vol_2 = rolling_volatility(returns, window=2, annualize=False)
        assert not vol_2.iloc[1:].isna().all(), "Window=2 should produce vol"


class TestRealizedVolatility:
    """Test realized volatility calculation"""
    
    def test_realized_vol_happy_path(self):
        """Test realized vol over full period"""
        returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.015, -0.015, 0.01, -0.01],
                           index=pd.date_range('2024-01-01', periods=8))
        
        vol = realized_vol(returns, annualize=False)
        
        # Should match pandas std
        expected = returns.std(ddof=1)
        np.testing.assert_almost_equal(vol, expected, decimal=6)
    
    def test_realized_vol_annualized(self):
        """Test annualized realized vol"""
        returns = pd.Series([0.01, -0.01, 0.02, -0.02, 0.015, -0.015, 0.01, -0.01],
                           index=pd.date_range('2024-01-01', periods=8))
        periods_per_year = 252
        
        vol = realized_vol(returns, annualize=True, periods_per_year=periods_per_year)
        expected = returns.std(ddof=1) * np.sqrt(periods_per_year)
        
        np.testing.assert_almost_equal(vol, expected, decimal=6)
    
    def test_realized_vol_with_date_range(self):
        """Test realized vol over specific date range"""
        dates = pd.date_range('2024-01-01', periods=10)
        returns = pd.Series(np.random.randn(10) * 0.01, index=dates)
        
        # Calculate vol for subset
        start = '2024-01-03'
        end = '2024-01-07'
        
        vol = realized_vol(returns, start=start, end=end, annualize=False)
        
        # Should match std of subset
        subset = returns.loc[start:end]
        expected = subset.std(ddof=1)
        
        np.testing.assert_almost_equal(vol, expected, decimal=6)
    
    def test_realized_vol_empty_series(self):
        """Test realized vol with empty series"""
        returns = pd.Series([], dtype=float)
        
        vol = realized_vol(returns, annualize=False)
        
        assert np.isnan(vol) or vol == 0, "Empty series should return NaN or 0"
    
    def test_realized_vol_single_value(self):
        """Test realized vol with single return"""
        returns = pd.Series([0.01])
        
        vol = realized_vol(returns, annualize=False)
        
        # Std of single value with ddof=1 is NaN
        assert np.isnan(vol), "Single value should return NaN"


class TestAnnualizedVolatility:
    """Test annualized volatility helper"""
    
    def test_annualized_vol_daily_to_annual(self):
        """Test daily vol to annualized"""
        daily_vol = 0.02  # 2% daily vol
        
        annual_vol = annualized_vol(daily_vol, periods_per_year=252)
        expected = daily_vol * np.sqrt(252)
        
        np.testing.assert_almost_equal(annual_vol, expected, decimal=6)
    
    def test_annualized_vol_hourly_to_annual(self):
        """Test hourly vol to annualized"""
        hourly_vol = 0.005
        trading_hours_per_year = 252 * 6.5  # ~1638 hours
        
        annual_vol = annualized_vol(hourly_vol, periods_per_year=trading_hours_per_year)
        expected = hourly_vol * np.sqrt(trading_hours_per_year)
        
        np.testing.assert_almost_equal(annual_vol, expected, decimal=6)
    
    def test_annualized_vol_series(self):
        """Test annualized vol on pandas Series"""
        vols = pd.Series([0.01, 0.02, 0.015, 0.025])
        
        annual_vols = annualized_vol(vols, periods_per_year=252)
        expected = vols * np.sqrt(252)
        
        pd.testing.assert_series_equal(annual_vols, expected, check_names=False)


class TestEdgeCases:
    """Test edge cases and error handling"""
    
    def test_all_nan_returns(self):
        """Test handling of all-NaN returns"""
        returns = pd.Series([np.nan, np.nan, np.nan])
        
        vol = rolling_volatility(returns, window=2, annualize=False)
        assert vol.isna().all(), "All NaN returns should produce all NaN vol"
        
        realized = realized_vol(returns, annualize=False)
        assert np.isnan(realized), "All NaN returns should produce NaN realized vol"
    
    def test_constant_prices(self):
        """Test handling of constant prices (zero returns)"""
        prices = pd.Series([100, 100, 100, 100])
        returns = compute_log_returns(prices)
        
        vol = rolling_volatility(returns, window=2, annualize=False)
        # Zero vol expected
        assert (vol.fillna(0) == 0).all(), "Constant prices should give zero vol"
    
    def test_extreme_values(self):
        """Test handling of extreme price movements"""
        prices = pd.Series([100, 200, 50, 300])  # Extreme jumps
        returns = compute_log_returns(prices)
        
        # Should still compute without error
        vol = rolling_volatility(returns, window=2, annualize=False)
        assert not vol.iloc[1:].isna().all(), "Should handle extreme values"
        assert vol.iloc[1:].max() > 0, "Should show high vol for extreme moves"
    
    def test_2d_array_input_error(self):
        """Test that 2D array inputs are handled properly (should extract single column or error)"""
        import pandas as pd
        import numpy as np
        
        # Create a 2D DataFrame (common mistake)
        df_2d = pd.DataFrame({
            'price': [100, 101, 102, 103],
            'return': [0, 0.01, 0.01, 0.01]
        })
        
        # Attempting to pass DataFrame instead of Series should fail
        # (or be handled by extracting single column)
        try:
            # This should error if function expects Series
            returns = compute_log_returns(df_2d)
            # If it doesn't error, it should return a Series
            assert isinstance(returns, pd.Series) or isinstance(returns, pd.DataFrame)
        except (TypeError, ValueError, AttributeError) as e:
            # Expected error - function properly rejects 2D input
            assert "1-dimensional" in str(e) or "Series" in str(e) or "operands" in str(e)
        
        # Correct way: extract single column
        prices_1d = df_2d['price']
        returns = compute_log_returns(prices_1d)
        assert isinstance(returns, pd.Series)
        assert returns.ndim == 1
