"""
Volatility Surface 3D Mesh & Skew Chart Component
Phase 6 - Agent-Viz

Displays:
1. 3D Mesh: Strike vs Expiry vs Implied Volatility
2. 2D Skew: Strike vs IV for selected expiry

Data source: engines/data/options_chain (read-only)
"""

import logging
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import dcc, html
from typing import Dict, Optional, List, Any, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Component IDs
VOL_SURFACE_ID = "chart-vol-3d"
VOL_SKEW_ID = "chart-vol-skew"

# Alpaca Dark Theme Colors
ALPACA_DARK = {
    "bg": "#1E1E1E",
    "paper": "#252525",
    "accent": "#F5C211",
    "positive": "#00C853",
    "negative": "#FF5252",
    "text": "#E0E0E0",
    "grid": "#333333",
    "surface_low": "#1565C0",   # Blue for low IV
    "surface_high": "#FF5722",  # Orange for high IV
}


def extract_iv_surface_data(
    options_data: Dict[str, Any],
    spot_price: float,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Extract IV surface data from options chain.
    
    Args:
        options_data: Dict with 'calls' and 'puts' DataFrames
        spot_price: Current underlying price
        
    Returns:
        Tuple of (strikes, expiries_days, iv_matrix)
    """
    calls = options_data.get("calls", pd.DataFrame())
    puts = options_data.get("puts", pd.DataFrame())
    
    # Combine calls and puts
    all_options = pd.concat([calls, puts], ignore_index=True)
    
    if all_options.empty:
        return np.array([]), np.array([]), np.array([[]])
    
    # Get unique strikes and expiries
    strike_col = "strike" if "strike" in all_options.columns else None
    iv_col = None
    for col in ["impliedVolatility", "implied_volatility", "iv", "IV"]:
        if col in all_options.columns:
            iv_col = col
            break
    
    expiry_col = None
    for col in ["expiration", "expiry", "expirationDate"]:
        if col in all_options.columns:
            expiry_col = col
            break
    
    if strike_col is None or iv_col is None:
        logger.warning("Missing required columns for IV surface")
        return np.array([]), np.array([]), np.array([[]])
    
    # Filter valid data
    valid_data = all_options[
        (all_options[strike_col] > 0) &
        (all_options[iv_col] > 0) &
        (all_options[iv_col] < 5)  # Filter out unrealistic IVs
    ].copy()
    
    if valid_data.empty:
        return np.array([]), np.array([]), np.array([[]])
    
    # Get unique strikes (filter around ATM)
    strikes = valid_data[strike_col].unique()
    strikes = strikes[(strikes >= spot_price * 0.85) & (strikes <= spot_price * 1.15)]
    strikes = np.sort(strikes)
    
    # If expiry column exists, use it; otherwise create synthetic
    if expiry_col and expiry_col in valid_data.columns:
        expiries = valid_data[expiry_col].unique()
        # Convert to days to expiry
        today = datetime.now()
        expiry_days = []
        for exp in expiries:
            try:
                if isinstance(exp, str):
                    exp_date = datetime.strptime(exp[:10], "%Y-%m-%d")
                else:
                    exp_date = pd.to_datetime(exp)
                days = (exp_date - today).days
                if days > 0:
                    expiry_days.append(days)
            except Exception:
                continue
        expiry_days = np.array(sorted(set(expiry_days)))
    else:
        # Generate synthetic expiries
        expiry_days = np.array([7, 14, 30, 45, 60, 90, 180])
    
    if len(strikes) < 3 or len(expiry_days) < 2:
        return np.array([]), np.array([]), np.array([[]])
    
    # Build IV matrix
    iv_matrix = np.zeros((len(expiry_days), len(strikes)))
    
    for i, days in enumerate(expiry_days):
        for j, strike in enumerate(strikes):
            # Find matching options
            mask = (valid_data[strike_col] == strike)
            if expiry_col:
                # Try to match expiry
                for exp in valid_data[expiry_col].unique():
                    try:
                        if isinstance(exp, str):
                            exp_date = datetime.strptime(exp[:10], "%Y-%m-%d")
                        else:
                            exp_date = pd.to_datetime(exp)
                        exp_days = (exp_date - today).days
                        if abs(exp_days - days) <= 3:
                            exp_mask = mask & (valid_data[expiry_col] == exp)
                            if exp_mask.any():
                                iv_matrix[i, j] = valid_data.loc[exp_mask, iv_col].mean()
                                break
                    except Exception:
                        continue
            else:
                # Use average IV at strike
                if mask.any():
                    iv_matrix[i, j] = valid_data.loc[mask, iv_col].mean()
    
    # Fill zeros with interpolation
    if np.any(iv_matrix == 0):
        from scipy import interpolate
        try:
            # Simple filling
            for i in range(iv_matrix.shape[0]):
                row = iv_matrix[i, :]
                if np.any(row > 0):
                    valid_idx = np.where(row > 0)[0]
                    if len(valid_idx) > 1:
                        f = interpolate.interp1d(
                            strikes[valid_idx], row[valid_idx],
                            kind="linear", fill_value="extrapolate"
                        )
                        iv_matrix[i, :] = f(strikes)
        except Exception:
            pass
    
    return strikes, expiry_days, iv_matrix


def create_vol_surface_figure(
    strikes: np.ndarray,
    expiry_days: np.ndarray,
    iv_matrix: np.ndarray,
    spot_price: float = 0,
    title: str = "Implied Volatility Surface",
) -> go.Figure:
    """
    Create the 3D volatility surface figure.
    
    Args:
        strikes: Array of strike prices
        expiry_days: Array of days to expiry
        iv_matrix: 2D array of IV values [expiry x strike]
        spot_price: Current spot price for reference
        title: Chart title
        
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    if len(strikes) == 0 or len(expiry_days) == 0 or iv_matrix.size == 0:
        # Empty state
        fig.add_annotation(
            text="No IV surface data available<br>Load options chain to display",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color=ALPACA_DARK["text"]),
        )
    else:
        # Create meshgrid
        X, Y = np.meshgrid(strikes, expiry_days)
        Z = iv_matrix * 100  # Convert to percentage
        
        # Add surface
        fig.add_trace(go.Surface(
            x=X,
            y=Y,
            z=Z,
            colorscale=[
                [0, ALPACA_DARK["surface_low"]],
                [0.5, ALPACA_DARK["accent"]],
                [1, ALPACA_DARK["surface_high"]],
            ],
            colorbar=dict(
                title=dict(text="IV (%)", font=dict(color=ALPACA_DARK["text"])),
                ticksuffix="%",
                tickfont=dict(color=ALPACA_DARK["text"]),
            ),
            hovertemplate=(
                "<b>Strike:</b> $%{x:.2f}<br>"
                "<b>DTE:</b> %{y}d<br>"
                "<b>IV:</b> %{z:.1f}%<br>"
                "<extra></extra>"
            ),
        ))
        
        # Add ATM reference plane if spot price available
        if spot_price > 0 and spot_price >= strikes.min() and spot_price <= strikes.max():
            fig.add_trace(go.Scatter3d(
                x=[spot_price] * len(expiry_days),
                y=expiry_days,
                z=Z[:, np.abs(strikes - spot_price).argmin()],
                mode="lines",
                line=dict(color=ALPACA_DARK["accent"], width=4),
                name="ATM",
            ))
    
    # Apply Alpaca Dark theme for 3D
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(color=ALPACA_DARK["text"], size=16),
            x=0.5,
        ),
        paper_bgcolor=ALPACA_DARK["paper"],
        scene=dict(
            xaxis=dict(
                title=dict(text="Strike ($)", font=dict(color=ALPACA_DARK["text"])),
                backgroundcolor=ALPACA_DARK["bg"],
                gridcolor=ALPACA_DARK["grid"],
                tickfont=dict(color=ALPACA_DARK["text"]),
            ),
            yaxis=dict(
                title=dict(text="Days to Expiry", font=dict(color=ALPACA_DARK["text"])),
                backgroundcolor=ALPACA_DARK["bg"],
                gridcolor=ALPACA_DARK["grid"],
                tickfont=dict(color=ALPACA_DARK["text"]),
            ),
            zaxis=dict(
                title=dict(text="IV (%)", font=dict(color=ALPACA_DARK["text"])),
                backgroundcolor=ALPACA_DARK["bg"],
                gridcolor=ALPACA_DARK["grid"],
                tickfont=dict(color=ALPACA_DARK["text"]),
            ),
            bgcolor=ALPACA_DARK["bg"],
        ),
        margin=dict(l=10, r=10, t=50, b=10),
    )
    
    return fig


