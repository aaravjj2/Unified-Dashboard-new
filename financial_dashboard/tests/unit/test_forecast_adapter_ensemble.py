import numpy as np
import pandas as pd
from financial_dashboard.services.forecast_adapter import ForecastAdapter


class FakeMLRunner:
    def initialize(self):
        pass

    def predict(self, name, input_data):
        # Predict a 5% increase over last price
        last = float(input_data['prices'][-1])
        return {'metadata': {'success': True}, 'predicted_price': last * 1.05}


def test_ensemble_is_weighted_average():
    prices = pd.Series(np.linspace(100.0, 120.0, 100))
    adapter = ForecastAdapter(deterministic=True)

    # Inject fake ml runner
    adapter.ml_runner = FakeMLRunner()

    horizon = 7

    ml_series = adapter._ml_forecast('TST', prices, horizon)
    stat_series = adapter._statistical_forecast(prices, horizon)
    weights = adapter._compute_model_weights(prices)

    ensemble = adapter._ensemble_forecast('TST', prices, horizon)

    expected = weights['ml'] * np.array(ml_series) + weights['stat'] * np.array(stat_series)

    assert np.allclose(ensemble, expected, atol=1e-6)
