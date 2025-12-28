import json
from financial_dashboard.app import create_app


def test_run_forecast_api_sync(monkeypatch):
    app = create_app()
    client = app.server.test_client()

    # Patch the run_predict used by the blueprint to avoid heavy work
    def fake_run_predict(payload):
        return {
            'ticker': payload.get('ticker'),
            'horizon': int(payload.get('horizon', 7)),
            'forecast': [100.0 + i for i in range(int(payload.get('horizon', 7)))],
            'status': 'success'
        }

    import financial_dashboard.api.market_forecast as mf
    monkeypatch.setattr(mf, 'run_predict', fake_run_predict)

    payload = {'ticker': 'TST', 'horizon': 5, 'confidence': 0.95}
    r = client.post('/api/market_forecast/run', json=payload)
    assert r.status_code == 200
    data = r.get_json()
    assert 'forecast_id' in data
    assert data['result']['status'] == 'success'


def test_latest_no_forecast(monkeypatch, tmp_path):
    app = create_app()
    client = app.server.test_client()

    # Ensure DATA_DIR is empty by pointing env var or filesystem to tmp
    import financial_dashboard.api.market_forecast as mf
    mf.DATA_DIR = str(tmp_path)

    r = client.get('/api/market_forecast/latest?ticker=NOPE')
    assert r.status_code == 404
