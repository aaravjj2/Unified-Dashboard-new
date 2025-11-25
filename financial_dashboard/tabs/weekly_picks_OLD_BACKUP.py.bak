"""Weekly Picks tab - Simplified version using robust price fetcher.

Clean implementation that uses utils.price_fetcher_weekly directly.
Replaces hundreds of lines of complex fallback logic with a single robust call.
"""

import os
import time
import threading
import traceback
import io
import sys
import logging
from dash import dcc, html, Input, Output, State, dash_table
from dash.exceptions import PreventUpdate
import _shared as SH

# Setup logger
logger = logging.getLogger(__name__)

JOBS = {}
WEEKLY_OUT_DIR = os.path.join(SH.DASH_ROOT, 'models', 'weekly_run')
ATTACHED_WEEKLY_PATH = os.environ.get('ATTACHED_WEEKLY_PATH') or None


def _start_local_job(target, args=(), kwargs=None, name=None):
    if kwargs is None:
        kwargs = {}
    jid = f"weekly_job_{int(time.time() * 1000)}"
    JOBS[jid] = {'name': name or getattr(target, '__name__', 'job'), 'status': 'queued', 'thread': None, 'result': None}

    def _runner(j):
        JOBS[j]['status'] = 'running'
        try:
            buf_out = io.StringIO()
            buf_err = io.StringIO()
            old_out, old_err = sys.stdout, sys.stderr
            try:
                sys.stdout, sys.stderr = buf_out, buf_err
                res = target(*args, **kwargs)
            finally:
                sys.stdout, sys.stderr = old_out, old_err
            JOBS[j]['result'] = res
            JOBS[j]['log'] = buf_out.getvalue() + '\n' + buf_err.getvalue()
            JOBS[j]['status'] = 'done'
        except Exception as e:
            JOBS[j]['result'] = {'ok': False, 'error': str(e), 'trace': traceback.format_exc()}
            try:
                JOBS[j]['log'] = buf_out.getvalue() + '\n' + buf_err.getvalue()
            except Exception:
                JOBS[j]['log'] = ''
            JOBS[j]['status'] = 'error'

    th = threading.Thread(target=_runner, args=(jid,), daemon=True)
    JOBS[jid]['thread'] = th
    th.start()
    return jid


def _find_latest_weekly_picks(base_dir=None):
    """Simplified CSV discovery using robust logic from weekly_picks_flask.py."""
    if ATTACHED_WEEKLY_PATH and os.path.exists(ATTACHED_WEEKLY_PATH):
        logger.info(f"Using ATTACHED_WEEKLY_PATH: {ATTACHED_WEEKLY_PATH}")
        return ATTACHED_WEEKLY_PATH

    # Use SH.DASH_ROOT if available, otherwise derive from file location
    try:
        dash_dir = SH.DASH_ROOT
        logger.info(f"Using SH.DASH_ROOT: {dash_dir}")
    except Exception as e:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        dash_dir = os.path.dirname(base_dir)
        logger.info(f"SH.DASH_ROOT not available ({e}), using derived path: {dash_dir}")

    import glob
    import re
    from datetime import datetime

    patterns = ['models/**/picks_*.csv', 'models/**/weeklypicks*.csv', 'models/**/picks_weekly*.csv']
    candidates = []
    for pattern in patterns:
        path = os.path.join(dash_dir, pattern)
        found = glob.glob(path, recursive=True)
        logger.debug(f"Pattern {pattern} found {len(found)} files")
        candidates.extend(found)
    
    if not candidates:
        logger.warning(f"No candidates found in {dash_dir} with patterns {patterns}")
        return None

    def _parse_date_from_name(path):
        filename = os.path.basename(path)
        m_yyyymmdd = re.search(r'(\d{8})', filename)
        if m_yyyymmdd:
            try: return datetime.strptime(m_yyyymmdd.group(1), '%Y%m%d').date()
            except ValueError: pass
        m_mmdd = re.search(r'weeklypicks(\d{4})', filename)
        if m_mmdd:
            try:
                mmdd_str = m_mmdd.group(1)
                today = datetime.now()
                file_date = datetime.strptime(f"{today.year}{mmdd_str}", '%Y%m%d')
                if file_date > today: file_date = file_date.replace(year=today.year - 1)
                return file_date.date()
            except ValueError: pass
        return None

    def _in_weekly_run(p):
        return ('models' + os.sep + 'weekly_run') in p or '/weekly_run/' in p or '\\weekly_run\\' in p

    def _is_picks_prefix(p):
        return os.path.basename(p).lower().startswith('picks_')

    def _sort_key(p):
        parsed = _parse_date_from_name(p) or datetime.min.date()
        mtime = os.path.getmtime(p)
        return (_is_picks_prefix(p), _in_weekly_run(p), parsed, mtime)

    candidates.sort(key=_sort_key, reverse=True)
    selected = candidates[0]
    logger.info(f"Selected weekly picks file: {selected}")
    return selected


