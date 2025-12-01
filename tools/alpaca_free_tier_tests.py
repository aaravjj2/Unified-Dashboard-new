import os
import requests
import time

ALPACA_API_KEY = os.getenv('APCA_API_KEY', 'PKMZZAL28UP5G05AECSW')
ALPACA_SECRET_KEY = os.getenv('APCA_API_SECRET_KEY', 'QavdtLfphkusZaXaVgcL4xBULaXHcUIFagIrupnT')

headers = {
    'APCA-API-KEY-ID': ALPACA_API_KEY,
    'APCA-API-SECRET-KEY': ALPACA_SECRET_KEY
}

# 1. Trading API Rate Limit Test (200 req/min)
def test_trading_api_rate_limit():
    url = 'https://paper-api.alpaca.markets/v2/account'
    success, fail = 0, 0
    for i in range(10):  # 10 quick requests, should not hit limit
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            success += 1
        else:
            fail += 1
        time.sleep(0.2)  # 5 req/sec
    print(f"Trading API: {success} success, {fail} fail")

# 2. Market Data API Rate Limit Test (200 req/min)
def test_market_data_api_rate_limit():
    url = 'https://data.alpaca.markets/v2/stocks/TSLA/quotes/latest'
    success, fail = 0, 0
    for i in range(10):
        r = requests.get(url, headers=headers)
        if r.status_code == 200:
            success += 1
        else:
            fail += 1
        time.sleep(0.2)
    print(f"Market Data API: {success} success, {fail} fail")

# 3. Market Data Coverage (IEX only, real-time)
def test_market_data_iex():
    url = 'https://data.alpaca.markets/v2/stocks/TSLA/quotes/latest'
    r = requests.get(url, headers=headers)
    data = r.json()
    print('IEX real-time data:', data)
    assert 'quote' in data

# 4. Historical Data Limitation (latest 15 min only)
def test_historical_data_limit():
    import datetime
    now = datetime.datetime.utcnow()
    start = (now - datetime.timedelta(minutes=20)).isoformat() + 'Z'
    end = now.isoformat() + 'Z'
    url = f'https://data.alpaca.markets/v2/stocks/TSLA/bars?start={start}&end={end}&timeframe=1Min'
    r = requests.get(url, headers=headers)
    data = r.json()
    print('Historical bars (20min window):', data)
    # Should only get bars for last 15 min
    bars = data.get('bars', [])
    if bars:
        oldest = bars[0]['t']
        print('Oldest bar timestamp:', oldest)
    else:
        print('No bars returned')

# 5. Websocket/Options: Not tested here (requires async/ws client)

def main():
    print('--- Trading API Rate Limit Test ---')
    test_trading_api_rate_limit()
    print('\n--- Market Data API Rate Limit Test ---')
    test_market_data_api_rate_limit()
    print('\n--- Market Data IEX Coverage Test ---')
    test_market_data_iex()
    print('\n--- Historical Data Limitation Test ---')
    test_historical_data_limit()
    print('\n--- Websocket/Options: Manual/Not tested in script ---')

if __name__ == '__main__':
    main()
