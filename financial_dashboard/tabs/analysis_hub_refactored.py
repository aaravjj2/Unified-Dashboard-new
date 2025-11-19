"""
Analysis Hub - Refactored UI Tab (Lightweight API Client)
==========================================================
Makes API calls to the Analysis Hub backend service via API Gateway.
No heavy analysis imports - pure UI client.

Architecture:
- Calls API Gateway at http://localhost:8049/api/analysis/*
- Job-based workflow: create job → poll status → display results
- Polling interval: 2 seconds
- Max polling: 150 attempts (5 minutes)
"""

import logging
from datetime import datetime, timedelta
import requests
import pandas as pd
import numpy as np
from dash import dcc, html, Input, Output, State, dash_table, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import dash
import plotly.graph_objects as go
import plotly.express as px
from financial_dashboard from financial_dashboard import _shared as SH
from services import analysis_service as analysis_service
# import lightweight picks helpers (preferred) and fall back to attribution helpers
try:
    from tabs.picks_helpers import _find_latest_picks_generic, _load_picks_df
except Exception:
    try:
        from tabs.attribution_analysis import _find_latest_picks_generic, _load_picks_df
    except Exception:
        # Fallbacks if helpers are not importable
        def _find_latest_picks_generic(patterns=None):
            return None
        def _load_picks_df(path, limit=50):
            return None

logger = logging.getLogger(__name__)

# API Configuration
API_GATEWAY_URL = "http://localhost:8049"
POLL_INTERVAL_MS = 2000  # 2 seconds
MAX_POLL_ATTEMPTS = 150  # 5 minutes total


# ============================================================================
# LAYOUT
# ============================================================================

