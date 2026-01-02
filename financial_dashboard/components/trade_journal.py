"""
Trade Journal Component
Phase 6 - Visualization & UX (Item 463)

Provides a comprehensive trade journaling system with:
- Trade logging with tags and notes
- Performance attribution
- Strategy tagging
- Searchable history
"""

from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
from datetime import datetime
from typing import List, Dict, Optional

# Design tokens from the main theme
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


def create_trade_journal_panel() -> html.Div:
    """Create the trade journal panel with logging and history."""
    
    # Sample trade data for demonstration
    sample_trades = [
        {
            "id": 1,
            "date": "2025-12-30",
            "time": "10:35",
            "ticker": "SPY",
            "strategy": "Iron Condor",
            "entry": "$2.45",
            "exit": "$1.20",
            "pnl": "+$125",
            "pnl_pct": "+51%",
            "tags": "earnings,high-iv",
            "notes": "Closed at 50% profit target",
            "status": "closed",
        },
        {
            "id": 2,
            "date": "2025-12-30",
            "time": "14:20",
            "ticker": "NVDA",
            "strategy": "Put Credit Spread",
            "entry": "$1.85",
            "exit": "--",
            "pnl": "+$65",
            "pnl_pct": "+35%",
            "tags": "trend-follow",
            "notes": "Letting winner run",
            "status": "open",
        },
        {
            "id": 3,
            "date": "2025-12-29",
            "time": "09:45",
            "ticker": "AAPL",
            "strategy": "Straddle",
            "entry": "$4.20",
            "exit": "$2.80",
            "pnl": "-$140",
            "pnl_pct": "-33%",
            "tags": "vol-play,mistake",
            "notes": "Cut loss on IV crush post-event",
            "status": "closed",
        },
        {
            "id": 4,
            "date": "2025-12-27",
            "time": "11:15",
            "ticker": "QQQ",
            "strategy": "Call Debit Spread",
            "entry": "$2.10",
            "exit": "$3.50",
            "pnl": "+$140",
            "pnl_pct": "+67%",
            "tags": "momentum",
            "notes": "Rode breakout to target",
            "status": "closed",
        },
    ]
    
    return html.Div([
        # Header
        html.Div([
            html.Div([
                html.Span("📓", style={"fontSize": "24px", "marginRight": "12px"}),
                html.Span("Trade Journal", style={
                    "fontSize": "18px",
                    "fontWeight": "600",
                    "color": THEME["text_primary"],
                }),
            ], style={"display": "flex", "alignItems": "center"}),
            
            html.Div([
                dbc.Badge("4 Total", color="info", className="me-2"),
                dbc.Badge("1 Open", color="success", className="me-2"),
                dbc.Badge("+$190 MTD", color="success"),
            ]),
        ], style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "marginBottom": "20px",
            "paddingBottom": "12px",
            "borderBottom": f"2px solid {THEME['gold']}",
        }),
        
        # Quick Add Trade Form
        html.Div([
            html.Div([
                html.Span("➕ Quick Add Trade", style={
                    "color": THEME["text_secondary"],
                    "fontSize": "13px",
                    "fontWeight": "500",
                }),
            ], style={"marginBottom": "12px"}),
            
            html.Div([
                dcc.Input(
                    id="journal-ticker",
                    type="text",
                    placeholder="Ticker",
                    style={
                        "width": "80px",
                        "padding": "8px 12px",
                        "backgroundColor": THEME["bg_tertiary"],
                        "border": f"1px solid {THEME['border']}",
                        "borderRadius": "6px",
                        "color": THEME["text_primary"],
                        "marginRight": "8px",
                    }
                ),
                dcc.Dropdown(
                    id="journal-strategy",
                    options=[
                        {"label": "Iron Condor", "value": "Iron Condor"},
                        {"label": "Put Credit Spread", "value": "Put Credit Spread"},
                        {"label": "Call Credit Spread", "value": "Call Credit Spread"},
                        {"label": "Put Debit Spread", "value": "Put Debit Spread"},
                        {"label": "Call Debit Spread", "value": "Call Debit Spread"},
                        {"label": "Straddle", "value": "Straddle"},
                        {"label": "Strangle", "value": "Strangle"},
                        {"label": "Calendar", "value": "Calendar"},
                        {"label": "Butterfly", "value": "Butterfly"},
                        {"label": "Custom", "value": "Custom"},
                    ],
                    placeholder="Strategy",
                    style={"width": "160px", "marginRight": "8px"},
                    className="dark-dropdown",
                ),
                dcc.Input(
                    id="journal-entry",
                    type="text",
                    placeholder="Entry $",
                    style={
                        "width": "80px",
                        "padding": "8px 12px",
                        "backgroundColor": THEME["bg_tertiary"],
                        "border": f"1px solid {THEME['border']}",
                        "borderRadius": "6px",
                        "color": THEME["text_primary"],
                        "marginRight": "8px",
                    }
                ),
                dcc.Input(
                    id="journal-tags",
                    type="text",
                    placeholder="Tags (comma-sep)",
                    style={
                        "width": "140px",
                        "padding": "8px 12px",
                        "backgroundColor": THEME["bg_tertiary"],
                        "border": f"1px solid {THEME['border']}",
                        "borderRadius": "6px",
                        "color": THEME["text_primary"],
                        "marginRight": "8px",
                    }
                ),
                html.Button(
                    "Log Trade",
                    id="journal-add-btn",
                    style={
                        "padding": "8px 16px",
                        "backgroundColor": THEME["gold"],
                        "color": "#0D1117",
                        "border": "none",
                        "borderRadius": "6px",
                        "fontWeight": "600",
                        "cursor": "pointer",
                    }
                ),
            ], style={"display": "flex", "alignItems": "center", "flexWrap": "wrap", "gap": "8px"}),
        ], style={
            "padding": "16px",
            "backgroundColor": THEME["bg_tertiary"],
            "borderRadius": "8px",
            "marginBottom": "20px",
        }),
        
        # Filter Controls
        html.Div([
            html.Div([
                html.Span("Filter: ", style={"color": THEME["text_muted"], "fontSize": "12px", "marginRight": "8px"}),
                dcc.RadioItems(
                    id="journal-status-filter",
                    options=[
                        {"label": " All", "value": "all"},
                        {"label": " Open", "value": "open"},
                        {"label": " Closed", "value": "closed"},
                        {"label": " Winners", "value": "winners"},
                        {"label": " Losers", "value": "losers"},
                    ],
                    value="all",
                    inline=True,
                    style={"fontSize": "12px"},
                    labelStyle={"color": THEME["text_secondary"], "marginRight": "12px"},
                ),
            ], style={"display": "flex", "alignItems": "center"}),
            
            dcc.Input(
                id="journal-search",
                type="text",
                placeholder="🔍 Search trades...",
                style={
                    "width": "200px",
                    "padding": "6px 12px",
                    "backgroundColor": THEME["bg_tertiary"],
                    "border": f"1px solid {THEME['border']}",
                    "borderRadius": "6px",
                    "color": THEME["text_primary"],
                    "fontSize": "12px",
                }
            ),
        ], style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "marginBottom": "16px",
        }),
        
        # Trade History Table
        dash_table.DataTable(
            id="journal-table",
            columns=[
                {"name": "Date", "id": "date", "type": "text"},
                {"name": "Time", "id": "time", "type": "text"},
                {"name": "Ticker", "id": "ticker", "type": "text"},
                {"name": "Strategy", "id": "strategy", "type": "text"},
                {"name": "Entry", "id": "entry", "type": "text"},
                {"name": "Exit", "id": "exit", "type": "text"},
                {"name": "P/L", "id": "pnl", "type": "text"},
                {"name": "%", "id": "pnl_pct", "type": "text"},
                {"name": "Tags", "id": "tags", "type": "text"},
                {"name": "Notes", "id": "notes", "type": "text"},
            ],
            data=sample_trades,
            style_header={
                "backgroundColor": THEME["bg_tertiary"],
                "color": THEME["text_primary"],
                "fontWeight": "600",
                "fontSize": "11px",
                "textTransform": "uppercase",
                "letterSpacing": "0.5px",
                "padding": "12px 8px",
                "borderBottom": f"2px solid {THEME['gold']}",
            },
            style_cell={
                "backgroundColor": THEME["bg_secondary"],
                "color": THEME["text_primary"],
                "fontSize": "13px",
                "fontFamily": "'JetBrains Mono', monospace",
                "padding": "10px 8px",
                "border": f"1px solid {THEME['border']}",
                "textAlign": "left",
                "maxWidth": "150px",
                "overflow": "hidden",
                "textOverflow": "ellipsis",
            },
            style_data_conditional=[
                # Positive P/L
                {
                    "if": {
                        "filter_query": "{pnl} contains '+'",
                        "column_id": "pnl"
                    },
                    "color": THEME["success"],
                    "fontWeight": "600",
                },
                # Negative P/L
                {
                    "if": {
                        "filter_query": "{pnl} contains '-'",
                        "column_id": "pnl"
                    },
                    "color": THEME["danger"],
                    "fontWeight": "600",
                },
                # Positive %
                {
                    "if": {
                        "filter_query": "{pnl_pct} contains '+'",
                        "column_id": "pnl_pct"
                    },
                    "color": THEME["success"],
                },
                # Negative %
                {
                    "if": {
                        "filter_query": "{pnl_pct} contains '-'",
                        "column_id": "pnl_pct"
                    },
                    "color": THEME["danger"],
                },
                # Open trades highlight
                {
                    "if": {
                        "filter_query": "{status} = 'open'",
                    },
                    "backgroundColor": f"{THEME['info']}15",
                    "borderLeft": f"3px solid {THEME['info']}",
                },
                # Tags styling
                {
                    "if": {"column_id": "tags"},
                    "color": THEME["gold"],
                    "fontSize": "11px",
                },
                # Alternating rows
                {
                    "if": {"row_index": "odd"},
                    "backgroundColor": THEME["bg_tertiary"],
                },
            ],
            style_table={
                "borderRadius": "8px",
                "overflow": "hidden",
            },
            page_size=10,
            sort_action="native",
            filter_action="native",
        ),
        
        # Performance Summary
        html.Div([
            html.Div([
                html.Span("📊 Performance Summary", style={
                    "color": THEME["text_primary"],
                    "fontSize": "14px",
                    "fontWeight": "600",
                }),
            ], style={"marginBottom": "12px"}),
            
            html.Div([
                # Win Rate
                html.Div([
                    html.Div("Win Rate", style={
                        "color": THEME["text_muted"],
                        "fontSize": "11px",
                        "textTransform": "uppercase",
                    }),
                    html.Div("75%", style={
                        "color": THEME["success"],
                        "fontSize": "24px",
                        "fontWeight": "700",
                        "fontFamily": "'JetBrains Mono', monospace",
                    }),
                    html.Div("3W / 1L", style={
                        "color": THEME["text_muted"],
                        "fontSize": "11px",
                    }),
                ], style={"textAlign": "center", "flex": "1"}),
                
                # Avg Win
                html.Div([
                    html.Div("Avg Win", style={
                        "color": THEME["text_muted"],
                        "fontSize": "11px",
                        "textTransform": "uppercase",
                    }),
                    html.Div("+$110", style={
                        "color": THEME["success"],
                        "fontSize": "24px",
                        "fontWeight": "700",
                        "fontFamily": "'JetBrains Mono', monospace",
                    }),
                    html.Div("+51% avg", style={
                        "color": THEME["text_muted"],
                        "fontSize": "11px",
                    }),
                ], style={"textAlign": "center", "flex": "1"}),
                
                # Avg Loss
                html.Div([
                    html.Div("Avg Loss", style={
                        "color": THEME["text_muted"],
                        "fontSize": "11px",
                        "textTransform": "uppercase",
                    }),
                    html.Div("-$140", style={
                        "color": THEME["danger"],
                        "fontSize": "24px",
                        "fontWeight": "700",
                        "fontFamily": "'JetBrains Mono', monospace",
                    }),
                    html.Div("-33% avg", style={
                        "color": THEME["text_muted"],
                        "fontSize": "11px",
                    }),
                ], style={"textAlign": "center", "flex": "1"}),
                
                # Profit Factor
                html.Div([
                    html.Div("Profit Factor", style={
                        "color": THEME["text_muted"],
                        "fontSize": "11px",
                        "textTransform": "uppercase",
                    }),
                    html.Div("2.36", style={
                        "color": THEME["gold"],
                        "fontSize": "24px",
                        "fontWeight": "700",
                        "fontFamily": "'JetBrains Mono', monospace",
                    }),
                    html.Div("$330 / $140", style={
                        "color": THEME["text_muted"],
                        "fontSize": "11px",
                    }),
                ], style={"textAlign": "center", "flex": "1"}),
                
                # Expectancy
                html.Div([
                    html.Div("Expectancy", style={
                        "color": THEME["text_muted"],
                        "fontSize": "11px",
                        "textTransform": "uppercase",
                    }),
                    html.Div("+$47", style={
                        "color": THEME["success"],
                        "fontSize": "24px",
                        "fontWeight": "700",
                        "fontFamily": "'JetBrains Mono', monospace",
                    }),
                    html.Div("per trade", style={
                        "color": THEME["text_muted"],
                        "fontSize": "11px",
                    }),
                ], style={"textAlign": "center", "flex": "1"}),
            ], style={
                "display": "flex",
                "gap": "16px",
                "padding": "16px",
                "backgroundColor": THEME["bg_tertiary"],
                "borderRadius": "8px",
            }),
        ], style={"marginTop": "20px"}),
        
        # Store for trade data
        dcc.Store(id="journal-trades-store", data=sample_trades),
        
    ], style={
        "backgroundColor": THEME["bg_secondary"],
        "border": f"1px solid {THEME['border']}",
        "borderRadius": "12px",
        "padding": "20px",
    })


