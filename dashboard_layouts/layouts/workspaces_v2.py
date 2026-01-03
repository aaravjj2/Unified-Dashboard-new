"""
Consolidated Workspace Layouts V2
Phase 15+ - Enhanced Agent-UX with Professional Alpaca Theme

Defines 4 main workspace layouts with enhanced visuals:
1. Scanner: Market Viz (GEX/Vol) + Flow Tape + Pattern Feed
2. Strategy: Chain + Builder + AI Forecasts  
3. Command: Positions + Trade Ops (Risk/Execution)
4. Admin: Status + Research

Design principles:
- Professional trading terminal aesthetic
- Clear visual hierarchy with Alpaca gold accents
- Information-dense but clean layouts
- Consistent spacing and typography
"""

import logging
from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from typing import Optional, Dict, Any, List
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

# =============================================================================
# DESIGN TOKENS - Matching CSS Custom Properties
# =============================================================================

THEME = {
    # Brand
    "gold": "#F5C211",
    "gold_light": "#FFD54F",
    "gold_dark": "#C9A000",
    
    # Backgrounds
    "bg_primary": "#0D1117",
    "bg_secondary": "#161B22",
    "bg_tertiary": "#21262D",
    "bg_elevated": "#30363D",
    
    # Text
    "text_primary": "#E6EDF3",
    "text_secondary": "#8B949E",
    "text_muted": "#6E7681",
    
    # Semantic
    "success": "#3FB950",
    "danger": "#F85149",
    "warning": "#D29922",
    "info": "#58A6FF",
    
    # Borders
    "border": "#30363D",
    "border_muted": "#21262D",
}

# Common component styles
STYLES = {
    "card": {
        "backgroundColor": THEME["bg_secondary"],
        "border": f"1px solid {THEME['border']}",
        "borderRadius": "12px",
        "padding": "20px",
        "marginBottom": "16px",
    },
    "card_accent": {
        "backgroundColor": THEME["bg_secondary"],
        "border": f"2px solid {THEME['gold']}",
        "borderRadius": "12px",
        "padding": "20px",
        "marginBottom": "16px",
        "boxShadow": f"0 0 20px rgba(245, 194, 17, 0.1)",
    },
    "header": {
        "color": THEME["text_primary"],
        "fontSize": "16px",
        "fontWeight": "600",
        "marginBottom": "16px",
        "paddingBottom": "8px",
        "borderBottom": f"2px solid {THEME['gold']}",
        "display": "flex",
        "alignItems": "center",
        "gap": "8px",
    },
    "metric_grid": {
        "display": "grid",
        "gridTemplateColumns": "repeat(4, 1fr)",
        "gap": "12px",
        "marginBottom": "16px",
    },
    "metric_card": {
        "backgroundColor": THEME["bg_tertiary"],
        "borderRadius": "8px",
        "padding": "16px",
        "textAlign": "center",
    },
    "workspace": {
        "padding": "24px",
        "backgroundColor": THEME["bg_primary"],
        "minHeight": "100vh",
    },
    "tab_style": {
        "backgroundColor": THEME["bg_primary"],
        "color": THEME["text_secondary"],
        "border": "none",
        "padding": "8px 20px",
    },
    "tab_selected": {
        "backgroundColor": THEME["bg_tertiary"],
        "color": THEME["gold"],
        "border": "none",
        "borderBottom": f"3px solid {THEME['gold']}",
        "padding": "8px 20px",
        "fontWeight": "600",
    },
}


# =============================================================================
# REUSABLE UI COMPONENTS
# =============================================================================

def create_workspace_header(
    title: str,
    icon: str,
    badges: List[Dict[str, str]] = None,
    subtitle: str = None
) -> html.Div:
    """Create a consistent workspace header."""
    badge_elements = []
    if badges:
        for b in badges:
            badge_elements.append(
                dbc.Badge(
                    b.get("text", ""),
                    color=b.get("color", "secondary"),
                    className="me-1",
                    style={"fontSize": "11px"}
                )
            )
    
    return html.Div([
        html.Div([
            html.Span(icon, style={"fontSize": "28px", "marginRight": "12px"}),
            html.Div([
                html.H3(
                    title,
                    style={
                        "color": THEME["text_primary"],
                        "margin": "0",
                        "fontWeight": "700",
                        "fontSize": "24px",
                    }
                ),
                html.Span(
                    subtitle,
                    style={"color": THEME["text_muted"], "fontSize": "13px"}
                ) if subtitle else None,
            ]),
        ], style={"display": "flex", "alignItems": "center"}),
        html.Div(badge_elements, style={"display": "flex", "alignItems": "center"}),
    ], style={
        "display": "flex",
        "justifyContent": "space-between",
        "alignItems": "center",
        "marginBottom": "24px",
        "paddingBottom": "16px",
        "borderBottom": f"1px solid {THEME['border']}",
    })


