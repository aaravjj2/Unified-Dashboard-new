"""
Minimal unified dashboard (restored): embed the existing Market Trends app
served at http://127.0.0.1:8050 in an iframe for the "Trends" tab, and provide
a simple placeholder for a future Market Forecast tab.

Usage:
  1) Start the Trends app (if using the standalone Trends server):
       python Dash/market_trends_dash.py
  2) Start this dashboard:
       python Dash/market_dashboard.py
  3) Open http://127.0.0.1:8051
"""

from dash import Dash, dcc, html, Input, Output, dash_table
import os
import time
import pandas as pd

# Load local keys.env into environment when available so the app picks up
# FINNHUB_API_KEY and ENABLE_MARKET_LOOKUP without requiring the caller to
# source the file manually before starting the process.
try:
    from src.utils.secrets import load_local_env
    try:
        load_local_env()
    except Exception:
        pass
except Exception:
    # src.utils may not be on sys.path in some standalone runs; ignore if so.
    pass

# Optional market lookup guard
_ENABLE_MARKET_LOOKUP = os.environ.get('ENABLE_MARKET_LOOKUP', '0') in ('1', 'true', 'True')

def _populate_market_fields_for_df(df, ticker_col='Ticker', force: bool = False):
    """Populate Price (live), Daily change, and Price start of month using yfinance.
    If lookups fail or yfinance not available, leaves placeholders."""
    # allow forcing lookups even if env guard is off (useful for manual refresh)
    # If explicit market lookup enabled, prefer yfinance bulk downloads.
    # Otherwise, when disabled but a FINNHUB key exists, fall back to
    # the faster Finnhub quote API via Dash.utils.price_fetch so the
    # standalone monthly tab can still show live-ish quotes.
    if not _ENABLE_MARKET_LOOKUP and not force:
        # attempt Finnhub fallback if available. Try package import first,
        # then fall back to loading the helper by file path so the tab works
        # when the project isn't installed as a package.
        fh_ok = False
        fetch_prices_batch = None
        try:
            from .utils.price_fetch import fetch_prices_batch as _fp
            fetch_prices_batch = _fp
            fh_ok = True
        except Exception:
            # try loading by file path
            try:
                import importlib.util
                import os
                pf_path = os.path.join(os.path.dirname(__file__), 'utils', 'price_fetch.py')
                if os.path.exists(pf_path):
                    spec = importlib.util.spec_from_file_location('utils.price_fetch', pf_path)
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    fetch_prices_batch = getattr(mod, 'fetch_prices_batch', None)
                    if fetch_prices_batch is not None:
                        fh_ok = True
            except Exception:
                fh_ok = False
        if not fh_ok:
            return df
    try:
        import yfinance as yf
    except Exception:
        return df
    try:
        tickers = df[ticker_col].dropna().unique().tolist()
    except Exception:
        return df
    if not tickers:
        return df
    try:
        data = yf.download(tickers, period='1mo', interval='1d', threads=False, progress=False)
    except Exception:
        # If yfinance bulk download fails but Finnhub helper is available,
        # fetch current quotes via fetch_prices_batch and populate Price (live)
        try:
            # reuse fetch_prices_batch if we previously loaded it, otherwise
            # attempt package import then file-path import (robust)
            if 'fetch_prices_batch' not in locals() or fetch_prices_batch is None:
                try:
                    from .utils.price_fetch import fetch_prices_batch as fetch_prices_batch
                except Exception:
                    import importlib.util
                    import os
                    pf_path = os.path.join(os.path.dirname(__file__), 'utils', 'price_fetch.py')
                    if os.path.exists(pf_path):
                        spec = importlib.util.spec_from_file_location('utils.price_fetch', pf_path)
                        mod = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(mod)
                        fetch_prices_batch = getattr(mod, 'fetch_prices_batch', None)
            fetched = fetch_prices_batch(tickers, parallelism=6, cache_ttl=30)
            live = []
            daily = []
            start = []
            for tk in df[ticker_col].fillna('').tolist():
                if not tk:
                    live.append('')
                    daily.append('')
                    start.append('')
                    continue
                p = fetched.get(tk, {}) if isinstance(fetched, dict) else {}
                lp = p.get('last_price')
                pc = p.get('prev_close')
                live.append(lp if lp is not None else '')
                try:
                    ch = (lp - pc) / pc if (lp is not None and pc not in (None, 0)) else ''
                except Exception:
                    ch = ''
                daily.append(ch)
                # no month-start info from quote API; leave blank
                start.append('')
            df['Price (live)'] = live
            df['Daily change'] = daily
            df['Price start of month'] = start
            return df
        except Exception:
            return df

    def _series(tk, field):
        try:
            if isinstance(data.columns, pd.MultiIndex):
                return data[field][tk].dropna()
            else:
                return data[field].dropna()
        except Exception:
            return pd.Series(dtype=float)

    daily_changes = []
    start_prices = []
    live_prices = []
    for tk in df[ticker_col].fillna('').tolist():
        if not tk:
            live_prices.append('')
            daily_changes.append('')
            start_prices.append('')
            continue
        s = _series(tk, 'Close')
        if s.empty:
            live_prices.append('')
            daily_changes.append('')
            start_prices.append('')
            continue
        today = s.iloc[-1]
        prev = s.iloc[-2] if len(s) >= 2 else pd.NA
        try:
            ch = (today - prev) / prev if pd.notna(prev) else ''
        except Exception:
            ch = ''
        start = s.iloc[0]
        live_prices.append(today)
        daily_changes.append(ch)
        start_prices.append(start)

    df['Price (live)'] = live_prices
    df['Daily change'] = daily_changes
    df['Price start of month'] = start_prices
    return df

