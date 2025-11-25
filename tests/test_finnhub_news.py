"""
Focused test for Finnhub company news using both keys.
Prints status, rate-limit headers, item count and 5 sample headlines.
"""
import os
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv('/mnt/c/Aarav/fin_env/unified-dashboard/keys.env')

FINNHUB_KEY1 = os.getenv('FINNHUB_API_KEY')
FINNHUB_KEY2 = os.getenv('FINNHUB2_API_KEY')

BASE_URL = 'https://finnhub.io/api/v1'
TICKER = 'AAPL'

end = datetime.now().date()
start = end - timedelta(days=7)

params_template = lambda key: {
    'symbol': TICKER,
    'from': start.strftime('%Y-%m-%d'),
    'to': end.strftime('%Y-%m-%d'),
    'token': key
}


def fetch_news(key, key_name):
    print('\n' + '='*60)
    print(f'Testing Finnhub news with {key_name}')
    print('='*60)
    if not key:
        print('Key not provided')
        return None
    try:
        r = requests.get(f'{BASE_URL}/company-news', params=params_template(key), timeout=10)
        print('Status:', r.status_code)
        for h in ['X-RateLimit-Limit', 'X-RateLimit-Remaining', 'X-RateLimit-Reset']:
            print(f'{h}:', r.headers.get(h, 'N/A'))
        if r.status_code == 200:
            data = r.json()
            print('Items:', len(data))
            for i, item in enumerate(data[:5]):
                print(f" {i+1}. {item.get('headline')[:120]}")
            return data
        else:
            print('Response text:', r.text[:300])
            return None
    except Exception as e:
        print('Exception:', e)
        return None


if __name__ == '__main__':
    fetch_news(FINNHUB_KEY1, 'Key 1')
    fetch_news(FINNHUB_KEY2, 'Key 2')
