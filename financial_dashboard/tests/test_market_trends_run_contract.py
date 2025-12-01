import pytest

from financial_dashboard import market_trends_dash as mtd


def test_run_full_analysis_contract():
    """Ensure run_full_analysis returns the expected contract shape."""
    # Use a small set of tickers to keep the test fast
    tickers = ['AAPL', 'MSFT', 'GOOGL']

    res = mtd.run_full_analysis(tickers, period='1y', interval='1d', options_topn=1, use_cache_only=True)

    assert isinstance(res, dict), "Result should be a dict"
    # When using cache_only, the function should still return a dict with keys
    assert 'detailed' in res or 'tidy' in res

    rows = res.get('detailed') or res.get('tidy') or []
    assert isinstance(rows, list)
    # If there are rows, they should contain at least ticker and composite_score or similar
    if rows:
        first = rows[0]
        assert isinstance(first, dict)
        assert 'ticker' in first or 'symbol' in first