# Defer loading heavy shared helpers and tab modules until startup to avoid
# import-time side-effects (matplotlib, heavy deps). Placeholders are used
# throughout; __main__ will attempt to import or load modules when starting
# the server interactively.
market_trends_tab = None
market_forecast_tab = None
monthly_picks_tab = None
SH = None

import importlib.util

def _load_mod(path, name=None):
    try:
        name = name or os.path.splitext(os.path.basename(path))[0]
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        return None


def _render_small_table_from_records(records, title=None, max_rows=25):
    """Render a compact DataTable from a list-of-dicts (records)."""
    try:
        if not records:
            return None
        df = pd.DataFrame(records)
        # limit rows for preview
        df = df.head(max_rows)
        cols = []
        # choose column order deterministically
        for c in df.columns.tolist():
            ctype = 'numeric' if pd.api.types.is_numeric_dtype(df[c]) else 'text'
            cols.append({'name': c, 'id': c, 'type': ctype})
        # coerce NaN -> None for Dash
        data = df.where(pd.notnull(df), None).to_dict(orient='records')
        table = dash_table.DataTable(columns=cols, data=data, page_size=min(max_rows, 25), style_table={'overflowX': 'auto'})
        children = []
        if title:
            children.append(html.H3(title))
        children.append(table)
        return html.Div(children)
    except Exception:
        return None


# Allow callbacks that reference dynamically-created component IDs (tabs may create IDs at runtime)
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server


def _run_trends_from_dashboard(dummy_arg=None, tickers=None, period='1y'):
    """Compatibility helper used by test scripts: enqueue a Trends background job and return the job id string.
    If the heavier `market_trends_dash.run_full_analysis` is available, use it; otherwise schedule a lightweight mock job.
    """
    try:
        # import shared helpers module used by tabs
        from . import _shared as SH
    except Exception:
        try:
            import _shared as SH
        except Exception:
            SH = None

    def job_target(inner_tickers, inner_period):
        try:
            # Try to call the standalone trends runner if present
            try:
                import importlib.util
                import os
                mt_path = os.path.join(os.path.dirname(__file__), 'market_trends_dash.py')
                spec = importlib.util.spec_from_file_location('market_trends_dash', mt_path)
                mt = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mt)
                if hasattr(mt, 'run_full_analysis'):
                    return mt.run_full_analysis(inner_tickers or ['AAPL'], period=inner_period or '1y')
            except Exception:
                pass
            # fallback: produce a fake quick result
            rows = []
            for t in (inner_tickers or ['AAPL']):
                rows.append({'ticker': t, 'composite_score': None, 'notes': 'mock run'})
            return {'ok': True, 'detailed': rows, 'tidy': rows}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    # schedule via SH if available, otherwise run inline and return string
    try:
        job_id = None
        if SH is not None and hasattr(SH, 'start_background_job'):
            job_id = SH.start_background_job(job_target, args=(tickers or ['AAPL'], period), job_name='run_full_analysis')
            return job_id
        else:
            res = job_target(tickers or ['AAPL'], period)
            # return a textual job id-like string for compatibility with callers that regex for job_\n
            return f"inline_result:{'ok' if res.get('ok') else 'error'}"
    except Exception:
        return None


