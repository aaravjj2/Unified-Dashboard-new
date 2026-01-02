"""
Gamma Exposure (GEX) Bar Chart Component
Phase 6 - Agent-Viz

Displays Dealer Gamma per strike:
- Green bars = Long gamma (dealers)
- Red bars = Short gamma (dealers)

Data source: engines/data/options_chain (read-only)
"""

import logging
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from dash import dcc, html
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)

# Component IDs
GEX_CHART_ID = "chart-gex"

# Alpaca Dark Theme Colors
ALPACA_DARK = {
    "bg": "#1E1E1E",
    "paper": "#252525",
    "accent": "#F5C211",
    "positive": "#00C853",  # Green for long gamma
    "negative": "#FF5252",  # Red for short gamma
    "text": "#E0E0E0",
    "grid": "#333333",
}


def calculate_dealer_gamma(
    options_data: Dict[str, Any],
    spot_price: float,
    num_strikes: int = 20,
) -> pd.DataFrame:
    """
    Calculate dealer gamma exposure per strike.
    
    Dealer gamma = -1 * (market maker gamma)
    When dealers sell options, they are short gamma.
    When they buy (hedge), they are long gamma.
    
    Args:
        options_data: Dict containing 'calls' and 'puts' DataFrames
        spot_price: Current underlying price
        num_strikes: Number of strikes to display around ATM
        
    Returns:
        DataFrame with columns: strike, gamma, color
    """
    calls = options_data.get("calls", pd.DataFrame())
    puts = options_data.get("puts", pd.DataFrame())
    
    if calls.empty and puts.empty:
        logger.warning("No options data available for GEX calculation")
        return pd.DataFrame(columns=["strike", "gamma", "color"])
    
    # Combine calls and puts gamma
    gamma_data = []
    
    # Process calls
    if not calls.empty and "strike" in calls.columns:
        for _, row in calls.iterrows():
            strike = row.get("strike", 0)
            gamma = row.get("gamma", 0) or 0
            oi = row.get("openInterest", row.get("open_interest", 100))
            # Dealer gamma is negative of customer gamma
            # Customers typically buy calls (long gamma)
            # So dealers are short gamma on calls they sold
            dealer_gamma = -gamma * (oi or 100) * 100  # Contract multiplier
            gamma_data.append({"strike": strike, "gamma": dealer_gamma, "type": "call"})
    
    # Process puts
    if not puts.empty and "strike" in puts.columns:
        for _, row in puts.iterrows():
            strike = row.get("strike", 0)
            gamma = row.get("gamma", 0) or 0
            oi = row.get("openInterest", row.get("open_interest", 100))
            # Customers typically buy puts (long gamma)
            # Dealers are short gamma on puts they sold
            dealer_gamma = -gamma * (oi or 100) * 100
            gamma_data.append({"strike": strike, "gamma": dealer_gamma, "type": "put"})
    
    if not gamma_data:
        return pd.DataFrame(columns=["strike", "gamma", "color"])
    
    df = pd.DataFrame(gamma_data)
    
    # Aggregate gamma per strike
    agg_df = df.groupby("strike")["gamma"].sum().reset_index()
    
    # Filter to strikes around ATM
    if spot_price > 0:
        atm_strikes = agg_df[
            (agg_df["strike"] >= spot_price * 0.9) &
            (agg_df["strike"] <= spot_price * 1.1)
        ].copy()
        if len(atm_strikes) >= num_strikes // 2:
            agg_df = atm_strikes
    
    # Limit to num_strikes
    agg_df = agg_df.nlargest(num_strikes, "strike", keep="all").sort_values("strike")
    
    # Assign colors based on gamma sign
    agg_df["color"] = agg_df["gamma"].apply(
        lambda x: ALPACA_DARK["positive"] if x > 0 else ALPACA_DARK["negative"]
    )
    
    return agg_df


