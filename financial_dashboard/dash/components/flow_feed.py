"""
Whale Stream Component - Phase 3: The Cockpit
==============================================
Filtered options flow feed showing only "whale" trades (Premium > $50k).

Features:
- Real-time flow filtering
- Color-coded by option type (Calls=Green, Puts=Red)
- Premium threshold filtering
- Sortable by timestamp, premium, size
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
import pandas as pd

from dash import html, dash_table
import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)


# =============================================================================
# ALPACA DARK THEME
# =============================================================================

ALPACA_DARK = {
    "bg": "#0D1117",
    "paper": "#161B22",
    "bg_tertiary": "#21262D",
    "gold": "#F5C211",
    "text": "#E6EDF3",
    "text_secondary": "#8B949E",
    "grid": "#30363D",
    "success": "#3FB950",
    "danger": "#F85149",
    "border": "#30363D",
}


# =============================================================================
# FLOW FILTERING
# =============================================================================

def filter_whale_trades(flow_data: List[Dict[str, Any]], 
                       min_premium: float = 50000) -> List[Dict[str, Any]]:
    """
    Filter options flow for "whale" trades.
    
    Args:
        flow_data: List of flow records with 'premium', 'size', 'type', etc.
        min_premium: Minimum premium threshold (default $50k)
        
    Returns:
        Filtered list of whale trades
    """
    if not flow_data:
        return []
    
    whales = []
    for trade in flow_data:
        premium = trade.get('premium', 0)
        if isinstance(premium, str):
            # Handle string premiums like "$12.50"
            premium = float(premium.replace('$', '').replace(',', ''))
        
        if premium >= min_premium:
            whales.append(trade)
    
    # Sort by premium descending
    whales.sort(key=lambda x: x.get('premium', 0), reverse=True)
    
    return whales


def classify_flow_sentiment(flow_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Classify overall flow sentiment from whale trades.
    
    Returns:
        {
            'call_volume': int,
            'put_volume': int,
            'call_premium': float,
            'put_premium': float,
            'sentiment': 'Bullish' | 'Bearish' | 'Neutral'
        }
    """
    call_vol = 0
    put_vol = 0
    call_prem = 0.0
    put_prem = 0.0
    
    for trade in flow_data:
        size = trade.get('size', 0)
        premium = trade.get('premium', 0)
        opt_type = trade.get('type', '').upper()
        
        if 'C' in opt_type or 'CALL' in opt_type:
            call_vol += size
            call_prem += premium
        elif 'P' in opt_type or 'PUT' in opt_type:
            put_vol += size
            put_prem += premium
    
    # Determine sentiment
    if call_prem > put_prem * 1.2:
        sentiment = 'Bullish'
    elif put_prem > call_prem * 1.2:
        sentiment = 'Bearish'
    else:
        sentiment = 'Neutral'
    
    return {
        'call_volume': call_vol,
        'put_volume': put_vol,
        'call_premium': call_prem,
        'put_premium': put_prem,
        'sentiment': sentiment
    }


# =============================================================================
# WHALE STREAM UI COMPONENT
# =============================================================================

