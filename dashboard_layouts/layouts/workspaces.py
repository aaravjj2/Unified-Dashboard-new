"""
Consolidated Workspace Layouts
Phase 15 - Agent-UX

Defines 4 main workspace layouts:
1. Scanner: Market Viz (GEX/Vol) + Flow Tape + Pattern Feed
2. Strategy: Chain + Builder + AI Forecasts  
3. Command: Positions + Trade Ops (Risk/Execution)
4. Admin: Status + Research

These replace the 12 individual tabs with 4 consolidated workspaces.
"""

import logging
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from typing import Optional, Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)

# Alpaca Dark Theme
ALPACA_DARK = {
    "bg": "#1E1E1E",
    "paper": "#252525",
    "accent": "#F5C211",
    "positive": "#00C853",
    "negative": "#FF5252",
    "text": "#E0E0E0",
    "grid": "#333333",
}

# Common styles
CARD_STYLE = {
    "backgroundColor": ALPACA_DARK["paper"],
    "borderRadius": "8px",
    "padding": "15px",
    "marginBottom": "15px",
}

HEADER_STYLE = {
    "color": ALPACA_DARK["text"],
    "marginBottom": "10px",
    "borderBottom": f"2px solid {ALPACA_DARK['accent']}",
    "paddingBottom": "8px",
}


# ===========================================================================
# PATTERN FEED COMPONENT
# ===========================================================================

def create_pattern_feed(patterns: Optional[List[Dict]] = None) -> html.Div:
    """
    Create Pattern Feed component showing detected chart patterns.
    
    Args:
        patterns: List of detected pattern dictionaries
        
    Returns:
        Pattern feed div component
    """
    if patterns is None:
        patterns = []
    
    pattern_items = []
    
    if not patterns:
        pattern_items.append(
            html.Div(
                children=[
                    html.Span("🔍 ", style={"marginRight": "5px"}),
                    html.Span("Scanning for patterns...", style={"color": ALPACA_DARK["text"]}),
                ],
                style={"padding": "10px", "textAlign": "center"}
            )
        )
    else:
        for p in patterns[:5]:  # Show top 5 patterns
            signal = p.get("signal", "neutral")
            pattern_type = p.get("pattern_type", "unknown")
            confidence = p.get("confidence", 0)
            description = p.get("description", "")
            target = p.get("target_price")
            
            # Color based on signal
            if signal == "bullish":
                signal_color = ALPACA_DARK["positive"]
                signal_icon = "📈"
            elif signal == "bearish":
                signal_color = ALPACA_DARK["negative"]
                signal_icon = "📉"
            else:
                signal_color = ALPACA_DARK["text"]
                signal_icon = "➡️"
            
            pattern_items.append(
                html.Div(
                    children=[
                        html.Div(
                            children=[
                                html.Span(signal_icon, style={"marginRight": "8px", "fontSize": "18px"}),
                                html.Span(
                                    signal.upper(),
                                    style={
                                        "color": signal_color,
                                        "fontWeight": "bold",
                                        "marginRight": "10px",
                                    }
                                ),
                                html.Span(
                                    pattern_type.replace("_", " ").title(),
                                    style={"color": ALPACA_DARK["accent"], "fontWeight": "500"}
                                ),
                            ],
                            style={"marginBottom": "5px"}
                        ),
                        html.Div(
                            children=[
                                html.Span(description, style={"color": ALPACA_DARK["text"], "fontSize": "12px"}),
                            ]
                        ),
                        html.Div(
                            children=[
                                dbc.Badge(f"{confidence:.0%} conf", color="info", className="me-2"),
                                dbc.Badge(f"Target: ${target:.2f}" if target else "N/A", color="success") if target else None,
                            ],
                            style={"marginTop": "5px"}
                        ),
                    ],
                    style={
                        "padding": "12px",
                        "borderLeft": f"4px solid {signal_color}",
                        "marginBottom": "10px",
                        "backgroundColor": ALPACA_DARK["bg"],
                        "borderRadius": "4px",
                    }
                )
            )
    
    return html.Div(
        id="pattern-feed-container",
        children=[
            html.H5(
                children=[
                    html.Span("🎯 Pattern Feed", style={"marginRight": "10px"}),
                    dbc.Badge("LIVE", color="success", className="me-2"),
                ],
                style=HEADER_STYLE
            ),
            html.Div(
                id="pattern-feed-items",
                children=pattern_items,
                style={"maxHeight": "400px", "overflowY": "auto"}
            ),
            # Store for pattern data
            dcc.Store(id="pattern-feed-store", data=patterns),
            # Interval for refresh
            dcc.Interval(id="pattern-feed-interval", interval=30000, n_intervals=0),
        ],
        style=CARD_STYLE
    )


