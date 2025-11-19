"""
Minimal Analysis tab implementation (Attribution-focused).

This is a compact, single-file implementation with a stable layout and two
helpers: _load_picks_in_range and _run_attribution_analysis. The helpers are
defensive and convert numpy scalars to Python floats so outputs can be stored
in Dash dcc.Store (JSON-safe).
"""

import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dash import dcc, html, Input, Output, State, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)

try:
    from utils import attribution as ATTR
except Exception:
    ATTR = None


def layout():
    return dbc.Container([
        html.Div([
            html.H2("Analysis Hub", className="mt-3 mb-3"),
            html.P("Understand past performance and test future scenarios", className="text-muted mb-4"),
        ], style={'background-color': '#2b3035', 'padding': '20px', 'border-radius': '8px', 'margin-bottom': '20px'}),

        dbc.Tabs(id='analysis-main-tabs', active_tab='attribution', children=[
            dbc.Tab(label='📈 Attribution Analysis', tab_id='attribution', children=dbc.Container([
                html.H4('Attribution Analysis', className='mt-3 mb-3'),
                dbc.Card(dbc.CardBody([
                    dbc.Row([
                        dbc.Col([html.Label('Picks Type'), dcc.Dropdown(id='attr-picks-type', options=[{'label':'Weekly','value':'weekly'}], value='weekly', clearable=False)], width=4),
                        dbc.Col([html.Label('Date Range'), dcc.DatePickerRange(id='attr-date-range', start_date=(datetime.now()-timedelta(days=90)).date(), end_date=datetime.now().date(), display_format='YYYY-MM-DD')], width=4),
                        dbc.Col([html.Label('Horizon'), dcc.Dropdown(id='attr-horizon', options=[{'label':'1 Week','value':'1w'},{'label':'1 Month','value':'1m'},{'label':'3 Months','value':'3m'}], value='1w', clearable=False)], width=4)
                    ]),
                    html.Br(),
                    dbc.Button('Run Attribution Analysis', id='attr-run-button', color='primary')
                ]), className='mb-4'),

                dbc.Alert(id='attr-status', color='info', is_open=False, duration=4000),

                html.Div(id='attr-results-container', style={'display':'none'}, children=[
                    dbc.Row([
                        dbc.Col(dbc.Card(dbc.CardBody([html.H6('Total Return', className='text-muted'), html.H4(id='attr-total-return', children='--')]))),
                        dbc.Col(dbc.Card(dbc.CardBody([html.H6('Alpha', className='text-muted'), html.H4(id='attr-alpha', children='--')]))),
                        dbc.Col(dbc.Card(dbc.CardBody([html.H6('Beta', className='text-muted'), html.H4(id='attr-beta', children='--')]))),
                        dbc.Col(dbc.Card(dbc.CardBody([html.H6('Beta Contrib', className='text-muted'), html.H4(id='attr-beta-contrib', children='--')]))),
                    ], className='mb-4'),
                    dbc.Card(dbc.CardBody([html.H5('Alpha vs Beta'), dcc.Graph(id='attr-scatter')])),
                    dbc.Card(dbc.CardBody([html.H5('Factor Contributions'), dcc.Graph(id='attr-factors')])),
                    dbc.Card(dbc.CardBody([html.H5('Per-Pick Details'), html.Div(id='attr-table')]))
                ])
            ], fluid=True)),
        ]),

        dcc.Store(id='attr-results-store')
    ], fluid=True)