def layout():
    """Build the Analysis Hub layout with sub-tabs."""
    return dbc.Container([
        html.H2("Analysis Hub", className="mt-3 mb-3"),
        
        # Store for job tracking - NAMESPACED to avoid conflicts
        dcc.Store(id='hub-attr-job-store', data=None),
        dcc.Store(id='hub-attr-results-store', data=None),
        dcc.Store(id='hub-attr-poll-counter', data=0),
        
        # Polling interval component
        dcc.Interval(
            id='hub-attr-poll-interval',
            interval=POLL_INTERVAL_MS,
            disabled=True,
            n_intervals=0
        ),
        
        # Sub-tabs
        dbc.Tabs(id="analysis-hub-subtabs", active_tab="portfolio-analytics-tab", children=[
            # Attribution Analysis Tab
            dbc.Tab(label="Attribution Analysis", tab_id="attr-analysis-tab", children=[
                dbc.Container([
                    # Controls section
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Analysis Configuration", className="mb-3"),
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Picks Type:", id='label-hub-attr-picks-type'),
                                    html.Div(children=[
                                        dcc.Dropdown(
                                            id='hub-attr-picks-type',
                                            options=[
                                                {'label': 'Weekly Picks', 'value': 'weekly'},
                                                {'label': 'Monthly Picks', 'value': 'monthly'}
                                            ],
                                            value='weekly',
                                            clearable=False
                                        )
                                    ], **{'aria-labelledby': 'label-hub-attr-picks-type'})
                                ], width=3),
                                dbc.Col([
                                    html.Label("Date Range:", id='label-hub-attr-date-range'),
                                    html.Div(children=[
                                        dcc.DatePickerRange(
                                            id='hub-attr-date-range',
                                            start_date=(datetime.now() - timedelta(days=90)).date(),
                                            end_date=datetime.now().date(),
                                            display_format='YYYY-MM-DD'
                                        )
                                    ], **{'aria-labelledby': 'label-hub-attr-date-range'})
                                ], width=3),
                                dbc.Col([
                                    html.Label("Horizon:", id='label-hub-attr-horizon'),
                                    html.Div(children=[
                                        dcc.Dropdown(
                                            id='hub-attr-horizon',
                                            options=[
                                                {'label': '1 Week', 'value': '1w'},
                                                {'label': '1 Month', 'value': '1m'},
                                                {'label': '3 Months', 'value': '3m'}
                                            ],
                                            value='1w',
                                            clearable=False
                                        )
                                    ], **{'aria-labelledby': 'label-hub-attr-horizon'})
                                ], width=3),
                                dbc.Col([
                                    html.Label("Market Regime:", id='label-hub-attr-regime'),
                                    html.Div(children=[
                                        dcc.Dropdown(
                                            id='hub-attr-regime-filter',
                                            options=[
                                                {'label': 'All Periods', 'value': 'all'},
                                                {'label': 'Bull Market', 'value': 'bull'},
                                                {'label': 'Bear Market', 'value': 'bear'},
                                                {'label': 'High Volatility', 'value': 'high_vol'},
                                                {'label': 'Low Volatility', 'value': 'low_vol'}
                                            ],
                                            value='all',
                                            clearable=False
                                        )
                                    ], **{'aria-labelledby': 'label-hub-attr-regime'})
                                ], width=3)
                            ], className="mb-3"),
                            
                            dbc.Row([
                                dbc.Col([
                                    dbc.Button(
                                        "Run Attribution Analysis",
                                        id='hub-attr-run-button',
                                        color='primary',
                                        className="me-2"
                                    ),
                                    dbc.Button(
                                        "Export Results",
                                        id='hub-attr-export-button',
                                        color='secondary',
                                        disabled=True
                                    )
                                ])
                            ])
                        ])
                    ], className="mb-4"),
                    
                    # Status/Progress
                    dbc.Alert(
                        id='hub-attr-status',
                        color='info',
                        is_open=False,
                        duration=None  # Don't auto-hide while polling
                    ),
                    
                    # Initial instruction panel
                    dbc.Alert([
                        html.H5("📊 Welcome to Attribution Analysis", className="alert-heading"),
                        html.P("This tool analyzes the performance attribution of your stock picks over time.", className="mb-2"),
                        html.Hr(),
                        html.P([
                            html.Strong("To get started: "),
                            "Configure your analysis parameters above and click ",
                            html.Strong('"Run Attribution Analysis"'),
                            " to see results."
                        ], className="mb-2"),
                        html.P("Results will include alpha/beta breakdown, factor contributions, and detailed pick analysis.", className="mb-0 small", style={'color': '#000000'})
                    ], id='attr-initial-instructions', color='info', className="mb-4", style={'display': 'block'}),
                    
                    # Results section
                    html.Div(id='attr-results-container', children=[
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Portfolio Attribution Summary", className="mb-3"),
                                html.Div(id='attr-portfolio-summary')
                            ])
                        ], className="mb-4"),
                        
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Alpha vs Beta Breakdown", className="mb-3"),
                                dcc.Graph(id='attr-alpha-beta-chart')
                            ])
                        ], className="mb-4"),
                        
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Factor Contributions", className="mb-3"),
                                html.P("Top factors driving portfolio performance", className="small", style={'color': '#000000'}),
                                dcc.Graph(id='attr-factor-chart')
                            ])
                        ], className="mb-4"),
                        
                        dbc.Card([
                            dbc.CardBody([
                                html.H5("Per-Pick Attribution Details", className="mb-3"),
                                html.Div(id='attr-picks-table')
                            ])
                        ])
                    ], style={'display': 'none'})
                ], fluid=True, className="mt-3")
            ]),
            
            # Portfolio Analytics Tab (restored)
            dbc.Tab(label="Portfolio Analytics", tab_id="portfolio-analytics-tab", children=[
                dbc.Container([
                    html.H5("Portfolio Analytics", className="mt-3 mb-3"),
                    html.P("Analyze portfolio performance, risk metrics, and optimization opportunities.", style={'color': '#000000'}),
                    dbc.Row([
                        dbc.Col([dbc.Card([dbc.CardBody([html.H6("Total Return", style={'color': '#000000'}), html.H3(id='hub-pa-total-return', children="0.00%")])])], width=3),
                        dbc.Col([dbc.Card([dbc.CardBody([html.H6("Sharpe Ratio", style={'color': '#000000'}), html.H3(id='hub-pa-sharpe', children="0.00")])])], width=3),
                        dbc.Col([dbc.Card([dbc.CardBody([html.H6("Max Drawdown", style={'color': '#000000'}), html.H3(id='hub-pa-drawdown', children="0.00%")])])], width=3),
                        dbc.Col([dbc.Card([dbc.CardBody([html.H6("Win Rate", style={'color': '#000000'}), html.H3(id='hub-pa-win-rate', children="0.00%")])])], width=3)
                    ], className="mb-4"),
                    dbc.Button("Calculate Analytics", id='hub-pa-calc-btn', color='primary', className="mb-3"),
                    dbc.Row([
                        dbc.Col([dbc.Card([dbc.CardBody([html.H6("Portfolio Performance Over Time"), dcc.Graph(id='hub-pa-performance-chart')])])], width=6),
                        dbc.Col([dbc.Card([dbc.CardBody([html.H6("Risk Distribution"), dcc.Graph(id='hub-pa-risk-chart')])])], width=6)
                    ], className="mb-4"),
                    html.H6("Exposure Analysis", className="mt-4 mb-3"),
                    dbc.Row([
                        dbc.Col([dbc.Card([dbc.CardBody([html.H6("Sector Exposure"), dcc.Graph(id='hub-pa-sector-exposure')])])], width=6),
                        dbc.Col([dbc.Card([dbc.CardBody([html.H6("Factor Exposure"), dcc.Graph(id='hub-pa-factor-exposure'), html.Div(id='hub-pa-sector-counts', className='mt-2'), html.Div(id='hub-pa-ticker-vol-table', className='mt-2')])])], width=6)
                    ], className="mb-4"),
                    html.H6("Risk Analysis", className="mt-4 mb-3"),
                    dbc.Row([dbc.Col([dbc.Card([dbc.CardBody([html.H6("Contribution to VaR"), dcc.Graph(id='hub-pa-var-contribution')])])], width=12)], className="mb-4"),
                    html.H6("Transaction Cost Analysis", className="mt-4 mb-3"),
                    dbc.Row([
                        dbc.Col([dbc.Card([dbc.CardBody([html.H6("Slippage Over Time"), dcc.Graph(id='hub-pa-slippage-chart')])])], width=6),
                        dbc.Col([dbc.Card([dbc.CardBody([html.H6("Total Trading Costs", style={'color': '#000000'}), html.H3(id='hub-pa-total-costs', children="$0.00"), html.P(id='hub-pa-cost-breakdown', className="small", style={'color': '#000000'})])])], width=6)
                    ])
                ], fluid=True)
            ]),
        ])
    ], fluid=True)


