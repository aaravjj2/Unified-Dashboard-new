"""
Volatility Lab - Layout with Tab Shell Error Wrapper
======================================================

Phase 34 canonical layout with 4 subtabs and safe error handling.

Canonical Subtabs:
1. IV Surface (vl-iv-tab)
2. Surface Explorer & History (vl-explorer-tab)  
3. Signals & Strategy Ideas (vl-signals-tab)
4. Quick Backtest & Replay (vl-backtest-tab)

Safe Layout Pattern:
- tab_shell() wrapper catches exceptions and renders error trace
- No heavy work at import time
- Lazy evaluation of components
"""

import logging
import traceback
import dash_bootstrap_components as dbc
from dash import html, dcc

from .components import (
    COMPONENT_IDS,
    create_heatmap,
    create_metrics_table,
    create_signal_table,
    create_backtest_summary,
    create_glass_card
)

logger = logging.getLogger(__name__)


def tab_shell(tab_content_func, tab_name="Unknown Tab"):
    """
    Safe wrapper for tab content rendering.
    
    Catches exceptions and renders collapsed error trace instead of crashing.
    
    Args:
        tab_content_func: Function that returns tab content
        tab_name: Tab name for error messages
        
    Returns:
        Tab content or error message div
    """
    try:
        return tab_content_func()
    except Exception as e:
        logger.exception(f"Error rendering {tab_name}")
        error_trace = traceback.format_exc()
        
        return dbc.Alert([
            html.H4(f"❌ {tab_name} Rendering Error", className="alert-heading"),
            html.P(str(e)),
            dbc.Collapse([
                html.Pre(error_trace, style={'fontSize': '10px', 'maxHeight': '300px', 'overflow': 'auto'})
            ], id=f"error-collapse-{tab_name.replace(' ', '-').lower()}", is_open=False),
            dbc.Button("Show Details", id=f"error-toggle-{tab_name.replace(' ', '-').lower()}", size="sm", className="mt-2")
        ], color="danger")


def create_iv_surface_tab():
    """
    Tab 1: IV Surface - Main calculation workspace.
    
    Components:
    - Ticker input (vl-calc-ticker)
    - Expiry selector (vl-calc-expiry)
    - Strike range (vl-calc-strikes)
    - Compute button (vl-calc-run-btn)
    - Heatmap (vl-heatmap)
    - Metrics table (vl-iv-metrics-table)
    - Diagnostics panel (vl-iv-diagnostics)
    - Download buttons (CSV/PNG/JSON)
    """
    logger.info("Creating IV Surface tab")
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                create_glass_card(
                    "Surface Parameters",
                    html.Div([
                        dbc.Label("Ticker"),
                        dbc.Input(
                            id=COMPONENT_IDS['calc_ticker'],
                            placeholder="SPY",
                            value="SPY",
                            type="text"
                        ),
                        dbc.Label("Expiry Mode", className="mt-2"),
                        dbc.Select(
                            id=COMPONENT_IDS['calc_expiry'],
                            options=[
                                {'label': 'Auto (Next 3)', 'value': 'auto'},
                                {'label': '30/60/90 Days', 'value': 'fixed'}
                            ],
                            value='auto'
                        ),
                        dbc.Label("Strike Range (%)", className="mt-2"),
                        dbc.Input(
                            id=COMPONENT_IDS['calc_strikes'],
                            placeholder="±10",
                            value="10",
                            type="number"
                        ),
                        dbc.Button(
                            "▶ Compute Surface",
                            id=COMPONENT_IDS['calc_run_btn'],
                            color="primary",
                            className="mt-3 w-100"
                        )
                    ])
                )
            ], width=3),
            
            dbc.Col([
                create_glass_card(
                    "Implied Volatility Surface",
                    html.Div([
                        dcc.Loading(
                            create_heatmap(),
                            type="default"
                        ),
                        html.Div([
                            dbc.Button("📥 CSV", id=COMPONENT_IDS['iv_grid_download'], size="sm", className="me-2"),
                            dbc.Button("🖼️ PNG", id=COMPONENT_IDS['iv_png_download'], size="sm", className="me-2"),
                            dbc.Button("📄 JSON", id=COMPONENT_IDS['iv_json_download'], size="sm")
                        ], className="mt-2")
                    ])
                )
            ], width=6),
            
            dbc.Col([
                create_glass_card(
                    "IV Metrics",
                    create_metrics_table()
                ),
                create_glass_card(
                    "Diagnostics",
                    html.Div(
                        id=COMPONENT_IDS['iv_diagnostics'],
                        children=[html.P("Run calculation to see diagnostics", className="text-muted")]
                    ),
                    card_id="diagnostics-card"
                )
            ], width=3)
        ])
    ], fluid=True, className="p-3")


