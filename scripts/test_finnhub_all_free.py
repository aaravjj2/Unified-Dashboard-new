import os
import requests

FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
FINNHUB2_API_KEY = os.getenv('FINNHUB2_API_KEY')

# Use the first key by default, fallback to second if needed
def get_finnhub_key():
    return FINNHUB_API_KEY or FINNHUB2_API_KEY

BASE_URL = "https://finnhub.io/api/v1"
SYMBOL = "TSLA"

endpoints = {
    "quote": f"/quote?symbol={SYMBOL}",
    "profile2": f"/stock/profile2?symbol={SYMBOL}",
    "peers": f"/stock/peers?symbol={SYMBOL}",
    "metric": f"/stock/metric?symbol={SYMBOL}&metric=all",
    "candle": f"/stock/candle?symbol={SYMBOL}&resolution=D&from=1704067200&to=1706659200",  # Jan 2024
    "news": f"/company-news?symbol={SYMBOL}&from=2024-01-01&to=2024-01-31",
    "earnings": f"/stock/earnings?symbol={SYMBOL}",
    "recommendation": f"/stock/recommendation?symbol={SYMBOL}",
    "target-price": f"/stock/target-price?symbol={SYMBOL}",
    "upgrade-downgrade": f"/stock/upgrade-downgrade?symbol={SYMBOL}",
    "insider-transactions": f"/stock/insider-transactions?symbol={SYMBOL}",
    "ownership": f"/stock/ownership?symbol={SYMBOL}",
    "financials-reported": f"/stock/financials-reported?symbol={SYMBOL}",
    "filings": f"/stock/filings?symbol={SYMBOL}",
    "split": f"/stock/split?symbol={SYMBOL}",
    "dividend": f"/stock/dividend?symbol={SYMBOL}",
    "executive": f"/stock/executive?symbol={SYMBOL}",
    "transcripts": f"/stock/transcripts?symbol={SYMBOL}",
    "sec-sentiment": f"/stock/sec-sentiment?symbol={SYMBOL}",
    "press-releases": f"/stock/press-releases?symbol={SYMBOL}",
}

def fetch_finnhub(endpoint):
    api_key = get_finnhub_key()
    url = f"{BASE_URL}{endpoint}&token={api_key}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {"error": str(e)}

def main():
    for name, endpoint in endpoints.items():
        print(f"\n--- {name.upper()} ---")
        result = fetch_finnhub(endpoint)
        print(result)

if __name__ == "__main__":
    main()
