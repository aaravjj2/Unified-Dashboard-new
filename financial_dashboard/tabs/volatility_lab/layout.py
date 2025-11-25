"""
Volatility Lab - Overhauled UI Layout
=====================================

Agent-1A: Premium, glass-morphism inspired layout for Volatility Analysis.

Layout Structure:
- Main layout(): 4-Tab Interface
- Tab 1: Overview (Glass Cards, Sparklines)
- Tab 2: IV Surface (Maximized Heatmap, 3D Toggle)
- Tab 3: Signals & Backtest (Split View)
- Tab 4: Diagnostics (Terminal Style)
"""

import logging
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

from .components import (
    COMPONENT_IDS,
    create_heatmap,
    create_metrics_table,
    create_signal_table,
    create_backtest_summary
)

logger = logging.getLogger(__name__)

def create_glass_card(title, content, footer=None, height="100%"):
    """Helper to create consistent glass-style cards"""
    return dbc.Card([
        dbc.CardHeader(html.H6(title, className="mb-0 fw-bold text-white"), 
                      style={"background": "rgba(255,255,255,0.05)", "borderBottom": "1px solid rgba(255,255,255,0.1)"}),
        dbc.CardBody(content),
        dbc.CardFooter(footer, style={"background": "rgba(255,255,255,0.02)", "borderTop": "1px solid rgba(255,255,255,0.1)"}) if footer else None
    ], className="h-100 shadow-sm", style={
        "background": "rgba(30, 30, 40, 0.6)",
        "backdropFilter": "blur(10px)",
        "border": "1px solid rgba(255,255,255,0.1)",
        "height": height
    })

def create_overview_panel():
    """Tab 1: Overview - High-level market state"""
    
    # 1. Key Metrics Row
    metrics_row = dbc.Row([
        dbc.Col(create_glass_card("ATM IV", [
            html.H2(id=COMPONENT_IDS['overview_atm_iv'], children="--", className="text-info display-4"),
            html.Small("Current At-The-Money Implied Volatility", className="text-muted")
        ]), width=4),
        dbc.Col(create_glass_card("Market Regime", [
            html.H4("High Volatility", className="text-warning mb-2"),
            html.Div(dbc.Progress(value=75, color="warning", className="mb-2", style={"height": "5px"})),
            html.Small("Regime: 75/100 (Elevated)", className="text-muted")
        ]), width=4),
        dbc.Col(create_glass_card("Last Update", [
            html.H4(id=COMPONENT_IDS['overview_last_surface'], children="--", className="text-white"),
            dbc.Button("🔄 Refresh Now", id=COMPONENT_IDS['overview_refresh_btn'], 
                      color="primary", size="sm", className="mt-2")
        ]), width=4),
    ], className="mb-4")

    # 2. Term Structure Row
    term_row = dbc.Row([
        dbc.Col(create_glass_card("Term Structure", [
            dbc.Row([
                dbc.Col([html.H5("30D", className="text-muted"), html.H3(id=COMPONENT_IDS['overview_term_30'], children="--", className="text-success")], width=4, className="text-center"),
                dbc.Col([html.H5("60D", className="text-muted"), html.H3(id=COMPONENT_IDS['overview_term_60'], children="--", className="text-primary")], width=4, className="text-center"),
                dbc.Col([html.H5("90D", className="text-muted"), html.H3(id=COMPONENT_IDS['overview_term_90'], children="--", className="text-warning")], width=4, className="text-center"),
            ]),
            html.Hr(className="my-3", style={"borderColor": "rgba(255,255,255,0.1)"}),
            dbc.Button("⚡ Quick Compute", id=COMPONENT_IDS['compute_quick_btn'], color="light", outline=True, className="w-100")
        ]), width=12)
    ])

    return html.Div([metrics_row, term_row], className="p-2")

def create_iv_surface_panel():
    """Tab 2: IV Surface - The main workspace"""
    
    controls = dbc.Row([
        dbc.Col([
            html.Label("Ticker", className="text-muted small"),
            dcc.Input(id=COMPONENT_IDS['calc_ticker'], value="SPY", className="form-control bg-dark text-white border-secondary")
        ], width=2),
        dbc.Col([
            html.Label("Expiry", className="text-muted small"),
            dcc.Dropdown(id=COMPONENT_IDS['calc_expiry'], placeholder="Auto", className="dash-bootstrap")
        ], width=2),
        dbc.Col([
            html.Label("Strike Range", className="text-muted small"),
            dcc.Input(id=COMPONENT_IDS['calc_strike_range'], value="±10%", className="form-control bg-dark text-white border-secondary")
        ], width=2),
        dbc.Col([
            html.Label("Action", className="text-muted small d-block"),
            dbc.Button("▶ Compute Surface", id=COMPONENT_IDS['calc_run_btn'], color="success", className="w-100")
        ], width=2),
        dbc.Col([
            html.Label("Export", className="text-muted small d-block"),
            dbc.Button("💾 CSV", id=COMPONENT_IDS['iv_export_btn'], color="secondary", outline=True, className="w-100")
        ], width=2),
    ], className="mb-3 align-items-end")

    heatmap_card = create_glass_card("Implied Volatility Surface", [
        dcc.Loading(
            dcc.Graph(id=COMPONENT_IDS['heatmap'], 
                     figure=create_heatmap([], [], [], "Ready to Compute"),
                     style={'height': '500px'},
                     config={'displayModeBar': True})
        )
    ])

    metrics_card = create_glass_card("Surface Metrics", [
        html.Div(id=COMPONENT_IDS['iv_metrics_table'])
    ])

    return html.Div([
        controls,
        dbc.Row([
            dbc.Col(heatmap_card, width=9),
            dbc.Col(metrics_card, width=3)
        ]),
        dbc.Row([
            dbc.Col([
                html.Label("History Explorer", className="text-muted small mt-3"),
                dcc.Slider(id=COMPONENT_IDS['explorer_date_slider'], min=0, max=10, value=0, marks={})
            ], width=12)
        ])
    ], className="p-2")

