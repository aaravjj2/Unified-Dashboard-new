"""
Strategy Engine UI Components

Phase 3: Options Strategy & Analysis UI
- Iron Condor Builder Panel
- Strategy Picker Panel
- Max Pain Display
- Greeks Rollup Dashboard

Author: Phase 3 Options Strategy Implementation
"""

import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from typing import Dict, List, Optional


# =============================================================================
# IRON CONDOR BUILDER UI
# =============================================================================

def create_iron_condor_builder_panel() -> html.Div:
    """Create Iron Condor Auto-Builder panel."""
    return html.Div([
        html.H5([
            html.Span("🦅 Iron Condor Auto-Builder", style={'marginRight': '10px'}),
            dbc.Badge("Phase 3", color="success", className="me-2"),
            dbc.Badge("EM-Based", color="info")
        ], style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        # Input controls row
        html.Div([
            # Ticker input
            html.Div([
                html.Label("Ticker", style={'color': '#9ca3af', 'fontSize': '12px'}),
                dcc.Input(
                    id='ic-ticker-input',
                    type='text',
                    value='SPY',
                    placeholder='SPY',
                    style={
                        'width': '100%',
                        'backgroundColor': '#2a2d3a',
                        'color': '#ffffff',
                        'border': '1px solid #444',
                        'borderRadius': '4px',
                        'padding': '8px'
                    }
                )
            ], style={'flex': '1', 'marginRight': '10px'}),
            
            # Stock price
            html.Div([
                html.Label("Stock Price", style={'color': '#9ca3af', 'fontSize': '12px'}),
                dcc.Input(
                    id='ic-stock-price',
                    type='number',
                    value=500,
                    placeholder='500',
                    style={
                        'width': '100%',
                        'backgroundColor': '#2a2d3a',
                        'color': '#ffffff',
                        'border': '1px solid #444',
                        'borderRadius': '4px',
                        'padding': '8px'
                    }
                )
            ], style={'flex': '1', 'marginRight': '10px'}),
            
            # IV
            html.Div([
                html.Label("IV (%)", style={'color': '#9ca3af', 'fontSize': '12px'}),
                dcc.Input(
                    id='ic-iv-input',
                    type='number',
                    value=20,
                    placeholder='20',
                    min=5,
                    max=200,
                    style={
                        'width': '100%',
                        'backgroundColor': '#2a2d3a',
                        'color': '#ffffff',
                        'border': '1px solid #444',
                        'borderRadius': '4px',
                        'padding': '8px'
                    }
                )
            ], style={'flex': '1', 'marginRight': '10px'}),
            
            # DTE
            html.Div([
                html.Label("Days to Expiry", style={'color': '#9ca3af', 'fontSize': '12px'}),
                dcc.Input(
                    id='ic-dte-input',
                    type='number',
                    value=30,
                    placeholder='30',
                    min=1,
                    max=365,
                    style={
                        'width': '100%',
                        'backgroundColor': '#2a2d3a',
                        'color': '#ffffff',
                        'border': '1px solid #444',
                        'borderRadius': '4px',
                        'padding': '8px'
                    }
                )
            ], style={'flex': '1', 'marginRight': '10px'}),
            
            # Wing width
            html.Div([
                html.Label("Wing Width ($)", style={'color': '#9ca3af', 'fontSize': '12px'}),
                dcc.Input(
                    id='ic-wing-width',
                    type='number',
                    value=5,
                    placeholder='5',
                    min=1,
                    max=50,
                    style={
                        'width': '100%',
                        'backgroundColor': '#2a2d3a',
                        'color': '#ffffff',
                        'border': '1px solid #444',
                        'borderRadius': '4px',
                        'padding': '8px'
                    }
                )
            ], style={'flex': '1', 'marginRight': '10px'}),
            
            # SD Multiplier
            html.Div([
                html.Label("SD Multiplier", style={'color': '#9ca3af', 'fontSize': '12px'}),
                dcc.Dropdown(
                    id='ic-sd-multiplier',
                    options=[
                        {'label': '0.5 SD (~38% PoP)', 'value': 0.5},
                        {'label': '1.0 SD (~68% PoP)', 'value': 1.0},
                        {'label': '1.5 SD (~87% PoP)', 'value': 1.5},
                        {'label': '2.0 SD (~95% PoP)', 'value': 2.0}
                    ],
                    value=1.0,
                    style={'backgroundColor': '#2a2d3a', 'color': '#000'}
                )
            ], style={'flex': '1.5'})
        ], style={'display': 'flex', 'marginBottom': '15px'}),
        
        # Build button
        html.Div([
            dbc.Button(
                [html.I(className="fa fa-calculator me-2"), "Build Iron Condor"],
                id='ic-build-button',
                color='primary',
                size='lg',
                className='me-2'
            ),
            dbc.Button(
                [html.I(className="fa fa-refresh me-2"), "Reset"],
                id='ic-reset-button',
                color='secondary',
                size='lg',
                outline=True
            )
        ], style={'marginBottom': '15px'}),
        
        # Expected Move display
        html.Div([
            html.Div(id='ic-em-display', children=[
                html.Div([
                    html.Span("📊 Expected Move: ", style={'color': '#9ca3af'}),
                    html.Span("--", style={'color': '#00d4ff', 'fontWeight': 'bold', 'fontSize': '18px'})
                ])
            ])
        ], style={
            'backgroundColor': '#262a3d',
            'padding': '12px',
            'borderRadius': '8px',
            'marginBottom': '15px'
        }),
        
        # Iron Condor legs display
        html.Div([
            html.H6("📋 Iron Condor Legs", style={'color': '#00d4ff', 'marginBottom': '10px'}),
            html.Div(id='ic-legs-display', children=[
                html.Div([
                    html.Span("Click 'Build Iron Condor' to generate strikes", 
                             style={'color': '#9ca3af', 'fontStyle': 'italic'})
                ])
            ])
        ], style={
            'backgroundColor': '#262a3d',
            'padding': '15px',
            'borderRadius': '8px',
            'marginBottom': '15px'
        }),
        
        # Payoff chart
        dcc.Graph(id='ic-payoff-chart', style={'height': '350px'})
        
    ], style={
        'backgroundColor': '#1e2130',
        'padding': '20px',
        'borderRadius': '10px',
        'border': '2px solid #00d4ff'
    })


# =============================================================================
# STRATEGY PICKER UI
# =============================================================================

def create_strategy_picker_panel() -> html.Div:
    """Create Strategy Picker panel with presets."""
    return html.Div([
        html.H5([
            html.Span("🎯 Strategy Picker", style={'marginRight': '10px'}),
            dbc.Badge("Presets", color="success", className="me-2")
        ], style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        # Preset buttons
        html.Div([
            dbc.ButtonGroup([
                dbc.Button(
                    [html.Span("⚖️ "), "Neutral"],
                    id='preset-neutral',
                    color='secondary',
                    outline=True,
                    className='me-1'
                ),
                dbc.Button(
                    [html.Span("📈 "), "Bullish"],
                    id='preset-bullish',
                    color='success',
                    outline=True,
                    className='me-1'
                ),
                dbc.Button(
                    [html.Span("📉 "), "Bearish"],
                    id='preset-bearish',
                    color='danger',
                    outline=True,
                    className='me-1'
                ),
                dbc.Button(
                    [html.Span("🔥 "), "High IV"],
                    id='preset-high-iv',
                    color='warning',
                    outline=True,
                    className='me-1'
                ),
                dbc.Button(
                    [html.Span("❄️ "), "Low IV"],
                    id='preset-low-iv',
                    color='info',
                    outline=True
                ),
            ], size='sm')
        ], style={'marginBottom': '15px'}),
        
        # AI Recommendation
        html.Div([
            html.Div(id='strategy-ai-recommendation', children=[
                html.Div([
                    html.Span("🤖 AI Recommendation: ", style={'color': '#00d4ff', 'fontWeight': 'bold'}),
                    html.Span("Analyzing market conditions...", style={'color': '#9ca3af'})
                ])
            ])
        ], style={
            'backgroundColor': '#262a3d',
            'padding': '12px',
            'borderRadius': '8px',
            'marginBottom': '15px'
        }),
        
        # Strategy cards
        html.Div(id='strategy-cards-container', children=[
            _create_strategy_placeholder()
        ])
        
    ], style={
        'backgroundColor': '#1e2130',
        'padding': '20px',
        'borderRadius': '10px',
        'border': '1px solid #444'
    })


def _create_strategy_placeholder() -> html.Div:
    """Create placeholder for strategy cards."""
    return html.Div([
        html.Div([
            html.Span("Select a market view preset above", style={'color': '#9ca3af'})
        ], style={'textAlign': 'center', 'padding': '30px'})
    ])


def create_strategy_card(
    name: str,
    strategy_id: str,
    win_rate: int,
    description: str = ""
) -> dbc.Card:
    """Create a strategy card component."""
    color = 'success' if win_rate >= 60 else 'warning' if win_rate >= 40 else 'danger'
    
    return dbc.Card([
        dbc.CardBody([
            html.H6(name, style={'color': '#ffffff', 'marginBottom': '5px'}),
            html.Div([
                dbc.Badge(f"{win_rate}% Win Rate", color=color, className="me-1"),
            ]),
            html.Small(description, style={'color': '#9ca3af'}) if description else None,
            dbc.Button(
                "Select",
                id={'type': 'select-strategy', 'index': strategy_id},
                color='primary',
                size='sm',
                className='mt-2'
            )
        ])
    ], style={
        'backgroundColor': '#262a3d',
        'border': '1px solid #444',
        'marginBottom': '10px'
    })


# =============================================================================
# MAX PAIN UI
# =============================================================================

def create_max_pain_panel() -> html.Div:
    """Create Max Pain display panel."""
    return html.Div([
        html.H5([
            html.Span("💢 Max Pain Calculator", style={'marginRight': '10px'}),
            dbc.Badge("Per Expiry", color="info")
        ], style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        # Ticker and expiry selection
        html.Div([
            html.Div([
                html.Label("Ticker", style={'color': '#9ca3af', 'fontSize': '12px'}),
                dcc.Input(
                    id='maxpain-ticker',
                    type='text',
                    value='SPY',
                    style={
                        'width': '100%',
                        'backgroundColor': '#2a2d3a',
                        'color': '#ffffff',
                        'border': '1px solid #444',
                        'borderRadius': '4px',
                        'padding': '8px'
                    }
                )
            ], style={'flex': '1', 'marginRight': '10px'}),
            
            html.Div([
                html.Label("Expiration", style={'color': '#9ca3af', 'fontSize': '12px'}),
                dcc.Dropdown(
                    id='maxpain-expiry',
                    options=[],  # Populated by callback
                    placeholder='Select expiry...',
                    style={'backgroundColor': '#2a2d3a'}
                )
            ], style={'flex': '2', 'marginRight': '10px'}),
            
            html.Div([
                dbc.Button(
                    [html.I(className="fa fa-calculator me-2"), "Calculate"],
                    id='maxpain-calculate-btn',
                    color='primary'
                )
            ], style={'flex': '1', 'alignSelf': 'flex-end'})
        ], style={'display': 'flex', 'marginBottom': '15px'}),
        
        # Max Pain result display
        html.Div([
            html.Div([
                html.Div([
                    html.Span("Max Pain Strike:", style={'color': '#9ca3af', 'fontSize': '12px'}),
                    html.Div(id='maxpain-strike-value', 
                            children="$--",
                            style={'color': '#f44336', 'fontSize': '28px', 'fontWeight': 'bold'})
                ], style={'textAlign': 'center', 'flex': '1'}),
                
                html.Div([
                    html.Span("Current Price:", style={'color': '#9ca3af', 'fontSize': '12px'}),
                    html.Div(id='maxpain-current-value',
                            children="$--",
                            style={'color': '#ffeb3b', 'fontSize': '28px', 'fontWeight': 'bold'})
                ], style={'textAlign': 'center', 'flex': '1'}),
                
                html.Div([
                    html.Span("Distance:", style={'color': '#9ca3af', 'fontSize': '12px'}),
                    html.Div(id='maxpain-distance-value',
                            children="--",
                            style={'color': '#00d4ff', 'fontSize': '28px', 'fontWeight': 'bold'})
                ], style={'textAlign': 'center', 'flex': '1'})
            ], style={'display': 'flex'})
        ], style={
            'backgroundColor': '#262a3d',
            'padding': '20px',
            'borderRadius': '8px',
            'marginBottom': '15px'
        }),
        
        # Max Pain chart
        dcc.Graph(id='maxpain-chart', style={'height': '350px'})
        
    ], style={
        'backgroundColor': '#1e2130',
        'padding': '20px',
        'borderRadius': '10px',
        'border': '1px solid #444'
    })


# =============================================================================
# GREEKS ROLLUP UI
# =============================================================================

def create_greeks_rollup_panel() -> html.Div:
    """Create Position Greeks Rollup dashboard."""
    return html.Div([
        html.H5([
            html.Span("📊 Position Greeks Rollup", style={'marginRight': '10px'}),
            dbc.Badge("Portfolio", color="primary", className="me-2"),
            dbc.Badge("Per Ticker", color="info")
        ], style={'color': '#ffffff', 'marginBottom': '15px'}),
        
        # Portfolio-level Greeks summary
        html.Div([
            html.H6("🌐 Portfolio Summary", style={'color': '#00d4ff', 'marginBottom': '10px'}),
            
            html.Div([
                # Delta card
                html.Div([
                    html.Div("Net Delta", style={'color': '#9ca3af', 'fontSize': '11px'}),
                    html.Div(id='rollup-portfolio-delta',
                            children="0",
                            style={'color': '#4caf50', 'fontSize': '24px', 'fontWeight': 'bold'}),
                    html.Div(id='rollup-delta-status',
                            children="Neutral",
                            style={'fontSize': '10px'})
                ], style={
                    'backgroundColor': '#262a3d',
                    'padding': '15px',
                    'borderRadius': '6px',
                    'flex': '1',
                    'marginRight': '10px',
                    'textAlign': 'center'
                }),
                
                # Gamma card
                html.Div([
                    html.Div("Net Gamma", style={'color': '#9ca3af', 'fontSize': '11px'}),
                    html.Div(id='rollup-portfolio-gamma',
                            children="0.00",
                            style={'color': '#2196f3', 'fontSize': '24px', 'fontWeight': 'bold'}),
                    html.Div("Per $1 Move", style={'color': '#6b7280', 'fontSize': '10px'})
                ], style={
                    'backgroundColor': '#262a3d',
                    'padding': '15px',
                    'borderRadius': '6px',
                    'flex': '1',
                    'marginRight': '10px',
                    'textAlign': 'center'
                }),
                
                # Theta card
                html.Div([
                    html.Div("Daily Theta", style={'color': '#9ca3af', 'fontSize': '11px'}),
                    html.Div(id='rollup-portfolio-theta',
                            children="$0",
                            style={'color': '#f44336', 'fontSize': '24px', 'fontWeight': 'bold'}),
                    html.Div("Per Day", style={'color': '#6b7280', 'fontSize': '10px'})
                ], style={
                    'backgroundColor': '#262a3d',
                    'padding': '15px',
                    'borderRadius': '6px',
                    'flex': '1',
                    'marginRight': '10px',
                    'textAlign': 'center'
                }),
                
                # Vega card
                html.Div([
                    html.Div("Net Vega", style={'color': '#9ca3af', 'fontSize': '11px'}),
                    html.Div(id='rollup-portfolio-vega',
                            children="$0",
                            style={'color': '#ff9800', 'fontSize': '24px', 'fontWeight': 'bold'}),
                    html.Div("Per 1% IV", style={'color': '#6b7280', 'fontSize': '10px'})
                ], style={
                    'backgroundColor': '#262a3d',
                    'padding': '15px',
                    'borderRadius': '6px',
                    'flex': '1',
                    'textAlign': 'center'
                })
            ], style={'display': 'flex', 'marginBottom': '15px'}),
            
            # Risk warnings
            html.Div(id='rollup-warnings-container', children=[])
        ], style={
            'backgroundColor': '#1e2130',
            'padding': '15px',
            'borderRadius': '8px',
            'marginBottom': '15px',
            'border': '1px solid #262a3d'
        }),
        
        # Per-ticker breakdown
        html.Div([
            html.H6("📈 By Ticker", style={'color': '#00d4ff', 'marginBottom': '10px'}),
            html.Div(id='rollup-ticker-breakdown', children=[
                html.Div([
                    html.Span("No positions to display", style={'color': '#9ca3af'})
                ], style={'textAlign': 'center', 'padding': '20px'})
            ])
        ], style={
            'backgroundColor': '#1e2130',
            'padding': '15px',
            'borderRadius': '8px',
            'border': '1px solid #262a3d'
        })
        
    ], style={
        'backgroundColor': '#1a1d2e',
        'padding': '20px',
        'borderRadius': '10px',
        'border': '1px solid #444'
    })


def create_ticker_greeks_row(
    ticker: str,
    delta: float,
    gamma: float,
    theta: float,
    vega: float,
    positions: int
) -> html.Div:
    """Create a row for ticker Greeks breakdown."""
    delta_color = '#4caf50' if delta >= 0 else '#f44336'
    theta_color = '#4caf50' if theta >= 0 else '#f44336'
    
    return html.Div([
        html.Div([
            html.Strong(ticker, style={'color': '#ffffff', 'fontSize': '14px'}),
            html.Span(f" ({positions} positions)", style={'color': '#6b7280', 'fontSize': '11px'})
        ], style={'flex': '1.5'}),
        
        html.Div([
            html.Span("Δ ", style={'color': '#9ca3af'}),
            html.Span(f"{delta:+.1f}", style={'color': delta_color, 'fontWeight': 'bold'})
        ], style={'flex': '1', 'textAlign': 'center'}),
        
        html.Div([
            html.Span("Γ ", style={'color': '#9ca3af'}),
            html.Span(f"{gamma:+.2f}", style={'color': '#2196f3', 'fontWeight': 'bold'})
        ], style={'flex': '1', 'textAlign': 'center'}),
        
        html.Div([
            html.Span("Θ ", style={'color': '#9ca3af'}),
            html.Span(f"${theta:+.0f}", style={'color': theta_color, 'fontWeight': 'bold'})
        ], style={'flex': '1', 'textAlign': 'center'}),
        
        html.Div([
            html.Span("ν ", style={'color': '#9ca3af'}),
            html.Span(f"${vega:+.0f}", style={'color': '#ff9800', 'fontWeight': 'bold'})
        ], style={'flex': '1', 'textAlign': 'center'})
        
    ], style={
        'display': 'flex',
        'alignItems': 'center',
        'padding': '10px',
        'backgroundColor': '#262a3d',
        'borderRadius': '6px',
        'marginBottom': '8px'
    })


# =============================================================================
# COMBINED STRATEGY TAB
# =============================================================================

def create_strategy_analysis_tab() -> html.Div:
    """Create the complete Strategy Analysis tab content."""
    return html.Div([
        # Row 1: Iron Condor Builder + Strategy Picker
        html.Div([
            html.Div([
                create_iron_condor_builder_panel()
            ], style={'flex': '1.2', 'marginRight': '15px'}),
            
            html.Div([
                create_strategy_picker_panel()
            ], style={'flex': '0.8'})
        ], style={'display': 'flex', 'marginBottom': '20px'}),
        
        # Row 2: Max Pain + Greeks Rollup
        html.Div([
            html.Div([
                create_max_pain_panel()
            ], style={'flex': '1', 'marginRight': '15px'}),
            
            html.Div([
                create_greeks_rollup_panel()
            ], style={'flex': '1'})
        ], style={'display': 'flex'})
        
    ], style={'padding': '15px'})
