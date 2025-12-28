import os
import pytest
from financial_dashboard.services.rag.ingestion_service import RAGDataIngestionService


@pytest.mark.skipif(not os.getenv('APCA_API_KEY_ID') or not os.getenv('APCA_API_SECRET_KEY'), reason="Alpaca keys not configured")
def test_live_alpaca_news_fetch():
    svc = RAGDataIngestionService()
    res = svc.fetch_alpaca_news(symbols=['AAPL'], days_back=1)
    assert res and any('AAPL' in (s or []) for a in res for s in [a.get('symbols')])


@pytest.mark.skipif(not os.getenv('FINNHUB_API_KEY'), reason="Finnhub key not configured")
def test_live_finnhub_news_fetch():
    svc = RAGDataIngestionService()
    res = svc.fetch_finnhub_news(category='general', days_back=1)
    assert res and len(res) > 0
