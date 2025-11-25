"""
Market Forecast Property Tests
Tests invariants and schema validation with random inputs
"""

import pytest
from hypothesis import given, strategies as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from services.forecast_adapter import ForecastAdapter

# Property testing strategies
ticker_strategy = st.sampled_from(['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA'])
horizon_strategy = st.integers(min_value=1, max_value=365)
confidence_strategy = st.floats(min_value=0.8, max_value=0.99)

class TestForecastProperties:
    """Property-based tests for forecast adapter"""
    
    @given(ticker=ticker_strategy, horizon=horizon_strategy, confidence=confidence_strategy)
    def test_deterministic_always_succeeds(self, ticker, horizon, confidence):
        """Property: Deterministic mode never fails"""
        adapter = ForecastAdapter(bento_url='http://localhost:5001', deterministic=True)
        
        result = adapter.run_forecast(
            ticker=ticker,
            horizon=horizon,
            confidence=confidence,
            model='default',
            forecast_id=f'test_{ticker}_{horizon}'
        )
        
        assert 'ticker' in result
        assert result['ticker'] == ticker
        
    @given(ticker=ticker_strategy, horizon=horizon_strategy)
    def test_forecast_series_monotonic_dates(self, ticker, horizon):
        """Property: Forecast dates are in chronological order"""
        adapter = ForecastAdapter(bento_url='http://localhost:5001', deterministic=True)
        
        result = adapter.run_forecast(
            ticker=ticker,
            horizon=horizon,
            confidence=0.95,
            model='default',
            forecast_id=f'test_{ticker}'
        )
        
        series = result.get('forecast_series', [])
        
        if len(series) > 1:
            dates = [s['date'] for s in series]
            assert dates == sorted(dates), "Dates must be chronological"
            
    @given(ticker=ticker_strategy)
    def test_confidence_bounds_valid(self, ticker):
        """Property: Lower bound < price < upper bound"""
        adapter = ForecastAdapter(bento_url='http://localhost:5001', deterministic=True)
        
        result = adapter.run_forecast(
            ticker=ticker,
            horizon=30,
            confidence=0.95,
            model='default',
            forecast_id=f'test_{ticker}'
        )
        
        series = result.get('forecast_series', [])
        
        for point in series:
            assert point['lower'] <= point['price'] <= point['upper'], \
                f"Confidence bounds violated: {point['lower']} <= {point['price']} <= {point['upper']}"
                
    @given(ticker=ticker_strategy)
    def test_expected_return_bounded(self, ticker):
        """Property: Expected return is reasonable (-1.0 to 2.0)"""
        adapter = ForecastAdapter(bento_url='http://localhost:5001', deterministic=True)
        
        result = adapter.run_forecast(
            ticker=ticker,
            horizon=30,
            confidence=0.95,
            model='default',
            forecast_id=f'test_{ticker}'
        )
        
        expected_return = result.get('expected_return', 0)
        
        assert -1.0 <= expected_return <= 2.0, \
            f"Expected return out of bounds: {expected_return}"

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--hypothesis-show-statistics'])
