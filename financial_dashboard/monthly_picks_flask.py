"""
Enhanced Monthly Picks viewer - Using yfinance with cache bypass
Shows P/L based on $1000 investment at month start
Run: python3 monthly_picks_flask.py
"""
from flask import Flask, render_template_string
import pandas as pd
import os
import glob
import yfinance as yf
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging
import random
import time
import requests
import os
import math

# Load API keys
load_dotenv('keys.env')

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Investment per stock for monthly picks
INVESTMENT_PER_STOCK = 1000.0

def find_latest_monthly_csv():
    base_dir = os.path.dirname(__file__)
    patterns = ['models/full_run/picks*.csv', 'models/full_run/monthly*.csv']
    candidates = []
    for pattern in patterns:
        path = os.path.join(base_dir, pattern)
        candidates.extend(glob.glob(path, recursive=False))
    
    return max(candidates, key=os.path.getmtime) if candidates else None

def get_live_prices(tickers, force_refresh=True):
    """Fetch prices with yfinance, adding delays to avoid rate limits"""
    price_data = {}
    
    # Process in small batches to avoid rate limits
    batch_size = 5
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        
        try:
            tickers_str = ' '.join(batch)

            # Determine the start of the current month to fetch correct historical data
            today = datetime.now()
            start_of_month = today.replace(day=1)
            # To get previous close for daily_change, fetch from previous month
            # Also ensures we have enough history if today is the first trading day
            start_date = (start_of_month - timedelta(days=10)).strftime('%Y-%m-%d')
            # yfinance expects end > start; use end = today + 1 day to include today's bar
            end_date = (today + timedelta(days=1)).strftime('%Y-%m-%d')
            start_of_month_str = start_of_month.strftime('%Y-%m-%d')

            data = None
            try:
                data = yf.download(
                    tickers_str,
                    start=start_date,
                    end=end_date,
                    interval='1d',
                    progress=False,
                    group_by='ticker' if len(batch) > 1 else None,
                    prepost=False,
                    auto_adjust=True,
                    actions=False,
                    threads=False  # Disable threading to avoid rate limits
                )
            except Exception as e:
                logging.warning(f"Batch yfinance download failed for {batch}: {e}")
                data = pd.DataFrame()
            
            for ticker in batch:
                try:
                    if len(batch) == 1:
                        ticker_data = data
                    else:
                        # yfinance returns a MultiIndex where the second level is usually the ticker
                        # (see weekly_picks_flask implementation). Use level=1 to extract per-ticker frame.
                        if isinstance(data.columns, pd.MultiIndex):
                            try:
                                ticker_data = data.xs(ticker, axis=1, level=1)
                            except Exception:
                                # Try the alternative orientation
                                try:
                                    ticker_data = data.xs(ticker, axis=1, level=0)
                                except Exception:
                                    ticker_data = pd.DataFrame()
                        else:
                            ticker_data = data
                    
                    if ticker_data.empty:
                        # Try a single-ticker fallback with period='1mo'
                        try:
                            fb = yf.download(ticker, period='1mo', interval='1d', progress=False, threads=False, auto_adjust=True)
                            if not fb.empty:
                                ticker_data = fb
                        except Exception:
                            ticker_data = pd.DataFrame()
                        if ticker_data.empty:
                            logging.info(f"No data for {ticker} after fallback")
                            continue
                    
                    close_prices = ticker_data['Close'].dropna() if 'Close' in ticker_data else pd.Series()

                    # pick current/prev if available
                    current_price = None
                    prev_price = None
                    daily_change = None
                    if len(close_prices) >= 1:
                        current_price = close_prices.iloc[-1]
                        if len(close_prices) >= 2:
                            prev_price = close_prices.iloc[-2]
                            try:
                                daily_change = ((current_price - prev_price) / prev_price) * 100
                            except Exception:
                                daily_change = None

                    # Determine month start price robustly
                    # IMPORTANT: Use LAST MONTH's final closing price as baseline
                    # (not first day of current month, which would show $0 P/L on month start date)
                    month_start_price = None
                    month_start_date = None
                    month_start_source = None
                    try:
                        if not close_prices.empty:
                            # Find the last close BEFORE start_of_month (i.e., end of previous month)
                            prev_month_prices = [ (idx, v) for idx, v in zip(close_prices.index, close_prices.values) if idx.date() < start_of_month.date() ]
                            if prev_month_prices:
                                # Use last close of previous month as baseline
                                month_start_date = str(prev_month_prices[-1][0].date())
                                month_start_price = prev_month_prices[-1][1]
                                month_start_source = 'yfinance'
                                logging.info(f"{ticker}: Using prev month close {month_start_price} from {month_start_date} as baseline")
                            else:
                                # Fallback: if no previous month data, use first available close
                                month_start_date = str(close_prices.index[0].date())
                                month_start_price = close_prices.iloc[0]
                                month_start_source = 'yfinance-fallback'
                    except Exception as e:
                        logging.warning(f"{ticker}: Month start price extraction failed: {e}")
                        month_start_price = None

                    # If still missing, try a broader yfinance fetch for 2 months and repeat
                    if month_start_price is None or pd.isna(month_start_price) or month_start_price == 0:
                        try:
                            logging.info(f"Attempting extended yfinance history for {ticker}")
                            ext = yf.download(ticker, period='2mo', interval='1d', progress=False, threads=False, auto_adjust=True)
                            if not ext.empty and 'Close' in ext:
                                ext_close = ext['Close'].dropna()
                                candidates = [ (idx, v) for idx, v in zip(ext_close.index, ext_close.values) if idx.date() >= start_of_month.date() ]
                                if candidates:
                                    month_start_date = str(candidates[0][0].date())
                                    month_start_price = candidates[0][1]
                                    month_start_source = 'yfinance-extended'
                        except Exception:
                            pass

                    # If still missing, try Polygon fallback
                    if month_start_price is None or pd.isna(month_start_price) or month_start_price == 0:
                        try:
                            poly = _fallback_polygon(ticker, start_of_month_str, today.strftime('%Y-%m-%d'))
                            if poly is not None:
                                month_start_price = poly.get('close') if isinstance(poly, dict) else poly
                                month_start_source = 'polygon'
                                month_start_date = poly.get('date') if isinstance(poly, dict) else None
                        except Exception:
                            pass

                    # Then Finnhub/Alpaca as previously implemented
                    if month_start_price is None or pd.isna(month_start_price) or month_start_price == 0:
                        logging.info(f"Month start price missing for {ticker}, trying fallbacks")
                        fb = _fallback_month_start_price(ticker)
                        if fb is not None:
                            logging.info(f"Fallback month start for {ticker} = {fb}")
                            month_start_price = fb
                            month_start_source = 'fallback'
                            month_start_date = None
                        else:
                            logging.info(f"No fallback available for {ticker}")

                    # compute profit_loss if month_start_price available
                    profit_loss = 'N/A'
                    try:
                        if month_start_price is None or (isinstance(month_start_price, float) and math.isnan(month_start_price)):
                            raise Exception('no month start')
                        if current_price is None:
                            raise Exception('no current')
                        shares = INVESTMENT_PER_STOCK / month_start_price
                        current_value = shares * current_price
                        profit_loss = current_value - INVESTMENT_PER_STOCK
                    except Exception:
                        profit_loss = 'N/A'

                    price_data[ticker] = {
                        'current_price': round(current_price, 2) if current_price is not None else 'N/A',
                        'daily_change': round(daily_change, 2) if daily_change is not None else 'N/A',
                        'month_start_price': round(month_start_price, 2) if month_start_price is not None and not pd.isna(month_start_price) else 'N/A',
                        'profit_loss': round(profit_loss, 2) if isinstance(profit_loss, (int, float)) else 'N/A',
                        'month_start_source': month_start_source,
                        'month_start_date': month_start_date
                    }
                except Exception as e:
                    logging.warning(f"Error processing {ticker}: {e}")
                    continue
            
            # Small delay between batches to avoid rate limits
            if i + batch_size < len(tickers):
                time.sleep(0.2)
                
        except Exception as e:
            logging.error(f"Error downloading batch {batch}: {e}")
            continue
    
    logging.info(f"Fetched prices for {len(price_data)}/{len(tickers)} tickers")
    return price_data


