#!/usr/bin/env python3
"""Run lightweight authenticated checks for API keys found in keys.env.

Usage: python3 scripts/test_keys.py
This will load local env via `src.utils.secrets.load_local_env()` and attempt
minimal provider requests. It will print a JSON report; no secret values are
printed.
"""
from src.utils.secrets import load_local_env, get_openai_key, get_alpaca_credentials, get_tiingo_key, get_finnhub_key, get_polygon_key, get_quandl_key, get_twelvedata_key, get_rapidapi_key, get_news_api_key
import requests
import json


def main():
    load_local_env()
    report = {}

    # OpenAI
    openai = get_openai_key()
    if openai:
        try:
            r = requests.get('https://api.openai.com/v1/models', headers={'Authorization': f'Bearer {openai}'}, timeout=10)
            report['OpenAI'] = (r.status_code, r.reason)
        except Exception as e:
            report['OpenAI'] = ('error', str(e))
    else:
        report['OpenAI'] = ('missing', '')

    # Alpaca
    key_id, secret, base_url = get_alpaca_credentials()
    if key_id and secret:
        try:
            r = requests.get(f"{base_url.rstrip('/')}/v2/account", headers={'APCA-API-KEY-ID': key_id, 'APCA-API-SECRET-KEY': secret}, timeout=10)
            report['Alpaca'] = (r.status_code, r.reason)
        except Exception as e:
            report['Alpaca'] = ('error', str(e))
    else:
        report['Alpaca'] = ('missing','')

    # Tiingo
    tiingo = get_tiingo_key()
    if tiingo:
        try:
            r = requests.get('https://api.tiingo.com/api/test', params={'token': tiingo}, timeout=10)
            report['Tiingo'] = (r.status_code, r.text[:200])
        except Exception as e:
            report['Tiingo'] = ('error', str(e))
    else:
        report['Tiingo'] = ('missing','')

    # Finnhub
    finn = get_finnhub_key()
    if finn:
        try:
            r = requests.get('https://finnhub.io/api/v1/stock/symbol', params={'exchange':'US','token':finn}, timeout=10)
            report['Finnhub'] = (r.status_code, (r.text[:200] if r.text else ''))
        except Exception as e:
            report['Finnhub'] = ('error', str(e))
    else:
        report['Finnhub'] = ('missing','')

    # Polygon
    poly = get_polygon_key()
    if poly:
        try:
            r = requests.get('https://api.polygon.io/v3/reference/tickers', params={'limit':1,'apiKey':poly}, timeout=10)
            report['Polygon'] = (r.status_code, (r.text[:200] if r.text else ''))
        except Exception as e:
            report['Polygon'] = ('error', str(e))
    else:
        report['Polygon'] = ('missing','')

    # TwelveData
    t12 = get_twelvedata_key()
    if t12:
        try:
            r = requests.get('https://api.twelvedata.com/time_series', params={'symbol':'AAPL','interval':'1day','apikey':t12,'outputsize':1}, timeout=10)
            report['TwelveData'] = (r.status_code, (r.text[:200] if r.text else ''))
        except Exception as e:
            report['TwelveData'] = ('error', str(e))
    else:
        report['TwelveData'] = ('missing','')

    # Quandl
    quandl = get_quandl_key()
    if quandl:
        try:
            r = requests.get('https://www.quandl.com/api/v3/datasets.json?query=AAPL&api_key='+quandl, timeout=10)
            report['Quandl'] = (r.status_code, (r.text[:200] if r.text else ''))
        except Exception as e:
            report['Quandl'] = ('error', str(e))
    else:
        report['Quandl'] = ('missing','')

    # RapidAPI presence
    rapid = get_rapidapi_key()
    report['RapidAPI'] = ('present' if rapid else 'missing','')

    # NewsAPI
    news = get_news_api_key()
    if news:
        try:
            r = requests.get('https://newsapi.org/v2/top-headlines', params={'apiKey':news,'pageSize':1}, timeout=10)
            report['NewsAPI'] = (r.status_code, (r.text[:200] if r.text else ''))
        except Exception as e:
            report['NewsAPI'] = ('error', str(e))
    else:
        report['NewsAPI'] = ('missing','')

    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
