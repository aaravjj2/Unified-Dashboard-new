import time
import json
from pathlib import Path
from financial_dashboard.utils import finnhub_news


def test_set_and_get_cache():
    ticker = 'TESTCACHE'
    data = [{'headline': 'Test headline'}]

    # Ensure we can set and then get cache
    finnhub_news.set_cached_news(ticker, data)
    got = finnhub_news.get_cached_news(ticker, ttl_seconds=60)
    assert got is not None
    assert isinstance(got, list)
    assert got[0]['headline'] == 'Test headline'


def test_cache_expiry():
    ticker = 'TESTCACHE'
    # load cache file and set ts to old
    cache_file = finnhub_news.CACHE_FILE
    assert cache_file.exists()
    with cache_file.open('r') as f:
        cache = json.load(f)

    # set entry ts to far past
    if ticker in cache:
        cache[ticker]['ts'] = time.time() - 3600 * 24  # 1 day ago
        with cache_file.open('w') as f:
            json.dump(cache, f)

    expired = finnhub_news.get_cached_news(ticker, ttl_seconds=60)
    assert expired is None
