"""
Backtest Visualization Dashboard
Phase 7 - Backtesting & Simulation (Items 531-550)

Provides comprehensive visualization of backtest results including:
- Equity curve with drawdown overlay
- Trade distribution charts
- Performance metrics dashboard
- Monte Carlo cone chart
"""

from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import pandas as pd
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

# Plotly template
PLOTLY_TEMPLATE = {
    "layout": {
        "paper_bgcolor": THEME["bg_primary"],
        "plot_bgcolor": THEME["bg_primary"],
        "font": {"color": THEME["text_primary"], "family": "JetBrains Mono, monospace"},
        "xaxis": {"gridcolor": THEME["bg_tertiary"], "zerolinecolor": THEME["border"]},
        "yaxis": {"gridcolor": THEME["bg_tertiary"], "zerolinecolor": THEME["border"]},
    }
}


def create_backtest_dashboard() -> html.Div:
    """Create the main backtest results dashboard."""
    
    return html.Div([
        # Header
        html.Div([
            html.Div([
                html.Span("🔬", style={"fontSize": "28px", "marginRight": "12px"}),
                html.Div([
                    html.Span("Backtest Lab", style={
                        "fontSize": "20px",
                        "fontWeight": "700",
                        "color": THEME["text_primary"],
                    }),
                    html.Span(" — Strategy Performance Analysis", style={
                        "fontSize": "14px",
                        "color": THEME["text_muted"],
                    }),
                ]),
            ], style={"display": "flex", "alignItems": "center"}),
            
            html.Div([
                dbc.Badge("Iron Condor", color="warning", className="me-2"),
                dbc.Badge("2 Years", color="info", className="me-2"),
                dbc.Badge("100% Complete", color="success"),
            ]),
        ], style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "marginBottom": "24px",
            "paddingBottom": "16px",
            "borderBottom": f"2px solid {THEME['gold']}",
        }),
        
        # Performance Metrics Row
        html.Div([
            _create_metric_card("Total Return", "+24.7%", THEME["success"], "vs S&P: +8.2%"),
            _create_metric_card("CAGR", "+11.8%", THEME["success"], "Annualized"),
            _create_metric_card("Sharpe", "1.42", THEME["gold"], "Risk-adjusted"),
            _create_metric_card("Sortino", "2.18", THEME["info"], "Downside only"),
            _create_metric_card("Max DD", "-8.3%", THEME["danger"], "Peak to trough"),
            _create_metric_card("Win Rate", "73%", THEME["success"], "186/255 trades"),
        ], style={
            "display": "grid",
            "gridTemplateColumns": "repeat(6, 1fr)",
            "gap": "16px",
            "marginBottom": "24px",
        }),
        
        # Main Charts Row
        html.Div([
            # Equity Curve
            html.Div([
                dcc.Graph(
                    id="backtest-equity-chart",
                    figure=create_equity_curve_figure(),
                    config={"displayModeBar": False},
                    style={"height": "350px"},
                ),
            ], style={
                "flex": "2",
                "backgroundColor": THEME["bg_secondary"],
                "borderRadius": "12px",
                "padding": "16px",
                "border": f"1px solid {THEME['border']}",
            }),
            
            # Trade Distribution
            html.Div([
                dcc.Graph(
                    id="backtest-trade-dist",
                    figure=create_trade_distribution_figure(),
                    config={"displayModeBar": False},
                    style={"height": "350px"},
                ),
            ], style={
                "flex": "1",
                "backgroundColor": THEME["bg_secondary"],
                "borderRadius": "12px",
                "padding": "16px",
                "border": f"1px solid {THEME['border']}",
            }),
        ], style={
            "display": "flex",
            "gap": "16px",
            "marginBottom": "24px",
        }),
        
        # Second Row - Monte Carlo & Monthly
        html.Div([
            # Monte Carlo Cone
            html.Div([
                dcc.Graph(
                    id="backtest-monte-carlo",
                    figure=create_monte_carlo_figure(),
                    config={"displayModeBar": False},
                    style={"height": "300px"},
                ),
            ], style={
                "flex": "1",
                "backgroundColor": THEME["bg_secondary"],
                "borderRadius": "12px",
                "padding": "16px",
                "border": f"1px solid {THEME['border']}",
            }),
            
            # Monthly Returns Heatmap
            html.Div([
                dcc.Graph(
                    id="backtest-monthly-heatmap",
                    figure=create_monthly_heatmap_figure(),
                    config={"displayModeBar": False},
                    style={"height": "300px"},
                ),
            ], style={
                "flex": "1",
                "backgroundColor": THEME["bg_secondary"],
                "borderRadius": "12px",
                "padding": "16px",
                "border": f"1px solid {THEME['border']}",
            }),
        ], style={
            "display": "flex",
            "gap": "16px",
            "marginBottom": "24px",
        }),
        
        # Risk Metrics & Trade Table
        html.Div([
            # Risk Metrics Panel
            html.Div([
                html.H6("📊 Risk Metrics", style={
                    "color": THEME["text_primary"],
                    "marginBottom": "16px",
                }),
                _create_risk_metrics_panel(),
            ], style={
                "flex": "1",
                "backgroundColor": THEME["bg_secondary"],
                "borderRadius": "12px",
                "padding": "16px",
                "border": f"1px solid {THEME['border']}",
            }),
            
            # Recent Trades
            html.Div([
                html.H6("📋 Recent Trades", style={
                    "color": THEME["text_primary"],
                    "marginBottom": "16px",
                }),
                _create_trades_table(),
            ], style={
                "flex": "2",
                "backgroundColor": THEME["bg_secondary"],
                "borderRadius": "12px",
                "padding": "16px",
                "border": f"1px solid {THEME['border']}",
            }),
        ], style={
            "display": "flex",
            "gap": "16px",
        }),
        
    ], style={
        "padding": "24px",
        "backgroundColor": THEME["bg_primary"],
        "minHeight": "100vh",
    })