# ============================================================================
# CALLBACKS
# ============================================================================

def register_callbacks(app):
    """Register all callbacks for the Analysis Hub tab."""
    
    @app.callback(
        [Output('hub-attr-status', 'children'),
         Output('hub-attr-status', 'is_open'),
         Output('hub-attr-status', 'color'),
         Output('hub-attr-job-store', 'data'),
         Output('hub-attr-poll-interval', 'disabled'),
         Output('attr-initial-instructions', 'style')],
        [Input('hub-attr-run-button', 'n_clicks'),
         Input('hub-attr-poll-interval', 'n_intervals')],
        [State('hub-attr-picks-type', 'value'),
         State('hub-attr-date-range', 'start_date'),
         State('hub-attr-date-range', 'end_date'),
         State('hub-attr-horizon', 'value'),
         State('hub-attr-regime-filter', 'value'),
         State('hub-attr-job-store', 'data'),
         State('hub-attr-poll-counter', 'data')]
    )
    def handle_attribution_workflow(n_clicks, n_intervals, picks_type, start_date, 
                                    end_date, horizon, regime_filter, job_data, poll_counter):
        """
        Unified callback handling three workflows:
        1. User clicks Run button → Create job via API
        2. Polling → Check job status
        3. Job complete → Store results
        """
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        
        trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        # FLOW 1: User clicked Run button
        if trigger_id == 'hub-attr-run-button':
            if not n_clicks:
                raise PreventUpdate
            
            try:
                # Create job via API Gateway
                job_request = {
                    "picks_type": picks_type,
                    "start_date": start_date,
                    "end_date": end_date,
                    "horizon": horizon,
                    "regime_filter": regime_filter
                }
                
                response = requests.post(
                    f"{API_GATEWAY_URL}/api/analysis/jobs",
                    json=job_request,
                    timeout=10
                )
                
                if response.status_code != 200:
                    return (
                        f"Failed to create analysis job: {response.text}",
                        True, 'danger', None, True, {'display': 'block'}
                    )
                
                job_info = response.json()
                job_id = job_info.get('job_id')
                
                logger.info(f"Created attribution job: {job_id}")
                
                return (
                    "Attribution analysis started... checking status",
                    True, 'info',
                    {'job_id': job_id, 'poll_count': 0},
                    False,  # Enable polling
                    {'display': 'none'}
                )
                
            except Exception as e:
                logger.error(f"Error creating job: {e}")
                return (
                    f"Error: {str(e)}",
                    True, 'danger', None, True, {'display': 'block'}
                )
        
        # FLOW 2: Polling for job status
        elif trigger_id == 'hub-attr-poll-interval':
            if not job_data or 'job_id' not in job_data:
                raise PreventUpdate
            
            job_id = job_data['job_id']
            poll_count = job_data.get('poll_count', 0) + 1
            
            # Check max attempts
            if poll_count > MAX_POLL_ATTEMPTS:
                return (
                    "Analysis timed out after 5 minutes",
                    True, 'warning', None, True, {'display': 'block'}
                )
            
            try:
                # Poll job status
                response = requests.get(
                    f"{API_GATEWAY_URL}/api/analysis/jobs/{job_id}",
                    timeout=10
                )
                
                if response.status_code != 200:
                    return (
                        f"Failed to check job status: {response.text}",
                        True, 'danger', None, True, {'display': 'block'}
                    )
                
                job_status = response.json()
                status = job_status.get('status')
                progress = job_status.get('progress', 0.0)
                
                if status == 'completed':
                    result = job_status.get('result', {})
                    logger.info(f"Job {job_id} completed")
                    
                    # Stop polling and trigger results display
                    # Store results in the results store and render
                    try:
                        # Prepare a simple summary HTML to populate the UI
                        summary = result.get('summary') if isinstance(result, dict) else None
                        metrics = result.get('summary') or result.get('metrics') or result.get('summary', {})
                        # Build a small summary card
                        summary_card = html.Div([
                            dbc.Row([
                                dbc.Col(html.Div([html.H6('Total Return'), html.H4(f"{metrics.get('total_return', metrics.get('expected_return', 0))}%")]), width=3),
                                dbc.Col(html.Div([html.H6('Sharpe'), html.H4(f"{metrics.get('sharpe', metrics.get('sharpe_ratio', 0))}")]), width=3),
                                dbc.Col(html.Div([html.H6('Max Drawdown'), html.H4(f"{metrics.get('max_drawdown', 0)}%")]), width=3)
                            ])
                        ])

                        # Simple per-pick table if available
                        picks_children = html.Div()
                        if isinstance(result.get('winners'), list) or isinstance(result.get('top_picks'), list):
                            rows = result.get('winners') or result.get('top_picks')
                            df = pd.DataFrame(rows)
                            picks_children = dash_table.DataTable(
                                columns=[{'name': c, 'id': c} for c in df.columns],
                                data=df.fillna('').to_dict(orient='records'),
                                page_size=10,
                                style_table={'overflowX': 'auto'}
                            )

                        children = html.Div([summary_card, html.Hr(), picks_children])

                    except Exception:
                        children = html.Div([html.P('Analysis complete — results available.' )])

                    return (
                        "Analysis complete! Processed results.",
                        True, 'success',
                        {'job_id': job_id, 'result': result, 'completed': True},
                        True,  # Disable polling
                        {'display': 'none'}
                    )
                
                elif status == 'failed':
                    error = job_status.get('error', 'Unknown error')
                    return (
                        f"Analysis failed: {error}",
                        True, 'danger', None, True, {'display': 'block'}
                    )
                
                else:
                    # Still running
                    return (
                        f"Running analysis... {int(progress * 100)}% (attempt {poll_count}/{MAX_POLL_ATTEMPTS})",
                        True, 'info',
                        {'job_id': job_id, 'poll_count': poll_count},
                        False,  # Continue polling
                        {'display': 'none'}
                    )
                
            except Exception as e:
                logger.error(f"Error polling job: {e}")
                return (
                    f"Error checking status: {str(e)}",
                    True, 'danger', None, True, {'display': 'block'}
                )
        
        raise PreventUpdate
    
    
    @app.callback(
        [Output('hub-attr-results-store', 'data'),
         Output('attr-results-container', 'style'),
         Output('hub-attr-export-button', 'disabled')],
        [Input('hub-attr-job-store', 'data')]
    )
    def update_results_store(job_data):
        """Extract results from completed job."""
        if not job_data or not job_data.get('completed'):
            raise PreventUpdate
        
        result = job_data.get('result')
        if result:
            return result, {'display': 'block'}, False
        
        raise PreventUpdate
    
    
    @app.callback(
        Output('attr-portfolio-summary', 'children'),
        [Input('hub-attr-results-store', 'data')]
    )
    def update_portfolio_summary(results):
        """Display portfolio-level attribution summary."""
        if not results:
            raise PreventUpdate
        
        portfolio = results.get('portfolio', {})
        
        return dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Return", style={'color': '#000000'}),
                        html.H4(f"{portfolio.get('total_return', 0):.2%}")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Alpha", style={'color': '#000000'}),
                        html.H4(f"{portfolio.get('alpha', 0):.2%}", 
                               style={'color': '#10b981' if portfolio.get('alpha', 0) > 0 else '#ef4444'})
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Beta", style={'color': '#000000'}),
                        html.H4(f"{portfolio.get('beta', 0):.3f}")
                    ])
                ])
            ], width=3),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Beta Contribution", style={'color': '#000000'}),
                        html.H4(f"{portfolio.get('beta_contrib', 0):.2%}")
                    ])
                ])
            ], width=3)
        ])
    
    
    @app.callback(
        Output('attr-alpha-beta-chart', 'figure'),
        [Input('hub-attr-results-store', 'data')]
    )
    def update_alpha_beta_chart(results):
        """Create alpha vs beta visualization."""
        if not results:
            return go.Figure()
        
        per_pick = results.get('per_pick', [])
        if not per_pick:
            return go.Figure()
        
        df = pd.DataFrame(per_pick)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['beta'],
            y=df['alpha'],
            mode='markers+text',
            text=df['ticker'],
            textposition='top center',
            marker=dict(
                size=10,
                color=df['alpha'],
                colorscale='RdYlGn',
                showscale=True,
                colorbar=dict(title="Alpha")
            ),
            name='Picks'
        ))
        
        # Reference lines
        fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
        fig.add_vline(x=1, line_dash="dash", line_color="gray", opacity=0.5)
        
        fig.update_layout(
            title="Alpha vs Beta by Pick",
            xaxis_title="Beta (Market Sensitivity)",
            yaxis_title="Alpha (Excess Return)",
            hovermode='closest',
            template='plotly_white'
        )
        
        return fig
    
    
    @app.callback(
        Output('attr-factor-chart', 'figure'),
        [Input('hub-attr-results-store', 'data')]
    )
    def update_factor_chart(results):
        """Create factor contribution chart."""
        if not results:
            return go.Figure()
        
        factors = results.get('portfolio', {}).get('top_factors', [])
        if not factors:
            return go.Figure()
        
        factor_names = [f['factor'] for f in factors]
        factor_values = [f['contribution'] for f in factors]
        
        fig = go.Figure(go.Bar(
            x=factor_names,
            y=factor_values,
            marker=dict(
                color=factor_values,
                colorscale='RdYlGn',
                showscale=False
            )
        ))
        
        fig.update_layout(
            title="Top Factor Contributions",
            xaxis_title="Factor",
            yaxis_title="Contribution",
            template='plotly_white'
        )
        
        return fig
    
    
    @app.callback(
        Output('attr-picks-table', 'children'),
        [Input('hub-attr-results-store', 'data')]
    )
    def update_picks_table(results):
        """Display per-pick attribution details."""
        if not results:
            raise PreventUpdate
        
        per_pick = results.get('per_pick', [])
        if not per_pick:
            return html.P("No pick-level data available")
        
        df = pd.DataFrame(per_pick)
        
        # Format numeric columns
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        for col in numeric_cols:
            if col in df.columns:
                df[col] = df[col].round(4)
        
        return dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[{'name': col, 'id': col} for col in df.columns],
            style_table={'overflowX': 'auto'},
            style_cell={
                'textAlign': 'left',
                'padding': '10px',
                'fontSize': '14px'
            },
            style_header={
                'backgroundColor': 'rgb(230, 230, 230)',
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {
                    'if': {'column_id': 'alpha'},
                    'backgroundColor': 'rgba(16, 185, 129, 0.1)'
                },
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': 'rgb(248, 248, 248)'
                }
            ],
            page_size=10,
            sort_action='native',
            filter_action='native'
        )


    # -------------------------
    # Portfolio Analytics (simplified) callback
    # -------------------------
    # Disable lightweight PA callback in this refactored UI to avoid duplicate registrations.
    # The full implementation in `tabs/attribution_analysis.py` handles the Portfolio Analytics
    # functionality. Commenting out the decorator below prevents this function from being
    # registered as a Dash callback while keeping the helper function for reference.
    # Note: The full Portfolio Analytics callback is implemented in tabs/attribution_analysis.py.
    # This in-file helper remains for reference but is intentionally not registered as a callback
    # to avoid duplicate callback registration.
    def calculate_portfolio_analytics(n_clicks):
        logger.info('calculate_portfolio_analytics clicked=%r', n_clicks)
        if not n_clicks:
            raise PreventUpdate

        # Default empty outputs
        empty_fig = go.Figure()
        try:
            # Try Alpaca first (best fidelity). If unavailable, fall back to picks-based equity.
            try:
                from src.utils.secrets import get_alpaca_credentials
                from alpaca_trade_api import REST
                key_id, secret, base_url = get_alpaca_credentials()
                if key_id and secret:
                    api = REST(key_id, secret, base_url)
                    portfolio_history = api.get_portfolio_history(period='3M', timeframe='1D')
                    portfolio_data = pd.DataFrame({'equity': portfolio_history.equity, 'timestamp': pd.to_datetime(portfolio_history.timestamp, unit='s')}).set_index('timestamp')
                else:
                    portfolio_data = None
            except Exception:
                portfolio_data = None

            if portfolio_data is None or portfolio_data.empty:
                # Use the analysis service loader to find picks in the recent window (last 90 days)
                try:
                    end = pd.Timestamp.now().normalize()
                    start = end - pd.Timedelta(days=90)
                    picks_df = analysis_service._load_picks_in_range('weekly', start_date=start.date().isoformat(), end_date=end.date().isoformat())
                except Exception:
                    picks_df = None

                if picks_df is None or picks_df.empty:
                    # Nothing to compute - return diagnostics
                    logger.warning('PA_DEBUG - no picks found via analysis_service for last 90 days')
                    detail = 'No picks found for recent date range (last 90 days). Try uploading picks or expand date window.'
                    return ('0.00%', '0.00', '0.00%', '0.00%', empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, '$0.00', detail, html.Div(), html.Div())

                # Build a synthetic equity curve using yfinance — equal-weight
                try:
                    tickers = picks_df['ticker'].astype(str).tolist()
                    import yfinance as yf
                    end = pd.Timestamp.now().normalize()
                    start = end - pd.Timedelta(days=90)
                    combined = None
                    for t in tickers:
                        try:
                            h = yf.download(t, start=start, end=end + pd.Timedelta(days=1), progress=False, auto_adjust=True, threads=False)
                            if 'Close' in h and not h.empty:
                                s = h['Close'].pct_change().fillna(0)
                                s.name = t
                                combined = pd.concat([combined, s], axis=1) if combined is not None else s.to_frame()
                        except Exception:
                            continue

                    if combined is None or combined.empty:
                        return ('0.00%', '0.00', '0.00%', '0.00%', empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, '$0.00', '', html.Div(), html.Div())

                    # equal-weight portfolio returns
                    returns = combined.mean(axis=1)
                    equity = (1 + returns).cumprod() * 10000
                    total_return = equity.iloc[-1] / equity.iloc[0] - 1
                    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
                    drawdown = (equity / equity.cummax() - 1).min()
                    win_rate = (returns > 0).sum() / len(returns)

                    perf_fig = go.Figure(); perf_fig.add_trace(go.Scatter(x=equity.index, y=equity.values, mode='lines', name='Equity'))
                    risk_fig = go.Figure(); risk_fig.add_trace(go.Histogram(x=returns * 100, nbinsx=30))

                    return (f"{total_return*100:.2f}%", f"{sharpe:.2f}", f"{drawdown*100:.2f}%", f"{win_rate*100:.1f}%", perf_fig, risk_fig, empty_fig, empty_fig, empty_fig, empty_fig, '$0.00', '', html.Div(), html.Div())

                except Exception as e:
                    logger.exception('PA fallback error: %s', e)
                    return ('0.00%', '0.00', '0.00%', '0.00%', empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, '$0.00', f'Error: {e}', html.Div(), html.Div())

            # If we have real portfolio_data from Alpaca compute metrics
            returns = portfolio_data['equity'].pct_change().dropna()
            total_return = portfolio_data['equity'].iloc[-1] / portfolio_data['equity'].iloc[0] - 1
            sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
            cumulative = (1 + returns).cumprod()
            running_max = cumulative.cummax()
            drawdown_val = (cumulative / running_max - 1).min()
            win_rate = (returns > 0).sum() / len(returns)

            perf_fig = go.Figure(); perf_fig.add_trace(go.Scatter(x=portfolio_data.index, y=portfolio_data['equity'], mode='lines', name='Portfolio Value'))
            risk_fig = go.Figure(); risk_fig.add_trace(go.Histogram(x=returns * 100, nbinsx=30))

            return (f"{total_return*100:.2f}%", f"{sharpe:.2f}", f"{drawdown_val*100:.2f}%", f"{win_rate*100:.1f}%", perf_fig, risk_fig, empty_fig, empty_fig, empty_fig, empty_fig, '$0.00', '', html.Div(), html.Div())

        except Exception as e:
            # Log full exception and return informative defaults so the UI updates visibly
            logger.exception('Error calculating portfolio analytics: %s', e)
            detail = f'Error calculating analytics: {str(e)}'
            return ('0.00%', '0.00', '0.00%', '0.00%', empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, empty_fig, '$0.00', detail, html.Div(), html.Div())


    # -------------------------
    # Scenario Analysis callbacks
    # -------------------------

    @app.callback(
        [Output('scenario-job-store', 'data'),
         Output('scenario-poll-interval', 'disabled')],
        [Input('scenario-run-btn', 'n_clicks')],
        [State('scenario-name', 'value'),
         State('scenario-universe', 'value'),
         State('scenario-horizon', 'value')]
    )
    def start_scenario_job(n_clicks, name, universe, horizon):
        if not n_clicks:
            raise PreventUpdate

        payload = {'name': name, 'universe': universe, 'horizon': horizon}
        try:
            r = requests.post(f"{API_GATEWAY_URL}/api/research/scenario-jobs", json=payload, timeout=10)
            r.raise_for_status()
            job = r.json()
            job_id = job.get('job_id')
            if job_id:
                SH.log(f"Started scenario job {job_id}")
                return {'job_id': job_id, 'poll_count': 0}, False
        except Exception as e:
            logger.error(f"Failed to start scenario job: {e}")

        # on failure, keep polling disabled
        return None, True


    @app.callback(
        [Output('scenario-job-store', 'data'),
         Output('scenario-poll-interval', 'disabled'),
         Output('scenario-results-area', 'children')],
        [Input('scenario-poll-interval', 'n_intervals')],
        [State('scenario-job-store', 'data')]
    )
    def poll_scenario_job(n_intervals, store):
        if not store or 'job_id' not in store:
            raise PreventUpdate

        job_id = store.get('job_id')
        poll_count = store.get('poll_count', 0) + 1

        # check max attempts
        if poll_count > MAX_POLL_ATTEMPTS:
            SH.log(f"Scenario job {job_id} timed out")
            return None, True, html.Div([dbc.Alert('Scenario timed out after 5 minutes', color='warning')])

        # first try in-process shared registry
        status = None
        try:
            status = SH.get_job_status(job_id)
        except Exception:
            status = None

        if not status:
            # try gateway
            try:
                r = requests.get(f"{API_GATEWAY_URL}/api/research/jobs/{job_id}", timeout=6)
                if r.status_code == 200:
                    status = r.json()
            except Exception as e:
                SH.log(f"Scenario poll gateway error: {e}")

        if not status:
            # update poll count and continue
            return {'job_id': job_id, 'poll_count': poll_count}, False, dash.no_update

        state = status.get('state') or status.get('status')

        if state == 'completed' or state == 'done':
            result = status.get('result') or {}

            # build summary cards
            summary = result.get('summary', {}) if isinstance(result, dict) else {}
            picks = result.get('picks', []) if isinstance(result, dict) else []

            # table of picks
            table = dash_table.DataTable(
                columns=[{'name': k, 'id': k} for k in (picks[0].keys() if picks else [])],
                data=picks,
                page_size=10,
                style_table={'overflowX': 'auto'}
            )

            summary_cards = dbc.Row([
                dbc.Col(dbc.Card(dbc.CardBody([html.H6(k), html.P(str(v))])), width=2)
                for k, v in summary.items()
            ])

            # optional charts: returns series and drawdown
            returns_fig = go.Figure()
            drawdown_fig = go.Figure()

            # prefer time series fields: 'equity_curve' (list of dicts with date/value) or 'returns_series'
            series = None
            if isinstance(result.get('equity_curve'), list) and result.get('equity_curve'):
                try:
                    df_series = pd.DataFrame(result.get('equity_curve'))
                    # expect columns ['date','value'] or ['timestamp','equity']
                    if 'date' in df_series.columns:
                        df_series['date'] = pd.to_datetime(df_series['date'])
                    elif 'timestamp' in df_series.columns:
                        df_series['date'] = pd.to_datetime(df_series['timestamp'])
                    # infer equity column
                    if 'value' in df_series.columns:
                        df_series['equity'] = df_series['value']
                    elif 'equity' in df_series.columns:
                        pass
                    series = df_series
                except Exception:
                    series = None
            elif isinstance(result.get('returns_series'), list) and result.get('returns_series'):
                try:
                    df_series = pd.DataFrame(result.get('returns_series'))
                    if 'date' in df_series.columns:
                        df_series['date'] = pd.to_datetime(df_series['date'])
                    series = df_series
                except Exception:
                    series = None

            if series is not None and not series.empty:
                # build returns plot if returns column exists
                if 'returns' in series.columns:
                    returns_fig.add_trace(go.Scatter(x=series['date'], y=series['returns'], mode='lines', name='Returns'))
                    returns_fig.update_layout(title='Returns Series', xaxis_title='Date', yaxis_title='Returns', template='plotly_white')

                # build equity/drawdown plot
                if 'equity' in series.columns:
                    series = series.sort_values('date')
                    series['peak'] = series['equity'].cummax()
                    series['drawdown'] = (series['equity'] - series['peak']) / series['peak']
                    drawdown_fig.add_trace(go.Scatter(x=series['date'], y=series['drawdown'], mode='lines', name='Drawdown', line=dict(color='crimson')))
                    drawdown_fig.update_layout(title='Drawdown', xaxis_title='Date', yaxis_title='Drawdown', template='plotly_white')

            charts = html.Div([
                dbc.Row([
                    dbc.Col(dcc.Graph(figure=returns_fig), width=6),
                    dbc.Col(dcc.Graph(figure=drawdown_fig), width=6)
                ])
            ])

            children = html.Div([summary_cards, html.Hr(), charts, html.Hr(), table])

            # stop polling and return results
            return None, True, children

        elif state == 'failed':
            error = status.get('error', 'Unknown')
            return None, True, html.Div([dbc.Alert(f"Scenario failed: {error}", color='danger')])

        # still running
        return {'job_id': job_id, 'poll_count': poll_count}, False, dash.no_update
