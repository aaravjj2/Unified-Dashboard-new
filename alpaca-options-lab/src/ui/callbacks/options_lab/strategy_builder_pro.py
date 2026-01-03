"""
Alpaca Options Lab - Strategy Builder Pro Components
Implements Items 76-100 from the 220 NEW IDEAS roadmap
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import sys
import os

# Add parent paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

# Import Week 2 enhancements
try:
    from src.ui.components.buttons import create_button
except ImportError:
    def create_button(button_id, text, **kwargs):
        return dbc.Button(text, id=button_id, **kwargs)

# ============================================================
# Strategy Types
# ============================================================
class StrategyType(Enum):
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"
    SHORT_CALL = "short_call"
    SHORT_PUT = "short_put"
    BULL_CALL_SPREAD = "bull_call_spread"
    BEAR_PUT_SPREAD = "bear_put_spread"
    IRON_CONDOR = "iron_condor"
    IRON_BUTTERFLY = "iron_butterfly"
    STRADDLE = "straddle"
    STRANGLE = "strangle"
    CALENDAR_SPREAD = "calendar_spread"
    DIAGONAL_SPREAD = "diagonal_spread"
    JADE_LIZARD = "jade_lizard"
    CUSTOM = "custom"

@dataclass
class StrategyLeg:
    """Single leg of an options strategy."""
    option_type: str  # 'call' or 'put'
    strike: float
    expiration: str
    quantity: int  # positive for long, negative for short
    premium: float
    delta: float = 0
    gamma: float = 0
    theta: float = 0
    vega: float = 0

@dataclass
class Strategy:
    """Complete options strategy."""
    name: str
    strategy_type: StrategyType
    legs: List[StrategyLeg]
    ticker: str
    spot_price: float
    max_profit: float = 0
    max_loss: float = 0
    breakevens: List[float] = field(default_factory=list)
    pop: float = 0  # Probability of profit
    net_credit: float = 0

# ============================================================
# ITEM 77: Pre-built Strategy Templates
# ============================================================
STRATEGY_TEMPLATES = {
    "iron_condor": {
        "name": "Iron Condor",
        "description": "Neutral strategy profiting from low volatility",
        "legs": [
            {"type": "put", "offset": -0.10, "qty": 1},   # Buy OTM put
            {"type": "put", "offset": -0.05, "qty": -1},  # Sell put
            {"type": "call", "offset": 0.05, "qty": -1},  # Sell call
            {"type": "call", "offset": 0.10, "qty": 1},   # Buy OTM call
        ],
        "ideal_iv": "high",
        "ideal_outlook": "neutral"
    },
    "iron_butterfly": {
        "name": "Iron Butterfly",
        "description": "Neutral strategy with ATM short strikes",
        "legs": [
            {"type": "put", "offset": -0.05, "qty": 1},
            {"type": "put", "offset": 0, "qty": -1},
            {"type": "call", "offset": 0, "qty": -1},
            {"type": "call", "offset": 0.05, "qty": 1},
        ],
        "ideal_iv": "high",
        "ideal_outlook": "neutral"
    },
    "bull_call_spread": {
        "name": "Bull Call Spread",
        "description": "Bullish debit spread",
        "legs": [
            {"type": "call", "offset": 0, "qty": 1},      # Buy ATM call
            {"type": "call", "offset": 0.05, "qty": -1},  # Sell OTM call
        ],
        "ideal_iv": "low",
        "ideal_outlook": "bullish"
    },
    "bear_put_spread": {
        "name": "Bear Put Spread",
        "description": "Bearish debit spread",
        "legs": [
            {"type": "put", "offset": 0, "qty": 1},       # Buy ATM put
            {"type": "put", "offset": -0.05, "qty": -1},  # Sell OTM put
        ],
        "ideal_iv": "low",
        "ideal_outlook": "bearish"
    },
    "long_straddle": {
        "name": "Long Straddle",
        "description": "Profit from large moves either direction",
        "legs": [
            {"type": "call", "offset": 0, "qty": 1},
            {"type": "put", "offset": 0, "qty": 1},
        ],
        "ideal_iv": "low",
        "ideal_outlook": "volatile"
    },
    "jade_lizard": {
        "name": "Jade Lizard",
        "description": "Short put spread + short call",
        "legs": [
            {"type": "put", "offset": -0.10, "qty": 1},
            {"type": "put", "offset": -0.05, "qty": -1},
            {"type": "call", "offset": 0.05, "qty": -1},
        ],
        "ideal_iv": "high",
        "ideal_outlook": "neutral_bullish"
    },
}

def apply_template(
    template_name: str,
    spot_price: float,
    calls_df: pd.DataFrame,
    puts_df: pd.DataFrame,
    expiration: str
) -> List[StrategyLeg]:
    """Apply a strategy template to create legs."""
    template = STRATEGY_TEMPLATES.get(template_name)
    if not template:
        return []
    
    legs = []
    for leg_def in template['legs']:
        target_strike = spot_price * (1 + leg_def['offset'])
        
        # Find closest strike
        if leg_def['type'] == 'call':
            df = calls_df
        else:
            df = puts_df
        
        if 'strike' not in df.columns or df.empty:
            continue
        
        closest_idx = (df['strike'] - target_strike).abs().idxmin()
        option = df.loc[closest_idx]
        
        leg = StrategyLeg(
            option_type=leg_def['type'],
            strike=option['strike'],
            expiration=expiration,
            quantity=leg_def['qty'],
            premium=option.get('lastPrice', option.get('mid', 0)),
            delta=option.get('delta', 0) * leg_def['qty'],
            gamma=option.get('gamma', 0) * abs(leg_def['qty']),
            theta=option.get('theta', 0) * leg_def['qty'],
            vega=option.get('vega', 0) * abs(leg_def['qty']),
        )
        legs.append(leg)
    
    return legs

# ============================================================
# ITEM 78: Auto-suggest Optimal Strikes
# ============================================================
def suggest_optimal_strikes(
    spot_price: float,
    iv: float,
    dte: int,
    risk_tolerance: str = 'moderate',  # conservative, moderate, aggressive
    outlook: str = 'neutral'  # bullish, bearish, neutral, volatile
) -> Dict[str, float]:
    """Suggest optimal strikes based on parameters."""
    
    # Expected move based on IV
    expected_move = spot_price * iv * np.sqrt(dte / 365)
    
    # Risk multipliers
    risk_mult = {'conservative': 1.5, 'moderate': 1.0, 'aggressive': 0.7}
    mult = risk_mult.get(risk_tolerance, 1.0)
    
    suggestions = {
        'atm_strike': round(spot_price, 0),
        'expected_move': expected_move,
    }
    
    if outlook in ['neutral', 'volatile']:
        suggestions.update({
            'short_put_strike': round(spot_price - expected_move * mult, 0),
            'short_call_strike': round(spot_price + expected_move * mult, 0),
            'long_put_strike': round(spot_price - expected_move * mult * 1.5, 0),
            'long_call_strike': round(spot_price + expected_move * mult * 1.5, 0),
        })
    elif outlook == 'bullish':
        suggestions.update({
            'long_strike': round(spot_price * 0.98, 0),
            'short_strike': round(spot_price * 1.05, 0),
        })
    elif outlook == 'bearish':
        suggestions.update({
            'long_strike': round(spot_price * 1.02, 0),
            'short_strike': round(spot_price * 0.95, 0),
        })
    
    return suggestions

# ============================================================
# ITEM 80: What-If Analysis
# ============================================================
def what_if_analysis(
    strategy: Strategy,
    price_range: Tuple[float, float],
    vol_changes: List[float] = [-0.2, -0.1, 0, 0.1, 0.2],
    time_decay_days: List[int] = [0, 7, 14, 30]
) -> pd.DataFrame:
    """Run what-if analysis on a strategy."""
    results = []
    
    prices = np.linspace(price_range[0], price_range[1], 50)
    
    for price in prices:
        for vol_change in vol_changes:
            for days in time_decay_days:
                pnl = calculate_strategy_pnl(strategy, price, vol_change, days)
                results.append({
                    'price': price,
                    'vol_change': vol_change,
                    'days_elapsed': days,
                    'pnl': pnl
                })
    
    return pd.DataFrame(results)

def calculate_strategy_pnl(
    strategy: Strategy,
    new_price: float,
    vol_change: float = 0,
    days_elapsed: int = 0
) -> float:
    """Calculate strategy P&L at a given price."""
    pnl = 0
    
    for leg in strategy.legs:
        # Intrinsic value at new price
        if leg.option_type == 'call':
            intrinsic = max(0, new_price - leg.strike)
        else:
            intrinsic = max(0, leg.strike - new_price)
        
        # Simplified P&L (ignores time value decay properly)
        leg_pnl = (intrinsic - leg.premium) * leg.quantity * 100
        
        # Add delta P&L for price change
        price_change = new_price - strategy.spot_price
        delta_pnl = leg.delta * price_change * 100
        
        # Add theta decay
        theta_cost = leg.theta * days_elapsed
        
        # Add vega for vol change
        vega_pnl = leg.vega * (vol_change * 100)
        
        pnl += leg_pnl + theta_cost + vega_pnl
    
    return pnl

# ============================================================
# ITEM 88: Strategy Heat Map
# ============================================================
def create_strategy_heatmap(what_if_df: pd.DataFrame) -> go.Figure:
    """Create P&L heatmap by price and time."""
    pivot = what_if_df[what_if_df['vol_change'] == 0].pivot_table(
        values='pnl',
        index='price',
        columns='days_elapsed',
        aggfunc='mean'
    )
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=[f"T+{d}" for d in pivot.columns],
        y=[f"${p:.0f}" for p in pivot.index],
        colorscale='RdYlGn',
        zmid=0,
        colorbar=dict(title="P&L ($)")
    ))
    
    fig.update_layout(
        title="Strategy P&L Heat Map",
        xaxis_title="Time",
        yaxis_title="Price",
        height=400
    )
    
    return fig

# ============================================================
# ITEM 89: Breakeven Visualizer
# ============================================================
def calculate_breakevens(strategy: Strategy) -> List[float]:
    """Calculate breakeven points for a strategy."""
    # Net premium
    net_premium = sum(leg.premium * leg.quantity * 100 for leg in strategy.legs)
    
    breakevens = []
    
    # Check strikes for breakeven
    strikes = sorted(set(leg.strike for leg in strategy.legs))
    
    # Add boundaries
    price_range = np.linspace(min(strikes) * 0.8, max(strikes) * 1.2, 1000)
    
    prev_pnl = None
    for price in price_range:
        pnl = calculate_strategy_pnl(strategy, price)
        
        if prev_pnl is not None:
            # Check for sign change (breakeven)
            if (prev_pnl < 0 and pnl >= 0) or (prev_pnl >= 0 and pnl < 0):
                breakevens.append(price)
        
        prev_pnl = pnl
    
    return breakevens

def create_payoff_diagram(strategy: Strategy) -> go.Figure:
    """Create payoff diagram with breakevens and probability zones."""
    strikes = [leg.strike for leg in strategy.legs]
    min_price = min(strikes) * 0.8
    max_price = max(strikes) * 1.2
    
    prices = np.linspace(min_price, max_price, 200)
    pnls = [calculate_strategy_pnl(strategy, p) for p in prices]
    
    breakevens = calculate_breakevens(strategy)
    
    fig = go.Figure()
    
    # P&L line
    colors = ['#28a745' if p >= 0 else '#dc3545' for p in pnls]
    
    fig.add_trace(go.Scatter(
        x=prices,
        y=pnls,
        mode='lines',
        name='P&L',
        line=dict(width=2),
        fill='tozeroy',
        fillcolor='rgba(40, 167, 69, 0.2)'
    ))
    
    # Zero line
    fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1)
    
    # Spot price line
    fig.add_vline(x=strategy.spot_price, line_dash="dash", line_color="blue",
                 annotation_text=f"Spot: ${strategy.spot_price:.2f}")
    
    # Breakeven points
    for be in breakevens:
        fig.add_vline(x=be, line_dash="dot", line_color="orange",
                     annotation_text=f"BE: ${be:.2f}")
    
    # Strike markers
    for leg in strategy.legs:
        marker_color = '#28a745' if leg.quantity > 0 else '#dc3545'
        fig.add_trace(go.Scatter(
            x=[leg.strike],
            y=[calculate_strategy_pnl(strategy, leg.strike)],
            mode='markers',
            marker=dict(size=12, color=marker_color, symbol='diamond'),
            name=f"{'Long' if leg.quantity > 0 else 'Short'} {leg.option_type.title()} ${leg.strike}"
        ))
    
    # Max profit/loss annotations
    max_profit = max(pnls)
    max_loss = min(pnls)
    
    fig.add_annotation(
        x=prices[pnls.index(max_profit)],
        y=max_profit,
        text=f"Max Profit: ${max_profit:,.0f}",
        showarrow=True,
        arrowhead=1
    )
    
    fig.add_annotation(
        x=prices[pnls.index(max_loss)],
        y=max_loss,
        text=f"Max Loss: ${max_loss:,.0f}",
        showarrow=True,
        arrowhead=1
    )
    
    fig.update_layout(
        title=f"Payoff Diagram: {strategy.name}",
        xaxis_title="Stock Price at Expiration",
        yaxis_title="Profit/Loss ($)",
        height=450,
        showlegend=True
    )
    
    return fig

# ============================================================
# ITEM 84: Risk/Reward Display
# ============================================================
def calculate_risk_reward(strategy: Strategy) -> Dict[str, Any]:
    """Calculate risk/reward metrics for strategy."""
    strikes = [leg.strike for leg in strategy.legs]
    prices = np.linspace(min(strikes) * 0.5, max(strikes) * 1.5, 500)
    pnls = [calculate_strategy_pnl(strategy, p) for p in prices]
    
    max_profit = max(pnls)
    max_loss = min(pnls)
    
    # Risk/Reward Ratio
    rr_ratio = abs(max_profit / max_loss) if max_loss != 0 else float('inf')
    
    # Expected value (simplified)
    avg_pnl = np.mean(pnls)
    
    return {
        'max_profit': max_profit,
        'max_loss': max_loss,
        'risk_reward_ratio': rr_ratio,
        'avg_pnl': avg_pnl,
        'profit_probability': sum(1 for p in pnls if p > 0) / len(pnls) * 100
    }

def create_risk_reward_card(metrics: Dict[str, Any]) -> dbc.Card:
    """Create risk/reward display card."""
    rr = metrics['risk_reward_ratio']
    rr_color = '#28a745' if rr >= 1 else '#dc3545'
    
    return dbc.Card([
        dbc.CardHeader("Risk/Reward Analysis"),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H4(f"${metrics['max_profit']:,.0f}", className="text-success mb-0"),
                        html.Small("Max Profit", className="text-muted")
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.H4(f"${metrics['max_loss']:,.0f}", className="text-danger mb-0"),
                        html.Small("Max Loss", className="text-muted")
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.H4(f"{rr:.2f}", style={"color": rr_color}, className="mb-0"),
                        html.Small("R/R Ratio", className="text-muted")
                    ], className="text-center")
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.H4(f"{metrics['profit_probability']:.0f}%", className="mb-0"),
                        html.Small("PoP", className="text-muted")
                    ], className="text-center")
                ], width=3),
            ])
        ])
    ], className="mb-3")

# ============================================================
# Strategy Builder UI
# ============================================================
def create_strategy_builder_panel() -> html.Div:
    """Create the strategy builder panel."""
    return html.Div([
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-tools me-2"),
                "Strategy Builder Pro"
            ]),
            dbc.CardBody([
                # Template selector
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Strategy Template"),
                        dbc.Select(
                            id="strategy-template-select",
                            options=[
                                {"label": t['name'], "value": k}
                                for k, t in STRATEGY_TEMPLATES.items()
                            ],
                            placeholder="Select template..."
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Risk Tolerance"),
                        dbc.Select(
                            id="risk-tolerance-select",
                            options=[
                                {"label": "Conservative", "value": "conservative"},
                                {"label": "Moderate", "value": "moderate"},
                                {"label": "Aggressive", "value": "aggressive"},
                            ],
                            value="moderate"
                        )
                    ], width=4),
                    dbc.Col([
                        dbc.Label("Market Outlook"),
                        dbc.Select(
                            id="market-outlook-select",
                            options=[
                                {"label": "Bullish", "value": "bullish"},
                                {"label": "Bearish", "value": "bearish"},
                                {"label": "Neutral", "value": "neutral"},
                                {"label": "Volatile", "value": "volatile"},
                            ],
                            value="neutral"
                        )
                    ], width=4),
                ], className="mb-3"),
                
                # Legs editor placeholder
                html.Div(id="strategy-legs-editor", className="mb-3"),
                
                # Action buttons
                dbc.ButtonGroup([
                    create_button(
                        button_id="auto-suggest-btn",
                        text=[html.I(className="fas fa-magic me-2"), "Auto-Suggest Strikes"],
                        variant="secondary"
                    ),
                    create_button(
                        button_id="calculate-strategy-btn",
                        text=[html.I(className="fas fa-calculator me-2"), "Calculate"],
                        variant="primary"
                    ),
                    create_button(
                        button_id="backtest-strategy-btn",
                        text=[html.I(className="fas fa-play me-2"), "Backtest"],
                        variant="success"
                    ),
                ], className="mb-3"),
                
                # Results area
                html.Div(id="strategy-results-area")
            ])
        ], **{'data-test-id': 'strategy-builder-card'})
    ], **{'data-test-id': 'strategy-builder-panel'})


__all__ = [
    'StrategyType',
    'StrategyLeg',
    'Strategy',
    'STRATEGY_TEMPLATES',
    'apply_template',
    'suggest_optimal_strikes',
    'what_if_analysis',
    'calculate_strategy_pnl',
    'create_strategy_heatmap',
    'calculate_breakevens',
    'create_payoff_diagram',
    'calculate_risk_reward',
    'create_risk_reward_card',
    'create_strategy_builder_panel',
]
