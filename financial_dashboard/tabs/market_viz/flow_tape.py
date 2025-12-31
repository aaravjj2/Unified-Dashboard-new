"""
Smart Flow Tape Component
Phase 6 - Agent-Viz

Real-time options flow feed with highlighting:
- Cost > $50k: Whale trades (highlighted row)
- Sentiment = Bullish: Green row
- Sentiment = Bearish: Red row
"""

import logging
import pandas as pd
import numpy as np
from dash import html, dash_table
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Component ID
FLOW_TABLE_ID = "table-flow"

# Alpaca Dark Theme Colors
ALPACA_DARK = {
    "bg": "#1E1E1E",
    "paper": "#252525",
    "accent": "#F5C211",
    "positive": "#00C853",
    "negative": "#FF5252",
    "text": "#E0E0E0",
    "grid": "#333333",
    "whale_bg": "#2E1A47",  # Purple tint for whale trades
    "bullish_bg": "#1B3D2F",  # Green tint for bullish
    "bearish_bg": "#3D1B1B",  # Red tint for bearish
}

# Flow tape columns
FLOW_COLUMNS = [
    {"name": "Time", "id": "time", "type": "text"},
    {"name": "Symbol", "id": "symbol", "type": "text"},
    {"name": "C/P", "id": "type", "type": "text"},
    {"name": "Strike", "id": "strike", "type": "numeric", "format": {"specifier": "$,.0f"}},
    {"name": "Expiry", "id": "expiry", "type": "text"},
    {"name": "Price", "id": "price", "type": "numeric", "format": {"specifier": "$,.2f"}},
    {"name": "Size", "id": "size", "type": "numeric", "format": {"specifier": ","}},
    {"name": "Cost", "id": "cost", "type": "numeric", "format": {"specifier": "$,.0f"}},
    {"name": "Spot", "id": "spot", "type": "numeric", "format": {"specifier": "$,.2f"}},
    {"name": "IV", "id": "iv", "type": "numeric", "format": {"specifier": ".1%"}},
    {"name": "Sentiment", "id": "sentiment", "type": "text"},
]


def calculate_sentiment(row: Dict[str, Any]) -> str:
    """
    Calculate trade sentiment based on price and spread.
    
    Logic:
    - If trade at/above ask: Aggressive buy (Bullish)
    - If trade at/below bid: Aggressive sell (Bearish)
    - If near mid: Neutral
    
    Args:
        row: Trade data dict
        
    Returns:
        Sentiment string: "Bullish", "Bearish", or "Neutral"
    """
    trade_price = row.get("price", 0)
    bid = row.get("bid", 0)
    ask = row.get("ask", 0)
    
    if bid <= 0 or ask <= 0:
        # Fallback to volume/OI ratio or random for mock
        return np.random.choice(["Bullish", "Bearish", "Neutral"], p=[0.45, 0.35, 0.20])
    
    mid = (bid + ask) / 2
    spread = ask - bid
    
    if spread <= 0:
        return "Neutral"
    
    # Determine sentiment based on trade location
    if trade_price >= ask - 0.1 * spread:
        return "Bullish"
    elif trade_price <= bid + 0.1 * spread:
        return "Bearish"
    else:
        return "Neutral"


def is_whale_trade(cost: float, threshold: float = 50000) -> bool:
    """
    Determine if trade qualifies as a whale trade.
    
    Args:
        cost: Total trade cost
        threshold: Whale threshold (default $50k)
        
    Returns:
        True if whale trade
    """
    return cost >= threshold


