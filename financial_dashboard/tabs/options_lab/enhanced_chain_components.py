"""
Alpaca Options Lab - Enhanced Chain Viewer Components
Implements Items 1-25 from the 220 NEW IDEAS roadmap
"""

import dash_bootstrap_components as dbc
from dash import html, dcc
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

# ============================================================
# ITEM 1: Bid/Ask Spread Highlighting
# ============================================================
def get_spread_color(spread_pct: float) -> str:
    """Get color based on spread tightness."""
    if spread_pct < 0.5:
        return "#28a745"  # Green - tight
    elif spread_pct < 1.5:
        return "#ffc107"  # Yellow - moderate  
    elif spread_pct < 3.0:
        return "#fd7e14"  # Orange - wide
    else:
        return "#dc3545"  # Red - very wide

def create_spread_badge(bid: float, ask: float) -> html.Span:
    """Create spread badge with color coding."""
    if bid <= 0 or ask <= 0:
        return html.Span("N/A", className="badge bg-secondary")
    
    spread = ask - bid
    mid = (bid + ask) / 2
    spread_pct = (spread / mid) * 100
    
    color = get_spread_color(spread_pct)
    return html.Span(
        f"${spread:.2f} ({spread_pct:.1f}%)",
        className="badge",
        style={"backgroundColor": color, "color": "white", "fontSize": "11px"}
    )

# ============================================================
# ITEM 2: Real-Time Last Trade Indicator
# ============================================================
def create_last_trade_badge(last_price: float, prev_close: float) -> html.Div:
    """Create last trade indicator with change."""
    if last_price <= 0:
        return html.Span("--", className="badge bg-secondary")
    
    change = last_price - prev_close if prev_close > 0 else 0
    pct_change = (change / prev_close * 100) if prev_close > 0 else 0
    
    color = "#28a745" if change >= 0 else "#dc3545"
    arrow = "▲" if change >= 0 else "▼"
    
    return html.Span([
        f"${last_price:.2f} ",
        html.Span(f"{arrow} {abs(pct_change):.1f}%", style={"color": color})
    ], style={"fontSize": "12px"})

# ============================================================
# ITEM 3: Volume Spike Detection
# ============================================================
def detect_volume_spike(current_vol: int, avg_vol: int, threshold: float = 3.0) -> Optional[html.Span]:
    """Detect volume spikes (vol > threshold * avg)."""
    if avg_vol <= 0:
        return None
    
    ratio = current_vol / avg_vol
    if ratio >= threshold:
        return html.Span(
            f"🔥 {ratio:.1f}x",
            className="badge bg-danger ms-1",
            title=f"Volume spike: {current_vol:,} vs avg {avg_vol:,}"
        )
    return None

# ============================================================
# ITEM 5: Quick Filters
# ============================================================
def create_chain_filters() -> dbc.Card:
    """Create quick filter controls for chain viewer."""
    return dbc.Card([
        dbc.CardBody([
            html.H6("Quick Filters", className="mb-2"),
            dbc.Row([
                dbc.Col([
                    dbc.Checkbox(
                        id="filter-itm-only",
                        label="ITM Only",
                        className="me-2"
                    ),
                ], width=3),
                dbc.Col([
                    dbc.Checkbox(
                        id="filter-otm-only",
                        label="OTM Only",
                        className="me-2"
                    ),
                ], width=3),
                dbc.Col([
                    dbc.Checkbox(
                        id="filter-high-iv",
                        label="High IV (>50%)",
                        className="me-2"
                    ),
                ], width=3),
                dbc.Col([
                    dbc.Checkbox(
                        id="filter-liquid",
                        label="Liquid (OI>1K)",
                        className="me-2"
                    ),
                ], width=3),
            ]),
        ], className="py-2")
    ], className="mb-2")

