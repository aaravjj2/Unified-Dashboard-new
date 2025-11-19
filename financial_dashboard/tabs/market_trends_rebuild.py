from dash import dcc, html, Input, Output, State, dash_table, callback_context
from dash.exceptions import PreventUpdate
import threading
from datetime import datetime
import pandas as pd
import json, time, uuid, os
try:
    import numpy as _np
except Exception:
    _np = None

# Minimal rebuild scaffold for Market Trends
# Purpose: provide a safe, incremental implementation that mirrors the
# original `tabs/market_trends.py` but is easier to iterate on.

SH = None
# Background jobs started by this rebuild module when SH isn't provided
BACKGROUND_JOBS = {}

# Simple logger
import logging
logger = logging.getLogger(__name__)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s'))
    logger.addHandler(h)
    logger.setLevel(logging.DEBUG)


def layout(is_tab=True):
    """Return the Trends layout. When is_tab=False this can be used as a
    standalone app layout (the unified dashboard will prefer embedding the
    native layout via the `render_tab` logic).
    """
    initial_results_children = html.Div([html.H4('No results yet')], style={'width': '100%', 'overflowX': 'auto'})

    # Hidden placeholder DataTable so callbacks referencing
    # 'results-table-client' can register before interactive table exists.
    placeholder_table = dash_table.DataTable(
        id='results-table-client',
        columns=[],
        data=[],
        page_size=0,
        style_table={'display': 'none'}
    )

    controls = html.Div([
        html.Label('Tickers (comma separated)'),
        dcc.Textarea(id='tickers-input', value='AAPL,MSFT,GOOGL', style={'width': '100%', 'minWidth': '480px'}),
        html.Button('Run Full Analysis', id='run-btn', n_clicks=0, style={'marginLeft': '8px'}),
        html.Label('Period'), dcc.Input(id='period-input', value='1y', type='text', style={'width': '120px'}),
        dcc.Checklist(id='analysis-options', options=[{'label':'Include options enrichment','value':'options'},{'label':'Include news enrichment','value':'news'},{'label':'Use cache only','value':'cache'}], value=['options','news'])
    ], style={'display': 'flex', 'gap': '8px', 'alignItems': 'center'})

    return html.Div([
        html.H3('Market Trends (rebuild)'),
        controls,
    dcc.Store(id='last-cached-rebuild', data=None),
    dcc.Store(id='rebuild-current-job', data=''),
    # Hidden trigger used by the original implementation; present here so
    # callbacks that reference it can register without client-side errors.
    html.Button(id='refresh-cached', n_clicks=0, style={'display': 'none'}),
    dcc.Interval(id='rebuild-poll-interval', interval=2000, disabled=True),
    html.Div(id='rebuild-results-area', children=initial_results_children),
    placeholder_table,
    html.Div(id='detail-modal', style={'display': 'none'}, children=[html.Button('Close', id='close-modal', n_clicks=0), html.Div(id='modal-content')])
    ])



