import numpy as np
import pandas as pd
from financial_dashboard.services.forecast_adapter import ForecastAdapter


class FakeMLRunner:
    def initialize(self):
        pass

    def predict(self, name, input_data):
        last = float(input_data['prices'][-1])
        return {'metadata': {'success': True}, 'predicted_price': last * 1.05}


def test_run_forecast_ensemble_path():
    adapter = ForecastAdapter(deterministic=True)

    # Short synthetic price series
    prices = pd.Series(np.linspace(100.0, 110.0, 60))
    metadata = {'source': 'synthetic', 'fetch_duration_ms': 1, 'data_timestamp': None, 'data_points': len(prices)}

    # Patch fetcher
    adapter._fetch_historical_data = lambda ticker, lookback_days=252: (prices, metadata)

    # Inject fake ml runner
    adapter.ml_runner = FakeMLRunner()

    res = adapter.run_forecast('TST', horizon=7, confidence=0.95, model='ensemble', forecast_id='f1')

    assert res['status'] == 'success'
    assert 'forecast' in res
    assert res['metadata']['inference_source'] == 'ensemble'
    assert len(res['forecast']) == 7