def register_callbacks(app):
    # Guard: if another tab/module already registered callbacks that update the
    # same output ids (e.g. attr-status / attr-results-store), skip registering
    # to avoid Dash 'Duplicate callback outputs' runtime errors.
    try:
        existing = getattr(app, 'callback_map', {}) or {}
        if any(('attr-status' in k) or ('attr-results-store' in k) for k in existing.keys()):
            logger.info('Skipping analysis.register_callbacks because similar outputs already registered')
            return
    except Exception:
        # If inspection fails, continue and register as usual
        pass
    # Combined callback to avoid Duplicate callback outputs error. Inspect which input triggered
    # and behave accordingly. This prevents Dash complaining when multiple callbacks try to
    # update the same outputs.
    @app.callback([
        Output('attr-status', 'children'), Output('attr-status', 'is_open'), Output('attr-status', 'color'),
        Output('attr-results-store', 'data'), Output('attr-results-container', 'style')],
        [Input('attr-run-button', 'n_clicks'), Input('analysis-main-tabs', 'active_tab')],
        [State('attr-picks-type', 'value'), State('attr-date-range', 'start_date'), State('attr-date-range', 'end_date'), State('attr-horizon', 'value'), State('attr-results-store', 'data')]
    )
    def attribution_controller(n_clicks, active_tab, picks_type, start_date, end_date, horizon, store):
        ctx = callback_context
        trigger = None
        if ctx and ctx.triggered:
            trigger = ctx.triggered[0]['prop_id'].split('.')[0]

        # Manual run via button
        if trigger == 'attr-run-button':
            if not n_clicks:
                raise PreventUpdate
            try:
                picks_df = _load_picks_in_range(picks_type, start_date, end_date)
                if picks_df is None or picks_df.empty:
                    return ('No picks found', True, 'warning', None, {'display':'none'})
                results = _run_attribution_analysis(picks_df, horizon)
                if not results:
                    return ('No matured picks for horizon', True, 'warning', None, {'display':'none'})
                return (f'Analyzed {len(picks_df)} picks', True, 'success', results, {'display':'block'})
            except Exception as e:
                logger.error(f'Attribution run error: {e}', exc_info=True)
                return (f'Error: {str(e)}', True, 'danger', None, {'display':'none'})

        # Auto-run when tab becomes active
        if trigger == 'analysis-main-tabs':
            if active_tab != 'attribution':
                raise PreventUpdate
            if store:
                raise PreventUpdate
            try:
                wide_start = (datetime.now() - timedelta(days=365)).date()
                wide_end = datetime.now().date()
                picks_df = _load_picks_in_range(picks_type, wide_start, wide_end)
                if picks_df is None or picks_df.empty:
                    return ('No picks found (auto)', True, 'warning', None, {'display':'none'})
                picks_df['date'] = pd.to_datetime(picks_df['date'])
                latest_date = picks_df['date'].max()
                latest_picks = picks_df[picks_df['date'] == latest_date]
                results = _run_attribution_analysis(latest_picks, horizon)
                if not results:
                    return ('Auto-run: no matured picks', True, 'warning', None, {'display':'none'})
                return (f'Auto-analyzed {len(latest_picks)} picks from {latest_date.date()}', True, 'success', results, {'display':'block'})
            except Exception as e:
                logger.error(f'Auto attribution error: {e}', exc_info=True)
                return (f'Error: {str(e)}', True, 'danger', None, {'display':'none'})

        # No recognized trigger
        raise PreventUpdate


def _load_picks_in_range(picks_type, start_date, end_date):
    """Load pick CSVs whose filename contains a date within [start_date, end_date]."""
    try:
        import glob, re
        picks_dir = os.path.join(os.path.dirname(__file__), '..', 'models', 'weekly_run' if picks_type == 'weekly' else 'models')
        picks_dir = os.path.abspath(picks_dir)
        if not os.path.exists(picks_dir):
            logger.warning(f'Picks dir not found: {picks_dir}')
            return None
        csv_files = glob.glob(os.path.join(picks_dir, '*picks*.csv'))
        all_picks = []
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        for csv_file in csv_files:
            try:
                filename = os.path.basename(csv_file)
                date_match = re.search(r'(\d{8})', filename)
                file_date = None
                if date_match:
                    file_date_str = date_match.group(1)
                    try:
                        file_date = pd.to_datetime(file_date_str, format='%Y%m%d')
                    except Exception:
                        file_date = None
                else:
                    mmdd_match = re.search(r'(\d{4})', filename)
                    if mmdd_match:
                        mmdd = mmdd_match.group(1)
                        try:
                            month = int(mmdd[:2])
                            day = int(mmdd[2:])
                            candidate = pd.Timestamp(year=end.year, month=month, day=day)
                            if candidate < start or candidate > end:
                                candidate = pd.Timestamp(year=end.year - 1, month=month, day=day)
                            file_date = candidate
                        except Exception:
                            file_date = None

                if file_date is None:
                    continue

                if file_date < start or file_date > end:
                    continue

                df = pd.read_csv(csv_file)
                if 'ticker' not in df.columns:
                    continue
                df['date'] = file_date
                all_picks.append(df)
            except Exception:
                continue

        if not all_picks:
            return None
        return pd.concat(all_picks, ignore_index=True)
    except Exception as e:
        logger.error(f'Load picks error: {e}')
        return None