def _load_weekly_df(path=None):
    try:
        p = path or _find_latest_weekly_picks()
        if not p:
            logger.warning("_find_latest_weekly_picks() returned None")
            return None, 'No weekly picks CSV found'
        logger.info(f"Loading weekly picks from: {p}")
    except Exception as e:
        logger.error(f"Error finding weekly picks: {e}")
        logger.error(traceback.format_exc())
        return None, f'Error finding weekly picks: {e}'
    
    try:
        import pandas as pd
        df = pd.read_csv(p)
        prov = {}
        for k in ('model_dir','stacker','universe','generated_utc'):
            if k in df.columns:
                prov[k] = df.iloc[0].get(k)
        df.attrs = getattr(df, 'attrs', {})
        df.attrs['picks_path'] = p
        if prov:
            df.attrs['provenance'] = prov
        return df, p
    except Exception as e:
        return None, str(e)


def _prepare_weekly_display_df(df):
    """Simplified version using robust utils.price_fetcher_weekly."""
    try:
        import pandas as _pd
        d = df.copy()
        
        # Use the robust weekly price fetcher
        try:
            from utils.price_fetcher_weekly import get_live_prices_weekly
            tickers = d['ticker'].tolist() if 'ticker' in d.columns else []
            price_data = get_live_prices_weekly(tickers, investment=250.0) if tickers else {}
            
            d['price_live'] = d['ticker'].map(lambda t: price_data.get(t, {}).get('current_price', 'N/A'))
            d['daily_change'] = d['ticker'].map(lambda t: price_data.get(t, {}).get('daily_change', 'N/A'))
            d['week_start'] = d['ticker'].map(lambda t: price_data.get(t, {}).get('week_start_price', 'N/A'))
            d['profit_loss'] = d['ticker'].map(lambda t: price_data.get(t, {}).get('profit_loss', 'N/A'))
        except Exception as e:
            logger.error(f"Failed to fetch live prices: {e}")
            d['price_live'] = 'N/A'
            d['daily_change'] = 'N/A'
            d['week_start'] = 'N/A'
            d['profit_loss'] = 'N/A'

        # Add Rank column
        d = d.reset_index(drop=True)
        d['Rank'] = list(range(1, len(d) + 1))
        
        # Reorder columns to match Flask viewer
        front = ['Rank', 'ticker', 'price_live', 'daily_change', 'week_start', 'profit_loss']
        rest = [c for c in d.columns if c not in front]
        cols = [c for c in front + rest if c in d.columns]
        d = d[cols]
        
        return d
    except Exception as e:
        logger.error(f"Failed to prepare display df: {e}")
        return df.copy()


