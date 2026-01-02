"""
Greeks Timeseries Component
Phase 6 - Visualization & UX (Items 465-475)

Provides real-time and historical Greeks visualization per position:
- Delta, Gamma, Theta, Vega timeseries charts
- Greeks heatmap by strike/expiry
- Position-level Greeks aggregation
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta

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


def create_greeks_timeseries_panel() -> html.Div:
    """Create the Greeks timeseries visualization panel."""
    
    return html.Div([
        # Header
        html.Div([
            html.Div([
                html.Span("📈", style={"fontSize": "20px", "marginRight": "10px"}),
                html.Span("Greeks Timeseries", style={
                    "fontSize": "16px",
                    "fontWeight": "600",
                    "color": THEME["text_primary"],
                }),
            ], style={"display": "flex", "alignItems": "center"}),
            
            # Controls
            html.Div([
                dcc.Dropdown(
                    id="greeks-position-select",
                    options=[
                        {"label": "SPY Iron Condor Jan 17", "value": "spy_ic_jan17"},
                        {"label": "NVDA Put Spread Feb 21", "value": "nvda_ps_feb21"},
                        {"label": "AAPL Call Jan 10", "value": "aapl_call_jan10"},
                        {"label": "Portfolio Total", "value": "portfolio"},
                    ],
                    value="portfolio",
                    clearable=False,
                    style={"width": "200px"},
                    className="dark-dropdown",
                ),
                dcc.Dropdown(
                    id="greeks-timeframe",
                    options=[
                        {"label": "1 Day", "value": "1d"},
                        {"label": "1 Week", "value": "1w"},
                        {"label": "1 Month", "value": "1m"},
                        {"label": "Since Open", "value": "open"},
                    ],
                    value="1w",
                    clearable=False,
                    style={"width": "120px", "marginLeft": "8px"},
                    className="dark-dropdown",
                ),
            ], style={"display": "flex", "alignItems": "center"}),
        ], style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "marginBottom": "16px",
            "paddingBottom": "12px",
            "borderBottom": f"2px solid {THEME['gold']}",
        }),
        
        # Current Greeks Summary
        html.Div([
            _create_greek_summary_card("Delta", "-12.5", "Δ", THEME["info"]),
            _create_greek_summary_card("Gamma", "+0.82", "Γ", THEME["warning"]),
            _create_greek_summary_card("Theta", "+$45.20", "Θ", THEME["success"]),
            _create_greek_summary_card("Vega", "-$23.10", "ν", THEME["danger"]),
            _create_greek_summary_card("Rho", "+$2.15", "ρ", THEME["text_secondary"]),
        ], style={
            "display": "grid",
            "gridTemplateColumns": "repeat(5, 1fr)",
            "gap": "12px",
            "marginBottom": "20px",
        }),
        
        # Main Chart
        dcc.Graph(
            id="greeks-timeseries-chart",
            figure=create_greeks_timeseries_figure(),
            config={"displayModeBar": False},
            style={"height": "350px"},
        ),
        
        # Greeks by Strike Heatmap
        html.Div([
            html.H6("Greeks Distribution by Strike", style={
                "color": THEME["text_secondary"],
                "fontSize": "13px",
                "marginBottom": "12px",
            }),
            dcc.Graph(
                id="greeks-strike-heatmap",
                figure=create_greeks_heatmap_figure(),
                config={"displayModeBar": False},
                style={"height": "200px"},
            ),
        ], style={"marginTop": "20px"}),
        
    ], style={
        "backgroundColor": THEME["bg_secondary"],
        "border": f"1px solid {THEME['border']}",
        "borderRadius": "12px",
        "padding": "20px",
    })


def _create_greek_summary_card(name: str, value: str, symbol: str, color: str) -> html.Div:
    """Create a Greek summary card."""
    is_positive = value.startswith("+")
    
    return html.Div([
        html.Div([
            html.Span(symbol, style={
                "fontSize": "18px",
                "fontWeight": "700",
                "color": color,
                "marginRight": "8px",
            }),
            html.Span(name, style={
                "fontSize": "12px",
                "color": THEME["text_muted"],
            }),
        ], style={"display": "flex", "alignItems": "baseline"}),
        html.Div(value, style={
            "fontSize": "20px",
            "fontWeight": "600",
            "fontFamily": "'JetBrains Mono', monospace",
            "color": THEME["success"] if is_positive else THEME["danger"],
        }),
    ], style={
        "backgroundColor": THEME["bg_tertiary"],
        "padding": "12px",
        "borderRadius": "8px",
        "borderLeft": f"3px solid {color}",
    })


def create_greeks_timeseries_figure() -> go.Figure:
    """Create the main Greeks timeseries chart."""
    
    # Generate sample data
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=100, freq="h")
    
    delta = np.cumsum(np.random.randn(100) * 0.5) - 12
    gamma = np.cumsum(np.random.randn(100) * 0.02) + 0.8
    theta = np.cumsum(np.random.randn(100) * 0.3) + 45
    vega = np.cumsum(np.random.randn(100) * 0.4) - 23
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Delta (Δ)", "Gamma (Γ)", "Theta (Θ)", "Vega (ν)"),
        vertical_spacing=0.12,
        horizontal_spacing=0.08,
    )
    
    # Delta
    fig.add_trace(
        go.Scatter(x=dates, y=delta, mode="lines", name="Delta",
                   line=dict(color=THEME["info"], width=2),
                   fill="tozeroy", fillcolor=f"rgba(88, 166, 255, 0.1)"),
        row=1, col=1
    )
    
    # Gamma
    fig.add_trace(
        go.Scatter(x=dates, y=gamma, mode="lines", name="Gamma",
                   line=dict(color=THEME["warning"], width=2),
                   fill="tozeroy", fillcolor=f"rgba(210, 153, 34, 0.1)"),
        row=1, col=2
    )
    
    # Theta
    fig.add_trace(
        go.Scatter(x=dates, y=theta, mode="lines", name="Theta",
                   line=dict(color=THEME["success"], width=2),
                   fill="tozeroy", fillcolor=f"rgba(63, 185, 80, 0.1)"),
        row=2, col=1
    )
    
    # Vega
    fig.add_trace(
        go.Scatter(x=dates, y=vega, mode="lines", name="Vega",
                   line=dict(color=THEME["danger"], width=2),
                   fill="tozeroy", fillcolor=f"rgba(248, 81, 73, 0.1)"),
        row=2, col=2
    )
    
    fig.update_layout(
        paper_bgcolor=THEME["bg_secondary"],
        plot_bgcolor=THEME["bg_secondary"],
        font=dict(color=THEME["text_primary"], family="JetBrains Mono, monospace", size=10),
        margin=dict(l=40, r=20, t=40, b=40),
        showlegend=False,
        hovermode="x unified",
    )
    
    # Update all axes
    for i in range(1, 3):
        for j in range(1, 3):
            fig.update_xaxes(gridcolor=THEME["bg_tertiary"], row=i, col=j)
            fig.update_yaxes(gridcolor=THEME["bg_tertiary"], row=i, col=j)
    
    return fig


def create_greeks_heatmap_figure() -> go.Figure:
    """Create Greeks distribution heatmap by strike."""
    
    strikes = [580, 585, 590, 595, 600, 605, 610, 615, 620]
    greeks = ["Delta", "Gamma", "Theta", "Vega"]
    
    # Sample data
    np.random.seed(42)
    data = np.random.randn(len(greeks), len(strikes))
    data[0, :] = np.linspace(-0.8, 0.8, len(strikes))  # Delta
    data[1, :] = np.exp(-((np.array(strikes) - 600) ** 2) / 200)  # Gamma peak at ATM
    data[2, :] = -np.exp(-((np.array(strikes) - 600) ** 2) / 300)  # Theta
    data[3, :] = np.exp(-((np.array(strikes) - 600) ** 2) / 400) * 0.5  # Vega
    
    fig = go.Figure(data=go.Heatmap(
        z=data,
        x=[str(s) for s in strikes],
        y=greeks,
        colorscale=[
            [0, THEME["danger"]],
            [0.5, THEME["bg_tertiary"]],
            [1, THEME["success"]],
        ],
        zmid=0,
        text=[[f"{v:.2f}" for v in row] for row in data],
        texttemplate="%{text}",
        textfont={"size": 9, "color": THEME["text_primary"]},
    ))
    
    fig.update_layout(
        paper_bgcolor=THEME["bg_secondary"],
        plot_bgcolor=THEME["bg_secondary"],
        font=dict(color=THEME["text_primary"], family="JetBrains Mono, monospace", size=10),
        margin=dict(l=60, r=20, t=10, b=40),
        xaxis_title="Strike Price",
    )
    
    return fig
