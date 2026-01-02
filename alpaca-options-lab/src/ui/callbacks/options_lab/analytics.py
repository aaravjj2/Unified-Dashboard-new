"""
Advanced Analytics for Options Lab

Provides:
- Greeks visualization
- IV surface 3D chart
- P&L simulation
- Payoff diagrams
- Volume/OI heatmaps
- Max pain calculation
- Put/call ratio analysis
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


@dataclass
class GreeksSummary:
    """Portfolio Greeks summary."""
    total_delta: float
    total_gamma: float
    total_theta: float
    total_vega: float
    total_rho: float
    delta_dollars: float  # Dollar delta exposure
    gamma_dollars: float
    theta_per_day: float
    vega_per_point: float


def calculate_portfolio_greeks(positions: List[Dict], spot_prices: Dict[str, float]) -> GreeksSummary:
    """
    Calculate aggregate portfolio Greeks.
    
    Args:
        positions: List of position dicts with Greeks
        spot_prices: Dict of ticker -> current price
        
    Returns:
        GreeksSummary with totals
    """
    total_delta = 0.0
    total_gamma = 0.0
    total_theta = 0.0
    total_vega = 0.0
    total_rho = 0.0
    delta_dollars = 0.0
    gamma_dollars = 0.0
    
    for pos in positions:
        qty = pos.get('qty', 0)
        delta = pos.get('delta', 0)
        gamma = pos.get('gamma', 0)
        theta = pos.get('theta', 0)
        vega = pos.get('vega', 0)
        rho = pos.get('rho', 0)
        ticker = pos.get('underlying', '')
        spot = spot_prices.get(ticker, 100)
        
        # Scale by quantity (options are 100 shares each)
        multiplier = qty * 100
        
        total_delta += delta * multiplier
        total_gamma += gamma * multiplier
        total_theta += theta * qty  # Theta is per contract
        total_vega += vega * qty
        total_rho += rho * qty
        
        # Dollar equivalents
        delta_dollars += delta * multiplier * spot
        gamma_dollars += gamma * multiplier * spot
    
    return GreeksSummary(
        total_delta=total_delta,
        total_gamma=total_gamma,
        total_theta=total_theta,
        total_vega=total_vega,
        total_rho=total_rho,
        delta_dollars=delta_dollars,
        gamma_dollars=gamma_dollars,
        theta_per_day=total_theta,
        vega_per_point=total_vega
    )


def create_greeks_dashboard(chain_data: Dict, selected_expiration: str) -> go.Figure:
    """
    Create Greeks visualization dashboard.
    
    Args:
        chain_data: Options chain data
        selected_expiration: Selected expiration date
        
    Returns:
        Plotly figure with Greeks charts
    """
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Delta', 'Gamma', 'Theta', 'Vega'),
        vertical_spacing=0.12,
        horizontal_spacing=0.1
    )
    
    chains = chain_data.get('chains', {})
    chain = chains.get(selected_expiration, {})
    spot_price = chain_data.get('spot_price', 100)
    
    calls = pd.DataFrame(chain.get('calls', []))
    puts = pd.DataFrame(chain.get('puts', []))
    
    if calls.empty and puts.empty:
        return fig
    
    # Ensure numeric
    for df in [calls, puts]:
        for col in ['strike', 'delta', 'gamma', 'theta', 'vega']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Delta chart
    if not calls.empty and 'delta' in calls.columns:
        fig.add_trace(
            go.Scatter(x=calls['strike'], y=calls['delta'], name='Call Delta', 
                      line=dict(color='#4caf50', width=2)),
            row=1, col=1
        )
    if not puts.empty and 'delta' in puts.columns:
        fig.add_trace(
            go.Scatter(x=puts['strike'], y=puts['delta'], name='Put Delta',
                      line=dict(color='#f44336', width=2)),
            row=1, col=1
        )
    fig.add_vline(x=spot_price, line_dash="dash", line_color="yellow", row=1, col=1)
    
    # Gamma chart
    if not calls.empty and 'gamma' in calls.columns:
        fig.add_trace(
            go.Scatter(x=calls['strike'], y=calls['gamma'], name='Call Gamma',
                      line=dict(color='#4caf50', width=2), showlegend=False),
            row=1, col=2
        )
    if not puts.empty and 'gamma' in puts.columns:
        fig.add_trace(
            go.Scatter(x=puts['strike'], y=puts['gamma'], name='Put Gamma',
                      line=dict(color='#f44336', width=2), showlegend=False),
            row=1, col=2
        )
    fig.add_vline(x=spot_price, line_dash="dash", line_color="yellow", row=1, col=2)
    
    # Theta chart
    if not calls.empty and 'theta' in calls.columns:
        fig.add_trace(
            go.Scatter(x=calls['strike'], y=calls['theta'], name='Call Theta',
                      line=dict(color='#4caf50', width=2), showlegend=False),
            row=2, col=1
        )
    if not puts.empty and 'theta' in puts.columns:
        fig.add_trace(
            go.Scatter(x=puts['strike'], y=puts['theta'], name='Put Theta',
                      line=dict(color='#f44336', width=2), showlegend=False),
            row=2, col=1
        )
    fig.add_vline(x=spot_price, line_dash="dash", line_color="yellow", row=2, col=1)
    
    # Vega chart
    if not calls.empty and 'vega' in calls.columns:
        fig.add_trace(
            go.Scatter(x=calls['strike'], y=calls['vega'], name='Call Vega',
                      line=dict(color='#4caf50', width=2), showlegend=False),
            row=2, col=2
        )
    if not puts.empty and 'vega' in puts.columns:
        fig.add_trace(
            go.Scatter(x=puts['strike'], y=puts['vega'], name='Put Vega',
                      line=dict(color='#f44336', width=2), showlegend=False),
            row=2, col=2
        )
    fig.add_vline(x=spot_price, line_dash="dash", line_color="yellow", row=2, col=2)
    
    fig.update_layout(
        template='plotly_dark',
        height=500,
        showlegend=True,
        legend=dict(orientation='h', yanchor='bottom', y=1.02),
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig


def create_iv_surface(chain_data: Dict) -> go.Figure:
    """
    Create 3D IV surface visualization.
    
    Args:
        chain_data: Options chain data with multiple expirations
        
    Returns:
        Plotly 3D surface figure
    """
    chains = chain_data.get('chains', {})
    spot_price = chain_data.get('spot_price', 100)
    
    if not chains:
        return go.Figure()
    
    # Collect IV data across strikes and expirations
    strikes = set()
    expirations = sorted(chains.keys())
    
    for exp, chain in chains.items():
        calls = chain.get('calls', [])
        for c in calls:
            strikes.add(c.get('strike', 0))
    
    strikes = sorted(strikes)
    
    if not strikes or not expirations:
        return go.Figure()
    
    # Build IV matrix (calls)
    iv_matrix = []
    
    for exp in expirations:
        chain = chains[exp]
        calls = {c['strike']: c.get('impliedVolatility', 0) for c in chain.get('calls', [])}
        
        row = [calls.get(s, np.nan) * 100 for s in strikes]  # Convert to %
        iv_matrix.append(row)
    
    iv_matrix = np.array(iv_matrix)
    
    # Convert expirations to days to expiry for y-axis
    today = datetime.now()
    dte = [(datetime.strptime(exp, '%Y-%m-%d') - today).days for exp in expirations]
    
    fig = go.Figure(data=[
        go.Surface(
            x=strikes,
            y=dte,
            z=iv_matrix,
            colorscale='Viridis',
            colorbar=dict(title='IV %'),
            hovertemplate='Strike: $%{x}<br>DTE: %{y}<br>IV: %{z:.1f}%<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title='Implied Volatility Surface',
        scene=dict(
            xaxis_title='Strike Price ($)',
            yaxis_title='Days to Expiration',
            zaxis_title='Implied Volatility (%)',
            camera=dict(eye=dict(x=1.5, y=1.5, z=0.8))
        ),
        template='plotly_dark',
        height=600,
        margin=dict(l=50, r=50, t=80, b=50)
    )
    
    return fig


def create_iv_skew_chart(chain_data: Dict, expiration: str) -> go.Figure:
    """
    Create IV skew/smile visualization for a single expiration.
    
    Args:
        chain_data: Options chain data
        expiration: Selected expiration
        
    Returns:
        Plotly figure showing IV skew
    """
    chains = chain_data.get('chains', {})
    chain = chains.get(expiration, {})
    spot_price = chain_data.get('spot_price', 100)
    
    calls = pd.DataFrame(chain.get('calls', []))
    puts = pd.DataFrame(chain.get('puts', []))
    
    fig = go.Figure()
    
    if not calls.empty and 'impliedVolatility' in calls.columns:
        calls['iv_pct'] = calls['impliedVolatility'] * 100
        calls['moneyness'] = (calls['strike'] / spot_price - 1) * 100
        
        fig.add_trace(go.Scatter(
            x=calls['moneyness'],
            y=calls['iv_pct'],
            mode='lines+markers',
            name='Call IV',
            line=dict(color='#4caf50', width=2),
            marker=dict(size=6)
        ))
    
    if not puts.empty and 'impliedVolatility' in puts.columns:
        puts['iv_pct'] = puts['impliedVolatility'] * 100
        puts['moneyness'] = (puts['strike'] / spot_price - 1) * 100
        
        fig.add_trace(go.Scatter(
            x=puts['moneyness'],
            y=puts['iv_pct'],
            mode='lines+markers',
            name='Put IV',
            line=dict(color='#f44336', width=2),
            marker=dict(size=6)
        ))
    
    fig.add_vline(x=0, line_dash="dash", line_color="yellow", annotation_text="ATM")
    
    fig.update_layout(
        title=f'IV Skew - {expiration}',
        xaxis_title='Moneyness (%)',
        yaxis_title='Implied Volatility (%)',
        template='plotly_dark',
        height=400,
        showlegend=True
    )
    
    return fig


def simulate_pnl(
    option_type: str,
    strike: float,
    premium: float,
    qty: int,
    is_long: bool,
    spot_range: Tuple[float, float],
    current_iv: float = 0.3,
    days_to_expiry: int = 30
) -> go.Figure:
    """
    Simulate P&L for an option position.
    
    Args:
        option_type: 'call' or 'put'
        strike: Strike price
        premium: Option premium paid/received
        qty: Number of contracts
        is_long: True for long, False for short
        spot_range: (min, max) price range to simulate
        current_iv: Current implied volatility
        days_to_expiry: Days until expiration
        
    Returns:
        Plotly figure with P&L simulation
    """
    spot_prices = np.linspace(spot_range[0], spot_range[1], 100)
    
    # P&L at expiration
    if option_type.lower() == 'call':
        intrinsic = np.maximum(spot_prices - strike, 0)
    else:
        intrinsic = np.maximum(strike - spot_prices, 0)
    
    if is_long:
        pnl_expiry = (intrinsic - premium) * qty * 100
    else:
        pnl_expiry = (premium - intrinsic) * qty * 100
    
    # P&L today (simplified using Black-Scholes approximation)
    # This is a rough approximation
    time_factor = np.sqrt(days_to_expiry / 365)
    if option_type.lower() == 'call':
        d1 = (np.log(spot_prices / strike) + (0.05 + current_iv**2 / 2) * days_to_expiry / 365) / (current_iv * time_factor + 1e-10)
        current_value = spot_prices * 0.5 * (1 + np.sign(d1) * (1 - np.exp(-0.5 * d1**2)))  # Simplified
    else:
        current_value = strike * 0.5 * np.exp(-0.05 * days_to_expiry / 365) - (spot_prices - strike) * 0.3
        current_value = np.maximum(current_value, 0)
    
    if is_long:
        pnl_current = (current_value - premium) * qty * 100
    else:
        pnl_current = (premium - current_value) * qty * 100
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=spot_prices, y=pnl_expiry,
        mode='lines', name='At Expiration',
        line=dict(color='#2196F3', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=spot_prices, y=pnl_current,
        mode='lines', name='Current',
        line=dict(color='#FF9800', width=2, dash='dash')
    ))
    
    # Break-even line
    fig.add_hline(y=0, line_color='white', line_dash='dot')
    
    # Strike line
    fig.add_vline(x=strike, line_color='yellow', line_dash='dash', 
                  annotation_text=f'Strike ${strike}')
    
    fig.update_layout(
        title=f'P&L Simulation: {"Long" if is_long else "Short"} {qty} {option_type.upper()} @ ${strike}',
        xaxis_title='Underlying Price ($)',
        yaxis_title='Profit/Loss ($)',
        template='plotly_dark',
        height=400,
        showlegend=True
    )
    
    return fig


def create_payoff_diagram(positions: List[Dict], spot_price: float) -> go.Figure:
    """
    Create payoff diagram for multi-leg strategy.
    
    Args:
        positions: List of position dicts with keys: type, strike, premium, qty, is_long
        spot_price: Current underlying price
        
    Returns:
        Plotly figure with combined payoff
    """
    # Determine price range
    strikes = [p['strike'] for p in positions]
    min_strike = min(strikes)
    max_strike = max(strikes)
    price_range = max_strike - min_strike
    
    spot_prices = np.linspace(
        min_strike - price_range * 0.3,
        max_strike + price_range * 0.3,
        200
    )
    
    total_pnl = np.zeros_like(spot_prices)
    
    fig = go.Figure()
    
    for i, pos in enumerate(positions):
        opt_type = pos['type'].lower()
        strike = pos['strike']
        premium = pos['premium']
        qty = pos['qty']
        is_long = pos.get('is_long', True)
        
        if opt_type == 'call':
            intrinsic = np.maximum(spot_prices - strike, 0)
        else:
            intrinsic = np.maximum(strike - spot_prices, 0)
        
        if is_long:
            pnl = (intrinsic - premium) * qty * 100
        else:
            pnl = (premium - intrinsic) * qty * 100
        
        total_pnl += pnl
        
        # Add individual leg trace
        fig.add_trace(go.Scatter(
            x=spot_prices, y=pnl,
            mode='lines',
            name=f'{"Long" if is_long else "Short"} {opt_type.upper()} ${strike}',
            line=dict(width=1, dash='dot'),
            opacity=0.5
        ))
    
    # Add combined payoff
    fig.add_trace(go.Scatter(
        x=spot_prices, y=total_pnl,
        mode='lines',
        name='Combined P&L',
        line=dict(color='#4caf50', width=3)
    ))
    
    fig.add_hline(y=0, line_color='white', line_dash='dot')
    fig.add_vline(x=spot_price, line_color='yellow', line_dash='dash',
                  annotation_text=f'Current ${spot_price}')
    
    fig.update_layout(
        title='Strategy Payoff Diagram (at Expiration)',
        xaxis_title='Underlying Price ($)',
        yaxis_title='Profit/Loss ($)',
        template='plotly_dark',
        height=450,
        showlegend=True
    )
    
    return fig


def create_volume_oi_heatmap(chain_data: Dict) -> go.Figure:
    """
    Create volume/OI heatmap across strikes and expirations.
    
    Args:
        chain_data: Options chain data
        
    Returns:
        Plotly heatmap figure
    """
    chains = chain_data.get('chains', {})
    
    if not chains:
        return go.Figure()
    
    # Collect data
    strikes = set()
    expirations = sorted(chains.keys())
    
    for exp, chain in chains.items():
        for opt_list in [chain.get('calls', []), chain.get('puts', [])]:
            for opt in opt_list:
                strikes.add(opt.get('strike', 0))
    
    strikes = sorted(strikes)
    
    # Build volume matrix (calls + puts combined)
    volume_matrix = []
    
    for exp in expirations:
        chain = chains[exp]
        call_vol = {c['strike']: (c.get('volume', 0) or 0) for c in chain.get('calls', [])}
        put_vol = {p['strike']: (p.get('volume', 0) or 0) for p in chain.get('puts', [])}
        
        row = [call_vol.get(s, 0) + put_vol.get(s, 0) for s in strikes]
        volume_matrix.append(row)
    
    volume_matrix = np.array(volume_matrix)
    
    fig = go.Figure(data=go.Heatmap(
        x=strikes,
        y=expirations,
        z=volume_matrix,
        colorscale='YlOrRd',
        colorbar=dict(title='Volume'),
        hovertemplate='Strike: $%{x}<br>Exp: %{y}<br>Volume: %{z:,}<extra></extra>'
    ))
    
    fig.update_layout(
        title='Options Volume Heatmap',
        xaxis_title='Strike Price ($)',
        yaxis_title='Expiration',
        template='plotly_dark',
        height=400
    )
    
    return fig


def calculate_max_pain(chain_data: Dict, expiration: str) -> Tuple[float, go.Figure]:
    """
    Calculate max pain strike for given expiration.
    
    Max pain is the strike where option holders would lose the most money
    (and option writers would profit the most).
    
    Args:
        chain_data: Options chain data
        expiration: Expiration date
        
    Returns:
        Tuple of (max_pain_strike, visualization_figure)
    """
    chains = chain_data.get('chains', {})
    chain = chains.get(expiration, {})
    
    calls = pd.DataFrame(chain.get('calls', []))
    puts = pd.DataFrame(chain.get('puts', []))
    
    if calls.empty and puts.empty:
        return 0, go.Figure()
    
    # Get all strikes
    strikes = set()
    if not calls.empty:
        strikes.update(calls['strike'].unique())
    if not puts.empty:
        strikes.update(puts['strike'].unique())
    
    strikes = sorted(strikes)
    
    # Calculate total pain at each strike
    pain_values = []
    
    for test_strike in strikes:
        call_pain = 0
        put_pain = 0
        
        # Call pain: sum of (max(0, strike - test_strike) * OI) for all calls
        if not calls.empty:
            for _, row in calls.iterrows():
                oi = row.get('openInterest', 0) or 0
                strike = row.get('strike', 0) or 0
                if test_strike > strike:
                    call_pain += (test_strike - strike) * oi * 100
        
        # Put pain: sum of (max(0, test_strike - strike) * OI) for all puts
        if not puts.empty:
            for _, row in puts.iterrows():
                oi = row.get('openInterest', 0) or 0
                strike = row.get('strike', 0) or 0
                if test_strike < strike:
                    put_pain += (strike - test_strike) * oi * 100
        
        pain_values.append(call_pain + put_pain)
    
    # Max pain is where total pain is minimized (for option holders)
    # which is where writers profit most
    min_pain_idx = np.argmin(pain_values)
    max_pain_strike = strikes[min_pain_idx]
    
    # Visualization
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=strikes,
        y=pain_values,
        marker_color=['#f44336' if s == max_pain_strike else '#2196F3' for s in strikes],
        hovertemplate='Strike: $%{x}<br>Total Pain: $%{y:,.0f}<extra></extra>'
    ))
    
    fig.add_annotation(
        x=max_pain_strike,
        y=pain_values[min_pain_idx],
        text=f'Max Pain: ${max_pain_strike}',
        showarrow=True,
        arrowhead=2,
        font=dict(color='yellow')
    )
    
    fig.update_layout(
        title=f'Max Pain Analysis - {expiration}',
        xaxis_title='Strike Price ($)',
        yaxis_title='Total Option Holder Pain ($)',
        template='plotly_dark',
        height=400
    )
    
    return max_pain_strike, fig


def calculate_put_call_ratio(chain_data: Dict) -> Dict[str, float]:
    """
    Calculate put/call ratios by volume and open interest.
    
    Args:
        chain_data: Options chain data
        
    Returns:
        Dict with 'volume_ratio', 'oi_ratio', interpretation
    """
    chains = chain_data.get('chains', {})
    
    total_call_vol = 0
    total_put_vol = 0
    total_call_oi = 0
    total_put_oi = 0
    
    for exp, chain in chains.items():
        calls = chain.get('calls', [])
        puts = chain.get('puts', [])
        
        for c in calls:
            total_call_vol += c.get('volume', 0) or 0
            total_call_oi += c.get('openInterest', 0) or 0
        
        for p in puts:
            total_put_vol += p.get('volume', 0) or 0
            total_put_oi += p.get('openInterest', 0) or 0
    
    vol_ratio = total_put_vol / total_call_vol if total_call_vol > 0 else 0
    oi_ratio = total_put_oi / total_call_oi if total_call_oi > 0 else 0
    
    # Interpretation
    if vol_ratio > 1.2:
        vol_sentiment = 'Bearish (high put volume)'
    elif vol_ratio < 0.8:
        vol_sentiment = 'Bullish (high call volume)'
    else:
        vol_sentiment = 'Neutral'
    
    if oi_ratio > 1.2:
        oi_sentiment = 'Bearish positioning'
    elif oi_ratio < 0.8:
        oi_sentiment = 'Bullish positioning'
    else:
        oi_sentiment = 'Balanced positioning'
    
    return {
        'volume_ratio': round(vol_ratio, 2),
        'oi_ratio': round(oi_ratio, 2),
        'call_volume': total_call_vol,
        'put_volume': total_put_vol,
        'call_oi': total_call_oi,
        'put_oi': total_put_oi,
        'volume_sentiment': vol_sentiment,
        'oi_sentiment': oi_sentiment
    }