def _create_metric_card(label: str, value: str, color: str, subtitle: str) -> html.Div:
    """Create a metric card."""
    return html.Div([
        html.Div(label, style={
            "color": THEME["text_muted"],
            "fontSize": "11px",
            "textTransform": "uppercase",
            "letterSpacing": "0.5px",
            "marginBottom": "4px",
        }),
        html.Div(value, style={
            "color": color,
            "fontSize": "24px",
            "fontWeight": "700",
            "fontFamily": "'JetBrains Mono', monospace",
        }),
        html.Div(subtitle, style={
            "color": THEME["text_muted"],
            "fontSize": "10px",
            "marginTop": "2px",
        }),
    ], style={
        "backgroundColor": THEME["bg_secondary"],
        "padding": "16px",
        "borderRadius": "8px",
        "border": f"1px solid {THEME['border']}",
        "textAlign": "center",
    })


def create_equity_curve_figure() -> go.Figure:
    """Create equity curve with drawdown overlay."""
    
    # Sample data
    np.random.seed(42)
    dates = pd.date_range("2023-01-01", "2024-12-31", freq="B")
    returns = np.random.normal(0.0008, 0.008, len(dates))
    equity = 100000 * np.cumprod(1 + returns)
    
    # Calculate drawdown
    rolling_max = pd.Series(equity).expanding().max()
    drawdown = (equity - rolling_max) / rolling_max * 100
    
    # Create figure with secondary y-axis
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    
    # Equity curve
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=equity,
            name="Portfolio Value",
            line=dict(color=THEME["gold"], width=2),
            fill="tozeroy",
            fillcolor=f"rgba(245, 194, 17, 0.1)",
        ),
        secondary_y=False,
    )
    
    # Drawdown
    fig.add_trace(
        go.Scatter(
            x=dates,
            y=drawdown,
            name="Drawdown",
            line=dict(color=THEME["danger"], width=1),
            fill="tozeroy",
            fillcolor=f"rgba(248, 81, 73, 0.2)",
        ),
        secondary_y=True,
    )
    
    fig.update_layout(
        title="Equity Curve & Drawdown",
        paper_bgcolor=THEME["bg_secondary"],
        plot_bgcolor=THEME["bg_secondary"],
        font=dict(color=THEME["text_primary"], family="JetBrains Mono, monospace", size=11),
        margin=dict(l=50, r=50, t=40, b=40),
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
    
    fig.update_xaxes(gridcolor=THEME["bg_tertiary"], showgrid=True)
    fig.update_yaxes(
        title_text="Portfolio Value ($)",
        gridcolor=THEME["bg_tertiary"],
        showgrid=True,
        secondary_y=False,
    )
    fig.update_yaxes(
        title_text="Drawdown (%)",
        gridcolor=THEME["bg_tertiary"],
        showgrid=False,
        secondary_y=True,
    )
    
    return fig


def create_trade_distribution_figure() -> go.Figure:
    """Create trade P&L distribution chart."""
    
    # Sample trade returns
    np.random.seed(42)
    trade_returns = np.concatenate([
        np.random.normal(50, 30, 180),  # Wins
        np.random.normal(-60, 40, 75),  # Losses
    ])
    
    fig = go.Figure()
    
    # Histogram
    fig.add_trace(go.Histogram(
        x=trade_returns,
        nbinsx=30,
        marker=dict(
            color=[THEME["success"] if x > 0 else THEME["danger"] for x in np.histogram(trade_returns, bins=30)[1][:-1]],
            line=dict(color=THEME["bg_primary"], width=1),
        ),
        opacity=0.8,
    ))
    
    # Add vertical line at zero
    fig.add_vline(x=0, line_dash="dash", line_color=THEME["text_muted"], line_width=1)
    
    # Add mean line
    fig.add_vline(x=np.mean(trade_returns), line_dash="dot", line_color=THEME["gold"], line_width=2,
                  annotation_text=f"Mean: ${np.mean(trade_returns):.0f}")
    
    fig.update_layout(
        title="Trade P&L Distribution",
        xaxis_title="P&L ($)",
        yaxis_title="Frequency",
        paper_bgcolor=THEME["bg_secondary"],
        plot_bgcolor=THEME["bg_secondary"],
        font=dict(color=THEME["text_primary"], family="JetBrains Mono, monospace", size=11),
        margin=dict(l=50, r=30, t=40, b=40),
        showlegend=False,
    )
    
    fig.update_xaxes(gridcolor=THEME["bg_tertiary"])
    fig.update_yaxes(gridcolor=THEME["bg_tertiary"])
    
    return fig


def create_monte_carlo_figure() -> go.Figure:
    """Create Monte Carlo simulation cone chart."""
    
    np.random.seed(42)
    n_simulations = 100
    n_periods = 252
    
    # Generate simulation paths
    all_paths = []
    for _ in range(n_simulations):
        returns = np.random.normal(0.0008, 0.01, n_periods)
        path = 100000 * np.cumprod(1 + returns)
        all_paths.append(path)
    
    all_paths = np.array(all_paths)
    
    # Calculate percentiles
    p5 = np.percentile(all_paths, 5, axis=0)
    p25 = np.percentile(all_paths, 25, axis=0)
    p50 = np.percentile(all_paths, 50, axis=0)
    p75 = np.percentile(all_paths, 75, axis=0)
    p95 = np.percentile(all_paths, 95, axis=0)
    
    x = list(range(n_periods))
    
    fig = go.Figure()
    
    # 5-95 percentile band
    fig.add_trace(go.Scatter(
        x=x + x[::-1],
        y=list(p95) + list(p5[::-1]),
        fill='toself',
        fillcolor=f"rgba(245, 194, 17, 0.1)",
        line=dict(color='rgba(0,0,0,0)'),
        name='5-95% Range',
    ))
    
    # 25-75 percentile band
    fig.add_trace(go.Scatter(
        x=x + x[::-1],
        y=list(p75) + list(p25[::-1]),
        fill='toself',
        fillcolor=f"rgba(245, 194, 17, 0.2)",
        line=dict(color='rgba(0,0,0,0)'),
        name='25-75% Range',
    ))
    
    # Median line
    fig.add_trace(go.Scatter(
        x=x,
        y=p50,
        mode='lines',
        line=dict(color=THEME["gold"], width=2),
        name='Median',
    ))
    
    fig.update_layout(
        title="Monte Carlo Projection (1 Year)",
        xaxis_title="Trading Days",
        yaxis_title="Portfolio Value ($)",
        paper_bgcolor=THEME["bg_secondary"],
        plot_bgcolor=THEME["bg_secondary"],
        font=dict(color=THEME["text_primary"], family="JetBrains Mono, monospace", size=11),
        margin=dict(l=50, r=30, t=40, b=40),
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


def create_monthly_heatmap_figure() -> go.Figure:
    """Create monthly returns heatmap."""
    
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    years = ['2023', '2024']
    
    # Sample monthly returns
    np.random.seed(42)
    returns = np.random.uniform(-5, 8, (len(years), len(months)))
    
    # Custom colorscale
    colorscale = [
        [0, THEME["danger"]],
        [0.5, THEME["bg_tertiary"]],
        [1, THEME["success"]],
    ]
    
    fig = go.Figure(data=go.Heatmap(
        z=returns,
        x=months,
        y=years,
        colorscale=colorscale,
        zmid=0,
        text=[[f"{v:.1f}%" for v in row] for row in returns],
        texttemplate="%{text}",
        textfont={"size": 10, "color": THEME["text_primary"]},
        hoverongaps=False,
    ))
    
    fig.update_layout(
        title="Monthly Returns Heatmap",
        paper_bgcolor=THEME["bg_secondary"],
        plot_bgcolor=THEME["bg_secondary"],
        font=dict(color=THEME["text_primary"], family="JetBrains Mono, monospace", size=11),
        margin=dict(l=50, r=30, t=40, b=40),
    )
    
    return fig


def _create_risk_metrics_panel() -> html.Div:
    """Create risk metrics panel."""
    
    metrics = [
        ("VaR (95%)", "-$1,247", "Daily"),
        ("CVaR (95%)", "-$1,893", "Expected shortfall"),
        ("Beta", "0.23", "vs S&P 500"),
        ("Calmar Ratio", "1.42", "CAGR/MaxDD"),
        ("Profit Factor", "2.31", "Gross P / Gross L"),
        ("Expectancy", "+$47", "Per trade"),
        ("Avg Days Held", "18.4", "Mean duration"),
        ("Recovery Factor", "2.98", "Net P / MaxDD"),
    ]
    
    return html.Div([
        html.Div([
            html.Div([
                html.Span(label, style={
                    "color": THEME["text_secondary"],
                    "fontSize": "12px",
                }),
                html.Span(sublabel, style={
                    "color": THEME["text_muted"],
                    "fontSize": "10px",
                    "marginLeft": "8px",
                }),
            ]),
            html.Span(value, style={
                "color": THEME["gold"] if value.startswith("+") or value.startswith("$") or value[0].isdigit() else THEME["text_primary"],
                "fontSize": "14px",
                "fontWeight": "600",
                "fontFamily": "'JetBrains Mono', monospace",
            }),
        ], style={
            "display": "flex",
            "justifyContent": "space-between",
            "alignItems": "center",
            "padding": "8px 0",
            "borderBottom": f"1px solid {THEME['border']}",
        })
        for label, value, sublabel in metrics
    ])


def _create_trades_table() -> dash_table.DataTable:
    """Create trades table."""
    
    sample_trades = [
        {"date": "2024-12-30", "strategy": "IC", "entry": "$2.45", "exit": "$1.20", "pnl": "+$125", "days": 18, "exit_reason": "Profit Target"},
        {"date": "2024-12-27", "strategy": "IC", "entry": "$2.10", "exit": "$2.80", "pnl": "-$70", "days": 12, "exit_reason": "Stop Loss"},
        {"date": "2024-12-23", "strategy": "IC", "entry": "$1.95", "exit": "$0.85", "pnl": "+$110", "days": 21, "exit_reason": "Profit Target"},
        {"date": "2024-12-18", "strategy": "IC", "entry": "$2.30", "exit": "$1.45", "pnl": "+$85", "days": 15, "exit_reason": "Profit Target"},
        {"date": "2024-12-12", "strategy": "IC", "entry": "$2.15", "exit": "$0.95", "pnl": "+$120", "days": 24, "exit_reason": "Profit Target"},
    ]
    
    return dash_table.DataTable(
        columns=[
            {"name": "Date", "id": "date"},
            {"name": "Type", "id": "strategy"},
            {"name": "Entry", "id": "entry"},
            {"name": "Exit", "id": "exit"},
            {"name": "P/L", "id": "pnl"},
            {"name": "Days", "id": "days"},
            {"name": "Reason", "id": "exit_reason"},
        ],
        data=sample_trades,
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
            "textAlign": "left",
        },
        style_data_conditional=[
            {
                "if": {"filter_query": "{pnl} contains '+'", "column_id": "pnl"},
                "color": THEME["success"],
                "fontWeight": "600",
            },
            {
                "if": {"filter_query": "{pnl} contains '-'", "column_id": "pnl"},
                "color": THEME["danger"],
                "fontWeight": "600",
            },
        ],
        page_size=5,
    )
