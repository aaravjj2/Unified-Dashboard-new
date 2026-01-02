"""
Alpaca Options Lab - Advanced Greeks Components
Implements Items 26-50 from the 220 NEW IDEAS roadmap
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta

# ============================================================
# ITEM 26: Interactive Greeks Heatmap
# ============================================================
def create_greeks_heatmap(
    calls_df: pd.DataFrame,
    puts_df: pd.DataFrame,
    greek: str = "delta",
    spot_price: float = 100
) -> go.Figure:
    """Create interactive Greeks heatmap by strike/expiry."""
    try:
        # Combine calls and puts
        calls_df = calls_df.copy()
        puts_df = puts_df.copy()
        calls_df['type'] = 'call'
        puts_df['type'] = 'put'
        
        df = pd.concat([calls_df, puts_df], ignore_index=True)
        
        if greek not in df.columns:
            greek = 'delta'  # fallback
        
        # Pivot for heatmap
        pivot = df.pivot_table(
            values=greek,
            index='strike',
            columns='type',
            aggfunc='mean'
        )
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale='RdYlGn',
            colorbar=dict(title=greek.title())
        ))
        
        # Add spot price line
        fig.add_hline(y=spot_price, line_dash="dash", line_color="blue", 
                     annotation_text="Spot")
        
        fig.update_layout(
            title=f"{greek.title()} Heatmap",
            xaxis_title="Option Type",
            yaxis_title="Strike",
            height=400
        )
        
        return fig
    except Exception as e:
        return go.Figure().add_annotation(text=f"Error: {str(e)}")

# ============================================================
# ITEM 27: Portfolio Greeks Aggregation
# ============================================================
def aggregate_portfolio_greeks(positions: List[Dict]) -> Dict[str, float]:
    """Aggregate Greeks across portfolio positions."""
    totals = {
        'delta': 0, 'gamma': 0, 'theta': 0, 'vega': 0, 'rho': 0
    }
    
    for pos in positions:
        qty = pos.get('quantity', 1)
        for greek in totals:
            totals[greek] += pos.get(greek, 0) * qty
    
    return totals

def create_portfolio_greeks_card(totals: Dict[str, float]) -> dbc.Card:
    """Create portfolio Greeks display card."""
    return dbc.Card([
        dbc.CardHeader("Portfolio Greeks"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H4(f"{totals['delta']:.2f}", 
                               style={"color": "#28a745" if totals['delta'] >= 0 else "#dc3545"}),
                        html.Small("Net Delta", className="text-muted")
                    ], className="text-center")
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.H4(f"{totals['gamma']:.4f}"),
                        html.Small("Gamma", className="text-muted")
                    ], className="text-center")
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.H4(f"${totals['theta']:.2f}", 
                               style={"color": "#dc3545" if totals['theta'] < 0 else "#28a745"}),
                        html.Small("Daily Theta", className="text-muted")
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.H4(f"${totals['vega']:.2f}"),
                        html.Small("Vega", className="text-muted")
                    ], className="text-center")
                ], width=2),
                dbc.Col([
                    html.Div([
                        html.H4(f"${totals['rho']:.2f}"),
                        html.Small("Rho", className="text-muted")
                    ], className="text-center")
                ], width=3),
            ])
        ])
    ], className="mb-3")

# ============================================================
# ITEM 30: Gamma Exposure (GEX) Chart
# ============================================================
def calculate_gex(
    calls_df: pd.DataFrame,
    puts_df: pd.DataFrame,
    spot_price: float
) -> pd.DataFrame:
    """Calculate Gamma Exposure (GEX) by strike."""
    try:
        strikes = sorted(set(
            list(calls_df['strike'].unique() if 'strike' in calls_df else []) +
            list(puts_df['strike'].unique() if 'strike' in puts_df else [])
        ))
        
        gex_data = []
        for strike in strikes:
            call_gamma = 0
            put_gamma = 0
            call_oi = 0
            put_oi = 0
            
            if len(calls_df[calls_df['strike'] == strike]) > 0:
                row = calls_df[calls_df['strike'] == strike].iloc[0]
                call_gamma = row.get('gamma', 0)
                call_oi = row.get('openInterest', 0)
            
            if len(puts_df[puts_df['strike'] == strike]) > 0:
                row = puts_df[puts_df['strike'] == strike].iloc[0]
                put_gamma = row.get('gamma', 0)
                put_oi = row.get('openInterest', 0)
            
            # GEX = Gamma * OI * spot^2 * 0.01
            # Calls add to GEX, puts subtract
            call_gex = call_gamma * call_oi * spot_price * spot_price * 0.01
            put_gex = -put_gamma * put_oi * spot_price * spot_price * 0.01
            net_gex = call_gex + put_gex
            
            gex_data.append({
                'strike': strike,
                'call_gex': call_gex / 1e6,  # In millions
                'put_gex': put_gex / 1e6,
                'net_gex': net_gex / 1e6
            })
        
        return pd.DataFrame(gex_data)
    except Exception:
        return pd.DataFrame()

def create_gex_chart(gex_df: pd.DataFrame, spot_price: float) -> go.Figure:
    """Create GEX chart by strike."""
    if gex_df.empty:
        return go.Figure().add_annotation(text="No GEX data available")
    
    fig = go.Figure()
    
    # Add bars for call and put GEX
    fig.add_trace(go.Bar(
        x=gex_df['strike'],
        y=gex_df['call_gex'],
        name='Call GEX',
        marker_color='green',
        opacity=0.7
    ))
    
    fig.add_trace(go.Bar(
        x=gex_df['strike'],
        y=gex_df['put_gex'],
        name='Put GEX',
        marker_color='red',
        opacity=0.7
    ))
    
    # Add net GEX line
    fig.add_trace(go.Scatter(
        x=gex_df['strike'],
        y=gex_df['net_gex'],
        name='Net GEX',
        mode='lines+markers',
        line=dict(color='blue', width=2)
    ))
    
    # Add spot price line
    fig.add_vline(x=spot_price, line_dash="dash", line_color="orange",
                 annotation_text=f"Spot: ${spot_price:.2f}")
    
    fig.update_layout(
        title="Gamma Exposure (GEX) by Strike",
        xaxis_title="Strike Price",
        yaxis_title="GEX ($M)",
        barmode='overlay',
        height=400
    )
    
    return fig

# ============================================================
# ITEM 31: Delta Hedging Calculator
# ============================================================
def calculate_delta_hedge(
    net_delta: float,
    spot_price: float,
    position_value: float
) -> Dict[str, Any]:
    """Calculate shares needed for delta hedging."""
    shares_needed = int(-net_delta * 100)  # Each delta = 100 shares
    hedge_cost = abs(shares_needed * spot_price)
    
    return {
        'shares_needed': shares_needed,
        'action': 'BUY' if shares_needed > 0 else 'SELL',
        'hedge_cost': hedge_cost,
        'new_delta': 0,  # After hedge
        'pct_of_position': (hedge_cost / position_value * 100) if position_value > 0 else 0
    }

def create_delta_hedge_card(hedge: Dict[str, Any]) -> dbc.Card:
    """Create delta hedge recommendation card."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-shield-alt me-2"),
            "Delta Hedge Recommendation"
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H4(f"{abs(hedge['shares_needed']):,}", className="mb-0"),
                    html.Small("Shares to " + hedge['action'], className="text-muted")
                ], width=4),
                dbc.Col([
                    html.H4(f"${hedge['hedge_cost']:,.0f}", className="mb-0"),
                    html.Small("Hedge Cost", className="text-muted")
                ], width=4),
                dbc.Col([
                    dbc.Button(
                        [html.I(className="fas fa-check me-2"), "Apply Hedge"],
                        id="apply-delta-hedge-btn",
                        color="success",
                        size="sm"
                    )
                ], width=4, className="d-flex align-items-center")
            ])
        ])
    ], className="mb-3", color="light")