# ============================================================
# ITEM 10: Quick Greeks Summary
# ============================================================
def create_greeks_summary(calls_df: pd.DataFrame, puts_df: pd.DataFrame) -> dbc.Card:
    """Create quick Greeks summary card."""
    try:
        # Aggregate Greeks
        total_call_delta = calls_df['delta'].sum() if 'delta' in calls_df else 0
        total_put_delta = puts_df['delta'].sum() if 'delta' in puts_df else 0
        net_delta = total_call_delta + total_put_delta
        
        total_gamma = (calls_df['gamma'].sum() if 'gamma' in calls_df else 0) + \
                     (puts_df['gamma'].sum() if 'gamma' in puts_df else 0)
        
        total_theta = (calls_df['theta'].sum() if 'theta' in calls_df else 0) + \
                     (puts_df['theta'].sum() if 'theta' in puts_df else 0)
        
        total_vega = (calls_df['vega'].sum() if 'vega' in calls_df else 0) + \
                    (puts_df['vega'].sum() if 'vega' in puts_df else 0)
        
    except Exception:
        net_delta = total_gamma = total_theta = total_vega = 0
    
    return dbc.Card([
        dbc.CardBody([
            html.H6("Greeks Summary", className="mb-2"),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Span("Net Δ: ", className="text-muted"),
                        html.Span(f"{net_delta:.2f}", 
                                 style={"color": "#28a745" if net_delta >= 0 else "#dc3545"})
                    ])
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Span("Γ: ", className="text-muted"),
                        html.Span(f"{total_gamma:.4f}")
                    ])
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Span("Θ: ", className="text-muted"),
                        html.Span(f"${total_theta:.2f}", 
                                 style={"color": "#dc3545" if total_theta < 0 else "#28a745"})
                    ])
                ], width=3),
                dbc.Col([
                    html.Div([
                        html.Span("ν: ", className="text-muted"),
                        html.Span(f"${total_vega:.2f}")
                    ])
                ], width=3),
            ])
        ], className="py-2")
    ], className="mb-2", style={"backgroundColor": "#f8f9fa"})