def process_flow_data(
    raw_trades: List[Dict[str, Any]],
    whale_threshold: float = 50000,
) -> pd.DataFrame:
    """
    Process raw trade data into flow tape format.
    
    Args:
        raw_trades: List of trade dicts
        whale_threshold: Cost threshold for whale trades
        
    Returns:
        DataFrame ready for display
    """
    if not raw_trades:
        return pd.DataFrame(columns=[c["id"] for c in FLOW_COLUMNS])
    
    processed = []
    for trade in raw_trades:
        cost = trade.get("cost", trade.get("price", 0) * trade.get("size", 0) * 100)
        sentiment = trade.get("sentiment") or calculate_sentiment(trade)
        
        processed.append({
            "time": trade.get("time", datetime.now().strftime("%H:%M:%S")),
            "symbol": trade.get("symbol", "SPY"),
            "type": trade.get("type", trade.get("option_type", "C")),
            "strike": trade.get("strike", 0),
            "expiry": trade.get("expiry", trade.get("expiration", "N/A")),
            "price": trade.get("price", 0),
            "size": trade.get("size", trade.get("volume", 0)),
            "cost": cost,
            "spot": trade.get("spot", trade.get("underlying_price", 0)),
            "iv": trade.get("iv", trade.get("implied_volatility", 0)),
            "sentiment": sentiment,
            "is_whale": is_whale_trade(cost, whale_threshold),
        })
    
    df = pd.DataFrame(processed)
    
    # Sort by time descending (most recent first)
    if "time" in df.columns:
        df = df.sort_values("time", ascending=False)
    
    return df


def get_row_style_conditions() -> List[Dict[str, Any]]:
    """
    Get conditional styling rules for flow tape rows.
    
    Returns:
        List of style conditions for dash_table
    """
    return [
        # Whale trades (highest priority)
        {
            "if": {
                "filter_query": "{cost} >= 50000",
            },
            "backgroundColor": ALPACA_DARK["whale_bg"],
            "fontWeight": "bold",
        },
        # Bullish sentiment
        {
            "if": {
                "filter_query": "{sentiment} = 'Bullish'",
            },
            "backgroundColor": ALPACA_DARK["bullish_bg"],
        },
        # Bearish sentiment
        {
            "if": {
                "filter_query": "{sentiment} = 'Bearish'",
            },
            "backgroundColor": ALPACA_DARK["bearish_bg"],
        },
        # Call options
        {
            "if": {
                "filter_query": "{type} = 'C' or {type} = 'CALL'",
                "column_id": "type",
            },
            "color": ALPACA_DARK["positive"],
        },
        # Put options
        {
            "if": {
                "filter_query": "{type} = 'P' or {type} = 'PUT'",
                "column_id": "type",
            },
            "color": ALPACA_DARK["negative"],
        },
    ]


def create_flow_tape(
    flow_data: Optional[List[Dict[str, Any]]] = None,
    max_rows: int = 50,
    title: str = "Smart Flow Tape",
) -> html.Div:
    """
    Create the complete flow tape component.
    
    Args:
        flow_data: List of trade dicts
        max_rows: Maximum rows to display
        title: Component title
        
    Returns:
        Dash HTML Div containing the flow table
    """
    # Process data
    if flow_data:
        df = process_flow_data(flow_data)
    else:
        df = pd.DataFrame(columns=[c["id"] for c in FLOW_COLUMNS])
    
    # Limit rows
    if len(df) > max_rows:
        df = df.head(max_rows)
    
    return html.Div(
        id="flow-tape-container",
        children=[
            # Header
            html.Div(
                children=[
                    html.H4(
                        title,
                        style={
                            "color": ALPACA_DARK["text"],
                            "margin": "0",
                            "display": "inline-block",
                        },
                    ),
                    html.Span(
                        " • Live",
                        style={
                            "color": ALPACA_DARK["positive"],
                            "fontSize": "12px",
                            "marginLeft": "10px",
                        },
                    ),
                ],
                style={"marginBottom": "15px"},
            ),
            # Legend
            html.Div(
                children=[
                    html.Span(
                        "🐋 Whale (>$50k)",
                        style={
                            "backgroundColor": ALPACA_DARK["whale_bg"],
                            "padding": "4px 8px",
                            "borderRadius": "4px",
                            "marginRight": "15px",
                            "fontSize": "11px",
                        },
                    ),
                    html.Span(
                        "📈 Bullish",
                        style={
                            "backgroundColor": ALPACA_DARK["bullish_bg"],
                            "padding": "4px 8px",
                            "borderRadius": "4px",
                            "marginRight": "15px",
                            "fontSize": "11px",
                        },
                    ),
                    html.Span(
                        "📉 Bearish",
                        style={
                            "backgroundColor": ALPACA_DARK["bearish_bg"],
                            "padding": "4px 8px",
                            "borderRadius": "4px",
                            "fontSize": "11px",
                        },
                    ),
                ],
                style={
                    "marginBottom": "15px",
                    "color": ALPACA_DARK["text"],
                },
            ),
            # Table
            dash_table.DataTable(
                id=FLOW_TABLE_ID,
                columns=FLOW_COLUMNS,
                data=df.to_dict("records") if not df.empty else [],
                page_size=20,
                page_action="native",
                sort_action="native",
                filter_action="native",
                style_table={
                    "overflowX": "auto",
                    "backgroundColor": ALPACA_DARK["bg"],
                },
                style_header={
                    "backgroundColor": ALPACA_DARK["paper"],
                    "color": ALPACA_DARK["text"],
                    "fontWeight": "bold",
                    "textAlign": "left",
                    "borderBottom": f"2px solid {ALPACA_DARK['accent']}",
                },
                style_cell={
                    "backgroundColor": ALPACA_DARK["bg"],
                    "color": ALPACA_DARK["text"],
                    "border": f"1px solid {ALPACA_DARK['grid']}",
                    "textAlign": "left",
                    "padding": "8px",
                    "fontSize": "13px",
                    "fontFamily": "monospace",
                },
                style_data_conditional=get_row_style_conditions(),
                style_filter={
                    "backgroundColor": ALPACA_DARK["paper"],
                    "color": ALPACA_DARK["text"],
                },
            ),
        ],
        style={
            "backgroundColor": ALPACA_DARK["paper"],
            "borderRadius": "8px",
            "padding": "15px",
        },
    )