# ============================================================
# ITEM 33: Theta Decay Projector
# ============================================================
def project_theta_decay(
    positions: List[Dict],
    days: List[int] = [1, 3, 7, 14, 30]
) -> pd.DataFrame:
    """Project theta decay over time."""
    daily_theta = sum(pos.get('theta', 0) * pos.get('quantity', 1) for pos in positions)
    
    projections = []
    cumulative = 0
    
    for d in days:
        # Theta accelerates as expiry approaches
        decay_factor = 1 + (d / 30) * 0.2  # Simple acceleration model
        day_decay = daily_theta * d * decay_factor
        cumulative = day_decay
        
        projections.append({
            'days': d,
            'label': f"T-{d}",
            'theta_decay': cumulative,
            'pct_loss': (cumulative / sum(pos.get('value', 0) * pos.get('quantity', 1) 
                        for pos in positions) * 100) if positions else 0
        })
    
    return pd.DataFrame(projections)

def create_theta_decay_chart(projections: pd.DataFrame) -> go.Figure:
    """Create theta decay projection chart."""
    if projections.empty:
        return go.Figure().add_annotation(text="No positions")
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=projections['label'],
        y=projections['theta_decay'],
        marker_color=['#ffc107' if d <= 7 else '#dc3545' 
                     for d in projections['days']],
        text=[f"${v:.0f}" for v in projections['theta_decay']],
        textposition='outside'
    ))
    
    fig.update_layout(
        title="Projected Theta Decay",
        xaxis_title="Time Horizon",
        yaxis_title="Cumulative Decay ($)",
        height=300
    )
    
    return fig

# ============================================================
# ITEM 40: Greeks Stress Test
# ============================================================
def stress_test_greeks(
    positions: List[Dict],
    spot_price: float,
    moves: List[float] = [-0.2, -0.1, -0.05, 0, 0.05, 0.1, 0.2]
) -> pd.DataFrame:
    """Stress test portfolio P&L for different price moves."""
    results = []
    
    for move in moves:
        new_spot = spot_price * (1 + move)
        pnl = 0
        
        for pos in positions:
            delta = pos.get('delta', 0)
            gamma = pos.get('gamma', 0)
            qty = pos.get('quantity', 1)
            
            # Taylor expansion: P&L ≈ Δ * ΔS + 0.5 * Γ * ΔS²
            delta_s = new_spot - spot_price
            position_pnl = (delta * delta_s + 0.5 * gamma * delta_s * delta_s) * qty * 100
            pnl += position_pnl
        
        results.append({
            'move_pct': move * 100,
            'new_spot': new_spot,
            'pnl': pnl,
            'color': 'green' if pnl >= 0 else 'red'
        })
    
    return pd.DataFrame(results)