def create_metric_card(
    label: str,
    value: str,
    sublabel: str = None,
    color: str = None,
    icon: str = None
) -> html.Div:
    """Create a metric display card."""
    value_color = {
        "success": THEME["success"],
        "danger": THEME["danger"],
        "warning": THEME["warning"],
        "info": THEME["info"],
        "gold": THEME["gold"],
    }.get(color, THEME["text_primary"])
    
    return html.Div([
        html.Div([
            html.Span(icon, style={"marginRight": "4px"}) if icon else None,
            html.Span(label),
        ], style={
            "fontSize": "11px",
            "color": THEME["text_muted"],
            "textTransform": "uppercase",
            "letterSpacing": "0.5px",
            "marginBottom": "4px",
        }),
        html.Div(
            value,
            style={
                "fontSize": "24px",
                "fontWeight": "700",
                "fontFamily": "'JetBrains Mono', monospace",
                "color": value_color,
                "lineHeight": "1.2",
            }
        ),
        html.Div(
            sublabel,
            style={
                "fontSize": "10px",
                "color": THEME["text_muted"],
                "marginTop": "4px",
            }
        ) if sublabel else None,
    ], style=STYLES["metric_card"])


def create_section_card(
    title: str,
    icon: str,
    children: List,
    accent: bool = False,
    badge: str = None
) -> html.Div:
    """Create a section card with header."""
    header_content = [
        html.Span(icon, style={"color": THEME["gold"], "fontSize": "18px"}),
        html.Span(title, style={"fontWeight": "600"}),
    ]
    if badge:
        header_content.append(
            dbc.Badge(badge, color="success", className="ms-2", style={"fontSize": "10px"})
        )
    
    return html.Div([
        html.Div(header_content, style=STYLES["header"]),
        html.Div(children),
    ], style=STYLES["card_accent"] if accent else STYLES["card"])


def create_status_badge(status: str, text: str = None) -> html.Span:
    """Create a status indicator badge."""
    colors = {
        "live": THEME["success"],
        "online": THEME["success"],
        "offline": THEME["danger"],
        "warning": THEME["warning"],
        "pending": THEME["info"],
    }
    color = colors.get(status.lower(), THEME["text_muted"])
    
    return html.Span([
        html.Span(style={
            "display": "inline-block",
            "width": "8px",
            "height": "8px",
            "borderRadius": "50%",
            "backgroundColor": color,
            "marginRight": "6px",
            "boxShadow": f"0 0 6px {color}",
        }),
        html.Span(text or status.upper(), style={
            "fontSize": "11px",
            "fontWeight": "600",
            "color": color,
            "textTransform": "uppercase",
        }),
    ], style={"display": "inline-flex", "alignItems": "center"})


# =============================================================================
# PATTERN FEED COMPONENT
# =============================================================================

def create_pattern_feed(patterns: Optional[List[Dict]] = None) -> html.Div:
    """Create enhanced Pattern Feed component."""
    if patterns is None:
        patterns = []
    
    pattern_items = []
    
    if not patterns:
        pattern_items.append(
            html.Div([
                html.Div("🔍", style={"fontSize": "32px", "marginBottom": "8px"}),
                html.Div("Scanning for chart patterns...", style={
                    "color": THEME["text_muted"],
                    "fontSize": "14px",
                }),
                html.Div("Patterns will appear here when detected", style={
                    "color": THEME["text_muted"],
                    "fontSize": "12px",
                    "marginTop": "4px",
                }),
            ], style={
                "textAlign": "center",
                "padding": "40px 20px",
            })
        )
    else:
        for p in patterns[:5]:
            signal = p.get("signal", "neutral")
            pattern_type = p.get("pattern_type", "unknown")
            confidence = p.get("confidence", 0)
            description = p.get("description", "")
            target = p.get("target_price")
            
            signal_config = {
                "bullish": {"color": THEME["success"], "icon": "📈", "border": THEME["success"]},
                "bearish": {"color": THEME["danger"], "icon": "📉", "border": THEME["danger"]},
            }.get(signal, {"color": THEME["text_muted"], "icon": "➡️", "border": THEME["border"]})
            
            pattern_items.append(
                html.Div([
                    html.Div([
                        html.Span(signal_config["icon"], style={"fontSize": "18px", "marginRight": "8px"}),
                        html.Span(signal.upper(), style={
                            "color": signal_config["color"],
                            "fontWeight": "700",
                            "fontSize": "12px",
                            "marginRight": "12px",
                        }),
                        html.Span(pattern_type.replace("_", " ").title(), style={
                            "color": THEME["gold"],
                            "fontWeight": "500",
                        }),
                    ]),
                    html.Div(description, style={
                        "color": THEME["text_muted"],
                        "fontSize": "12px",
                        "marginTop": "4px",
                    }),
                    html.Div([
                        dbc.Badge(f"{confidence:.0%} conf", color="info", className="me-2"),
                        dbc.Badge(f"Target: ${target:.2f}", color="success") if target else None,
                    ], style={"marginTop": "8px"}),
                ], style={
                    "padding": "12px 16px",
                    "borderLeft": f"4px solid {signal_config['border']}",
                    "marginBottom": "8px",
                    "backgroundColor": THEME["bg_tertiary"],
                    "borderRadius": "0 8px 8px 0",
                })
            )
    
    return create_section_card(
        title="Pattern Feed",
        icon="🎯",
        badge="LIVE",
        children=[
            html.Div(
                id="pattern-feed-items",
                children=pattern_items,
                style={"maxHeight": "400px", "overflowY": "auto"}
            ),
            dcc.Store(id="pattern-feed-store", data=patterns),
            dcc.Interval(id="pattern-feed-interval", interval=30000, n_intervals=0),
        ]
    )