# ===========================================================================
# SCANNER LAYOUT
# ===========================================================================

def scanner_layout() -> html.Div:
    """
    Scanner Workspace: Market Viz (GEX/Vol) + Flow Tape + Pattern Feed.
    
    Combines visual analysis tools for market scanning.
    """
    # Import components - these preserve original IDs
    try:
        from financial_dashboard.components.charts.gex import create_gex_chart, generate_mock_gex_data, GEX_CHART_ID
        from financial_dashboard.components.charts.vol_surface import create_vol_surface, generate_mock_vol_surface, VOL_SURFACE_ID, VOL_SKEW_ID
        from financial_dashboard.tabs.market_viz.flow_tape import create_flow_tape, generate_mock_flow_data, FLOW_TABLE_ID
        
        # Generate mock data
        spot_price = 450.0
        ticker = "SPY"
        gex_data = generate_mock_gex_data(spot_price=spot_price)
        vol_data = generate_mock_vol_surface(spot_price=spot_price)
        flow_data = generate_mock_flow_data(ticker=ticker, spot_price=spot_price)
        
        gex_chart = create_gex_chart(gex_data, spot_price=spot_price, ticker=ticker)
        vol_surface = create_vol_surface(vol_data, spot_price=spot_price, ticker=ticker)
        flow_tape = create_flow_tape(flow_data)
        
    except ImportError as e:
        logger.error(f"Error importing scanner components: {e}")
        gex_chart = html.Div("GEX Chart loading...", id=GEX_CHART_ID if 'GEX_CHART_ID' in dir() else "chart-gex")
        vol_surface = html.Div("Vol Surface loading...", id="chart-vol-3d")
        flow_tape = html.Div("Flow Tape loading...", id="table-flow")
    
    return html.Div(
        id="scanner-workspace",
        children=[
            # Header
            html.Div(
                children=[
                    html.H3(
                        children=[
                            html.Span("🔭 Scanner Workspace", style={"marginRight": "15px"}),
                            dbc.Badge("GEX", color="warning", className="me-1"),
                            dbc.Badge("VOL", color="info", className="me-1"),
                            dbc.Badge("FLOW", color="success", className="me-1"),
                            dbc.Badge("PATTERNS", color="danger"),
                        ],
                        style={"color": ALPACA_DARK["text"], "marginBottom": "20px"}
                    ),
                ],
            ),
            
            # Top Row: GEX + Vol Surface
            dbc.Row(
                children=[
                    dbc.Col(
                        children=[
                            html.Div(
                                children=[
                                    html.H5("📊 Dealer Gamma Exposure (GEX)", style=HEADER_STYLE),
                                    gex_chart,
                                ],
                                style=CARD_STYLE
                            ),
                        ],
                        md=6
                    ),
                    dbc.Col(
                        children=[
                            html.Div(
                                children=[
                                    html.H5("📈 Volatility Surface", style=HEADER_STYLE),
                                    vol_surface,
                                ],
                                style=CARD_STYLE
                            ),
                        ],
                        md=6
                    ),
                ],
                className="mb-3"
            ),
            
            # Bottom Row: Flow Tape + Pattern Feed
            dbc.Row(
                children=[
                    dbc.Col(
                        children=[
                            html.Div(
                                children=[
                                    html.H5("🔥 Smart Flow Tape", style=HEADER_STYLE),
                                    flow_tape,
                                ],
                                style=CARD_STYLE
                            ),
                        ],
                        md=7
                    ),
                    dbc.Col(
                        children=[
                            create_pattern_feed(),
                        ],
                        md=5
                    ),
                ],
            ),
        ],
        style={
            "padding": "20px",
            "backgroundColor": ALPACA_DARK["bg"],
            "minHeight": "100vh",
        }
    )