def _render_metrics(df):
    try:
        import pandas as _pd
        if df is None:
            return html.Div()

        n = int(len(df))
        pl_series = None
        if 'profit_loss' in df.columns:
            try:
                pl_series = _pd.to_numeric(df['profit_loss'], errors='coerce')
            except Exception:
                pl_series = None

        overall_spend = 250.0 * n
        total_pl = float(pl_series.sum()) if (pl_series is not None) else 0.0
        roi = None
        try:
            roi = (total_pl / overall_spend) if overall_spend else None
        except Exception:
            roi = None

        def _fmt_currency(v):
            try:
                return f"${v:,.2f}"
            except Exception:
                return str(v)

        def _fmt_percent(x):
            try:
                return f"{x*100:.2f}%" if x is not None else '-'
            except Exception:
                return str(x)

        card_style = {'padding': '10px 14px', 'backgroundColor': '#082430', 'border': '1px solid rgba(255,255,255,0.05)', 'borderRadius': '6px', 'minWidth': '140px', 'textAlign': 'center'}
        label_style = {'fontSize': '12px', 'color': '#cbd5e1'}
        value_style = {'fontSize': '16px', 'fontWeight': '700', 'color': '#e6eef8'}

        spend_el = html.Div([html.Div('Overall spend', style=label_style), html.Div(_fmt_currency(overall_spend), style=value_style)], style=card_style)
        pl_color = '#10B981' if total_pl > 0 else ('#EF4444' if total_pl < 0 else '#e6eef8')
        pl_vs = value_style.copy(); pl_vs['color'] = pl_color
        pl_el = html.Div([html.Div('Total profit / loss', style=label_style), html.Div(_fmt_currency(total_pl), style=pl_vs)], style=card_style)
        roi_el = html.Div([html.Div('ROI', style=label_style), html.Div(_fmt_percent(roi), style=value_style)], style=card_style)

        return html.Div([spend_el, pl_el, roi_el], id='wp-metrics-row', style={'display': 'flex', 'gap': '12px', 'marginTop': '12px', 'alignItems': 'center'})
    except Exception:
        return html.Div()