# ============================================================
# ITEM 17: Max Pain Indicator
# ============================================================
def calculate_max_pain(calls_df: pd.DataFrame, puts_df: pd.DataFrame) -> float:
    """Calculate max pain strike."""
    try:
        strikes = sorted(set(calls_df['strike'].unique()) | set(puts_df['strike'].unique()))
        
        min_pain = float('inf')
        max_pain_strike = strikes[len(strikes)//2] if strikes else 0
        
        for strike in strikes:
            # Calculate total pain at this strike
            call_oi = calls_df[calls_df['strike'] == strike]['openInterest'].sum() if 'openInterest' in calls_df else 0
            put_oi = puts_df[puts_df['strike'] == strike]['openInterest'].sum() if 'openInterest' in puts_df else 0
            
            call_pain = sum(
                max(0, strike - s) * calls_df[calls_df['strike'] == s]['openInterest'].sum()
                for s in strikes if s < strike
            )
            put_pain = sum(
                max(0, s - strike) * puts_df[puts_df['strike'] == s]['openInterest'].sum()
                for s in strikes if s > strike
            )
            
            total_pain = call_pain + put_pain
            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = strike
                
        return max_pain_strike
    except Exception:
        return 0

def create_max_pain_badge(max_pain: float, spot: float) -> html.Div:
    """Create max pain indicator badge."""
    diff = max_pain - spot
    pct_diff = (diff / spot * 100) if spot > 0 else 0
    
    return html.Div([
        html.Span("Max Pain: ", className="text-muted"),
        html.Span(f"${max_pain:.2f}", className="fw-bold"),
        html.Span(f" ({'+' if pct_diff >= 0 else ''}{pct_diff:.1f}%)", 
                 style={"color": "#28a745" if pct_diff >= 0 else "#dc3545", "fontSize": "11px"})
    ], className="mb-2")

# ============================================================
# ITEM 18: Put/Call Ratio Badge
# ============================================================
def calculate_put_call_ratio(calls_df: pd.DataFrame, puts_df: pd.DataFrame, metric: str = 'volume') -> float:
    """Calculate put/call ratio by volume or OI."""
    try:
        if metric == 'volume':
            call_vol = calls_df['volume'].sum() if 'volume' in calls_df else 0
            put_vol = puts_df['volume'].sum() if 'volume' in puts_df else 0
            return put_vol / call_vol if call_vol > 0 else 0
        else:  # OI
            call_oi = calls_df['openInterest'].sum() if 'openInterest' in calls_df else 0
            put_oi = puts_df['openInterest'].sum() if 'openInterest' in puts_df else 0
            return put_oi / call_oi if call_oi > 0 else 0
    except Exception:
        return 0

def create_pcr_badge(pcr: float) -> html.Span:
    """Create P/C ratio badge with sentiment indicator."""
    if pcr < 0.7:
        color = "#28a745"  # Bullish
        sentiment = "Bullish"
    elif pcr < 1.0:
        color = "#17a2b8"  # Neutral bullish
        sentiment = "Neutral"
    elif pcr < 1.3:
        color = "#ffc107"  # Neutral bearish
        sentiment = "Neutral"
    else:
        color = "#dc3545"  # Bearish
        sentiment = "Bearish"
    
    return html.Span([
        f"P/C: {pcr:.2f} ",
        html.Span(f"({sentiment})", style={"fontSize": "10px"})
    ], className="badge", style={"backgroundColor": color, "color": "white"})

# ============================================================
# ITEM 23: Probability of Profit (PoP)
# ============================================================
def calculate_pop(strike: float, spot: float, iv: float, dte: int, option_type: str) -> float:
    """Calculate probability of profit for option."""
    try:
        from scipy.stats import norm
        import math
        
        if iv <= 0 or dte <= 0:
            return 0
        
        t = dte / 365
        d2 = (math.log(spot / strike) - 0.5 * iv**2 * t) / (iv * math.sqrt(t))
        
        if option_type.lower() == 'call':
            return norm.cdf(d2) * 100
        else:
            return (1 - norm.cdf(d2)) * 100
    except Exception:
        return 0

# ============================================================
# ITEM 25: Unusual Activity Badge
# ============================================================
def detect_unusual_activity(volume: int, open_interest: int, threshold: float = 3.0) -> Optional[html.Span]:
    """Detect unusual activity (volume > threshold * OI)."""
    if open_interest <= 0:
        return None
    
    ratio = volume / open_interest
    if ratio >= threshold:
        return html.Span(
            f"⚡ UNUSUAL",
            className="badge bg-warning text-dark ms-1",
            title=f"Volume {volume:,} is {ratio:.1f}x of OI {open_interest:,}"
        )
    return None

# ============================================================
# Enhanced Chain Table Builder
# ============================================================
def build_enhanced_chain_table(
    calls_df: pd.DataFrame,
    puts_df: pd.DataFrame,
    spot_price: float,
    expiration: str
) -> html.Div:
    """Build enhanced chain viewer table with all improvements."""
    
    # Calculate metrics
    max_pain = calculate_max_pain(calls_df, puts_df)
    pcr = calculate_put_call_ratio(calls_df, puts_df)
    
    # Header with metrics
    header = dbc.Row([
        dbc.Col([
            create_max_pain_badge(max_pain, spot_price)
        ], width=4),
        dbc.Col([
            create_pcr_badge(pcr)
        ], width=4),
        dbc.Col([
            html.Span(f"Exp: {expiration}", className="text-muted")
        ], width=4, className="text-end"),
    ], className="mb-2")
    
    # Build table rows
    table_rows = []
    
    # Get all strikes
    all_strikes = sorted(set(
        list(calls_df['strike'].unique() if 'strike' in calls_df else []) +
        list(puts_df['strike'].unique() if 'strike' in puts_df else [])
    ))
    
    for strike in all_strikes:
        call_row = calls_df[calls_df['strike'] == strike].iloc[0] if len(calls_df[calls_df['strike'] == strike]) > 0 else None
        put_row = puts_df[puts_df['strike'] == strike].iloc[0] if len(puts_df[puts_df['strike'] == strike]) > 0 else None
        
        # Determine ITM/ATM/OTM
        is_call_itm = strike < spot_price
        is_put_itm = strike > spot_price
        is_atm = abs(strike - spot_price) / spot_price < 0.02
        
        strike_class = "fw-bold text-primary" if is_atm else ""
        
        # Build call side
        call_cells = _build_option_cells(call_row, "call", strike, spot_price) if call_row is not None else _empty_cells()
        
        # Strike column (center)
        strike_cell = html.Td([
            html.Span(f"${strike:.2f}", className=strike_class),
            html.Br(),
            html.Small("ATM", className="text-primary") if is_atm else 
            html.Small("ITM", className="text-success") if (is_call_itm and call_row is not None) else 
            html.Small("OTM", className="text-muted") if call_row is not None else ""
        ], className="text-center", style={"backgroundColor": "#f8f9fa"})
        
        # Build put side
        put_cells = _build_option_cells(put_row, "put", strike, spot_price) if put_row is not None else _empty_cells()
        
        row = html.Tr(call_cells + [strike_cell] + put_cells)
        table_rows.append(row)
    
    # Table header
    table_header = html.Thead(html.Tr([
        html.Th("Bid", className="text-end"),
        html.Th("Ask", className="text-end"),
        html.Th("Last", className="text-end"),
        html.Th("Vol", className="text-end"),
        html.Th("OI", className="text-end"),
        html.Th("IV", className="text-end"),
        html.Th("Delta", className="text-end"),
        html.Th("Strike", className="text-center", style={"backgroundColor": "#e9ecef"}),
        html.Th("Delta", className="text-start"),
        html.Th("IV", className="text-start"),
        html.Th("OI", className="text-start"),
        html.Th("Vol", className="text-start"),
        html.Th("Last", className="text-start"),
        html.Th("Ask", className="text-start"),
        html.Th("Bid", className="text-start"),
    ]))
    
    table = dbc.Table([
        table_header,
        html.Tbody(table_rows)
    ], bordered=True, hover=True, size="sm", className="chain-table")
    
    return html.Div([
        header,
        create_chain_filters(),
        create_greeks_summary(calls_df, puts_df),
        table
    ])

def _build_option_cells(row: pd.Series, option_type: str, strike: float, spot: float) -> List[html.Td]:
    """Build cells for one option."""
    try:
        bid = row.get('bid', 0)
        ask = row.get('ask', 0)
        last = row.get('lastPrice', row.get('last', 0))
        vol = int(row.get('volume', 0))
        oi = int(row.get('openInterest', 0))
        iv = row.get('impliedVolatility', row.get('iv', 0)) * 100
        delta = row.get('delta', 0)
        
        # Detect unusual activity
        unusual = detect_unusual_activity(vol, oi)
        
        cells = [
            html.Td(f"${bid:.2f}", className="text-end"),
            html.Td(f"${ask:.2f}", className="text-end"),
            html.Td(f"${last:.2f}", className="text-end"),
            html.Td([f"{vol:,}", unusual] if unusual else f"{vol:,}", className="text-end"),
            html.Td(f"{oi:,}", className="text-end"),
            html.Td(f"{iv:.1f}%", className="text-end"),
            html.Td(f"{delta:.2f}", className="text-end"),
        ]
        
        return cells if option_type == "call" else cells[::-1]
    except Exception:
        return _empty_cells()

def _empty_cells() -> List[html.Td]:
    """Return empty cells for missing option."""
    return [html.Td("--", className="text-muted") for _ in range(7)]


# ============================================================
# Export for use in callbacks
# ============================================================
__all__ = [
    'get_spread_color',
    'create_spread_badge',
    'create_last_trade_badge',
    'detect_volume_spike',
    'create_chain_filters',
    'create_greeks_summary',
    'calculate_max_pain',
    'create_max_pain_badge',
    'calculate_put_call_ratio',
    'create_pcr_badge',
    'calculate_pop',
    'detect_unusual_activity',
    'build_enhanced_chain_table',
]