def create_gex_figure(
    gamma_df: pd.DataFrame,
    spot_price: float = 0,
    title: str = "Dealer Gamma Exposure (GEX)",
) -> go.Figure:
    """
    Create the GEX bar chart figure.
    
    Args:
        gamma_df: DataFrame with strike, gamma, color columns
        spot_price: Current underlying price for reference line
        title: Chart title
        
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    if gamma_df.empty:
        # Empty state
        fig.add_annotation(
            text="No GEX data available<br>Load options chain to display",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color=ALPACA_DARK["text"]),
        )
    else:
        # Add bar chart
        fig.add_trace(go.Bar(
            x=gamma_df["strike"],
            y=gamma_df["gamma"],
            marker_color=gamma_df["color"],
            name="Dealer Gamma",
            hovertemplate=(
                "<b>Strike:</b> $%{x:.2f}<br>"
                "<b>Gamma:</b> %{y:,.0f}<br>"
                "<extra></extra>"
            ),
        ))
        
        # Add spot price reference line
        if spot_price > 0:
            fig.add_vline(
                x=spot_price,
                line_dash="dash",
                line_color=ALPACA_DARK["accent"],
                line_width=2,
                annotation_text=f"Spot: ${spot_price:.2f}",
                annotation_position="top",
                annotation_font_color=ALPACA_DARK["accent"],
            )
        
        # Add zero line
        fig.add_hline(
            y=0,
            line_color=ALPACA_DARK["grid"],
            line_width=1,
        )
    
    # Apply Alpaca Dark theme
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(color=ALPACA_DARK["text"], size=16),
            x=0.5,
        ),
        paper_bgcolor=ALPACA_DARK["paper"],
        plot_bgcolor=ALPACA_DARK["bg"],
        font=dict(color=ALPACA_DARK["text"]),
        xaxis=dict(
            title="Strike Price",
            gridcolor=ALPACA_DARK["grid"],
            tickformat="$,.0f",
        ),
        yaxis=dict(
            title="Dealer Gamma ($)",
            gridcolor=ALPACA_DARK["grid"],
            tickformat=",",
        ),
        showlegend=False,
        margin=dict(l=60, r=30, t=50, b=50),
        hovermode="x unified",
    )
    
    return fig


def create_gex_chart(
    options_data: Optional[Dict[str, Any]] = None,
    spot_price: float = 0,
    ticker: str = "SPY",
) -> html.Div:
    """
    Create the complete GEX chart component.
    
    Args:
        options_data: Options chain data dict with 'calls' and 'puts'
        spot_price: Current spot price
        ticker: Underlying ticker symbol
        
    Returns:
        Dash HTML Div containing the chart
    """
    # Calculate gamma exposure
    if options_data:
        gamma_df = calculate_dealer_gamma(options_data, spot_price)
    else:
        gamma_df = pd.DataFrame(columns=["strike", "gamma", "color"])
    
    # Create figure
    fig = create_gex_figure(
        gamma_df,
        spot_price=spot_price,
        title=f"Dealer Gamma Exposure (GEX) - {ticker}",
    )
    
    return html.Div(
        id="gex-chart-container",
        children=[
            dcc.Graph(
                id=GEX_CHART_ID,
                figure=fig,
                config={
                    "displayModeBar": True,
                    "displaylogo": False,
                    "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                },
                style={"height": "400px"},
            ),
            html.Div(
                className="gex-legend",
                children=[
                    html.Span(
                        "■ Long Gamma (Dealers)",
                        style={"color": ALPACA_DARK["positive"], "marginRight": "20px"},
                    ),
                    html.Span(
                        "■ Short Gamma (Dealers)",
                        style={"color": ALPACA_DARK["negative"]},
                    ),
                ],
                style={
                    "textAlign": "center",
                    "padding": "10px",
                    "fontSize": "12px",
                },
            ),
        ],
        style={
            "backgroundColor": ALPACA_DARK["paper"],
            "borderRadius": "8px",
            "padding": "10px",
            "marginBottom": "20px",
        },
    )


def generate_mock_gex_data(
    spot_price: float = 450.0,
    num_strikes: int = 15,
) -> Dict[str, Any]:
    """
    Generate mock GEX data for testing/demo.
    
    Args:
        spot_price: Mock spot price
        num_strikes: Number of strikes to generate
        
    Returns:
        Mock options data dict
    """
    np.random.seed(42)  # VIZ_DETERMINISTIC
    
    strikes = np.linspace(spot_price * 0.92, spot_price * 1.08, num_strikes)
    
    calls_data = []
    puts_data = []
    
    for strike in strikes:
        moneyness = (strike - spot_price) / spot_price
        
        # Gamma peaks at ATM, decays with distance
        atm_factor = np.exp(-50 * moneyness**2)
        base_gamma = 0.05 * atm_factor
        
        # Calls
        calls_data.append({
            "strike": strike,
            "gamma": base_gamma * (1 + np.random.uniform(-0.2, 0.2)),
            "openInterest": int(1000 + np.random.exponential(2000)),
        })
        
        # Puts
        puts_data.append({
            "strike": strike,
            "gamma": base_gamma * (1 + np.random.uniform(-0.2, 0.2)),
            "openInterest": int(800 + np.random.exponential(1500)),
        })
    
    return {
        "ticker": "SPY",
        "spot_price": spot_price,
        "calls": pd.DataFrame(calls_data),
        "puts": pd.DataFrame(puts_data),
    }


if __name__ == "__main__":
    # Test the component
    mock_data = generate_mock_gex_data()
    gamma_df = calculate_dealer_gamma(mock_data, mock_data["spot_price"])
    print(f"Generated {len(gamma_df)} strikes of GEX data")
    print(gamma_df.head(10))