def _fallback_month_start_price(ticker):
    """Attempt to fetch a month-start price from alternative APIs (Finnhub, Alpaca).
    Returns a float price or None on failure.
    """
    # 1) Try Finnhub if API key present
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    if finnhub_key:
        try:
            # Finnhub provides historical candlesticks
            url = f"https://finnhub.io/api/v1/stock/candle?symbol={ticker}&resolution=D&from={int((datetime.now()-timedelta(days=31)).timestamp())}&to={int(datetime.now().timestamp())}&token={finnhub_key}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                j = resp.json()
                if j.get('s') == 'ok' and 'c' in j and len(j['c']) > 0:
                    return float(j['c'][0])
        except Exception:
            logging.debug('Finnhub fallback failed for %s', ticker)

    # 2) Try Alpaca (market data) if credentials present
    # Keys file uses APCA_* names; check both naming conventions for compatibility
    alpaca_key = os.getenv('ALPACA_API_KEY') or os.getenv("APCA_API_KEY_ID") or os.getenv("APCA_API_KEY_ID")
    alpaca_secret = os.getenv('ALPACA_API_SECRET') or os.getenv("APCA_API_SECRET_KEY") or os.getenv("APCA_API_SECRET_KEY")
    apca_endpoint = os.getenv("APCA_ENDPOINT") or os.getenv("APCA_ENDPOINT")
    if alpaca_key and alpaca_secret:
        try:
            # Use Alpaca market data v2 aggregated bars
            from datetime import date
            start = (datetime.now() - timedelta(days=31)).strftime('%Y-%m-%d')
            end = datetime.now().strftime('%Y-%m-%d')
            headers = {'APCA-API-KEY-ID': alpaca_key, 'APCA-API-SECRET-KEY': alpaca_secret}
            api_url = f"https://data.alpaca.markets/v2/stocks/{ticker}/bars?start={start}&end={end}&timeframe=1Day&limit=100"
            r = requests.get(api_url, headers=headers, timeout=5)
            if r.status_code == 200:
                data = r.json()
                bars = data.get('bars') or []
                if len(bars) > 0:
                    # return first bar's close as month start
                    return float(bars[0].get('c'))
        except Exception:
            logging.debug('Alpaca fallback failed for %s', ticker)

    return None