# ===========================================================================
# STRATEGY LAYOUT
# ===========================================================================

def strategy_layout() -> html.Div:
    """
    Strategy Workspace: Chain + Builder + AI Forecasts.
    
    Combines tools for strategy construction and analysis.
    """
    # Import strategy components
    try:
        from financial_dashboard.tabs.options_lab.alpaca_ui_enhanced import (
            create_chain_viewer_panel,
            create_greeks_panel,
            create_iv_surface_panel,
            create_strategy_builder,
            create_ml_recommendations_panel,
        )
        from financial_dashboard.tabs.options_lab.strategy_engine_ui import create_strategy_analysis_tab
        from forecast_ui.tabs.forecasts import create_forecast_tab
        
        chain_viewer = create_chain_viewer_panel()
        greeks_panel = create_greeks_panel()
        iv_panel = create_iv_surface_panel()
        strategy_builder = create_strategy_builder()
        ml_panel = create_ml_recommendations_panel()
        strategy_engine = create_strategy_analysis_tab()
        forecast_tab = create_forecast_tab()
        
    except ImportError as e:
        logger.error(f"Error importing strategy components: {e}")
        chain_viewer = html.Div("Chain Viewer loading...", id="chain-viewer-placeholder")
        greeks_panel = html.Div("Greeks loading...", id="greeks-panel-placeholder")
        iv_panel = html.Div("IV loading...", id="iv-panel-placeholder")
        strategy_builder = html.Div("Builder loading...", id="builder-placeholder")
        ml_panel = html.Div("ML loading...", id="ml-placeholder")
        strategy_engine = html.Div("Engine loading...", id="engine-placeholder")
        forecast_tab = html.Div("Forecast loading...", id="forecast-placeholder")
    
    return html.Div(
        id="strategy-workspace",
        children=[
            # Header
            html.Div(
                children=[
                    html.H3(
                        children=[
                            html.Span("⚔️ Strategy Workspace", style={"marginRight": "15px"}),
                            dbc.Badge("CHAIN", color="primary", className="me-1"),
                            dbc.Badge("BUILD", color="warning", className="me-1"),
                            dbc.Badge("AI", color="danger"),
                        ],
                        style={"color": ALPACA_DARK["text"], "marginBottom": "20px"}
                    ),
                ],
            ),
            
            # Sub-tabs for strategy sections
            dcc.Tabs(
                id="strategy-sub-tabs",
                value="chain-tab",
                children=[
                    dcc.Tab(
                        label="📈 Chain & Greeks",
                        value="chain-tab",
                        children=[
                            html.Div(
                                children=[chain_viewer, greeks_panel, iv_panel],
                                style={"padding": "15px"}
                            )
                        ],
                        style={"backgroundColor": ALPACA_DARK["bg"]},
                        selected_style={"backgroundColor": ALPACA_DARK["paper"], "color": ALPACA_DARK["accent"]}
                    ),
                    dcc.Tab(
                        label="🎯 Builder",
                        value="builder-tab",
                        children=[
                            html.Div(
                                children=[strategy_builder],
                                style={"padding": "15px"}
                            )
                        ],
                        style={"backgroundColor": ALPACA_DARK["bg"]},
                        selected_style={"backgroundColor": ALPACA_DARK["paper"], "color": ALPACA_DARK["accent"]}
                    ),
                    dcc.Tab(
                        label="🦅 Engine",
                        value="engine-tab",
                        children=[strategy_engine],
                        style={"backgroundColor": ALPACA_DARK["bg"]},
                        selected_style={"backgroundColor": ALPACA_DARK["paper"], "color": ALPACA_DARK["accent"]}
                    ),
                    dcc.Tab(
                        label="🤖 AI Forecast",
                        value="ai-tab",
                        children=[
                            html.Div(
                                children=[ml_panel, forecast_tab],
                                style={"padding": "15px"}
                            )
                        ],
                        style={"backgroundColor": ALPACA_DARK["bg"]},
                        selected_style={"backgroundColor": ALPACA_DARK["paper"], "color": ALPACA_DARK["accent"]}
                    ),
                ],
                style={"marginBottom": "15px"}
            ),
        ],
        style={
            "padding": "20px",
            "backgroundColor": ALPACA_DARK["bg"],
            "minHeight": "100vh",
        }
    )


