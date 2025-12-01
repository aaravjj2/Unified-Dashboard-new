import os
import requests

# Load Finnhub API keys from environment
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
FINNHUB2_API_KEY = os.getenv('FINNHUB2_API_KEY')

# Use the first key by default, fallback to second if needed
def get_finnhub_key():
    return FINNHUB_API_KEY or FINNHUB2_API_KEY

# Basic fetch test for TSLA quote

def fetch_tsla_quote():
    api_key = get_finnhub_key()
    url = f"https://finnhub.io/api/v1/quote?symbol=TSLA&token={api_key}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print("TSLA Quote:", data)
        return data
    except Exception as e:
        print("Error fetching TSLA quote:", e)
        return None

if __name__ == "__main__":
    fetch_tsla_quote()
