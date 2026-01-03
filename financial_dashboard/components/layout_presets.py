"""
Layout Presets Component
Phase 6 - Visualization & UX (Item 493)

Provides switchable layout presets:
- Analysis Heavy: More charts and data visualization
- Trading Heavy: Quick execution focus
- Monitoring: Position/risk monitoring focus
- Custom: User-defined layout
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
from typing import Dict, List, Optional

# Design tokens
THEME = {
    "bg_primary": "#0D1117",
    "bg_secondary": "#161B22",
    "bg_tertiary": "#21262D",
    "gold": "#F5C211",
    "success": "#3FB950",
    "danger": "#F85149",
    "warning": "#D29922",
    "info": "#58A6FF",
    "text_primary": "#E6EDF3",
    "text_secondary": "#8B949E",
    "text_muted": "#6E7681",
    "border": "#30363D",
}

# Layout preset definitions
LAYOUT_PRESETS = {
    "analysis": {
        "name": "Analysis Heavy",
        "icon": "📊",
        "description": "Focus on charts, Greeks, and volatility analysis",
        "grid": {
            "chain": {"width": "35%", "height": "100%"},
            "greeks": {"width": "30%", "height": "50%"},
            "volatility": {"width": "30%", "height": "50%"},
            "chart": {"width": "35%", "height": "100%"},
        },
        "visible_panels": ["chain", "greeks", "volatility", "chart", "scanner"],
        "hidden_panels": ["order_entry", "positions_mini"],
    },
    "trading": {
        "name": "Trading Heavy",
        "icon": "⚡",
        "description": "Quick order entry with essential data",
        "grid": {
            "chain": {"width": "45%", "height": "100%"},
            "order_entry": {"width": "25%", "height": "60%"},
            "positions": {"width": "30%", "height": "100%"},
            "alerts": {"width": "25%", "height": "40%"},
        },
        "visible_panels": ["chain", "order_entry", "positions", "alerts", "quick_trade"],
        "hidden_panels": ["volatility", "advanced_greeks"],
    },
    "monitoring": {
        "name": "Position Monitor",
        "icon": "👁️",
        "description": "Portfolio and risk monitoring focus",
        "grid": {
            "positions": {"width": "50%", "height": "60%"},
            "risk": {"width": "50%", "height": "60%"},
            "alerts": {"width": "50%", "height": "40%"},
            "performance": {"width": "50%", "height": "40%"},
        },
        "visible_panels": ["positions", "risk", "alerts", "performance", "journal"],
        "hidden_panels": ["chain", "scanner"],
    },
    "compact": {
        "name": "Compact View",
        "icon": "📱",
        "description": "Minimal interface for smaller screens",
        "grid": {
            "chain": {"width": "100%", "height": "50%"},
            "positions": {"width": "100%", "height": "50%"},
        },
        "visible_panels": ["chain", "positions"],
        "hidden_panels": ["volatility", "greeks", "scanner"],
    },
    "custom": {
        "name": "Custom Layout",
        "icon": "⚙️",
        "description": "Your personalized layout",
        "grid": {},  # User-defined
        "visible_panels": [],  # User-defined
        "hidden_panels": [],
    },
}


def create_layout_preset_selector() -> html.Div:
    """Create the layout preset selector component."""
    
    return html.Div([
        html.Div([
            html.Span("🖼️", style={"marginRight": "8px", "fontSize": "16px"}),
            html.Span("Layout", style={
                "color": THEME["text_secondary"],
                "fontSize": "12px",
                "fontWeight": "500",
            }),
        ], style={"marginBottom": "8px"}),
        
        dcc.Dropdown(
            id="layout-preset-selector",
            options=[
                {
                    "label": html.Div([
                        html.Span(preset["icon"], style={"marginRight": "8px"}),
                        html.Span(preset["name"]),
                    ], style={"display": "flex", "alignItems": "center"}),
                    "value": key,
                }
                for key, preset in LAYOUT_PRESETS.items()
            ],
            value="trading",
            clearable=False,
            style={"width": "180px"},
            className="dark-dropdown",
        ),
    ], style={
        "display": "flex",
        "flexDirection": "column",
    })


def create_layout_preset_cards() -> html.Div:
    """Create visual cards for layout preset selection."""
    
    cards = []
    for key, preset in LAYOUT_PRESETS.items():
        card = html.Div([
            html.Div([
                html.Span(preset["icon"], style={"fontSize": "24px"}),
            ], style={"marginBottom": "8px"}),
            
            html.Div(preset["name"], style={
                "color": THEME["text_primary"],
                "fontSize": "13px",
                "fontWeight": "600",
                "marginBottom": "4px",
            }),
            
            html.Div(preset["description"], style={
                "color": THEME["text_muted"],
                "fontSize": "11px",
                "lineHeight": "1.4",
            }),
        ], id=f"layout-preset-{key}", className="layout-preset-card", style={
            "padding": "16px",
            "backgroundColor": THEME["bg_secondary"],
            "border": f"1px solid {THEME['border']}",
            "borderRadius": "8px",
            "cursor": "pointer",
            "transition": "all 0.2s ease",
            "textAlign": "center",
            "minWidth": "140px",
        })
        cards.append(card)
    
    return html.Div(cards, style={
        "display": "flex",
        "gap": "12px",
        "flexWrap": "wrap",
    })


def create_layout_customizer_modal() -> dbc.Modal:
    """Create the layout customization modal."""
    
    available_panels = [
        ("chain", "Options Chain", "📋"),
        ("greeks", "Greeks Panel", "🔢"),
        ("volatility", "Volatility Lab", "📈"),
        ("scanner", "Scanner", "🔍"),
        ("order_entry", "Order Entry", "📝"),
        ("positions", "Positions", "💼"),
        ("alerts", "Alerts", "🔔"),
        ("journal", "Trade Journal", "📓"),
        ("risk", "Risk Monitor", "⚠️"),
        ("performance", "Performance", "📊"),
        ("chart", "Price Chart", "📉"),
    ]
    
    return dbc.Modal([
        dbc.ModalHeader([
            html.Div([
                html.Span("⚙️", style={"fontSize": "24px", "marginRight": "12px"}),
                html.Span("Customize Layout", style={
                    "fontSize": "18px",
                    "fontWeight": "600",
                    "color": THEME["text_primary"],
                }),
            ], style={"display": "flex", "alignItems": "center"}),
        ], style={
            "backgroundColor": THEME["bg_secondary"],
            "borderBottom": f"1px solid {THEME['border']}",
        }, close_button=True),
        
        dbc.ModalBody([
            # Preset Selection
            html.Div([
                html.Label("Start from Preset", style={
                    "color": THEME["text_secondary"],
                    "fontSize": "12px",
                    "marginBottom": "8px",
                    "display": "block",
                }),
                create_layout_preset_cards(),
            ], style={"marginBottom": "24px"}),
            
            # Panel Visibility
            html.Div([
                html.Label("Visible Panels", style={
                    "color": THEME["text_secondary"],
                    "fontSize": "12px",
                    "marginBottom": "8px",
                    "display": "block",
                }),
                dcc.Checklist(
                    id="layout-visible-panels",
                    options=[
                        {
                            "label": html.Div([
                                html.Span(icon, style={"marginRight": "8px"}),
                                html.Span(name),
                            ], style={"display": "flex", "alignItems": "center"}),
                            "value": key,
                        }
                        for key, name, icon in available_panels
                    ],
                    value=["chain", "positions", "greeks", "alerts"],
                    style={"fontSize": "13px"},
                    labelStyle={
                        "display": "inline-flex",
                        "alignItems": "center",
                        "color": THEME["text_primary"],
                        "marginRight": "16px",
                        "marginBottom": "8px",
                        "cursor": "pointer",
                    },
                ),
            ], style={"marginBottom": "24px"}),
            
            # Grid Size
            html.Div([
                html.Label("Grid Configuration", style={
                    "color": THEME["text_secondary"],
                    "fontSize": "12px",
                    "marginBottom": "8px",
                    "display": "block",
                }),
                html.Div([
                    html.Div([
                        html.Span("Columns:", style={"color": THEME["text_muted"], "fontSize": "12px", "marginRight": "8px"}),
                        dcc.Slider(
                            id="layout-columns",
                            min=1,
                            max=4,
                            value=2,
                            marks={i: str(i) for i in range(1, 5)},
                            step=1,
                        ),
                    ], style={"flex": "1", "marginRight": "24px"}),
                    html.Div([
                        html.Span("Rows:", style={"color": THEME["text_muted"], "fontSize": "12px", "marginRight": "8px"}),
                        dcc.Slider(
                            id="layout-rows",
                            min=1,
                            max=3,
                            value=2,
                            marks={i: str(i) for i in range(1, 4)},
                            step=1,
                        ),
                    ], style={"flex": "1"}),
                ], style={"display": "flex"}),
            ], style={"marginBottom": "24px"}),
            
            # Save as Preset
            html.Div([
                html.Label("Save as Custom Preset", style={
                    "color": THEME["text_secondary"],
                    "fontSize": "12px",
                    "marginBottom": "8px",
                    "display": "block",
                }),
                html.Div([
                    dcc.Input(
                        id="layout-preset-name",
                        type="text",
                        placeholder="My Custom Layout",
                        style={
                            "flex": "1",
                            "padding": "8px 12px",
                            "backgroundColor": THEME["bg_tertiary"],
                            "border": f"1px solid {THEME['border']}",
                            "borderRadius": "6px",
                            "color": THEME["text_primary"],
                            "fontSize": "13px",
                            "marginRight": "8px",
                        }
                    ),
                    dbc.Button("Save", id="save-custom-layout", color="primary", size="sm"),
                ], style={"display": "flex"}),
            ]),
            
        ], style={
            "backgroundColor": THEME["bg_primary"],
            "padding": "24px",
        }),
        
        dbc.ModalFooter([
            dbc.Button("Reset to Default", id="reset-layout", color="secondary", outline=True, size="sm"),
            dbc.Button("Apply Layout", id="apply-layout", color="warning", size="sm", style={
                "backgroundColor": THEME["gold"],
                "color": "#0D1117",
                "border": "none",
            }),
        ], style={
            "backgroundColor": THEME["bg_secondary"],
            "borderTop": f"1px solid {THEME['border']}",
        }),
        
    ], id="layout-customizer-modal", is_open=False, size="lg", centered=True)


def create_layout_indicator() -> html.Div:
    """Create a small indicator showing current layout preset."""
    
    return html.Div([
        html.Span("⚡", style={"marginRight": "4px"}),
        html.Span("Trading", id="current-layout-name", style={
            "fontSize": "11px",
            "color": THEME["text_secondary"],
        }),
    ], id="layout-indicator", style={
        "display": "flex",
        "alignItems": "center",
        "padding": "4px 8px",
        "backgroundColor": THEME["bg_tertiary"],
        "borderRadius": "4px",
        "cursor": "pointer",
    })


# CSS for layout preset cards
LAYOUT_CSS = """
<style>
.layout-preset-card:hover {
    border-color: var(--alpaca-gold) !important;
    background-color: var(--bg-tertiary) !important;
}

.layout-preset-card.active {
    border-color: var(--alpaca-gold) !important;
    box-shadow: 0 0 0 2px rgba(245, 194, 17, 0.3);
}

.dark-dropdown .Select-control {
    background-color: var(--bg-tertiary) !important;
    border-color: var(--border-primary) !important;
}

.dark-dropdown .Select-menu-outer {
    background-color: var(--bg-secondary) !important;
}
</style>
"""
