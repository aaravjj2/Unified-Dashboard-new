#
# Description: This script fetches company news headlines for a list of stock tickers
#              for the last 30 days using the Finnhub API.
#

import finnhub
import datetime

# --- Configuration ---
# Replace 'YOUR_API_KEY' with your actual Finnhub API key.
FINNHUB_API_KEY = "d28ndhhr01qmp5u9g65gd28ndhhr01qmp5u9g660"

# List of tickers to fetch news for.
tickers = [
    'INTU', 'ANET', 'TMO', 'QCOM', 'TBB', 'GEV', 'SCHW', 'SPGI', 'TXN', 'BA',
    'TJX', 'ISRG', 'LRCX', 'ADBE', 'LOW', 'AMGN', 'BSX', 'NEE', 'APH', 'COF',
    'SYK', 'PGR', 'AMAT', 'GILD', 'DHR', 'PFE', 'PANW', 'BX', 'HON', 'KLAC',
    'UNP', 'KKR', 'DE', 'MDT', 'ADI', 'CMCSA', 'COP', 'ADP', 'CRWD', 'WELL',
    'DASH', 'SE', 'LMT', 'MO', 'INTC', 'NKE', 'IBKR', 'PLD', 'HOOD', 'SO'
]

# --- Main Script Logic ---

# 1. Set up the Finnhub client
try:
    finnhub_client = finnhub.Client(api_key=FINNHUB_API_KEY)
except Exception as e:
    print(f"Error initializing Finnhub client: {e}")
    exit()

# 2. Calculate the date range (last 30 days)
today = datetime.date.today()
thirty_days_ago = today - datetime.timedelta(days=30)

# Format dates into YYYY-MM-DD strings as required by the Finnhub API
end_date = today.strftime("%Y-%m-%d")
start_date = thirty_days_ago.strftime("%Y-%m-%d")

print(f"Fetching news from {start_date} to {end_date}...\n")

# 3. Loop through each ticker and fetch news
for ticker in tickers:
    print(f"--- News for {ticker} ---")
    try:
        # Fetch company news for the specified date range
        news_list = finnhub_client.company_news(ticker, _from=start_date, to=end_date)

        # 4. Print the headlines
        if not news_list:
            print(f"No news found for {ticker} in the last 30 days.")
        else:
            # We'll print the top 5 headlines to keep the output clean
            for i, news_item in enumerate(news_list[:5]):
                headline = news_item.get('headline', 'No headline available')
                print(f"  - {headline}")

    except Exception as e:
        print(f"An error occurred while fetching news for {ticker}: {e}")

    # Add a blank line for better readability between tickers
    print("")

print("Script finished.")