def _fallback_polygon(ticker, start_date, end_date):
    """Fetch daily bars from Polygon to get month-start close. Returns dict {'date':..., 'close':...} or None."""
    poly_key = os.getenv("POLYGON_API_KEY")
    if not poly_key:
        return None
    try:
        # Polygon v2 historic aggregates
        url = f"https://api.polygon.io/v2/aggs/ticker/{ticker}/range/1/day/{start_date}/{end_date}?adjusted=true&sort=asc&limit=120&apiKey={poly_key}"
        r = requests.get(url, timeout=6)
        if r.status_code == 200:
            j = r.json()
            results = j.get('results') or []
            if results:
                first = results[0]
                # t is unix ms
                dt = datetime.utcfromtimestamp(first.get('t')/1000).date().isoformat()
                return {'date': dt, 'close': float(first.get('c'))}
    except Exception:
        logging.debug('Polygon fallback failed for %s', ticker)
    return None

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
            flex: 1;
        }
        .summary-box h3 {
            margin: 0 0 10px 0;
            color: #2196F3;
            font-size: 16px;
        }
        .summary-value {
            font-size: 24px;
            font-weight: bold;
            margin: 5px 0;
        }
    </style>
</head>
<body>
    <h1>📊 Monthly Stock Picks</h1>
    <div style="color:#FFD700;font-weight:700;margin-top:6px">DEV: Monthly picks template updated 2025-10-07 — refresh to see live prices</div>
    <div class="info">Investment per stock: $1,000 | P/L calculated from month start</div>
    
    {% if error %}
        <div class="error">{{ error }}</div>
    {% else %}
        <div class="summary-container">
            <div class="summary-box">
                <h3>📈 Total Picks</h3>
                <div class="summary-value">{{ summary.total_picks }}</div>
            </div>
            <div class="summary-box">
                <h3>💰 Total Investment</h3>
                <div class="summary-value">${{ '{:,.0f}'.format(summary.total_investment) }}</div>
            </div>
            <div class="summary-box">
                <h3>📊 Total P/L</h3>
                <div class="summary-value {% if summary.total_profit_loss >= 0 %}profit{% else %}loss{% endif %}">
                    ${{ '{:,.2f}'.format(summary.total_profit_loss) }}
                </div>
            </div>
            <div class="summary-box">
                <h3>🎯 Total ROI %</h3>
                <div class="summary-value {% if summary.roi_percentage >= 0 %}profit{% else %}loss{% endif %}">
                    {{ '{:+.2f}%'.format(summary.roi_percentage) }}
                </div>
            </div>
            <div class="summary-box">
                <h3>📈 Winners</h3>
                <div class="summary-value positive">{{ summary.winners }}</div>
            </div>
            <div class="summary-box">
                <h3>📉 Losers</h3>
                <div class="summary-value negative">{{ summary.losers }}</div>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Ticker</th>
                    <th>Current Price</th>
                    <th>Daily Change %</th>
                    <th>Month Start Price</th>
                       <th>Month Start Source</th>
                       <th>Month Start Date</th>
                    <th>Profit/Loss</th>
                </tr>
            </thead>
            <tbody>
                {% for row in picks %}
                <tr>
                    <td>{{ row.rank }}</td>
                    <td><strong>{{ row.ticker }}</strong></td>
                    <td>${{ row.current_price if row.current_price != 'N/A' else 'N/A' }}</td>
                    <td class="{% if row.daily_change != 'N/A' and row.daily_change > 0 %}positive{% elif row.daily_change != 'N/A' and row.daily_change < 0 %}negative{% endif %}">
                        {{ '{:.2f}%'.format(row.daily_change) if row.daily_change != 'N/A' else 'N/A' }}
                    </td>
                    <td>${{ row.month_start_price if row.month_start_price != 'N/A' else 'N/A' }}</td>
                        <td>{{ row.month_start_source if row.month_start_source else 'N/A' }}</td>
                        <td>{{ row.month_start_date if row.month_start_date else 'N/A' }}</td>
                    <td class="{% if row.profit_loss != 'N/A' and row.profit_loss > 0 %}profit{% elif row.profit_loss != 'N/A' and row.profit_loss < 0 %}loss{% endif %}">
                        ${{ '{:.2f}'.format(row.profit_loss) if row.profit_loss != 'N/A' else 'N/A' }}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        
        <div class="info" style="margin-top: 20px;">
            CSV file: {{ csv_file }}<br>
            Last updated: {{ timestamp }}
        </div>
    {% endif %}
