"""
Volatility Lab - Compact Single-Tab 4-Panel Layout
==================================================

Agent-1B Implementation: Compact, production-ready volatility analytics.

Architecture:
- Single tab with 4 panels in 2x2 grid
- Clean API integration (/api/volsurface/*)
- Deterministic fixture support (VOLLAB_DETERMINISTIC=1)
- DB persistence with JSON fallback
- Newton-Raphson solver with Brent fallback

Panels:
1. Overview - Quick metrics and last surface summary
2. IV Surface - Primary calculation canvas with heatmap
3. Signals + Backtest - Strategy signals and backtesting
4. Diagnostics - Collapsible solver logs and debug info

Owner: Agent-1B
Status: Scaffold Complete
"""

import logging
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Stable component IDs per spec
COMPONENT_IDS = {
    # Overview panel
    'overview_last_surface': 'vl-overview-last-surface',
    'overview_atm_iv': 'vl-overview-atm-iv',
    'overview_term_30': 'vl-overview-term-30',
    'overview_term_60': 'vl-overview-term-60',
    'overview_term_90': 'vl-overview-term-90',
    'compute_quick_btn': 'vl-compute-quick-btn',
    'overview_refresh_btn': 'vl-overview-refresh-btn',
    
    # IV Surface panel
    'calc_ticker': 'vl-calc-ticker',
    'calc_expiry': 'vl-calc-expiry',
    'calc_strike_range': 'vl-calc-strike-range',
    'calc_run_btn': 'vl-calc-run-btn',
    'heatmap': 'vl-heatmap',
    'iv_metrics_table': 'vl-iv-metrics-table',
    'iv_export_btn': 'vl-iv-export-btn',
    'explorer_date_slider': 'vl-explorer-date-slider',
    
    # Signals + Backtest panel
    'signal_run_btn': 'vl-signal-run-btn',
    'signal_table': 'vl-signal-table',
    'signal_paper_order_btn': 'vl-signal-paper-order-btn',
    'backtest_run_btn': 'vl-backtest-run-btn',
    'backtest_results': 'vl-backtest-results',
    'backtest_export_btn': 'vl-backtest-export-btn',
    
    # Diagnostics panel
    'diag_solver_log': 'vl-diag-solver-log',
    'diag_iterations': 'vl-diag-iterations',
    'diag_last_payload': 'vl-diag-last-payload',
    'diag_export_log': 'vl-diag-export-log',
}


def create_overview_panel():
    """Panel 1: Overview - Quick metrics and surface summary"""
    return dbc.Card([
        dbc.CardHeader([
            html.H5("📊 Overview", className="mb-0"),
            dbc.Button("🔄", id=COMPONENT_IDS['overview_refresh_btn'], 
                      size="sm", color="link", className="float-end")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div("Last Surface", className="text-muted small"),
                    html.H6(id=COMPONENT_IDS['overview_last_surface'], 
                           children="No data", className="mb-0")
                ], width=6),
                dbc.Col([
                    html.Div("ATM IV", className="text-muted small"),
                    html.H6(id=COMPONENT_IDS['overview_atm_iv'], 
                           children="--", className="mb-0")
                ], width=6),
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    html.Div("30D Term", className="text-muted small"),
                    html.Span(id=COMPONENT_IDS['overview_term_30'], children="--")
                ], width=4),
                dbc.Col([
                    html.Div("60D Term", className="text-muted small"),
                    html.Span(id=COMPONENT_IDS['overview_term_60'], children="--")
                ], width=4),
                dbc.Col([
                    html.Div("90D Term", className="text-muted small"),
                    html.Span(id=COMPONENT_IDS['overview_term_90'], children="--")
                ], width=4),
            ], className="mb-3"),
            dbc.Button("⚡ Quick Compute", 
                      id=COMPONENT_IDS['compute_quick_btn'],
                      color="primary", size="sm", className="w-100")
        ])
    ], className="h-100")


def create_iv_surface_panel():
    """Panel 2: IV Surface - Primary calculation canvas"""
    return dbc.Card([
        dbc.CardHeader(html.H5("📈 IV Surface Calculator", className="mb-0")),
        dbc.CardBody([
            # Input controls
            dbc.Row([
                dbc.Col([
                    html.Label("Ticker", className="small"),
                    dcc.Input(id=COMPONENT_IDS['calc_ticker'], 
                             type="text", value="SPY",
                             placeholder="SPY", className="form-control form-control-sm")
                ], width=3),
                dbc.Col([
                    html.Label("Expiry", className="small"),
                    dcc.Dropdown(id=COMPONENT_IDS['calc_expiry'],
                                options=[], placeholder="Select...",
                                className="form-control-sm")
                ], width=3),
                dbc.Col([
                    html.Label("Strike Range", className="small"),
                    dcc.Input(id=COMPONENT_IDS['calc_strike_range'],
                             type="text", value="±10%",
                             placeholder="±10%", className="form-control form-control-sm")
                ], width=3),
                dbc.Col([
                    html.Label(" ", className="small d-block"),
                    dbc.Button("▶ Run", id=COMPONENT_IDS['calc_run_btn'],
                              color="success", size="sm", className="w-100")
                ], width=3),
            ], className="mb-3"),
            
            # Heatmap visualization
            dcc.Loading(
                dcc.Graph(id=COMPONENT_IDS['heatmap'],
                         figure=go.Figure(),
                         style={'height': '300px'})
            ),
            
            # Metrics table
            html.Div(id=COMPONENT_IDS['iv_metrics_table'], className="mt-2"),
            
            # History slider and export
            dbc.Row([
                dbc.Col([
                    html.Label("History", className="small"),
                    dcc.Slider(id=COMPONENT_IDS['explorer_date_slider'],
                              min=0, max=10, value=0, marks={})
                ], width=9),
                dbc.Col([
                    dbc.Button("💾 Export", id=COMPONENT_IDS['iv_export_btn'],
                              size="sm", color="secondary", className="w-100 mt-4")
                ], width=3),
            ])
        ])
    ], className="h-100")