# Top-level helper: allow the unified 'Run Full Analysis' button to enqueue
# a Trends background job. This callback uses the shared helper if present
# (SH.start_background_job) or falls back to running inline for compatibility.
try:
    @app.callback(Output('dashboard-queued-job', 'children'), Input('run-btn-unified', 'n_clicks'))
    def _unified_run(n):
        if not n:
            return ''
        try:
            # Prefer using SH if available so the job runs in background
            if 'SH' in globals() and SH is not None and hasattr(SH, 'start_background_job'):
                jid = SH.start_background_job(lambda: _run_trends_from_dashboard(None, None, '1y'), job_name='unified_run')
                return str(jid)
            else:
                # Run inline and return a short status string
                res = _run_trends_from_dashboard(None, None, '1y')
                return str(res)
        except Exception as e:
            return f'error:{e}'
except Exception:
    pass

# Minimal initial layout so `app.layout` is not None at run time. This
# provides the Tabs control and the `tab-content` container that the
# render_tab callback fills. Also include hidden placeholders used by
# various tab callbacks so registrations referencing these IDs don't
# trigger missing-component warnings. Add a small set of hidden Buttons
# and Stores for forecast-related callback IDs (e.g. `mf-run`) so the
# Dash renderer does not raise ReferenceError when callbacks reference
# `n_clicks` or similar properties on those IDs.
# Try to load the native Trends tab at startup so the Run Full Analysis
# controls are visible immediately in the unified dashboard. This is a
# best-effort attempt and will fall back to an empty tab-content if the
# module can't be loaded or is a standalone Dash app.
native_trends_children = []
# The initial children will be set by the render_tab callback on first load.

placeholder_children = [
    # Link to a tiny CSS endpoint that will be served by Flask. Using a
    # query-string cache-buster ensures the browser fetches the latest copy
    # after a server restart.
    html.Link(rel='stylesheet', href=f"/_inline_custom.css?v={int(time.time())}"),
    html.H2('Unified Market Dashboard'),
    dcc.Tabs(id='tabs', value='tab-trends', children=[
        dcc.Tab(label='Trends', value='tab-trends'),
        dcc.Tab(label='Forecast', value='tab-forecast'),
        dcc.Tab(label='Monthly Picks', value='tab-monthly-picks'),
        dcc.Tab(label='Weekly Picks', value='tab-weekly-picks'),
        dcc.Tab(label='Analysis Hub', value='tab-analysis')
    ]),
    html.Div(id='tab-content', children=native_trends_children or [], style={
        'marginTop': '12px',
        'flexGrow': 1 # Allow this container to grow and fill available space
    }),
    # A unified Run button shown in the top-level dashboard so users can
    # trigger the Trends 'Run Full Analysis' workflow even when the
    # standalone Trends module is embedded as an iframe or not mountable.
    html.Div(html.Button('Run Full Analysis', id='run-btn-unified', n_clicks=0, style={'marginTop': '8px'}), style={'marginBottom': '8px'}),
    html.Div(id='mf-results', style={'display': 'none'}),
    html.Div(id='mf-status', style={'display': 'none'}),
    html.Div(id='mf-poll', style={'display': 'none'}),
    html.Div(id='mf-job', style={'display': 'none'}),
    # Hidden interactive placeholders (buttons) used by Forecast callbacks
    # that expect an `n_clicks` property. These are hidden from the user
    # but present in the layout so Dash's renderer does not complain.
    html.Button('mf-run', id='mf-run', style={'display': 'none'}),
    html.Button('mf-download', id='mf-download', style={'display': 'none'}),
    # A small Store that can be used by forecast callbacks to persist
    # lightweight state; keeps callback registrations happy.
    dcc.Store(id='mf-store', data={}),
    # NOTE: dashboard-queued-job is defined in index.py as dcc.Store (removed duplicate html.Div)
    # Provide a DataTable placeholder for `results-table` so callbacks that
    # reference properties like `data` or `active_cell` see a compatible
    # component type even before the table is populated. Keep it hidden
    # initially; it will be replaced by the server-rendered DataTable when
    # cached results are loaded.
    html.Div(dash_table.DataTable(id='results-table', columns=[], data=[], page_size=10), style={'display': 'none'}),
    # Also provide a hidden DataTable placeholder for the client-side
    # interactive table id used by the Trends tab. This ensures callbacks
    # that reference `results-table-client.active_cell` can register at
    # startup even when the Trends tab is rendered later or embedded.
    html.Div(dash_table.DataTable(id='results-table-client', columns=[], data=[], page_size=0, style_table={'display': 'none'}), style={'display': 'none'}),
    # NOTE: current-job Store is defined in index.py (removed duplicate)
]

