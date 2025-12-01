from dash import dcc, html, Input, Output, State
import dash
import json, os, time
from datetime import datetime
import pandas as pd
import traceback

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, 'market_trends_new_error.log')

# Minimal, self-contained Market Trends module
# - Fetches prices via yfinance when needed
# - Computes a simple composite score from SPY returns and MA gap
# - Writes outputs to outputs/market_trends/regime_pred_{date}.json

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'output', 'market_trends')
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _find_latest_valid_output():
    """Return (path, data) for the most recent JSON file under OUTPUT_DIR that can be parsed.
    If none found, return (None, None)."""
    files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.startswith('regime_pred_') and f.endswith('.json')])
    if not files:
        return None, None
    # iterate from newest to oldest and return first that parses
    for fname in reversed(files):
        path = os.path.join(OUTPUT_DIR, fname)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return path, data
        except Exception as e:
            # log and continue to previous file
            try:
                tb = traceback.format_exc()
                with open(LOG_PATH, 'a', encoding='utf-8') as lf:
                    lf.write(f"[{datetime.utcnow().isoformat()}] Skipping invalid output {path}: {e}\n")
                    lf.write(tb + "\n\n")
            except Exception:
                pass
            continue
    return None, None


def get_latest_recs():
    """Return (path, recs) where recs is the list used for the table (or (None, None))."""
    path, data = _find_latest_valid_output()
    if not path or not data:
        return None, None
    recs = data.get('detailed') or data.get('tidy')
    if not recs and isinstance(data, dict):
        recs = [data]
    if not recs or not isinstance(recs, list):
        return path, []
    return path, recs


def make_page_from_recs(recs, page_current, page_size):
    start = int(page_current) * int(page_size)
    end = start + int(page_size)
    page = recs[start:end]
    def sanitize_row(r):
        out = {}
        for k,v in r.items():
            try:
                if isinstance(v, (dict, list)):
                    out[k] = json.dumps(v, default=str)
                else:
                    out[k] = v
            except Exception:
                out[k] = str(v)
        return out
    page_s = [sanitize_row(r) for r in page]
    cols = [{ 'name': c, 'id': c } for c in list(page_s[0].keys())] if page_s else []
    return page_s, cols

layout = html.Div([
    html.H3('Market Trends (New)'),
    html.Div([
        html.Label('Tickers (comma separated)'),
        dcc.Textarea(id='mt-tickers', value='SPY', style={'width': '100%', 'minWidth': '320px', 'maxWidth': '95vw', 'resize': 'vertical'}, rows=2),
    ], style={'marginBottom': '8px'}),
    html.Div([html.Button('Compute Now', id='mt-compute', n_clicks=0), html.Button('Refresh from disk', id='mt-refresh', n_clicks=0, style={'marginLeft':'8px'}), html.Button('Load Table', id='mt-load-table', n_clicks=0, style={'marginLeft':'8px'})], style={'marginBottom':'8px'}),
    html.Div(id='mt-status'),
    dcc.Loading(id='mt-loading', children=[html.Div(id='mt-output')], type='circle'),
    dcc.Store(id='mt-last-out', data=None)
    ,dcc.Store(id='mt-table-meta', data=None)
    ,
    # Results table (server-side pagination)
    dash.dash_table.DataTable(
        id='mt-results-table',
        columns=[],
        data=[],
        page_current=0,
        page_size=25,
        page_action='custom',
        style_table={'overflowX':'auto','maxWidth':'95vw'},
        virtualization=True,
        style_cell={'whiteSpace': 'nowrap', 'textAlign': 'left', 'padding':'4px 6px','fontSize':'11px'},
    )
    ,
    # Modal container used by callbacks when showing details
    html.Div(id='detail-modal', style={'display':'none'}, children=[
        html.Div(id='modal-content')
    ])
])


