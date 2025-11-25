import os
import requests

ALPACA_API_KEY = os.getenv('APCA_API_KEY', 'PKMZZAL28UP5G05AECSW')
ALPACA_SECRET_KEY = os.getenv('APCA_API_SECRET_KEY', 'QavdtLfphkusZaXaVgcL4xBULaXHcUIFagIrupnT')
ALPACA_ENDPOINT = os.getenv('APCA_ENDPOINT', 'https://paper-api.alpaca.markets/v2')

headers = {
    'APCA-API-KEY-ID': ALPACA_API_KEY,
    'APCA-API-SECRET-KEY': ALPACA_SECRET_KEY
}

def test_tsla_quote():
    url = 'https://data.alpaca.markets/v2/stocks/TSLA/quotes/latest'
    r = requests.get(url, headers=headers)
    print('Status:', r.status_code)
    print('Response:', r.json())
    return r

if __name__ == '__main__':
    test_tsla_quote()