def create_signals_panel():
    """Tab 3: Signals & Backtest"""
    
    signals_col = dbc.Col(create_glass_card("Trading Signals", [
        dbc.Row([
            dbc.Col(dbc.Button("🔍 Scan Signals", id=COMPONENT_IDS['signal_run_btn'], color="info", className="w-100 mb-3"), width=6),
            dbc.Col(dbc.Button("📋 Paper Trade", id=COMPONENT_IDS['signal_paper_order_btn'], color="warning", outline=True, className="w-100 mb-3"), width=6),
        ]),
        html.Div(id=COMPONENT_IDS['signal_table'], children=html.Div("No signals generated", className="text-muted text-center py-5"))
    ]), width=6)

    backtest_col = dbc.Col(create_glass_card("Strategy Backtest", [
        dbc.Row([
            dbc.Col(dbc.Button("▶ Run Backtest", id=COMPONENT_IDS['backtest_run_btn'], color="primary", className="w-100 mb-3"), width=6),
            dbc.Col(dbc.Button("💾 Export Results", id=COMPONENT_IDS['backtest_export_btn'], color="secondary", outline=True, className="w-100 mb-3"), width=6),
        ]),
        html.Div(id=COMPONENT_IDS['backtest_results'], children=html.Div("No backtest run", className="text-muted text-center py-5"))
    ]), width=6)

    return dbc.Row([signals_col, backtest_col], className="p-2")

def create_diagnostics_panel():
    """Tab 4: Diagnostics"""
    
    log_viewer = html.Div([
        html.Div(id=COMPONENT_IDS['diag_solver_log'], 
                children="> System Ready...", 
                style={
                    "fontFamily": "monospace", 
                    "fontSize": "0.85rem", 
                    "color": "#0f0", 
                    "backgroundColor": "#000", 
                    "padding": "1rem", 
                    "borderRadius": "5px", 
                    "height": "300px", 
                    "overflowY": "auto"
                })
    ])

    stats_row = dbc.Row([
        dbc.Col(create_glass_card("Iterations", html.H3(id=COMPONENT_IDS['diag_iterations'], children="0", className="text-center")), width=3),
        dbc.Col(create_glass_card("Last Payload", html.Pre(id=COMPONENT_IDS['diag_last_payload'], children="{}", style={"fontSize": "0.7rem", "maxHeight": "100px"})), width=9),
    ], className="mb-3")

    return html.Div([
        stats_row,
        create_glass_card("Solver Logs", [
            log_viewer,
            dbc.Button("📥 Download Log", id=COMPONENT_IDS['diag_export_log'], color="secondary", size="sm", className="mt-2")
        ]),
        # Hidden collapse for compatibility with existing callbacks
        dbc.Collapse(id=COMPONENT_IDS['diag_collapse'], is_open=True) 
    ], className="p-2")

def layout():
    """Main Volatility Lab Layout"""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2([html.I(className="bi bi-activity me-2 text-info"), "Volatility Lab"], className="display-6 fw-bold text-white"),
                html.P("Advanced Implied Volatility Surface Analysis & Arbitrage Detection", className="text-muted lead")
            ], width=8),
            dbc.Col([
                # Status indicator
                html.Div([
                    html.Span("● System Online", className="text-success me-3"),
                    html.Span("● Data Feed Active", className="text-success")
                ], className="text-end mt-2")
            ], width=4)
        ], className="mb-4 border-bottom border-secondary pb-2"),

        dbc.Tabs([
            dbc.Tab(create_overview_panel(), label="📊 Overview", tab_id="tab-overview", active_label_class_name="fw-bold text-info"),
            dbc.Tab(create_iv_surface_panel(), label="📈 IV Surface", tab_id="tab-iv-surface", active_label_class_name="fw-bold text-info"),
            dbc.Tab(create_signals_panel(), label="🎯 Signals & Backtest", tab_id="tab-signals", active_label_class_name="fw-bold text-info"),
            dbc.Tab(create_diagnostics_panel(), label="🔧 Diagnostics", tab_id="tab-diagnostics", active_label_class_name="fw-bold text-info"),
        ], id="volatility-lab-tabs", active_tab="tab-overview", className="mb-4 nav-fill"),

        # Hidden Stores
        dcc.Store(id=COMPONENT_IDS['surface_store'], data=None),
        dcc.Store(id=COMPONENT_IDS['job_store'], data=None),
        dcc.Interval(id=COMPONENT_IDS['health_interval'], interval=5000, n_intervals=0),
        
    ], fluid=True, className="p-4", style={"minHeight": "100vh", "background": "linear-gradient(135deg, #111827 0%, #1f2937 100%)"})

__all__ = ['layout']
