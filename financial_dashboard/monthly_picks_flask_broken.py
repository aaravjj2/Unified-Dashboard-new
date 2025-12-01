"""
Enhanced Monthly Picks viewer with live price data and profit/loss calculation
Shows P/L based on $1000 investment at month start
Run: python3 monthly_picks_flask.py
"""
from flask import Flask, render_template_string
import pandas as pd
import os
import glob
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

# Load API keys
load_dotenv('keys.env')

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Investment per stock for monthly picks
INVESTMENT_PER_STOCK = 1000.0

# API Keys
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY")
FINNHUB2_API_KEY = os.getenv("FINNHUB2_API_KEY")
ALPACA_API_KEY = os.getenv("APCA_API_KEY_ID")
ALPACA_SECRET_KEY = os.getenv("APCA_API_SECRET_KEY")
ALPACA_BASE_URL = 'https://data.alpaca.markets/v2'

def find_latest_monthly_csv():
    base_dir = os.path.dirname(__file__)
    patterns = ['models/full_run/picks*.csv', 'models/full_run/monthly*.csv']
    candidates = []
    for pattern in patterns:
        path = os.path.join(base_dir, pattern)
        candidates.extend(glob.glob(path, recursive=False))
    
    return max(candidates, key=os.path.getmtime) if candidates else None