def register_callbacks(app, sh=None, shared=None):
    """Register a minimal set of callbacks. Accepts SH via positional or
    keyword argument and sets module-level SH for helper usage.
    """
    global SH
    if sh is not None:
        SH = sh
    elif shared is not None:
        SH = shared
    
    # Helper: render a list-of-records as a DataTable and return container
    def _render_table_from_records(recs):
        if not recs:
            return html.Div('No records to display.'), None
        # Ensure rows are dicts
        rows = [r if isinstance(r, dict) else dict(r) for r in recs]
        # Add inspect and row id
        for i, r in enumerate(rows):
            r.setdefault('_inspect', 'Inspect')
            r.setdefault('_row_id', i)
        keys = list(rows[0].keys())
        cols = [{'name': c, 'id': c} for c in keys]
        # style similar to original: readable and force black text
        style_cell = {
            'whiteSpace': 'nowrap',
            'textAlign': 'left',
            'fontSize': '11px',
            'padding': '4px 6px',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'minWidth': '60px',
            'width': 'auto',
            'lineHeight': '14px',
            'maxHeight': '36px',
            'height': '32px'
        }
        table = dash_table.DataTable(
            id='results-table-client',
            columns=cols,
            data=rows,
            page_size=25,
            sort_action='native',
            filter_action='native',
            style_table={'overflowX': 'auto'},
            style_cell=style_cell,
            style_as_list_view=True
        )
        return html.Div([html.H4('Results'), table]), table

    def _render_brief_section(last):
        if not last:
            return html.Div()
        parts = []
        brief_text = last.get('brief_text') if isinstance(last, dict) else None
        if brief_text:
            parts.append(html.Div(brief_text, style={'whiteSpace': 'pre-wrap'}))
        brief_json = last.get('brief_json') if isinstance(last, dict) else None
        if brief_json:
            try:
                parts.append(html.Pre(json.dumps(brief_json, indent=2)))
            except Exception:
                parts.append(html.Div(str(brief_json)))
        return html.Div(parts, style={'padding': '6px', 'backgroundColor': '#f7fafc', 'border': '1px solid #eee'})

    @app.callback(
    Output('rebuild-results-area', 'children'),
    Output('last-cached-rebuild', 'data'),
        Output('rebuild-current-job', 'data'),
            Output('rebuild-poll-interval', 'disabled'),
        Input('run-btn', 'n_clicks'),
        Input('refresh-cached', 'n_clicks'),
        Input('rebuild-poll-interval', 'n_intervals'),
        State('tickers-input', 'value'),
        State('period-input', 'value'),
        State('analysis-options', 'value'),
    State('rebuild-current-job', 'data')
    )
    def show_cached_or_run(n_clicks, refresh_clicks, n_intervals, tickers_value, period_value, analysis_opts, rebuild_current_job):
        triggered = callback_context.triggered[0]['prop_id'].split('.')[0] if callback_context.triggered else None
        # Debug: log invocation so we can trace client->server callback activity
        try:
            logger.debug('show_cached_or_run called: n_clicks=%s refresh_clicks=%s triggered=%s', n_clicks, refresh_clicks, triggered)
        except Exception:
            pass
        # On initial load (no trigger) try to show cached results if available.
        if triggered is None:
            last = None
            try:
                if SH is not None and hasattr(SH, 'RESULTS_CACHE'):
                    last = SH.RESULTS_CACHE.get('results')
            except Exception:
                last = None
            if not last:
                last = load_last_cached_results()
            if last:
                recs = last.get('detailed') or last.get('tidy') or []
                children, table = _render_table_from_records(recs)
                brief = _render_brief_section(last)
                # return all four outputs: children, last-cached, current-job, poll-disabled
                return html.Div([brief, html.H4('Loaded cached results'), children]), _sanitize_for_store(last), '', True
            # no cached data — leave as-is
            return html.Div('No cached results available.'), None, '', True

        # Polling path: handle periodic checks for background job
        if triggered == 'rebuild-poll-interval':
            # Poll either SH.JOBS (if SH provided) or local BACKGROUND_JOBS
            if not rebuild_current_job:
                # nothing to poll
                raise PreventUpdate
            try:
                if SH is not None and hasattr(SH, 'JOBS'):
                    job = SH.JOBS.get(rebuild_current_job)
                    source = 'SH'
                else:
                    job = BACKGROUND_JOBS.get(rebuild_current_job)
                    source = 'local'
                if not job:
                    return html.Div(f'Unknown job {rebuild_current_job} ({source})'), None, '', True

                if source == 'local':
                    th = job.get('thread')
                    if th and th.is_alive():
                        return html.Div(f'Job {rebuild_current_job}: running (background)'), None, rebuild_current_job, False
                    r = job.get('result')
                    if not r:
                        return html.Div(f'Job {rebuild_current_job} finished but no result'), None, '', True
                    if not r.get('ok'):
                        return html.Pre(json.dumps(r, indent=2)), None, '', True
                    recs = r.get('detailed') or r.get('tidy') or []
                    if recs:
                        children, table = _render_table_from_records(recs)
                        brief = _render_brief_section(r)
                        try:
                            BACKGROUND_JOBS.pop(rebuild_current_job, None)
                        except Exception:
                            pass
                        return html.Div([brief, html.H4('Results'), children]), _sanitize_for_store(r), '', True
                    return html.Div('Job finished but no detailed results'), None, '', True

                # SH-sourced job
                status = job.get('status')
                if status in ('queued', 'running'):
                    return html.Div(f'Job {rebuild_current_job}: {status}'), None, rebuild_current_job, False
                if status == 'error':
                    return html.Div(f"Job {rebuild_current_job} failed: {job.get('result') or job.get('result')}") , None, '', True
                last = SH.RESULTS_CACHE.get('results')
                if last:
                    recs = last.get('detailed') or last.get('tidy') or []
                    children, table = _render_table_from_records(recs)
                    brief = _render_brief_section(last)
                    return html.Div([brief, html.H4('Results'), children]), _sanitize_for_store(last), '', True
                return html.Div('Job finished but no results'), None, '', True
            except Exception:
                logger.exception('Exception in poll handling')
                raise PreventUpdate

        # If the run button was clicked, attempt to run the real analysis
        if triggered == 'run-btn':
            tickers = [t.strip().upper() for t in (tickers_value or '').split(',') if t.strip()]
            if not tickers:
                return html.Div('No tickers provided.'), None, '', True
            # For development: call the real run_full_analysis synchronously so we can render results immediately
            # Attempt a synchronous run with a short join timeout. If it takes
            # too long, fall back to running in background and enable polling.
            res = None
            try:
                import market_trends_dash as mtd
                run_fn = getattr(mtd, 'run_full_analysis', None)
            except Exception:
                run_fn = None

            if run_fn is None:
                logger.debug('run_full_analysis not available in market_trends_dash; using mock fallback')
                res = None
            else:
                # start in a thread, join for a short time
                job_id = str(uuid.uuid4())
                result_container = {}

                def _runner():
                    try:
                        result_container['res'] = run_fn(tickers, period=period_value or '1y', interval='1d', options_topn=3, no_options=False, no_news=False, use_cache_only=('cache' in (analysis_opts or [])))
                    except Exception:
                        import traceback
                        result_container['exc'] = traceback.format_exc()

                th = threading.Thread(target=_runner, daemon=True)
                th.start()
                th.join(6.0)  # wait up to 6 seconds for quick runs
                if th.is_alive():
                    # still running -> move to background job registry and enable poll
                    logger.info('Analysis is long-running; moving job to BACKGROUND_JOBS %s', job_id)
                    BACKGROUND_JOBS[job_id] = {'thread': th, 'started': time.time(), 'tickers': tickers, 'result': None}

                    # start a background watcher to capture result when done
                    def _bg_waiter(jid, cont):
                        th_local = cont['thread']
                        th_local.join()
                        # try to fetch result from local closure if available
                        try:
                            if 'res' in result_container:
                                BACKGROUND_JOBS[jid]['result'] = result_container.get('res')
                            elif 'exc' in result_container:
                                BACKGROUND_JOBS[jid]['result'] = {'ok': False, 'error': 'exception', 'trace': result_container.get('exc')}
                            else:
                                BACKGROUND_JOBS[jid]['result'] = {'ok': False, 'error': 'no result'}
                        except Exception:
                            BACKGROUND_JOBS[jid]['result'] = {'ok': False, 'error': 'bg waiter failed'}

                    watcher = threading.Thread(target=_bg_waiter, args=(job_id, BACKGROUND_JOBS[job_id]), daemon=True)
                    watcher.start()
                    # return a queued UI and enable poll
                    return html.Div(f'Job {job_id} started in background...'), None, job_id, False
                else:
                    # finished within timeout
                    if 'exc' in result_container:
                        tb = result_container.get('exc')
                        logger.exception('Exception during run_full_analysis (finished quickly)')
                        err_children = html.Div([html.H4('Run failed'), html.Pre(tb, style={'whiteSpace': 'pre-wrap', 'maxHeight': '400px', 'overflow': 'auto'})])
                        return err_children, None, '', True
                    res = result_container.get('res')

            if not res:
                # fallback mock
                rows = []
                for i, t in enumerate(tickers[:25]):
                    rows.append({'ticker': t, 'score': round(100 * (1.0 / (i+1)), 2), '_inspect': 'Inspect', '_row_id': i})
                children, table = _render_table_from_records(rows)
                return children, _sanitize_for_store({'detailed': rows}), '', True

            try:
                safe = {
                    'detailed': res.get('detailed') or res.get('tidy') or [],
                    'tidy': res.get('tidy') or res.get('detailed') or [],
                    'brief_text': res.get('brief_text'),
                    'brief_json': res.get('brief_json'),
                    'prices': res.get('prices') or {}
                }
                if SH is not None and hasattr(SH, 'RESULTS_CACHE'):
                    SH.RESULTS_CACHE['results'] = safe
                    SH.RESULTS_CACHE['loaded_at'] = time.time()
                children, table = _render_table_from_records(safe.get('detailed') or [])
                return html.Div([_render_brief_section(safe), html.H4('Results'), children]), _sanitize_for_store(safe), '', True
            except Exception:
                rows = []
                for i, t in enumerate(tickers[:25]):
                    rows.append({'ticker': t, 'score': round(100 * (1.0 / (i+1)), 2), '_inspect': 'Inspect', '_row_id': i})
                children, table = _render_table_from_records(rows)
                return children, _sanitize_for_store({'detailed': rows}), '', True

        # refresh clicked: reload cache from disk
        if triggered == 'refresh-cached':
            last = load_last_cached_results()
            if last:
                recs = last.get('detailed') or last.get('tidy') or []
                children, table = _render_table_from_records(recs)
                brief = _render_brief_section(last)
                return html.Div([brief, html.H4('Refreshed cached results'), children]), _sanitize_for_store(last), '', True
            raise PreventUpdate

    # Expose for direct invocation during development/testing
    globals()['show_cached_or_run'] = show_cached_or_run

    # polling merged into `show_cached_or_run` to avoid duplicate Outputs

    @app.callback(
        Output('detail-modal', 'style'),
        Output('modal-content', 'children'),
        Input('results-table-client', 'active_cell'),
        Input('close-modal', 'n_clicks'),
        State('results-table-client', 'data'),
        allow_duplicate=True
    )
    def open_or_close_modal(active_cell, close_n, rows):
        if close_n:
            return {'display': 'none'}, ''
        if not active_cell or not rows:
            raise PreventUpdate
        try:
            r = rows[active_cell.get('row')]
            kv = [html.Div(f"{k}: {v}") for k, v in r.items() if not str(k).startswith('_')]
            return {'display': 'block', 'position': 'fixed', 'left': '10%', 'top': '10%', 'width': '80%', 'height': '80%', 'backgroundColor': 'white', 'border': '1px solid #ccc', 'padding': '10px', 'overflow': 'auto', 'zIndex': 1000}, [html.H3(f"Details: {r.get('ticker') if r else ''}"), html.Div(kv)]
        except Exception:
            return {'display': 'none'}, ''

    globals()['open_or_close_modal'] = open_or_close_modal