# ===========================================================================
# COMMAND LAYOUT
# ===========================================================================

def command_layout() -> html.Div:
    """
    Command Workspace: Positions + Trade Ops (Risk/Execution).
    
    Central hub for position management and trade execution.
    """
    try:
        from financial_dashboard.tabs.options_lab.alpaca_ui_enhanced import (
            create_positions_panel,
            create_risk_analytics_panel,
            create_flow_analysis_panel,
        )
        from tradeops_ui.tabs.trade_ops import create_trade_ops_tab
        
        positions_panel = create_positions_panel()
        risk_panel = create_risk_analytics_panel()
        flow_panel = create_flow_analysis_panel()
        trade_ops = create_trade_ops_tab()
        
    except ImportError as e:
        logger.error(f"Error importing command components: {e}")
        positions_panel = html.Div("Positions loading...", id="positions-placeholder")
        risk_panel = html.Div("Risk loading...", id="risk-placeholder")
        flow_panel = html.Div("Flow loading...", id="flow-placeholder")
        trade_ops = html.Div("Trade Ops loading...", id="tradeops-placeholder")
    
    return html.Div(
        id="command-workspace",
        children=[
            # Header
            html.Div(
                children=[
                    html.H3(
                        children=[
                            html.Span("🎮 Command Center", style={"marginRight": "15px"}),
                            dbc.Badge("POSITIONS", color="primary", className="me-1"),
                            dbc.Badge("RISK", color="danger", className="me-1"),
                            dbc.Badge("EXECUTE", color="success"),
                        ],
                        style={"color": ALPACA_DARK["text"], "marginBottom": "20px"}
                    ),
                ],
            ),
            
            # Sub-tabs
            dcc.Tabs(
                id="command-sub-tabs",
                value="positions-tab",
                children=[
                    dcc.Tab(
                        label="💼 Positions",
                        value="positions-tab",
                        children=[
                            html.Div(
                                children=[positions_panel],
                                style={"padding": "15px"}
                            )
                        ],
                        style={"backgroundColor": ALPACA_DARK["bg"]},
                        selected_style={"backgroundColor": ALPACA_DARK["paper"], "color": ALPACA_DARK["accent"]}
                    ),
                    dcc.Tab(
                        label="⚠️ Risk & P/L",
                        value="risk-tab",
                        children=[
                            html.Div(
                                children=[risk_panel, flow_panel],
                                style={"padding": "15px"}
                            )
                        ],
                        style={"backgroundColor": ALPACA_DARK["bg"]},
                        selected_style={"backgroundColor": ALPACA_DARK["paper"], "color": ALPACA_DARK["accent"]}
                    ),
                    dcc.Tab(
                        label="⚙️ Trade Ops",
                        value="tradeops-tab",
                        children=[trade_ops],
                        style={"backgroundColor": ALPACA_DARK["bg"]},
                        selected_style={"backgroundColor": ALPACA_DARK["paper"], "color": ALPACA_DARK["accent"]}
                    ),
                ],
                style={"marginBottom": "15px"}
            ),
        ],
        style={
            "padding": "20px",
            "backgroundColor": ALPACA_DARK["bg"],
            "minHeight": "100vh",
        }
    )


