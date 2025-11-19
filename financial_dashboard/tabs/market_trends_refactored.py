"""
Full Market Trends tab (original implementation).
Copied from `tabs/market_trends.py` to preserve the complete UI and callbacks.
This file provides the original behavior for the Market Trends tab when the
refactored placeholder is not desired.
"""

from dash import dcc, html, Input, Output, State, dash_table, callback_context, no_update
from dash_extensions.enrich import Dash
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
import pandas as pd
from financial_dashboard from financial_dashboard import _shared as SH
from utils import market_trend as MT
import json, time, uuid, traceback, os, re, logging
import importlib
import threading
from datetime import datetime
import plotly.graph_objects as go
from logging.handlers import RotatingFileHandler
import time
import json

# Add necessary imports and logger initialization
from financial_dashboard._shared import (
    load_last_cached_results,
    load_cached_results_from_outputs,
    _sanitize_for_store,
    load_module_from_path,
)
from financial_dashboard.utils.events_helper import create_events_panel, get_events_summary
logger = logging.getLogger(__name__)


def _compute_live_market_trend():
    """Compute market trend on-the-fly using current market data."""
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        
        # Fetch SPY data for trend calculation
        spy = yf.Ticker("SPY")
        end_date = datetime.now()
        start_date = end_date - timedelta(days=400)
        hist = spy.history(start=start_date, end=end_date)
        
        if hist.empty or len(hist) < 20:
            return None
        
        # Calculate returns
        r1m = (hist['Close'].iloc[-1] / hist['Close'].iloc[-21] - 1) if len(hist) >= 21 else 0
        r3m = (hist['Close'].iloc[-1] / hist['Close'].iloc[-63] - 1) if len(hist) >= 63 else 0
        r6m = (hist['Close'].iloc[-1] / hist['Close'].iloc[-126] - 1) if len(hist) >= 126 else 0
        
        # Calculate moving averages
        ma50 = hist['Close'].rolling(50).mean()
        ma200 = hist['Close'].rolling(200).mean()
        
        ma50_pct_slope = 0
        if len(ma50) >= 10:
            ma50_pct_slope = (ma50.iloc[-1] / ma50.iloc[-10] - 1)
        
        ma50_vs_ma200 = 0
        if not pd.isna(ma50.iloc[-1]) and not pd.isna(ma200.iloc[-1]) and ma200.iloc[-1] > 0:
            ma50_vs_ma200 = (ma50.iloc[-1] / ma200.iloc[-1] - 1)
        
        # Get VIX data
        vix_ticker = yf.Ticker("^VIX")
        vix_hist = vix_ticker.history(start=start_date, end=end_date)
        vix = vix_hist['Close'].iloc[-1] if not vix_hist.empty else 20.0
        vix_mean_252 = vix_hist['Close'].mean() if len(vix_hist) >= 20 else 20.0
        vix_std_252 = vix_hist['Close'].std() if len(vix_hist) >= 20 else 5.0
        
        # Simple breadth approximation (use volume as proxy)
        adv_decl_ratio = 0.0
        if 'Volume' in hist.columns and len(hist) >= 5:
            recent_vol_trend = hist['Volume'].iloc[-5:].mean() / hist['Volume'].iloc[-20:-5].mean() if len(hist) >= 20 else 1.0
            adv_decl_ratio = (recent_vol_trend - 1.0) * 0.5
        
        # Compute trend using the utility
        trend_result = MT.compute_market_trend(
            r1m=r1m, r3m=r3m, r6m=r6m,
            ma50_pct_slope=ma50_pct_slope,
            ma50_vs_ma200=ma50_vs_ma200,
            vix=vix,
            vix_mean_252=vix_mean_252,
            vix_std_252=vix_std_252,
            adv_decl_ratio=adv_decl_ratio
        )
        
        return trend_result
        
    except Exception as e:
        logger.error(f"Error computing live market trend: {e}")
        return None