def create_pnl_attribution_panel() -> html.Div:
    """Create P/L attribution breakdown panel."""
    
    return html.Div([
        html.Div([
            html.Span("📊", style={"fontSize": "20px", "marginRight": "10px", "color": THEME["gold"]}),
            html.Span("P/L Attribution", style={
                "fontSize": "16px",
                "fontWeight": "600",
                "color": THEME["text_primary"],
            }),
        ], style={
            "marginBottom": "16px",
            "paddingBottom": "8px",
            "borderBottom": f"2px solid {THEME['gold']}",
        }),
        
        # Attribution breakdown
        html.Div([
            # By Strategy
            html.Div([
                html.Div("By Strategy", style={
                    "color": THEME["text_secondary"],
                    "fontSize": "12px",
                    "marginBottom": "8px",
                    "fontWeight": "500",
                }),
                html.Div([
                    _create_attribution_bar("Iron Condor", 125, 190, THEME["success"]),
                    _create_attribution_bar("Put Credit Spread", 65, 190, THEME["success"]),
                    _create_attribution_bar("Call Debit Spread", 140, 190, THEME["success"]),
                    _create_attribution_bar("Straddle", -140, 190, THEME["danger"]),
                ]),
            ], style={"marginBottom": "20px"}),
            
            # By Driver
            html.Div([
                html.Div("By Driver", style={
                    "color": THEME["text_secondary"],
                    "fontSize": "12px",
                    "marginBottom": "8px",
                    "fontWeight": "500",
                }),
                html.Div([
                    _create_attribution_bar("Theta Decay", 180, 250, THEME["success"]),
                    _create_attribution_bar("Price Movement", 70, 250, THEME["success"]),
                    _create_attribution_bar("IV Change", -60, 250, THEME["danger"]),
                ]),
            ]),
        ]),
        
    ], style={
        "backgroundColor": THEME["bg_secondary"],
        "border": f"1px solid {THEME['border']}",
        "borderRadius": "12px",
        "padding": "20px",
    })


def _create_attribution_bar(label: str, value: int, max_val: int, color: str) -> html.Div:
    """Create a single attribution bar."""
    pct = abs(value) / max_val * 100
    sign = "+" if value >= 0 else ""
    
    return html.Div([
        html.Div([
            html.Span(label, style={"color": THEME["text_secondary"], "fontSize": "12px"}),
            html.Span(f"{sign}${value}", style={
                "color": color,
                "fontSize": "12px",
                "fontWeight": "600",
                "fontFamily": "'JetBrains Mono', monospace",
            }),
        ], style={"display": "flex", "justifyContent": "space-between", "marginBottom": "4px"}),
        
        html.Div([
            html.Div(style={
                "width": f"{pct}%",
                "height": "6px",
                "backgroundColor": color,
                "borderRadius": "3px",
                "transition": "width 0.3s ease",
            }),
        ], style={
            "width": "100%",
            "height": "6px",
            "backgroundColor": THEME["bg_tertiary"],
            "borderRadius": "3px",
        }),
    ], style={"marginBottom": "12px"})
