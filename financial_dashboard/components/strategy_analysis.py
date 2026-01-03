"""
Parameter Sensitivity Analysis & Strategy Comparison
Phase 7 - Backtesting & Simulation (Items 576-580)

Provides:
- Parameter sensitivity heatmaps
- Strategy comparison charts
- Walk-forward visualization
- Backtest export functionality
"""

from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime

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


def create_parameter_sensitivity_panel() -> html.Div:
    """Create parameter sensitivity analysis panel."""
    
    return html.Div([
        # Header
        html.Div([
            html.Div([
                html.Span("🎛️", style={"fontSize": "20px", "marginRight": "10px"}),
                html.Span("Parameter Sensitivity", style={
                    "fontSize": "16px",
                    "fontWeight": "600",
                    "color": THEME["text_primary"],
                }),
            ], style={"display": "flex", "alignItems": "center"}),
            
            # Parameter selection
            html.Div([
                dcc.Dropdown(
                    id="sensitivity-param-x",
                    options=[
                        {"label": "Profit Target %", "value": "profit_target"},
                        {"label": "Stop Loss %", "value": "stop_loss"},
                        {"label": "Days to Expiry", "value": "dte"},
                        {"label": "IV Rank Min", "value": "iv_rank"},
                        {"label": "Delta Target", "value": "delta"},
                        {"label": "Position Size %", "value": "position_size"},
                    ],
                    value="profit_target",
                    clearable=False,
                    style={"width": "150px"},
                    className="dark-dropdown",
                ),
                html.Span("vs", style={
                    "color": THEME["text_muted"],
                    "margin": "0 8px",
                    "fontSize": "12px",
                }),
                dcc.Dropdown(
                    id="sensitivity-param-y",
                    options=[
                        {"label": "Stop Loss %", "value": "stop_loss"},
                        {"label": "Profit Target %", "value": "profit_target"},
                        {"label": "Days to Expiry", "value": "dte"},
                        {"label": "IV Rank Min", "value": "iv_rank"},
                        {"label": "Delta Target", "value": "delta"},
                        {"label": "Position Size %", "value": "position_size"},
                    ],
                    value="stop_loss",
                    clearable=False,
                    style={"width": "150px"},
                    className="dark-dropdown",
                ),
            ], style={"display": "flex", "alignItems": "center"}),
        ], style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "marginBottom": "20px",
            "paddingBottom": "12px",
            "borderBottom": f"2px solid {THEME['gold']}",
        }),
        
        # Metric selector
        html.Div([
            html.Span("Metric: ", style={
                "color": THEME["text_muted"],
                "fontSize": "12px",
                "marginRight": "8px",
            }),
            dcc.RadioItems(
                id="sensitivity-metric",
                options=[
                    {"label": " Sharpe", "value": "sharpe"},
                    {"label": " Return", "value": "return"},
                    {"label": " Win Rate", "value": "win_rate"},
                    {"label": " Profit Factor", "value": "profit_factor"},
                    {"label": " Max DD", "value": "max_dd"},
                ],
                value="sharpe",
                inline=True,
                labelStyle={
                    "color": THEME["text_secondary"],
                    "marginRight": "16px",
                    "fontSize": "12px",
                },
            ),
        ], style={"marginBottom": "16px"}),
        
        # Heatmap
        dcc.Graph(
            id="sensitivity-heatmap",
            figure=create_sensitivity_heatmap(),
            config={"displayModeBar": False},
            style={"height": "400px"},
        ),
        
        # Optimal parameters summary
        html.Div([
            html.H6("Optimal Parameters", style={
                "color": THEME["text_secondary"],
                "fontSize": "13px",
                "marginBottom": "12px",
            }),
            html.Div([
                _create_optimal_param("Profit Target", "50%", "Sharpe: 1.42"),
                _create_optimal_param("Stop Loss", "200%", "Sharpe: 1.42"),
                _create_optimal_param("DTE", "30-45", "Sharpe: 1.38"),
                _create_optimal_param("IV Rank", ">30", "Sharpe: 1.35"),
            ], style={
                "display": "grid",
                "gridTemplateColumns": "repeat(4, 1fr)",
                "gap": "12px",
            }),
        ], style={"marginTop": "20px"}),
        
    ], style={
        "backgroundColor": THEME["bg_secondary"],
        "border": f"1px solid {THEME['border']}",
        "borderRadius": "12px",
        "padding": "20px",
    })


