"""
Alpaca-Style Options Lab UI Components

Creates a clean, professional options chain display matching Alpaca's web interface.
Side-by-side calls/puts table with all Greeks, IV, OI, and volume.
"""

import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from typing import Dict, List, Optional
import pandas as pd
import logging

logger = logging.getLogger(__name__)


def create_alpaca_options_table(calls_df: pd.DataFrame, puts_df: pd.DataFrame, spot_price: float) -> html.Div:
    """
    Create Alpaca-style side-by-side options chain table.
    
    Args:
        calls_df: DataFrame with call options
        puts_df: DataFrame with put options
        spot_price: Current underlying price
        
    Returns:
        Dash Div component with formatted table
    """
    # Ensure DataFrames have required columns and correct types
    required_cols = ['strike', 'lastPrice', 'bid', 'ask', 'change', 'volume', 
                     'openInterest', 'impliedVolatility', 'delta']
    
    for col in required_cols:
        if col not in calls_df.columns:
            calls_df[col] = 0.0
        else:
            # Ensure numeric type
            calls_df[col] = pd.to_numeric(calls_df[col], errors='coerce').fillna(0.0)
            
        if col not in puts_df.columns:
            puts_df[col] = 0.0
        else:
            # Ensure numeric type
            puts_df[col] = pd.to_numeric(puts_df[col], errors='coerce').fillna(0.0)
    
    # Get unique strikes (union of calls and puts) - ensure they're floats
    all_strikes = sorted(set(list(map(float, calls_df['strike'].unique())) + list(map(float, puts_df['strike'].unique()))))
    
    # Build combined table data
    table_data = []
    
    for strike in all_strikes:
        # Get call data
        call_row = calls_df[calls_df['strike'] == strike]
        if not call_row.empty:
            call_row = call_row.iloc[0]
            call_oi = int(float(call_row['openInterest']))
            call_vol = int(float(call_row['volume']))
            call_delta_val = float(call_row['delta'])
            call_iv_val = float(call_row['impliedVolatility'])
            call_chg_val = float(call_row['change'])
            call_bid_val = float(call_row['bid'])
            call_ask_val = float(call_row['ask'])
            call_last_val = float(call_row['lastPrice'])
            
            call_delta = f"{call_delta_val:.3f}" if call_delta_val != 0 else "-"
            call_iv = f"{call_iv_val*100:.1f}%" if call_iv_val != 0 else "-"
            call_chg = f"{call_chg_val:.2f}" if call_chg_val != 0 else "-"
            call_bid = f"${call_bid_val:.2f}" if call_bid_val != 0 else "-"
            call_ask = f"${call_ask_val:.2f}" if call_ask_val != 0 else "-"
            call_last = f"${call_last_val:.2f}" if call_last_val != 0 else "-"
        else:
            call_oi = call_vol = "-"
            call_delta = call_iv = call_chg = call_bid = call_ask = call_last = "-"
        
        # Get put data
        put_row = puts_df[puts_df['strike'] == strike]
        if not put_row.empty:
            put_row = put_row.iloc[0]
            put_oi = int(float(put_row['openInterest']))
            put_vol = int(float(put_row['volume']))
            put_delta_val = float(put_row['delta'])
            put_iv_val = float(put_row['impliedVolatility'])
            put_chg_val = float(put_row['change'])
            put_bid_val = float(put_row['bid'])
            put_ask_val = float(put_row['ask'])
            put_last_val = float(put_row['lastPrice'])
            
            put_delta = f"{put_delta_val:.3f}" if put_delta_val != 0 else "-"
            put_iv = f"{put_iv_val*100:.1f}%" if put_iv_val != 0 else "-"
            put_chg = f"{put_chg_val:.2f}" if put_chg_val != 0 else "-"
            put_bid = f"${put_bid_val:.2f}" if put_bid_val != 0 else "-"
            put_ask = f"${put_ask_val:.2f}" if put_ask_val != 0 else "-"
            put_last = f"${put_last_val:.2f}" if put_last_val != 0 else "-"
        else:
            put_oi = put_vol = "-"
            put_delta = put_iv = put_chg = put_bid = put_ask = put_last = "-"
        
        # Highlight ATM strike
        is_atm = abs(float(strike) - float(spot_price)) < (all_strikes[1] - all_strikes[0]) if len(all_strikes) > 1 else False
        
        row = {
            'call_oi': call_oi,
            'call_vol': call_vol,
            'call_delta': call_delta,
            'call_iv': call_iv,
            'call_chg': call_chg,
            'call_bid': call_bid,
            'call_ask': call_ask,
            'call_last': call_last,
            'strike': f"${strike:.2f}",
            'put_last': put_last,
            'put_bid': put_bid,
            'put_ask': put_ask,
            'put_chg': put_chg,
            'put_iv': put_iv,
            'put_delta': put_delta,
            'put_vol': put_vol,
            'put_oi': put_oi,
            'is_atm': is_atm
        }
        
        table_data.append(row)
    
    # Create DataTable with Alpaca-style formatting + BUY buttons
    table = dash_table.DataTable(
        id='alpaca-options-table',
        data=table_data,
        columns=[
            # Calls (left side)
            {'name': 'OI', 'id': 'call_oi', 'type': 'numeric'},
            {'name': 'Vol', 'id': 'call_vol', 'type': 'numeric'},
            {'name': 'Delta', 'id': 'call_delta'},
            {'name': 'IV', 'id': 'call_iv'},
            {'name': 'Chg', 'id': 'call_chg'},
            {'name': 'Bid', 'id': 'call_bid'},
            {'name': 'Ask', 'id': 'call_ask'},
            {'name': 'Last', 'id': 'call_last'},
            
            # Strike (center)
            {'name': 'Strike', 'id': 'strike'},
            
            # Puts (right side)
            {'name': 'Last', 'id': 'put_last'},
            {'name': 'Bid', 'id': 'put_bid'},
            {'name': 'Ask', 'id': 'put_ask'},
            {'name': 'Chg', 'id': 'put_chg'},
            {'name': 'IV', 'id': 'put_iv'},
            {'name': 'Delta', 'id': 'put_delta'},
            {'name': 'Vol', 'id': 'put_vol'},
            {'name': 'OI', 'id': 'put_oi', 'type': 'numeric'},
        ],
        row_selectable='single',  # Enable row selection for buying
        style_table={
            'overflowX': 'auto',
            'maxHeight': '600px',
            'overflowY': 'auto'
        },
        style_header={
            'backgroundColor': '#1e2130',
            'color': 'white',
            'fontWeight': 'bold',
            'textAlign': 'center',
            'border': '1px solid #3d4050',
            'fontSize': '13px'
        },
        style_cell={
            'textAlign': 'center',
            'padding': '8px',
            'backgroundColor': '#2a2d3a',
            'color': '#e0e0e0',
            'border': '1px solid #3d4050',
            'fontSize': '12px',
            'fontFamily': 'monospace'
        },
        style_data_conditional=[
            # Highlight ATM row
            {
                'if': {'filter_query': '{is_atm} eq true'},
                'backgroundColor': '#3a3d4a',
                'fontWeight': 'bold'
            },
            # Call side (left) background
            {
                'if': {'column_id': ['call_oi', 'call_vol', 'call_delta', 'call_iv', 
                                     'call_chg', 'call_bid', 'call_ask', 'call_last']},
                'backgroundColor': '#2a3d2a'  # Slight green tint
            },
            # Put side (right) background
            {
                'if': {'column_id': ['put_last', 'put_bid', 'put_ask', 'put_chg', 
                                     'put_iv', 'put_delta', 'put_vol', 'put_oi']},
                'backgroundColor': '#3d2a2a'  # Slight red tint
            },
            # Strike column (center) - highlight
            {
                'if': {'column_id': 'strike'},
                'backgroundColor': '#35384a',
                'fontWeight': 'bold',
                'fontSize': '13px'
            },
            # Positive changes in green
            {
                'if': {
                    'filter_query': '{call_chg} > 0 || {put_chg} > 0',
                    'column_id': ['call_chg', 'put_chg']
                },
                'color': '#4caf50'
            },
            # Negative changes in red
            {
                'if': {
                    'filter_query': '{call_chg} < 0 || {put_chg} < 0',
                    'column_id': ['call_chg', 'put_chg']
                },
                'color': '#f44336'
            }
        ],
        fixed_rows={'headers': True},
        page_action='none',
    )
    
    # Create trade panel for selected option
    trade_panel = create_trade_panel()
    
    return html.Div([
        table,
        trade_panel
    ], style={'marginTop': '20px'})


