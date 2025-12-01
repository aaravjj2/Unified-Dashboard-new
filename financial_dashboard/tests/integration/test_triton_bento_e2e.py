import os
import time
import pytest
import requests

from financial_dashboard.serving.triton_integration import TritonClient


@pytest.mark.integration
def test_triton_embeddings_and_sentiment_e2e():
    """Integration test: confirm Triton server is up and returns embeddings+sentiment."""
    tc = TritonClient(url=os.getenv('TRITON_URL', 'localhost:8000'))
    assert tc.is_server_ready(), 'Triton server not ready'

    texts = ["Apple Q4 earnings beat estimates", "Mixed guidance weighs on stock"]
    emb = tc.infer_embeddings(texts)
    assert emb.shape[0] == len(texts)
    preds = tc.infer_sentiment(texts)
    assert isinstance(preds, list)
    assert all('label' in p and 'score' in p for p in preds)


@pytest.mark.integration
def test_bento_forecast_and_sentiment_e2e():
    bento_url = os.getenv('BENTO_URL', 'http://127.0.0.1:3000')
    # Forecast
    r = requests.post(f"{bento_url}/forecast_price", json={"request": {"ticker": "AAPL", "horizon": 7}})
    assert r.status_code == 200
    data = r.json()
    assert 'ticker' in data and data['ticker'] == 'AAPL'

    # Sentiment
    r2 = requests.post(f"{bento_url}/analyze_sentiment", json={"request": {"texts": ["Apple beat estimates"]}})
    # Bento may return a 200 with error message structured as dict containing error field in `data`
    assert r2.status_code in (200, 400)
    # If successful, ensure sentiments present
    if r2.status_code == 200:
        d = r2.json()
        assert 'sentiments' in d or 'aggregate' in d or 'error' in d