def create_skew_figure(
    strikes: np.ndarray,
    iv_values: np.ndarray,
    spot_price: float = 0,
    expiry_label: str = "30 DTE",
) -> go.Figure:
    """
    Create the 2D volatility skew figure.
    
    Args:
        strikes: Array of strike prices
        iv_values: Array of IV values for the selected expiry
        spot_price: Current spot price
        expiry_label: Label for the selected expiry
        
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    if len(strikes) == 0 or len(iv_values) == 0:
        fig.add_annotation(
            text="No skew data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=14, color=ALPACA_DARK["text"]),
        )
    else:
        # Add skew line
        fig.add_trace(go.Scatter(
            x=strikes,
            y=iv_values * 100,
            mode="lines+markers",
            line=dict(color=ALPACA_DARK["accent"], width=2),
            marker=dict(size=6, color=ALPACA_DARK["accent"]),
            name="IV Skew",
            hovertemplate=(
                "<b>Strike:</b> $%{x:.2f}<br>"
                "<b>IV:</b> %{y:.1f}%<br>"
                "<extra></extra>"
            ),
        ))
        
        # Add ATM reference
        if spot_price > 0:
            fig.add_vline(
                x=spot_price,
                line_dash="dash",
                line_color=ALPACA_DARK["positive"],
                line_width=2,
                annotation_text="ATM",
                annotation_position="top",
                annotation_font_color=ALPACA_DARK["positive"],
            )
    
    fig.update_layout(
        title=dict(
            text=f"IV Skew - {expiry_label}",
            font=dict(color=ALPACA_DARK["text"], size=14),
            x=0.5,
        ),
        paper_bgcolor=ALPACA_DARK["paper"],
        plot_bgcolor=ALPACA_DARK["bg"],
        font=dict(color=ALPACA_DARK["text"]),
        xaxis=dict(
            title="Strike ($)",
            gridcolor=ALPACA_DARK["grid"],
            tickformat="$,.0f",
        ),
        yaxis=dict(
            title="Implied Volatility (%)",
            gridcolor=ALPACA_DARK["grid"],
            ticksuffix="%",
        ),
        showlegend=False,
        margin=dict(l=60, r=30, t=40, b=50),
        hovermode="x unified",
    )
    
    return fig


def create_vol_surface(
    options_data: Optional[Dict[str, Any]] = None,
    spot_price: float = 0,
    ticker: str = "SPY",
    selected_expiry_idx: int = 2,  # Default to ~30 DTE
) -> html.Div:
    """
    Create the complete volatility surface component.
    
    Args:
        options_data: Options chain data dict
        spot_price: Current spot price
        ticker: Underlying ticker symbol
        selected_expiry_idx: Index of expiry to show in skew chart
        
    Returns:
        Dash HTML Div containing both charts
    """
    # Extract surface data
    if options_data:
        strikes, expiry_days, iv_matrix = extract_iv_surface_data(options_data, spot_price)
    else:
        strikes, expiry_days, iv_matrix = np.array([]), np.array([]), np.array([[]])
    
    # Create 3D surface figure
    surface_fig = create_vol_surface_figure(
        strikes, expiry_days, iv_matrix,
        spot_price=spot_price,
        title=f"IV Surface - {ticker}",
    )
    
    # Create 2D skew figure (for selected expiry)
    if len(iv_matrix) > 0 and len(expiry_days) > selected_expiry_idx:
        skew_iv = iv_matrix[selected_expiry_idx, :]
        expiry_label = f"{int(expiry_days[selected_expiry_idx])} DTE"
    else:
        skew_iv = np.array([])
        expiry_label = "N/A"
    
    skew_fig = create_skew_figure(
        strikes, skew_iv,
        spot_price=spot_price,
        expiry_label=expiry_label,
    )
    
    return html.Div(
        id="vol-surface-container",
        children=[
            # 3D Surface
            html.Div(
                children=[
                    dcc.Graph(
                        id=VOL_SURFACE_ID,
                        figure=surface_fig,
                        config={
                            "displayModeBar": True,
                            "displaylogo": False,
                        },
                        style={"height": "450px"},
                    ),
                ],
                style={
                    "backgroundColor": ALPACA_DARK["paper"],
                    "borderRadius": "8px",
                    "padding": "10px",
                    "marginBottom": "15px",
                },
            ),
            # 2D Skew
            html.Div(
                children=[
                    dcc.Graph(
                        id=VOL_SKEW_ID,
                        figure=skew_fig,
                        config={
                            "displayModeBar": True,
                            "displaylogo": False,
                            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
                        },
                        style={"height": "300px"},
                    ),
                ],
                style={
                    "backgroundColor": ALPACA_DARK["paper"],
                    "borderRadius": "8px",
                    "padding": "10px",
                },
            ),
        ],
    )


def generate_mock_vol_surface(
    spot_price: float = 450.0,
    num_strikes: int = 15,
    num_expiries: int = 6,
) -> Dict[str, Any]:
    """
    Generate mock volatility surface data for testing/demo.
    
    Args:
        spot_price: Mock spot price
        num_strikes: Number of strikes
        num_expiries: Number of expiries
        
    Returns:
        Mock options data dict with IV values
    """
    np.random.seed(42)  # VIZ_DETERMINISTIC
    
    strikes = np.linspace(spot_price * 0.85, spot_price * 1.15, num_strikes)
    expiry_days = [7, 14, 30, 45, 60, 90][:num_expiries]
    
    calls_data = []
    puts_data = []
    
    base_iv = 0.20  # 20% base IV
    
    for exp_idx, days in enumerate(expiry_days):
        exp_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        term_factor = 1 + 0.1 * np.sqrt(days / 30)  # Term structure
        
        for strike in strikes:
            moneyness = (strike - spot_price) / spot_price
            
            # Volatility smile/skew
            skew = 0.15 * moneyness  # Negative skew (puts have higher IV)
            smile = 0.3 * moneyness**2  # Smile curvature
            
            iv = base_iv * term_factor * (1 - skew + smile)
            iv = max(0.05, min(1.0, iv))  # Clamp to reasonable range
            iv += np.random.uniform(-0.01, 0.01)  # Add noise
            
            calls_data.append({
                "strike": strike,
                "impliedVolatility": iv,
                "expiration": exp_date,
                "openInterest": int(500 + np.random.exponential(1000)),
            })
            
            puts_data.append({
                "strike": strike,
                "impliedVolatility": iv * (1 + 0.05 * max(0, -moneyness)),  # Put skew
                "expiration": exp_date,
                "openInterest": int(400 + np.random.exponential(800)),
            })
    
    return {
        "ticker": "SPY",
        "spot_price": spot_price,
        "calls": pd.DataFrame(calls_data),
        "puts": pd.DataFrame(puts_data),
    }


if __name__ == "__main__":
    # Test the component
    mock_data = generate_mock_vol_surface()
    strikes, expiry_days, iv_matrix = extract_iv_surface_data(
        mock_data, mock_data["spot_price"]
    )
    print(f"Surface: {len(strikes)} strikes x {len(expiry_days)} expiries")
    print(f"IV range: {iv_matrix.min()*100:.1f}% - {iv_matrix.max()*100:.1f}%")