def generate_mock_flow_data(
    num_trades: int = 30,
    ticker: str = "SPY",
    spot_price: float = 450.0,
) -> List[Dict[str, Any]]:
    """
    Generate mock flow data for testing/demo.
    
    Args:
        num_trades: Number of trades to generate
        ticker: Underlying symbol
        spot_price: Current spot price
        
    Returns:
        List of trade dicts
    """
    np.random.seed(42)  # VIZ_DETERMINISTIC
    
    trades = []
    base_time = datetime.now() - timedelta(minutes=num_trades)
    
    for i in range(num_trades):
        is_call = np.random.random() > 0.45
        
        # Generate strike around ATM
        moneyness = np.random.uniform(-0.1, 0.1)
        strike = round(spot_price * (1 + moneyness), 0)
        
        # Generate expiry (1-60 DTE)
        dte = np.random.choice([7, 14, 21, 30, 45, 60])
        expiry = (datetime.now() + timedelta(days=dte)).strftime("%Y-%m-%d")
        
        # Generate price and size
        # Whale trades occur ~10% of time
        is_whale = np.random.random() < 0.10
        
        base_price = max(0.10, abs(moneyness) * 10 + np.random.uniform(1, 5))
        if is_call and moneyness > 0:
            base_price *= 0.5  # OTM calls cheaper
        elif not is_call and moneyness < 0:
            base_price *= 0.5  # OTM puts cheaper
        
        if is_whale:
            size = np.random.randint(500, 2000)
        else:
            size = np.random.randint(10, 200)
        
        cost = base_price * size * 100
        
        # Generate sentiment
        sentiment = np.random.choice(
            ["Bullish", "Bearish", "Neutral"],
            p=[0.45, 0.35, 0.20]
        )
        
        trades.append({
            "time": (base_time + timedelta(minutes=i)).strftime("%H:%M:%S"),
            "symbol": ticker,
            "type": "C" if is_call else "P",
            "strike": strike,
            "expiry": expiry,
            "price": round(base_price, 2),
            "size": size,
            "cost": round(cost, 0),
            "spot": spot_price,
            "iv": round(0.15 + np.random.uniform(0, 0.25), 3),
            "sentiment": sentiment,
        })
    
    return trades


if __name__ == "__main__":
    # Test the component
    mock_data = generate_mock_flow_data()
    df = process_flow_data(mock_data)
    print(f"Generated {len(df)} trades")
    print(f"Whale trades: {df['is_whale'].sum()}")
    print(f"Bullish: {(df['sentiment'] == 'Bullish').sum()}")
    print(f"Bearish: {(df['sentiment'] == 'Bearish').sum()}")