# =============================================================================
# SCANNER WORKSPACE
# =============================================================================

def scanner_layout() -> html.Div:
    """Scanner Workspace: Market Viz (GEX/Vol) + Flow Tape + Pattern Feed."""
    try:
        from financial_dashboard.components.charts.gex import create_gex_chart, generate_mock_gex_data, GEX_CHART_ID
        from financial_dashboard.components.charts.vol_surface import create_vol_surface, generate_mock_vol_surface, VOL_SURFACE_ID
        from financial_dashboard.tabs.market_viz.flow_tape import create_flow_tape, generate_mock_flow_data
        
        spot_price = 450.0
        ticker = "SPY"
        gex_data = generate_mock_gex_data(spot_price=spot_price)
        vol_data = generate_mock_vol_surface(spot_price=spot_price)
        flow_data = generate_mock_flow_data(ticker=ticker, spot_price=spot_price)
        
        gex_chart = create_gex_chart(gex_data, spot_price=spot_price, ticker=ticker)
        vol_surface = create_vol_surface(vol_data, spot_price=spot_price, ticker=ticker)
        flow_tape = create_flow_tape(flow_data)
        
    except ImportError as e:
        logger.error(f"Scanner import error: {e}")
        gex_chart = html.Div("GEX Chart loading...", className="skeleton", style={"height": "300px"})
        vol_surface = html.Div("Vol Surface loading...", className="skeleton", style={"height": "300px"})
        flow_tape = html.Div("Flow Tape loading...", className="skeleton", style={"height": "200px"})
    
    return html.Div(
        id="scanner-workspace",
        className="fade-in",
        children=[
            create_workspace_header(
                title="Scanner Workspace",
                icon="🔭",
                subtitle="Real-time market visualization & flow analysis",
                badges=[
                    {"text": "GEX", "color": "warning"},
                    {"text": "VOL", "color": "info"},
                    {"text": "FLOW", "color": "success"},
                    {"text": "PATTERNS", "color": "danger"},
                ]
            ),
            
            # Market Overview Metrics
            html.Div([
                create_metric_card("SPY", "$450.25", "+1.2%", "success", "📈"),
                create_metric_card("VIX", "18.5", "-5.2%", "success", "📊"),
                create_metric_card("GEX", "+2.1B", "Positive", "gold", "⚡"),
                create_metric_card("Flow", "Bullish", "65% Calls", "info", "🔥"),
            ], style=STYLES["metric_grid"]),
            
            # Top Row: GEX + Vol Surface
            dbc.Row([
                dbc.Col([
                    create_section_card(
                        title="Dealer Gamma Exposure (GEX)",
                        icon="📊",
                        badge="LIVE",
                        children=[gex_chart]
                    )
                ], md=6),
                dbc.Col([
                    create_section_card(
                        title="Volatility Surface",
                        icon="📈",
                        children=[vol_surface]
                    )
                ], md=6),
            ], className="mb-3"),
            
            # Bottom Row: Flow Tape + Pattern Feed
            dbc.Row([
                dbc.Col([
                    create_section_card(
                        title="Smart Flow Tape",
                        icon="🔥",
                        badge="LIVE",
                        children=[flow_tape]
                    )
                ], md=7),
                dbc.Col([
                    create_pattern_feed()
                ], md=5),
            ]),
        ],
        style=STYLES["workspace"]
    )