def load_last_cached_results():
    """Try to load the last cached results from SH.RESULTS_CACHE if
    available, otherwise attempt to load a few known JSON files from the
    repository root. Returns a dict-like object or None.
    """
    try:
        if SH is not None and hasattr(SH, 'RESULTS_CACHE'):
            res = SH.RESULTS_CACHE.get('results')
            if res:
                return res
    except Exception:
        pass

    # Fallback: try some common filenames that the project uses
    candidates = [
        'last_response.json',
        'last_response',
        'last_update_response.json',
        'forecast_post_response.json'
    ]
    for fn in candidates:
        p = os.path.join(os.getcwd(), fn)
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as fh:
                    return json.load(fh)
            except Exception:
                continue
    return None


def _sanitize_for_store(obj):
    """Return a JSON-serializable copy of `obj` suitable for storing in
    dcc.Store. Converts pandas DataFrames to records and numpy types to
    native Python types. Keeps primitive types unchanged.
    """
    try:
        if obj is None:
            return None
        # If it's a pandas DataFrame
        if isinstance(obj, pd.DataFrame):
            return obj.fillna('').to_dict(orient='records')
        # If it's a dict, recurse
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                out[k] = _sanitize_for_store(v)
            return out
        # If it's a list/tuple, recurse
        if isinstance(obj, (list, tuple)):
            return [_sanitize_for_store(v) for v in obj]
        # numpy scalars
        if _np is not None and isinstance(obj, (_np.generic,)):
            try:
                return obj.item()
            except Exception:
                return str(obj)
        # pandas types
        try:
            import pandas as _pd
            if hasattr(_pd, 'Timestamp') and isinstance(obj, _pd.Timestamp):
                return str(obj)
        except Exception:
            pass
        # Fallback: try to JSON-serialize; if it fails return str()
        try:
            json.dumps(obj)
            return obj
        except Exception:
            return str(obj)
    except Exception:
        try:
            return str(obj)
        except Exception:
            return None

    # Note: the unified_handler duplicate callback was removed to avoid
    # duplicate Output registrations for 'results-area.children'. The
    # primary handler for run/refresh is `show_cached_or_run` defined above.


