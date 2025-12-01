"""Pytest for PriceClient (free-tier integration smoke).

This is a minimal, network-enabled smoke test that asserts the
PriceClient returns a mapping for requested tickers and that the
current_price values are numeric.

Note: This test performs live provider calls (Alpaca / Finnhub / yfinance)
and therefore is a higher-level integration test. It's kept small and
deterministic for local validation during remediation work.
"""
import pytest
from financial_dashboard.utils.price_client import PriceClient


def test_priceclient_returns_numeric_prices():
    client = PriceClient()
    tickers = ['AAPL', 'MSFT', 'TSLA']

    results = client.get_prices(tickers=tickers, lookback_days=30, investment_per_ticker=1000.0)

    assert isinstance(results, dict), "get_prices should return a dict keyed by ticker"
    for t in tickers:
        assert t in results, f"Missing ticker in results: {t}"
        data = results[t]
        assert isinstance(data, dict), f"Ticker data should be a dict for {t}"

        # current_price should exist and be numeric (or convertible to float)
        cp = data.get('current_price')
        assert cp is not None, f"current_price missing for {t}"
        try:
            float(cp)
        except Exception:
            pytest.fail(f"current_price for {t} is not numeric: {cp}")