def get_live_prices_alpaca(tickers):
    """Fetch historical prices from Alpaca API for the past month"""
    price_data = {}
    
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        logging.error("Alpaca API keys not found in environment")
        return price_data
    
    headers = {
        'APCA-API-KEY-ID': ALPACA_API_KEY,
        'APCA-API-SECRET-KEY': ALPACA_SECRET_KEY
    }
    
    # Calculate date range (1 month ago to today)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    for ticker in tickers:
        try:
            # Fetch bars (OHLCV data) from Alpaca
            url = f"{ALPACA_BASE_URL}/stocks/{ticker}/bars"
            params = {
                'start': start_date,
                'end': end_date,
                'timeframe': '1Day',
                'limit': 1000,
                'adjustment': 'all'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                bars = data.get('bars', [])
                
                if len(bars) >= 2:
                    # Get current price (most recent close)
                    current_price = bars[-1]['c']
                    prev_price = bars[-2]['c']
                    daily_change = ((current_price - prev_price) / prev_price) * 100
                    
                    # Get month start price (first bar)
                    month_start_price = bars[0]['c']
                    
                    # Calculate P/L
                    shares = INVESTMENT_PER_STOCK / month_start_price
                    current_value = shares * current_price
                    profit_loss = current_value - INVESTMENT_PER_STOCK
                    
                    price_data[ticker] = {
                        'current_price': round(current_price, 2),
                        'daily_change': round(daily_change, 2),
                        'month_start_price': round(month_start_price, 2),
                        'profit_loss': round(profit_loss, 2)
                    }
                else:
                    logging.warning(f"Insufficient data for {ticker} from Alpaca")
            else:
                logging.warning(f"Alpaca API error for {ticker}: {response.status_code}")
                
        except Exception as e:
            logging.warning(f"Error fetching {ticker} from Alpaca: {e}")
            continue
    
    return price_data

def get_live_prices_finnhub(tickers):
    """Fetch current prices from Finnhub API (fallback)"""
    price_data = {}
    
    if not FINNHUB_API_KEY:
        logging.error("Finnhub API key not found")
        return price_data
    
    for ticker in tickers:
        try:
            # Get current quote
            url = f"https://finnhub.io/api/v1/quote"
            params = {'symbol': ticker, 'token': FINNHUB_API_KEY}
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                current_price = data.get('c', 0)  # Current price
                prev_close = data.get('pc', 0)  # Previous close
                
                if current_price and prev_close:
                    daily_change = ((current_price - prev_close) / prev_close) * 100
                    
                    # For monthly data, we'll use previous close as approximation
                    # (Finnhub free tier doesn't provide historical data easily)
                    month_start_price = prev_close
                    
                    shares = INVESTMENT_PER_STOCK / month_start_price
                    current_value = shares * current_price
                    profit_loss = current_value - INVESTMENT_PER_STOCK
                    
                    price_data[ticker] = {
                        'current_price': round(current_price, 2),
                        'daily_change': round(daily_change, 2),
                        'month_start_price': round(month_start_price, 2),
                        'profit_loss': round(profit_loss, 2)
                    }
        except Exception as e:
            logging.warning(f"Error fetching {ticker} from Finnhub: {e}")
            continue
    
    return price_data

def get_live_prices(tickers, force_refresh=True):
    """Fetch live prices using Alpaca (primary) and Finnhub (fallback)
    
    Args:
        tickers: List of ticker symbols
        force_refresh: Not used but kept for API compatibility
    """
    logging.info(f"Fetching prices for {len(tickers)} tickers using Alpaca/Finnhub")
    
    # Try Alpaca first (more reliable for historical data)
    price_data = get_live_prices_alpaca(tickers)
    
    # For any tickers that failed, try Finnhub
    failed_tickers = [t for t in tickers if t not in price_data]
    if failed_tickers:
        logging.info(f"Retrying {len(failed_tickers)} tickers with Finnhub")
        finnhub_data = get_live_prices_finnhub(failed_tickers)
        price_data.update(finnhub_data)
    
    logging.info(f"Successfully fetched prices for {len(price_data)}/{len(tickers)} tickers")
    return price_data

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Monthly Picks</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            padding: 20px;
        }
        h1 { color: #2196F3; }
        .info { color: #888; font-size: 12px; margin: 10px 0; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: #2c2c2c;
        }
        th, td {
            padding: 8px;
            text-align: left;
            border-bottom: 1px solid #444;
            font-size: 13px;
        }
        th {
            background: #333;
            font-weight: bold;
            position: sticky;
            top: 0;
            font-size: 12px;
        }
        tr:hover { background: #3a3a3a; }
        .error { color: #ff6b6b; padding: 20px; }
        .positive { color: #4CAF50; }
        .negative { color: #ff6b6b; }
        .refresh-note { 
            color: #888; 
            font-size: 11px; 
            margin: 5px 0; 
            font-style: italic;
        }
        .profit { color: #4CAF50; font-weight: bold; }
        .loss { color: #ff6b6b; font-weight: bold; }
        .summary-container {
            display: flex;
            gap: 20px;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        .summary-box {
            background: #2c2c2c;
            border: 2px solid #444;
            border-radius: 8px;
            padding: 20px;
            min-width: 200px;
            text-align: center;
        }
        .summary-label {
            color: #888;
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 10px;
        }
        .summary-value {
            font-size: 28px;
            font-weight: bold;
        }
        .summary-value.spent { color: #2196F3; }
        .summary-value.profit-positive { color: #4CAF50; }
        .summary-value.profit-negative { color: #ff6b6b; }
        .summary-value.roi-positive { color: #4CAF50; }
        .summary-value.roi-negative { color: #ff6b6b; }
    </style>
</head>
<body>
    <h1>📈 Monthly Picks Dashboard</h1>
    {% if error %}
        <div class="error">{{ error }}</div>
    {% else %}
        <div class="info">Loaded: {{ csv_path }}</div>
        <div class="info">Total picks: {{ total }} | Price data updated: {{ update_time }}</div>
        <div class="refresh-note">Refresh page to update live prices</div>
        
        <!-- Summary Boxes -->
        <div class="summary-container">
            <div class="summary-box">
                <div class="summary-label">Total Money Spent</div>
                <div class="summary-value spent">${{ total_spent }}</div>
            </div>
            <div class="summary-box">
                <div class="summary-label">Total Profit/Loss</div>
                <div class="summary-value {{ 'profit-positive' if total_pl >= 0 else 'profit-negative' }}">
                    ${{ '+' if total_pl >= 0 else '' }}{{ total_pl }}
                </div>
            </div>
            <div class="summary-box">
                <div class="summary-label">ROI</div>
                <div class="summary-value {{ 'roi-positive' if roi >= 0 else 'roi-negative' }}">
                    {{ '+' if roi >= 0 else '' }}{{ roi }}%
                </div>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    {% for col in columns %}
                    <th>{{ col }}</th>
                    {% endfor %}
                </tr>
            </thead>
            <tbody>
                {% for row in data %}
                <tr>
                    {% for col in columns %}
                    <td {% if col == 'daily_change' %}class="{{ 'positive' if row[col]|float > 0 else 'negative' if row[col]|float < 0 else '' }}"{% elif col == 'profit_loss' %}class="{{ 'profit' if row[col]|float > 0 else 'loss' if row[col]|float < 0 else '' }}"{% endif %}>
                        {% if col == 'daily_change' and row[col] != 'N/A' %}
                            {{ '+' if row[col]|float > 0 else '' }}{{ row[col] }}%
                        {% elif col == 'profit_loss' and row[col] != 'N/A' %}
                            ${{ '+' if row[col]|float > 0 else '' }}{{ row[col] }}
                        {% else %}
                            {{ row[col] }}
                        {% endif %}
                    </td>
                    {% endfor %}
                </tr>
                {% endfor %}
            </tbody>
        </table>
    {% endif %}
</body>
</html>
"""

@app.route('/')
def index():
    csv_path = find_latest_monthly_csv()
    
    if not csv_path:
        return render_template_string(HTML_TEMPLATE, error="No monthly picks CSV found")
    
    try:
        df = pd.read_csv(csv_path)
        
        # Add rank column (1, 2, 3, ...)
        df['rank'] = range(1, len(df) + 1)
        
        # Get live price data for all tickers
        tickers = df['ticker'].tolist() if 'ticker' in df.columns else []
        price_data = get_live_prices(tickers)
        
        # Add live price columns
        df['current_price'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('current_price', 'N/A'))
        df['daily_change'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('daily_change', 'N/A'))
        df['month_start_price'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('month_start_price', 'N/A'))
        df['profit_loss'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('profit_loss', 'N/A'))
        
        # Define a list of priority columns to ensure a clean, useful table
        priority_cols = [
            'rank', 'ticker', 'composite_score', 'price',
            'current_price', 'daily_change', 'month_start_price', 'profit_loss',
            'sma20', 'sma50', 'sma200',
            'rsi', 'macd_hist', 'rel_strength', 'beta',
            'avg_vol', 'vol_today', 'vol_surge',
            'momentum_12m', 'vol_60_ann', 'earnings_soon', 'earnings_date',
            'news_sentiment', 'options_signal'
        ]

        # Select only the priority columns that actually exist in the DataFrame
        cols = [c for c in priority_cols if c in df.columns]

        # If some priority columns are missing, add any other existing columns from the CSV
        # to the end, excluding known internal/unwanted ones.
        existing_cols = set(cols)
        other_cols = [c for c in df.columns if c not in existing_cols and c not in ['score', 'pred_rank']]
        cols.extend(other_cols)
        
        df_display = df[cols]
        
        # Calculate summary statistics
        total_spent = len(df) * INVESTMENT_PER_STOCK
        
        # Sum up all profit/loss values (exclude N/A)
        pl_values = [price_data.get(t, {}).get('profit_loss', 0) for t in tickers]
        pl_values = [v for v in pl_values if isinstance(v, (int, float))]
        total_pl = round(sum(pl_values), 2)
        
        # Calculate ROI: (total_pl / total_spent) * 100
        roi = round((total_pl / total_spent * 100), 2) if total_spent > 0 else 0
        
        return render_template_string(
            HTML_TEMPLATE,
            columns=cols,
            data=df_display.to_dict('records'),
            csv_path=csv_path,
            total=len(df),
            update_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_spent=f"{total_spent:,.2f}",
            total_pl=total_pl,
            roi=roi
        )
    except Exception as e:
        logging.exception("Error in index route")
        return render_template_string(HTML_TEMPLATE, error=f"Error: {str(e)}")

if __name__ == '__main__':
    print("Monthly Picks Dashboard starting on http://0.0.0.0:8052")
    app.run(host='0.0.0.0', port=8052, debug=False)
