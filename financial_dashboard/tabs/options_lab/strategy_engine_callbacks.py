"""
Strategy Engine Callbacks

Phase 3: Options Strategy & Analysis Callbacks
- Iron Condor Builder callbacks
- Strategy Picker callbacks
- Max Pain callbacks
- Greeks Rollup callbacks

Author: Phase 3 Options Strategy Implementation
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import dash
from dash import Input, Output, State, callback, html, dcc, ALL, MATCH
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np

from .iron_condor_engine import (
    get_iron_condor_builder,
    get_strategy_picker,
    get_max_pain_calculator,
    get_greeks_rollup,
    StrategyPicker,
    ExpectedMoveCalculator
)
from .strategy_engine_ui import (
    create_strategy_card,
    create_ticker_greeks_row
)

logger = logging.getLogger(__name__)


def register_strategy_engine_callbacks(app: dash.Dash):
    """Register all strategy engine callbacks."""
    
    # =========================================================================
    # IRON CONDOR BUILDER CALLBACKS
    # =========================================================================
    
    @app.callback(
        [
            Output('ic-em-display', 'children'),
            Output('ic-legs-display', 'children'),
            Output('ic-payoff-chart', 'figure')
        ],
        [
            Input('ic-build-button', 'n_clicks')
        ],
        [
            State('ic-ticker-input', 'value'),
            State('ic-stock-price', 'value'),
            State('ic-iv-input', 'value'),
            State('ic-dte-input', 'value'),
            State('ic-wing-width', 'value'),
            State('ic-sd-multiplier', 'value')
        ],
        prevent_initial_call=True
    )
    def build_iron_condor(
        n_clicks,
        ticker,
        stock_price,
        iv_pct,
        dte,
        wing_width,
        sd_multiplier
    ):
        """Build Iron Condor based on inputs."""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            # Validate inputs
            stock_price = float(stock_price or 100)
            iv = float(iv_pct or 20) / 100  # Convert percentage to decimal
            dte = int(dte or 30)
            wing_width = float(wing_width or 5)
            sd_multiplier = float(sd_multiplier or 1.0)
            ticker = ticker or 'SPY'
            
            # Build Iron Condor
            builder = get_iron_condor_builder()
            condor = builder.build_iron_condor(
                stock_price=stock_price,
                iv=iv,
                days_to_expiry=dte,
                wing_width=wing_width,
                sd_multiplier=sd_multiplier
            )
            condor['ticker'] = ticker
            
            # Create EM display
            em = condor['expected_move']
            em_range_low, em_range_high = stock_price - em, stock_price + em
            
            em_display = html.Div([
                html.Div([
                    html.Span("📊 Expected Move: ", style={'color': '#9ca3af'}),
                    html.Span(f"±${em:.2f}", style={'color': '#00d4ff', 'fontWeight': 'bold', 'fontSize': '20px'}),
                    html.Span(f" ({em/stock_price*100:.1f}%)", style={'color': '#9ca3af', 'marginLeft': '8px'})
                ]),
                html.Div([
                    html.Span("Range: ", style={'color': '#6b7280', 'fontSize': '12px'}),
                    html.Span(f"${em_range_low:.2f} - ${em_range_high:.2f}", 
                             style={'color': '#4caf50', 'fontSize': '12px'})
                ], style={'marginTop': '5px'}),
                html.Div([
                    html.Span(f"{sd_multiplier} SD = ~{int((1 - 2 * (1 - _norm_cdf(sd_multiplier))) * 100)}% Probability of Profit",
                             style={'color': '#ff9800', 'fontSize': '11px'})
                ], style={'marginTop': '3px'})
            ])
            
            # Create legs display
            legs = condor['legs']
            legs_display = html.Div([
                # Put side
                html.Div([
                    html.Strong("Put Side", style={'color': '#f44336', 'marginBottom': '5px', 'display': 'block'}),
                    _create_leg_row("BUY", legs['put_long']['strike'], 'Put', 'Long Wing'),
                    _create_leg_row("SELL", legs['put_short']['strike'], 'Put', f"Δ {legs['put_short'].get('delta', 'N/A')}")
                ], style={'flex': '1', 'paddingRight': '15px', 'borderRight': '1px solid #444'}),
                
                # Call side
                html.Div([
                    html.Strong("Call Side", style={'color': '#4caf50', 'marginBottom': '5px', 'display': 'block'}),
                    _create_leg_row("SELL", legs['call_short']['strike'], 'Call', f"Δ {legs['call_short'].get('delta', 'N/A')}"),
                    _create_leg_row("BUY", legs['call_long']['strike'], 'Call', 'Long Wing')
                ], style={'flex': '1', 'paddingLeft': '15px'})
            ], style={'display': 'flex'}),
            
            # Metrics summary
            metrics = condor['metrics']
            metrics_row = html.Div([
                html.Div([
                    html.Span("Profit Zone: ", style={'color': '#9ca3af', 'fontSize': '11px'}),
                    html.Span(f"${legs['put_short']['strike']:.0f} - ${legs['call_short']['strike']:.0f}",
                             style={'color': '#4caf50', 'fontWeight': 'bold'})
                ], style={'marginRight': '20px'}),
                html.Div([
                    html.Span("PoP Est: ", style={'color': '#9ca3af', 'fontSize': '11px'}),
                    html.Span(f"{metrics['pop_estimate']}%", style={'color': '#00d4ff', 'fontWeight': 'bold'})
                ])
            ], style={'display': 'flex', 'marginTop': '15px', 'paddingTop': '10px', 'borderTop': '1px solid #444'})
            
            full_legs_display = html.Div([legs_display, metrics_row])
            
            # Create payoff chart
            payoff_fig = _create_iron_condor_payoff_chart(condor)
            
            return em_display, full_legs_display, payoff_fig
            
        except Exception as e:
            logger.error(f"Error building iron condor: {e}")
            error_msg = html.Div([
                html.Span("❌ Error: ", style={'color': '#f44336'}),
                html.Span(str(e), style={'color': '#9ca3af'})
            ])
            empty_fig = _create_empty_payoff_chart()
            return error_msg, error_msg, empty_fig
    
    @app.callback(
        [
            Output('ic-stock-price', 'value'),
            Output('ic-iv-input', 'value'),
            Output('ic-dte-input', 'value'),
            Output('ic-wing-width', 'value'),
            Output('ic-sd-multiplier', 'value')
        ],
        Input('ic-reset-button', 'n_clicks'),
        prevent_initial_call=True
    )
    def reset_iron_condor_inputs(n_clicks):
        """Reset Iron Condor inputs to defaults."""
        if not n_clicks:
            raise PreventUpdate
        return 500, 20, 30, 5, 1.0
    
    # =========================================================================
    # STRATEGY PICKER CALLBACKS
    # =========================================================================
    
    @app.callback(
        [
            Output('strategy-ai-recommendation', 'children'),
            Output('strategy-cards-container', 'children')
        ],
        [
            Input('preset-neutral', 'n_clicks'),
            Input('preset-bullish', 'n_clicks'),
            Input('preset-bearish', 'n_clicks'),
            Input('preset-high-iv', 'n_clicks'),
            Input('preset-low-iv', 'n_clicks')
        ],
        prevent_initial_call=True
    )
    def update_strategy_preset(
        neutral_clicks,
        bullish_clicks,
        bearish_clicks,
        high_iv_clicks,
        low_iv_clicks
    ):
        """Update strategy cards based on preset selection."""
        ctx = dash.callback_context
        
        if not ctx.triggered:
            raise PreventUpdate
        
        button_id = ctx.triggered[0]['prop_id'].split('.')[0]
        
        preset_map = {
            'preset-neutral': 'neutral',
            'preset-bullish': 'bullish',
            'preset-bearish': 'bearish',
            'preset-high-iv': 'high_iv',
            'preset-low-iv': 'low_iv'
        }
        
        preset_name = preset_map.get(button_id, 'neutral')
        preset = StrategyPicker.get_preset(preset_name)
        
        if not preset:
            raise PreventUpdate
        
        # Create AI recommendation
        ai_rec = html.Div([
            html.Div([
                html.Span("🤖 AI Recommendation: ", style={'color': '#00d4ff', 'fontWeight': 'bold'}),
                html.Span(f"{preset['icon']} {preset['name']}", 
                         style={'color': preset['color'], 'fontWeight': 'bold'})
            ]),
            html.Div([
                html.Span(preset['description'], style={'color': '#9ca3af', 'fontSize': '12px'})
            ], style={'marginTop': '5px'})
        ])
        
        # Create strategy cards
        cards = []
        for strat in preset['strategies']:
            card = create_strategy_card(
                name=strat['name'],
                strategy_id=strat['id'],
                win_rate=strat['win_rate']
            )
            cards.append(html.Div([card], style={'marginBottom': '10px'}))
        
        cards_container = html.Div(cards)
        
        return ai_rec, cards_container
    
    # =========================================================================
    # STRATEGY SELECTION CALLBACK
    # =========================================================================
    
    @app.callback(
        Output('selected-strategy-display', 'children'),
        Input({'type': 'select-strategy', 'index': ALL}, 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_strategy_selection(n_clicks_list):
        """Handle strategy card selection."""
        ctx = dash.callback_context
        
        if not ctx.triggered or not any(n_clicks_list):
            raise PreventUpdate
        
        # Get the triggered button
        triggered = ctx.triggered[0]
        prop_id = triggered['prop_id']
        
        # Extract strategy ID from the pattern-matching ID
        import json
        id_dict = json.loads(prop_id.split('.')[0])
        strategy_id = id_dict.get('index', '')
        
        if not strategy_id:
            raise PreventUpdate
        
        # Generate strategy configuration based on strategy_id
        strategy_config = _build_strategy_config(strategy_id)
        
        if not strategy_config:
            return html.Div([
                html.P(f"Strategy '{strategy_id}' configuration not available yet.", 
                       style={'color': '#ff9800'})
            ])
        
        # Create strategy details display
        return _create_strategy_details(strategy_config)
    
    def _build_strategy_config(strategy_id: str) -> Optional[Dict]:
        """Build strategy configuration for the selected strategy."""
        # Sample stock price for demonstration (in real app, would use live data)
        stock_price = 500.0  # e.g., SPY
        
        # Strategy configurations
        configs = {
            'iron_condor': {
                'name': 'Iron Condor',
                'type': 'neutral',
                'description': 'Sell OTM put spread + OTM call spread',
                'max_profit': 'Net credit received',
                'max_loss': 'Width of spread - credit',
                'breakevens': ['Lower strike + credit', 'Higher strike - credit'],
                'legs': [
                    {'type': 'Sell Put', 'strike': stock_price * 0.95, 'premium': 2.50, 'delta': -0.25},
                    {'type': 'Buy Put', 'strike': stock_price * 0.90, 'premium': 1.00, 'delta': -0.10},
                    {'type': 'Sell Call', 'strike': stock_price * 1.05, 'premium': 2.50, 'delta': 0.25},
                    {'type': 'Buy Call', 'strike': stock_price * 1.10, 'premium': 1.00, 'delta': 0.10},
                ],
                'net_credit': 3.00,
                'margin_req': 500.0
            },
            'iron_condor_wide': {
                'name': 'Iron Condor (Wide)',
                'type': 'neutral',
                'description': 'Wider wings for higher probability',
                'max_profit': 'Net credit received',
                'max_loss': 'Width of spread - credit',
                'breakevens': ['Lower strike + credit', 'Higher strike - credit'],
                'legs': [
                    {'type': 'Sell Put', 'strike': stock_price * 0.92, 'premium': 3.00, 'delta': -0.20},
                    {'type': 'Buy Put', 'strike': stock_price * 0.85, 'premium': 1.00, 'delta': -0.08},
                    {'type': 'Sell Call', 'strike': stock_price * 1.08, 'premium': 3.00, 'delta': 0.20},
                    {'type': 'Buy Call', 'strike': stock_price * 1.15, 'premium': 1.00, 'delta': 0.08},
                ],
                'net_credit': 4.00,
                'margin_req': 700.0
            },
            'iron_butterfly': {
                'name': 'Iron Butterfly',
                'type': 'neutral',
                'description': 'ATM short straddle + OTM wing protection',
                'max_profit': 'Net credit received',
                'max_loss': 'Width of wing - credit',
                'breakevens': ['ATM strike ± credit'],
                'legs': [
                    {'type': 'Buy Put', 'strike': stock_price * 0.95, 'premium': 1.50, 'delta': -0.15},
                    {'type': 'Sell Put', 'strike': stock_price, 'premium': 4.00, 'delta': -0.50},
                    {'type': 'Sell Call', 'strike': stock_price, 'premium': 4.00, 'delta': 0.50},
                    {'type': 'Buy Call', 'strike': stock_price * 1.05, 'premium': 1.50, 'delta': 0.15},
                ],
                'net_credit': 5.00,
                'margin_req': 500.0
            },
            'short_straddle': {
                'name': 'Short Straddle',
                'type': 'neutral',
                'description': 'Sell ATM put + ATM call (undefined risk)',
                'max_profit': 'Net credit received',
                'max_loss': 'Unlimited',
                'breakevens': ['Strike ± total credit'],
                'legs': [
                    {'type': 'Sell Put', 'strike': stock_price, 'premium': 5.00, 'delta': -0.50},
                    {'type': 'Sell Call', 'strike': stock_price, 'premium': 5.00, 'delta': 0.50},
                ],
                'net_credit': 10.00,
                'margin_req': 5000.0
            },
            'short_strangle': {
                'name': 'Short Strangle',
                'type': 'neutral',
                'description': 'Sell OTM put + OTM call (undefined risk)',
                'max_profit': 'Net credit received',
                'max_loss': 'Unlimited',
                'breakevens': ['Put strike - credit', 'Call strike + credit'],
                'legs': [
                    {'type': 'Sell Put', 'strike': stock_price * 0.95, 'premium': 2.50, 'delta': -0.25},
                    {'type': 'Sell Call', 'strike': stock_price * 1.05, 'premium': 2.50, 'delta': 0.25},
                ],
                'net_credit': 5.00,
                'margin_req': 3000.0
            },
            'bull_call_spread': {
                'name': 'Bull Call Spread',
                'type': 'bullish',
                'description': 'Buy ATM call + Sell OTM call',
                'max_profit': 'Width of spread - debit',
                'max_loss': 'Net debit paid',
                'breakevens': ['Long strike + debit'],
                'legs': [
                    {'type': 'Buy Call', 'strike': stock_price, 'premium': 5.00, 'delta': 0.50},
                    {'type': 'Sell Call', 'strike': stock_price * 1.05, 'premium': 2.00, 'delta': 0.25},
                ],
                'net_credit': -3.00,  # Debit
                'margin_req': 300.0
            },
            'bull_put_spread': {
                'name': 'Bull Put Spread',
                'type': 'bullish',
                'description': 'Sell ATM put + Buy OTM put (credit spread)',
                'max_profit': 'Net credit received',
                'max_loss': 'Width of spread - credit',
                'breakevens': ['Short strike - credit'],
                'legs': [
                    {'type': 'Sell Put', 'strike': stock_price, 'premium': 5.00, 'delta': -0.50},
                    {'type': 'Buy Put', 'strike': stock_price * 0.95, 'premium': 2.00, 'delta': -0.25},
                ],
                'net_credit': 3.00,
                'margin_req': 500.0
            },
            'long_call': {
                'name': 'Long Call',
                'type': 'bullish',
                'description': 'Buy a call option (unlimited upside)',
                'max_profit': 'Unlimited',
                'max_loss': 'Premium paid',
                'breakevens': ['Strike + premium'],
                'legs': [
                    {'type': 'Buy Call', 'strike': stock_price * 1.02, 'premium': 4.00, 'delta': 0.45},
                ],
                'net_credit': -4.00,  # Debit
                'margin_req': 400.0
            },
            'cash_secured_put': {
                'name': 'Cash-Secured Put',
                'type': 'bullish',
                'description': 'Sell put with cash to cover assignment',
                'max_profit': 'Premium received',
                'max_loss': 'Strike - premium (if stock goes to 0)',
                'breakevens': ['Strike - premium'],
                'legs': [
                    {'type': 'Sell Put', 'strike': stock_price * 0.95, 'premium': 3.00, 'delta': -0.30},
                ],
                'net_credit': 3.00,
                'margin_req': stock_price * 0.95 * 100  # Full cash secured
            },
            'bear_put_spread': {
                'name': 'Bear Put Spread',
                'type': 'bearish',
                'description': 'Buy ATM put + Sell OTM put',
                'max_profit': 'Width of spread - debit',
                'max_loss': 'Net debit paid',
                'breakevens': ['Long strike - debit'],
                'legs': [
                    {'type': 'Buy Put', 'strike': stock_price, 'premium': 5.00, 'delta': -0.50},
                    {'type': 'Sell Put', 'strike': stock_price * 0.95, 'premium': 2.00, 'delta': -0.25},
                ],
                'net_credit': -3.00,  # Debit
                'margin_req': 300.0
            },
            'bear_call_spread': {
                'name': 'Bear Call Spread',
                'type': 'bearish',
                'description': 'Sell ATM call + Buy OTM call (credit spread)',
                'max_profit': 'Net credit received',
                'max_loss': 'Width of spread - credit',
                'breakevens': ['Short strike + credit'],
                'legs': [
                    {'type': 'Sell Call', 'strike': stock_price, 'premium': 5.00, 'delta': 0.50},
                    {'type': 'Buy Call', 'strike': stock_price * 1.05, 'premium': 2.00, 'delta': 0.25},
                ],
                'net_credit': 3.00,
                'margin_req': 500.0
            },
            'long_put': {
                'name': 'Long Put',
                'type': 'bearish',
                'description': 'Buy a put option (profit from downside)',
                'max_profit': 'Strike - premium (if stock goes to 0)',
                'max_loss': 'Premium paid',
                'breakevens': ['Strike - premium'],
                'legs': [
                    {'type': 'Buy Put', 'strike': stock_price * 0.98, 'premium': 4.00, 'delta': -0.45},
                ],
                'net_credit': -4.00,  # Debit
                'margin_req': 400.0
            },
            'covered_call': {
                'name': 'Covered Call',
                'type': 'bearish',
                'description': 'Own stock + Sell OTM call',
                'max_profit': 'Strike - stock cost + premium',
                'max_loss': 'Stock cost - premium',
                'breakevens': ['Stock cost - premium'],
                'legs': [
                    {'type': '100 Shares', 'strike': stock_price, 'premium': 0, 'delta': 1.00},
                    {'type': 'Sell Call', 'strike': stock_price * 1.05, 'premium': 2.50, 'delta': 0.25},
                ],
                'net_credit': 2.50,
                'margin_req': stock_price * 100
            },
            'credit_spread': {
                'name': 'Credit Spread',
                'type': 'high_iv',
                'description': 'Sell premium with limited risk',
                'max_profit': 'Net credit received',
                'max_loss': 'Width of spread - credit',
                'breakevens': ['Depends on direction'],
                'legs': [
                    {'type': 'Sell Put', 'strike': stock_price * 0.95, 'premium': 3.50, 'delta': -0.30},
                    {'type': 'Buy Put', 'strike': stock_price * 0.90, 'premium': 1.50, 'delta': -0.15},
                ],
                'net_credit': 2.00,
                'margin_req': 500.0
            },
            'jade_lizard': {
                'name': 'Jade Lizard',
                'type': 'high_iv',
                'description': 'Short put + Short call spread (no upside risk)',
                'max_profit': 'Net credit received',
                'max_loss': 'Put strike - credit',
                'breakevens': ['Put strike - credit'],
                'legs': [
                    {'type': 'Sell Put', 'strike': stock_price * 0.95, 'premium': 3.00, 'delta': -0.25},
                    {'type': 'Sell Call', 'strike': stock_price * 1.05, 'premium': 2.50, 'delta': 0.25},
                    {'type': 'Buy Call', 'strike': stock_price * 1.10, 'premium': 1.00, 'delta': 0.10},
                ],
                'net_credit': 4.50,
                'margin_req': 600.0
            },
            'long_straddle': {
                'name': 'Long Straddle',
                'type': 'low_iv',
                'description': 'Buy ATM put + ATM call (profit from big move)',
                'max_profit': 'Unlimited',
                'max_loss': 'Total premium paid',
                'breakevens': ['Strike ± total debit'],
                'legs': [
                    {'type': 'Buy Put', 'strike': stock_price, 'premium': 4.00, 'delta': -0.50},
                    {'type': 'Buy Call', 'strike': stock_price, 'premium': 4.00, 'delta': 0.50},
                ],
                'net_credit': -8.00,  # Debit
                'margin_req': 800.0
            },
            'long_strangle': {
                'name': 'Long Strangle',
                'type': 'low_iv',
                'description': 'Buy OTM put + OTM call (profit from big move)',
                'max_profit': 'Unlimited',
                'max_loss': 'Total premium paid',
                'breakevens': ['Put strike - debit', 'Call strike + debit'],
                'legs': [
                    {'type': 'Buy Put', 'strike': stock_price * 0.95, 'premium': 2.00, 'delta': -0.25},
                    {'type': 'Buy Call', 'strike': stock_price * 1.05, 'premium': 2.00, 'delta': 0.25},
                ],
                'net_credit': -4.00,  # Debit
                'margin_req': 400.0
            },
            'calendar_spread': {
                'name': 'Calendar Spread',
                'type': 'low_iv',
                'description': 'Sell near-term, buy far-term (same strike)',
                'max_profit': 'Dependent on IV expansion',
                'max_loss': 'Net debit paid',
                'breakevens': ['Around strike price'],
                'legs': [
                    {'type': 'Sell Call (Near)', 'strike': stock_price, 'premium': 2.00, 'delta': 0.50},
                    {'type': 'Buy Call (Far)', 'strike': stock_price, 'premium': 4.00, 'delta': 0.55},
                ],
                'net_credit': -2.00,  # Debit
                'margin_req': 200.0
            },
            'diagonal_spread': {
                'name': 'Diagonal Spread',
                'type': 'low_iv',
                'description': 'Calendar with different strikes',
                'max_profit': 'Dependent on price movement + IV',
                'max_loss': 'Net debit paid',
                'breakevens': ['Complex - depends on movement'],
                'legs': [
                    {'type': 'Sell Call (Near)', 'strike': stock_price * 1.02, 'premium': 1.50, 'delta': 0.40},
                    {'type': 'Buy Call (Far)', 'strike': stock_price, 'premium': 4.50, 'delta': 0.55},
                ],
                'net_credit': -3.00,  # Debit
                'margin_req': 300.0
            },
        }
        
        return configs.get(strategy_id)
    
    def _create_strategy_details(config: Dict) -> html.Div:
        """Create detailed strategy display."""
        is_credit = config['net_credit'] > 0
        credit_label = "Net Credit" if is_credit else "Net Debit"
        credit_color = '#4caf50' if is_credit else '#f44336'
        
        # Type color mapping
        type_colors = {
            'neutral': '#9ca3af',
            'bullish': '#4caf50',
            'bearish': '#f44336',
            'high_iv': '#ff9800',
            'low_iv': '#2196f3'
        }
        type_color = type_colors.get(config['type'], '#9ca3af')
        
        # Build legs table
        legs_rows = []
        for leg in config['legs']:
            row = html.Tr([
                html.Td(leg['type'], style={'color': '#00d4ff' if 'Buy' in leg['type'] else '#ff9800'}),
                html.Td(f"${leg['strike']:.0f}", style={'color': '#ffffff'}),
                html.Td(f"${leg['premium']:.2f}", style={'color': '#9ca3af'}),
                html.Td(f"{leg['delta']:+.2f}", style={'color': '#9ca3af'}),
            ])
            legs_rows.append(row)
        
        return html.Div([
            # Header
            html.Div([
                html.H5([
                    html.Span("✅ ", style={'color': '#4caf50'}),
                    config['name'],
                    dbc.Badge(config['type'].replace('_', ' ').title(), 
                             color='primary', 
                             style={'marginLeft': '10px', 'backgroundColor': type_color})
                ], style={'color': '#ffffff', 'marginBottom': '5px'}),
                html.P(config['description'], style={'color': '#9ca3af', 'fontSize': '13px'})
            ]),
            
            # Key metrics
            html.Div([
                html.Div([
                    html.Div(credit_label, style={'color': '#6b7280', 'fontSize': '11px'}),
                    html.Div(f"${abs(config['net_credit']):.2f}", 
                            style={'color': credit_color, 'fontWeight': 'bold', 'fontSize': '16px'})
                ], style={'flex': '1', 'textAlign': 'center'}),
                html.Div([
                    html.Div("Max Profit", style={'color': '#6b7280', 'fontSize': '11px'}),
                    html.Div(config['max_profit'], 
                            style={'color': '#4caf50', 'fontWeight': 'bold', 'fontSize': '12px'})
                ], style={'flex': '1', 'textAlign': 'center'}),
                html.Div([
                    html.Div("Max Loss", style={'color': '#6b7280', 'fontSize': '11px'}),
                    html.Div(config['max_loss'], 
                            style={'color': '#f44336', 'fontWeight': 'bold', 'fontSize': '12px'})
                ], style={'flex': '1', 'textAlign': 'center'}),
                html.Div([
                    html.Div("Margin Req", style={'color': '#6b7280', 'fontSize': '11px'}),
                    html.Div(f"${config['margin_req']:,.0f}", 
                            style={'color': '#ff9800', 'fontWeight': 'bold', 'fontSize': '12px'})
                ], style={'flex': '1', 'textAlign': 'center'}),
            ], style={
                'display': 'flex', 
                'backgroundColor': '#1a1a2e', 
                'padding': '15px', 
                'borderRadius': '8px',
                'marginBottom': '15px'
            }),
            
            # Legs table
            html.Div([
                html.H6("Strategy Legs", style={'color': '#ffffff', 'marginBottom': '10px'}),
                html.Table([
                    html.Thead(html.Tr([
                        html.Th("Leg", style={'color': '#9ca3af', 'textAlign': 'left', 'padding': '8px'}),
                        html.Th("Strike", style={'color': '#9ca3af', 'textAlign': 'left', 'padding': '8px'}),
                        html.Th("Premium", style={'color': '#9ca3af', 'textAlign': 'left', 'padding': '8px'}),
                        html.Th("Delta", style={'color': '#9ca3af', 'textAlign': 'left', 'padding': '8px'}),
                    ])),
                    html.Tbody(legs_rows)
                ], style={'width': '100%', 'borderCollapse': 'collapse'})
            ], style={
                'backgroundColor': '#262a3d',
                'padding': '15px',
                'borderRadius': '8px',
                'marginBottom': '15px'
            }),
            
            # Breakevens
            html.Div([
                html.Span("📊 Breakevens: ", style={'color': '#9ca3af', 'fontWeight': 'bold'}),
                html.Span(' | '.join(config['breakevens']), style={'color': '#ffffff'})
            ], style={'marginBottom': '15px'}),
            
            # Action buttons
            html.Div([
                dbc.Button(
                    [html.Span("🚀 "), "Execute Trade"],
                    id='execute-selected-strategy-btn',
                    color='success',
                    className='me-2'
                ),
                dbc.Button(
                    [html.Span("📈 "), "View Payoff Chart"],
                    id='view-payoff-btn',
                    color='info',
                    outline=True
                )
            ])
            
        ], style={
            'backgroundColor': '#1e2130',
            'padding': '20px',
            'borderRadius': '10px',
            'border': '2px solid #4caf50',
            'marginTop': '15px'
        })
    
    # =========================================================================
    # MAX PAIN CALLBACKS
    # =========================================================================
    
    @app.callback(
        [
            Output('maxpain-strike-value', 'children'),
            Output('maxpain-current-value', 'children'),
            Output('maxpain-distance-value', 'children'),
            Output('maxpain-chart', 'figure')
        ],
        Input('maxpain-calculate-btn', 'n_clicks'),
        [
            State('maxpain-ticker', 'value'),
            State('maxpain-expiry', 'value')
        ],
        prevent_initial_call=True
    )
    def calculate_max_pain(n_clicks, ticker, expiry):
        """Calculate and display Max Pain."""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            ticker = ticker or 'SPY'
            
            # Generate sample data (in production, fetch from API)
            stock_price = 500 if ticker == 'SPY' else 180  # Sample prices
            chain_data = _generate_sample_chain(stock_price)
            
            # Calculate max pain
            calculator = get_max_pain_calculator()
            result = calculator.calculate_max_pain(chain_data, stock_price)
            
            max_pain = result['max_pain']
            distance = result['distance_to_max_pain']
            distance_pct = result['distance_pct']
            
            # Create chart
            chart = calculator.create_max_pain_chart(result, ticker)
            
            # Format outputs
            mp_value = f"${max_pain:.0f}"
            curr_value = f"${stock_price:.2f}"
            dist_value = f"{'+' if distance >= 0 else ''}{distance:.2f} ({distance_pct:+.1f}%)"
            
            return mp_value, curr_value, dist_value, chart
            
        except Exception as e:
            logger.error(f"Error calculating max pain: {e}")
            empty_fig = _create_empty_chart("Max Pain Error")
            return "$--", "$--", "--", empty_fig
    
    # =========================================================================
    # GREEKS ROLLUP CALLBACKS
    # =========================================================================
    
    @app.callback(
        [
            Output('rollup-portfolio-delta', 'children'),
            Output('rollup-portfolio-gamma', 'children'),
            Output('rollup-portfolio-theta', 'children'),
            Output('rollup-portfolio-vega', 'children'),
            Output('rollup-delta-status', 'children'),
            Output('rollup-delta-status', 'style'),
            Output('rollup-warnings-container', 'children'),
            Output('rollup-ticker-breakdown', 'children')
        ],
        Input('strategy-engine-refresh-trigger', 'data'),
        prevent_initial_call=False
    )
    def update_greeks_rollup(trigger):
        """Update Greeks rollup display."""
        try:
            rollup = get_greeks_rollup()
            
            # Add sample positions if empty (for demo)
            if not rollup.positions:
                _add_sample_positions(rollup)
            
            portfolio = rollup.get_portfolio_rollup()
            risk = rollup.get_risk_summary()
            
            # Format values
            delta = portfolio['delta']
            gamma = portfolio['gamma']
            theta = portfolio['theta']
            vega = portfolio['vega']
            
            delta_str = f"{delta:+.1f}"
            gamma_str = f"{gamma:+.4f}"
            theta_str = f"${theta:+.0f}"
            vega_str = f"${vega:+.0f}"
            
            # Delta status
            if abs(delta) < 50:
                status_text = "✓ Delta Neutral"
                status_style = {'color': '#4caf50', 'fontSize': '10px'}
            elif delta > 0:
                status_text = f"📈 Long {abs(delta):.0f} delta"
                status_style = {'color': '#2196f3', 'fontSize': '10px'}
            else:
                status_text = f"📉 Short {abs(delta):.0f} delta"
                status_style = {'color': '#f44336', 'fontSize': '10px'}
            
            # Warnings
            warnings = risk['warnings']
            warnings_display = html.Div([
                html.Div([
                    dbc.Alert(w, color='warning', className='mb-1 py-1 px-2')
                    for w in warnings
                ]) if warnings else html.Div([
                    dbc.Alert("✅ No risk warnings", color='success', className='mb-0 py-1 px-2')
                ])
            ])
            
            # Ticker breakdown
            by_ticker = portfolio.get('by_ticker', {})
            if by_ticker:
                ticker_rows = [
                    create_ticker_greeks_row(
                        ticker=t,
                        delta=data['delta'],
                        gamma=data['gamma'],
                        theta=data['theta'],
                        vega=data['vega'],
                        positions=data['positions']
                    )
                    for t, data in by_ticker.items()
                ]
                ticker_breakdown = html.Div(ticker_rows)
            else:
                ticker_breakdown = html.Div([
                    html.Span("No positions to display", style={'color': '#9ca3af'})
                ], style={'textAlign': 'center', 'padding': '20px'})
            
            return (
                delta_str, gamma_str, theta_str, vega_str,
                status_text, status_style,
                warnings_display, ticker_breakdown
            )
            
        except Exception as e:
            logger.error(f"Error updating Greeks rollup: {e}")
            return "0", "0.00", "$0", "$0", "Error", {'color': '#f44336'}, html.Div(), html.Div()
    
    logger.info("✅ Strategy Engine callbacks registered")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _norm_cdf(x: float) -> float:
    """Cumulative normal distribution approximation."""
    import math
    return (1 + math.erf(x / math.sqrt(2))) / 2


def _create_leg_row(action: str, strike: float, option_type: str, note: str = "") -> html.Div:
    """Create a leg display row."""
    action_color = '#4caf50' if action == 'BUY' else '#f44336'
    
    return html.Div([
        dbc.Badge(action, color='success' if action == 'BUY' else 'danger', 
                 className='me-2', style={'width': '45px'}),
        html.Span(f"${strike:.0f} {option_type}", style={'color': '#ffffff', 'marginRight': '10px'}),
        html.Span(note, style={'color': '#6b7280', 'fontSize': '11px'})
    ], style={'marginBottom': '5px'})


def _create_iron_condor_payoff_chart(condor: Dict) -> go.Figure:
    """Create payoff chart for Iron Condor."""
    legs = condor['legs']
    stock_price = condor['stock_price']
    
    # Get strikes
    put_long_k = legs['put_long']['strike']
    put_short_k = legs['put_short']['strike']
    call_short_k = legs['call_short']['strike']
    call_long_k = legs['call_long']['strike']
    
    # Assume typical credit received (1/3 of wing width)
    wing_width = put_short_k - put_long_k
    credit = wing_width * 0.33 * 100  # $33 per contract for $5 wings
    max_loss = (wing_width * 100) - credit
    
    # Price range
    price_range = np.linspace(put_long_k * 0.95, call_long_k * 1.05, 200)
    
    payoffs = []
    for price in price_range:
        # Calculate payoff at each price
        if price <= put_long_k:
            pnl = -max_loss
        elif price <= put_short_k:
            pnl = -max_loss + (price - put_long_k) * 100
        elif price <= call_short_k:
            pnl = credit
        elif price <= call_long_k:
            pnl = credit - (price - call_short_k) * 100
        else:
            pnl = -max_loss
        
        payoffs.append(pnl)
    
    fig = go.Figure()
    
    # Payoff line
    fig.add_trace(go.Scatter(
        x=price_range,
        y=payoffs,
        mode='lines',
        line=dict(color='#4caf50', width=3),
        fill='tozeroy',
        fillcolor='rgba(76, 175, 80, 0.2)',
        name='P&L at Expiration'
    ))
    
    # Zero line
    fig.add_hline(y=0, line_dash="dash", line_color="white", opacity=0.5)
    
    # Current price
    fig.add_vline(x=stock_price, line_dash="dot", line_color="yellow",
                  annotation_text=f"Current: ${stock_price:.2f}")
    
    # Strike markers
    for strike, label, color in [
        (put_long_k, "Long Put", "#f44336"),
        (put_short_k, "Short Put", "#f44336"),
        (call_short_k, "Short Call", "#4caf50"),
        (call_long_k, "Long Call", "#4caf50")
    ]:
        fig.add_vline(x=strike, line_dash="dot", line_color=color, opacity=0.5)
    
    # Add profit zone shading
    fig.add_vrect(
        x0=put_short_k, x1=call_short_k,
        fillcolor="rgba(76, 175, 80, 0.1)",
        layer="below",
        line_width=0
    )
    
    fig.update_layout(
        title=f"{condor.get('ticker', 'N/A')} Iron Condor Payoff | Max Profit: ${credit:.0f} | Max Loss: ${max_loss:.0f}",
        xaxis_title="Stock Price at Expiration",
        yaxis_title="Profit / Loss ($)",
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=350,
        hovermode='x unified',
        showlegend=False
    )
    
    return fig


def _create_empty_payoff_chart() -> go.Figure:
    """Create empty payoff chart."""
    fig = go.Figure()
    fig.add_annotation(
        text="Click 'Build Iron Condor' to generate payoff chart",
        x=0.5, y=0.5,
        xref="paper", yref="paper",
        showarrow=False,
        font=dict(color="#9ca3af", size=14)
    )
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=350
    )
    return fig


def _create_empty_chart(title: str) -> go.Figure:
    """Create empty chart with title."""
    fig = go.Figure()
    fig.add_annotation(
        text="No data available",
        x=0.5, y=0.5,
        xref="paper", yref="paper",
        showarrow=False,
        font=dict(color="#9ca3af", size=14)
    )
    fig.update_layout(
        title=title,
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(22,33,62,0.8)',
        height=350
    )
    return fig


def _generate_sample_chain(stock_price: float) -> pd.DataFrame:
    """Generate sample options chain for max pain calculation."""
    # Create strikes around current price
    strikes = [stock_price + i * 5 for i in range(-15, 16)]
    
    data = []
    for strike in strikes:
        # Generate realistic OI distribution
        distance = abs(strike - stock_price) / stock_price
        base_oi = int(10000 * np.exp(-distance * 5))
        
        # Calls have more OI above current, puts below
        if strike > stock_price:
            call_oi = int(base_oi * 1.2)
            put_oi = int(base_oi * 0.8)
        else:
            call_oi = int(base_oi * 0.8)
            put_oi = int(base_oi * 1.2)
        
        data.append({
            'strike': strike,
            'call_oi': call_oi + np.random.randint(-500, 500),
            'put_oi': put_oi + np.random.randint(-500, 500)
        })
    
    return pd.DataFrame(data)


def _add_sample_positions(rollup):
    """Add sample positions for demo."""
    # SPY Iron Condor
    rollup.add_position('SPY', 'put', 'sell', 1, -0.15, 0.02, -0.05, 0.10)
    rollup.add_position('SPY', 'put', 'buy', 1, -0.08, 0.01, -0.03, 0.05)
    rollup.add_position('SPY', 'call', 'sell', 1, 0.15, 0.02, -0.05, 0.10)
    rollup.add_position('SPY', 'call', 'buy', 1, 0.08, 0.01, -0.03, 0.05)
    
    # AAPL Long Call
    rollup.add_position('AAPL', 'call', 'buy', 2, 0.55, 0.03, -0.08, 0.15)
    
    # NVDA Put Credit Spread
    rollup.add_position('NVDA', 'put', 'sell', 1, -0.25, 0.015, -0.04, 0.12)
    rollup.add_position('NVDA', 'put', 'buy', 1, -0.10, 0.008, -0.02, 0.06)
