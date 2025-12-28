import sys
import types
from datetime import datetime
import pytest

from financial_dashboard.services.rag.ingestion_service import RAGDataIngestionService


class FakeAlpacaArticle:
    def __init__(self, headline, summary, url, created_at, symbols):
        self.headline = headline
        self.summary = summary
        self.url = url
        self.created_at = created_at
        self.symbols = symbols


class FakeNewsClientWithSymbols:
    def __init__(self, key=None, secret=None):
        pass

    def get_news(self, symbols=None, start=None, end=None, limit=50):
        # honor symbols arg
        return [
            FakeAlpacaArticle(
                headline=f"Test {symbols[0]} news",
                summary="Summary",
                url=f"https://example.com/{symbols[0]}",
                created_at=datetime.utcnow(),
                symbols=[symbols[0]]
            )
        ]


class FakeNewsClientNoSymbolKw:
    def __init__(self, key=None, secret=None):
        pass

    # Signature does NOT accept 'symbols' kwarg -> triggers TypeError in client.get_news(symbols=[...]) call
    def get_news(self, start, end, limit=200):
        return [
            {
                'headline': 'Fallback AAPL news',
                'summary': 'Summary',
                'url': 'https://example.com/aapl',
                'created_at': datetime.utcnow(),
                'symbols': ['AAPL']
            }
        ]


def _patch_alpaca_client(monkeypatch, client_cls):
    mod = types.ModuleType('alpaca')
    data_mod = types.ModuleType('alpaca.data')
    data_mod.NewsClient = client_cls
    sys.modules['alpaca'] = mod
    sys.modules['alpaca.data'] = data_mod


def _patch_finnhub_client(monkeypatch, client_cls):
    mod = types.ModuleType('finnhub')
    mod.Client = client_cls
    sys.modules['finnhub'] = mod


def test_alpaca_per_symbol_supported(monkeypatch):
    _patch_alpaca_client(monkeypatch, FakeNewsClientWithSymbols)
    svc = RAGDataIngestionService(index_dir="/tmp")
    res = svc.fetch_alpaca_news(symbols=['AAPL'], days_back=1)
    assert res and any('AAPL' in (a.get('symbols') or []) for a in res)


def test_alpaca_per_symbol_unsupported(monkeypatch):
    _patch_alpaca_client(monkeypatch, FakeNewsClientNoSymbolKw)
    svc = RAGDataIngestionService(index_dir="/tmp")
    res = svc.fetch_alpaca_news(symbols=['AAPL'], days_back=1)
    assert res and any('AAPL' in (a.get('symbols') or []) for a in res)


class FakeFinnhubA:
    # supports general_news(category)
    def __init__(self, api_key=None):
        pass

    def general_news(self, category):
        return [
            {'headline': 'AAPL beats', 'summary': 'Good', 'url': 'https://x', 'datetime': int(datetime.utcnow().timestamp()), 'related': 'AAPL'}
        ]


class FakeFinnhubB:
    # requires minId arg
    def __init__(self, api_key=None):
        pass

    def general_news(self, category, minId):
        return [
            {'headline': 'AAPL corr', 'summary': 'Info', 'url': 'https://x2', 'datetime': int(datetime.utcnow().timestamp()), 'related': 'aapl,nvda'}
        ]


def test_finnhub_general_news_variants(monkeypatch):
    _patch_finnhub_client(monkeypatch, FakeFinnhubA)
    svc = RAGDataIngestionService(index_dir="/tmp")
    res = svc.fetch_finnhub_news(category='general', days_back=1)
    assert res and any('AAPL' in (a.get('symbols') or []) for a in res)

    _patch_finnhub_client(monkeypatch, FakeFinnhubB)
    svc = RAGDataIngestionService(index_dir="/tmp")
    res = svc.fetch_finnhub_news(category='general', days_back=1)
    assert res and any('AAPL' in (a.get('symbols') or []) for a in res)