# Define placeholder functions to resolve NameErrors
def _render_brief_section(last):
    """Renders the brief section from cached results."""
    if not last:
        return html.Div()
    
    brief_text = last.get('brief_text', '')
    
    # Enrich with events data
    events_summary = get_events_summary()
    if events_summary:
        high_count = events_summary.get('high_severity_count', 0)
        if high_count > 0:
            brief_text += f" Market shows {high_count} high-severity events today, indicating elevated volatility."
    
    # ============ PHASE 3: MARKET TREND LABEL INTEGRATION ============
    # Extract market trend composite and label if available
    trend_label = None
    trend_composite = None
    trend_tooltip = "Market trend analysis not available"
    
    try:
        # Check if market trend data exists in results
        if 'market_trend' in last:
            trend_data = last['market_trend']
            trend_label = trend_data.get('label', 'Unknown')
            trend_composite = trend_data.get('composite', 0.0)
            
            # Build tooltip explaining components
            scores = trend_data.get('scores', {})
            components = []
            if scores:
                for key, val in scores.items():
                    components.append(f"{key}: {val:.2f}")
            
            trend_tooltip = (
                f"Composite: {trend_composite:.2f} | "
                f"Components: {', '.join(components) if components else 'N/A'}"
            )
        else:
            # Compute trend on the fly if not in cached results
            try:
                trend_result = _compute_live_market_trend()
                if trend_result:
                    trend_label = trend_result.get('label', 'Unknown')
                    trend_composite = trend_result.get('composite', 0.0)
                    scores = trend_result.get('scores', {})
                    components = []
                    if scores:
                        for key, val in scores.items():
                            components.append(f"{key}: {val:.2f}")
                    trend_tooltip = (
                        f"Composite: {trend_composite:.2f} | "
                        f"Components: {', '.join(components) if components else 'N/A'}"
                    )
            except Exception as e2:
                logger.warning(f"Could not compute live market trend: {e2}")
    except Exception as e:
        logger.warning(f"Could not extract market trend label: {e}")
    
    # Create trend badge if available
    trend_badge = html.Div()
    if trend_label:
        # Color based on label
        badge_colors = {
            'Strong Bull': '#10b981',  # Green
            'Bull': '#84cc16',         # Light green
            'Neutral': '#94a3b8',      # Gray
            'Bear': '#f59e0b',         # Orange
            'Strong Bear': '#ef4444',  # Red
        }
        badge_color = badge_colors.get(trend_label, '#6b7280')
        
        trend_badge = html.Div([
            html.Span(
                f"Market Trend: {trend_label}",
                title=trend_tooltip,
                style={
                    'backgroundColor': badge_color,
                    'color': 'white',
                    'padding': '4px 12px',
                    'borderRadius': '4px',
                    'fontSize': '14px',
                    'fontWeight': 'bold',
                    'display': 'inline-block',
                    'marginBottom': '8px',
                    'cursor': 'help',
                }
            )
        ])
    # ================================================================
    
    return html.Div([
        html.H5("Market Brief"),
        trend_badge,  # Display trend badge above brief text
        html.P(brief_text)
    ])

def _render_table_from_records(records):
    """Renders a Dash DataTable from a list of records."""
    print("DEBUG: _render_table_from_records called from tabs/market_trends.py with FIX applied")
    if not records:
        return html.Div("No data to display."), None

    df = pd.DataFrame(records)
    cols = [{"name": i, "id": i} for i in df.columns]
    table = dash_table.DataTable(
        id='results-table-client',
        columns=cols,
        data=records,
        page_action='none',  # Show all rows without pagination
        sort_action='native',
        filter_action='native',
        virtualization=True,  # Enable virtualization for better performance
        # REMOVED fixed_rows - was causing only 2 rows to render!
        # fixed_rows={'headers': True},
        style_table={
            'overflowX': 'auto',
            'overflowY': 'auto',
            'maxHeight': '600px',  # Add max height for scrolling
            'width': '100%',
            'maxWidth': '100%',
            'backgroundColor': '#ffffff'
        },
        style_cell={
            'textAlign': 'left',
            'padding': '8px 10px',
            'backgroundColor': '#ffffff',
            'color': '#000000',
            'border': '1px solid #ddd',
            'minWidth': '80px',
            'maxWidth': '250px',
            'whiteSpace': 'nowrap',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'fontFamily': 'Arial, sans-serif',
            'fontSize': '13px',
            'lineHeight': '1.4'
        },
        style_header={
            'backgroundColor': '#2c3e50',
            'color': '#ffffff',
            'fontWeight': 'bold',
            'border': '1px solid #ddd',
            'textAlign': 'left',
            'padding': '10px',
            'fontSize': '13px',
            'lineHeight': '1.4'
        },
        style_data={
            'backgroundColor': '#ffffff',
            'color': '#000000',
            'border': '1px solid #ddd',
            'whiteSpace': 'nowrap',
            'overflow': 'hidden',
            'textOverflow': 'ellipsis',
            'lineHeight': '1.4'
        },
        style_data_conditional=[
            {
                'if': {'row_index': 'odd'},
                'backgroundColor': '#f8f9fa !important',
                'color': '#000000 !important'
            },
            {
                'if': {'row_index': 'even'},
                'backgroundColor': '#ffffff !important',
                'color': '#000000 !important'
            }
        ]
    )
    # Wrap in a responsive container div
    container = html.Div(
        [table],
        id='trends-results-table-container',
        style={
            'width': '100%',
            'maxWidth': '100%',
            'overflowX': 'auto',
            'backgroundColor': '#ffffff',
            'borderRadius': '6px',
            'border': '1px solid #e5e7eb',
            'marginTop': '8px'
        },
        **{'data-testid': 'trends-results-table-container'}
    )
    return container, table