# ===========================================================================
# ADMIN LAYOUT
# ===========================================================================

def admin_layout() -> html.Div:
    """
    Admin Workspace: Status + Research.
    
    System monitoring and research tools.
    """
    try:
        from financial_dashboard.tabs.options_lab.system_status_ui import create_system_status_panel
        from research_ui.tabs.research import create_research_tab
        
        status_panel = create_system_status_panel()
        research_tab = create_research_tab()
        
    except ImportError as e:
        logger.error(f"Error importing admin components: {e}")
        status_panel = html.Div("Status loading...", id="status-placeholder")
        research_tab = html.Div("Research loading...", id="research-placeholder")
    
    return html.Div(
        id="admin-workspace",
        children=[
            # Header
            html.Div(
                children=[
                    html.H3(
                        children=[
                            html.Span("🔧 Admin Workspace", style={"marginRight": "15px"}),
                            dbc.Badge("STATUS", color="info", className="me-1"),
                            dbc.Badge("RESEARCH", color="warning"),
                        ],
                        style={"color": ALPACA_DARK["text"], "marginBottom": "20px"}
                    ),
                ],
            ),
            
            # Sub-tabs
            dcc.Tabs(
                id="admin-sub-tabs",
                value="status-tab",
                children=[
                    dcc.Tab(
                        label="🔧 System Status",
                        value="status-tab",
                        children=[status_panel],
                        style={"backgroundColor": ALPACA_DARK["bg"]},
                        selected_style={"backgroundColor": ALPACA_DARK["paper"], "color": ALPACA_DARK["accent"]}
                    ),
                    dcc.Tab(
                        label="📊 Research Lab",
                        value="research-tab",
                        children=[research_tab],
                        style={"backgroundColor": ALPACA_DARK["bg"]},
                        selected_style={"backgroundColor": ALPACA_DARK["paper"], "color": ALPACA_DARK["accent"]}
                    ),
                ],
                style={"marginBottom": "15px"}
            ),
        ],
        style={
            "padding": "20px",
            "backgroundColor": ALPACA_DARK["bg"],
            "minHeight": "100vh",
        }
    )


# ===========================================================================
# WORKSPACE REGISTRY
# ===========================================================================

WORKSPACE_REGISTRY = {
    "scanner": {
        "label": "🔭 Scanner",
        "layout": scanner_layout,
        "description": "Market Viz, Flow Tape, Pattern Feed",
    },
    "strategy": {
        "label": "⚔️ Strategy",
        "layout": strategy_layout,
        "description": "Chain, Builder, AI Forecasts",
    },
    "command": {
        "label": "🎮 Command",
        "layout": command_layout,
        "description": "Positions, Risk, Execution",
    },
    "admin": {
        "label": "🔧 Admin",
        "layout": admin_layout,
        "description": "Status, Research",
    },
}


def get_workspace_tabs() -> List[dcc.Tab]:
    """
    Get the 4 consolidated workspace tabs.
    
    Returns:
        List of dcc.Tab components
    """
    tabs = []
    
    for key, config in WORKSPACE_REGISTRY.items():
        tabs.append(
            dcc.Tab(
                label=config["label"],
                value=f"{key}-workspace-tab",
                children=[config["layout"]()],
                style={"backgroundColor": ALPACA_DARK["bg"], "color": "#fff"},
                selected_style={"backgroundColor": ALPACA_DARK["paper"], "color": ALPACA_DARK["accent"]}
            )
        )
    
    return tabs
