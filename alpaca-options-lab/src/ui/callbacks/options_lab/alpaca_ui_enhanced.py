"""
Enhanced Alpaca Options Lab UI V2

Major enhancements:
- Greeks visualization panel
- IV surface 3D chart
- Strategy builder panel
- Position tracker
- ML recommendations panel
- Risk analytics dashboard
- Real-time alerts
- Watchlist management
- AI Automation Hub (100+ improvements)
- Smart Analysis Engine
- Auto Trading Engine
- Monitoring & Alerts System
- System Status (Phase 1 Data Fabric)
"""

import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import logging

# Import system status panel
from .system_status_ui import create_system_status_panel
# Import strategy engine panel (Phase 3)
from .strategy_engine_ui import create_strategy_analysis_tab
# Import ML forecast tab (Phase 2)
from forecast_ui.tabs.forecasts import create_forecast_tab
# Import Trade Ops tab (Phase 4/5)
from tradeops_ui.tabs.trade_ops import create_trade_ops_tab
# Import Research tab (Phase 7)
from research_ui.tabs.research import create_research_tab
# Import Market Viz tab (Phase 6 - Agent-Viz)
from financial_dashboard.tabs.market_viz.layout import create_market_viz_layout

logger = logging.getLogger(__name__)


# ===========================================================================
# AI AUTOMATION HUB PANEL (100+ Improvements)
# ===========================================================================

