import os
from financial_dashboard.services.forecast_adapter import ForecastAdapter


def test_prewarm_writes_cache(tmp_path, monkeypatch):
    # Use a fake home directory
    fake_home = tmp_path / 'home'
    fake_home.mkdir()
    monkeypatch.setenv('HOME', str(fake_home))

    adapter = ForecastAdapter(deterministic=True)

    # Patch _fetch_historical_data to return a small series
    class FakeSeries:
        def __len__(self):
            return 10

    adapter._fetch_historical_data = lambda t, lookback_days=252: ([1, 2, 3], {'source': 'test', 'fetch_duration_ms': 1})

    adapter.prewarm(['TST'], lookback_days=30)

    cache_dir = fake_home / '.cache' / 'financial_dashboard'
    cache_file = cache_dir / 'prewarm_cache.json'

    assert cache_file.exists(), 'Prewarm cache file should be created in $HOME/.cache/financial_dashboard'
