#!/usr/bin/env python3
"""Test provider endpoints and capture rate-limit headers where available.

This script loads local env via `src.utils.secrets.load_local_env()` and then
makes small authenticated requests to providers to capture status codes and
any common rate-limit headers. It prints a JSON object mapping provider ->
{'status': int|'error'|'missing', 'headers': {<header>: <value>, ...}, 'note': str}

No secret values are printed.
"""
from src.utils.secrets import load_local_env, get_openai_key, get_alpaca_credentials, get_tiingo_key, get_finnhub_key, get_polygon_key, get_quandl_key, get_twelvedata_key, get_rapidapi_key, get_news_api_key
import requests
import json

HEADERS_OF_INTEREST = [
    'x-ratelimit-limit', 'x-ratelimit-remaining', 'x-ratelimit-reset',
    'x-ratelimit-limit-requests', 'x-request-limit', 'rate-limit', 'retry-after',
    'x-ratelimit-requests-limit', 'x-ratelimit-requests-remaining'
]


def extract_headers(resp):
    out = {}
    for h in HEADERS_OF_INTEREST:
        if h in resp.headers:
            out[h] = resp.headers.get(h)
    return out


def main():
    load_local_env()
    report = {}

    # Quandl: try dataset endpoint and search endpoint
    quandl = get_quandl_key()
    if quandl:
        try:
            r1 = requests.get(f'https://www.quandl.com/api/v3/datasets/WIKI/AAPL.json?api_key={quandl}', timeout=10)
            r2 = requests.get(f'https://www.quandl.com/api/v3/datasets.json?query=AAPL&api_key={quandl}', timeout=10)
            report['Quandl_dataset'] = {'status': r1.status_code, 'headers': extract_headers(r1), 'note': r1.reason}
            report['Quandl_search'] = {'status': r2.status_code, 'headers': extract_headers(r2), 'note': r2.reason}
        except Exception as e:
            report['Quandl'] = {'status': 'error', 'headers': {}, 'note': str(e)}
    else:
        report['Quandl'] = {'status': 'missing', 'headers': {}, 'note': ''}

    # Re-check other providers for rate limit headers
    # OpenAI
    openai = get_openai_key()
    if openai:
        try:
            r = requests.get('https://api.openai.com/v1/models', headers={'Authorization': f'Bearer {openai}'}, timeout=10)
            report['OpenAI'] = {'status': r.status_code, 'headers': extract_headers(r), 'note': r.reason}
        except Exception as e:
            report['OpenAI'] = {'status': 'error', 'headers': {}, 'note': str(e)}
    else:
        report['OpenAI'] = {'status': 'missing', 'headers': {}, 'note': ''}

    # Alpaca
    key_id, secret, base_url = get_alpaca_credentials()
    if key_id and secret:
        try:
            r = requests.get(f"{base_url.rstrip('/')}/v2/account", headers={'APCA-API-KEY-ID': key_id, 'APCA-API-SECRET-KEY': secret}, timeout=10)
            report['Alpaca'] = {'status': r.status_code, 'headers': extract_headers(r), 'note': r.reason}
        except Exception as e:
            report['Alpaca'] = {'status': 'error', 'headers': {}, 'note': str(e)}
    else:
        report['Alpaca'] = {'status': 'missing', 'headers': {}, 'note': ''}

    # Tiingo
    tiingo = get_tiingo_key()
    if tiingo:
        try:
            r = requests.get('https://api.tiingo.com/api/test', params={'token': tiingo}, timeout=10)
            report['Tiingo'] = {'status': r.status_code, 'headers': extract_headers(r), 'note': r.text[:200]}
        except Exception as e:
            report['Tiingo'] = {'status': 'error', 'headers': {}, 'note': str(e)}
    else:
        report['Tiingo'] = {'status': 'missing', 'headers': {}, 'note': ''}

    # Finnhub
    finn = get_finnhub_key()
    if finn:
        try:
            r = requests.get('https://finnhub.io/api/v1/stock/symbol', params={'exchange':'US','token':finn}, timeout=10)
            report['Finnhub'] = {'status': r.status_code, 'headers': extract_headers(r), 'note': (r.text[:200] if r.text else '')}
        except Exception as e:
            report['Finnhub'] = {'status': 'error', 'headers': {}, 'note': str(e)}
    else:
        report['Finnhub'] = {'status': 'missing', 'headers': {}, 'note': ''}

    # Polygon
    poly = get_polygon_key()
    if poly:
        try:
            r = requests.get('https://api.polygon.io/v3/reference/tickers', params={'limit':1,'apiKey':poly}, timeout=10)
            report['Polygon'] = {'status': r.status_code, 'headers': extract_headers(r), 'note': (r.text[:200] if r.text else '')}
        except Exception as e:
            report['Polygon'] = {'status': 'error', 'headers': {}, 'note': str(e)}
    else:
        report['Polygon'] = {'status': 'missing', 'headers': {}, 'note': ''}

    # TwelveData
    t12 = get_twelvedata_key()
    if t12:
        try:
            r = requests.get('https://api.twelvedata.com/time_series', params={'symbol':'AAPL','interval':'1day','apikey':t12,'outputsize':1}, timeout=10)
            report['TwelveData'] = {'status': r.status_code, 'headers': extract_headers(r), 'note': (r.text[:200] if r.text else '')}
        except Exception as e:
            report['TwelveData'] = {'status': 'error', 'headers': {}, 'note': str(e)}
    else:
        report['TwelveData'] = {'status': 'missing', 'headers': {}, 'note': ''}

    # NewsAPI
    news = get_news_api_key()
    if news:
        try:
            r = requests.get('https://newsapi.org/v2/top-headlines', params={'apiKey':news,'pageSize':1, 'country':'us'}, timeout=10)
            report['NewsAPI'] = {'status': r.status_code, 'headers': extract_headers(r), 'note': (r.text[:200] if r.text else '')}
        except Exception as e:
            report['NewsAPI'] = {'status': 'error', 'headers': {}, 'note': str(e)}
    else:
        report['NewsAPI'] = {'status': 'missing', 'headers': {}, 'note': ''}

    # RapidAPI presence only
    rapid = get_rapidapi_key()
    report['RapidAPI'] = {'status': 'present' if rapid else 'missing', 'headers': {}, 'note': ''}

    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