def _render_server_table(records):
    """Render a plain server-side HTML table (Dash html.Table) as a reliable
    fallback when client DataTable styling is being overridden by CSS.
    Returns a Div containing the table with class 'market-trends-server-preview'."""
    if not records:
        return html.Div('No data to display.', className='market-trends-server-preview')

    try:
        df = pd.DataFrame(records)
    except Exception:
        # If records aren't a rectangular structure, render a preformatted dump
        return html.Div([html.H4('Results'), html.Pre(json.dumps(records, indent=2))], className='market-trends-server-preview')

    # Build header
    headers = [html.Th(col) for col in df.columns]

    # Build rows
    body_rows = []
    for _, row in df.iterrows():
        cells = []
        for col in df.columns:
            val = row.get(col, '')
            try:
                # stringify safely
                cell_text = '' if pd.isna(val) else str(val)
            except Exception:
                cell_text = str(val)
            cells.append(html.Td(cell_text))
        body_rows.append(html.Tr(cells))

    table = html.Table([
        html.Thead(html.Tr(headers)),
        html.Tbody(body_rows)
    ], style={
        'width': '100%', 'borderCollapse': 'collapse', 'background': '#0b1824', 'color': '#e6eef8'
    }, className='market-trends-server-preview')

    wrapper = html.Div([
        html.H4('Analysis Results (server-rendered)', style={'color': '#e6eef8', 'margin': '8px 0'}),
        table
    ], style={'padding': '8px', 'border': '1px solid #123', 'background': '#071028'})

    return wrapper

def build_price_figure(df, title="Price Chart"):
    """Builds a Plotly figure for price data."""
    if df is None or df.empty:
        return go.Figure()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='Close'))
    fig.update_layout(title=title)
    return fig

def run_full_analysis(*args, **kwargs):
    """Placeholder for run_full_analysis to avoid NameError on startup."""
    logging.warning("run_full_analysis called from tab module; attempting to locate full analysis implementation.")
    # First try to load the primary analysis module from the repository's Gradio folder
    try:
        proj_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        gradio_path = os.path.join(proj_root, 'Gradio', 'market_trends.py')
        if os.path.exists(gradio_path) and 'load_module_from_path' in globals():
            try:
                mod = load_module_from_path(gradio_path, 'market_trends')
                if mod is not None and hasattr(mod, 'run_full_analysis'):
                    return mod.run_full_analysis(*args, **kwargs)
            except Exception:
                logging.exception('Failed to load Gradio/market_trends run_full_analysis')
    except Exception:
        logging.exception('Error while attempting to locate Gradio/market_trends')

    # Fallback: if the lightweight utils.market_trend exposes a compatible function, use it
    try:
        if hasattr(MT, 'run_full_analysis'):
            return MT.run_full_analysis(*args, **kwargs)
    except Exception:
        logging.exception('Fallback MT.run_full_analysis failed')

    # As a last resort, raise a clear error so callers know why the background job failed
    raise RuntimeError('run_full_analysis implementation not found in Gradio/market_trends.py or utils.market_trend')

