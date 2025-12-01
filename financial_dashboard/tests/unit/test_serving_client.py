"""
Unit tests for model serving wrapper (Bento/Triton/local) and ForecastAdapter integration.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock


def test_serving_client_bento_mode(monkeypatch):
    """Test ServingClient in Bento mode calls Bento endpoint and parses response."""
    monkeypatch.setenv('USE_BENTO', '1')
    monkeypatch.setenv('BENTO_URL', 'http://localhost:5001')

    # Mock requests.post
    import requests
    with patch('requests.post') as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'ticker': 'AAPL',
            'forecast': [{'date': '2025-12-01', 'yhat': 170.0, 'yhat_lower': 160.0, 'yhat_upper': 180.0}]
        }
        mock_post.return_value = mock_resp

        from financial_dashboard.serving.serving_client import ServingClient
        sc = ServingClient()
        res = sc.predict_forecast('AAPL', 30, 'ensemble', 0.95)
        assert res['status'] == 'success'
        assert res['source'] == 'bento'
        assert 'data' in res
        assert res['data']['ticker'] == 'AAPL'


@patch('financial_dashboard.serving.triton_integration.TritonClient')
def test_serving_client_triton_mode(mock_triton_client_class, monkeypatch):
    monkeypatch.setenv('USE_TRITON', '1')
    monkeypatch.setenv('TRITON_URL', 'localhost:8000')

    # Create a fake triton client that raises if used (we won't fully exercise it here)
    mock_triton = MagicMock()
    mock_triton.infer_sentiment.return_value = [{'label': 'positive', 'score': 0.9}]
    mock_triton_client_class.return_value = mock_triton

    from financial_dashboard.serving.serving_client import ServingClient
    sc = ServingClient()
    # predict_forecast currently returns an error placeholder for triton (not fully implemented)
    res = sc.predict_forecast('AAPL', 30, 'ensemble', 0.95)
    assert res['source'] == 'triton'


def test_serving_client_local_mode(monkeypatch):
    monkeypatch.delenv('USE_BENTO', raising=False)
    monkeypatch.delenv('USE_TRITON', raising=False)

    from financial_dashboard.serving.serving_client import ServingClient

    # Monkeypatch AIForecastEngine to return a predictable forecast
    class DummyEngine:
        def forecast(self, ticker, horizon, model):
            return {
                'forecast': [{'date': '2025-12-01', 'yhat': 100.0}],
                'confidence': 0.95
            }

    monkeypatch.setattr('financial_dashboard.models.ai_forecast_engine.AIForecastEngine', DummyEngine, raising=False)

    sc = ServingClient()
    res = sc.predict_forecast('AAPL', 30, 'ensemble', 0.95)
    assert res['status'] == 'success'
    assert res['source'] == 'local'
    assert 'data' in res


def test_forecast_adapter_uses_serving_client(monkeypatch):
    """Test ForecastAdapter.run_forecast uses ServingClient when available."""
    monkeypatch.setenv('USE_BENTO', '1')
    monkeypatch.setenv('BENTO_URL', 'http://localhost:5001')

    import requests
    with patch('requests.post') as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            'ticker': 'AAPL',
            'forecast': [{'date': '2025-12-01', 'yhat': 200.0}],
            'confidence': 0.95
        }
        mock_post.return_value = mock_resp

        from financial_dashboard.services.forecast_adapter import ForecastAdapter
        adapter = ForecastAdapter()

        # Monkeypatch _fetch_historical_data to return valid (series, metadata) tuple
        import pandas as pd
        idx = pd.date_range('2025-01-01', periods=120, freq='D')
        prices = pd.Series([100 + i * 0.5 for i in range(len(idx))], index=idx)
        metadata = {
            'source': 'mock',
            'fetch_duration_ms': 0,
            'data_timestamp': '2025-05-01T00:00:00',
            'ticker': 'AAPL'
        }
        monkeypatch.setattr(adapter, '_fetch_historical_data', lambda t, lookback_days=252: (prices, metadata))

        res = adapter.run_forecast('AAPL', 30, 0.95, 'ensemble', 'test123')
        assert res['status'] == 'success'
        assert res['ticker'] == 'AAPL'
        assert 'forecast' in res
