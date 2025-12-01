"""Monthly Picks standalone Dash app.

This module provides a small standalone Dash application that server-side
renders the latest monthly picks CSV (if available) and offers a download
endpoint. Dynamic run/poll UI was intentionally removed to avoid callback
ID collisions when this module is mounted alongside other Dash tabs.
"""

import os
from pathlib import Path

from dash import Dash, html, dash_table
from flask import send_file

import pandas as pd

# Optional market lookups (yfinance). Guarded by ENABLE_MARKET_LOOKUP env var so
# the app can run offline. If yfinance isn't installed, the code will skip lookups.
_ENABLE_MARKET_LOOKUP = os.environ.get('ENABLE_MARKET_LOOKUP', '0') in ('1', 'true', 'True')

def _populate_market_fields(disp: pd.DataFrame, tickers_col: str = 'Ticker') -> pd.DataFrame:
    """Fetch recent prices with yfinance and populate Daily change and
    Price start of month columns. If lookups fail, leaves placeholders.
    """
    if not _ENABLE_MARKET_LOOKUP:
        return disp

    try:
        import yfinance as yf
    except Exception:
        # yfinance not installed; skip lookups
        return disp

    tickers = disp[tickers_col].dropna().unique().tolist()
    if not tickers:
        return disp

    # Download 1 month of daily data for all tickers in a single call when
    # possible, then compute today's change and first-of-month price.
    try:
        # Use period=1mo and interval=1d to get the month window including today
        data = yf.download(tickers, period='1mo', interval='1d', threads=False, progress=False)
    except Exception:
        data = None

    # Helper: robustly extract a close-price series for a ticker from the
    # downloaded DataFrame. If the bulk download doesn't contain the ticker,
    # fall back to a single-ticker history call.
    def _get_series_for(tk, field='Close'):
        # try bulk data first
        try:
            if data is None:
                raise KeyError('no-bulk-data')

            # Case A: MultiIndex columns like ('Price','Close') x ticker
            if isinstance(data.columns, pd.MultiIndex):
                try:
                    # Common layout: top-level field names, second-level tickers
                    s = data[field].get(tk, pd.Series(dtype=float)).dropna()
                    if not s.empty:
                        return s
                except Exception:
                    pass
                try:
                    # Alternative layout: top-level tickers, second-level fields
                    # data.xs will select by ticker level
                    s = data.xs(tk, axis=1, level=1)[field].dropna()
                    if not s.empty:
                        return s
                except Exception:
                    pass
                try:
                    # Try inverse: select the field level first then ticker
                    s = data.xs(field, axis=1, level=0).get(tk, pd.Series(dtype=float)).dropna()
                    if not s.empty:
                        return s
                except Exception:
                    pass
                # nothing found in bulk
                raise KeyError('no-bulk-series')

            # Case B: flat columns (single-ticker download or single-column)
            if field in data.columns:
                s = data[field].dropna()
                if not s.empty:
                    return s
            # last resort: try lower-case field name
            lowf = field.lower()
            if lowf in data.columns:
                s = data[lowf].dropna()
                if not s.empty:
                    return s
            raise KeyError('no-flat-series')
        except Exception:
            # fallback: try per-ticker history (slower but more robust)
            try:
                hist = yf.Ticker(tk).history(period='1mo', interval='1d')
                if hist is None or hist.empty:
                    return pd.Series(dtype=float)
                # hist commonly has a 'Close' column
                if 'Close' in hist.columns:
                    return hist['Close'].dropna()
                # try lowercase
                if 'close' in hist.columns:
                    return hist['close'].dropna()
                return pd.Series(dtype=float)
            except Exception:
                return pd.Series(dtype=float)

    # Populate for each ticker in disp
    daily_changes = []
    start_month_prices = []
    live_prices = []
    for tk in disp[tickers_col].fillna('').tolist():
        if not tk:
            daily_changes.append('')
            start_month_prices.append('')
            live_prices.append('')
            continue
        close_s = _get_series_for(tk, 'Close')
        if close_s.empty:
            daily_changes.append('')
            start_month_prices.append('')
            live_prices.append('')
            continue

        # Today's close is the last index
        today_close = close_s.iloc[-1]
        # Yesterday/previous close
        prev_close = close_s.iloc[-2] if len(close_s) >= 2 else pd.NA
        try:
            daily_change = (today_close - prev_close) / prev_close if pd.notna(prev_close) else ''
        except Exception:
            daily_change = ''

        # Price at start of month -> first available index in the month window
        start_price = close_s.iloc[0]

        daily_changes.append(daily_change)
        start_month_prices.append(start_price)
        live_prices.append(today_close)

    disp['Daily change'] = daily_changes
    disp['Price start of month'] = start_month_prices
    disp['Price (live)'] = live_prices
    return disp