def layout():
    """
    Defines the layout for the Market Trends tab.
    All placeholder components are removed from here and are now managed
    by the centralized `layout_placeholders.py`.
    """
    return html.Div([
        # Mount-trigger disabled to prevent STATUS_BREAKPOINT circular callback issues
        # dcc.Interval(id='mount-trigger', interval=100, max_intervals=1),
        html.H3('Market Trends'),
        html.Div([
            html.Label('Tickers (comma separated)'),
            html.Div([
                dcc.Textarea(id='tickers-input', value='NVDA,AAPL,MSFT,GOOGL,META,AMZN,TSLA,INTC,AMD,AVGO,NTCL,SPY,QQQ,XLK,LZMH', style={'width': '100%', 'minWidth': '720px', 'maxWidth': '95vw', 'resize': 'vertical'}, rows=2),
            ], style={'flex': '1 1 auto', 'display': 'flex'}),
            html.Button('Run Full Analysis', id='run-btn', n_clicks=0, style={'marginLeft': '8px'}),
        ], style={'display': 'flex', 'alignItems': 'center', 'gap': '8px', 'marginBottom': '8px'}),

        html.Div([
            html.Label('Period (e.g. 6mo,1y)', style={'marginRight': '8px'}),
            dcc.Input(id='period-input', value='1y', type='text', style={'width': '120px'}),
        ], style={'marginBottom': '8px'}),

        html.Div([
            html.Label('Analysis options'),
            dcc.Checklist(id='analysis-options', options=[
                {'label': 'Include options enrichment', 'value': 'options'},
                {'label': 'Include news enrichment', 'value': 'news'},
                {'label': 'Use cache only', 'value': 'cache'}
            ], value=['options', 'news'], inline=False),
        ], style={'marginBottom': '8px'}),

        html.Div(id='status', style={'marginTop': 6, 'display': 'none'}),

        html.Button('Reload Model', id='reload-model', n_clicks=0),
        html.Button('Refresh cached display', id='refresh-cached', n_clicks=0, style={'marginLeft': '8px'}),
        html.Div(id='model-status', style={'fontSize': '12px', 'color': '#cbd5e1', 'marginTop': 6}),

        html.Button('Toggle full brief', id='toggle-brief', n_clicks=0, style={'marginTop': '8px'}),
        html.Div(id='full-brief', style={'display': 'none', 'marginTop': '8px', 'padding': '10px', 'borderRadius': '6px', 'backgroundColor': '#071028', 'color': '#e6eef8', 'border': '1px solid #123'}),

        html.Div(id='compact-brief-wrapper', children=[html.Div(id='compact-brief')], style={'marginTop': '8px', 'maxWidth': '1200px'}),

        # Recent Critical Events Panel
        html.Div([
            create_events_panel(severity_filter='HIGH', max_events=10)
        ], style={'marginTop': '16px', 'marginBottom': '16px', 'maxWidth': '1200px'}),

        # The results will be rendered here by the callback - wrapped in responsive container
        dcc.Loading(
            id='loading',
            children=[
                html.Div(
                    id='results-area',
                    style={
                        'width': '100%',
                        'maxWidth': '100%',
                        'overflowX': 'auto',
                        'marginTop': '12px'
                    }
                )
            ],
            type='circle'
        ),

        html.Div(id='job-history', style={'marginTop': 12}),
        html.Button('Download CSV (latest)', id='download-btn', n_clicks=0),

        # Debug console
        html.Div([
            html.H4("Debug Console"),
            dcc.Textarea(id='debug-input', style={'width': '100%', 'height': '100px'}),
            html.Button('Log to Console', id='debug-log-btn'),
            html.Div(id='debug-output')
        ], style={'marginTop': '20px', 'border': '1px solid #ccc', 'padding': '10px'})
    ])