</body>
</html>
"""

@app.route('/')
def index():
    try:
        csv_path = find_latest_monthly_csv()
        if not csv_path:
            return render_template_string(HTML_TEMPLATE, error="No monthly picks CSV file found")
        
        df = pd.read_csv(csv_path)
        
        if 'rank' not in df.columns:
            if 'composite_score' in df.columns:
                df = df.sort_values('composite_score', ascending=False)
            elif 'composite' in df.columns:
                df = df.sort_values('composite', ascending=False)
            df['rank'] = range(1, len(df) + 1)
        
        tickers = df['ticker'].tolist()[:20]
        live_prices = get_live_prices(tickers, force_refresh=True)
        
        picks = []
        for idx, row in df.head(20).iterrows():
            ticker = row['ticker']
            price_info = live_prices.get(ticker, {})
            
            picks.append({
                'rank': row.get('rank', idx + 1),
                'ticker': ticker,
                'current_price': price_info.get('current_price', 'N/A'),
                'daily_change': price_info.get('daily_change', 'N/A'),
                'month_start_price': price_info.get('month_start_price', 'N/A'),
                'profit_loss': price_info.get('profit_loss', 'N/A'),
                'month_start_source': price_info.get('month_start_source', 'N/A'),
                'month_start_date': price_info.get('month_start_date', 'N/A')
            })
        
        total_profit_loss = sum(p['profit_loss'] for p in picks if p['profit_loss'] != 'N/A')
        winners = sum(1 for p in picks if p['profit_loss'] != 'N/A' and p['profit_loss'] > 0)
        losers = sum(1 for p in picks if p['profit_loss'] != 'N/A' and p['profit_loss'] < 0)
        
        # Calculate ROI%
        total_investment = INVESTMENT_PER_STOCK * len(picks)
        roi_percentage = (total_profit_loss / total_investment * 100) if total_investment > 0 else 0
        
        summary = {
            'total_picks': len(picks),
            'total_investment': total_investment,
            'total_profit_loss': total_profit_loss,
            'roi_percentage': roi_percentage,
            'winners': winners,
            'losers': losers
        }
        
        return render_template_string(
            HTML_TEMPLATE,
            picks=picks,
            summary=summary,
            csv_file=os.path.basename(csv_path),
            timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            error=None
        )
    
    except Exception as e:
        logging.exception("Error in index route")
        return render_template_string(HTML_TEMPLATE, error=f"Error: {str(e)}")

# AGENT 1B FIX: Add JSON API endpoint for automated testing
@app.route('/api/monthly_picks')
def api_monthly_picks():
    """JSON API endpoint for monthly picks data (for cURL/automated testing)"""
    try:
        from flask import jsonify
        
        latest_csv = find_latest_monthly_csv()
        if not latest_csv:
            return jsonify({
                'status': 'error',
                'message': 'No monthly picks CSV found',
                'count': 0,
                'tickers': []
            }), 404
        
        df = pd.read_csv(latest_csv)
        tickers = df['Ticker'].tolist() if 'Ticker' in df.columns else df.iloc[:, 0].tolist()
        
        # Get live prices
        price_data = get_live_prices(tickers, force_refresh=True)
        
        # Merge with CSV data
        enriched_data = []
        for idx, row in df.iterrows():
            ticker = row.get('Ticker', row.iloc[0])
            pdata = price_data.get(ticker, {})
            
            record = row.to_dict()
            
            # Use correct key names from get_live_prices return structure
            current_price = pdata.get('current_price')
            month_start_price = pdata.get('month_start_price')
            daily_change = pdata.get('daily_change')  # Not 'daily_change_pct'
            profit_loss = pdata.get('profit_loss')
            
            # Calculate ROI if we have the necessary data
            roi_pct = None
            if isinstance(profit_loss, (int, float)) and isinstance(month_start_price, (int, float)) and month_start_price != 0:
                try:
                    roi_pct = (profit_loss / INVESTMENT_PER_STOCK) * 100
                except:
                    roi_pct = None
            
            record.update({
                'Current_Price': current_price if current_price != 'N/A' else None,
                'Daily_Change': daily_change if daily_change != 'N/A' else None,
                'Month_Start_Price': month_start_price if month_start_price != 'N/A' else None,
                'Profit_Loss': profit_loss if profit_loss != 'N/A' else None,
                'ROI_Pct': round(roi_pct, 2) if roi_pct is not None else None,
                'Month_Start_Source': pdata.get('month_start_source'),
                'Month_Start_Date': pdata.get('month_start_date')
            })
            
            # Clean NaN values for JSON serialization
            for key, value in record.items():
                if pd.isna(value):
                    record[key] = None
            
            enriched_data.append(record)
        
        return jsonify({
            'status': 'success',
            'count': len(enriched_data),
            'tickers': tickers,
            'data': enriched_data,
            'source_file': os.path.basename(latest_csv),
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logging.exception("Error in API endpoint")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'count': 0,
            'tickers': []
        }), 500

if __name__ == '__main__':
    # Prefer PORT environment variable so start_all.sh can control binding
    # Default to legacy port 8052 per maintenance decision
    port = int(os.getenv('PORT', os.getenv('MONTHLY_PICKS_PORT', '8052')))
    print(f"Monthly Picks Flask starting on http://0.0.0.0:{port}")
    print(f"JSON API available at: http://0.0.0.0:{port}/api/monthly_picks")
    app.run(host='0.0.0.0', port=port, debug=False)