def create_explorer_tab():
    """
    Tab 2: Surface Explorer & History.
    
    Components:
    - Date slider (vl-explorer-date-slider)
    - Load button (vl-explorer-load-btn)
    - Compare overlay (vl-compare-overlay)
    - Pin/favorite button (vl-pin-surface-btn)
    - Export JSON (vl-export-json)
    """
    logger.info("Creating Explorer tab")
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                create_glass_card(
                    "Historical Surfaces",
                    html.Div([
                        dbc.Label("Date Range"),
                        dcc.RangeSlider(
                            id=COMPONENT_IDS['explorer_date_slider'],
                            min=0,
                            max=30,
                            value=[0, 7],
                            marks={0: 'Today', 7: '7d', 14: '14d', 30: '30d'}
                        ),
                        dbc.Button("Load Surfaces", id=COMPONENT_IDS['explorer_load_btn'], color="primary", className="mt-3 w-100"),
                        html.Hr(),
                        dbc.Checklist(
                            id=COMPONENT_IDS['compare_overlay'],
                            options=[{'label': 'Show Delta Heatmap', 'value': 'delta'}],
                            value=[]
                        )
                    ])
                ),
                create_glass_card(
                    "Actions",
                    html.Div([
                        dbc.Button("📌 Pin Surface", id=COMPONENT_IDS['pin_surface_btn'], outline=True, className="w-100 mb-2"),
                        dbc.Button("📤 Export JSON", id=COMPONENT_IDS['export_json'], outline=True, className="w-100")
                    ])
                )
            ], width=3),
            
            dbc.Col([
                create_glass_card(
                    "Surface Comparison",
                    html.Div([
                        html.P("Select surfaces from the slider to compare", className="text-muted text-center p-5")
                    ])
                )
            ], width=9)
        ])
    ], fluid=True, className="p-3")


def create_signals_tab():
    """
    Tab 3: Signals & Strategy Ideas.
    
    Components:
    - Signal run button (vl-signal-run-btn)
    - Signal table (vl-signal-table)
    - Export signals (vl-signal-export-btn)
    - Send to Options Lab (vl-signal-send-to-options)
    - Create paper order (vl-signal-create-paper-order)
    """
    logger.info("Creating Signals tab")
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                create_glass_card(
                    "Signal Generation",
                    html.Div([
                        dbc.Label("Strategy"),
                        dbc.Select(
                            options=[
                                {'label': 'High IV Rank', 'value': 'iv_rank'},
                                {'label': 'Skew Play', 'value': 'skew'},
                                {'label': 'Straddle Candidates', 'value': 'straddle'}
                            ],
                            value='iv_rank',
                            id="signal-strategy-select"
                        ),
                        dbc.Button(
                            "🔍 Generate Signals",
                            id=COMPONENT_IDS['signal_run_btn'],
                            color="success",
                            className="mt-3 w-100"
                        )
                    ])
                )
            ], width=3),
            
            dbc.Col([
                create_glass_card(
                    "Trading Signals",
                    html.Div([
                        dcc.Loading(
                            html.Div(id='signal-table-container', children=[create_signal_table()]),
                            type="default"
                        ),
                        html.Div([
                            dbc.Button("📥 Export Signals", id=COMPONENT_IDS['signal_export_btn'], size="sm", className="me-2"),
                            dbc.Button("📬 Send to Options Lab", id=COMPONENT_IDS['signal_send_to_options'], size="sm", className="me-2"),
                            dbc.Button("📄 Create Paper Order", id=COMPONENT_IDS['signal_create_paper_order'], size="sm", color="primary")
                        ], className="mt-3")
                    ])
                )
            ], width=9)
        ])
    ], fluid=True, className="p-3")


