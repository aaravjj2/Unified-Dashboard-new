"""
Enhanced Weekly Picks viewer with live price data and profit/loss calculation
Shows P/L based on $250 investment at week start
Run: python3 weekly_picks_flask.py
"""
from flask import Flask, render_template_string
import pandas as pd
import os
import glob
import yfinance as yf
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import logging

# Load API keys
load_dotenv('keys.env')

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Investment per stock for weekly picks
INVESTMENT_PER_STOCK = 250.0

def find_latest_weekly_csv():
    # Allow pinning a specific weekly CSV via environment for dev/testing parity
    ATTACHED = os.environ.get('ATTACHED_WEEKLY_PATH') or None
    if ATTACHED and os.path.exists(ATTACHED):
        return ATTACHED

    base_dir = os.path.dirname(__file__)
    # Search recursively to find files in subdirectories like weekly_run/
    # include the pipeline's picks_YYYYMMDD.csv naming as well as weeklypicks and picks_weekly variants
    patterns = ['models/**/picks_*.csv', 'models/**/weeklypicks*.csv', 'models/**/picks_weekly*.csv']
    candidates = []
    for pattern in patterns:
        path = os.path.join(base_dir, pattern)
        # Use recursive=True to search subdirectories
        candidates.extend(glob.glob(path, recursive=True))
    
    if not candidates:
        return None

    # Prefer files with a parseable date in the name (YYYYMMDD or MMDD)
    # This is more robust than relying on file modification time.
    import re
    from datetime import datetime

    def _parse_date_from_name(path):
        filename = os.path.basename(path)
        # Match YYYYMMDD
        m_yyyymmdd = re.search(r'(\d{8})', filename)
        if m_yyyymmdd:
            try:
                return datetime.strptime(m_yyyymmdd.group(1), '%Y%m%d').date()
            except ValueError:
                pass
        
        # Match MMDD (e.g., weeklypicks1006.csv)
        m_mmdd = re.search(r'weeklypicks(\d{4})', filename)
        if m_mmdd:
            try:
                # Assume current year, handle year-end rollover
                mmdd_str = m_mmdd.group(1)
                today = datetime.now()
                file_date = datetime.strptime(f"{today.year}{mmdd_str}", '%Y%m%d')
                # If date is in the future, assume it's from last year
                if file_date > today:
                    file_date = file_date.replace(year=today.year - 1)
                return file_date.date()
            except ValueError:
                pass
        return None

    # Prefer picks_*.csv naming (pipeline canonical), then files under models/weekly_run,
    # then by parsed date and mtime.
    def _in_weekly_run(p):
        return ('models' + os.sep + 'weekly_run') in p or '/weekly_run/' in p or '\\weekly_run\\' in p

    def _is_picks_prefix(p):
        return os.path.basename(p).lower().startswith('picks_')

    def _sort_key(p):
        # primary: is picks_ prefix, secondary: in weekly_run, tertiary: parsed date, quaternary: mtime
        parsed = _parse_date_from_name(p) or datetime.min.date()
        mtime = os.path.getmtime(p)
        return (_is_picks_prefix(p), _in_weekly_run(p), parsed, mtime)

    candidates.sort(key=_sort_key, reverse=True)
    
    # The first item in the sorted list is the best candidate
    return candidates[0]

