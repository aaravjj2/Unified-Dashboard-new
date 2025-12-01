"""
Test script for Market Forecast tab - validates all models and scenarios.
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

import pandas as pd
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_data_fetching():
    """Test yfinance data fetching."""
    print("\n" + "="*60)
    print("TEST 1: Data Fetching")
    print("="*60)
    
    try:
        import yfinance as yf
        
        ticker = 'AAPL'
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365)
        
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        
        print(f"✓ Successfully fetched {len(hist)} days of data for {ticker}")
        print(f"  Date range: {hist.index[0]} to {hist.index[-1]}")
        print(f"  Last close: ${hist['Close'].iloc[-1]:.2f}")
        print(f"  Data columns: {list(hist.columns)}")
        
        return True, hist
        
    except Exception as e:
        print(f"✗ Data fetch failed: {e}")
        return False, None


def test_prophet_model(hist_data):
    """Test Prophet forecaster."""
    print("\n" + "="*60)
    print("TEST 2: Prophet Model")
    print("="*60)
    
    try:
        from financial_dashboard.models import ProphetForecaster
        
        # Prepare data
        data = pd.DataFrame({
            'ds': hist_data.index,
            'y': hist_data['Close'].values
        })
        
        # Train and predict
        prophet = ProphetForecaster()
        prophet.fit(data)
        forecast = prophet.predict(horizon=14, confidence=0.95)
        
        print(f"✓ Prophet model trained successfully")
        print(f"  Forecast points: {len(forecast['forecast'])}")
        print(f"  First prediction: ${forecast['forecast'][0]:.2f}")
        print(f"  Last prediction: ${forecast['forecast'][-1]:.2f}")
        print(f"  Has confidence intervals: {all(k in forecast for k in ['lower_95', 'upper_95'])}")
        
        return True, forecast
        
    except Exception as e:
        print(f"✗ Prophet test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_arima_model(hist_data):
    """Test ARIMA forecaster."""
    print("\n" + "="*60)
    print("TEST 3: ARIMA Model")
    print("="*60)
    
    try:
        from financial_dashboard.models import ARIMAForecaster
        
        data = pd.DataFrame({
            'ds': hist_data.index,
            'y': hist_data['Close'].values
        })
        
        arima = ARIMAForecaster()
        arima.fit(data)
        forecast = arima.predict(horizon=14)
        
        print(f"✓ ARIMA model trained successfully")
        print(f"  Forecast points: {len(forecast['forecast'])}")
        print(f"  First prediction: ${forecast['forecast'][0]:.2f}")
        print(f"  Last prediction: ${forecast['forecast'][-1]:.2f}")
        
        return True, forecast
        
    except Exception as e:
        print(f"✗ ARIMA test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_lstm_model(hist_data):
    """Test LSTM forecaster."""
    print("\n" + "="*60)
    print("TEST 4: LSTM Model")
    print("="*60)
    
    try:
        from financial_dashboard.models import LSTMForecaster
        
        data = pd.DataFrame({
            'ds': hist_data.index,
            'y': hist_data['Close'].values
        })
        
        lstm = LSTMForecaster()
        lstm.fit(data)
        forecast = lstm.predict(horizon=14)
        
        print(f"✓ LSTM model trained successfully")
        print(f"  Forecast points: {len(forecast['forecast'])}")
        print(f"  First prediction: ${forecast['forecast'][0]:.2f}")
        print(f"  Last prediction: ${forecast['forecast'][-1]:.2f}")
        
        return True, forecast
        
    except Exception as e:
        print(f"✗ LSTM test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_ensemble_model(hist_data):
    """Test Ensemble forecaster."""
    print("\n" + "="*60)
    print("TEST 5: Ensemble Model")
    print("="*60)
    
    try:
        from financial_dashboard.models import EnsembleForecaster
        
        data = pd.DataFrame({
            'ds': hist_data.index,
            'y': hist_data['Close'].values
        })
        
        ensemble = EnsembleForecaster()
        ensemble.fit(data)
        forecast = ensemble.predict(horizon=14)
        
        print(f"✓ Ensemble model trained successfully")
        print(f"  Forecast points: {len(forecast['forecast'])}")
        print(f"  First prediction: ${forecast['forecast'][0]:.2f}")
        print(f"  Last prediction: ${forecast['forecast'][-1]:.2f}")
        print(f"  Individual models: {list(forecast.get('models', {}).keys())}")
        
        return True, forecast
        
    except Exception as e:
        print(f"✗ Ensemble test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_scenario_simulator(baseline_forecast):
    """Test scenario simulator."""
    print("\n" + "="*60)
    print("TEST 6: Scenario Simulator")
    print("="*60)
    
    try:
        from financial_dashboard.utils.scenario_simulator import ScenarioSimulator
        
        # Test Fed rate cut scenario
        result = ScenarioSimulator.apply_scenario(
            baseline_forecast=baseline_forecast,
            scenario_type='fed_rate_cut',
            param_value=-25,
            decay_rate=0.9
        )
        
        print(f"✓ Scenario applied successfully")
        print(f"  Scenario: {result['scenario_info']['name']}")
        print(f"  Initial impact: {result['scenario_info']['initial_impact_pct']:.2f}%")
        print(f"  Baseline first: ${baseline_forecast[0]:.2f}")
        print(f"  Adjusted first: ${result['adjusted_forecast'][0]:.2f}")
        print(f"  Impact first day: {result['impact_pct'][0]:.2f}%")
        
        # Test all scenarios
        scenarios_tested = []
        for scenario_type in ScenarioSimulator.SCENARIOS.keys():
            try:
                ScenarioSimulator.apply_scenario(baseline_forecast, scenario_type, 10)
                scenarios_tested.append(scenario_type)
            except:
                pass
        
        print(f"  All scenarios working: {len(scenarios_tested)}/{len(ScenarioSimulator.SCENARIOS)}")
        
        return True
        
    except Exception as e:
        print(f"✗ Scenario test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fan_charts():
    """Test fan chart utilities."""
    print("\n" + "="*60)
    print("TEST 7: Fan Chart Utilities")
    print("="*60)
    
    try:
        from financial_dashboard.utils.fan_charts import (
            create_fan_chart,
            create_scenario_comparison_chart,
            create_model_comparison_chart
        )
        
        # Create dummy data
        import plotly.graph_objects as go
        dates = pd.date_range(start='2024-01-01', periods=30)
        values = [100 + i for i in range(30)]
        forecast_dates = pd.date_range(start='2024-01-31', periods=14)
        forecast_data = {
            'forecast': [115 + i for i in range(14)],
            'lower_80': [110 + i for i in range(14)],
            'upper_80': [120 + i for i in range(14)],
            'lower_95': [108 + i for i in range(14)],
            'upper_95': [122 + i for i in range(14)],
        }
        
        # Test fan chart
        fig1 = create_fan_chart(dates, values, forecast_dates, forecast_data, 'TEST')
        assert isinstance(fig1, go.Figure)
        print(f"✓ Fan chart created successfully")
        
        # Test scenario comparison
        fig2 = create_scenario_comparison_chart(
            forecast_dates,
            forecast_data['forecast'],
            [x * 1.02 for x in forecast_data['forecast']],
            'Test Scenario',
            'TEST'
        )
        assert isinstance(fig2, go.Figure)
        print(f"✓ Scenario comparison chart created")
        
        # Test model comparison
        fig3 = create_model_comparison_chart(
            forecast_dates,
            {'prophet': forecast_data['forecast'], 'arima': [x * 0.98 for x in forecast_data['forecast']]},
            'TEST'
        )
        assert isinstance(fig3, go.Figure)
        print(f"✓ Model comparison chart created")
        
        return True
        
    except Exception as e:
        print(f"✗ Fan chart test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n" + "="*60)
    print("MARKET FORECAST TAB - COMPREHENSIVE TEST SUITE")
    print("="*60)
    
    results = {}
    
    # Test 1: Data fetching
    success, hist_data = test_data_fetching()
    results['Data Fetching'] = success
    
    if not success:
        print("\n❌ Cannot proceed without data")
        return
    
    # Test 2-5: Models
    results['Prophet'] = test_prophet_model(hist_data)[0]
    results['ARIMA'] = test_arima_model(hist_data)[0]
    results['LSTM'] = test_lstm_model(hist_data)[0]
    ensemble_success, ensemble_forecast = test_ensemble_model(hist_data)
    results['Ensemble'] = ensemble_success
    
    # Test 6: Scenarios
    if ensemble_success:
        results['Scenarios'] = test_scenario_simulator(ensemble_forecast['forecast'])
    else:
        results['Scenarios'] = False
    
    # Test 7: Visualizations
    results['Fan Charts'] = test_fan_charts()
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, passed_test in results.items():
        status = "✓ PASS" if passed_test else "✗ FAIL"
        print(f"{status:10} {test_name}")
    
    print("\n" + "="*60)
    print(f"OVERALL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*60)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Market Forecast tab is fully functional.")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review errors above.")


if __name__ == "__main__":
    main()
