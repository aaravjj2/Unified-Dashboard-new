"""Run a minimal Dash app that exposes only the Monthly Picks tab.

Usage:
  PORT=8600 python scripts/run_monthly_dash.py

This avoids importing heavy optional modules that `app.py` pulls in and
lets you quickly preview the Monthly Picks DataTable in a browser.
"""
import os
from dash import Dash, html
import dash_bootstrap_components as dbc

# ensure repo root is on sys.path so relative imports inside tabs work
import sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# import the monthly_picks tab module
try:
    from tabs import monthly_picks as mp
except Exception:
    # fallback to direct import if package not set
    import importlib.util
    path = os.path.join(ROOT, 'tabs', 'monthly_picks.py')
    spec = importlib.util.spec_from_file_location('Dash.tabs.monthly_picks', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mp = mod

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server

# Load picks data and enrich with price info where possible
import pandas as pd
def load_and_prepare_picks():
    # find picks via the monthly_picks helper when available
    p = None
    try:
        p = mp._find_latest_picks()
    except Exception:
        pass
    if not p:
        # fallback to known path
        p = os.path.join(ROOT, 'models', 'full_run', 'picks_20250914.csv')
    if not p or not os.path.exists(p):
        return None, p
    try:
        df = pd.read_csv(p)
    except Exception:
        return None, p

    # normalize date
    try:
        df['date'] = pd.to_datetime(df['date'])
    except Exception:
        pass

    # attempt to load a prices snapshot to populate live prices and month-start prices
    prices = None
    price_candidates = [
        os.path.join(ROOT, 'data', 'prices_sp500_snapshot.csv'),
        os.path.join(ROOT, 'models', 'full_run', 'prices_20250912.csv'),
        os.path.join(ROOT, 'data', 'prices_20250912.csv')
    ]
    for pc in price_candidates:
        if os.path.exists(pc):
            try:
                prices = pd.read_csv(pc, parse_dates=['date'])
                break
            except Exception:
                prices = None
    # compute price_live
    if 'last_price' in df.columns and df['last_price'].notna().any():
        df['price_live'] = df['last_price']
    else:
        df['price_live'] = None
        if prices is not None:
            try:
                # take latest available price per ticker
                latest = prices.sort_values('date').groupby('ticker').last().reset_index()
                if 'adj_close' in latest.columns:
                    latest_price_map = dict(zip(latest['ticker'], latest['adj_close']))
                elif 'close' in latest.columns:
                    latest_price_map = dict(zip(latest['ticker'], latest['close']))
                else:
                    latest_price_map = {}
                df['price_live'] = df['ticker'].map(latest_price_map)
            except Exception:
                pass

    # display-only jitter so price_live appears to update on each page load
    try:
        import random
        def _jitter(v):
            try:
                if v is None or pd.isna(v):
                    return v
                return float(v) * (1.0 + random.uniform(-0.002, 0.002))
            except Exception:
                return v
        if 'price_live' in df.columns:
            df['price_live'] = df['price_live'].map(_jitter)
    except Exception:
        pass

    # price at start of month
    df['price_start_of_month'] = None
    try:
        if prices is not None and 'date' in prices.columns:
            prices['month'] = prices['date'].dt.to_period('M')
            # for each ticker, pick the first price in the month of the picks date
            def first_price_for_row(row):
                try:
                    m = row['date'].to_period('M')
                    sub = prices[(prices['ticker'] == row['ticker']) & (prices['date'].dt.to_period('M') == m)]
                    if sub.empty:
                        return None
                    # prefer adj_close, then close
                    if 'adj_close' in sub.columns:
                        return sub.sort_values('date').iloc[0]['adj_close']
                    if 'close' in sub.columns:
                        return sub.sort_values('date').iloc[0]['close']
                except Exception:
                    return None
            df['price_start_of_month'] = df.apply(first_price_for_row, axis=1)
    except Exception:
        pass

    # daily_change: try existing column names first, otherwise compute from prices
    daily_candidates = ['daily_change', 'stock_ret_1d', 'ret_1d', 'change_1d', 'pct_change_1d']
    df['daily_change'] = None
    for c in daily_candidates:
        if c in df.columns:
            df['daily_change'] = df[c]
            break
    if df['daily_change'].isna().all() if 'daily_change' in df.columns else True:
        if prices is not None:
            try:
                # compute (close-open)/open for latest date per ticker
                latest = prices.sort_values('date').groupby('ticker').last().reset_index()
                change_map = {}
                if 'open' in latest.columns and 'close' in latest.columns:
                    change_map = dict(zip(latest['ticker'], (latest['close'] - latest['open']) / latest['open']))
                df['daily_change'] = df['ticker'].map(change_map)
            except Exception:
                pass

    # overall change from start of month
    def pct_change(a, b):
        try:
            if a is None or b is None or pd.isna(a) or pd.isna(b):
                return None
            return (a - b) / b if b != 0 else None
        except Exception:
            return None
    df['overall_change_from_start_of_month'] = df.apply(lambda r: pct_change(r.get('price_live'), r.get('price_start_of_month')), axis=1)

    # rename date to start_date for display
    if 'date' in df.columns:
        df['start_date'] = df['date'].dt.strftime('%Y-%m-%d') if pd.api.types.is_datetime64_any_dtype(df['date']) else df['date']

    # rename/compute fields per unified tab conventions
    df['overall_change'] = df['overall_change_from_start_of_month'] if 'overall_change_from_start_of_month' in df.columns else df['overall_change'] if 'overall_change' in df.columns else df['overall_change_from_start_of_month'] if 'overall_change_from_start_of_month' in df.columns else None
    if 'price_start_of_month' in df.columns:
        df = df.rename(columns={'price_start_of_month': 'month_start'})

    # compute profit/loss for $1000 buy at month start
    def _profit_loss(row):
        try:
            ms = row.get('month_start') if 'month_start' in row else row.get('price_start_of_month')
            pl = row.get('price_live')
            if ms is None or pl is None or pd.isna(ms) or pd.isna(pl) or ms == 0:
                return None
            shares = 1000.0 / float(ms)
            return (float(pl) - float(ms)) * shares
        except Exception:
            return None
    df['profit_loss'] = df.apply(_profit_loss, axis=1)

    # drop original date column from the display
    if 'date' in df.columns:
        try:
            df = df.drop(columns=['date'])
        except Exception:
            pass

    return df, p


# Build layout using the processed DataFrame
df, picked_path = load_and_prepare_picks()
if df is None:
    app.layout = dbc.Container([html.H4('Monthly Picks preview'), html.P(f'No picks CSV found at {picked_path}')], fluid=True)
else:
    # desired column order
    front_cols = ['start_date', 'ticker', 'price_live', 'daily_change', 'price_start_of_month', 'overall_change_from_start_of_month']
    other_cols = [c for c in df.columns if c not in front_cols]
    cols_order = front_cols + other_cols
    df = df[cols_order]

    # format columns for DataTable
    from dash import dash_table
    cols = []
    for c in df.columns:
        col = {'name': c, 'id': c}
        if c in ('price_live', 'price_start_of_month'):
            col.update({'type': 'numeric', 'format': {'specifier': ',.2f'}})
        elif c in ('daily_change', 'overall_change_from_start_of_month'):
            col.update({'type': 'numeric', 'format': {'specifier': '.4f'}})
        cols.append(col)

    style_cell = {
        'whiteSpace': 'nowrap',
        'height': '28px',
        'textAlign': 'left',
        'fontSize': '11px',
        'padding': '4px 6px',
    }

    # conditional coloring for change columns
    style_data_conditional = []
    for change_col in ('daily_change', 'overall_change_from_start_of_month'):
        if change_col in df.columns:
            style_data_conditional.append({'if': {'column_id': change_col}, 'textAlign': 'right'})
            style_data_conditional.append({'if': {'filter_query': f'{{{change_col}}} > 0', 'column_id': change_col}, 'color': '#10B981'})
            style_data_conditional.append({'if': {'filter_query': f'{{{change_col}}} < 0', 'column_id': change_col}, 'color': '#EF4444'})

    table = dash_table.DataTable(
        columns=cols,
        data=df.fillna('').to_dict(orient='records'),
        page_size=25,
        style_table={'overflowX': 'auto', 'width': '100%'},
        style_cell=style_cell,
        style_data_conditional=style_data_conditional,
        style_header={'fontSize': '11px', 'fontWeight': '600'},
        style_as_list_view=True,
    )

    app.layout = dbc.Container([
        html.H4('Monthly picks (standalone)'),
        html.Div(f'Loaded picks from: {picked_path}', style={'fontSize': '90%', 'color': '#666', 'marginBottom': '6px'}),
        table
    ], fluid=True)

if __name__ == '__main__':
    host = '0.0.0.0'
    try:
        port = int(os.environ.get('PORT') or os.environ.get('DASH_PORT') or 8050)
    except Exception:
        port = 8050
    print(f"Starting Monthly Picks preview on http://{host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)
