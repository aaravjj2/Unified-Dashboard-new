"""Monthly Picks tab - minimal clean implementation.

This is a compact, single-purpose module that:
- finds the latest picks_YYYYMMDD.csv
- loads and trims the CSV
- enriches with price data from utils.price_fetcher.get_live_prices
- returns a Dash layout and callback registration matching weekly behavior

Keep imports small at module load time so importing the module is cheap.
"""

import os
import glob
import re
from datetime import datetime
import logging
import pandas as pd
from dash import dcc, html, Input, Output, dash_table

logger = logging.getLogger(__name__)

INVESTMENT_PER_STOCK = 1000.0


def _find_latest_monthly_picks():
    attached = os.environ.get('ATTACHED_MONTHLY_PATH')
    if attached and os.path.exists(attached):
        return attached

    root = os.getcwd()
    patterns = [
        os.path.join(root, 'models', 'full_run', 'picks_*.csv'),
        os.path.join(root, 'picks', 'picks_*.csv'),
    ]
    candidates = []
    for p in patterns:
        candidates.extend(glob.glob(p))

    parent = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    candidates.extend(glob.glob(os.path.join(parent, 'models', 'full_run', 'picks_*.csv')))

    if not candidates:
        return None

    def _key(p):
        m = re.search(r'(20\d{6})', os.path.basename(p))
        if m:
            try:
                return datetime.strptime(m.group(1), '%Y%m%d')
            except Exception:
                pass
        return datetime.fromtimestamp(os.path.getmtime(p))

    candidates.sort(key=_key, reverse=True)
    return candidates[0]


def _load_and_enrich_picks():
    path = _find_latest_monthly_picks()
    if not path:
        return None, 'No monthly picks CSV found', None

    df = pd.read_csv(path)
    if 'rank' not in df.columns:
        df.insert(0, 'rank', range(1, len(df) + 1))

    df = df.head(200)
    tickers = df['ticker'].tolist() if 'ticker' in df.columns else []

    try:
        from utils.price_fetcher import get_live_prices
        price_map = get_live_prices(tickers, investment=INVESTMENT_PER_STOCK)
    except Exception:
        price_map = {}

    df['current_price'] = df['ticker'].map(lambda t: price_map.get(t, {}).get('current_price', 'N/A'))
    df['daily_change'] = df['ticker'].map(lambda t: price_map.get(t, {}).get('daily_change', 'N/A'))
    df['month_start_price'] = df['ticker'].map(lambda t: price_map.get(t, {}).get('month_start_price', 'N/A'))
    df['profit_loss'] = df['ticker'].map(lambda t: price_map.get(t, {}).get('profit_loss', 'N/A'))

    display_cols = ['rank', 'ticker', 'current_price', 'daily_change', 'month_start_price', 'profit_loss']
    rest = [c for c in df.columns if c not in display_cols]
    df = df[display_cols + rest]

    total = len(tickers)
    total_investment = total * INVESTMENT_PER_STOCK
    total_pl = 0.0
    for t in tickers:
        pl = price_map.get(t, {}).get('profit_loss') if price_map else None
        try:
            if pl is not None:
                total_pl += float(pl)
        except Exception:
            continue

    summary = {
        'total': total,
        'total_investment': f"{total_investment:,.0f}",
        'total_pl': f"{total_pl:+,.2f}",
        'csv_path': path,
        'update_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

    return df, None, summary


def _fmt_cell(col, v):
    if v is None or v == 'N/A':
        return 'N/A'
    try:
        if col == 'daily_change':
            val = float(v)
            return f"+{val:.2f}%" if val > 0 else f"{val:.2f}%"
        if col == 'profit_loss':
            val = float(v)
            return f"{val:+,.2f}"
        if 'price' in col or 'current' in col:
            val = float(v)
            return f"${val:.2f}"
        return v
    except Exception:
        return v


def layout():
    return html.Div([
        html.H1("📊 Monthly Stock Picks", style={'color': '#2196F3'}),
        html.Button("🔄 Refresh Prices", id='mp-refresh-btn', n_clicks=0),
        html.Div(id='mp-content'),
        dcc.Store(id='mp-data-store'),
        dcc.Store(id='mp-page-load-trigger', data=0),
    ], style={'padding': '18px'})


def register_callbacks(app, SH=None):
    @app.callback(
        Output('mp-content', 'children'),
        Output('mp-data-store', 'data'),
        Input('mp-refresh-btn', 'n_clicks'),
        Input('mp-page-load-trigger', 'data')
    )
    def _reload(n_clicks, page_load):
        df, error, summary = _load_and_enrich_picks()
        if error:
            return html.Div(error, style={'color': '#ff6b6b'}), None

        formatted = df.copy()
        for col in ['daily_change', 'profit_loss', 'current_price', 'month_start_price']:
            if col in formatted.columns:
                formatted[col] = formatted[col].apply(lambda v, c=col: _fmt_cell(c, v))

        cols = [{"name": c, "id": c} for c in formatted.columns]
        table = dash_table.DataTable(data=formatted.to_dict('records'), columns=cols, page_size=50, style_table={'overflowX': 'auto'})
        info = html.Div([html.Div(f"Loaded: {summary['csv_path']}"), html.Div(f"Total: {summary['total']} | Updated: {summary['update_time']}")], style={'marginBottom': '8px'})
        return html.Div([info, table]), formatted.to_dict('records')