def _create_optimal_param(name: str, value: str, metric: str) -> html.Div:
    """Create optimal parameter card."""
    return html.Div([
        html.Div(name, style={
            "color": THEME["text_muted"],
            "fontSize": "11px",
            "marginBottom": "4px",
        }),
        html.Div(value, style={
            "color": THEME["gold"],
            "fontSize": "18px",
            "fontWeight": "600",
            "fontFamily": "'JetBrains Mono', monospace",
        }),
        html.Div(metric, style={
            "color": THEME["text_muted"],
            "fontSize": "10px",
        }),
    ], style={
        "backgroundColor": THEME["bg_tertiary"],
        "padding": "12px",
        "borderRadius": "6px",
        "textAlign": "center",
    })


def create_sensitivity_heatmap() -> go.Figure:
    """Create parameter sensitivity heatmap."""
    
    # Parameter ranges
    profit_targets = [25, 30, 40, 50, 60, 75, 100]
    stop_losses = [100, 150, 200, 250, 300, 400]
    
    # Generate synthetic Sharpe ratios
    np.random.seed(42)
    sharpe_matrix = np.zeros((len(stop_losses), len(profit_targets)))
    
    for i, sl in enumerate(stop_losses):
        for j, pt in enumerate(profit_targets):
            # Optimal around 50% PT and 200% SL
            base = 1.2
            pt_factor = 1 - abs(pt - 50) / 100
            sl_factor = 1 - abs(sl - 200) / 400
            sharpe = base + 0.4 * pt_factor + 0.3 * sl_factor + np.random.uniform(-0.1, 0.1)
            sharpe_matrix[i, j] = max(0, sharpe)
    
    # Find optimal
    max_idx = np.unravel_index(sharpe_matrix.argmax(), sharpe_matrix.shape)
    
    fig = go.Figure(data=go.Heatmap(
        z=sharpe_matrix,
        x=[f"{pt}%" for pt in profit_targets],
        y=[f"{sl}%" for sl in stop_losses],
        colorscale=[
            [0, THEME["danger"]],
            [0.5, THEME["warning"]],
            [1, THEME["success"]],
        ],
        text=[[f"{v:.2f}" for v in row] for row in sharpe_matrix],
        texttemplate="%{text}",
        textfont={"size": 11, "color": THEME["text_primary"]},
        hovertemplate="PT: %{x}<br>SL: %{y}<br>Sharpe: %{z:.2f}<extra></extra>",
        colorbar=dict(
            title=dict(text="Sharpe", font=dict(color=THEME["text_secondary"])),
            tickfont=dict(color=THEME["text_secondary"]),
        ),
    ))
    
    # Add marker for optimal
    fig.add_annotation(
        x=max_idx[1],
        y=max_idx[0],
        text="★",
        showarrow=False,
        font=dict(size=20, color=THEME["gold"]),
    )
    
    fig.update_layout(
        title="Sharpe Ratio by Parameter Combination",
        xaxis_title="Profit Target",
        yaxis_title="Stop Loss",
        paper_bgcolor=THEME["bg_secondary"],
        plot_bgcolor=THEME["bg_secondary"],
        font=dict(color=THEME["text_primary"], family="JetBrains Mono, monospace", size=11),
        margin=dict(l=80, r=40, t=50, b=60),
    )
    
    return fig