app.layout = html.Div(placeholder_children)

# Ensure forecast-related IDs exist as hidden placeholders so modular
# callback registrations that reference these IDs don't cause the
# renderer to report missing-input ReferenceErrors when the Forecast
# tab module is not mounted yet.
try:
    # lightweight placeholders: Stores, Divs, Intervals, Buttons, Inputs
    forecast_placeholders = [
        dcc.Store(id='mf-job', data=''),
        dcc.Interval(id='mf-poll', interval=2000, disabled=True),
        html.Div(id='mf-status', style={'display': 'none'}),
        html.Div(id='mf-results', style={'display': 'none'}),
        dcc.Download(id='mf-download'),
        html.Button('Download CSV (latest)', id='mf-download-btn', n_clicks=0, style={'display': 'none'}),
        html.Button('Run Forecast', id='mf-run', n_clicks=0, style={'display': 'none'}),
        html.Button('Ping', id='mf-ping', n_clicks=0, style={'display': 'none'}),
        html.Div(id='mf-ping-output', style={'display': 'none'}),
        html.Div(id='mf-backtest-area', style={'display': 'none'}),
        html.Button('Run Backtest', id='mf-backtest-run', n_clicks=0, style={'display': 'none'}),
        html.Button('Refresh Backtest outputs', id='mf-backtest-refresh', n_clicks=0, style={'display': 'none'}),
        html.Span(id='mf-backtest-compact-stats', style={'display': 'none'}),
        dcc.Interval(id='mf-backtest-poll', interval=3000, disabled=True),
        dcc.Store(id='mf-backtest-job', data=''),
        html.Button('mf-backtest-internal-download', id='mf-backtest-internal-download', n_clicks=0, style={'display':'none'}),
        html.Button('mf-backtest-internal-download-2', id='mf-backtest-internal-download-2', n_clicks=0, style={'display':'none'})
    ]
    # Append placeholders to the layout's hidden area
    try:
        # append at the end of the root Div children
        app.layout.children.extend(forecast_placeholders)
    except Exception:
        pass
except Exception:
    pass

# Serve model artifacts (picks/scored CSVs) from the models/ folder so the
# dashboard can link to them directly. This is intentionally minimal and
# restricted to the `models` folder under the project root.
try:
    from flask import send_from_directory, abort

    @server.route('/models/<path:filename>')
    def _serve_model_file(filename):
        base_folder = os.path.join(os.path.dirname(__file__), '..', 'models')
        full = os.path.normpath(os.path.join(base_folder, filename))
        # Prevent path traversal outside the models directory
        if not full.startswith(os.path.normpath(base_folder)) or not os.path.exists(full):
            return abort(404)
        # send as attachment so browser downloads it
        return send_from_directory(base_folder, filename, as_attachment=True)
except Exception:
    pass