def create_stress_test_chart(results: pd.DataFrame, spot_price: float) -> go.Figure:
    """Create stress test P&L chart."""
    if results.empty:
        return go.Figure().add_annotation(text="No data")
    
    colors = ['#28a745' if p >= 0 else '#dc3545' for p in results['pnl']]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=[f"{m:.0f}%" for m in results['move_pct']],
        y=results['pnl'],
        marker_color=colors,
        text=[f"${p:,.0f}" for p in results['pnl']],
        textposition='outside'
    ))
    
    fig.add_hline(y=0, line_dash="solid", line_color="black")
    
    fig.update_layout(
        title=f"P&L Stress Test (Spot: ${spot_price:.2f})",
        xaxis_title="Price Move",
        yaxis_title="Estimated P&L ($)",
        height=350
    )
    
    return fig

# ============================================================
# ITEM 49: Greeks Alert Thresholds
# ============================================================
def check_greeks_alerts(
    totals: Dict[str, float],
    thresholds: Dict[str, Tuple[float, float]]
) -> List[Dict[str, Any]]:
    """Check if Greeks exceed alert thresholds."""
    alerts = []
    
    default_thresholds = {
        'delta': (-50, 50),
        'gamma': (0, 10),
        'theta': (-500, 0),
        'vega': (-1000, 1000)
    }
    
    thresholds = {**default_thresholds, **thresholds}
    
    for greek, (low, high) in thresholds.items():
        value = totals.get(greek, 0)
        if value < low:
            alerts.append({
                'greek': greek,
                'level': 'warning',
                'message': f"{greek.title()} ({value:.2f}) below threshold ({low})",
                'action': f"Consider reducing {greek} exposure"
            })
        elif value > high:
            alerts.append({
                'greek': greek,
                'level': 'danger',
                'message': f"{greek.title()} ({value:.2f}) above threshold ({high})",
                'action': f"Consider hedging {greek} exposure"
            })
    
    return alerts

def create_alerts_panel(alerts: List[Dict[str, Any]]) -> html.Div:
    """Create Greeks alerts panel."""
    if not alerts:
        return html.Div([
            html.I(className="fas fa-check-circle text-success me-2"),
            "All Greeks within thresholds"
        ], className="alert alert-success")
    
    alert_items = []
    for alert in alerts:
        color = "warning" if alert['level'] == 'warning' else 'danger'
        alert_items.append(
            dbc.Alert([
                html.Strong(alert['message']),
                html.Br(),
                html.Small(alert['action'], className="text-muted")
            ], color=color, className="mb-2")
        )
    
    return html.Div(alert_items)

# ============================================================
# Main Dashboard Builder
# ============================================================
def create_advanced_greeks_dashboard(
    calls_df: pd.DataFrame,
    puts_df: pd.DataFrame,
    positions: List[Dict],
    spot_price: float
) -> html.Div:
    """Build complete advanced Greeks dashboard."""
    
    # Calculate aggregates
    totals = aggregate_portfolio_greeks(positions)
    gex_df = calculate_gex(calls_df, puts_df, spot_price)
    theta_proj = project_theta_decay(positions)
    stress_results = stress_test_greeks(positions, spot_price)
    alerts = check_greeks_alerts(totals, {})
    
    # Delta hedge recommendation
    hedge = calculate_delta_hedge(totals['delta'], spot_price, 100000)
    
    return html.Div([
        # Portfolio Greeks Summary
        create_portfolio_greeks_card(totals),
        
        # Alerts
        html.H5("Risk Alerts", className="mt-3 mb-2"),
        create_alerts_panel(alerts),
        
        # Delta Hedge
        create_delta_hedge_card(hedge),
        
        # Charts Row 1
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(figure=create_gex_chart(gex_df, spot_price))
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(figure=create_theta_decay_chart(theta_proj))
                    ])
                ])
            ], width=6),
        ], className="mb-3"),
        
        # Charts Row 2
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(figure=create_stress_test_chart(stress_results, spot_price))
                    ])
                ])
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(figure=create_greeks_heatmap(calls_df, puts_df, 'delta', spot_price))
                    ])
                ])
            ], width=6),
        ]),
    ])


__all__ = [
    'create_greeks_heatmap',
    'aggregate_portfolio_greeks',
    'create_portfolio_greeks_card',
    'calculate_gex',
    'create_gex_chart',
    'calculate_delta_hedge',
    'create_delta_hedge_card',
    'project_theta_decay',
    'create_theta_decay_chart',
    'stress_test_greeks',
    'create_stress_test_chart',
    'check_greeks_alerts',
    'create_alerts_panel',
    'create_advanced_greeks_dashboard',
]