# =============================================================================
# STRATEGY WORKSPACE
# =============================================================================

def strategy_layout() -> html.Div:
    """Strategy Workspace: Chain + Builder + AI Forecasts."""
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
        logger.error(f"Strategy import error: {e}")
        chain_viewer = html.Div("Chain Viewer loading...", className="skeleton", style={"height": "400px"})
        greeks_panel = html.Div("Greeks loading...", className="skeleton", style={"height": "200px"})
        iv_panel = html.Div("IV loading...", className="skeleton", style={"height": "300px"})
        strategy_builder = html.Div("Builder loading...", className="skeleton", style={"height": "300px"})
        ml_panel = html.Div("ML loading...", className="skeleton", style={"height": "200px"})
        strategy_engine = html.Div("Engine loading...", className="skeleton", style={"height": "400px"})
        forecast_tab = html.Div("Forecast loading...", className="skeleton", style={"height": "400px"})
    
    return html.Div(
        id="strategy-workspace",
        className="fade-in",
        children=[
            create_workspace_header(
                title="Strategy Workspace",
                icon="⚔️",
                subtitle="Options chain analysis & strategy construction",
                badges=[
                    {"text": "CHAIN", "color": "primary"},
                    {"text": "BUILD", "color": "warning"},
                    {"text": "AI", "color": "danger"},
                ]
            ),
            
            # Quick Stats
            html.Div([
                create_metric_card("IV Rank", "45%", "Percentile", "info", "📊"),
                create_metric_card("Expected Move", "±$12.50", "2.8%", "warning", "📈"),
                create_metric_card("Max Pain", "$448", "Friday Exp", "gold", "🎯"),
                create_metric_card("P/C Ratio", "0.85", "Slightly Bullish", "success", "⚖️"),
            ], style=STYLES["metric_grid"]),
            
            # Sub-tabs
            dcc.Tabs(
                id="strategy-sub-tabs",
                value="chain-tab",
                children=[
                    dcc.Tab(
                        label="📈 Chain & Greeks",
                        value="chain-tab",
                        children=[
                            html.Div([chain_viewer, greeks_panel, iv_panel], style={"padding": "20px"})
                        ],
                        style=STYLES["tab_style"],
                        selected_style=STYLES["tab_selected"]
                    ),
                    dcc.Tab(
                        label="🎯 Strategy Builder",
                        value="builder-tab",
                        children=[
                            html.Div([strategy_builder], style={"padding": "20px"})
                        ],
                        style=STYLES["tab_style"],
                        selected_style=STYLES["tab_selected"]
                    ),
                    dcc.Tab(
                        label="🦅 Strategy Engine",
                        value="engine-tab",
                        children=[strategy_engine],
                        style=STYLES["tab_style"],
                        selected_style=STYLES["tab_selected"]
                    ),
                    dcc.Tab(
                        label="🤖 AI Forecast",
                        value="ai-tab",
                        children=[
                            html.Div([ml_panel, forecast_tab], style={"padding": "20px"})
                        ],
                        style=STYLES["tab_style"],
                        selected_style=STYLES["tab_selected"]
                    ),
                ],
                style={"marginBottom": "16px"}
            ),
        ],
        style=STYLES["workspace"]
    )


# =============================================================================
# COMMAND WORKSPACE
# =============================================================================