def create_strategy_comparison_panel() -> html.Div:
    """Create strategy comparison panel."""
    
    return html.Div([
        # Header
        html.Div([
            html.Div([
                html.Span("⚖️", style={"fontSize": "20px", "marginRight": "10px"}),
                html.Span("Strategy Comparison", style={
                    "fontSize": "16px",
                    "fontWeight": "600",
                    "color": THEME["text_primary"],
                }),
            ], style={"display": "flex", "alignItems": "center"}),
            
            dbc.Button([
                html.Span("➕", style={"marginRight": "6px"}),
                "Add Strategy",
            ], id="add-strategy-btn", size="sm", color="warning", style={
                "backgroundColor": THEME["gold"],
                "border": "none",
                "color": "#0D1117",
            }),
        ], style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "marginBottom": "20px",
            "paddingBottom": "12px",
            "borderBottom": f"2px solid {THEME['gold']}",
        }),
        
        # Strategy selector
        html.Div([
            dcc.Checklist(
                id="strategy-comparison-select",
                options=[
                    {"label": " Iron Condor", "value": "iron_condor"},
                    {"label": " Put Credit Spread", "value": "put_spread"},
                    {"label": " Call Credit Spread", "value": "call_spread"},
                    {"label": " Straddle", "value": "straddle"},
                    {"label": " Butterfly", "value": "butterfly"},
                ],
                value=["iron_condor", "put_spread", "straddle"],
                inline=True,
                labelStyle={
                    "color": THEME["text_secondary"],
                    "marginRight": "20px",
                    "fontSize": "12px",
                },
            ),
        ], style={"marginBottom": "16px"}),
        
        # Comparison Charts
        html.Div([
            # Equity curves
            html.Div([
                dcc.Graph(
                    id="strategy-equity-comparison",
                    figure=create_strategy_equity_comparison(),
                    config={"displayModeBar": False},
                    style={"height": "280px"},
                ),
            ], style={"flex": "2"}),
            
            # Metrics radar
            html.Div([
                dcc.Graph(
                    id="strategy-radar",
                    figure=create_strategy_radar(),
                    config={"displayModeBar": False},
                    style={"height": "280px"},
                ),
            ], style={"flex": "1"}),
        ], style={
            "display": "flex",
            "gap": "16px",
            "marginBottom": "20px",
        }),
        
        # Comparison Table
        _create_comparison_table(),
        
    ], style={
        "backgroundColor": THEME["bg_secondary"],
        "border": f"1px solid {THEME['border']}",
        "borderRadius": "12px",
        "padding": "20px",
    })


def create_strategy_equity_comparison() -> go.Figure:
    """Create strategy equity curve comparison."""
    
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", "2024-12-31", freq="B")
    
    strategies = {
        "Iron Condor": {"color": THEME["gold"], "vol": 0.006, "drift": 0.0008},
        "Put Credit Spread": {"color": THEME["success"], "vol": 0.008, "drift": 0.0006},
        "Straddle": {"color": THEME["info"], "vol": 0.012, "drift": 0.0004},
    }
    
    fig = go.Figure()
    
    for name, params in strategies.items():
        returns = np.random.normal(params["drift"], params["vol"], len(dates))
        equity = 100000 * np.cumprod(1 + returns)
        
        fig.add_trace(go.Scatter(
            x=dates,
            y=equity,
            mode="lines",
            name=name,
            line=dict(color=params["color"], width=2),
        ))
    
    fig.update_layout(
        title="Equity Curve Comparison",
        paper_bgcolor=THEME["bg_secondary"],
        plot_bgcolor=THEME["bg_secondary"],
        font=dict(color=THEME["text_primary"], family="JetBrains Mono, monospace", size=10),
        margin=dict(l=50, r=30, t=40, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
        hovermode="x unified",
    )
    
    fig.update_xaxes(gridcolor=THEME["bg_tertiary"])
    fig.update_yaxes(gridcolor=THEME["bg_tertiary"], title="Portfolio Value ($)")
    
    return fig


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    """Convert hex color to rgba string with alpha."""
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def create_strategy_radar() -> go.Figure:
    """Create strategy comparison radar chart."""
    
    categories = ["Return", "Sharpe", "Win Rate", "Profit Factor", "Recovery"]
    
    strategies_data = {
        "Iron Condor": [0.75, 0.85, 0.9, 0.8, 0.7],
        "Put Credit Spread": [0.65, 0.7, 0.85, 0.75, 0.8],
        "Straddle": [0.5, 0.55, 0.6, 0.65, 0.5],
    }
    
    colors = {
        "Iron Condor": THEME["gold"],
        "Put Credit Spread": THEME["success"],
        "Straddle": THEME["info"],
    }
    
    fig = go.Figure()
    
    for name, values in strategies_data.items():
        fig.add_trace(go.Scatterpolar(
            r=values + [values[0]],  # Close the polygon
            theta=categories + [categories[0]],
            name=name,
            line=dict(color=colors[name], width=2),
            fill="toself",
            fillcolor=_hex_to_rgba(colors[name], 0.12),
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 1],
                gridcolor=THEME["bg_tertiary"],
                tickfont=dict(size=8, color=THEME["text_muted"]),
            ),
            angularaxis=dict(
                gridcolor=THEME["bg_tertiary"],
                tickfont=dict(size=9, color=THEME["text_secondary"]),
            ),
            bgcolor=THEME["bg_secondary"],
        ),
        paper_bgcolor=THEME["bg_secondary"],
        font=dict(color=THEME["text_primary"], family="JetBrains Mono, monospace", size=10),
        margin=dict(l=40, r=40, t=20, b=40),
        showlegend=False,
    )
    
    return fig


