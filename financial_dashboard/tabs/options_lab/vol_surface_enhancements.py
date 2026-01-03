"""
Alpaca Options Lab - Volatility Surface Enhancements
Implements Items 51-75 from the 220 NEW IDEAS roadmap
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Tuple, Any
from scipy import interpolate
from scipy.stats import norm
from datetime import datetime, timedelta


# ============================================================
# ITEM 51: IV Percentile Display
# ============================================================
def calculate_iv_percentile(current_iv: float, historical_ivs: List[float], window: int = 252) -> float:
    """Calculate IV percentile based on historical data."""
    if not historical_ivs or len(historical_ivs) < 2:
        return 50.0
    
    ivs = historical_ivs[-window:] if len(historical_ivs) > window else historical_ivs
    percentile = (sum(1 for iv in ivs if iv < current_iv) / len(ivs)) * 100
    return percentile


def create_iv_percentile_badge(percentile: float) -> html.Span:
    """Create colored badge for IV percentile."""
    if percentile >= 80:
        color = "danger"
        label = "Very High"
    elif percentile >= 60:
        color = "warning"
        label = "High"
    elif percentile >= 40:
        color = "info"
        label = "Normal"
    elif percentile >= 20:
        color = "primary"
        label = "Low"
    else:
        color = "success"
        label = "Very Low"
    
    return html.Span([
        dbc.Badge(f"IV Rank: {percentile:.1f}%", color=color, className="me-1"),
        dbc.Badge(label, color=color, className="opacity-75")
    ])


# ============================================================
# ITEM 52: IV Rank vs IV Percentile
# ============================================================
def calculate_iv_rank(current_iv: float, high_iv: float, low_iv: float) -> float:
    """Calculate IV Rank (where IV is within its range)."""
    if high_iv == low_iv:
        return 50.0
    return ((current_iv - low_iv) / (high_iv - low_iv)) * 100


def create_iv_comparison_card(
    current_iv: float,
    historical_ivs: List[float],
    high_iv: float,
    low_iv: float
) -> dbc.Card:
    """Create card comparing IV Rank vs IV Percentile."""
    iv_percentile = calculate_iv_percentile(current_iv, historical_ivs)
    iv_rank = calculate_iv_rank(current_iv, high_iv, low_iv)
    
    return dbc.Card([
        dbc.CardHeader("IV Analysis"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H4(f"{iv_percentile:.1f}%", className="mb-0"),
                        html.Small("IV Percentile", className="text-muted"),
                        dbc.Progress(value=iv_percentile, className="mt-1", style={"height": "8px"})
                    ])
                ], width=6),
                dbc.Col([
                    html.Div([
                        html.H4(f"{iv_rank:.1f}%", className="mb-0"),
                        html.Small("IV Rank", className="text-muted"),
                        dbc.Progress(value=iv_rank, className="mt-1", style={"height": "8px"})
                    ])
                ], width=6),
            ]),
            html.Hr(),
            html.Small([
                html.Strong("Current IV: "), f"{current_iv:.1%}",
                html.Br(),
                html.Strong("52W High: "), f"{high_iv:.1%}",
                html.Br(),
                html.Strong("52W Low: "), f"{low_iv:.1%}",
            ], className="text-muted")
        ])
    ])


# ============================================================
# ITEM 53: Term Structure Chart
# ============================================================
def create_term_structure_chart(expirations: List[str], ivs: List[float]) -> go.Figure:
    """Create term structure chart showing IV across expirations."""
    fig = go.Figure()
    
    # Convert expirations to DTE
    today = datetime.now()
    dtes = []
    for exp in expirations:
        try:
            exp_date = datetime.strptime(exp, "%Y-%m-%d")
            dte = (exp_date - today).days
            dtes.append(dte)
        except:
            dtes.append(30)  # Default
    
    # Main term structure line
    fig.add_trace(go.Scatter(
        x=dtes,
        y=[iv * 100 for iv in ivs],
        mode='lines+markers',
        name='Term Structure',
        line=dict(color='#007bff', width=2),
        marker=dict(size=8)
    ))
    
    # Highlight contango vs backwardation
    if len(ivs) >= 2:
        if ivs[0] < ivs[-1]:
            shape_color = 'rgba(40, 167, 69, 0.1)'  # Green - contango
            annotation = "Contango (Normal)"
        else:
            shape_color = 'rgba(220, 53, 69, 0.1)'  # Red - backwardation
            annotation = "Backwardation"
        
        fig.add_annotation(
            x=dtes[-1] / 2,
            y=max([iv * 100 for iv in ivs]),
            text=annotation,
            showarrow=False,
            font=dict(size=14)
        )
    
    fig.update_layout(
        title="Volatility Term Structure",
        xaxis_title="Days to Expiration",
        yaxis_title="Implied Volatility (%)",
        height=350,
        showlegend=False
    )
    
    return fig


# ============================================================
# ITEM 54: Skew Visualization
# ============================================================
def create_skew_chart(strikes: List[float], ivs: List[float], atm_strike: float) -> go.Figure:
    """Create volatility skew chart."""
    fig = go.Figure()
    
    # Calculate moneyness
    moneyness = [(s / atm_strike - 1) * 100 for s in strikes]
    
    # Skew line
    fig.add_trace(go.Scatter(
        x=moneyness,
        y=[iv * 100 for iv in ivs],
        mode='lines+markers',
        name='IV Skew',
        line=dict(color='#6f42c1', width=2),
        fill='tozeroy',
        fillcolor='rgba(111, 66, 193, 0.1)'
    ))
    
    # ATM line
    fig.add_vline(x=0, line_dash="dash", line_color="black", annotation_text="ATM")
    
    # Skew metrics
    if len(ivs) >= 3:
        # 25-delta skew approximation
        put_wing = ivs[0] if ivs else 0
        call_wing = ivs[-1] if ivs else 0
        atm_iv = ivs[len(ivs)//2] if ivs else 0
        
        put_skew = (put_wing - atm_iv) * 100
        call_skew = (call_wing - atm_iv) * 100
        
        fig.add_annotation(
            x=moneyness[0],
            y=ivs[0] * 100,
            text=f"Put Skew: {put_skew:+.1f}%",
            showarrow=True
        )
        fig.add_annotation(
            x=moneyness[-1],
            y=ivs[-1] * 100,
            text=f"Call Skew: {call_skew:+.1f}%",
            showarrow=True
        )
    
    fig.update_layout(
        title="Volatility Skew",
        xaxis_title="Moneyness (%)",
        yaxis_title="Implied Volatility (%)",
        height=350
    )
    
    return fig


# ============================================================
# ITEM 55: Historical vs Implied Volatility
# ============================================================
def create_hv_iv_comparison(dates: List, hvs: List[float], ivs: List[float]) -> go.Figure:
    """Create HV vs IV comparison chart."""
    fig = go.Figure()
    
    # Historical volatility
    fig.add_trace(go.Scatter(
        x=dates,
        y=[hv * 100 for hv in hvs],
        mode='lines',
        name='Historical Vol (HV)',
        line=dict(color='#17a2b8', width=2)
    ))
    
    # Implied volatility
    fig.add_trace(go.Scatter(
        x=dates,
        y=[iv * 100 for iv in ivs],
        mode='lines',
        name='Implied Vol (IV)',
        line=dict(color='#6f42c1', width=2)
    ))
    
    # Premium/Discount band
    if len(hvs) == len(ivs):
        spreads = [(iv - hv) * 100 for hv, iv in zip(hvs, ivs)]
        
        # Color based on premium/discount
        for i in range(len(dates) - 1):
            spread = spreads[i]
            color = 'rgba(40, 167, 69, 0.2)' if spread > 0 else 'rgba(220, 53, 69, 0.2)'
    
    fig.update_layout(
        title="Historical vs Implied Volatility",
        xaxis_title="Date",
        yaxis_title="Volatility (%)",
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    
    return fig


# ============================================================
# ITEM 57: Vol Surface Rotation Animation
# ============================================================
def create_3d_vol_surface(
    strikes: np.ndarray,
    expirations: np.ndarray,
    iv_matrix: np.ndarray,
    spot_price: float
) -> go.Figure:
    """Create interactive 3D volatility surface."""
    
    # Calculate moneyness
    moneyness = (strikes / spot_price - 1) * 100
    
    fig = go.Figure(data=[go.Surface(
        x=moneyness,
        y=expirations,
        z=iv_matrix * 100,
        colorscale='Viridis',
        colorbar=dict(title="IV (%)"),
        contours={
            "z": {"show": True, "usecolormap": True, "highlightcolor": "limegreen", "project_z": True}
        }
    )])
    
    # Add ATM line
    atm_ivs = [iv_matrix[i, len(strikes)//2] * 100 for i in range(len(expirations))]
    fig.add_trace(go.Scatter3d(
        x=[0] * len(expirations),
        y=expirations,
        z=atm_ivs,
        mode='lines',
        name='ATM',
        line=dict(color='red', width=5)
    ))
    
    fig.update_layout(
        title='3D Volatility Surface',
        scene=dict(
            xaxis_title='Moneyness (%)',
            yaxis_title='Days to Expiration',
            zaxis_title='Implied Volatility (%)',
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2)
            )
        ),
        height=500
    )
    
    return fig


# ============================================================
# ITEM 58: Vol Surface Smoothing
# ============================================================
def smooth_vol_surface(
    strikes: np.ndarray,
    expirations: np.ndarray,
    iv_matrix: np.ndarray,
    smoothing_factor: float = 0.5
) -> np.ndarray:
    """Apply smoothing to volatility surface."""
    from scipy.ndimage import gaussian_filter
    
    smoothed = gaussian_filter(iv_matrix, sigma=smoothing_factor)
    return smoothed


def interpolate_vol_surface(
    strikes: np.ndarray,
    expirations: np.ndarray,
    iv_matrix: np.ndarray,
    new_strikes: np.ndarray,
    new_expirations: np.ndarray
) -> np.ndarray:
    """Interpolate volatility surface to new grid."""
    interp_func = interpolate.RectBivariateSpline(
        expirations, strikes, iv_matrix, kx=3, ky=3
    )
    
    return interp_func(new_expirations, new_strikes)


# ============================================================
# ITEM 60: Volatility Cone
# ============================================================
def calculate_volatility_cone(
    price_history: pd.Series,
    windows: List[int] = [10, 20, 30, 60, 90, 120]
) -> pd.DataFrame:
    """Calculate volatility cone percentiles."""
    results = []
    
    for window in windows:
        # Rolling volatility
        returns = price_history.pct_change().dropna()
        rolling_vol = returns.rolling(window).std() * np.sqrt(252)
        rolling_vol = rolling_vol.dropna()
        
        if len(rolling_vol) > 0:
            results.append({
                'window': window,
                'current': rolling_vol.iloc[-1],
                'min': rolling_vol.min(),
                'p25': rolling_vol.quantile(0.25),
                'median': rolling_vol.median(),
                'p75': rolling_vol.quantile(0.75),
                'max': rolling_vol.max()
            })
    
    return pd.DataFrame(results)


def create_volatility_cone_chart(vol_cone_df: pd.DataFrame, current_iv: float = None) -> go.Figure:
    """Create volatility cone chart."""
    fig = go.Figure()
    
    windows = vol_cone_df['window'].tolist()
    
    # Max band
    fig.add_trace(go.Scatter(
        x=windows,
        y=vol_cone_df['max'] * 100,
        mode='lines',
        name='Max',
        line=dict(color='rgba(220, 53, 69, 0.5)', dash='dot')
    ))
    
    # 75th percentile
    fig.add_trace(go.Scatter(
        x=windows,
        y=vol_cone_df['p75'] * 100,
        mode='lines',
        name='75th %ile',
        fill=None,
        line=dict(color='rgba(255, 193, 7, 0.8)')
    ))
    
    # Median
    fig.add_trace(go.Scatter(
        x=windows,
        y=vol_cone_df['median'] * 100,
        mode='lines',
        name='Median',
        fill='tonexty',
        fillcolor='rgba(255, 193, 7, 0.2)',
        line=dict(color='#007bff', width=2)
    ))
    
    # 25th percentile
    fig.add_trace(go.Scatter(
        x=windows,
        y=vol_cone_df['p25'] * 100,
        mode='lines',
        name='25th %ile',
        fill='tonexty',
        fillcolor='rgba(23, 162, 184, 0.2)',
        line=dict(color='rgba(23, 162, 184, 0.8)')
    ))
    
    # Min band
    fig.add_trace(go.Scatter(
        x=windows,
        y=vol_cone_df['min'] * 100,
        mode='lines',
        name='Min',
        line=dict(color='rgba(40, 167, 69, 0.5)', dash='dot')
    ))
    
    # Current realized vol
    fig.add_trace(go.Scatter(
        x=windows,
        y=vol_cone_df['current'] * 100,
        mode='lines+markers',
        name='Current RV',
        line=dict(color='black', width=3),
        marker=dict(size=8)
    ))
    
    # Current IV line
    if current_iv:
        fig.add_hline(
            y=current_iv * 100,
            line_dash="dash",
            line_color="purple",
            annotation_text=f"Current IV: {current_iv*100:.1f}%"
        )
    
    fig.update_layout(
        title="Volatility Cone",
        xaxis_title="Lookback Window (Days)",
        yaxis_title="Volatility (%)",
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )
    
    return fig


# ============================================================
# ITEM 61: Vol Surface Delta Viewer
# ============================================================
def calculate_surface_changes(
    current_surface: np.ndarray,
    previous_surface: np.ndarray
) -> np.ndarray:
    """Calculate changes in vol surface."""
    return current_surface - previous_surface


def create_surface_change_heatmap(
    strikes: np.ndarray,
    expirations: np.ndarray,
    changes: np.ndarray,
    spot_price: float
) -> go.Figure:
    """Create heatmap of vol surface changes."""
    moneyness = (strikes / spot_price - 1) * 100
    
    fig = go.Figure(data=go.Heatmap(
        x=moneyness,
        y=expirations,
        z=changes * 100,
        colorscale='RdYlGn_r',  # Red for increase, green for decrease
        zmid=0,
        colorbar=dict(title="IV Change (%)")
    ))
    
    fig.update_layout(
        title="Vol Surface Changes (1D)",
        xaxis_title="Moneyness (%)",
        yaxis_title="Days to Expiration",
        height=400
    )
    
    return fig


# ============================================================
# ITEM 63: IV vs RV Spread
# ============================================================
def calculate_vol_premium(iv: float, rv: float) -> Dict[str, Any]:
    """Calculate volatility risk premium metrics."""
    spread = iv - rv
    premium_pct = (spread / rv * 100) if rv != 0 else 0
    
    return {
        'iv': iv,
        'rv': rv,
        'spread': spread,
        'premium_pct': premium_pct,
        'signal': 'SELL_VOL' if premium_pct > 20 else 'BUY_VOL' if premium_pct < -10 else 'NEUTRAL'
    }


def create_vol_premium_indicator(metrics: Dict[str, Any]) -> dbc.Card:
    """Create volatility premium indicator card."""
    signal_colors = {
        'SELL_VOL': ('danger', 'Sell Premium'),
        'BUY_VOL': ('success', 'Buy Vol'),
        'NEUTRAL': ('secondary', 'Neutral')
    }
    
    color, label = signal_colors.get(metrics['signal'], ('secondary', 'Unknown'))
    
    return dbc.Card([
        dbc.CardHeader("Vol Risk Premium"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H5(f"{metrics['iv']*100:.1f}%", className="text-primary mb-0"),
                    html.Small("IV", className="text-muted")
                ], width=4),
                dbc.Col([
                    html.H5(f"{metrics['rv']*100:.1f}%", className="text-info mb-0"),
                    html.Small("RV", className="text-muted")
                ], width=4),
                dbc.Col([
                    html.H5(f"{metrics['spread']*100:+.1f}%", className="mb-0"),
                    html.Small("Spread", className="text-muted")
                ], width=4),
            ]),
            html.Hr(),
            html.Div([
                dbc.Badge(label, color=color, className="me-2"),
                html.Small(f"Premium: {metrics['premium_pct']:+.1f}%")
            ], className="text-center")
        ])
    ])


# ============================================================
# ITEM 65: Expected Move Calculator
# ============================================================
def calculate_expected_move(
    spot_price: float,
    atm_iv: float,
    dte: int,
    straddle_price: float = None
) -> Dict[str, float]:
    """Calculate expected move metrics."""
    # From IV
    iv_move = spot_price * atm_iv * np.sqrt(dte / 365)
    
    # From straddle price
    if straddle_price:
        straddle_move = straddle_price * 0.85  # 85% rule of thumb
    else:
        straddle_move = iv_move
    
    # 1 and 2 standard deviation moves
    return {
        'spot': spot_price,
        'expected_move_1sd': iv_move,
        'expected_move_2sd': iv_move * 2,
        'upper_1sd': spot_price + iv_move,
        'lower_1sd': spot_price - iv_move,
        'upper_2sd': spot_price + iv_move * 2,
        'lower_2sd': spot_price - iv_move * 2,
        'straddle_move': straddle_move,
        'move_pct': iv_move / spot_price * 100
    }


def create_expected_move_visual(metrics: Dict[str, float]) -> go.Figure:
    """Create expected move visualization."""
    fig = go.Figure()
    
    # Current price
    fig.add_trace(go.Scatter(
        x=[0],
        y=[metrics['spot']],
        mode='markers',
        name='Current',
        marker=dict(size=15, color='blue', symbol='diamond')
    ))
    
    # 1 SD range
    fig.add_shape(
        type="rect",
        x0=-0.3, x1=0.3,
        y0=metrics['lower_1sd'], y1=metrics['upper_1sd'],
        fillcolor="rgba(40, 167, 69, 0.3)",
        line=dict(color="green", width=2)
    )
    
    # 2 SD range
    fig.add_shape(
        type="rect",
        x0=-0.4, x1=0.4,
        y0=metrics['lower_2sd'], y1=metrics['upper_2sd'],
        fillcolor="rgba(255, 193, 7, 0.2)",
        line=dict(color="orange", width=1, dash="dash")
    )
    
    # Annotations
    fig.add_annotation(x=0.35, y=metrics['upper_1sd'], text=f"1σ: ${metrics['upper_1sd']:.2f}", showarrow=False)
    fig.add_annotation(x=0.35, y=metrics['lower_1sd'], text=f"1σ: ${metrics['lower_1sd']:.2f}", showarrow=False)
    fig.add_annotation(x=0.45, y=metrics['upper_2sd'], text=f"2σ: ${metrics['upper_2sd']:.2f}", showarrow=False)
    fig.add_annotation(x=0.45, y=metrics['lower_2sd'], text=f"2σ: ${metrics['lower_2sd']:.2f}", showarrow=False)
    
    fig.update_layout(
        title=f"Expected Move: ±${metrics['expected_move_1sd']:.2f} ({metrics['move_pct']:.1f}%)",
        showlegend=False,
        xaxis=dict(showticklabels=False, showgrid=False),
        yaxis_title="Price ($)",
        height=350
    )
    
    return fig


# ============================================================
# ITEM 68: Vol Surface Snapshot Save/Compare
# ============================================================
class VolSurfaceSnapshot:
    """Store and compare vol surface snapshots."""
    
    def __init__(self):
        self.snapshots = {}
    
    def save_snapshot(
        self,
        name: str,
        strikes: np.ndarray,
        expirations: np.ndarray,
        iv_matrix: np.ndarray
    ):
        """Save a vol surface snapshot."""
        self.snapshots[name] = {
            'timestamp': datetime.now(),
            'strikes': strikes.copy(),
            'expirations': expirations.copy(),
            'iv_matrix': iv_matrix.copy()
        }
    
    def compare_snapshots(self, name1: str, name2: str) -> np.ndarray:
        """Compare two snapshots and return difference."""
        if name1 not in self.snapshots or name2 not in self.snapshots:
            return None
        
        snap1 = self.snapshots[name1]
        snap2 = self.snapshots[name2]
        
        # Assume same grid for simplicity
        return snap2['iv_matrix'] - snap1['iv_matrix']
    
    def list_snapshots(self) -> List[Dict]:
        """List all saved snapshots."""
        return [
            {'name': name, 'timestamp': data['timestamp']}
            for name, data in self.snapshots.items()
        ]


# ============================================================
# Main Vol Surface Dashboard
# ============================================================
def create_vol_surface_dashboard() -> html.Div:
    """Create comprehensive volatility surface dashboard."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("Volatility Surface Controls"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Label("Surface Type"),
                                dbc.Select(
                                    id="vol-surface-type",
                                    options=[
                                        {"label": "IV Surface", "value": "iv"},
                                        {"label": "Delta Surface", "value": "delta"},
                                        {"label": "Gamma Surface", "value": "gamma"},
                                    ],
                                    value="iv"
                                )
                            ], width=4),
                            dbc.Col([
                                dbc.Label("Smoothing"),
                                dcc.Slider(
                                    id="vol-surface-smoothing",
                                    min=0, max=2, step=0.1, value=0.5,
                                    marks={0: '0', 1: '1', 2: '2'}
                                )
                            ], width=4),
                            dbc.Col([
                                dbc.Label("View"),
                                dbc.RadioItems(
                                    id="vol-surface-view",
                                    options=[
                                        {"label": "3D", "value": "3d"},
                                        {"label": "Heatmap", "value": "heatmap"},
                                    ],
                                    value="3d",
                                    inline=True
                                )
                            ], width=4),
                        ])
                    ])
                ])
            ], width=12)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="vol-surface-main-chart")
            ], width=8),
            dbc.Col([
                html.Div(id="vol-surface-metrics")
            ], width=4)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="term-structure-chart")
            ], width=6),
            dbc.Col([
                dcc.Graph(id="skew-chart")
            ], width=6)
        ], className="mb-3"),
        
        dbc.Row([
            dbc.Col([
                dcc.Graph(id="vol-cone-chart")
            ], width=6),
            dbc.Col([
                dcc.Graph(id="hv-iv-chart")
            ], width=6)
        ])
    ])


__all__ = [
    'calculate_iv_percentile',
    'create_iv_percentile_badge',
    'calculate_iv_rank',
    'create_iv_comparison_card',
    'create_term_structure_chart',
    'create_skew_chart',
    'create_hv_iv_comparison',
    'create_3d_vol_surface',
    'smooth_vol_surface',
    'interpolate_vol_surface',
    'calculate_volatility_cone',
    'create_volatility_cone_chart',
    'calculate_surface_changes',
    'create_surface_change_heatmap',
    'calculate_vol_premium',
    'create_vol_premium_indicator',
    'calculate_expected_move',
    'create_expected_move_visual',
    'VolSurfaceSnapshot',
    'create_vol_surface_dashboard',
]