def layout():
    return html.Div([
        html.Div([
            html.H3('Weekly picks (preview)', style={'margin': 0}),
            html.Div([
                dcc.Input(id='wp-max-tickers', value=50, type='number', className='small-input'),
                dcc.Checklist(id='wp-debug-logs', options=[{'label': 'Debug logs', 'value': 'debug'}], value=[], className='small-input'),
                html.Button('Run', id='wp-run-btn', n_clicks=0),
                html.A('Download CSV', id='wp-download-link', href='', download='weekly_picks.csv', className='btn'),
                html.Button('Refresh', id='wp-refresh-prices', n_clicks=0),
            ], className='picks-header compact'),
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center'}),
        html.Div(id='wp-status', style={'marginTop': 6}),
        html.Pre(id='wp-debug-log', style={'whiteSpace': 'pre-wrap', 'maxHeight': '300px', 'overflow': 'auto', 'backgroundColor': '#000', 'color': '#fff', 'padding': '8px', 'display': 'none'}),
        html.Hr(),
        html.Div(id='wp-standalone-table'),
        dcc.Store(id='wp-current-job', data=''),
        dcc.Loading(id='wp-loading', children=[html.Div(id='wp-results-area')], type='circle'),
    ])


def register_callbacks(app, SH=None):
    if SH is None:
        import _shared as SH

    def _demo_target(max_tickers, debug=False):
        if debug:
            print(f"DEBUG: running weekly demo target for max_tickers={max_tickers}")
        df, p = _load_weekly_df()
        if df is None:
            print('DEBUG: failed to load weekly df:', p) if debug else None
            return {'ok': False, 'error': p}
        if debug:
            try:
                print('DEBUG: sample tickers:', list(df['ticker'].head(10)))
            except Exception:
                pass
        return df

    @app.callback(Output('wp-current-job', 'data'), Input('wp-run-btn', 'n_clicks'), State('wp-max-tickers', 'value'), State('wp-debug-logs', 'value'), prevent_initial_call=True)
    def _run(n_clicks, max_tickers, debug_val):
        if not n_clicks:
            raise PreventUpdate
        debug = bool(debug_val and 'debug' in debug_val)
        if SH is not None and hasattr(SH, 'start_background_job'):
            try:
                jid = SH.start_background_job(_demo_target, args=(max_tickers, debug), job_name='weekly_picks')
            except Exception:
                jid = SH.start_background_job(_demo_target, args=(max_tickers,), job_name='weekly_picks')
        else:
            jid = _start_local_job(_demo_target, args=(max_tickers, debug), name='weekly_picks')
        return jid

    @app.callback(Output('wp-standalone-table', 'children'), Input('wp-current-job', 'data'))
    def _render(job):
        df, p = _load_weekly_df()
        if df is None:
            return [html.Div([html.H4('No weekly picks available'), html.P(p)])]
        
        disp = _prepare_weekly_display_df(df)
        
        try:
            d = disp.copy()
            records = d.fillna('').to_dict(orient='records')
            cols = []
            display_name_map = {
                'Rank': 'Rank',
                'ticker': 'Ticker',
                'price_live': 'Current Price',
                'daily_change': 'Daily Change %',
                'week_start': 'Week Start Price',
                'profit_loss': 'Profit/Loss',
            }
            for c in d.columns:
                col = {'name': display_name_map.get(c, c), 'id': c}
                if c in ('price_live', 'week_start', 'profit_loss'):
                    col.update({'type': 'numeric', 'format': {'specifier': ',.2f'}})
                elif c in ('daily_change',):
                    col.update({'type': 'numeric', 'format': {'specifier': '.4f'}})
                cols.append(col)

            style_data_conditional = [
                {'if': {'column_id': 'price_live'}, 'textAlign': 'right'},
                {'if': {'column_id': 'profit_loss'}, 'textAlign': 'right'},
                {'if': {'column_id': 'daily_change'}, 'textAlign': 'right'},
                {'if': {'filter_query': '{profit_loss} > 0', 'column_id': 'profit_loss'}, 'color': '#10B981'},
                {'if': {'filter_query': '{profit_loss} < 0', 'column_id': 'profit_loss'}, 'color': '#EF4444'},
                {'if': {'filter_query': '{daily_change} > 0', 'column_id': 'daily_change'}, 'color': '#10B981'},
                {'if': {'filter_query': '{daily_change} < 0', 'column_id': 'daily_change'}, 'color': '#EF4444'},
            ]

            table = dash_table.DataTable(
                columns=cols,
                data=records,
                page_size=25,
                style_table={'overflowX': 'auto', 'width': '100%'},
                style_cell={'whiteSpace': 'nowrap', 'height': '28px', 'textAlign': 'left', 'fontSize': '11px', 'padding': '4px 6px', 'color': '#000'},
                style_data_conditional=style_data_conditional,
                style_header={'fontSize': '11px', 'fontWeight': '600'},
                style_as_list_view=True,
            )
        except Exception:
            table = html.Div('Failed to build table')
        
        metrics = _render_metrics(disp)

        prov_children = []
        attrs = getattr(disp, 'attrs', {})
        if attrs.get('picks_path'):
            prov_children.append(html.Div(f"Showing: {os.path.basename(attrs['picks_path'])}", style={'fontSize': '12px', 'color': '#cbd5e1'}))

        prov = html.Div(prov_children, style={'display': 'flex', 'gap': '8px', 'marginTop': '8px'}) if prov_children else html.Div()

        return [html.Div([prov, table, metrics])]

    @app.callback(Output('wp-download-link', 'href'), Input('wp-current-job', 'data'))
    def _update_download(job):
        p = _find_latest_weekly_picks()
        if not p:
            return ''
        try:
            rel = os.path.relpath(p, SH.PROJECT_ROOT)
            return '/' + rel.replace('\\', '/')
        except Exception:
            return p

    @app.callback(Output('wp-status', 'children'), Output('wp-debug-log', 'style'), Output('wp-debug-log', 'children'), Input('wp-current-job', 'data'))
    def _show_job_status(job):
        if not job:
            return ('', {'display': 'none'}, '')
        st = JOBS.get(job, {})
        name = st.get('name', '')
        status = st.get('status', '')
        msg = html.Div(f"Job {name} ({job}) status: {status}")
        log_style = {'display': 'none'}
        log_text = ''
        if st and st.get('log'):
            log_style = {'display': 'block', 'whiteSpace': 'pre-wrap', 'maxHeight': '300px', 'overflow': 'auto', 'backgroundColor': '#000', 'color': '#fff', 'padding': '8px'}
            log_text = st.get('log')
        return (msg, log_style, log_text)