def create_trade_panel() -> html.Div:
    """Create trade execution panel that appears when an option is selected."""
    return html.Div([
        html.Div(id='option-trade-panel', children=[
            dbc.Card([
                dbc.CardHeader([
                    html.H5("📊 Trade Selected Option", className="mb-0"),
                ], style={'backgroundColor': '#1e2130', 'color': '#ffffff'}),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("Option Type:", className="text-muted"),
                            dbc.RadioItems(
                                id='trade-option-type',
                                options=[
                                    {'label': '📈 CALL', 'value': 'call'},
                                    {'label': '📉 PUT', 'value': 'put'}
                                ],
                                value='call',
                                inline=True,
                                className="mb-2"
                            )
                        ], md=3),
                        dbc.Col([
                            html.Label("Action:", className="text-muted"),
                            dbc.RadioItems(
                                id='trade-action',
                                options=[
                                    {'label': '🟢 BUY', 'value': 'buy'},
                                    {'label': '🔴 SELL', 'value': 'sell'}
                                ],
                                value='buy',
                                inline=True,
                                className="mb-2"
                            )
                        ], md=3),
                        dbc.Col([
                            html.Label("Quantity:", className="text-muted"),
                            dbc.Input(
                                id='trade-quantity',
                                type='number',
                                value=1,
                                min=1,
                                max=100,
                                step=1,
                                style={'backgroundColor': '#2a2d3a', 'color': '#ffffff', 'border': '1px solid #3d4050'}
                            )
                        ], md=2),
                        dbc.Col([
                            html.Label("Order Type:", className="text-muted"),
                            dbc.Select(
                                id='trade-order-type',
                                options=[
                                    {'label': 'Market', 'value': 'market'},
                                    {'label': 'Limit', 'value': 'limit'}
                                ],
                                value='limit',
                                style={'backgroundColor': '#2a2d3a', 'color': '#ffffff', 'border': '1px solid #3d4050'}
                            )
                        ], md=2),
                        dbc.Col([
                            html.Label("Limit Price:", className="text-muted"),
                            dbc.Input(
                                id='trade-limit-price',
                                type='number',
                                placeholder='$0.00',
                                step=0.01,
                                style={'backgroundColor': '#2a2d3a', 'color': '#ffffff', 'border': '1px solid #3d4050'}
                            )
                        ], md=2),
                    ], className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.Div(id='trade-summary', children=[
                                html.Span("Select an option row above to trade", className="text-muted")
                            ])
                        ], md=8),
                        dbc.Col([
                            dbc.Button(
                                [html.I(className="bi bi-cart-check me-2"), "Execute Trade"],
                                id='execute-trade-btn',
                                color='success',
                                size='lg',
                                className="w-100",
                                disabled=True
                            )
                        ], md=4),
                    ]),
                    html.Div(id='trade-result', className="mt-3")
                ], style={'backgroundColor': '#2a2d3a'})
            ], style={'backgroundColor': '#1e2130', 'border': '1px solid #3d4050', 'marginTop': '20px'})
        ], style={'display': 'none'})  # Hidden by default, shown when row selected
    ])