def register_callbacks(app):
    """
    Registers all callbacks for the Market Trends tab.
    The `shared` object is now imported directly from `_shared`.
    """
    @app.callback(
        Output('results-area', 'children'),
        Output('trends-last-cached', 'data'), # Use the new unique ID
        Output('status', 'children'),
        Output('status', 'style'),
        Output('job-history', 'children'),
        Input('run-btn', 'n_clicks'),
        Input('poll-interval', 'n_intervals'),
        Input('reload-trigger', 'data'),
        Input('dashboard-queued-job', 'data'),
        # mount-trigger removed to fix STATUS_BREAKPOINT
        State('tickers-input', 'value'),
        State('period-input', 'value'),
        State('current-job', 'data'),
        State('analysis-options', 'value')
    )
    def update_results_and_poll(n_clicks, n_intervals, reload_data, queued_job_id, tickers, period, job_id, analysis_options):
        ctx = callback_context
        
        # Get triggered ID
        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0] if ctx.triggered else 'reload-trigger'

        # Handle page load/reload - auto-load cached results
        if triggered_id == 'reload-trigger' or not ctx.triggered:
            try:
                last = load_last_cached_results()
                if last and (last.get('detailed') or last.get('tidy')):
                    sanitized = _sanitize_for_store(last)
                    data = sanitized.get('detailed') or sanitized.get('tidy', [])
                    if data:
                        logger.info(f"Auto-loading cached results on mount: {len(data)} rows")
                        table, _ = _render_table_from_records(data)
                        # Wrap in a responsive container
                        composite = html.Div(
                            [table],
                            id='trends-composite-results',
                            style={
                                'marginTop': '12px',
                                'border': '1px solid #e5e7eb',
                                'borderRadius': '6px',
                                'backgroundColor': '#ffffff'
                            }
                        )
                        return composite, sanitized, f"Loaded {len(data)} rows from cache", {'display': 'block', 'color': '#10b981'}, None
            except Exception as e:
                logger.error(f"Initial cache load failed: {e}", exc_info=True)
            # If no cached data, show empty state
            empty_state = html.Div(
                "No cached data. Click 'Run Full Analysis' to generate results.",
                style={'padding': '20px', 'textAlign': 'center', 'color': '#9ca3af'}
            )
            return empty_state, None, "", {'display': 'none'}, None
        opts = analysis_options or []

        # Handle job queued from another tab (e.g. forecast)
        if triggered_id == 'dashboard-queued-job' and queued_job_id:
            if job_id and job_id == queued_job_id:
                # This tab is already tracking this job
                raise PreventUpdate
            # A new job was started elsewhere; this tab should start polling
            # and show status. We don't get the job result directly, but we
            # can show the user that something is running.
            return (
                no_update, no_update,
                f"Running job {queued_job_id}...",
                {'display': 'block', 'backgroundColor': '#007bff', 'color': 'white'},
                no_update
            )

        # Handle manual "Run" button click
        if triggered_id == 'run-btn' and n_clicks > 0:
            if job_id:
                return no_update, no_update, "A job is already running.", {'display': 'block', 'backgroundColor': 'orange'}, no_update

            logger.info(f"Starting new analysis for tickers: {tickers}")
            # Normalize options keys: checklist uses 'cache' value
            job_params = {'tickers': tickers, 'period': period, 'options': 'options' in opts, 'news': 'news' in opts, 'cache_only': 'cache' in opts}
            new_job_id = str(uuid.uuid4())

            # Use the shared background job runner. Support both legacy SH API
            # that accepted a job_id kwarg, and the newer API that returns a job id.
            started_job_id = None
            if SH is not None and hasattr(SH, 'start_background_job'):
                try:
                    # Prefer a server-level run_full_analysis implementation when available.
                    target_fn = globals().get('run_full_analysis')
                    try:
                        import sys, importlib
                        mt_dash = sys.modules.get('market_trends_dash') or sys.modules.get('Dash.market_trends_dash')
                        if mt_dash and hasattr(mt_dash, 'run_full_analysis'):
                            target_fn = getattr(mt_dash, 'run_full_analysis')
                        else:
                            try:
                                mod = importlib.import_module('Dash.market_trends_dash')
                                if hasattr(mod, 'run_full_analysis'):
                                    target_fn = mod.run_full_analysis
                            except Exception:
                                pass
                    except Exception:
                        pass

                    try:
                        # legacy form (some old helpers accepted job_id)
                        started_job_id = SH.start_background_job(target_fn, job_name='trends_analysis', job_id=new_job_id, **job_params)
                    except TypeError:
                        # newer form: start_background_job(target, args=(), kwargs=None, job_name=None) -> job_id
                        started_job_id = SH.start_background_job(target_fn, args=(), kwargs=job_params, job_name='trends_analysis')
                except Exception:
                    logger.exception("Failed to start background job via SH.start_background_job")

            # If shared runner didn't return an ID, fall back to the generated one
            job_id_to_show = started_job_id or new_job_id

            return (
                no_update, no_update,
                f"Started job {job_id_to_show}",
                {'display': 'block', 'backgroundColor': '#007bff', 'color': 'white'},
                no_update
            )

        # Handle polling for results
        if triggered_id == 'poll-interval' and job_id:
            try:
                # Prefer in-process shared job registry
                job_info = None
                try:
                    if SH is not None and hasattr(SH, 'get_job_status'):
                        job_info = SH.get_job_status(job_id)
                except Exception:
                    job_info = None

                # Fallback: query API Gateway if SH doesn't know about this job
                if not job_info:
                    try:
                        import requests
                        gw = os.environ.get('API_GATEWAY_URL', 'http://127.0.0.1:8049')
                        resp = requests.get(f"{gw}/api/trends/jobs/{job_id}", timeout=5)
                        if resp.status_code == 200:
                            job_info = resp.json()
                    except Exception:
                        job_info = None

                if not job_info:
                    return no_update, no_update, f"Job {job_id} not found.", {'display': 'block', 'backgroundColor': 'red'}, no_update

                status = job_info.get('status')
                if status == 'completed':
                    try:
                        result = job_info.get('result')
                        logger.info(f"Job completed, result type: {type(result)}, is dict: {isinstance(result, dict)}")
                        
                        if not result or not isinstance(result, dict):
                            return html.Div([html.H4('Job completed'), html.P('No result data returned')]), no_update, "Job completed (no data)", {'display': 'block', 'backgroundColor': 'orange'}, no_update
                        
                        logger.info(f"Result keys: {list(result.keys())}")
                        sanitized = _sanitize_for_store(result)
                        detailed_data = sanitized.get('detailed', [])
                        logger.info(f"Detailed data length: {len(detailed_data) if detailed_data else 0}")
                        
                        if not detailed_data:
                            return html.Div([html.H4('Job completed'), html.P('No detailed data in result')]), sanitized, "Job completed (empty)", {'display': 'block', 'backgroundColor': 'orange'}, no_update
                        
                        table_container, _ = _render_table_from_records(detailed_data)
                        # Ensure a server-rendered fallback is available in case client CSS hides rows
                        server_table = _render_server_table(detailed_data)
                        logger.info(f"Table container type: {type(table_container)}")
                        logger.info(f"Table container id: {getattr(table_container, 'id', 'NO_ID')}")
                        logger.info(f"Table container has children: {hasattr(table_container, 'children')}")
                        
                        history_entry = html.Div(f"Job {job_id} completed at {datetime.now().strftime('%H:%M:%S')}")
                        
                        # Store the result in cache so "Reload Model" can access it
                        try:
                            SH.RESULTS_CACHE['results'] = sanitized
                            SH.RESULTS_CACHE['loaded_at'] = time.time()
                            logger.info("Stored result in RESULTS_CACHE")
                        except Exception as cache_err:
                            logger.error(f"Failed to cache result: {cache_err}")
                        
                        # Ensure we're returning a proper Dash component with visible content
                        results_display = html.Div([
                            html.H4("Analysis Results", style={'color': '#fff', 'margin': '10px 0'}),
                            table_container,
                            server_table
                        ], style={'padding': '10px'})
                        
                        logger.info(f"Returning results_display to results-area with {len(detailed_data)} rows")
                        
                        return (
                            results_display, sanitized,
                            "Job completed.", {'display': 'block', 'backgroundColor': 'green'},
                            history_entry
                        )
                    except Exception as e:
                        logger.exception('Error rendering completed job result')
                        # Return a visible error div so headless tests can detect content
                        return html.Div([html.H4('Job completed but rendering failed'), html.Pre(str(e))]), no_update, "Job completed (render error)", {'display': 'block', 'backgroundColor': 'orange'}, no_update

                elif status == 'failed':
                    # job_info['result'] may contain error details
                    err = None
                    try:
                        err = job_info.get('result', {}).get('error') if isinstance(job_info.get('result'), dict) else job_info.get('error')
                    except Exception:
                        err = str(job_info.get('result'))
                    return (
                        html.Div([html.H4('Job failed'), html.Pre(str(err))]), no_update,
                        "Job failed.", {'display': 'block', 'backgroundColor': 'red'},
                        no_update
                    )
                else: # running
                    return (
                        no_update, no_update,
                        f"Job {job_id} is running...", {'display': 'block'},
                        no_update
                    )
            except Exception as e:
                logger.exception('Unexpected error while polling job status')
                return html.Div([html.H4('Polling failed'), html.Pre(str(e))]), no_update, "Polling error", {'display': 'block', 'backgroundColor': 'red'}, no_update

        # Handle manual refresh from cache
        # FIX: Check if 'reload-trigger' is IN triggered_id (it will be 'reload-trigger.data')
        if 'reload-trigger' in triggered_id and reload_data:
            try:
                logger.info("Refresh cached display triggered, loading from cache...")
                last = load_last_cached_results()
                if last:
                    sanitized = _sanitize_for_store(last)
                    detailed = sanitized.get('detailed', [])
                    logger.info(f"Loaded {len(detailed)} records from cache")
                    table, _ = _render_table_from_records(detailed)
                    logger.info("Table rendered successfully from cache")
                    return table, sanitized, "Reloaded from cache", {'display': 'block', 'backgroundColor': 'green'}, None
                else:
                    logger.warning("No cached data found")
                    return html.Div("No cached data available."), None, "No cached data", {'display': 'block', 'backgroundColor': 'orange'}, None
            except Exception as e:
                logger.error(f"Cache reload failed: {e}")
                import traceback
                traceback.print_exc()
                return html.Div(f"Failed to reload from cache: {str(e)}"), None, str(e), {'display': 'block', 'backgroundColor': 'red'}, None

        raise PreventUpdate

    @app.callback(
        Output('current-job', 'data'),
        Output('poll-interval', 'disabled'),
        Input('status', 'children'),
        State('current-job', 'data')
    )
    def manage_polling(status_text, job_id):
        """Enable/disable polling based on job status."""
        if not status_text:
            return job_id, True # No status, disable polling

        if "Started job" in status_text:
            new_job_id = status_text.split("Started job ")[-1]
            return new_job_id, False # Start polling
        elif "is running" in status_text:
            return job_id, False # Continue polling
        elif "completed" in status_text or "failed" in status_text:
            return None, True # Stop polling
        
        return job_id, True # Default to disabled

    @app.callback(
        Output('detail-modal', 'is_open'),
        Output('modal-content-body', 'children'),
        Input('results-table-client', 'active_cell'),
        Input('close-modal', 'n_clicks'),
        State('results-table-client', 'data'),
        State('trends-last-cached', 'data') # Use the new unique ID
    )
    def show_detail_modal(active_cell, close_clicks, table_data, last_cached):
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        triggered_id = ctx.triggered[0]['prop_id'].split('.')[0]

        if triggered_id == 'close-modal':
            return False, None

        if triggered_id == 'results-table-client' and active_cell:
            row_idx = active_cell['row']
            if not table_data or row_idx >= len(table_data):
                raise PreventUpdate
            
            record = table_data[row_idx]
            ticker = record.get('Ticker')
            
            # Find the full record from the original cached data
            full_record = None
            if last_cached and last_cached.get('detailed'):
                for r in last_cached['detailed']:
                    if r.get('Ticker') == ticker:
                        full_record = r
                        break
            
            if not full_record:
                return False, "Could not find full record."

            # Render a simple view of the full record
            content = html.Div([
                html.H4(f"Details for {ticker}"),
                html.Pre(json.dumps(full_record, indent=2))
            ])
            return True, content

        raise PreventUpdate

    @app.callback(Output('download-data', 'data'), Input('download-btn', 'n_clicks'))
    def download_csv(n_clicks):
        if n_clicks == 0:
            raise PreventUpdate
        
        try:
            # Use the shared helper to find the latest detailed CSV
            latest_csv_path = SH.get_latest_artifact_path('tech_report_detailed.csv')
            if latest_csv_path and os.path.exists(latest_csv_path):
                return dcc.send_file(latest_csv_path)
        except Exception as e:
            logger.error(f"Download failed: {e}")
        
        # Fallback: try to create from last cached results if file not found
        try:
            last = load_last_cached_results()
            if last and last.get('detailed'):
                df = pd.DataFrame(last['detailed'])
                return dcc.send_data_frame(df.to_csv, "market_trends_latest.csv", index=False)
        except Exception as e:
            logger.error(f"Fallback download failed: {e}")

        raise PreventUpdate

    @app.callback(
        Output('model-status', 'children'),
        Input('reload-model', 'n_clicks')
    )
    def reload_model(n_clicks):
        if n_clicks == 0:
            return "Model ready."
        
        try:
            importlib.reload(MT)
            return f"Model reloaded at {datetime.now().strftime('%H:%M:%S')}"
        except Exception as e:
            return f"Failed to reload model: {e}"

    @app.callback(
        Output('reload-trigger', 'data'),
        Input('refresh-cached', 'n_clicks')
    )
    def refresh_cached_display(n_clicks):
        if n_clicks == 0:
            raise PreventUpdate
        # Just trigger the reload by updating the store
        return {'timestamp': time.time()}

    @app.callback(
        Output('full-brief', 'style'),
        Output('full-brief', 'children'),
        Input('toggle-brief', 'n_clicks'),
        State('full-brief', 'style'),
        State('trends-last-cached', 'data') # Use the new unique ID
    )
    def toggle_full_brief(n_clicks, style, last_cached):
        if n_clicks == 0:
            raise PreventUpdate
        
        if style.get('display') == 'none':
            # Show the brief
            brief_text = "No brief available."
            if last_cached and last_cached.get('brief_text'):
                brief_text = last_cached['brief_text']
            return {'display': 'block'}, html.Pre(brief_text)
        else:
            # Hide the brief
            return {'display': 'none'}, None

    @app.callback(
        Output('compact-brief-wrapper', 'children'),
        Input('trends-last-cached', 'data') # Use the new unique ID
    )
    def update_compact_brief(last_cached):
        brief_text = None
        trend_label = None
        trend_tooltip = "Market trend analysis"
        
        # Try to get brief from the store first
        if last_cached and last_cached.get('brief_text'):
            brief_text = last_cached['brief_text']
            # Try to extract trend from cached data
            try:
                if last_cached.get('detailed') and len(last_cached['detailed']) > 0:
                    first_row = last_cached['detailed'][0]
                    if 'market_trend_label' in first_row:
                        trend_label = first_row['market_trend_label']
                        trend_composite = first_row.get('market_trend_composite', 0.0)
                        scores = {
                            'Price': first_row.get('market_trend_price_score', 0),
                            'MACD': first_row.get('market_trend_macd_score', 0),
                            'RSI': first_row.get('market_trend_rsi_score', 0),
                            'VIX': first_row.get('market_trend_vix_score', 0),
                        }
                        components = [f"{k}: {v:.2f}" for k, v in scores.items() if v != 0]
                        trend_tooltip = (
                            f"Composite: {trend_composite:.2f} | "
                            f"Components: {', '.join(components) if components else 'N/A'}"
                        )
            except Exception as e:
                logger.warning(f"Could not extract market trend label from cache: {e}")
        else:
            # Fallback: load from persisted outputs server-side
            try:
                logger.debug("Compact brief callback: trends-last-cached empty, loading from disk")
                persisted = load_last_cached_results()
                if persisted and persisted.get('brief_text'):
                    brief_text = persisted['brief_text']
                    logger.debug(f"Loaded brief from disk: {len(brief_text)} chars")
            except Exception as e:
                logger.error(f"Failed to load persisted brief: {e}")
        
        # If no trend label extracted, compute live
        if not trend_label:
            try:
                trend_result = _compute_live_market_trend()
                if trend_result:
                    trend_label = trend_result.get('label', 'Unknown')
                    trend_composite = trend_result.get('composite', 0.0)
                    scores = trend_result.get('scores', {})
                    components = [f"{k}: {v:.2f}" for k, v in scores.items()]
                    trend_tooltip = (
                        f"Composite: {trend_composite:.2f} | "
                        f"Components: {', '.join(components) if components else 'N/A'}"
                    )
            except Exception as e:
                logger.warning(f"Could not compute live market trend: {e}")
        
        if not brief_text:
            return html.Div("No brief available.")
        
        # Show a truncated version of the brief
        truncated = (brief_text[:300] + '...') if len(brief_text) > 300 else brief_text
        
        # Create trend badge
        trend_badge = html.Div()
        if trend_label:
            badge_colors = {
                'Strong Bull': '#10b981',  # Green
                'Bull': '#84cc16',         # Light green
                'Neutral': '#94a3b8',      # Gray
                'Bear': '#f59e0b',         # Orange
                'Strong Bear': '#ef4444',  # Red
            }
            badge_color = badge_colors.get(trend_label, '#6b7280')
            
            trend_badge = html.Div([
                html.Span(
                    f"🔥 {trend_label}",
                    title=trend_tooltip,
                    style={
                        'backgroundColor': badge_color,
                        'color': 'white',
                        'padding': '6px 16px',
                        'borderRadius': '6px',
                        'fontSize': '15px',
                        'fontWeight': 'bold',
                        'display': 'inline-block',
                        'marginBottom': '12px',
                        'cursor': 'help',
                        'boxShadow': '0 2px 4px rgba(0,0,0,0.2)',
                    }
                )
            ])
        
        return html.Div([
            html.H5("Compact Brief"),
            trend_badge,  # Display badge ABOVE the text
            html.P(truncated)
        ])

    app.clientside_callback(
        """
        function(n_clicks, text) {
            if (n_clicks > 0 && text) {
                fetch('/log-message', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ message: text })
                });
            }
            return '';
        }
        """,
        Output('debug-output', 'children'),
        Input('debug-log-btn', 'n_clicks'),
        State('debug-input', 'value'),
        prevent_initial_call=True
    )

# End of callbacks for market_trends tab.