def create_backtest_tab():
    """
    Tab 4: Quick Backtest & Replay.
    
    Components:
    - Backtest run button (vl-backtest-run-btn)
    - Seed input (vl-backtest-seed)
    - Results summary (vl-backtest-results)
    - Equity curve (vl-backtest-equity-curve)
    - Trades table (vl-backtest-trades-table)
    """
    logger.info("Creating Backtest tab")
    
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                create_glass_card(
                    "Backtest Parameters",
                    html.Div([
                        dbc.Label("Random Seed (Deterministic)"),
                        dbc.Input(
                            id=COMPONENT_IDS['backtest_seed'],
                            placeholder="42",
                            value="42",
                            type="number"
                        ),
                        dbc.Label("Backtest Period", className="mt-2"),
                        dbc.Select(
                            options=[
                                {'label': '1 Month', 'value': '1m'},
                                {'label': '3 Months', 'value': '3m'},
                                {'label': '6 Months', 'value': '6m'}
                            ],
                            value='1m',
                            id="backtest-period-select"
                        ),
                        dbc.Button(
                            "▶ Run Backtest",
                            id=COMPONENT_IDS['backtest_run_btn'],
                            color="primary",
                            className="mt-3 w-100"
                        )
                    ])
                )
            ], width=3),
            
            dbc.Col([
                dcc.Loading(
                    html.Div([
                        create_backtest_summary(),
                        html.Div(id=COMPONENT_IDS['backtest_equity_curve'], className="mt-3", children=[
                            html.P("Run backtest to see equity curve", className="text-muted text-center p-4")
                        ]),
                        html.Div(id=COMPONENT_IDS['backtest_trades_table'], className="mt-3", children=[
                            html.P("Run backtest to see trades", className="text-muted text-center p-4")
                        ])
                    ]),
                    type="default"
                )
            ], width=9)
        ])
    ], fluid=True, className="p-3")


def create_layout():
    """
    Main create_layout() function - Phase 34 required signature.
    
    Returns complete Volatility Lab layout with 4 canonical tabs wrapped in tab_shell.
    """
    logger.info("Creating Volatility Lab layout (Phase 34)")
    
    return dbc.Container([
        html.H2("⚡ Volatility Lab", className="mb-3"),
        html.P("IV Surface Analysis, Signals, and Backtesting", className="text-muted mb-4"),
        
        dbc.Tabs([
            dbc.Tab(
                tab_shell(create_iv_surface_tab, "IV Surface"),
                label="📊 IV Surface",
                tab_id="vl-iv-tab"
            ),
            dbc.Tab(
                tab_shell(create_explorer_tab, "Surface Explorer"),
                label="🔍 Explorer & History",
                tab_id="vl-explorer-tab"
            ),
            dbc.Tab(
                tab_shell(create_signals_tab, "Signals & Ideas"),
                label="💡 Signals & Ideas",
                tab_id="vl-signals-tab"
            ),
            dbc.Tab(
                tab_shell(create_backtest_tab, "Backtest & Replay"),
                label="⏮️ Backtest & Replay",
                tab_id="vl-backtest-tab"
            )
        ], id="vl-subtabs", active_tab="vl-iv-tab"),
        
        # Hidden stores
        dcc.Store(id=COMPONENT_IDS['surface_store']),
        dcc.Store(id=COMPONENT_IDS['signals_store']),
        dcc.Store(id=COMPONENT_IDS['backtest_store'])
        
    ], fluid=True, className="volatility-lab-container p-4")


__all__ = ['create_layout']