def command_layout() -> html.Div:
    """Command Workspace: Positions + Trade Ops (Risk/Execution)."""
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
        logger.error(f"Command import error: {e}")
        positions_panel = html.Div("Positions loading...", className="skeleton", style={"height": "300px"})
        risk_panel = html.Div("Risk loading...", className="skeleton", style={"height": "250px"})
        flow_panel = html.Div("Flow loading...", className="skeleton", style={"height": "300px"})
        trade_ops = html.Div("Trade Ops loading...", className="skeleton", style={"height": "400px"})
    
    return html.Div(
        id="command-workspace",
        className="fade-in",
        children=[
            create_workspace_header(
                title="Command Center",
                icon="🎮",
                subtitle="Position management & trade execution",
                badges=[
                    {"text": "POSITIONS", "color": "primary"},
                    {"text": "RISK", "color": "danger"},
                    {"text": "EXECUTE", "color": "success"},
                ]
            ),
            
            # Portfolio Summary
            html.Div([
                create_metric_card("Net P/L", "+$2,450", "Today", "success", "💰"),
                create_metric_card("Delta", "-125", "Shares Eq.", "warning", "Δ"),
                create_metric_card("Theta", "+$85", "Per Day", "success", "Θ"),
                create_metric_card("Risk Score", "LOW", "3 Positions", "success", "⚠️"),
            ], style=STYLES["metric_grid"]),
            
            # Sub-tabs
            dcc.Tabs(
                id="command-sub-tabs",
                value="positions-tab",
                children=[
                    dcc.Tab(
                        label="💼 Positions",
                        value="positions-tab",
                        children=[
                            html.Div([positions_panel], style={"padding": "20px"})
                        ],
                        style=STYLES["tab_style"],
                        selected_style=STYLES["tab_selected"]
                    ),
                    dcc.Tab(
                        label="⚠️ Risk & P/L",
                        value="risk-tab",
                        children=[
                            html.Div([risk_panel, flow_panel], style={"padding": "20px"})
                        ],
                        style=STYLES["tab_style"],
                        selected_style=STYLES["tab_selected"]
                    ),
                    dcc.Tab(
                        label="⚙️ Trade Ops",
                        value="tradeops-tab",
                        children=[trade_ops],
                        style=STYLES["tab_style"],
                        selected_style=STYLES["tab_selected"]
                    ),
                ],
                style={"marginBottom": "16px"}
            ),
        ],
        style=STYLES["workspace"]
    )


# =============================================================================
# ADMIN WORKSPACE
# =============================================================================

def admin_layout() -> html.Div:
    """Admin Workspace: Status + Research."""
    try:
        from financial_dashboard.tabs.options_lab.system_status_ui import create_system_status_panel
        from research_ui.tabs.research import create_research_tab
        
        status_panel = create_system_status_panel()
        research_tab = create_research_tab()
        
    except ImportError as e:
        logger.error(f"Admin import error: {e}")
        status_panel = html.Div("Status loading...", className="skeleton", style={"height": "400px"})
        research_tab = html.Div("Research loading...", className="skeleton", style={"height": "400px"})
    
    return html.Div(
        id="admin-workspace",
        className="fade-in",
        children=[
            create_workspace_header(
                title="Admin Workspace",
                icon="🔧",
                subtitle="System monitoring & research tools",
                badges=[
                    {"text": "STATUS", "color": "info"},
                    {"text": "RESEARCH", "color": "warning"},
                ]
            ),
            
            # System Health
            html.Div([
                create_metric_card("API Status", "Online", "Alpaca", "success", "🟢"),
                create_metric_card("Data Feed", "Live", "< 100ms", "success", "📡"),
                create_metric_card("Models", "3/3", "Loaded", "success", "🤖"),
                create_metric_card("Cache", "85%", "Hit Rate", "info", "💾"),
            ], style=STYLES["metric_grid"]),
            
            # Sub-tabs
            dcc.Tabs(
                id="admin-sub-tabs",
                value="status-tab",
                children=[
                    dcc.Tab(
                        label="🔧 System Status",
                        value="status-tab",
                        children=[status_panel],
                        style=STYLES["tab_style"],
                        selected_style=STYLES["tab_selected"]
                    ),
                    dcc.Tab(
                        label="📊 Research Lab",
                        value="research-tab",
                        children=[research_tab],
                        style=STYLES["tab_style"],
                        selected_style=STYLES["tab_selected"]
                    ),
                ],
                style={"marginBottom": "16px"}
            ),
        ],
        style=STYLES["workspace"]
    )


# =============================================================================
# WORKSPACE REGISTRY
# =============================================================================

WORKSPACE_REGISTRY = {
    "scanner": {
        "label": "🔭 Scanner",
        "layout": scanner_layout,
        "description": "Market Viz, Flow Tape, Pattern Feed",
        "color": "warning",
    },
    "strategy": {
        "label": "⚔️ Strategy",
        "layout": strategy_layout,
        "description": "Chain, Builder, AI Forecasts",
        "color": "info",
    },
    "command": {
        "label": "🎮 Command",
        "layout": command_layout,
        "description": "Positions, Risk, Execution",
        "color": "danger",
    },
    "admin": {
        "label": "🔧 Admin",
        "layout": admin_layout,
        "description": "Status, Research",
        "color": "success",
    },
}


def get_workspace_tabs() -> List[dcc.Tab]:
    """Get the 4 consolidated workspace tabs."""
    tabs = []
    
    for key, config in WORKSPACE_REGISTRY.items():
        tabs.append(
            dcc.Tab(
                label=config["label"],
                value=f"{key}-workspace-tab",
                children=[config["layout"]()],
                style=STYLES["tab_style"],
                selected_style=STYLES["tab_selected"]
            )
        )
    
    return tabs