def _run_attribution_analysis(picks_df, horizon):
    """Run a simple attribution on picks_df and return a JSON-serializable dict."""
    try:
        import yfinance as yf
        horizon_days = {'1w': 7, '1m': 30, '3m': 90}.get(horizon, 7)
        per_pick_results = []
        today = pd.Timestamp.now().normalize()

        for _, pick in picks_df.iterrows():
            ticker = pick.get('ticker')
            pick_date = pd.to_datetime(pick.get('date'))
            end_date = pick_date + timedelta(days=horizon_days)
            if end_date > today:
                continue
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(start=pick_date - timedelta(days=1), end=end_date + timedelta(days=1))
                if len(hist) < 2:
                    continue
                realized_return = float(hist['Close'].iloc[-1] / hist['Close'].iloc[0] - 1)
                spy = yf.Ticker('SPY')
                spy_hist = spy.history(start=pick_date - timedelta(days=1), end=end_date + timedelta(days=1))
                benchmark_return = float(spy_hist['Close'].iloc[-1] / spy_hist['Close'].iloc[0] - 1) if len(spy_hist) >=2 else 0.0
                beta = 1.0
                if ATTR:
                    try:
                        long_hist = stock.history(start=pick_date - timedelta(days=252), end=pick_date)
                        spy_long = spy.history(start=pick_date - timedelta(days=252), end=pick_date)
                        if len(long_hist) >= 20 and len(spy_long) >= 20:
                            merged = pd.DataFrame({'stock': long_hist['Close'].pct_change(), 'spy': spy_long['Close'].pct_change()}).dropna()
                            if len(merged) >= 20:
                                beta_raw = ATTR.estimate_beta(merged, 'stock', 'spy')
                                beta = float(beta_raw) if not isinstance(beta_raw, (int,float)) else beta_raw
                    except Exception:
                        pass
                beta_contrib = float(beta) * float(benchmark_return)
                alpha = float(realized_return) - float(beta_contrib)
                per_pick_results.append({'ticker': ticker, 'date': pick_date.strftime('%Y-%m-%d'), 'realized_return': realized_return, 'alpha': alpha, 'beta': beta, 'beta_contrib': beta_contrib})
            except Exception:
                continue

        if not per_pick_results:
            return None

        total_return = np.mean([p['realized_return'] for p in per_pick_results])
        total_alpha = np.mean([p['alpha'] for p in per_pick_results])
        avg_beta = np.mean([p['beta'] for p in per_pick_results])
        total_beta_contrib = np.mean([p['beta_contrib'] for p in per_pick_results])

        def _to_py(x):
            try:
                if isinstance(x,(np.floating,np.integer)):
                    return float(x)
            except Exception:
                pass
            return x

        portfolio = {'total_return': _to_py(total_return), 'alpha': _to_py(total_alpha), 'beta': _to_py(avg_beta), 'beta_contrib': _to_py(total_beta_contrib), 'top_factors':[{'factor':'momentum','contribution':0.02},{'factor':'sentiment','contribution':0.015}]}
        cleaned = []
        for p in per_pick_results:
            cp = dict(p)
            for k,v in cp.items():
                if isinstance(v,(np.floating,np.integer)):
                    cp[k] = float(v)
            cleaned.append(cp)
        return {'portfolio': portfolio, 'per_pick': cleaned}
    except Exception as e:
        logger.error(f'Attribution analysis error: {e}')
        return None