def create_alpaca_header(ticker: str, spot_price: float, timestamp: str) -> html.Div:
    """
    Create Alpaca-style header with ticker and spot price.
    
    Args:
        ticker: Stock symbol
        spot_price: Current price
        timestamp: Data timestamp
        
    Returns:
        Dash Div with header
    """
    return html.Div([
        html.Div([
            html.H3(ticker, style={
                'display': 'inline-block',
                'marginRight': '20px',
                'color': '#ffffff',
                'fontSize': '28px',
                'fontWeight': 'bold'
            }),
            html.Div([
                html.Span("Underlying Share Price: ", style={
                    'color': '#9ca3af',
                    'fontSize': '14px',
                    'marginRight': '8px'
                }),
                html.Span(f"${spot_price:.2f}", style={
                    'color': '#4caf50',
                    'fontSize': '24px',
                    'fontWeight': 'bold'
                })
            ], style={'display': 'inline-block', 'verticalAlign': 'middle'}),
            html.Div([
                html.Small(f"Updated: {timestamp}", style={
                    'color': '#6b7280',
                    'fontSize': '11px',
                    'marginLeft': '20px'
                })
            ], style={'display': 'inline-block', 'verticalAlign': 'middle'})
        ], style={
            'padding': '20px',
            'backgroundColor': '#1e2130',
            'borderRadius': '8px',
            'marginBottom': '20px'
        })
    ])


def create_expiration_selector(expirations: List[str], selected: Optional[str] = None) -> html.Div:
    """
    Create Alpaca-style expiration date selector.
    
    Args:
        expirations: List of expiration dates
        selected: Currently selected expiration
        
    Returns:
        Dash Div with dropdown
    """
    if not expirations:
        expirations = []
    
    if selected is None and expirations:
        selected = expirations[0]
    
    return html.Div([
        html.Label("Expiration Date:", style={
            'color': '#9ca3af',
            'fontSize': '13px',
            'fontWeight': 'bold',
            'marginRight': '10px',
            'display': 'inline-block'
        }),
        dcc.Dropdown(
            id='alpaca-expiration-selector',  # Internal ID - synced to alpaca-expiration-dropdown
            options=[{'label': exp, 'value': exp} for exp in expirations],
            value=selected,
            clearable=False,
            style={
                'width': '200px',
                'display': 'inline-block',
                'verticalAlign': 'middle',
                'backgroundColor': '#2a2d3a',
                'color': '#ffffff'
            },
            className='alpaca-dropdown'
        )
    ], style={
        'marginBottom': '20px',
        'padding': '15px',
        'backgroundColor': '#1e2130',
        'borderRadius': '8px'
    })