def create_ai_automation_hub_panel() -> html.Div:
    """Create AI Automation Hub panel with all automated features."""
    return html.Div([
        html.H5([
            html.Span("🤖 AI Automation Hub", style={'marginRight': '10px'}),
            dbc.Badge("LIVE", color="success", className="me-2"),
            dbc.Badge("100+ Features", color="info")
        ], style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        # Focus Tickers Display
        html.Div([
            html.Span("Focus: ", style={'color': '#9ca3af', 'fontSize': '12px'}),
            dbc.Badge("GLD", color="warning", className="me-1"),
            dbc.Badge("SLV", color="secondary", className="me-1"),
            dbc.Badge("SPY", color="primary", className="me-1"),
            dbc.Badge("NVDA", color="success", className="me-1"),
            dbc.Badge("AAPL", color="info", className="me-1"),
            dbc.Badge("MSFT", color="primary", className="me-1"),
            dbc.Badge("GOOGL", color="danger", className="me-1"),
            dbc.Badge("AMZN", color="warning", className="me-1"),
            dbc.Badge("META", color="info", className="me-1"),
            dbc.Badge("TSLA", color="danger", className="me-1"),
        ], style={'marginBottom': '15px'}),
        
        # Row 1: Market Regime & Scanner
        html.Div([
            # Market Regime Card
            html.Div([
                html.Div([
                    html.Span("📊 Market Regime", style={'fontWeight': 'bold', 'color': '#00d4ff'}),
                ], style={'marginBottom': '10px'}),
                html.Div(id='ai-regime-display', children=[
                    html.Div([
                        html.Span("Loading...", style={'color': '#9ca3af'})
                    ])
                ]),
                html.Div(id='ai-regime-strategies', style={'marginTop': '10px'})
            ], style={
                'backgroundColor': '#262a3d', 'padding': '15px', 'borderRadius': '8px',
                'flex': '1', 'marginRight': '15px'
            }),
            
            # AI Scanner Card
            html.Div([
                html.Div(id='ai-scanner-results', children=[
                    html.Div([
                        html.Span("🔍 AI Market Scan", style={'fontWeight': 'bold', 'color': '#00d4ff'}),
                        html.Span(" | Initializing...", style={'color': '#9ca3af', 'fontSize': '12px'})
                    ])
                ])
            ], style={
                'backgroundColor': '#262a3d', 'padding': '15px', 'borderRadius': '8px',
                'flex': '1.5'
            }),
        ], style={'display': 'flex', 'marginBottom': '15px'}),
        
        # Row 2: AI Signals & Technical Analysis
        html.Div([
            # AI Signals
            html.Div([
                html.Div(id='ai-signals-container', children=[
                    html.Div([
                        html.Span("🎯 AI Signals", style={'fontWeight': 'bold', 'color': '#00d4ff'}),
                        html.Span(" | Generating...", style={'color': '#9ca3af', 'fontSize': '12px'})
                    ])
                ])
            ], style={
                'backgroundColor': '#262a3d', 'padding': '15px', 'borderRadius': '8px',
                'flex': '1', 'marginRight': '15px'
            }),
            
            # Technical Analysis
            html.Div([
                html.Div(id='ai-ta-analysis', children=[
                    html.Div([
                        html.Span("📈 Technical Analysis", style={'fontWeight': 'bold', 'color': '#00d4ff'}),
                        html.Span(" | Analyzing...", style={'color': '#9ca3af', 'fontSize': '12px'})
                    ])
                ])
            ], style={
                'backgroundColor': '#262a3d', 'padding': '15px', 'borderRadius': '8px',
                'flex': '1'
            }),
        ], style={'display': 'flex', 'marginBottom': '15px'}),
        
        # Row 3: IV Analysis & Auto Strategy
        html.Div([
            # IV Analysis
            html.Div([
                html.Div(id='ai-iv-analysis', children=[
                    html.Div([
                        html.Span("📊 IV Analysis", style={'fontWeight': 'bold', 'color': '#00d4ff'}),
                        html.Span(" | Computing...", style={'color': '#9ca3af', 'fontSize': '12px'})
                    ])
                ])
            ], style={
                'backgroundColor': '#262a3d', 'padding': '15px', 'borderRadius': '8px',
                'flex': '1', 'marginRight': '15px'
            }),
            
            # Auto Strategy
            html.Div([
                html.Div(id='ai-auto-strategy', children=[
                    html.Div([
                        html.Span("🤖 Auto Strategy", style={'fontWeight': 'bold', 'color': '#00d4ff'}),
                        html.Span(" | Building...", style={'color': '#9ca3af', 'fontSize': '12px'})
                    ])
                ])
            ], style={
                'backgroundColor': '#262a3d', 'padding': '15px', 'borderRadius': '8px',
                'flex': '1'
            }),
        ], style={'display': 'flex', 'marginBottom': '15px'}),
        
        # Row 4: ML Predictions & Alerts
        html.Div([
            # ML Predictions
            html.Div([
                html.Div(id='ai-ml-predictions', children=[
                    html.Div([
                        html.Span("🧠 ML Predictions", style={'fontWeight': 'bold', 'color': '#00d4ff'}),
                        html.Span(" | Predicting...", style={'color': '#9ca3af', 'fontSize': '12px'})
                    ])
                ])
            ], style={
                'backgroundColor': '#262a3d', 'padding': '15px', 'borderRadius': '8px',
                'flex': '1', 'marginRight': '15px'
            }),
            
            # Alerts
            html.Div([
                html.Div(id='ai-alerts-container', children=[
                    html.Div([
                        html.Span("🔔 AI Alerts", style={'fontWeight': 'bold', 'color': '#00d4ff'}),
                        html.Span(" | Monitoring...", style={'color': '#9ca3af', 'fontSize': '12px'})
                    ])
                ])
            ], style={
                'backgroundColor': '#262a3d', 'padding': '15px', 'borderRadius': '8px',
                'flex': '1'
            }),
        ], style={'display': 'flex', 'marginBottom': '15px'}),
        
        # Feature Summary
        html.Div([
            html.H6("✨ AI Features Active", style={'color': '#00d4ff', 'marginBottom': '10px'}),
            html.Div([
                html.Div([
                    dbc.Badge("Auto Market Scanner", color="success", className="me-1 mb-1"),
                    dbc.Badge("AI Signal Generator", color="success", className="me-1 mb-1"),
                    dbc.Badge("Market Regime Detection", color="success", className="me-1 mb-1"),
                    dbc.Badge("Technical Analysis", color="success", className="me-1 mb-1"),
                    dbc.Badge("IV Percentile Analysis", color="success", className="me-1 mb-1"),
                    dbc.Badge("Auto Strategy Builder", color="success", className="me-1 mb-1"),
                    dbc.Badge("ML Price Prediction", color="success", className="me-1 mb-1"),
                    dbc.Badge("Volatility Forecast", color="success", className="me-1 mb-1"),
                    dbc.Badge("Expected Move Calc", color="success", className="me-1 mb-1"),
                    dbc.Badge("Iron Condor Builder", color="success", className="me-1 mb-1"),
                    dbc.Badge("Credit Spread Builder", color="success", className="me-1 mb-1"),
                    dbc.Badge("Risk Management", color="success", className="me-1 mb-1"),
                    dbc.Badge("Position Monitor", color="success", className="me-1 mb-1"),
                    dbc.Badge("IV Spike Alerts", color="success", className="me-1 mb-1"),
                    dbc.Badge("Price Alerts", color="success", className="me-1 mb-1"),
                    dbc.Badge("Portfolio Analytics", color="success", className="me-1 mb-1"),
                    dbc.Badge("Greeks Calculator", color="success", className="me-1 mb-1"),
                    dbc.Badge("Earnings Alerts", color="success", className="me-1 mb-1"),
                    dbc.Badge("VIX Monitor", color="success", className="me-1 mb-1"),
                    dbc.Badge("Auto Position Sizing", color="success", className="me-1 mb-1"),
                ], style={'display': 'flex', 'flexWrap': 'wrap'})
            ])
        ], style={'backgroundColor': '#262a3d', 'padding': '15px', 'borderRadius': '8px'})
        
    ], style={
        'backgroundColor': '#1e2130',
        'padding': '15px',
        'borderRadius': '8px',
        'marginTop': '15px',
        'border': '2px solid #00d4ff'
    })


def create_chain_viewer_panel() -> html.Div:
    """
    Create Options Chain Viewer panel.
    
    Displays the live options chain data table with calls/puts,
    strikes, IV, Greeks, and volume data. This is the main chain
    viewer that was missing from the consolidated layout.
    """
    return html.Div([
        html.H5("📈 Options Chain Viewer", style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        # Expiration selector
        html.Div([
            html.Div([
                html.Label("Expiration Date:", style={'color': '#9ca3af', 'fontSize': '12px', 'marginRight': '10px'}),
                dcc.Dropdown(
                    id='chain-viewer-expiration',
                    options=[],
                    value=None,
                    placeholder="Select expiration...",
                    style={'width': '200px', 'display': 'inline-block'}
                ),
            ], style={'display': 'flex', 'alignItems': 'center', 'marginBottom': '10px'}),
            
            # Filter controls
            html.Div([
                html.Span("Filter: ", style={'color': '#9ca3af', 'fontSize': '12px', 'marginRight': '10px'}),
                dcc.RadioItems(
                    id='chain-filter-moneyness',
                    options=[
                        {'label': ' All', 'value': 'all'},
                        {'label': ' ITM', 'value': 'itm'},
                        {'label': ' ATM ±5', 'value': 'atm'},
                        {'label': ' OTM', 'value': 'otm'}
                    ],
                    value='all',
                    inline=True,
                    style={'fontSize': '12px'},
                    labelStyle={'color': '#e0e0e0', 'marginRight': '15px'}
                )
            ], style={'marginBottom': '10px'})
        ], style={
            'padding': '10px',
            'backgroundColor': '#2a2d3a',
            'borderRadius': '6px',
            'marginBottom': '15px'
        }),
        
        # Chain table container (populated by callbacks)
        html.Div(
            id='chain-viewer-table-container',
            children=[
                html.Div([
                    html.P("📊 Click 'Load Chain' to fetch options data", 
                           style={'color': '#9ca3af', 'textAlign': 'center', 'padding': '40px'}),
                    html.P("💡 Data updates automatically on symbol change", 
                           style={'color': '#6b7280', 'textAlign': 'center', 'fontSize': '12px'})
                ])
            ],
            style={
                'minHeight': '400px',
                'backgroundColor': '#1e2130',
                'borderRadius': '6px',
                'padding': '10px',
                'overflowX': 'auto'
            }
        ),
        
        # Chain stats summary
        html.Div([
            html.Div([
                html.Span("Calls OI: ", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Span(id='chain-calls-oi', children="--", style={'color': '#4caf50', 'fontSize': '13px', 'fontWeight': 'bold'}),
            ], style={'display': 'inline-block', 'marginRight': '20px'}),
            html.Div([
                html.Span("Puts OI: ", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Span(id='chain-puts-oi', children="--", style={'color': '#f44336', 'fontSize': '13px', 'fontWeight': 'bold'}),
            ], style={'display': 'inline-block', 'marginRight': '20px'}),
            html.Div([
                html.Span("P/C Ratio: ", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Span(id='chain-pc-ratio', children="--", style={'color': '#F5C211', 'fontSize': '13px', 'fontWeight': 'bold'}),
            ], style={'display': 'inline-block', 'marginRight': '20px'}),
            html.Div([
                html.Span("Max Pain: ", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Span(id='chain-max-pain', children="--", style={'color': '#00d4ff', 'fontSize': '13px', 'fontWeight': 'bold'}),
            ], style={'display': 'inline-block'}),
        ], style={
            'padding': '10px',
            'backgroundColor': '#2a2d3a',
            'borderRadius': '6px',
            'marginTop': '10px'
        })
        
    ], style={
        'backgroundColor': '#1e2130',
        'padding': '15px',
        'borderRadius': '8px',
        'marginTop': '15px',
        'border': '2px solid #F5C211'
    })


def create_greeks_panel() -> html.Div:
    """Create Greeks visualization panel."""
    return html.Div([
        html.H5("📊 Greeks Analysis", style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        # Greeks summary cards
        html.Div([
            # Delta card
            html.Div([
                html.Div("Delta", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div(id='greeks-delta-value', children="0.00", 
                        style={'color': '#4caf50', 'fontSize': '20px', 'fontWeight': 'bold'}),
                html.Div("$ Exposure", style={'color': '#6b7280', 'fontSize': '10px'}),
                html.Div(id='greeks-delta-dollars', children="$0", 
                        style={'color': '#9ca3af', 'fontSize': '12px'})
            ], style={
                'backgroundColor': '#2a2d3a',
                'padding': '12px',
                'borderRadius': '6px',
                'flex': '1',
                'marginRight': '10px',
                'textAlign': 'center'
            }),
            
            # Gamma card
            html.Div([
                html.Div("Gamma", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div(id='greeks-gamma-value', children="0.00", 
                        style={'color': '#2196F3', 'fontSize': '20px', 'fontWeight': 'bold'}),
                html.Div("Per $1 Move", style={'color': '#6b7280', 'fontSize': '10px'}),
                html.Div(id='greeks-gamma-change', children="$0", 
                        style={'color': '#9ca3af', 'fontSize': '12px'})
            ], style={
                'backgroundColor': '#2a2d3a',
                'padding': '12px',
                'borderRadius': '6px',
                'flex': '1',
                'marginRight': '10px',
                'textAlign': 'center'
            }),
            
            # Theta card
            html.Div([
                html.Div("Theta", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div(id='greeks-theta-value', children="0.00", 
                        style={'color': '#f44336', 'fontSize': '20px', 'fontWeight': 'bold'}),
                html.Div("Daily Decay", style={'color': '#6b7280', 'fontSize': '10px'}),
                html.Div(id='greeks-theta-daily', children="$0/day", 
                        style={'color': '#9ca3af', 'fontSize': '12px'})
            ], style={
                'backgroundColor': '#2a2d3a',
                'padding': '12px',
                'borderRadius': '6px',
                'flex': '1',
                'marginRight': '10px',
                'textAlign': 'center'
            }),
            
            # Vega card
            html.Div([
                html.Div("Vega", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div(id='greeks-vega-value', children="0.00", 
                        style={'color': '#FF9800', 'fontSize': '20px', 'fontWeight': 'bold'}),
                html.Div("Per 1% IV", style={'color': '#6b7280', 'fontSize': '10px'}),
                html.Div(id='greeks-vega-pct', children="$0", 
                        style={'color': '#9ca3af', 'fontSize': '12px'})
            ], style={
                'backgroundColor': '#2a2d3a',
                'padding': '12px',
                'borderRadius': '6px',
                'flex': '1',
                'textAlign': 'center'
            }),
        ], style={'display': 'flex', 'marginBottom': '15px'}),
        
        # Greeks chart
        dcc.Graph(id='greeks-chart', style={'height': '350px'})
        
    ], style={
        'backgroundColor': '#1e2130',
        'padding': '15px',
        'borderRadius': '8px',
        'marginBottom': '15px'
    })


def create_iv_surface_panel() -> html.Div:
    """Create IV surface 3D visualization panel."""
    return html.Div([
        html.H5("🌊 IV Surface", style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        html.Div([
            # View mode selector
            html.Div([
                html.Label("View: ", style={'color': '#9ca3af', 'fontSize': '12px', 'marginRight': '8px'}),
                dcc.RadioItems(
                    id='iv-view-mode',
                    options=[
                        {'label': ' 3D Surface', 'value': '3d'},
                        {'label': ' Skew Chart', 'value': 'skew'},
                        {'label': ' Term Structure', 'value': 'term'}
                    ],
                    value='3d',
                    inline=True,
                    style={'color': '#e0e0e0', 'fontSize': '12px'},
                    labelStyle={'marginRight': '15px'}
                )
            ], style={'marginBottom': '10px'}),
        ]),
        
        # IV surface chart
        dcc.Graph(id='iv-surface-chart', style={'height': '450px'})
        
    ], style={
        'backgroundColor': '#1e2130',
        'padding': '15px',
        'borderRadius': '8px',
        'marginBottom': '15px'
    })


def create_strategy_builder() -> html.Div:
    """Create strategy builder panel."""
    return html.Div([
        html.H5("🎯 Strategy Builder", style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        # Quick strategy buttons
        html.Div([
            html.Button("Bull Call", id='strat-bull-call', n_clicks=0,
                       style=_btn_style('#4caf50')),
            html.Button("Bear Put", id='strat-bear-put', n_clicks=0,
                       style=_btn_style('#f44336')),
            html.Button("Iron Condor", id='strat-iron-condor', n_clicks=0,
                       style=_btn_style('#2196F3')),
            html.Button("Straddle", id='strat-straddle', n_clicks=0,
                       style=_btn_style('#9C27B0')),
            html.Button("Strangle", id='strat-strangle', n_clicks=0,
                       style=_btn_style('#FF9800')),
            html.Button("Butterfly", id='strat-butterfly', n_clicks=0,
                       style=_btn_style('#00BCD4')),
        ], style={'marginBottom': '15px', 'display': 'flex', 'flexWrap': 'wrap', 'gap': '8px'}),
        
        # Strategy legs table
        html.Div([
            html.H6("Strategy Legs", style={'color': '#9ca3af', 'marginBottom': '10px', 'fontSize': '13px'}),
            dash_table.DataTable(
                id='strategy-legs-table',
                columns=[
                    {'name': 'Leg', 'id': 'leg'},
                    {'name': 'Type', 'id': 'type'},
                    {'name': 'Strike', 'id': 'strike'},
                    {'name': 'Qty', 'id': 'qty'},
                    {'name': 'Action', 'id': 'action'},
                    {'name': 'Premium', 'id': 'premium'},
                ],
                data=[],
                style_header={'backgroundColor': '#2a2d3a', 'color': '#ffffff', 'fontWeight': 'bold'},
                style_cell={'backgroundColor': '#1e2130', 'color': '#e0e0e0', 'fontSize': '12px', 'padding': '8px'},
                row_deletable=True
            )
        ], style={'marginBottom': '15px'}),
        
        # Strategy summary
        html.Div([
            html.Div([
                html.Span("Net Premium: ", style={'color': '#9ca3af'}),
                html.Span(id='strat-net-premium', children="$0.00", 
                         style={'color': '#4caf50', 'fontWeight': 'bold'})
            ], style={'marginRight': '20px'}),
            html.Div([
                html.Span("Max Profit: ", style={'color': '#9ca3af'}),
                html.Span(id='strat-max-profit', children="$0.00", 
                         style={'color': '#4caf50', 'fontWeight': 'bold'})
            ], style={'marginRight': '20px'}),
            html.Div([
                html.Span("Max Loss: ", style={'color': '#9ca3af'}),
                html.Span(id='strat-max-loss', children="$0.00", 
                         style={'color': '#f44336', 'fontWeight': 'bold'})
            ], style={'marginRight': '20px'}),
            html.Div([
                html.Span("Breakeven: ", style={'color': '#9ca3af'}),
                html.Span(id='strat-breakeven', children="$0.00", 
                         style={'color': '#FF9800', 'fontWeight': 'bold'})
            ]),
        ], style={'display': 'flex', 'marginBottom': '15px', 'fontSize': '13px'}),
        
        # Payoff diagram
        dcc.Graph(id='payoff-diagram', style={'height': '300px'}),
        
        # Execute button
        html.Div([
            html.Button("📝 Execute Strategy (Paper)", id='execute-strategy-btn', n_clicks=0,
                       style={
                           'backgroundColor': '#4caf50',
                           'color': 'white',
                           'padding': '10px 25px',
                           'border': 'none',
                           'borderRadius': '5px',
                           'fontSize': '14px',
                           'fontWeight': 'bold',
                           'cursor': 'pointer',
                           'marginRight': '10px'
                       }),
            html.Button("🗑️ Clear", id='clear-strategy-btn', n_clicks=0,
                       style={
                           'backgroundColor': '#666',
                           'color': 'white',
                           'padding': '10px 25px',
                           'border': 'none',
                           'borderRadius': '5px',
                           'fontSize': '14px',
                           'cursor': 'pointer'
                       })
        ], style={'textAlign': 'center', 'marginTop': '15px'}),
        
        # Execute strategy result output
        html.Div(id='execute-strategy-result', style={'marginTop': '10px'})
        
    ], style={
        'backgroundColor': '#1e2130',
        'padding': '15px',
        'borderRadius': '8px',
        'marginBottom': '15px'
    })


def create_ml_recommendations_panel() -> html.Div:
    """Create ML-powered recommendations panel."""
    return html.Div([
        html.H5("🤖 AI Recommendations", style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        # Outlook selector
        html.Div([
            html.Label("Your Market Outlook: ", style={'color': '#9ca3af', 'fontSize': '12px', 'marginRight': '10px'}),
            dcc.RadioItems(
                id='ml-outlook-selector',
                options=[
                    {'label': ' Bullish', 'value': 'bullish'},
                    {'label': ' Bearish', 'value': 'bearish'},
                    {'label': ' Neutral', 'value': 'neutral'},
                    {'label': ' Volatile', 'value': 'volatile'}
                ],
                value='neutral',
                inline=True,
                style={'color': '#e0e0e0', 'fontSize': '12px'},
                labelStyle={'marginRight': '15px'}
            ),
        ], style={'marginBottom': '15px'}),
        
        # Risk tolerance
        html.Div([
            html.Label("Risk Tolerance: ", style={'color': '#9ca3af', 'fontSize': '12px', 'marginRight': '10px'}),
            dcc.Slider(
                id='ml-risk-slider',
                min=1, max=3, step=1,
                marks={1: 'Low', 2: 'Moderate', 3: 'High'},
                value=2
            )
        ], style={'marginBottom': '20px', 'width': '300px'}),
        
        # ML Predictions section
        html.Div([
            html.H6("📈 Price Prediction (7 days)", style={'color': '#9ca3af', 'marginBottom': '10px'}),
            html.Div([
                html.Div([
                    html.Div("Direction", style={'color': '#6b7280', 'fontSize': '11px'}),
                    html.Div(id='ml-price-direction', children="BULLISH", 
                            style={'color': '#4caf50', 'fontSize': '16px', 'fontWeight': 'bold'})
                ], style={'flex': '1', 'textAlign': 'center'}),
                html.Div([
                    html.Div("Target", style={'color': '#6b7280', 'fontSize': '11px'}),
                    html.Div(id='ml-price-target', children="$0.00", 
                            style={'color': '#2196F3', 'fontSize': '16px', 'fontWeight': 'bold'})
                ], style={'flex': '1', 'textAlign': 'center'}),
                html.Div([
                    html.Div("Confidence", style={'color': '#6b7280', 'fontSize': '11px'}),
                    html.Div(id='ml-confidence', children="0%", 
                            style={'color': '#FF9800', 'fontSize': '16px', 'fontWeight': 'bold'})
                ], style={'flex': '1', 'textAlign': 'center'}),
            ], style={'display': 'flex', 'marginBottom': '15px', 'backgroundColor': '#2a2d3a', 
                     'padding': '15px', 'borderRadius': '6px'})
        ]),
        
        # IV Forecast
        html.Div([
            html.H6("📊 IV Forecast", style={'color': '#9ca3af', 'marginBottom': '10px'}),
            html.Div([
                html.Div([
                    html.Div("Current IV", style={'color': '#6b7280', 'fontSize': '11px'}),
                    html.Div(id='ml-current-iv', children="0%", 
                            style={'color': '#e0e0e0', 'fontSize': '14px'})
                ], style={'flex': '1', 'textAlign': 'center'}),
                html.Div([
                    html.Div("Forecast IV", style={'color': '#6b7280', 'fontSize': '11px'}),
                    html.Div(id='ml-forecast-iv', children="0%", 
                            style={'color': '#9C27B0', 'fontSize': '14px', 'fontWeight': 'bold'})
                ], style={'flex': '1', 'textAlign': 'center'}),
                html.Div([
                    html.Div("IV Rank", style={'color': '#6b7280', 'fontSize': '11px'}),
                    html.Div(id='ml-iv-rank', children="0%", 
                            style={'color': '#00BCD4', 'fontSize': '14px'})
                ], style={'flex': '1', 'textAlign': 'center'}),
            ], style={'display': 'flex', 'marginBottom': '15px', 'backgroundColor': '#2a2d3a', 
                     'padding': '15px', 'borderRadius': '6px'})
        ]),
        
        # Recommended strategies
        html.Div([
            html.H6("🎯 Recommended Strategies", style={'color': '#9ca3af', 'marginBottom': '10px'}),
            html.Div(id='ml-strategy-recommendations', children=[
                _create_strategy_card("Loading...", "Please load options data first", "#666")
            ])
        ]),
        
        # Strike recommendations
        html.Div([
            html.H6("💡 Optimal Strikes", style={'color': '#9ca3af', 'marginBottom': '10px', 'marginTop': '15px'}),
            html.Div(id='ml-strike-recommendations', children=[
                html.Div("Loading...", style={'color': '#6b7280', 'fontSize': '12px'})
            ])
        ]),
        
        # Sentiment Analysis
        html.Div([
            html.H6("📰 Market Sentiment", style={'color': '#9ca3af', 'marginBottom': '10px', 'marginTop': '15px'}),
            html.Div(id='sentiment-analysis-display', children=[
                html.Div("Loading...", style={'color': '#6b7280', 'fontSize': '12px'})
            ])
        ]),
        
        # Multi-Model Consensus
        html.Div([
            html.H6("🧠 Multi-Model Consensus", style={'color': '#9ca3af', 'marginBottom': '10px', 'marginTop': '20px'}),
            html.Button("Generate Consensus", id='generate-consensus-btn', n_clicks=0,
                       style={
                           'backgroundColor': '#9c27b0',
                           'color': 'white',
                           'padding': '8px 15px',
                           'border': 'none',
                           'borderRadius': '4px',
                           'cursor': 'pointer',
                           'width': '100%',
                           'marginBottom': '10px'
                       }),
            dcc.Loading(
                id="loading-consensus",
                type="circle",
                children=html.Div(id='consensus-results')
            )
        ], style={'backgroundColor': '#2a2d3a', 'padding': '10px', 'borderRadius': '4px', 'marginTop': '15px'}),
        
        # Monte Carlo AI Forecast
        html.Div([
            html.H6("📈 AI Price Forecast", style={'color': '#9ca3af', 'marginBottom': '10px', 'marginTop': '20px'}),
            
            # Contract selector
            html.Div([
                html.Label("Select Contract:", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div([
                    dcc.Dropdown(
                        id='forecast-expiration-dropdown',
                        placeholder='Expiration',
                        style={'width': '120px', 'marginRight': '5px'},
                        className='dark-dropdown'
                    ),
                    dcc.Dropdown(
                        id='forecast-strike-dropdown',
                        placeholder='Strike',
                        style={'width': '100px', 'marginRight': '5px'},
                        className='dark-dropdown'
                    ),
                    dcc.RadioItems(
                        id='forecast-type-radio',
                        options=[
                            {'label': 'Call', 'value': 'call'},
                            {'label': 'Put', 'value': 'put'}
                        ],
                        value='call',
                        inline=True,
                        style={'color': '#e0e0e0', 'fontSize': '11px'}
                    )
                ], style={'display': 'flex', 'gap': '5px', 'alignItems': 'center', 'flexWrap': 'wrap'})
            ], style={'marginBottom': '10px'}),
            
            html.Button("🔮 Generate Forecast", id='generate-forecast-btn', n_clicks=0,
                       style={
                           'backgroundColor': '#2196F3',
                           'color': 'white',
                           'padding': '8px 15px',
                           'border': 'none',
                           'borderRadius': '4px',
                           'cursor': 'pointer',
                           'width': '100%',
                           'marginBottom': '10px'
                       }),
            dcc.Loading(
                id="loading-forecast",
                type="circle",
                children=html.Div(id='forecast-results')
            )
        ], style={'backgroundColor': '#2a2d3a', 'padding': '10px', 'borderRadius': '4px', 'marginTop': '15px'})
        
    ], style={
        'backgroundColor': '#1e2130',
        'padding': '15px',
        'borderRadius': '8px',
        'marginBottom': '15px'
    })


def create_positions_panel() -> html.Div:
    """Create positions tracker panel."""
    return html.Div([
        html.H5("💼 Positions", style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        # Portfolio summary
        html.Div([
            html.Div([
                html.Div("Total P&L", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div(id='positions-total-pnl', children="$0.00", 
                        style={'color': '#4caf50', 'fontSize': '24px', 'fontWeight': 'bold'})
            ], style={'flex': '1', 'textAlign': 'center'}),
            html.Div([
                html.Div("Day P&L", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div(id='positions-day-pnl', children="$0.00", 
                        style={'color': '#2196F3', 'fontSize': '24px', 'fontWeight': 'bold'})
            ], style={'flex': '1', 'textAlign': 'center'}),
            html.Div([
                html.Div("Open Positions", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div(id='positions-count', children="0", 
                        style={'color': '#FF9800', 'fontSize': '24px', 'fontWeight': 'bold'})
            ], style={'flex': '1', 'textAlign': 'center'}),
        ], style={'display': 'flex', 'marginBottom': '15px', 'backgroundColor': '#2a2d3a', 
                 'padding': '15px', 'borderRadius': '6px'}),
        
        # Positions table
        dash_table.DataTable(
            id='positions-table',
            columns=[
                {'name': 'Symbol', 'id': 'symbol'},
                {'name': 'Type', 'id': 'type'},
                {'name': 'Qty', 'id': 'qty'},
                {'name': 'Avg Cost', 'id': 'avg_cost'},
                {'name': 'Current', 'id': 'current_price'},
                {'name': 'P&L', 'id': 'pnl'},
                {'name': 'P&L %', 'id': 'pnl_pct'},
                {'name': 'Action', 'id': 'action', 'presentation': 'markdown'}
            ],
            data=[],
            style_header={'backgroundColor': '#2a2d3a', 'color': '#ffffff', 'fontWeight': 'bold', 'fontSize': '12px'},
            style_cell={'backgroundColor': '#1e2130', 'color': '#e0e0e0', 'fontSize': '12px', 'padding': '8px'},
            style_data_conditional=[
                {'if': {'filter_query': '{pnl} > 0', 'column_id': 'pnl'}, 'color': '#4caf50'},
                {'if': {'filter_query': '{pnl} < 0', 'column_id': 'pnl'}, 'color': '#f44336'},
                {'if': {'filter_query': '{pnl_pct} > 0', 'column_id': 'pnl_pct'}, 'color': '#4caf50'},
                {'if': {'filter_query': '{pnl_pct} < 0', 'column_id': 'pnl_pct'}, 'color': '#f44336'},
            ]
        )
        
    ], style={
        'backgroundColor': '#1e2130',
        'padding': '15px',
        'borderRadius': '8px',
        'marginBottom': '15px'
    })


def create_risk_analytics_panel() -> html.Div:
    """Create risk analytics panel."""
    return html.Div([
        html.H5("⚠️ Risk Analytics", style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        # Risk metrics
        html.Div([
            html.Div([
                html.Div("Portfolio Delta", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div(id='risk-portfolio-delta', children="0", 
                        style={'color': '#4caf50', 'fontSize': '18px', 'fontWeight': 'bold'}),
                html.Div("shares equivalent", style={'color': '#6b7280', 'fontSize': '10px'})
            ], style={'flex': '1', 'textAlign': 'center', 'padding': '10px'}),
            
            html.Div([
                html.Div("Max Daily Loss", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div(id='risk-max-loss', children="$0", 
                        style={'color': '#f44336', 'fontSize': '18px', 'fontWeight': 'bold'}),
                html.Div("at 2σ move", style={'color': '#6b7280', 'fontSize': '10px'})
            ], style={'flex': '1', 'textAlign': 'center', 'padding': '10px'}),
            
            html.Div([
                html.Div("Margin Used", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div(id='risk-margin-used', children="0%", 
                        style={'color': '#FF9800', 'fontSize': '18px', 'fontWeight': 'bold'}),
                html.Div("of available", style={'color': '#6b7280', 'fontSize': '10px'})
            ], style={'flex': '1', 'textAlign': 'center', 'padding': '10px'}),
            
            html.Div([
                html.Div("Risk Score", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div(id='risk-score', children="LOW", 
                        style={'color': '#4caf50', 'fontSize': '18px', 'fontWeight': 'bold'}),
                html.Div("overall", style={'color': '#6b7280', 'fontSize': '10px'})
            ], style={'flex': '1', 'textAlign': 'center', 'padding': '10px'}),
        ], style={'display': 'flex', 'marginBottom': '15px', 'backgroundColor': '#2a2d3a', 
                 'borderRadius': '6px'}),
        
        # P&L scenario analysis
        dcc.Graph(id='risk-scenario-chart', style={'height': '250px'})
        
    ], style={
        'backgroundColor': '#1e2130',
        'padding': '15px',
        'borderRadius': '8px',
        'marginBottom': '15px'
    })


def create_flow_analysis_panel() -> html.Div:
    """Create options flow analysis panel."""
    return html.Div([
        html.H5("🔥 Unusual Activity", style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        # Put/Call ratio
        html.Div([
            html.Div([
                html.Div("Put/Call Ratio (Volume)", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div(id='flow-pcr-volume', children="0.00", 
                        style={'fontSize': '20px', 'fontWeight': 'bold'})
            ], style={'flex': '1', 'textAlign': 'center'}),
            html.Div([
                html.Div("Put/Call Ratio (OI)", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div(id='flow-pcr-oi', children="0.00", 
                        style={'fontSize': '20px', 'fontWeight': 'bold'})
            ], style={'flex': '1', 'textAlign': 'center'}),
            html.Div([
                html.Div("Sentiment", style={'color': '#9ca3af', 'fontSize': '11px'}),
                html.Div(id='flow-sentiment', children="NEUTRAL", 
                        style={'color': '#FF9800', 'fontSize': '20px', 'fontWeight': 'bold'})
            ], style={'flex': '1', 'textAlign': 'center'}),
        ], style={'display': 'flex', 'marginBottom': '15px', 'backgroundColor': '#2a2d3a', 
                 'padding': '15px', 'borderRadius': '6px'}),
        
        # Max pain
        html.Div([
            html.Div([
                html.Span("Max Pain: ", style={'color': '#9ca3af', 'fontSize': '13px'}),
                html.Span(id='flow-max-pain', children="$0.00", 
                         style={'color': '#FF9800', 'fontSize': '18px', 'fontWeight': 'bold'})
            ]),
            html.Div([
                html.Span("Distance from Spot: ", style={'color': '#9ca3af', 'fontSize': '12px'}),
                html.Span(id='flow-max-pain-distance', children="0%", 
                         style={'color': '#e0e0e0', 'fontSize': '14px'})
            ])
        ], style={'marginBottom': '15px'}),
        
        # Volume/OI heatmap
        dcc.Graph(id='flow-heatmap', style={'height': '250px'}),
        
        # Unusual activity table
        html.H6("🔔 Unusual Trades", style={'color': '#9ca3af', 'marginTop': '15px', 'marginBottom': '10px'}),
        dash_table.DataTable(
            id='unusual-activity-table',
            columns=[
                {'name': 'Time', 'id': 'time'},
                {'name': 'Type', 'id': 'type'},
                {'name': 'Strike', 'id': 'strike'},
                {'name': 'Exp', 'id': 'expiration'},
                {'name': 'Volume', 'id': 'volume'},
                {'name': 'OI', 'id': 'oi'},
                {'name': 'Vol/OI', 'id': 'vol_oi_ratio'},
                {'name': 'Premium', 'id': 'premium'}
            ],
            data=[],
            style_header={'backgroundColor': '#2a2d3a', 'color': '#ffffff', 'fontWeight': 'bold', 'fontSize': '11px'},
            style_cell={'backgroundColor': '#1e2130', 'color': '#e0e0e0', 'fontSize': '11px', 'padding': '6px'},
            page_size=5
        )
        
    ], style={
        'backgroundColor': '#1e2130',
        'padding': '15px',
        'borderRadius': '8px',
        'marginBottom': '15px'
    })


def create_watchlist_panel() -> html.Div:
    """Create watchlist management panel."""
    return html.Div([
        html.H5("👀 Watchlist", style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        # Add to watchlist
        html.Div([
            dcc.Input(
                id='watchlist-add-input',
                type='text',
                placeholder='Add symbol (e.g., AAPL)',
                style={
                    'width': '150px',
                    'padding': '8px',
                    'backgroundColor': '#2a2d3a',
                    'color': '#ffffff',
                    'border': '1px solid #3d4050',
                    'borderRadius': '4px',
                    'marginRight': '10px'
                }
            ),
            html.Button("Add", id='watchlist-add-btn', n_clicks=0,
                       style={
                           'backgroundColor': '#4caf50',
                           'color': 'white',
                           'padding': '8px 15px',
                           'border': 'none',
                           'borderRadius': '4px',
                           'cursor': 'pointer'
                       })
        ], style={'marginBottom': '15px'}),
        
        # Watchlist items
        html.Div(id='watchlist-items', children=[
            _create_watchlist_item("SPY", 450.00, 1.25, 0.28),
            _create_watchlist_item("QQQ", 380.00, -0.50, -0.13),
            _create_watchlist_item("AAPL", 175.00, 2.30, 1.33),
        ])
        
    ], style={
        'backgroundColor': '#1e2130',
        'padding': '15px',
        'borderRadius': '8px',
        'marginBottom': '15px'
    })


def create_alerts_panel() -> html.Div:
    """Create price/IV alerts panel."""
    return html.Div([
        html.H5("🔔 Alerts", style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        # Create alert
        html.Div([
            dcc.Dropdown(
                id='alert-type-dropdown',
                options=[
                    {'label': 'Price Above', 'value': 'price_above'},
                    {'label': 'Price Below', 'value': 'price_below'},
                    {'label': 'IV Above', 'value': 'iv_above'},
                    {'label': 'IV Below', 'value': 'iv_below'},
                    {'label': 'Volume Spike', 'value': 'volume_spike'}
                ],
                value='price_above',
                style={'width': '150px', 'marginRight': '10px'},
                className='dark-dropdown'
            ),
            dcc.Input(
                id='alert-value-input',
                type='number',
                placeholder='Value',
                style={
                    'width': '100px',
                    'padding': '8px',
                    'backgroundColor': '#2a2d3a',
                    'color': '#ffffff',
                    'border': '1px solid #3d4050',
                    'borderRadius': '4px',
                    'marginRight': '10px'
                }
            ),
            html.Button("Create Alert", id='create-alert-btn', n_clicks=0,
                       style={
                           'backgroundColor': '#2196F3',
                           'color': 'white',
                           'padding': '8px 15px',
                           'border': 'none',
                           'borderRadius': '4px',
                           'cursor': 'pointer'
                       })
        ], style={'display': 'flex', 'marginBottom': '15px', 'alignItems': 'center'}),
        
        # Active alerts
        html.Div(id='active-alerts', children=[
            html.Div("No active alerts", style={'color': '#6b7280', 'fontSize': '12px'})
        ])
        
    ], style={
        'backgroundColor': '#1e2130',
        'padding': '15px',
        'borderRadius': '8px',
        'marginBottom': '15px'
    })


def _btn_style(color: str) -> Dict:
    """Generate button style with given color."""
    return {
        'backgroundColor': color,
        'color': 'white',
        'padding': '6px 12px',
        'border': 'none',
        'borderRadius': '4px',
        'cursor': 'pointer',
        'fontSize': '12px',
        'fontWeight': 'bold'
    }


def _create_strategy_card(name: str, description: str, color: str) -> html.Div:
    """Create a strategy recommendation card."""
    return html.Div([
        html.Div(name, style={'color': color, 'fontWeight': 'bold', 'fontSize': '14px'}),
        html.Div(description, style={'color': '#9ca3af', 'fontSize': '11px', 'marginTop': '4px'})
    ], style={
        'backgroundColor': '#2a2d3a',
        'padding': '10px',
        'borderRadius': '6px',
        'marginBottom': '8px',
        'borderLeft': f'3px solid {color}'
    })


def _create_watchlist_item(symbol: str, price: float, change: float, change_pct: float) -> html.Div:
    """Create a watchlist item."""
    color = '#4caf50' if change >= 0 else '#f44336'
    sign = '+' if change >= 0 else ''
    
    return html.Div([
        html.Div([
            html.Span(symbol, style={'color': '#ffffff', 'fontWeight': 'bold', 'fontSize': '14px'}),
            html.Span(f"${price:.2f}", style={'color': '#e0e0e0', 'marginLeft': '10px'})
        ]),
        html.Div([
            html.Span(f"{sign}{change:.2f} ({sign}{change_pct:.2f}%)", style={'color': color, 'fontSize': '12px'})
        ])
    ], style={
        'backgroundColor': '#2a2d3a',
        'padding': '10px',
        'borderRadius': '6px',
        'marginBottom': '8px',
        'display': 'flex',
        'justifyContent': 'space-between',
        'alignItems': 'center',
        'cursor': 'pointer'
    })


def create_consolidated_options_layout(ticker: str = "SPY") -> html.Div:
    """
    Create consolidated 4-tab Alpaca Options Lab layout.
    Phase 15 - Agent-UX Consolidation + Week 2 Enhancements
    
    Workspaces:
    1. Scanner: Market Viz + Flow + Patterns
    2. Strategy: Chain + Builder + AI
    3. Command: Positions + Trade Ops
    4. Admin: Status + Research
    """
    from dashboard_layouts.layouts.workspaces import (
        scanner_layout,
        strategy_layout,
        command_layout,
        admin_layout,
        deeptech_layout,
    )
    
    # Import Week 2 CSS injectors
    try:
        from src.ui.components.loading_states import inject_loading_css
        from src.ui.components.buttons import inject_button_css
        loading_css = inject_loading_css()
        button_css = inject_button_css()
    except ImportError:
        loading_css = html.Style("")
        button_css = html.Style("")
    
    return html.Div([
        # Inject Week 2 CSS for loading states and button hover effects
        loading_css,
        button_css,
        # Top bar with ticker input and controls (preserved from original)
        html.Div([
            html.Div([
                html.Label("Symbol:", style={'color': '#9ca3af', 'fontSize': '13px', 'fontWeight': 'bold', 'marginRight': '10px'}),
                dcc.Input(
                    id='alpaca-ticker-input',
                    type='text',
                    value=ticker,
                    placeholder='Enter ticker...',
                    style={
                        'width': '120px',
                        'padding': '8px',
                        'backgroundColor': '#2a2d3a',
                        'color': '#ffffff',
                        'border': '1px solid #3d4050',
                        'borderRadius': '4px',
                        'marginRight': '10px'
                    }
                ),
                html.Button("Load Chain", id='alpaca-load-button', n_clicks=0,
                           style={
                               'padding': '8px 20px',
                               'backgroundColor': '#4caf50',
                               'color': 'white',
                               'border': 'none',
                               'borderRadius': '4px',
                               'cursor': 'pointer',
                               'fontWeight': 'bold',
                               'marginRight': '20px'
                           }),
                
                # Trading mode toggle
                html.Div([
                    html.Span("Trading Mode: ", style={'color': '#9ca3af', 'fontSize': '12px'}),
                    dcc.RadioItems(
                        id='trading-mode-toggle',
                        options=[
                            {'label': ' Paper', 'value': 'paper'},
                            {'label': ' Live', 'value': 'live'}
                        ],
                        value='paper',
                        inline=True,
                        style={'fontSize': '12px'},
                        labelStyle={'color': '#e0e0e0', 'marginRight': '10px'}
                    )
                ], style={'display': 'inline-block', 'marginRight': '20px'}),
                
                # Auto-refresh toggle
                html.Div([
                    dcc.Checklist(
                        id='auto-refresh-toggle',
                        options=[{'label': ' Auto-Refresh (30s)', 'value': 'enabled'}],
                        value=[],
                        style={'fontSize': '12px', 'color': '#e0e0e0'}
                    )
                ], style={'display': 'inline-block'}),
                
                # Command Palette Button (Phase 17)
                html.Button(
                    "⌘K",
                    id='command-palette-trigger',
                    n_clicks=0,
                    style={
                        'padding': '6px 12px',
                        'backgroundColor': '#3d4050',
                        'color': '#F5C211',
                        'border': '1px solid #F5C211',
                        'borderRadius': '4px',
                        'cursor': 'pointer',
                        'fontWeight': 'bold',
                        'fontSize': '12px',
                        'marginLeft': '15px'
                    },
                    title='Open Command Palette (Ctrl+K)'
                ),
                
                # Phase 15 indicator
                dbc.Badge("5-Tab UX", color="warning", className="ms-3"),
            ], style={'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap'})
        ], style={
            'padding': '15px',
            'backgroundColor': '#1e2130',
            'borderRadius': '8px',
            'marginBottom': '15px'
        }),
        
        # CONSOLIDATED 4 TABS (Phase 15)
        dcc.Tabs(
            id='main-workspace-tabs',
            value='scanner-workspace-tab',
            children=[
                # Tab 1: Scanner Workspace
                dcc.Tab(
                    label='🔭 Scanner',
                    value='scanner-workspace-tab',
                    children=[scanner_layout()],
                    style={'backgroundColor': '#16181f', 'color': '#fff'},
                    selected_style={'backgroundColor': '#2a2d3a', 'color': '#F5C211'}
                ),
                
                # Tab 2: Strategy Workspace
                dcc.Tab(
                    label='⚔️ Strategy',
                    value='strategy-workspace-tab',
                    children=[strategy_layout()],
                    style={'backgroundColor': '#16181f', 'color': '#fff'},
                    selected_style={'backgroundColor': '#2a2d3a', 'color': '#00d4ff'}
                ),
                
                # Tab 3: Command Workspace
                dcc.Tab(
                    label='🎮 Command',
                    value='command-workspace-tab',
                    children=[command_layout()],
                    style={'backgroundColor': '#16181f', 'color': '#fff'},
                    selected_style={'backgroundColor': '#2a2d3a', 'color': '#ff5722'}
                ),
                
                # Tab 4: Deep-Tech Workspace (NEW)
                dcc.Tab(
                    label='🔬 Deep-Tech',
                    value='deeptech-workspace-tab',
                    children=[deeptech_layout()],
                    style={'backgroundColor': '#16181f', 'color': '#fff'},
                    selected_style={'backgroundColor': '#2a2d3a', 'color': '#00bcd4'}
                ),
                
                # Tab 5: Admin Workspace
                dcc.Tab(
                    label='🔧 Admin',
                    value='admin-workspace-tab',
                    children=[admin_layout()],
                    style={'backgroundColor': '#16181f', 'color': '#fff'},
                    selected_style={'backgroundColor': '#2a2d3a', 'color': '#4caf50'}
                ),
            ],
            style={'marginBottom': '15px'}
        ),
        
        # Hidden components (preserved for callbacks)
        dcc.Dropdown(id='alpaca-expiration-dropdown', options=[], value=None, style={'display': 'none'}),
        dcc.Download(id='alpaca-download-csv'),
        dcc.Download(id='alpaca-download-json'),
        dcc.Store(id='alpaca-options-store'),
        dcc.Store(id='strategy-legs-store', data=[]),
        dcc.Store(id='positions-store', data=[]),
        dcc.Store(id='watchlist-store', data=['SPY', 'QQQ', 'AAPL']),
        dcc.Store(id='alerts-store', data=[]),
        dcc.Store(id='strategy-engine-refresh-trigger', data=0),
        dcc.Store(id='pattern-data-store', data=[]),  # Phase 15: Pattern detection store
        dcc.Store(id='command-history-store', data=[]),  # Phase 17: Command history
        dcc.Store(id='workspace-switch-trigger', data=''),  # Workspace hotkey trigger
        dcc.Interval(id='alpaca-auto-load', interval=2000, n_intervals=0, max_intervals=1),
        dcc.Interval(id='auto-refresh-interval', interval=30000, n_intervals=0, disabled=True),
        
        html.Div(id='alpaca-cache-info', style={'display': 'none'}),
        html.Div(id='alpaca-order-modal-container'),
        html.Div(id='alpaca-header-container', style={'display': 'none'}),  # Preserve for callbacks
        html.Div(id='alpaca-expiration-container', style={'display': 'none'}),  # Preserve for callbacks
        html.Div(id='alpaca-export-container', style={'display': 'none'}),  # Preserve for callbacks
        html.Div(id='alpaca-table-container', style={'display': 'none'}),  # Preserve for callbacks
        html.Div(id='alpaca-status-message', style={
            'marginTop': '20px', 'padding': '10px', 'borderRadius': '4px', 'fontSize': '13px'
        }),
        
        # Hotkey listener for Terminal UX
        html.Div(id='hotkey-listener', style={'display': 'none'}),
        
        # Phase 17: Command Palette Modal
        dbc.Modal([
            dbc.ModalHeader([
                html.Div([
                    html.Span("⌘", style={
                        'backgroundColor': '#3d4050',
                        'padding': '2px 8px',
                        'borderRadius': '4px',
                        'marginRight': '8px',
                        'fontSize': '12px'
                    }),
                    html.Span("Command Palette", style={'fontWeight': 'bold'})
                ], style={'display': 'flex', 'alignItems': 'center'})
            ], close_button=True, style={'backgroundColor': '#1e2130', 'borderBottom': '1px solid #3d4050'}),
            
            dbc.ModalBody([
                # Command Input
                html.Div([
                    dcc.Input(
                        id='command-input',
                        type='text',
                        placeholder='Type a command (e.g., /gex SPY, /chain AAPL)...',
                        autoFocus=True,
                        debounce=True,
                        style={
                            'width': '100%',
                            'padding': '12px 15px',
                            'backgroundColor': '#2a2d3a',
                            'color': '#ffffff',
                            'border': '2px solid #F5C211',
                            'borderRadius': '8px',
                            'fontSize': '16px',
                            'outline': 'none'
                        }
                    ),
                ], style={'marginBottom': '15px'}),
                
                # Suggestions List
                html.Div(
                    id='command-suggestions',
                    children=[
                        html.Div([
                            html.Div([
                                html.Span("/gex", style={'color': '#F5C211', 'fontWeight': 'bold', 'marginRight': '10px'}),
                                html.Span("<TICKER>", style={'color': '#6b7280', 'fontSize': '12px'}),
                            ]),
                            html.Div("Show Gamma Exposure (GEX) chart", style={'color': '#9ca3af', 'fontSize': '12px', 'marginTop': '2px'})
                        ], style={'padding': '10px 15px', 'borderLeft': '3px solid #F5C211', 'backgroundColor': '#2a2d3a', 'marginBottom': '2px'}),
                        html.Div([
                            html.Div([
                                html.Span("/chain", style={'color': '#F5C211', 'fontWeight': 'bold', 'marginRight': '10px'}),
                                html.Span("<TICKER>", style={'color': '#6b7280', 'fontSize': '12px'}),
                            ]),
                            html.Div("Load options chain for ticker", style={'color': '#9ca3af', 'fontSize': '12px', 'marginTop': '2px'})
                        ], style={'padding': '10px 15px', 'borderLeft': '3px solid transparent', 'marginBottom': '2px'}),
                        html.Div([
                            html.Div([
                                html.Span("/flow", style={'color': '#F5C211', 'fontWeight': 'bold', 'marginRight': '10px'}),
                                html.Span("<TICKER>", style={'color': '#6b7280', 'fontSize': '12px'}),
                            ]),
                            html.Div("Show options flow tape", style={'color': '#9ca3af', 'fontSize': '12px', 'marginTop': '2px'})
                        ], style={'padding': '10px 15px', 'borderLeft': '3px solid transparent', 'marginBottom': '2px'}),
                        html.Div([
                            html.Div([
                                html.Span("/forecast", style={'color': '#F5C211', 'fontWeight': 'bold', 'marginRight': '10px'}),
                                html.Span("<TICKER>", style={'color': '#6b7280', 'fontSize': '12px'}),
                            ]),
                            html.Div("Get AI forecast for ticker", style={'color': '#9ca3af', 'fontSize': '12px', 'marginTop': '2px'})
                        ], style={'padding': '10px 15px', 'borderLeft': '3px solid transparent', 'marginBottom': '2px'}),
                        html.Div([
                            html.Div([
                                html.Span("/scanner", style={'color': '#F5C211', 'fontWeight': 'bold', 'marginRight': '10px'}),
                            ]),
                            html.Div("Switch to Scanner workspace", style={'color': '#9ca3af', 'fontSize': '12px', 'marginTop': '2px'})
                        ], style={'padding': '10px 15px', 'borderLeft': '3px solid transparent', 'marginBottom': '2px'}),
                        html.Div([
                            html.Div([
                                html.Span("/help", style={'color': '#F5C211', 'fontWeight': 'bold', 'marginRight': '10px'}),
                            ]),
                            html.Div("Show all available commands", style={'color': '#9ca3af', 'fontSize': '12px', 'marginTop': '2px'})
                        ], style={'padding': '10px 15px', 'borderLeft': '3px solid transparent', 'marginBottom': '2px'}),
                    ],
                    style={
                        'maxHeight': '300px',
                        'overflowY': 'auto',
                        'backgroundColor': '#1e2130',
                        'borderRadius': '8px'
                    }
                ),
                
                # Result Display
                html.Div(id='command-result-display', children=[]),
                
                # Help Footer
                html.Div([
                    html.Span("↑↓ Navigate", style={'marginRight': '15px', 'color': '#6b7280'}),
                    html.Span("Enter Execute", style={'marginRight': '15px', 'color': '#6b7280'}),
                    html.Span("Esc Close", style={'color': '#6b7280'}),
                ], style={
                    'marginTop': '15px',
                    'paddingTop': '10px',
                    'borderTop': '1px solid #3d4050',
                    'fontSize': '12px'
                })
            ], style={'backgroundColor': '#16181f', 'padding': '20px'}),
        ], 
        id='command-palette-modal',
        is_open=False,
        size='lg',
        centered=True,
        backdrop=True,
        ),
        
    ], style={
        'padding': '20px',
        'backgroundColor': '#16181f',
        'minHeight': '100vh',
        'color': '#ffffff'
    })


def create_enhanced_options_layout(ticker: str = "SPY") -> html.Div:
    """
    Create enhanced Alpaca-style Options Lab layout with all panels.
    Original 12-tab layout preserved for backwards compatibility.
    
    This replaces the basic layout with comprehensive analytics.
    """
    return html.Div([
        # Top bar with ticker input and controls
        html.Div([
            html.Div([
                html.Label("Symbol:", style={'color': '#9ca3af', 'fontSize': '13px', 'fontWeight': 'bold', 'marginRight': '10px'}),
                dcc.Input(
                    id='alpaca-ticker-input',
                    type='text',
                    value=ticker,
                    placeholder='Enter ticker...',
                    style={
                        'width': '120px',
                        'padding': '8px',
                        'backgroundColor': '#2a2d3a',
                        'color': '#ffffff',
                        'border': '1px solid #3d4050',
                        'borderRadius': '4px',
                        'marginRight': '10px'
                    }
                ),
                html.Button("Load Chain", id='alpaca-load-button', n_clicks=0,
                           style={
                               'padding': '8px 20px',
                               'backgroundColor': '#4caf50',
                               'color': 'white',
                               'border': 'none',
                               'borderRadius': '4px',
                               'cursor': 'pointer',
                               'fontWeight': 'bold',
                               'marginRight': '20px'
                           }),
                
                # Trading mode toggle
                html.Div([
                    html.Span("Trading Mode: ", style={'color': '#9ca3af', 'fontSize': '12px'}),
                    dcc.RadioItems(
                        id='trading-mode-toggle',
                        options=[
                            {'label': ' Paper', 'value': 'paper'},
                            {'label': ' Live', 'value': 'live'}
                        ],
                        value='paper',
                        inline=True,
                        style={'fontSize': '12px'},
                        labelStyle={'color': '#e0e0e0', 'marginRight': '10px'}
                    )
                ], style={'display': 'inline-block', 'marginRight': '20px'}),
                
                # Auto-refresh toggle
                html.Div([
                    dcc.Checklist(
                        id='auto-refresh-toggle',
                        options=[{'label': ' Auto-Refresh (30s)', 'value': 'enabled'}],
                        value=[],
                        style={'fontSize': '12px', 'color': '#e0e0e0'}
                    )
                ], style={'display': 'inline-block'})
            ], style={'display': 'flex', 'alignItems': 'center', 'flexWrap': 'wrap'})
        ], style={
            'padding': '15px',
            'backgroundColor': '#1e2130',
            'borderRadius': '8px',
            'marginBottom': '15px'
        }),
        
        # Main content with tabs
        dcc.Tabs([
            # Tab 1: Options Chain
            dcc.Tab(label='📈 Chain', children=[
                dcc.Loading(
                    id='alpaca-loading',
                    type='circle',
                    children=[
                        html.Div(id='alpaca-header-container'),
                        html.Div(id='alpaca-expiration-container'),
                        
                        # Export buttons
                        html.Div([
                            html.Button("📥 CSV", id='alpaca-export-csv-btn', n_clicks=0, style=_btn_style('#2196F3')),
                            html.Button("📥 JSON", id='alpaca-export-json-btn', n_clicks=0, style=_btn_style('#9C27B0')),
                            html.Button("🔄 Refresh", id='alpaca-refresh-btn', n_clicks=0, style=_btn_style('#FF9800')),
                        ], id='alpaca-export-container', style={
                            'marginBottom': '15px', 'padding': '10px', 'backgroundColor': '#1e2130',
                            'borderRadius': '8px', 'display': 'none', 'gap': '10px'
                        }),
                        
                        html.Div(id='alpaca-table-container')
                    ],
                    color='#4caf50'
                )
            ], style={'backgroundColor': '#16181f', 'color': '#fff'},
               selected_style={'backgroundColor': '#2a2d3a', 'color': '#4caf50'}),
            
            # Tab 2: Greeks & IV
            dcc.Tab(label='📊 Greeks & IV', children=[
                html.Div([
                    create_greeks_panel(),
                    create_iv_surface_panel()
                ], style={'padding': '15px'})
            ], style={'backgroundColor': '#16181f', 'color': '#fff'},
               selected_style={'backgroundColor': '#2a2d3a', 'color': '#4caf50'}),
            
            # Tab 3: Strategies
            dcc.Tab(label='🎯 Strategy Builder', children=[
                html.Div([
                    create_strategy_builder()
                ], style={'padding': '15px'})
            ], style={'backgroundColor': '#16181f', 'color': '#fff'},
               selected_style={'backgroundColor': '#2a2d3a', 'color': '#4caf50'}),
            
            # Tab 4: Strategy Engine (Phase 3 - IC Builder, Picker, Greeks Rollup)
            dcc.Tab(label='🦅 Strategy Engine', children=[
                create_strategy_analysis_tab()
            ], style={'backgroundColor': '#16181f', 'color': '#fff'},
               selected_style={'backgroundColor': '#2a2d3a', 'color': '#00d4ff'}),
            
            # Tab 5: ML Recommendations
            dcc.Tab(label='🤖 AI', children=[
                html.Div([
                    create_ml_recommendations_panel(),
                    
                    # AI Automation Hub (100+ improvements)
                    create_ai_automation_hub_panel()
                ], style={'padding': '15px'})
            ], style={'backgroundColor': '#16181f', 'color': '#fff'},
               selected_style={'backgroundColor': '#2a2d3a', 'color': '#4caf50'}),
            
            # Tab 6: ML Forecast (Phase 2)
            dcc.Tab(label='🔮 Forecast', children=[
                create_forecast_tab()
            ], style={'backgroundColor': '#16181f', 'color': '#fff'},
               selected_style={'backgroundColor': '#2a2d3a', 'color': '#9c27b0'}),
            
            # Tab 7: Flow Analysis
            dcc.Tab(label='🔥 Flow', children=[
                html.Div([
                    create_flow_analysis_panel()
                ], style={'padding': '15px'})
            ], style={'backgroundColor': '#16181f', 'color': '#fff'},
               selected_style={'backgroundColor': '#2a2d3a', 'color': '#4caf50'}),
            
            # Tab 7: Positions & Risk
            dcc.Tab(label='💼 Positions', children=[
                html.Div([
                    create_positions_panel(),
                    create_risk_analytics_panel()
                ], style={'padding': '15px'})
            ], style={'backgroundColor': '#16181f', 'color': '#fff'},
               selected_style={'backgroundColor': '#2a2d3a', 'color': '#4caf50'}),
            
            # Tab 8: System Status (Phase 1 Data Fabric)
            dcc.Tab(label='🔧 Status', children=[
                create_system_status_panel()
            ], style={'backgroundColor': '#16181f', 'color': '#fff'},
               selected_style={'backgroundColor': '#2a2d3a', 'color': '#4caf50'}),
            
            # Tab 9: Trade Operations (Phase 4/5)
            dcc.Tab(label='⚙️ Trade Ops', children=[
                create_trade_ops_tab()
            ], style={'backgroundColor': '#16181f', 'color': '#fff'},
               selected_style={'backgroundColor': '#2a2d3a', 'color': '#ff5722'}),
            
            # Tab 10: Research Lab (Phase 7)
            dcc.Tab(label='📊 Research', children=[
                create_research_tab()
            ], style={'backgroundColor': '#16181f', 'color': '#fff'},
               selected_style={'backgroundColor': '#2a2d3a', 'color': '#00bcd4'}),
            
            # Tab 11: Market Viz (Phase 6 - Agent-Viz)
            dcc.Tab(label='📈 Market Viz', children=[
                create_market_viz_layout(ticker='SPY', use_mock=False)  # NO MOCK DATA
            ], style={'backgroundColor': '#16181f', 'color': '#fff'},
               selected_style={'backgroundColor': '#2a2d3a', 'color': '#F5C211'}),
            
        ], style={'marginBottom': '15px'}),
        
        # Sidebar with watchlist and alerts
        html.Div([
            html.Div([
                create_watchlist_panel(),
                create_alerts_panel()
            ], style={'width': '300px', 'position': 'fixed', 'right': '20px', 'top': '100px', 'display': 'none'}),
        ], id='sidebar-container'),
        
        # Hidden components
        dcc.Dropdown(id='alpaca-expiration-dropdown', options=[], value=None, style={'display': 'none'}),
        dcc.Download(id='alpaca-download-csv'),
        dcc.Download(id='alpaca-download-json'),
        dcc.Store(id='alpaca-options-store'),
        dcc.Store(id='strategy-legs-store', data=[]),
        dcc.Store(id='positions-store', data=[]),
        dcc.Store(id='watchlist-store', data=['SPY', 'QQQ', 'AAPL']),
        dcc.Store(id='alerts-store', data=[]),
        dcc.Store(id='strategy-engine-refresh-trigger', data=0),  # Phase 3 Greeks rollup trigger
        dcc.Interval(id='alpaca-auto-load', interval=2000, n_intervals=0, max_intervals=1),
        dcc.Interval(id='auto-refresh-interval', interval=30000, n_intervals=0, disabled=True),
        
        html.Div(id='alpaca-cache-info', style={'display': 'none'}),
        html.Div(id='alpaca-order-modal-container'),
        html.Div(id='alpaca-status-message', style={
            'marginTop': '20px', 'padding': '10px', 'borderRadius': '4px', 'fontSize': '13px'
        })
        
    ], style={
        'padding': '20px',
        'backgroundColor': '#16181f',
        'minHeight': '100vh',
        'color': '#ffffff'
    })