def create_whale_stream(flow_data: Optional[List[Dict[str, Any]]] = None,
                       min_premium: float = 50000,
                       max_rows: int = 20,
                       component_id: str = "whale-stream-table") -> html.Div:
    """
    Create Whale Stream component with filtered flow table.
    
    Phase 3: The Cockpit - High-value options flow only.
    
    Args:
        flow_data: Raw flow data
        min_premium: Minimum premium threshold
        max_rows: Maximum rows to display
        component_id: Unique ID for the table
        
    Returns:
        Styled Dash component with DataTable
    """
    # Filter for whales
    if flow_data:
        whales = filter_whale_trades(flow_data, min_premium)
    else:
        # Mock data for initial render
        whales = _generate_mock_whale_trades()
    
    # Limit rows
    whales = whales[:max_rows]
    
    # Get sentiment
    sentiment_data = classify_flow_sentiment(whales)
    
    # Format for display
    table_data = []
    for trade in whales:
        table_data.append({
            'time': trade.get('time', ''),
            'symbol': trade.get('symbol', ''),
            'type': trade.get('type', ''),
            'strike': f"${trade.get('strike', 0):.0f}",
            'expiry': trade.get('expiry', ''),
            'size': f"{trade.get('size', 0):,}",
            'premium': f"${trade.get('premium', 0):,.0f}",
            'side': trade.get('side', '')
        })
    
    # Define columns
    columns = [
        {"name": "Time", "id": "time"},
        {"name": "Symbol", "id": "symbol"},
        {"name": "Type", "id": "type"},
        {"name": "Strike", "id": "strike"},
        {"name": "Expiry", "id": "expiry"},
        {"name": "Size", "id": "size"},
        {"name": "Premium", "id": "premium"},
        {"name": "Side", "id": "side"}
    ]
    
    return html.Div([
        # Header with sentiment indicator
        html.Div([
            html.Span("🐋 Whale Stream", style={
                'fontSize': '14px',
                'fontWeight': '600',
                'color': ALPACA_DARK['text']
            }),
            dbc.Badge(
                f"${min_premium/1000:.0f}K+ Premium",
                color="warning",
                className="ms-2",
                style={'fontSize': '10px'}
            ),
            html.Div([
                html.Span(f"Sentiment: ", style={
                    'fontSize': '11px',
                    'color': ALPACA_DARK['text_secondary']
                }),
                html.Span(sentiment_data['sentiment'], style={
                    'fontSize': '11px',
                    'fontWeight': 'bold',
                    'color': (
                        ALPACA_DARK['success'] if sentiment_data['sentiment'] == 'Bullish'
                        else ALPACA_DARK['danger'] if sentiment_data['sentiment'] == 'Bearish'
                        else ALPACA_DARK['text_secondary']
                    )
                })
            ], style={'marginLeft': 'auto'})
        ], style={
            'display': 'flex',
            'alignItems': 'center',
            'marginBottom': '12px',
            'paddingBottom': '8px',
            'borderBottom': f"2px solid {ALPACA_DARK['gold']}"
        }),
        
        # Data Table
        dash_table.DataTable(
            id=component_id,
            columns=columns,
            data=table_data,
            style_table={
                'overflowY': 'auto',
                'maxHeight': '400px',
                'backgroundColor': ALPACA_DARK['paper'],
            },
            style_header={
                'backgroundColor': ALPACA_DARK['bg_tertiary'],
                'color': ALPACA_DARK['text_secondary'],
                'fontWeight': 'bold',
                'fontSize': '11px',
                'textTransform': 'uppercase',
                'borderBottom': f"1px solid {ALPACA_DARK['border']}",
                'padding': '8px'
            },
            style_data={
                'backgroundColor': ALPACA_DARK['paper'],
                'color': ALPACA_DARK['text'],
                'fontSize': '12px',
                'fontFamily': "'JetBrains Mono', monospace",
                'borderBottom': f"1px solid {ALPACA_DARK['border']}",
                'padding': '8px'
            },
            style_cell={
                'textAlign': 'left',
                'whiteSpace': 'nowrap',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'maxWidth': '120px'
            },
            style_data_conditional=[
                # Alternate row colors
                {
                    'if': {'row_index': 'odd'},
                    'backgroundColor': ALPACA_DARK['bg_tertiary']
                },
                # Green for CALL types
                {
                    'if': {
                        'filter_query': '{type} contains "C" || {type} contains "CALL"',
                        'column_id': 'type'
                    },
                    'color': ALPACA_DARK['success'],
                    'fontWeight': 'bold'
                },
                # Red for PUT types
                {
                    'if': {
                        'filter_query': '{type} contains "P" || {type} contains "PUT"',
                        'column_id': 'type'
                    },
                    'color': ALPACA_DARK['danger'],
                    'fontWeight': 'bold'
                },
                # Highlight large premiums
                {
                    'if': {'column_id': 'premium'},
                    'color': ALPACA_DARK['gold'],
                    'fontWeight': 'bold'
                }
            ],
            page_action='none',  # Show all rows
            sort_action='native',
            sort_mode='multi',
            filter_action='native'
        )
    ], style={
        'backgroundColor': ALPACA_DARK['paper'],
        'padding': '16px',
        'borderRadius': '12px',
        'border': f"1px solid {ALPACA_DARK['grid']}",
        'height': '100%'
    })


def _generate_mock_whale_trades() -> List[Dict[str, Any]]:
    """Generate mock whale trades for testing."""
    import random
    from datetime import datetime, timedelta
    
    symbols = ['SPY', 'QQQ', 'NVDA', 'TSLA', 'AAPL']
    types = ['CALL', 'PUT']
    sides = ['BUY', 'SELL']
    
    trades = []
    base_time = datetime.now()
    
    for i in range(15):
        symbol = random.choice(symbols)
        opt_type = random.choice(types)
        
        # Generate realistic strikes
        if symbol == 'SPY':
            strike = random.choice(range(440, 460, 5))
        elif symbol == 'NVDA':
            strike = random.choice(range(130, 150, 5))
        elif symbol == 'TSLA':
            strike = random.choice(range(240, 270, 10))
        else:
            strike = random.choice(range(180, 200, 5))
        
        # Generate realistic premiums
        size = random.randint(50, 500) * 10
        price_per_contract = random.uniform(3, 20)
        premium = size * price_per_contract * 100  # Convert to dollars
        
        # Ensure it's a whale trade
        if premium < 50000:
            premium = random.uniform(50000, 500000)
        
        trade_time = base_time - timedelta(minutes=random.randint(1, 120))
        
        trades.append({
            'time': trade_time.strftime('%H:%M:%S'),
            'symbol': symbol,
            'type': opt_type,
            'strike': strike,
            'expiry': '2026-01-31',
            'size': size,
            'premium': premium,
            'side': random.choice(sides)
        })
    
    # Sort by premium
    trades.sort(key=lambda x: x['premium'], reverse=True)
    
    return trades


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Whale Stream Component Test")
    print("=" * 60)
    
    # Generate mock data
    mock_trades = _generate_mock_whale_trades()
    
    print(f"\n✅ Generated {len(mock_trades)} mock whale trades")
    
    # Filter
    whales = filter_whale_trades(mock_trades, min_premium=100000)
    print(f"   Filtered to {len(whales)} trades with premium > $100k")
    
    # Sentiment
    sentiment = classify_flow_sentiment(mock_trades)
    print(f"\n📊 Flow Sentiment:")
    print(f"   Calls: {sentiment['call_volume']:,} contracts, ${sentiment['call_premium']:,.0f}")
    print(f"   Puts: {sentiment['put_volume']:,} contracts, ${sentiment['put_premium']:,.0f}")
    print(f"   Overall: {sentiment['sentiment']}")
    
    # Top 3 trades
    print(f"\n🐋 Top 3 Whale Trades:")
    for i, trade in enumerate(mock_trades[:3], 1):
        print(f"   {i}. {trade['symbol']} {trade['type']} ${trade['strike']} - ${trade['premium']:,.0f}")
    
    print("\n" + "=" * 60)