def get_live_prices(tickers, force_refresh=True):
    """Fetch current prices, daily changes, and calculate P/L based on $250 investment at week start
    
    Args:
        force_refresh: If True, bypasses yfinance internal cache to get fresh data
    """
    price_data = {}
    try:
        # Fetch data for all tickers at once
        # Add prepost=True and auto_adjust=False to force fresh data fetch
        tickers_str = ' '.join(tickers)
        data = yf.download(tickers_str, period='5d', interval='1d', progress=False, threads=True, 
                          prepost=False, auto_adjust=True, actions=False)
        
        for ticker in tickers:
            try:
                if len(tickers) == 1:
                    ticker_data = data
                else:
                    ticker_data = data.xs(ticker, axis=1, level=1) if isinstance(data.columns, pd.MultiIndex) else data
                
                if ticker_data.empty:
                    continue
                    
                # Get most recent price
                close_prices = ticker_data['Close'].dropna()
                if len(close_prices) < 2:
                    continue
                
                current_price = close_prices.iloc[-1]
                prev_price = close_prices.iloc[-2]
                daily_change = ((current_price - prev_price) / prev_price) * 100
                
                # Get week start price (5 days ago or first available)
                week_start_price = close_prices.iloc[0]
                
                # Calculate profit/loss: $250 invested at week start
                # shares = $250 / week_start_price
                # current_value = shares * current_price
                # profit_loss = current_value - $250
                shares = INVESTMENT_PER_STOCK / week_start_price
                current_value = shares * current_price
                profit_loss = current_value - INVESTMENT_PER_STOCK
                
                price_data[ticker] = {
                    'current_price': round(current_price, 2),
                    'daily_change': round(daily_change, 2),
                    'week_start_price': round(week_start_price, 2),
                    'profit_loss': round(profit_loss, 2)
                }
            except Exception as e:
                logging.warning(f"Error fetching data for {ticker}: {e}")
                continue
    except Exception as e:
        logging.error(f"Error in batch download: {e}")
    
    return price_data

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Weekly Picks</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: #e0e0e0;
            padding: 20px;
        }
        h1 { color: #4CAF50; }
        .info { color: #888; font-size: 12px; margin: 10px 0; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: #2c2c2c;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #444;
        }
        th {
            background: #333;
            font-weight: bold;
            position: sticky;
            top: 0;
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
    <h1>📊 Weekly Picks Dashboard</h1>
    <div style="color:#FFD700;font-weight:700;margin-top:6px">DEV: Weekly picks template updated 2025-10-07 — refresh to see live prices</div>
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
    csv_path = find_latest_weekly_csv()
    
    if not csv_path:
        return render_template_string(HTML_TEMPLATE, error="No weekly picks CSV found")
    
    try:
        df = pd.read_csv(csv_path)
        
        # Limit to 20 tickers as requested
        df = df.head(20)
        
        # Add rank column (1, 2, 3, ...)
        df['rank'] = range(1, len(df) + 1)
        
        # Get live price data for tickers (force refresh on each page load)
        tickers = df['ticker'].tolist() if 'ticker' in df.columns else []
        # Prefer precomputed week-start prices if available
        weekstart_map = {}
        # Helper: try picks date first, then today, then latest file
        base_ws_pattern = os.path.join(os.path.dirname(__file__), 'data', 'weekly_weekstart_*.json')
        ws_candidates = glob.glob(base_ws_pattern)

        def _normalize_date_str(val):
            try:
                s = str(int(val)) if (not isinstance(val, str) and not pd.isna(val)) else str(val)
            except Exception:
                s = str(val)
            # If already YYYYMMDD
            if s.isdigit() and len(s) == 8:
                return s
            try:
                return pd.to_datetime(s).strftime('%Y%m%d')
            except Exception:
                return None

        candidate_ws = None
        # If picks CSV has a date column, try to use that
        if 'date' in df.columns and not df['date'].isna().all():
            pd_date = _normalize_date_str(df['date'].iloc[0])
            if pd_date:
                path = os.path.join(os.path.dirname(__file__), 'data', f'weekly_weekstart_{pd_date}.json')
                if os.path.exists(path):
                    candidate_ws = path

        # then try today's file
        if candidate_ws is None:
            today_str = datetime.now().strftime('%Y%m%d')
            path = os.path.join(os.path.dirname(__file__), 'data', f'weekly_weekstart_{today_str}.json')
            if os.path.exists(path):
                candidate_ws = path

        # finally, pick the most recent weekly_weekstart_*.json
        if candidate_ws is None and ws_candidates:
            ws_candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            candidate_ws = ws_candidates[0]

        if candidate_ws and os.path.exists(candidate_ws):
            try:
                with open(candidate_ws, 'r') as f:
                    ws_json = json.load(f)
                ws_data = ws_json.get('data', {})
                # build a mapping of ticker -> week_start_price/date
                for tk, val in ws_data.items():
                    weekstart_map[tk] = val
            except Exception:
                logging.exception('Failed loading week-start JSON')

        # fetch live current prices and daily change (no week-start calculation here)
        price_data = get_live_prices(tickers, force_refresh=True)
        
        # Add live price columns
        df['current_price'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('current_price', 'N/A'))
        df['daily_change'] = df['ticker'].map(lambda t: price_data.get(t, {}).get('daily_change', 'N/A'))
        # Use precomputed week-start if present, else fall back to live price_data's week_start
        def _map_week_start(t):
            v = weekstart_map.get(t)
            if v and v.get('week_start_price') is not None:
                return v.get('week_start_price')
            return price_data.get(t, {}).get('week_start_price', 'N/A')

        def _map_week_start_date(t):
            v = weekstart_map.get(t)
            if v and v.get('week_start_date'):
                return v.get('week_start_date')
            return 'N/A'

        df['week_start_price'] = df['ticker'].map(lambda t: _map_week_start(t))
        df['week_start_date'] = df['ticker'].map(lambda t: _map_week_start_date(t))
        df['profit_loss'] = df.apply(lambda r: (r['current_price'] - r['week_start_price']) / r['week_start_price'] * INVESTMENT_PER_STOCK if isinstance(r['current_price'], (int, float)) and isinstance(r['week_start_price'], (int, float)) and r['week_start_price'] != 0 else 'N/A', axis=1)
        
        # Select columns to display (remove score and pred_rank)
        base_cols = ['rank', 'ticker']

        # Add live price columns
        live_cols = ['current_price', 'daily_change', 'week_start_price', 'week_start_date', 'profit_loss']

        # Add all other CSV columns except score and pred_rank and the live columns
        csv_cols = [c for c in df.columns if c not in ['rank', 'ticker', 'score', 'pred_rank', 'current_price', 'daily_change', 'week_start_price', 'week_start_date', 'profit_loss']]

        cols = base_cols + live_cols + csv_cols
        
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

# AGENT 1B FIX: Add JSON API endpoint for automated testing
@app.route('/api/weekly_picks')
def api_weekly_picks():
    """JSON API endpoint for weekly picks data (for cURL/automated testing)"""
    try:
        from flask import jsonify
        
        latest_csv = find_latest_weekly_csv()
        if not latest_csv:
            return jsonify({
                'status': 'error',
                'message': 'No weekly picks CSV found',
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
            week_start_price = pdata.get('week_start_price')
            daily_change = pdata.get('daily_change')  # Not 'daily_change_pct'
            profit_loss = pdata.get('profit_loss')
            
            # Calculate ROI if we have the necessary data
            roi_pct = None
            if isinstance(profit_loss, (int, float)) and isinstance(week_start_price, (int, float)) and week_start_price != 0:
                try:
                    roi_pct = (profit_loss / INVESTMENT_PER_STOCK) * 100
                except:
                    roi_pct = None
            
            record.update({
                'Current_Price': current_price if current_price != 'N/A' else None,
                'Daily_Change': daily_change if daily_change != 'N/A' else None,
                'Week_Start_Price': week_start_price if week_start_price != 'N/A' else None,
                'Profit_Loss': profit_loss if profit_loss != 'N/A' else None,
                'ROI_Pct': round(roi_pct, 2) if roi_pct is not None else None
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
    # Default to legacy port 8053 per maintenance decision
    port = int(os.getenv('PORT', os.getenv('WEEKLY_PICKS_PORT', '8053')))
    print(f"Weekly Picks Dashboard starting on http://0.0.0.0:{port}")
    print(f"JSON API available at: http://0.0.0.0:{port}/api/weekly_picks")
    app.run(host='0.0.0.0', port=port, debug=False)