def create_app():
    app = Dash(__name__)
    # register download route
    _register_download_route(app)
    # Pre-render latest picks table (server-side) so the table appears immediately
    table_component = html.Div('No scored cache found')
    download_link = html.Div()
    try:
        path = _find_latest_scored()
        if path:
            df = pd.read_csv(path)

            # Build a display DataFrame with requested leading columns.
            disp = df.copy()

            # Rank: prefer pred_rank, fallback to pred_rank-like columns or score
            if 'pred_rank' in df.columns:
                disp['Rank'] = df['pred_rank']
            elif 'pred_rank_rank' in df.columns:
                disp['Rank'] = df['pred_rank_rank']
            else:
                disp['Rank'] = df.get('pred_rank', df.get('score', pd.NA))

            # Date and Ticker (use existing columns)
            disp['Date'] = df.get('date', '')
            disp['Ticker'] = df.get('ticker', '')

            # Price (live) from last_price if available
            disp['Price (live)'] = df.get('last_price', '')

            # Daily change and Price at start of month are not present in the
            # CSV. Add empty placeholders so the table shows those columns.
            disp['Daily change'] = ''
            disp['Price start of month'] = ''

            # Build the final ordered column list: requested leading cols first,
            # then the rest of the columns from the original file (excluding
            # duplicates of the ones we've already added).
            # Also add a Profit/Loss column computed from live price minus start
            # of month price.
            leading = ['Rank', 'Date', 'Ticker', 'Price (live)', 'Daily change', 'Price start of month', 'Profit/Loss']
            rest = [c for c in df.columns if c not in {'pred_rank', 'date', 'ticker', 'last_price'}]
            final_cols = leading + rest

            # Ensure all final columns exist in disp (create from df if needed)
            for c in final_cols:
                if c not in disp.columns:
                    disp[c] = df.get(c, '')

            # Optionally populate market lookup fields (yfinance). This is
            # guarded by ENABLE_MARKET_LOOKUP environment variable.
            disp = _populate_market_fields(disp, tickers_col='Ticker')

            # Compute Profit/Loss = Price (live) - Price start of month (numeric)
            try:
                disp['_pl_live'] = pd.to_numeric(disp.get('Price (live)', pd.Series(dtype=float)), errors='coerce')
                disp['_pl_start'] = pd.to_numeric(disp.get('Price start of month', pd.Series(dtype=float)), errors='coerce')
                disp['Profit/Loss'] = (disp['_pl_live'] - disp['_pl_start'])
                # allow the DataTable to display blanks for NaN by leaving them
            except Exception:
                disp['Profit/Loss'] = ''

            # Mark numeric columns so DataTable treats them as numbers and
            # build data with None for missing numeric values (preserve numeric
            # type so filter_query numeric comparisons work).
            numeric_cols = {'Price (live)', 'Daily change', 'Price start of month', 'Profit/Loss'}
            cols = []
            for c in final_cols:
                if c in numeric_cols:
                    cols.append({'name': c, 'id': c, 'type': 'numeric'})
                else:
                    cols.append({'name': c, 'id': c, 'type': 'text'})

            # Build DataTable data while preserving numeric types. Replace
            # NaN with None (so Dash renders blanks) rather than empty strings
            # which would coerce columns to object/string types and break
            # numeric comparisons in style_data_conditional.
            data_df = disp[final_cols].copy()
            for nc in numeric_cols.intersection(data_df.columns):
                data_df[nc] = pd.to_numeric(data_df[nc], errors='coerce')
            data = data_df.where(pd.notnull(data_df), None).to_dict(orient='records')

            # Conditional styling: color Price (live) green/red depending on
            # whether it's above/below the start-of-month price; color Daily
            # change and Profit/Loss similarly based on sign. Use both text
            # color and a subtle background so it's visible even with themes.
            style_data_conditional = [
                {
                    'if': {'filter_query': '{Price (live)} > {Price start of month}', 'column_id': 'Price (live)'} ,
                    'color': 'green',
                    'backgroundColor': '#e6ffea'
                },
                {
                    'if': {'filter_query': '{Price (live)} < {Price start of month}', 'column_id': 'Price (live)'} ,
                    'color': 'red',
                    'backgroundColor': '#ffecec'
                },
                {
                    'if': {'filter_query': '{Daily change} > 0', 'column_id': 'Daily change'},
                    'color': 'green',
                    'backgroundColor': '#e6ffea'
                },
                {
                    'if': {'filter_query': '{Daily change} < 0', 'column_id': 'Daily change'},
                    'color': 'red',
                    'backgroundColor': '#ffecec'
                },
                {
                    'if': {'filter_query': '{Profit/Loss} > 0', 'column_id': 'Profit/Loss'},
                    'color': 'green',
                    'backgroundColor': '#e6ffea'
                },
                {
                    'if': {'filter_query': '{Profit/Loss} < 0', 'column_id': 'Profit/Loss'},
                    'color': 'red',
                    'backgroundColor': '#ffecec'
                }
            ]
            table_component = dash_table.DataTable(
                columns=cols,
                data=data,
                page_size=25,
                style_data_conditional=style_data_conditional
            )
            download_link = html.A('Download latest picks CSV', href='/download_latest_picks', target='_blank')
    except Exception:
        table_component = html.Div('Error loading latest picks')

    app.layout = html.Div([
        html.Div([html.H2('Monthly Picks — Standalone')], style={'padding': '8px'}),
        html.Div([
            html.Div([
                html.Div('Monthly Picks pipeline — latest picks are shown to the right'),
            ], style={'width': '38%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '12px'}),

            html.Div([
                html.Div('Use the download link to save the latest picks.'),
            ], style={'width': '60%', 'display': 'inline-block', 'verticalAlign': 'top', 'padding': '12px'}),
        ], style={'display': 'flex'}),

        # server-side rendered table; no callbacks are registered so there are no output collisions
        html.Div(table_component, id='mp-results-area', style={'padding': '12px'}),
        html.Div(download_link, id='mp-download-area', style={'padding': '12px'}),
    ])


    # No dynamic callbacks are registered in this standalone app. The table is
    # pre-rendered server-side and placed in the layout under the
    # `mp-results-area` id. This avoids duplicate Output registrations when
    # multiple Dash modules are imported into the same process.

    return app



def _find_latest_scored():
    """Return absolute path to the latest scored_full_*.csv or picks/*.csv if available."""
    # Search both the repository root and the Dash/picks folder so the
    # standalone app can find artifacts written by other scripts.
    # base resolves to the repo root (one level up from Dash/)
    base = Path(__file__).resolve().parents[1]
    candidates = []

    # look in models/full_run under repo root
    mfr = base / 'models' / 'full_run'
    if mfr.exists():
        # Prefer picks_*.csv if available (final outputs), but include scored_full as fallback
        candidates += list(mfr.glob('picks_*.csv'))
        candidates += list(mfr.glob('scored_full_*.csv'))

    # picks/ under repo root
    picks_dir = base / 'picks'
    if picks_dir.exists():
        candidates += list(picks_dir.glob('picks_*.csv'))

    # Also consider Dash/picks (in case artifacts are saved relative to the Dash folder)
    dash_picks = Path(__file__).resolve().parent / 'picks'
    if dash_picks.exists():
        candidates += list(dash_picks.glob('picks_*.csv'))

    # Also consider Dash/models/full_run (artifacts may be written relative to the Dash folder)
    dash_mfr = Path(__file__).resolve().parent / 'models' / 'full_run'
    if dash_mfr.exists():
        candidates += list(dash_mfr.glob('picks_*.csv'))
        candidates += list(dash_mfr.glob('scored_full_*.csv'))

    if not candidates:
        return None
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return str(latest)


# add a download route to serve the latest scored CSV
def _register_download_route(app):
    server = app.server

    @server.route('/download_latest_picks')
    def _download_latest_picks():
        path = _find_latest_scored()
        if not path:
            return ('{"error":"No picks cache available"}', 404, {'Content-Type': 'application/json'})
        try:
            # send_file will set a sensible filename from the path
            return send_file(path, as_attachment=True)
        except Exception as e:
            return (f'{{"error":"Error sending file: {e}"}}', 500, {'Content-Type': 'application/json'})




if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('MONTHLY_PORT', '8060'))
    print(f'Starting Monthly Picks app on http://127.0.0.1:{port}')
    try:
        app.run(port=port, debug=False)
    except Exception:
        try:
            app.run_server(port=port, debug=False)
        except Exception as e:
            print('Failed to start server:', e)