def _create_comparison_table() -> dash_table.DataTable:
    """Create strategy comparison table."""
    
    data = [
        {"strategy": "Iron Condor", "return": "+24.7%", "sharpe": "1.42", "sortino": "2.18", 
         "win_rate": "73%", "pf": "2.31", "max_dd": "-8.3%", "trades": "255"},
        {"strategy": "Put Credit Spread", "return": "+18.2%", "sharpe": "1.15", "sortino": "1.72",
         "win_rate": "68%", "pf": "1.85", "max_dd": "-11.2%", "trades": "312"},
        {"strategy": "Straddle", "return": "+8.5%", "sharpe": "0.65", "sortino": "0.92",
         "win_rate": "52%", "pf": "1.24", "max_dd": "-18.7%", "trades": "145"},
    ]
    
    return dash_table.DataTable(
        columns=[
            {"name": "Strategy", "id": "strategy"},
            {"name": "Return", "id": "return"},
            {"name": "Sharpe", "id": "sharpe"},
            {"name": "Sortino", "id": "sortino"},
            {"name": "Win Rate", "id": "win_rate"},
            {"name": "PF", "id": "pf"},
            {"name": "Max DD", "id": "max_dd"},
            {"name": "Trades", "id": "trades"},
        ],
        data=data,
        style_header={
            "backgroundColor": THEME["bg_tertiary"],
            "color": THEME["text_primary"],
            "fontWeight": "600",
            "fontSize": "11px",
            "textTransform": "uppercase",
            "padding": "10px 8px",
            "borderBottom": f"2px solid {THEME['gold']}",
        },
        style_cell={
            "backgroundColor": THEME["bg_secondary"],
            "color": THEME["text_primary"],
            "fontSize": "12px",
            "fontFamily": "'JetBrains Mono', monospace",
            "padding": "8px",
            "border": f"1px solid {THEME['border']}",
            "textAlign": "center",
        },
        style_data_conditional=[
            {
                "if": {"filter_query": "{return} contains '+'", "column_id": "return"},
                "color": THEME["success"],
                "fontWeight": "600",
            },
            {
                "if": {"column_id": "strategy"},
                "textAlign": "left",
                "fontWeight": "500",
            },
            {
                "if": {"filter_query": "{max_dd} contains '-'", "column_id": "max_dd"},
                "color": THEME["danger"],
            },
        ],
    )