def register_callbacks(app):
    @app.callback(Output('mt-status', 'children'), Output('mt-output','children'), Output('mt-last-out','data'),
                  Input('mt-compute','n_clicks'), Input('mt-refresh','n_clicks'),
                  State('mt-tickers','value'))
    def compute_or_load(n_compute, n_refresh, tickers_value):
        try:
            ctx = dash.callback_context
            triggered = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else None
            if triggered == 'mt-compute':
                # run compute
                try:
                    # prefer absolute import when running as script
                    from pipelines.compute_market_trends import compute_and_write
                except Exception:
                    import importlib
                    try:
                        compute_mod = importlib.import_module('pipelines.compute_market_trends')
                        compute_and_write = getattr(compute_mod, 'compute_and_write')
                    except Exception as e:
                        tb = traceback.format_exc()
                        with open(LOG_PATH, 'a', encoding='utf-8') as lf:
                            lf.write(f"[{datetime.utcnow().isoformat()}] Import error in compute: {e}\n")
                            lf.write(tb + "\n\n")
                        return f'Failed to import compute module: {e}', '', None
                try:
                    # parse tickers from textarea (comma separated)
                    tickers = None
                    try:
                        if tickers_value:
                            tickers = [t.strip().upper() for t in str(tickers_value).split(',') if t.strip()]
                    except Exception:
                        tickers = None
                    path = compute_and_write(tickers=tickers) if 'tickers' in compute_and_write.__code__.co_varnames else compute_and_write()
                except Exception as e:
                    tb = traceback.format_exc()
                    with open(LOG_PATH, 'a', encoding='utf-8') as lf:
                        lf.write(f"[{datetime.utcnow().isoformat()}] Exception running compute_and_write: {e}\n")
                        lf.write(tb + "\n\n")
                    return f'Compute failed: {e}', '', None

                try:
                    with open(path,'r',encoding='utf-8') as f:
                        data = json.load(f)
                except Exception as e:
                    tb = traceback.format_exc()
                    with open(LOG_PATH, 'a', encoding='utf-8') as lf:
                        lf.write(f"[{datetime.utcnow().isoformat()}] Failed to read output {path}: {e}\n")
                        lf.write(tb + "\n\n")
                    return f'Compute finished but failed to read {path}: {e}', '', None
                return f'Computed at {datetime.utcnow().isoformat()} UTC', html.Pre(json.dumps(data, indent=2)[:10000]), data
            else:
                # refresh
                # find latest valid JSON file
                path, data = _find_latest_valid_output()
                if not path:
                    return 'No valid outputs found', '', None
                fname = os.path.basename(path)
                return f'Loaded {fname}', html.Pre(json.dumps(data, indent=2)[:10000]), data
        except Exception as e:
            tb = traceback.format_exc()
            try:
                with open(LOG_PATH, 'a', encoding='utf-8') as lf:
                    lf.write(f"[{datetime.utcnow().isoformat()}] Exception in compute_or_load: {e}\n")
                    lf.write(tb + "\n\n")
            except Exception:
                pass
            return 'Internal server error (see server log)', '', None

    @app.callback(
        Output('mt-table-meta','data'),
        Input('mt-load-table','n_clicks'),
        State('mt-last-out','data')
    )
    def prepare_table_meta(n_load, last_out):
        # return a dict {'path': path, 'total': total} or None
        try:
            # find latest valid JSON file
            path, data = _find_latest_valid_output()
            if not path:
                return None
            # data may already be a dict parsed by helper
            if data is None:
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception as e:
                    tb = traceback.format_exc()
                    with open(LOG_PATH, 'a', encoding='utf-8') as lf:
                        lf.write(f"[{datetime.utcnow().isoformat()}] prepare_table_meta failed reading {path}: {e}\n")
                        lf.write(tb + "\n\n")
                    return None
            recs = data.get('detailed') or data.get('tidy')
            if not recs and isinstance(data, dict):
                recs = [data]
            if not recs or not isinstance(recs, list):
                return {'path': path, 'total': 0}
            return {'path': path, 'total': len(recs)}
        except Exception as e:
            tb = traceback.format_exc()
            with open(LOG_PATH, 'a', encoding='utf-8') as lf:
                lf.write(f"[{datetime.utcnow().isoformat()}] prepare_table_meta error: {e}\n")
                lf.write(tb + "\n\n")
            return None

    @app.callback(
        Output('mt-status','children'),
        Input('mt-table-meta','data')
    )
    def prepare_table_status(meta):
        try:
            if not meta:
                return 'No outputs found'
            # meta may be a list (wrapped) or a dict
            if isinstance(meta, list) and meta:
                m = meta[0]
            else:
                m = meta
            return f"Prepared table: {m.get('total',0)} rows from {os.path.basename(m.get('path',''))}"
        except Exception as e:
            with open(LOG_PATH, 'a', encoding='utf-8') as lf:
                lf.write(f"[{datetime.utcnow().isoformat()}] prepare_table_status error: {e}\n")
            return 'Error preparing table'

    @app.callback(
        Output('mt-results-table','data'),
        Output('mt-results-table','columns'),
        Input('mt-load-table','n_clicks'),
        State('mt-last-out','data')
    )
    def load_table_direct(n_clicks, last_out):
        """Directly prepare first page of results and populate the DataTable when user clicks 'Load Table'."""
        try:
            path, recs = get_latest_recs()
            if not recs:
                return [], []
            page_s, cols = make_page_from_recs(recs, 0, 25)
            return page_s, cols
        except Exception as e:
            tb = traceback.format_exc()
            with open(LOG_PATH, 'a', encoding='utf-8') as lf:
                lf.write(f"[{datetime.utcnow().isoformat()}] load_table_direct error: {e}\n")
                lf.write(tb + "\n\n")
            return [], []

    # Row inspect -> open modal with chart
    @app.callback(
        Output('detail-modal', 'style'),
        Output('modal-content', 'children'),
        Input('mt-results-table', 'active_cell'),
        Input('mt-results-table', 'data'),
        Input('mt-last-out', 'data'),
        allow_duplicate=True
    )
    def open_modal(active_cell, rows, last_out):
            try:
                if not active_cell or not rows:
                    return {'display': 'none'}, ''
                row_idx = active_cell.get('row')
                row = rows[row_idx]
                ticker = row.get('ticker') or row.get('Ticker') or row.get('symbol')
                # try to find prices for ticker in last_out or on disk
                prices = None
                try:
                    if last_out and isinstance(last_out, dict):
                        p = last_out.get('prices') or {}
                        prices = p.get(ticker)
                except Exception:
                    prices = None

                # fallback: try loads latest file prices
                if prices is None:
                    try:
                        from .market_trends_helper import load_cached_results_from_outputs
                        out = load_cached_results_from_outputs()
                        if out and isinstance(out, dict):
                            prices = out.get('prices', {}).get(ticker)
                    except Exception:
                        prices = None

                chart = None
                try:
                    from .market_trends_helper import build_price_figure
                    chart = build_price_figure(prices, title=f"{ticker} - Price")
                except Exception:
                    chart = None

                content = [html.H3(f"Details: {ticker}"), html.Div([html.Pre(str(row))])]
                if chart is not None:
                    content.append(html.Div([dcc.Graph(figure=chart)]))
                return {'display': 'block', 'position': 'fixed', 'left': '10%', 'top': '10%', 'width': '80%', 'height': '80%', 'backgroundColor': 'white', 'border': '1px solid #ccc', 'padding': '10px', 'overflow': 'auto', 'zIndex': 1000}, content
            except Exception:
                return {'display': 'none'}, ''

    @app.callback(
        Output('mt-results-table','data'),
        Output('mt-results-table','columns'),
        Input('mt-results-table','page_current'),
        Input('mt-results-table','page_size'),
        Input('mt-table-meta','data'),
    )
    def serve_table_page(page_current, page_size, meta):
            try:
                if not meta or not isinstance(meta, dict) or not meta.get('path'):
                    return [], []
                path = meta.get('path')
                try:
                    with open(path,'r',encoding='utf-8') as f:
                        payload = json.load(f)
                except Exception:
                    # fallback: try to find a valid output instead
                    path2, payload = _find_latest_valid_output()
                    if not path2:
                        return [], []
                    path = path2
                recs = payload.get('detailed') or payload.get('tidy')
                if not recs and isinstance(payload, dict):
                    recs = [payload]
                if not recs or not isinstance(recs, list):
                    return [], []
                start = int(page_current) * int(page_size)
                end = start + int(page_size)
                page = recs[start:end]
                # sanitize nested types
                def sanitize_row(r):
                    out = {}
                    for k,v in r.items():
                        try:
                            if isinstance(v, (dict, list)):
                                out[k] = json.dumps(v, default=str)
                            else:
                                out[k] = v
                        except Exception:
                            out[k] = str(v)
                    return out
                page_s = [sanitize_row(r) for r in page]
                cols = []
                if page_s:
                    cols = [{ 'name': c, 'id': c } for c in list(page_s[0].keys())]
                return page_s, cols
            except Exception as e:
                tb = traceback.format_exc()
                with open(LOG_PATH, 'a', encoding='utf-8') as lf:
                    lf.write(f"[{datetime.utcnow().isoformat()}] serve_table_page error: {e}\n")
                    lf.write(tb + "\n\n")
                return [], []