def create_signals_backtest_panel():
    """Panel 3: Signals + Quick Backtest"""
    return dbc.Card([
        dbc.CardHeader(html.H5("🎯 Signals & Backtest", className="mb-0")),
        dbc.CardBody([
            # Signals section
            html.H6("Trading Signals", className="mb-2"),
            dbc.Row([
                dbc.Col([
                    dbc.Button("🔍 Run Signals", id=COMPONENT_IDS['signal_run_btn'],
                              color="info", size="sm", className="w-100")
                ], width=6),
                dbc.Col([
                    dbc.Button("📋 Paper Order", id=COMPONENT_IDS['signal_paper_order_btn'],
                              color="warning", size="sm", className="w-100")
                ], width=6),
            ], className="mb-2"),
            html.Div(id=COMPONENT_IDS['signal_table'], 
                    children=html.P("No signals", className="text-muted small"),
                    className="mb-3"),
            
            html.Hr(),
            
            # Backtest section
            html.H6("Quick Backtest", className="mb-2"),
            dbc.Row([
                dbc.Col([
                    dbc.Button("▶ Run Backtest", id=COMPONENT_IDS['backtest_run_btn'],
                              color="primary", size="sm", className="w-100")
                ], width=6),
                dbc.Col([
                    dbc.Button("💾 Export", id=COMPONENT_IDS['backtest_export_btn'],
                              color="secondary", size="sm", className="w-100")
                ], width=6),
            ], className="mb-2"),
            html.Div(id=COMPONENT_IDS['backtest_results'],
                    children=html.P("No results", className="text-muted small"))
        ])
    ], className="h-100")


def create_diagnostics_panel():
    """Panel 4: Diagnostics - Collapsible solver logs and debug info"""
    return dbc.Card([
        dbc.CardHeader([
            html.H5("🔧 Diagnostics", className="mb-0 d-inline"),
            html.Small(" (collapsible)", className="text-muted ms-2")
        ]),
        dbc.Collapse([
            dbc.CardBody([
                html.Div([
                    html.Strong("Solver Log", className="small"),
                    html.Pre(id=COMPONENT_IDS['diag_solver_log'],
                            children="No solver runs yet",
                            className="border p-2 small",
                            style={'maxHeight': '100px', 'overflow': 'auto',
                                  'backgroundColor': '#f8f9fa'})
                ], className="mb-2"),
                
                html.Div([
                    html.Strong("Iterations: ", className="small"),
                    html.Span(id=COMPONENT_IDS['diag_iterations'], children="--")
                ], className="mb-2"),
                
                html.Div([
                    html.Strong("Last Payload", className="small"),
                    html.Pre(id=COMPONENT_IDS['diag_last_payload'],
                            children="{}",
                            className="border p-2 small",
                            style={'maxHeight': '80px', 'overflow': 'auto',
                                  'backgroundColor': '#f8f9fa'})
                ], className="mb-2"),
                
                dbc.Button("📥 Export Log", id=COMPONENT_IDS['diag_export_log'],
                          size="sm", color="secondary", className="w-100")
            ])
        ], id="vl-diag-collapse", is_open=False)
    ], className="h-100")


def layout():
    """Main Volatility Lab layout - 2x2 grid of panels"""
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="bi bi-activity me-2"),
                    "Volatility Lab"
                ], className="mb-1"),
                html.P("Compact single-tab IV surface calculator with signals and diagnostics",
                      className="text-muted small mb-3")
            ])
        ]),
        
        # 2x2 Grid
        dbc.Row([
            # Top row
            dbc.Col(create_overview_panel(), md=6, className="mb-3"),
            dbc.Col(create_iv_surface_panel(), md=6, className="mb-3"),
        ]),
        dbc.Row([
            # Bottom row
            dbc.Col(create_signals_backtest_panel(), md=6, className="mb-3"),
            dbc.Col(create_diagnostics_panel(), md=6, className="mb-3"),
        ]),
        
        # Hidden stores for state management
        dcc.Store(id='vl-surface-store', data=None),
        dcc.Store(id='vl-job-store', data=None),
        
    ], fluid=True, className="p-4")


def register_callbacks(app):
    """Register Volatility Lab callbacks - placeholder for wiring phase"""
    logger.info("✓ Volatility Lab callbacks registered (scaffold mode)")
    
    # Placeholder callbacks - will be implemented in UI wiring phase
    @app.callback(
        Output(COMPONENT_IDS['overview_last_surface'], 'children'),
        Input(COMPONENT_IDS['overview_refresh_btn'], 'n_clicks'),
        prevent_initial_call=True
    )
    def refresh_overview(n):
        return f"Refreshed at {datetime.now().strftime('%H:%M:%S')}"
    
    @app.callback(
        Output('vl-diag-collapse', 'is_open'),
        Input(COMPONENT_IDS['diag_solver_log'], 'n_clicks'),
        State('vl-diag-collapse', 'is_open'),
        prevent_initial_call=True
    )
    def toggle_diagnostics(n, is_open):
        return not is_open if n else is_open
    
    logger.info("✓ Volatility Lab scaffold callbacks active")