try:
    from flask import Response

    @server.route('/_inline_custom.css')
    def _inline_custom_css():
        css = '''
            /* Force DataTable header background to white and header text to black */
            .dash-table-container .dash-spreadsheet .dash-spreadsheet-header .dash-cell,
            .dash-table-container .dash-header .dash-cell,
            .dash-table-container .dash-cell.column-header,
            .dash-table-container .dash-header .column-header,
            .dash-table-container table th,
            .dash-table-container .dash-spreadsheet-container th {
                background: #ffffff !important;
                color: #000000 !important;
                border-bottom: 1px solid #dcdcdc !important;
            }

            /* Ensure any filter inputs / placeholder chips inside headers use black text */
            .dash-table-container input, .dash-table-container input::placeholder,
            .dash-table-container .column-header--name, .dash-table-container .column-header--name div,
            .dash-table-container .dash-filter {
                color: #000000 !important;
                background: transparent !important;
            }

            /* Common tab implementations used by Dash (rc-tabs / dash-tabs) */
            .rc-tabs-tab, .rc-tabs-tab * , .dash-tabs .tab, .dash-tabs .tab * {
                color: #000 !important;
            }

            /* Tickers input width (user request) */
            #tickers-input { width: 600px !important; }
        '''
        # Extra aggressive header selectors to cover multiple Dash versions
        css = css + '''
        /* Additional fallbacks to cover DataTable header internals */
        .dash-table-container .dash-spreadsheet .dash-spreadsheet-header .dash-cell,
        .dash-table-container .dash-spreadsheet .dash-spreadsheet-header .dash-cell *,
        .dash-table-container .dash-spreadsheet .column-header--name, 
        .dash-table-container .dash-spreadsheet .column-header--name *,
        .dash-table-container .dash-header .column-header, 
        .dash-table-container .dash-header .column-header *,
        .dash-table-container th > div, .dash-table-container th > span {
            background: #ffffff !important;
            color: #000000 !important;
            font-weight: 600 !important;
        }
        /* Ensure any remaining header chips, sort icons or filter inputs are dark */
        .dash-table-container .filter-chip, .dash-table-container .column-header__name, .dash-table-container .dash-sort,
        .dash-table-container .column-header--sort, .dash-table-container .dash-filter, .dash-table-container .dash-filter * {
            color: #000000 !important;
            background: transparent !important;
            display: none !important; /* hide residual mini-controls to avoid duplicates */
        }

        /* High-specificity override for virtualized DataTable header row (dt-table-container__row-0)
           This targets the header when it is rendered inside the virtualized grid markup and
           forces black text and white background. */
        .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner .dt-table-container__row-0,
        .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner .dt-table-container__row-0 *,
        .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner .dt-table-container__row-0 .dash-cell-value,
        .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner .dt-table-container__row-0 td,
        .dash-table-container .dash-spreadsheet-container .dash-spreadsheet-inner .dt-table-container__row-0 th {
            color: #000000 !important;
            background: #ffffff !important;
        }
        '''
        return Response(css, mimetype='text/css')
except Exception:
    pass