def run_analysis_for_test(tickers_value, period_value='1y', analysis_opts=None):
    """Directly run the analysis logic used by the callback without relying
    on dash.callback_context. This helper is only for development/testing.
    Returns the same tuple as the callback: (children, last-cached, current-job, poll-disabled)
    """
    analysis_opts = analysis_opts or ['options', 'news']
    tickers = [t.strip().upper() for t in (tickers_value or '').split(',') if t.strip()]
    if not tickers:
        return html.Div('No tickers provided.'), None, '', True
    try:
        import market_trends_dash as mtd
        if hasattr(mtd, 'run_full_analysis'):
            res = mtd.run_full_analysis(tickers, period=period_value or '1y', interval='1d', options_topn=3, no_options=False, no_news=False, use_cache_only=('cache' in (analysis_opts or [])))
        else:
            res = None
    except Exception:
        import traceback
        tb = traceback.format_exc()
        print('Exception while running run_full_analysis (test helper):\n', tb)
        return html.Div([html.H4('Run failed'), html.Pre(tb, style={'whiteSpace': 'pre-wrap'})]), None, '', True

    if not res:
        rows = []
        for i, t in enumerate(tickers[:25]):
            rows.append({'ticker': t, 'score': round(100 * (1.0 / (i+1)), 2), '_inspect': 'Inspect', '_row_id': i})
        cols = [{'name': c, 'id': c} for c in rows[0].keys()]
        table = dash_table.DataTable(id='results-table-client', columns=cols, data=rows, page_size=25, style_cell={'color': 'black'})
        return html.Div([html.H4('Results'), table]), _sanitize_for_store({'detailed': rows}), '', True

    safe = {
        'detailed': res.get('detailed') or res.get('tidy') or [],
        'tidy': res.get('tidy') or res.get('detailed') or [],
        'brief_text': res.get('brief_text'),
        'brief_json': res.get('brief_json'),
        'prices': res.get('prices') or {}
    }
    recs = safe.get('detailed') or []
    if recs:
        cols = [{'name': c, 'id': c} for c in recs[0].keys()]
        table = dash_table.DataTable(id='results-table-client', columns=cols, data=recs, page_size=25, style_cell={'color': 'black'})
    else:
        table = html.Div('No records to display.')
    brief = html.Div(safe.get('brief_text') or '')
    return html.Div([brief, html.H4('Results'), table]), _sanitize_for_store(safe), '', True


    @app.callback(Output('detail-modal', 'style'), Output('modal-content', 'children'), Input('results-table-client', 'active_cell'), Input('close-modal', 'n_clicks'), State('results-table-client', 'data'))
    def open_or_close_modal(active_cell, close_n, rows):
        if close_n:
            return {'display': 'none'}, ''
        if not active_cell or not rows:
            raise PreventUpdate
        try:
            r = rows[active_cell.get('row')]
            kv = [html.Div(f"{k}: {v}") for k, v in r.items() if not str(k).startswith('_')]
            return {'display': 'block', 'position': 'fixed', 'left': '10%', 'top': '10%', 'width': '80%', 'height': '80%', 'backgroundColor': 'white', 'border': '1px solid #ccc', 'padding': '10px', 'overflow': 'auto', 'zIndex': 1000}, [html.H3(f"Details: {r.get('ticker') if r else ''}"), html.Div(kv)]
        except Exception:
            return {'display': 'none'}, ''


if __name__ == '__main__':
    # Run this module as a standalone Dash app for development/testing.
    try:
        import os
        from dash import Dash

        app = Dash(__name__, suppress_callback_exceptions=True)
        server = app.server
        # Use the standalone layout variant
        app.layout = layout(is_tab=False)
        # Register callbacks (SH may be None in this dev runner)
        try:
            register_callbacks(app)
        except Exception:
            # allow callback registration to fail gracefully while iterating
            import traceback
            traceback.print_exc()

        port = int(os.environ.get('TRENDS_REBUILD_PORT', '8060'))
        print(f"Starting Market Trends rebuild app on http://127.0.0.1:{port}")
        app.run(port=port, debug=False)
    except Exception as e:
        print('Failed to start Trends rebuild app:', e)
        import traceback
        traceback.print_exc()
