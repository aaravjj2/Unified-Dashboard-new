"""
Alpaca Options Lab - Reusable Chart Components

Production-grade chart library for options trading visualization:
- Greeks heatmaps and surfaces
- P&L attribution charts
- Risk visualization
- Options payoff diagrams
- Volatility surfaces

Usage:
    from src.ui.visualization.charts import (
        create_greeks_heatmap,
        create_pnl_attribution,
        create_options_payoff,
        create_volatility_surface,
    )
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

import numpy as np

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# =============================================================================
# STYLE CONSTANTS
# =============================================================================

class ChartTheme(Enum):
    """Chart color themes."""
    DARK = "dark"
    LIGHT = "light"
    PROFESSIONAL = "professional"


THEMES = {
    ChartTheme.DARK: {
        "background": "#1a1a2e",
        "paper": "#16213e",
        "text": "#e8e8e8",
        "grid": "#2a2a4a",
        "positive": "#2ecc71",
        "negative": "#e74c3c",
        "neutral": "#95a5a6",
        "primary": "#3498db",
        "secondary": "#9b59b6",
        "accent": "#f39c12",
    },
    ChartTheme.LIGHT: {
        "background": "#ffffff",
        "paper": "#f5f5f5",
        "text": "#2c3e50",
        "grid": "#e0e0e0",
        "positive": "#27ae60",
        "negative": "#c0392b",
        "neutral": "#7f8c8d",
        "primary": "#2980b9",
        "secondary": "#8e44ad",
        "accent": "#d35400",
    },
    ChartTheme.PROFESSIONAL: {
        "background": "#0a0a0f",
        "paper": "#12121a",
        "text": "#d4d4d4",
        "grid": "#1a1a25",
        "positive": "#00c853",
        "negative": "#ff1744",
        "neutral": "#546e7a",
        "primary": "#2196f3",
        "secondary": "#7c4dff",
        "accent": "#ff9100",
    },
}

DEFAULT_THEME = ChartTheme.PROFESSIONAL


def get_theme(theme: ChartTheme = DEFAULT_THEME) -> Dict[str, str]:
    """Get color theme."""
    return THEMES.get(theme, THEMES[DEFAULT_THEME])


def apply_theme(fig: "go.Figure", theme: ChartTheme = DEFAULT_THEME) -> "go.Figure":
    """Apply theme to figure."""
    colors = get_theme(theme)
    
    fig.update_layout(
        paper_bgcolor=colors["paper"],
        plot_bgcolor=colors["background"],
        font=dict(color=colors["text"]),
        xaxis=dict(
            gridcolor=colors["grid"],
            zerolinecolor=colors["grid"],
        ),
        yaxis=dict(
            gridcolor=colors["grid"],
            zerolinecolor=colors["grid"],
        ),
    )
    
    return fig


# =============================================================================
# GREEKS CHARTS
# =============================================================================

def create_greeks_heatmap(
    strikes: List[float],
    expirations: List[datetime],
    values: List[List[float]],
    greek: str = "delta",
    title: Optional[str] = None,
    theme: ChartTheme = DEFAULT_THEME,
) -> "go.Figure":
    """
    Create Greeks heatmap across strikes and expirations.
    
    Args:
        strikes: List of strike prices
        expirations: List of expiration dates
        values: 2D array of Greek values [exp][strike]
        greek: Greek name for labeling
        title: Chart title
        theme: Color theme
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    colors = get_theme(theme)
    title = title or f"{greek.title()} Heatmap"
    
    # Format expiration labels
    exp_labels = [e.strftime("%Y-%m-%d") if hasattr(e, 'strftime') else str(e) 
                  for e in expirations]
    
    # Colorscale based on Greek type
    if greek.lower() in ("delta", "gamma"):
        colorscale = [
            [0, colors["negative"]],
            [0.5, colors["neutral"]],
            [1, colors["positive"]],
        ]
    elif greek.lower() == "theta":
        colorscale = [
            [0, colors["negative"]],
            [1, colors["neutral"]],
        ]
    else:
        colorscale = "Viridis"
    
    fig = go.Figure(data=go.Heatmap(
        z=values,
        x=strikes,
        y=exp_labels,
        colorscale=colorscale,
        text=[[f"{v:.4f}" for v in row] for row in values],
        texttemplate="%{text}",
        textfont={"size": 9},
        hoverongaps=False,
        colorbar=dict(title=greek.title()),
    ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Strike",
        yaxis_title="Expiration",
        height=400,
    )
    
    return apply_theme(fig, theme)


def create_greeks_surface(
    strikes: List[float],
    expirations: List[float],  # Days to expiry
    values: List[List[float]],
    greek: str = "delta",
    title: Optional[str] = None,
    theme: ChartTheme = DEFAULT_THEME,
) -> "go.Figure":
    """
    Create 3D Greeks surface.
    
    Args:
        strikes: List of strike prices
        expirations: Days to expiration
        values: 2D array of Greek values
        greek: Greek name
        title: Chart title
        theme: Color theme
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    colors = get_theme(theme)
    title = title or f"{greek.title()} Surface"
    
    fig = go.Figure(data=[go.Surface(
        x=strikes,
        y=expirations,
        z=values,
        colorscale="Viridis",
        colorbar=dict(title=greek.title()),
    )])
    
    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title="Strike",
            yaxis_title="DTE",
            zaxis_title=greek.title(),
            bgcolor=colors["background"],
        ),
        height=500,
    )
    
    return apply_theme(fig, theme)


# =============================================================================
# P&L ATTRIBUTION CHARTS
# =============================================================================

def create_pnl_attribution(
    components: Dict[str, float],
    title: str = "P&L Attribution",
    theme: ChartTheme = DEFAULT_THEME,
) -> "go.Figure":
    """
    Create P&L attribution waterfall chart.
    
    Args:
        components: Dict of P&L components (e.g., {"delta": 100, "theta": -20})
        title: Chart title
        theme: Color theme
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    colors = get_theme(theme)
    
    labels = list(components.keys()) + ["Total"]
    values = list(components.values())
    total = sum(values)
    
    # Determine colors
    bar_colors = []
    for v in values:
        if v >= 0:
            bar_colors.append(colors["positive"])
        else:
            bar_colors.append(colors["negative"])
    bar_colors.append(colors["primary"] if total >= 0 else colors["secondary"])
    
    # Waterfall measure types
    measures = ["relative"] * len(values) + ["total"]
    
    fig = go.Figure(go.Waterfall(
        name="P&L",
        orientation="v",
        measure=measures,
        x=labels,
        y=values + [total],
        text=[f"${v:,.0f}" for v in values] + [f"${total:,.0f}"],
        textposition="outside",
        connector={"line": {"color": colors["grid"]}},
        increasing={"marker": {"color": colors["positive"]}},
        decreasing={"marker": {"color": colors["negative"]}},
        totals={"marker": {"color": colors["primary"]}},
    ))
    
    fig.update_layout(
        title=title,
        yaxis_title="P&L ($)",
        showlegend=False,
    )
    
    return apply_theme(fig, theme)


def create_pnl_decomposition(
    timestamps: List[datetime],
    delta_pnl: List[float],
    gamma_pnl: List[float],
    theta_pnl: List[float],
    vega_pnl: List[float],
    other_pnl: Optional[List[float]] = None,
    title: str = "P&L Decomposition Over Time",
    theme: ChartTheme = DEFAULT_THEME,
) -> "go.Figure":
    """
    Create stacked area chart showing P&L decomposition over time.
    
    Args:
        timestamps: Time series
        delta_pnl: Delta P&L
        gamma_pnl: Gamma P&L
        theta_pnl: Theta P&L
        vega_pnl: Vega P&L
        other_pnl: Other P&L
        title: Chart title
        theme: Color theme
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    colors = get_theme(theme)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=timestamps, y=delta_pnl,
        mode="lines", name="Delta P&L",
        stackgroup="one",
        line=dict(color=colors["primary"]),
        fillcolor=f"rgba(33, 150, 243, 0.3)",
    ))
    
    fig.add_trace(go.Scatter(
        x=timestamps, y=gamma_pnl,
        mode="lines", name="Gamma P&L",
        stackgroup="one",
        line=dict(color=colors["positive"]),
        fillcolor=f"rgba(0, 200, 83, 0.3)",
    ))
    
    fig.add_trace(go.Scatter(
        x=timestamps, y=theta_pnl,
        mode="lines", name="Theta P&L",
        stackgroup="one",
        line=dict(color=colors["accent"]),
        fillcolor=f"rgba(255, 145, 0, 0.3)",
    ))
    
    fig.add_trace(go.Scatter(
        x=timestamps, y=vega_pnl,
        mode="lines", name="Vega P&L",
        stackgroup="one",
        line=dict(color=colors["secondary"]),
        fillcolor=f"rgba(124, 77, 255, 0.3)",
    ))
    
    if other_pnl:
        fig.add_trace(go.Scatter(
            x=timestamps, y=other_pnl,
            mode="lines", name="Other P&L",
            stackgroup="one",
            line=dict(color=colors["neutral"]),
        ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Date",
        yaxis_title="P&L ($)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )
    
    return apply_theme(fig, theme)


# =============================================================================
# RISK VISUALIZATION
# =============================================================================

def create_risk_chart(
    categories: List[str],
    current_values: List[float],
    limit_values: List[float],
    title: str = "Risk Utilization",
    theme: ChartTheme = DEFAULT_THEME,
) -> "go.Figure":
    """
    Create risk limit utilization chart.
    
    Args:
        categories: Risk category names
        current_values: Current utilization values
        limit_values: Maximum limit values
        title: Chart title
        theme: Color theme
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    colors = get_theme(theme)
    
    # Calculate utilization percentages
    utilizations = [c / l * 100 if l > 0 else 0 
                   for c, l in zip(current_values, limit_values)]
    
    # Color based on utilization
    bar_colors = []
    for util in utilizations:
        if util < 50:
            bar_colors.append(colors["positive"])
        elif util < 80:
            bar_colors.append(colors["accent"])
        else:
            bar_colors.append(colors["negative"])
    
    fig = go.Figure()
    
    # Current values
    fig.add_trace(go.Bar(
        x=categories,
        y=utilizations,
        name="Current",
        marker_color=bar_colors,
        text=[f"{u:.1f}%" for u in utilizations],
        textposition="outside",
    ))
    
    # Limit line at 100%
    fig.add_hline(
        y=100,
        line_dash="dash",
        line_color=colors["negative"],
        annotation_text="Limit",
        annotation_position="right",
    )
    
    # Warning line at 80%
    fig.add_hline(
        y=80,
        line_dash="dot",
        line_color=colors["accent"],
        opacity=0.5,
    )
    
    fig.update_layout(
        title=title,
        yaxis_title="Utilization (%)",
        showlegend=False,
        yaxis=dict(range=[0, max(120, max(utilizations) * 1.1)]),
    )
    
    return apply_theme(fig, theme)


def create_var_chart(
    portfolio_values: List[float],
    var_95: float,
    var_99: float,
    title: str = "Value at Risk Distribution",
    theme: ChartTheme = DEFAULT_THEME,
) -> "go.Figure":
    """
    Create VaR distribution chart.
    
    Args:
        portfolio_values: Historical portfolio values or simulated returns
        var_95: 95% VaR value
        var_99: 99% VaR value
        title: Chart title
        theme: Color theme
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    colors = get_theme(theme)
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=portfolio_values,
        nbinsx=50,
        name="Returns",
        marker_color=colors["primary"],
        opacity=0.7,
    ))
    
    # VaR lines
    fig.add_vline(
        x=var_95,
        line_dash="dash",
        line_color=colors["accent"],
        annotation_text=f"VaR 95%: ${var_95:,.0f}",
        annotation_position="top left",
    )
    
    fig.add_vline(
        x=var_99,
        line_dash="dash",
        line_color=colors["negative"],
        annotation_text=f"VaR 99%: ${var_99:,.0f}",
        annotation_position="top left",
    )
    
    fig.update_layout(
        title=title,
        xaxis_title="P&L ($)",
        yaxis_title="Frequency",
    )
    
    return apply_theme(fig, theme)


# =============================================================================
# OPTIONS PAYOFF DIAGRAMS
# =============================================================================

@dataclass
class OptionLeg:
    """Option leg for payoff calculation."""
    strike: float
    premium: float
    is_call: bool
    is_long: bool
    quantity: int = 1


def create_options_payoff(
    legs: List[OptionLeg],
    underlying_range: Optional[Tuple[float, float]] = None,
    current_price: Optional[float] = None,
    title: str = "Options Payoff Diagram",
    theme: ChartTheme = DEFAULT_THEME,
) -> "go.Figure":
    """
    Create options strategy payoff diagram.
    
    Args:
        legs: List of option legs
        underlying_range: (min, max) underlying price range
        current_price: Current underlying price (for reference line)
        title: Chart title
        theme: Color theme
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    colors = get_theme(theme)
    
    # Determine price range
    if underlying_range:
        min_price, max_price = underlying_range
    else:
        strikes = [leg.strike for leg in legs]
        strike_range = max(strikes) - min(strikes) if len(strikes) > 1 else strikes[0] * 0.2
        min_price = min(strikes) - strike_range * 0.5
        max_price = max(strikes) + strike_range * 0.5
    
    # Generate underlying prices
    prices = np.linspace(min_price, max_price, 200)
    
    # Calculate payoff for each leg
    total_payoff = np.zeros_like(prices)
    total_premium = 0.0
    
    for leg in legs:
        direction = 1 if leg.is_long else -1
        
        if leg.is_call:
            intrinsic = np.maximum(prices - leg.strike, 0)
        else:
            intrinsic = np.maximum(leg.strike - prices, 0)
        
        payoff = direction * leg.quantity * (intrinsic - leg.premium)
        total_payoff += payoff
        total_premium += direction * leg.quantity * leg.premium
    
    fig = go.Figure()
    
    # Total payoff
    fig.add_trace(go.Scatter(
        x=prices,
        y=total_payoff,
        mode="lines",
        name="Payoff at Expiry",
        line=dict(color=colors["primary"], width=2),
    ))
    
    # Profit/Loss regions
    fig.add_trace(go.Scatter(
        x=prices,
        y=np.where(total_payoff >= 0, total_payoff, 0),
        fill="tozeroy",
        fillcolor=f"rgba(0, 200, 83, 0.2)",
        line=dict(width=0),
        showlegend=False,
    ))
    
    fig.add_trace(go.Scatter(
        x=prices,
        y=np.where(total_payoff < 0, total_payoff, 0),
        fill="tozeroy",
        fillcolor=f"rgba(255, 23, 68, 0.2)",
        line=dict(width=0),
        showlegend=False,
    ))
    
    # Break-even line
    fig.add_hline(y=0, line_dash="dash", line_color=colors["neutral"])
    
    # Current price reference
    if current_price:
        fig.add_vline(
            x=current_price,
            line_dash="dot",
            line_color=colors["accent"],
            annotation_text=f"Current: ${current_price:.2f}",
            annotation_position="top",
        )
    
    # Strike markers
    for leg in legs:
        fig.add_vline(
            x=leg.strike,
            line_dash="dot",
            line_color=colors["grid"],
            opacity=0.5,
        )
    
    # Calculate key metrics
    max_profit = np.max(total_payoff)
    max_loss = np.min(total_payoff)
    
    fig.update_layout(
        title=f"{title}<br><sup>Max Profit: ${max_profit:,.0f} | Max Loss: ${max_loss:,.0f}</sup>",
        xaxis_title="Underlying Price ($)",
        yaxis_title="Profit/Loss ($)",
        hovermode="x unified",
    )
    
    return apply_theme(fig, theme)


def create_strategy_comparison(
    strategies: Dict[str, List[OptionLeg]],
    underlying_range: Tuple[float, float],
    title: str = "Strategy Comparison",
    theme: ChartTheme = DEFAULT_THEME,
) -> "go.Figure":
    """
    Compare multiple options strategies.
    
    Args:
        strategies: Dict mapping strategy name to list of legs
        underlying_range: (min, max) price range
        title: Chart title
        theme: Color theme
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    colors = get_theme(theme)
    color_list = [colors["primary"], colors["secondary"], colors["positive"], 
                  colors["accent"], colors["negative"]]
    
    prices = np.linspace(underlying_range[0], underlying_range[1], 200)
    
    fig = go.Figure()
    
    for idx, (name, legs) in enumerate(strategies.items()):
        total_payoff = np.zeros_like(prices)
        
        for leg in legs:
            direction = 1 if leg.is_long else -1
            
            if leg.is_call:
                intrinsic = np.maximum(prices - leg.strike, 0)
            else:
                intrinsic = np.maximum(leg.strike - prices, 0)
            
            payoff = direction * leg.quantity * (intrinsic - leg.premium)
            total_payoff += payoff
        
        fig.add_trace(go.Scatter(
            x=prices,
            y=total_payoff,
            mode="lines",
            name=name,
            line=dict(color=color_list[idx % len(color_list)], width=2),
        ))
    
    fig.add_hline(y=0, line_dash="dash", line_color=colors["neutral"])
    
    fig.update_layout(
        title=title,
        xaxis_title="Underlying Price ($)",
        yaxis_title="Profit/Loss ($)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )
    
    return apply_theme(fig, theme)


# =============================================================================
# VOLATILITY SURFACE
# =============================================================================

def create_volatility_surface(
    strikes: List[float],
    expirations: List[float],  # Days to expiry
    iv_values: List[List[float]],
    title: str = "Implied Volatility Surface",
    theme: ChartTheme = DEFAULT_THEME,
) -> "go.Figure":
    """
    Create 3D implied volatility surface.
    
    Args:
        strikes: List of strikes
        expirations: Days to expiration
        iv_values: 2D array of IV values [exp][strike]
        title: Chart title
        theme: Color theme
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    colors = get_theme(theme)
    
    fig = go.Figure(data=[go.Surface(
        x=strikes,
        y=expirations,
        z=[[v * 100 for v in row] for row in iv_values],  # Convert to percentage
        colorscale="Viridis",
        colorbar=dict(title="IV (%)"),
    )])
    
    fig.update_layout(
        title=title,
        scene=dict(
            xaxis_title="Strike ($)",
            yaxis_title="DTE (days)",
            zaxis_title="IV (%)",
            bgcolor=colors["background"],
            xaxis=dict(
                gridcolor=colors["grid"],
                backgroundcolor=colors["background"],
            ),
            yaxis=dict(
                gridcolor=colors["grid"],
                backgroundcolor=colors["background"],
            ),
            zaxis=dict(
                gridcolor=colors["grid"],
                backgroundcolor=colors["background"],
            ),
        ),
        height=600,
    )
    
    return apply_theme(fig, theme)


def create_volatility_smile(
    strikes: List[float],
    iv_values: List[float],
    atm_strike: Optional[float] = None,
    title: str = "Volatility Smile",
    theme: ChartTheme = DEFAULT_THEME,
) -> "go.Figure":
    """
    Create 2D volatility smile chart.
    
    Args:
        strikes: List of strikes
        iv_values: IV values for each strike
        atm_strike: ATM strike for reference
        title: Chart title
        theme: Color theme
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    colors = get_theme(theme)
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=strikes,
        y=[v * 100 for v in iv_values],  # Percentage
        mode="lines+markers",
        name="IV",
        line=dict(color=colors["primary"], width=2),
        marker=dict(size=6),
    ))
    
    if atm_strike:
        fig.add_vline(
            x=atm_strike,
            line_dash="dot",
            line_color=colors["accent"],
            annotation_text="ATM",
            annotation_position="top",
        )
    
    fig.update_layout(
        title=title,
        xaxis_title="Strike ($)",
        yaxis_title="Implied Volatility (%)",
    )
    
    return apply_theme(fig, theme)


# =============================================================================
# POSITION CHARTS
# =============================================================================

def create_position_treemap(
    positions: List[Dict[str, Any]],
    value_field: str = "market_value",
    title: str = "Position Allocation",
    theme: ChartTheme = DEFAULT_THEME,
) -> "go.Figure":
    """
    Create position treemap visualization.
    
    Args:
        positions: List of position dicts with symbol, value, etc.
        value_field: Field to use for sizing
        title: Chart title
        theme: Color theme
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    colors = get_theme(theme)
    
    labels = []
    parents = []
    values = []
    marker_colors = []
    
    # Root
    labels.append("Portfolio")
    parents.append("")
    values.append(0)  # Will be calculated
    marker_colors.append(colors["primary"])
    
    for pos in positions:
        symbol = pos.get("symbol", "Unknown")
        value = abs(pos.get(value_field, 0))
        pnl = pos.get("unrealized_pnl", 0)
        
        labels.append(symbol)
        parents.append("Portfolio")
        values.append(value)
        
        if pnl > 0:
            marker_colors.append(colors["positive"])
        elif pnl < 0:
            marker_colors.append(colors["negative"])
        else:
            marker_colors.append(colors["neutral"])
    
    fig = go.Figure(go.Treemap(
        labels=labels,
        parents=parents,
        values=values,
        marker=dict(colors=marker_colors),
        textinfo="label+value+percent root",
        hovertemplate="<b>%{label}</b><br>Value: $%{value:,.0f}<br>%{percentRoot:.1%} of portfolio<extra></extra>",
    ))
    
    fig.update_layout(
        title=title,
    )
    
    return apply_theme(fig, theme)


# =============================================================================
# MULTI-PANEL DASHBOARDS
# =============================================================================

def create_greeks_dashboard(
    positions: List[Dict[str, Any]],
    portfolio_greeks: Dict[str, float],
    theme: ChartTheme = DEFAULT_THEME,
) -> "go.Figure":
    """
    Create multi-panel Greeks dashboard.
    
    Args:
        positions: List of position dicts with Greeks
        portfolio_greeks: Aggregated portfolio Greeks
        theme: Color theme
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        raise ImportError("plotly is required for charting")
    
    colors = get_theme(theme)
    
    fig = make_subplots(
        rows=2,
        cols=2,
        subplot_titles=("Delta by Position", "Gamma by Position", "Theta by Position", "Vega by Position"),
        specs=[
            [{"type": "bar"}, {"type": "bar"}],
            [{"type": "bar"}, {"type": "bar"}],
        ],
    )
    
    symbols = [p.get("symbol", "?") for p in positions]
    
    # Delta
    deltas = [p.get("delta", 0) for p in positions]
    fig.add_trace(
        go.Bar(
            x=symbols, y=deltas, name="Delta",
            marker_color=[colors["positive"] if d >= 0 else colors["negative"] for d in deltas],
        ),
        row=1, col=1,
    )
    
    # Gamma
    gammas = [p.get("gamma", 0) for p in positions]
    fig.add_trace(
        go.Bar(
            x=symbols, y=gammas, name="Gamma",
            marker_color=colors["secondary"],
        ),
        row=1, col=2,
    )
    
    # Theta
    thetas = [p.get("theta", 0) for p in positions]
    fig.add_trace(
        go.Bar(
            x=symbols, y=thetas, name="Theta",
            marker_color=[colors["negative"] if t < 0 else colors["positive"] for t in thetas],
        ),
        row=2, col=1,
    )
    
    # Vega
    vegas = [p.get("vega", 0) for p in positions]
    fig.add_trace(
        go.Bar(
            x=symbols, y=vegas, name="Vega",
            marker_color=colors["accent"],
        ),
        row=2, col=2,
    )
    
    fig.update_layout(
        height=600,
        showlegend=False,
        title=f"Greeks Dashboard | Δ: {portfolio_greeks.get('delta', 0):.2f} | Γ: {portfolio_greeks.get('gamma', 0):.4f} | Θ: {portfolio_greeks.get('theta', 0):.2f} | V: {portfolio_greeks.get('vega', 0):.2f}",
    )
    
    return apply_theme(fig, theme)