def create_alpaca_layout(ticker: str = "SPY") -> html.Div:
    """
    Create complete Alpaca-style Options Lab layout.
    
    Args:
        ticker: Default ticker symbol
        
    Returns:
        Complete layout component
    """
    return html.Div([
        # Ticker input
        html.Div([
            html.Label("Symbol:", style={
                'color': '#9ca3af',
                'fontSize': '13px',
                'fontWeight': 'bold',
                'marginRight': '10px',
                'display': 'inline-block'
            }),
            dcc.Input(
                id='alpaca-ticker-input',
                type='text',
                value=ticker,
                placeholder='Enter ticker...',
                style={
                    'width': '150px',
                    'padding': '8px',
                    'backgroundColor': '#2a2d3a',
                    'color': '#ffffff',
                    'border': '1px solid #3d4050',
                    'borderRadius': '4px',
                    'fontSize': '14px',
                    'marginRight': '10px'
                }
            ),
            html.Button(
                "Load Chain",
                id='alpaca-load-button',
                n_clicks=0,
                style={
                    'padding': '8px 20px',
                    'backgroundColor': '#4caf50',
                    'color': 'white',
                    'border': 'none',
                    'borderRadius': '4px',
                    'cursor': 'pointer',
                    'fontSize': '14px',
                    'fontWeight': 'bold'
                }
            )
        ], style={
            'marginBottom': '20px',
            'padding': '15px',
            'backgroundColor': '#1e2130',
            'borderRadius': '8px'
        }),
        
        # Loading spinner
        dcc.Loading(
            id='alpaca-loading',
            type='circle',
            children=[
                # Header (populated by callback)
                html.Div(id='alpaca-header-container'),
                
                # Expiration selector (populated by callback)
                html.Div(id='alpaca-expiration-container'),
                
                # Export buttons
                html.Div([
                    html.Button(
                        "📥 Export CSV",
                        id='alpaca-export-csv-btn',
                        n_clicks=0,
                        style={
                            'padding': '8px 16px',
                            'backgroundColor': '#2196F3',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '4px',
                            'cursor': 'pointer',
                            'fontSize': '13px',
                            'marginRight': '10px'
                        }
                    ),
                    html.Button(
                        "📥 Export JSON",
                        id='alpaca-export-json-btn',
                        n_clicks=0,
                        style={
                            'padding': '8px 16px',
                            'backgroundColor': '#9C27B0',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '4px',
                            'cursor': 'pointer',
                            'fontSize': '13px',
                            'marginRight': '10px'
                        }
                    ),
                    html.Button(
                        "🔄 Refresh",
                        id='alpaca-refresh-btn',
                        n_clicks=0,
                        style={
                            'padding': '8px 16px',
                            'backgroundColor': '#FF9800',
                            'color': 'white',
                            'border': 'none',
                            'borderRadius': '4px',
                            'cursor': 'pointer',
                            'fontSize': '13px'
                        }
                    ),
                ], id='alpaca-export-container', style={
                    'marginBottom': '15px',
                    'padding': '10px',
                    'backgroundColor': '#1e2130',
                    'borderRadius': '8px',
                    'display': 'none'  # Hidden until data loads
                }),
                
                # Options table (populated by callback)
                html.Div(id='alpaca-table-container')
            ],
            color='#4caf50'
        ),
        
        # Hidden dropdown placeholder to satisfy callback registration
        # This gets replaced by the actual dropdown when data loads
        dcc.Dropdown(
            id='alpaca-expiration-dropdown',
            options=[],
            value=None,
            style={'display': 'none'}
        ),
        
        # Download components
        dcc.Download(id='alpaca-download-csv'),
        dcc.Download(id='alpaca-download-json'),
        
        # Store for options data
        dcc.Store(id='alpaca-options-store'),
        # Auto-load trigger (fires once on load to populate default ticker)
        dcc.Interval(id='alpaca-auto-load', interval=2000, n_intervals=0, max_intervals=1),
        
        # Cache info display (for debugging)
        html.Div(id='alpaca-cache-info', style={'display': 'none'}),
        # Order modal container (populated dynamically)
        html.Div(id='alpaca-order-modal-container'),
        
        # Status message
        html.Div(id='alpaca-status-message', style={
            'marginTop': '20px',
            'padding': '10px',
            'borderRadius': '4px',
            'fontSize': '13px'
        })
        
    ], style={
        'padding': '20px',
        'backgroundColor': '#16181f',
        'minHeight': '100vh',
        'color': '#ffffff'
    })