def create_walk_forward_visualization() -> html.Div:
    """Create walk-forward optimization visualization."""
    
    return html.Div([
        # Header
        html.Div([
            html.Span("📊", style={"fontSize": "20px", "marginRight": "10px"}),
            html.Span("Walk-Forward Analysis", style={
                "fontSize": "16px",
                "fontWeight": "600",
                "color": THEME["text_primary"],
            }),
        ], style={
            "marginBottom": "16px",
            "paddingBottom": "12px",
            "borderBottom": f"2px solid {THEME['gold']}",
        }),
        
        # Walk-forward chart
        dcc.Graph(
            id="walk-forward-chart",
            figure=create_walk_forward_figure(),
            config={"displayModeBar": False},
            style={"height": "300px"},
        ),
        
        # Summary stats
        html.Div([
            html.Div([
                html.Div("In-Sample Avg", style={"color": THEME["text_muted"], "fontSize": "11px"}),
                html.Div("+18.4%", style={"color": THEME["info"], "fontSize": "18px", "fontWeight": "600"}),
            ], style={"textAlign": "center"}),
            html.Div([
                html.Div("Out-of-Sample Avg", style={"color": THEME["text_muted"], "fontSize": "11px"}),
                html.Div("+12.1%", style={"color": THEME["success"], "fontSize": "18px", "fontWeight": "600"}),
            ], style={"textAlign": "center"}),
            html.Div([
                html.Div("Efficiency Ratio", style={"color": THEME["text_muted"], "fontSize": "11px"}),
                html.Div("65.8%", style={"color": THEME["gold"], "fontSize": "18px", "fontWeight": "600"}),
            ], style={"textAlign": "center"}),
            html.Div([
                html.Div("Windows Tested", style={"color": THEME["text_muted"], "fontSize": "11px"}),
                html.Div("24", style={"color": THEME["text_primary"], "fontSize": "18px", "fontWeight": "600"}),
            ], style={"textAlign": "center"}),
        ], style={
            "display": "grid",
            "gridTemplateColumns": "repeat(4, 1fr)",
            "gap": "16px",
            "marginTop": "16px",
            "padding": "16px",
            "backgroundColor": THEME["bg_tertiary"],
            "borderRadius": "8px",
        }),
        
    ], style={
        "backgroundColor": THEME["bg_secondary"],
        "border": f"1px solid {THEME['border']}",
        "borderRadius": "12px",
        "padding": "20px",
    })


def create_walk_forward_figure() -> go.Figure:
    """Create walk-forward optimization chart."""
    
    np.random.seed(42)
    windows = list(range(1, 25))
    in_sample = 15 + np.random.uniform(-5, 8, 24)
    out_sample = 10 + np.random.uniform(-8, 10, 24)
    
    fig = go.Figure()
    
    # In-sample bars
    fig.add_trace(go.Bar(
        x=windows,
        y=in_sample,
        name="In-Sample",
        marker_color=THEME["info"],
        opacity=0.7,
    ))
    
    # Out-of-sample bars
    fig.add_trace(go.Bar(
        x=windows,
        y=out_sample,
        name="Out-of-Sample",
        marker_color=THEME["success"],
        opacity=0.7,
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color=THEME["text_muted"], line_width=1)
    
    fig.update_layout(
        title="Walk-Forward Windows Performance",
        xaxis_title="Window #",
        yaxis_title="Return (%)",
        paper_bgcolor=THEME["bg_secondary"],
        plot_bgcolor=THEME["bg_secondary"],
        font=dict(color=THEME["text_primary"], family="JetBrains Mono, monospace", size=10),
        margin=dict(l=50, r=30, t=40, b=40),
        barmode="group",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(0,0,0,0)",
        ),
    )
    
    fig.update_xaxes(gridcolor=THEME["bg_tertiary"])
    fig.update_yaxes(gridcolor=THEME["bg_tertiary"])
    
    return fig


def create_backtest_export_panel() -> html.Div:
    """Create backtest results export panel."""
    
    return html.Div([
        html.Div([
            html.Span("📤", style={"fontSize": "16px", "marginRight": "8px"}),
            html.Span("Export Results", style={
                "fontSize": "14px",
                "fontWeight": "500",
                "color": THEME["text_primary"],
            }),
        ], style={"marginBottom": "12px"}),
        
        html.Div([
            dbc.Button([
                html.Span("📊", style={"marginRight": "6px"}),
                "Full Report (PDF)",
            ], id="export-backtest-pdf", size="sm", color="secondary", outline=True, className="me-2"),
            
            dbc.Button([
                html.Span("📋", style={"marginRight": "6px"}),
                "Trades (CSV)",
            ], id="export-backtest-csv", size="sm", color="secondary", outline=True, className="me-2"),
            
            dbc.Button([
                html.Span("📈", style={"marginRight": "6px"}),
                "Equity (JSON)",
            ], id="export-backtest-json", size="sm", color="secondary", outline=True),
        ]),
        
        dcc.Download(id="backtest-download"),
        
    ], style={
        "backgroundColor": THEME["bg_tertiary"],
        "borderRadius": "8px",
        "padding": "16px",
    })