# Top-level renderer function for the active tab. Do NOT register this
# as a callback at import time to avoid colliding with other app instances
# that may import this module. The function will be registered only when
# this module is executed as __main__ (standalone server).
def render_tab(tab):
    """Simplified tab renderer.

    This version is intentionally minimal and always returns a list so Dash's
    wildcard/multi-output validation is satisfied. It prefers modular tab
    layouts when present, falls back to simple cached previews where possible,
    and otherwise returns a consistent placeholder.
    """
    # normalize incoming tab value
    from flask import request
    def _req_log(msg):
        pass # logging removed for clarity

    try:
        t0 = str(tab or '')
    except Exception:
        t0 = ''
    if t0.startswith('tab-'):
        core = t0[4:]
    elif t0.startswith('tab_'):
        core = t0[4:]
    else:
        core = t0
    core = core.replace('_', '-').replace(' ', '-')
    if core in ('market-trends', 'market_trends', 'markettrends'):
        tab_key = 'tab-trends'
    elif core in ('market-forecast', 'market_forecast', 'forecast'):
        tab_key = 'tab-forecast'
    elif core in ('monthly-picks', 'monthly_picks', 'monthly'):
        tab_key = 'tab-monthly-picks'
    elif core in ('weekly-picks', 'weekly_picks', 'weekly'):
        tab_key = 'tab-weekly-picks'
    elif core in ('daily-picks', 'daily_picks', 'daily'):
        tab_key = 'tab-daily-picks'
    else:
        tab_key = 'tab-' + core if core else core

    try:
        _req_log(f"render_tab normalized={tab_key} incoming={t0}")
    except Exception:
        pass

    # Helper to safely mount a module layout if available
    def _mount_native(mod, label):
        # If the module is a simple tab module (provides layout() and
        # register_callbacks but does not itself define a Dash `app`), it is
        # safe to mount its `layout()` here so that component IDs referenced
        # by its callbacks are present in the page. If the module defines a
        # top-level `app` (i.e. it's a standalone Dash app), prefer the
        # iframe embedding path instead to avoid cross-app callback issues.
        try:
            if mod is None:
                return None
            # If the module defines an `app` attribute assume it's a full
            # Dash app and do not embed its layout here.
            if hasattr(mod, 'app'):
                return None
            if hasattr(mod, 'layout'):
                try:
                    raw = mod.layout()
                    if raw is None:
                        return None
                    # normalize to a list of children so callers can return it
                    if isinstance(raw, (list, tuple)):
                        return list(raw)
                    # wrap single component into a list so callers always get a
                    # list of children (prevents Dash wildcard/multi-output return type
                    # mismatches when a single component is returned).
                    return [raw]
                except Exception:
                    return None
        except Exception:
            return None

    # Trends
    if tab_key == 'tab-trends':
        m = globals().get('market_trends_tab')
        out = _mount_native(m, 'market_trends')
        if out is not None:
            return out
        # Prefer embedding the running Trends server via iframe rather than
        # directly embedding another Dash app's `layout()` here. Embedding a
        # monolithic module's `app.layout` can surface components whose
        # callbacks are registered on a different Dash app instance and thus
        # the buttons and interactivity won't function in this unified app.
    trends_port = os.environ.get('DASH_PORT', os.environ.get('PORT', '8050'))
    return [html.Div([html.Div(f'Trends (embedded) - ensure the standalone Trends app is running at http://127.0.0.1:{trends_port}', style={'marginBottom': '8px'}), html.Iframe(src=f'http://127.0.0.1:{trends_port}', style={'width': '100%', 'height': '800px', 'border': '1px solid #233'})])]

    # Forecast
    if tab_key == 'tab-forecast':
        out = _mount_native(globals().get('market_forecast_tab'), 'market_forecast')
        if out is not None:
            pass
    # If there is a separate Forecast server, prefer iframe embedding to
    # avoid mixing callback registrations between different Dash apps.
    if tab_key == 'tab-forecast':
        out = _mount_native(globals().get('market_forecast_tab'), 'market_forecast')
        if out is not None:
            return out
        # Prefer iframe embedding for standalone Forecast server if available
    return [html.Div([html.Div('Forecast (embedded) - run the standalone Forecast app and expose it to embed', style={'marginBottom': '8px'}), html.Iframe(src='http://127.0.0.1:5001', style={'width': '100%', 'height': '800px', 'border': '1px solid #233'})])]

    # Monthly picks
    if tab_key == 'tab-monthly-picks':
        out = _mount_native(globals().get('monthly_picks_tab'), 'monthly_picks')
        if out is not None:
            return out
        return [html.Div([html.H3('Monthly Picks'), html.P('Monthly picks tab: module not available or callbacks not registered.')])]

    # Weekly picks
    if tab_key == 'tab-weekly-picks':
        out = _mount_native(globals().get('weekly_picks_tab'), 'weekly_picks')
        if out is not None:
            return out
        # fallback simple placeholder
        return [html.Div([html.H3('Weekly Picks'), html.P('Weekly picks tab: module not available or callbacks not registered.')])]

    # Analysis Hub (Attribution + Scenario combined)
    if tab_key == 'tab-analysis':
        out = _mount_native(globals().get('analysis_tab'), 'analysis')
        if out is not None:
            return out
        return [html.Div([html.H3('Analysis Hub'), html.P('Analysis tab: module not available or callbacks not registered.')])]

    # Daily picks
    if tab_key == 'tab-daily-picks':
        out = _mount_native(globals().get('daily_picks_tab'), 'daily_picks')
        if out is not None:
            return out
        return [html.Div([html.H3('Daily Picks'), html.P('Daily picks tab: module not implemented.')])]

    return [html.Div('Unknown tab')]


if __name__ == '__main__':
    # Eagerly import all tab modules at startup. This is more robust than lazy loading.
    base = os.path.dirname(__file__)
    try:
        # Ensure a package stub exists so relative imports inside tabs work
        import sys
        import types
        if 'Dash' not in sys.modules:
            pkg = types.ModuleType('Dash')
            pkg.__path__ = [base]
            sys.modules['Dash'] = pkg

        try:
            import _shared as SH
        except Exception:
            sh_path = os.path.join(base, '_shared.py')
            SH = _load_mod(sh_path, '_shared')

        try:
            from .tabs import market_trends as market_trends_tab
        except Exception:
            mt_path = os.path.join(base, 'tabs', 'market_trends.py')
            market_trends_tab = _load_mod(mt_path, 'Dash.tabs.market_trends')

        try:
            from .tabs import market_forecast as market_forecast_tab
        except Exception:
            mf_path = os.path.join(base, 'tabs', 'market_forecast.py')
            market_forecast_tab = _load_mod(mf_path, 'Dash.tabs.market_forecast')

        try:
            from .tabs import monthly_picks as monthly_picks_tab
        except Exception:
            mp_path = os.path.join(base, 'tabs', 'monthly_picks.py')
            monthly_picks_tab = _load_mod(mp_path, 'Dash.tabs.monthly_picks')

        try:
            from .tabs import weekly_picks as weekly_picks_tab
        except Exception:
            wp_path = os.path.join(base, 'tabs', 'weekly_picks.py')
            weekly_picks_tab = _load_mod(wp_path, 'Dash.tabs.weekly_picks')

        try:
            # Prefer the richer, canonical implementation when available
            from .tabs import attribution_analysis as analysis_tab
        except Exception:
            try:
                from .tabs import analysis as analysis_tab
            except Exception:
                an_path = os.path.join(base, 'tabs', 'analysis.py')
                analysis_tab = _load_mod(an_path, 'Dash.tabs.analysis')

        try:
            # Register callbacks from modular tabs when available. Allow registration
            # even when the shared helper (SH) is not present; tabs should handle
            # a None SH gracefully if they don't need it.
            if market_trends_tab is not None and hasattr(market_trends_tab, 'register_callbacks'):
                try:
                    market_trends_tab.register_callbacks(app, SH)
                    print('Registered market_trends_tab callbacks')
                except Exception as e:
                    print('market_trends_tab.register_callbacks failed:', e)
            if market_forecast_tab is not None and hasattr(market_forecast_tab, 'register_callbacks'):
                try:
                    market_forecast_tab.register_callbacks(app, SH)
                    print('Registered market_forecast_tab callbacks')
                except Exception as e:
                    print('market_forecast_tab.register_callbacks failed:', e)
            if monthly_picks_tab is not None and hasattr(monthly_picks_tab, 'register_callbacks'):
                try:
                    monthly_picks_tab.register_callbacks(app, SH)
                    print('Registered monthly_picks_tab callbacks')
                except Exception as e:
                    print('monthly_picks_tab.register_callbacks failed:', e)
            if weekly_picks_tab is not None and hasattr(weekly_picks_tab, 'register_callbacks'):
                try:
                    weekly_picks_tab.register_callbacks(app, SH)
                    print('Registered weekly_picks_tab callbacks')
                except Exception as e:
                    print('weekly_picks_tab.register_callbacks failed:', e)
            if analysis_tab is not None and hasattr(analysis_tab, 'register_callbacks'):
                try:
                    analysis_tab.register_callbacks(app)
                    print('Registered analysis_tab callbacks')
                except Exception as e:
                    print('analysis_tab.register_callbacks failed:', e)
        except Exception:
            pass

        # Register the local render_tab callback only when running this
        # module as the standalone dashboard. When this file is imported by
        # another runner (for example the unified app), we must not register
        # callbacks that target shared Output ids like 'tab-content' to
        # avoid Duplicate callback outputs errors.
        # Only register the local render_tab callback when this module is
        # executed as the main program. When this file is imported by the
        # unified runner we must not register callbacks that target shared
        # Output ids like 'tab-content' to avoid Duplicate callback outputs.
        try:
            if __name__ == '__main__':
                app.callback(Output('tab-content', 'children'), Input('tabs', 'value'))(render_tab)
                print('Registered local render_tab callback')
            else:
                print('Skipped registering local render_tab callback (imported)')
        except Exception as _e:
            print('Failed to register local render_tab callback:', _e)

    except Exception as e:
        print('Deferred import/register step failed:', e)

    port = int(os.environ.get('MARKET_DASH_PORT', os.environ.get('PORT', '8051')))
    trends_port = os.environ.get('DASH_PORT', os.environ.get('PORT', '8050'))
    print(f'Starting Market Dashboard on http://127.0.0.1:{port} (embed expects trends app at 127.0.0.1:{trends_port})')
    try:
        app.run(port=port, debug=False)
    except Exception:
        try:
            app.run_server(port=port, debug=False)
        except Exception as e:
            print('Failed to start server:', e)
