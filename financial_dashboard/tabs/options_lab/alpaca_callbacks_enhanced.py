"""
Enhanced Alpaca Options Lab Callbacks V2

Additional callbacks for:
- Greeks visualization
- IV surface charts
- Strategy builder
- ML recommendations
- Flow analysis
- Position tracking
- Risk analytics
"""

import logging
from dash import Input, Output, State, callback, ctx, no_update
from dash import html
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime

logger = logging.getLogger(__name__)


def register_enhanced_callbacks(app):
    """
    Register all enhanced callbacks for the options lab.
    Call this function after app initialization.
    """
    
    # Greeks visualization callback
    @app.callback(
        [
            Output('greeks-delta-value', 'children'),
            Output('greeks-delta-dollars', 'children'),
            Output('greeks-gamma-value', 'children'),
            Output('greeks-gamma-change', 'children'),
            Output('greeks-theta-value', 'children'),
            Output('greeks-theta-daily', 'children'),
            Output('greeks-vega-value', 'children'),
            Output('greeks-vega-pct', 'children'),
            Output('greeks-chart', 'figure')
        ],
        [
            Input('alpaca-options-store', 'data'),
            Input('alpaca-expiration-dropdown', 'value')
        ]
    )
    def update_greeks_panel(options_data, expiration):
        """Update Greeks visualization panel."""
        empty_fig = go.Figure()
        empty_fig.update_layout(template='plotly_dark', height=350)
        
        if not options_data or not expiration:
            return "0.00", "$0", "0.00", "$0", "0.00", "$0/day", "0.00", "$0", empty_fig
        
        try:
            from .analytics import create_greeks_dashboard
            
            spot_price = options_data.get('spot_price', 100)
            chains = options_data.get('chains', {})
            chain = chains.get(expiration, {})
            
            calls = chain.get('calls', [])
            puts = chain.get('puts', [])
            
            # Calculate aggregate Greeks (simplified - sum of ATM options)
            total_delta = 0
            total_gamma = 0
            total_theta = 0
            total_vega = 0
            
            # Find ATM strike
            strikes = [c['strike'] for c in calls] if calls else []
            if strikes:
                atm_strike = min(strikes, key=lambda x: abs(x - spot_price))
                
                # Get ATM options
                atm_call = next((c for c in calls if c['strike'] == atm_strike), {})
                atm_put = next((p for p in puts if p['strike'] == atm_strike), {})
                
                total_delta = atm_call.get('delta', 0.5) + atm_put.get('delta', -0.5)
                total_gamma = atm_call.get('gamma', 0.05) + atm_put.get('gamma', 0.05)
                total_theta = atm_call.get('theta', -0.1) + atm_put.get('theta', -0.1)
                total_vega = atm_call.get('vega', 0.2) + atm_put.get('vega', 0.2)
            
            delta_dollars = total_delta * 100 * spot_price
            gamma_dollars = total_gamma * 100 * spot_price
            
            # Create chart
            fig = create_greeks_dashboard(options_data, expiration)
            
            return (
                f"{total_delta:.3f}",
                f"${delta_dollars:,.0f}",
                f"{total_gamma:.4f}",
                f"${gamma_dollars:,.0f}",
                f"{total_theta:.3f}",
                f"${total_theta * 100:.2f}/day",
                f"{total_vega:.3f}",
                f"${total_vega * 100:.2f}",
                fig
            )
            
        except Exception as e:
            logger.error(f"Greeks panel error: {e}")
            return "0.00", "$0", "0.00", "$0", "0.00", "$0/day", "0.00", "$0", empty_fig
    
    
    # IV Surface callback
    @app.callback(
        Output('iv-surface-chart', 'figure'),
        [
            Input('alpaca-options-store', 'data'),
            Input('iv-view-mode', 'value'),
            Input('alpaca-expiration-dropdown', 'value')
        ]
    )
    def update_iv_surface(options_data, view_mode, expiration):
        """Update IV surface visualization."""
        empty_fig = go.Figure()
        empty_fig.update_layout(template='plotly_dark', height=450)
        
        if not options_data:
            return empty_fig
        
        try:
            from .analytics import create_iv_surface, create_iv_skew_chart
            
            if view_mode == '3d':
                return create_iv_surface(options_data)
            elif view_mode == 'skew' and expiration:
                return create_iv_skew_chart(options_data, expiration)
            elif view_mode == 'term':
                # Term structure - IV vs DTE for ATM options
                chains = options_data.get('chains', {})
                spot = options_data.get('spot_price', 100)
                
                exps = sorted(chains.keys())
                ivs = []
                dtes = []
                
                today = datetime.now()
                
                for exp in exps:
                    chain = chains[exp]
                    calls = chain.get('calls', [])
                    
                    if calls:
                        strikes = [c['strike'] for c in calls]
                        atm = min(strikes, key=lambda x: abs(x - spot))
                        atm_call = next((c for c in calls if c['strike'] == atm), {})
                        iv = atm_call.get('impliedVolatility', 0) * 100
                        
                        exp_date = datetime.strptime(exp, '%Y-%m-%d')
                        dte = (exp_date - today).days
                        
                        ivs.append(iv)
                        dtes.append(dte)
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=dtes, y=ivs,
                    mode='lines+markers',
                    name='ATM IV',
                    line=dict(color='#4caf50', width=2),
                    marker=dict(size=8)
                ))
                fig.update_layout(
                    title='IV Term Structure (ATM)',
                    xaxis_title='Days to Expiration',
                    yaxis_title='Implied Volatility (%)',
                    template='plotly_dark',
                    height=450
                )
                return fig
            
            return empty_fig
            
        except Exception as e:
            logger.error(f"IV surface error: {e}")
            return empty_fig
    
    
    # Strategy builder callbacks
    @app.callback(
        [
            Output('strategy-legs-store', 'data'),
            Output('strategy-legs-table', 'data')
        ],
        [
            Input('strat-bull-call', 'n_clicks'),
            Input('strat-bear-put', 'n_clicks'),
            Input('strat-iron-condor', 'n_clicks'),
            Input('strat-straddle', 'n_clicks'),
            Input('strat-strangle', 'n_clicks'),
            Input('strat-butterfly', 'n_clicks'),
            Input('clear-strategy-btn', 'n_clicks')
        ],
        [
            State('alpaca-options-store', 'data'),
            State('alpaca-expiration-dropdown', 'value'),
            State('strategy-legs-store', 'data')
        ]
    )
    def update_strategy_legs(bull_call, bear_put, condor, straddle, strangle, butterfly, clear,
                            options_data, expiration, current_legs):
        """Update strategy legs based on quick strategy buttons."""
        triggered = ctx.triggered_id if hasattr(ctx, 'triggered_id') else None
        
        if triggered == 'clear-strategy-btn':
            return [], []
        
        if not options_data or not expiration:
            return current_legs or [], current_legs or []
        
        try:
            chains = options_data.get('chains', {})
            chain = chains.get(expiration, {})
            spot = options_data.get('spot_price', 100)
            
            calls = chain.get('calls', [])
            puts = chain.get('puts', [])
            
            if not calls or not puts:
                return current_legs or [], current_legs or []
            
            strikes = sorted(set([c['strike'] for c in calls]))
            atm_idx = min(range(len(strikes)), key=lambda i: abs(strikes[i] - spot))
            atm = strikes[atm_idx]
            
            legs = []
            
            if triggered == 'strat-bull-call':
                # Bull call spread
                lower = atm
                upper = strikes[min(atm_idx + 2, len(strikes)-1)]
                
                lower_call = next((c for c in calls if c['strike'] == lower), {})
                upper_call = next((c for c in calls if c['strike'] == upper), {})
                
                legs = [
                    {'leg': 1, 'type': 'CALL', 'strike': f"${lower}", 'qty': 1, 'action': 'BUY', 
                     'premium': f"${lower_call.get('ask', 0):.2f}"},
                    {'leg': 2, 'type': 'CALL', 'strike': f"${upper}", 'qty': 1, 'action': 'SELL',
                     'premium': f"${upper_call.get('bid', 0):.2f}"}
                ]
                
            elif triggered == 'strat-bear-put':
                # Bear put spread
                upper = atm
                lower = strikes[max(0, atm_idx - 2)]
                
                upper_put = next((p for p in puts if p['strike'] == upper), {})
                lower_put = next((p for p in puts if p['strike'] == lower), {})
                
                legs = [
                    {'leg': 1, 'type': 'PUT', 'strike': f"${upper}", 'qty': 1, 'action': 'BUY',
                     'premium': f"${upper_put.get('ask', 0):.2f}"},
                    {'leg': 2, 'type': 'PUT', 'strike': f"${lower}", 'qty': 1, 'action': 'SELL',
                     'premium': f"${lower_put.get('bid', 0):.2f}"}
                ]
                
            elif triggered == 'strat-iron-condor':
                # Iron condor
                put_long = strikes[max(0, atm_idx - 3)]
                put_short = strikes[max(0, atm_idx - 1)]
                call_short = strikes[min(atm_idx + 1, len(strikes)-1)]
                call_long = strikes[min(atm_idx + 3, len(strikes)-1)]
                
                legs = [
                    {'leg': 1, 'type': 'PUT', 'strike': f"${put_long}", 'qty': 1, 'action': 'BUY',
                     'premium': f"${next((p for p in puts if p['strike'] == put_long), {}).get('ask', 0):.2f}"},
                    {'leg': 2, 'type': 'PUT', 'strike': f"${put_short}", 'qty': 1, 'action': 'SELL',
                     'premium': f"${next((p for p in puts if p['strike'] == put_short), {}).get('bid', 0):.2f}"},
                    {'leg': 3, 'type': 'CALL', 'strike': f"${call_short}", 'qty': 1, 'action': 'SELL',
                     'premium': f"${next((c for c in calls if c['strike'] == call_short), {}).get('bid', 0):.2f}"},
                    {'leg': 4, 'type': 'CALL', 'strike': f"${call_long}", 'qty': 1, 'action': 'BUY',
                     'premium': f"${next((c for c in calls if c['strike'] == call_long), {}).get('ask', 0):.2f}"}
                ]
                
            elif triggered == 'strat-straddle':
                # Long straddle
                atm_call = next((c for c in calls if c['strike'] == atm), {})
                atm_put = next((p for p in puts if p['strike'] == atm), {})
                
                legs = [
                    {'leg': 1, 'type': 'CALL', 'strike': f"${atm}", 'qty': 1, 'action': 'BUY',
                     'premium': f"${atm_call.get('ask', 0):.2f}"},
                    {'leg': 2, 'type': 'PUT', 'strike': f"${atm}", 'qty': 1, 'action': 'BUY',
                     'premium': f"${atm_put.get('ask', 0):.2f}"}
                ]
                
            elif triggered == 'strat-strangle':
                # Long strangle
                put_strike = strikes[max(0, atm_idx - 2)]
                call_strike = strikes[min(atm_idx + 2, len(strikes)-1)]
                
                otm_call = next((c for c in calls if c['strike'] == call_strike), {})
                otm_put = next((p for p in puts if p['strike'] == put_strike), {})
                
                legs = [
                    {'leg': 1, 'type': 'PUT', 'strike': f"${put_strike}", 'qty': 1, 'action': 'BUY',
                     'premium': f"${otm_put.get('ask', 0):.2f}"},
                    {'leg': 2, 'type': 'CALL', 'strike': f"${call_strike}", 'qty': 1, 'action': 'BUY',
                     'premium': f"${otm_call.get('ask', 0):.2f}"}
                ]
                
            elif triggered == 'strat-butterfly':
                # Iron butterfly (sell ATM straddle, buy OTM strangle)
                wing_lower = strikes[max(0, atm_idx - 2)]
                wing_upper = strikes[min(atm_idx + 2, len(strikes)-1)]
                
                legs = [
                    {'leg': 1, 'type': 'PUT', 'strike': f"${wing_lower}", 'qty': 1, 'action': 'BUY',
                     'premium': f"${next((p for p in puts if p['strike'] == wing_lower), {}).get('ask', 0):.2f}"},
                    {'leg': 2, 'type': 'PUT', 'strike': f"${atm}", 'qty': 1, 'action': 'SELL',
                     'premium': f"${next((p for p in puts if p['strike'] == atm), {}).get('bid', 0):.2f}"},
                    {'leg': 3, 'type': 'CALL', 'strike': f"${atm}", 'qty': 1, 'action': 'SELL',
                     'premium': f"${next((c for c in calls if c['strike'] == atm), {}).get('bid', 0):.2f}"},
                    {'leg': 4, 'type': 'CALL', 'strike': f"${wing_upper}", 'qty': 1, 'action': 'BUY',
                     'premium': f"${next((c for c in calls if c['strike'] == wing_upper), {}).get('ask', 0):.2f}"}
                ]
            
            return legs, legs
            
        except Exception as e:
            logger.error(f"Strategy legs error: {e}")
            return current_legs or [], current_legs or []
    
    
    # Strategy summary and payoff diagram
    @app.callback(
        [
            Output('strat-net-premium', 'children'),
            Output('strat-max-profit', 'children'),
            Output('strat-max-loss', 'children'),
            Output('strat-breakeven', 'children'),
            Output('payoff-diagram', 'figure')
        ],
        [Input('strategy-legs-store', 'data')],
        [State('alpaca-options-store', 'data')]
    )
    def update_strategy_summary(legs, options_data):
        """Update strategy summary and payoff diagram."""
        empty_fig = go.Figure()
        empty_fig.update_layout(template='plotly_dark', height=300)
        
        if not legs or not options_data:
            return "$0.00", "$0.00", "$0.00", "$0.00", empty_fig
        
        try:
            from .analytics import create_payoff_diagram
            import numpy as np
            
            spot = options_data.get('spot_price', 100)
            
            # Parse legs and calculate
            net_premium = 0
            positions = []
            
            for leg in legs:
                strike = float(leg['strike'].replace('$', ''))
                premium = float(leg['premium'].replace('$', ''))
                is_long = leg['action'] == 'BUY'
                opt_type = leg['type'].lower()
                
                if is_long:
                    net_premium -= premium
                else:
                    net_premium += premium
                
                positions.append({
                    'type': opt_type,
                    'strike': strike,
                    'premium': premium,
                    'qty': leg['qty'],
                    'is_long': is_long
                })
            
            # Calculate max profit/loss (simplified)
            strikes = [p['strike'] for p in positions]
            min_strike = min(strikes)
            max_strike = max(strikes)
            
            # Simulate P&L at various prices
            prices = np.linspace(min_strike * 0.8, max_strike * 1.2, 100)
            pnls = np.zeros_like(prices)
            
            for pos in positions:
                if pos['type'] == 'call':
                    intrinsic = np.maximum(prices - pos['strike'], 0)
                else:
                    intrinsic = np.maximum(pos['strike'] - prices, 0)
                
                if pos['is_long']:
                    pnls += (intrinsic - pos['premium']) * pos['qty'] * 100
                else:
                    pnls += (pos['premium'] - intrinsic) * pos['qty'] * 100
            
            max_profit = max(pnls)
            max_loss = abs(min(pnls))
            
            # Find breakeven(s)
            sign_changes = np.where(np.diff(np.signbit(pnls)))[0]
            breakevens = []
            for idx in sign_changes:
                # Linear interpolation
                be = prices[idx] - pnls[idx] * (prices[idx+1] - prices[idx]) / (pnls[idx+1] - pnls[idx])
                breakevens.append(be)
            
            be_str = " / ".join([f"${be:.2f}" for be in breakevens]) if breakevens else "$0.00"
            
            # Create payoff figure
            fig = create_payoff_diagram(positions, spot)
            
            return (
                f"${net_premium * 100:,.2f}",
                f"${max_profit:,.2f}" if max_profit < 1e6 else "Unlimited",
                f"${max_loss:,.2f}",
                be_str,
                fig
            )
            
        except Exception as e:
            logger.error(f"Strategy summary error: {e}")
            return "$0.00", "$0.00", "$0.00", "$0.00", empty_fig
    
    
    # ML Recommendations callback
    @app.callback(
        [
            Output('ml-price-direction', 'children'),
            Output('ml-price-direction', 'style'),
            Output('ml-price-target', 'children'),
            Output('ml-confidence', 'children'),
            Output('ml-current-iv', 'children'),
            Output('ml-forecast-iv', 'children'),
            Output('ml-iv-rank', 'children'),
            Output('ml-strategy-recommendations', 'children'),
            Output('ml-strike-recommendations', 'children')
        ],
        [
            Input('alpaca-options-store', 'data'),
            Input('ml-outlook-selector', 'value'),
            Input('ml-risk-slider', 'value')
        ]
    )
    def update_ml_recommendations(options_data, outlook, risk_level):
        """Update ML-powered recommendations using GROQ AI."""
        default_style = {'color': '#FF9800', 'fontSize': '16px', 'fontWeight': 'bold'}
        empty_recs = [html.Div("Load options data to see recommendations", style={'color': '#6b7280'})]
        empty_strikes = [html.Div("Loading...", style={'color': '#6b7280'})]
        
        if not options_data:
            return "N/A", default_style, "$0.00", "0%", "0%", "0%", "0%", empty_recs, empty_strikes
        
        try:
            from .ml_recommendations import get_groq_recommendation
            from .strategies import suggest_strategies
            
            ticker = options_data.get('ticker', 'SPY')
            spot = options_data.get('spot_price', 100)
            
            # Get AI recommendation
            market_context = f"User outlook: {outlook}, Risk level: {risk_level}"
            recommendation = get_groq_recommendation(ticker, spot, options_data, market_context)
            
            # Parse recommendation
            strategy = recommendation.get('strategy', 'N/A')
            confidence = recommendation.get('confidence', 0.5)
            risk_level_str = recommendation.get('risk_level', 'Medium')
            
            # Direction based on strategy name
            direction = 'BULLISH' if 'bull' in strategy.lower() else 'BEARISH' if 'bear' in strategy.lower() else 'NEUTRAL'
            
            direction_style = {
                'color': '#4caf50' if direction == 'BULLISH' else '#f44336' if direction == 'BEARISH' else '#FF9800',
                'fontSize': '16px',
                'fontWeight': 'bold'
            }
            
            # Estimate target based on direction and spot
            target_mult = 1.05 if direction == 'BULLISH' else 0.95 if direction == 'BEARISH' else 1.0
            target = spot * target_mult
            
            # IV metrics (simplified)
            current_iv = "18.5%"
            forecast_iv = "19.2%"
            iv_rank = "45%"
            
            # Get strategy suggestions using our strategy module
            risk_map = {1: 'low', 2: 'moderate', 3: 'high'}
            suggestions = suggest_strategies(options_data, outlook, risk_map.get(risk_level, 'moderate'))
            
            from .alpaca_ui_enhanced import _create_strategy_card
            
            strategy_cards = []
            # Add AI recommendation first
            ai_color = '#4caf50' if 'bull' in strategy.lower() else '#f44336' if 'bear' in strategy.lower() else '#2196F3'
            strategy_cards.append(_create_strategy_card(
                f"🤖 {strategy}",
                recommendation.get('rationale', 'AI-generated recommendation'),
                ai_color
            ))
            
            # Add other suggestions
            for s in suggestions[:2]:
                color = '#4caf50' if 'bull' in s['strategy'].lower() else '#f44336' if 'bear' in s['strategy'].lower() else '#2196F3'
                strategy_cards.append(_create_strategy_card(s['strategy'], s['reasoning'], color))
            
            # Strike recommendations from AI
            strikes = recommendation.get('strikes', [str(int(spot)), str(int(spot + 10))])
            strike_items = []
            for i, strike in enumerate(strikes[:3]):
                option_type = 'call' if direction == 'BULLISH' else 'put'
                strike_items.append(html.Div([
                    html.Span(f"${strike} {option_type.upper()}", 
                             style={'color': '#4caf50' if option_type == 'call' else '#f44336', 'fontWeight': 'bold'}),
                    html.Span(f" - {recommendation.get('rationale', '')[:50]}...", style={'color': '#9ca3af', 'fontSize': '11px'})
                ], style={'marginBottom': '5px'}))
            
            if not strike_items:
                strike_items = [html.Div("No recommendations available", style={'color': '#6b7280'})]
            
            return (
                direction,
                direction_style,
                f"${target:.2f}",
                f"{confidence * 100:.0f}%",
                current_iv,
                forecast_iv,
                iv_rank,
                strategy_cards,
                strike_items
            )
            
        except Exception as e:
            logger.error(f"ML recommendations error: {e}")
            return "ERROR", default_style, "$0.00", "0%", "0%", "0%", "0%", empty_recs, empty_strikes
    
    
    # Flow analysis callback
    @app.callback(
        [
            Output('flow-pcr-volume', 'children'),
            Output('flow-pcr-volume', 'style'),
            Output('flow-pcr-oi', 'children'),
            Output('flow-pcr-oi', 'style'),
            Output('flow-sentiment', 'children'),
            Output('flow-sentiment', 'style'),
            Output('flow-max-pain', 'children'),
            Output('flow-max-pain-distance', 'children'),
            Output('flow-heatmap', 'figure')
        ],
        [
            Input('alpaca-options-store', 'data'),
            Input('alpaca-expiration-dropdown', 'value')
        ]
    )
    def update_flow_analysis(options_data, expiration):
        """Update flow analysis panel."""
        empty_fig = go.Figure()
        empty_fig.update_layout(template='plotly_dark', height=250)
        default_style = {'fontSize': '20px', 'fontWeight': 'bold', 'color': '#e0e0e0'}
        
        if not options_data or not expiration:
            return "0.00", default_style, "0.00", default_style, "N/A", default_style, "$0", "0%", empty_fig
        
        try:
            from .analytics import calculate_put_call_ratio, calculate_max_pain, create_volume_oi_heatmap
            
            spot = options_data.get('spot_price', 100)
            
            # Calculate P/C ratios
            pcr = calculate_put_call_ratio(options_data)
            vol_ratio = pcr['volume_ratio']
            oi_ratio = pcr['oi_ratio']
            
            # Determine colors based on ratios
            vol_color = '#f44336' if vol_ratio > 1.2 else '#4caf50' if vol_ratio < 0.8 else '#FF9800'
            oi_color = '#f44336' if oi_ratio > 1.2 else '#4caf50' if oi_ratio < 0.8 else '#FF9800'
            
            # Sentiment
            sentiment = pcr['volume_sentiment'].split('(')[0].strip()
            sent_color = '#f44336' if 'Bearish' in sentiment else '#4caf50' if 'Bullish' in sentiment else '#FF9800'
            
            # Max pain
            max_pain_strike, _ = calculate_max_pain(options_data, expiration)
            distance_pct = ((max_pain_strike - spot) / spot) * 100
            
            # Heatmap
            heatmap = create_volume_oi_heatmap(options_data)
            
            return (
                f"{vol_ratio:.2f}",
                {'fontSize': '20px', 'fontWeight': 'bold', 'color': vol_color},
                f"{oi_ratio:.2f}",
                {'fontSize': '20px', 'fontWeight': 'bold', 'color': oi_color},
                sentiment.upper(),
                {'fontSize': '20px', 'fontWeight': 'bold', 'color': sent_color},
                f"${max_pain_strike:.2f}",
                f"{distance_pct:+.1f}%",
                heatmap
            )
            
        except Exception as e:
            logger.error(f"Flow analysis error: {e}")
            return "0.00", default_style, "0.00", default_style, "N/A", default_style, "$0", "0%", empty_fig
    
    
    # Auto-refresh toggle
    @app.callback(
        Output('auto-refresh-interval', 'disabled'),
        [Input('auto-refresh-toggle', 'value')]
    )
    def toggle_auto_refresh(value):
        """Enable/disable auto-refresh."""
        return 'enabled' not in (value or [])
    
    
    # Auto-refresh trigger
    @app.callback(
        Output('alpaca-load-button', 'n_clicks'),
        [Input('auto-refresh-interval', 'n_intervals')],
        [State('alpaca-load-button', 'n_clicks')]
    )
    def auto_refresh_trigger(n_intervals, current_clicks):
        """Trigger refresh on interval."""
        if n_intervals and n_intervals > 0:
            return (current_clicks or 0) + 1
        return no_update
    
    
    # Sentiment Analysis Callback
    @app.callback(
        Output('sentiment-analysis-display', 'children'),
        [Input('alpaca-ticker-input', 'value')]
    )
    def update_sentiment(ticker):
        if not ticker:
            return html.Div("Enter ticker", style={'color': '#666'})
            
        try:
            from .sentiment_analyzer import get_comprehensive_sentiment
            sentiment = get_comprehensive_sentiment(ticker)
            
            color = '#4caf50' if sentiment['overall'] == 'Bullish' else '#f44336' if sentiment['overall'] == 'Bearish' else '#FF9800'
            
            return html.Div([
                html.Div([
                    html.Span("Overall: ", style={'color': '#aaa'}),
                    html.Span(sentiment['overall'], style={'color': color, 'fontWeight': 'bold'})
                ], style={'marginBottom': '5px'}),
                
                html.Div([
                    html.Span("News Score: ", style={'color': '#aaa'}),
                    html.Span(f"{sentiment['sources']['news']['score']:.2f}", style={'color': '#e0e0e0'})
                ], style={'fontSize': '12px'})
            ])
        except Exception as e:
            logger.error(f"Sentiment error: {e}")
            return html.Div("Sentiment unavailable", style={'color': '#666'})

    # Multi-Model Consensus Callback
    @app.callback(
        Output('consensus-results', 'children'),
        [Input('generate-consensus-btn', 'n_clicks')],
        [State('alpaca-options-store', 'data'),
         State('alpaca-ticker-input', 'value')]
    )
    def update_consensus(n_clicks, options_data, ticker):
        if not n_clicks or not options_data or not ticker:
            return html.Div()
            
        try:
            from .multi_model_recommendations import get_multi_model_recommendations
            import asyncio
            
            spot = options_data.get('spot_price', 100)
            
            # Run consensus
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                # If loop is running, we can't use run_until_complete
                # This happens if Dash is running with uvicorn
                # We'll try to use a thread
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, get_multi_model_recommendations(ticker, spot, options_data))
                    consensus = future.result()
            else:
                consensus = loop.run_until_complete(get_multi_model_recommendations(ticker, spot, options_data))
            
            # Store recommendation
            try:
                from .ml_performance import store_recommendation
                store_recommendation(ticker, spot, consensus)
            except Exception as e:
                logger.error(f"Failed to store recommendation: {e}")
            
            # Format results
            return html.Div([
                html.Div([
                    html.Span("Consensus: ", style={'color': '#aaa'}),
                    html.Span(consensus.get('consensus_strategy', 'Unknown'), 
                             style={'color': '#4caf50', 'fontWeight': 'bold', 'fontSize': '16px'})
                ], style={'marginBottom': '10px'}),
                
                html.Div([
                    html.Span("Confidence: ", style={'color': '#aaa'}),
                    html.Span(f"{consensus.get('confidence_score', 0):.0%}", 
                             style={'color': '#2196F3', 'fontWeight': 'bold'})
                ], style={'marginBottom': '10px'}),
                
                html.Div([
                    html.Div("Model Votes:", style={'color': '#aaa', 'fontSize': '12px', 'marginBottom': '5px'}),
                    html.Div([
                        html.Span(f"{model}: {vote}", 
                                 style={'display': 'block', 'color': '#e0e0e0', 'fontSize': '12px', 'marginLeft': '10px'})
                        for model, vote in consensus.get('model_votes', {}).items()
                    ])
                ], style={'marginBottom': '10px'}),
                
                html.Div([
                    html.Div("Rationale:", style={'color': '#aaa', 'fontSize': '12px'}),
                    html.Div(consensus.get('rationale', 'No rationale provided'), style={'color': '#fff', 'fontSize': '12px', 'fontStyle': 'italic'})
                ])
            ])
            
        except Exception as e:
            logger.error(f"Consensus error: {e}")
            return html.Div(f"Error generating consensus: {str(e)}", style={'color': 'red'})

    
    # Forecast dropdown population
    @app.callback(
        [Output('forecast-expiration-dropdown', 'options'),
         Output('forecast-strike-dropdown', 'options')],
        [Input('alpaca-options-store', 'data')]
    )
    def populate_forecast_dropdowns(options_data):
        if not options_data:
            return [], []
        
        expirations = []
        strikes = set()
        
        chains = options_data.get('chains', {})
        for exp, chain in chains.items():
            expirations.append({'label': exp, 'value': exp})
            for c in chain.get('calls', []):
                strikes.add(c.get('strike', 0))
        
        strike_options = [{'label': f'${s:.0f}', 'value': s} for s in sorted(strikes)]
        return expirations[:8], strike_options[:20]  # Limit options
    
    
    # Monte Carlo Forecast Callback
    @app.callback(
        Output('forecast-results', 'children'),
        [Input('generate-forecast-btn', 'n_clicks')],
        [State('alpaca-options-store', 'data'),
         State('alpaca-ticker-input', 'value'),
         State('forecast-expiration-dropdown', 'value'),
         State('forecast-strike-dropdown', 'value'),
         State('forecast-type-radio', 'value')]
    )
    def generate_ai_forecast(n_clicks, options_data, ticker, expiration, strike, option_type):
        if not n_clicks or not options_data or not ticker:
            return html.Div()
        
        try:
            import numpy as np
            from datetime import datetime, timedelta
            import plotly.graph_objects as go
            
            spot = options_data.get('spot_price', 100)
            strike = float(strike) if strike else spot
            
            # Find contract IV
            iv = 0.30  # Default
            chains = options_data.get('chains', {})
            if expiration and expiration in chains:
                chain = chains[expiration]
                contracts = chain.get('calls' if option_type == 'call' else 'puts', [])
                for c in contracts:
                    if abs(c.get('strike', 0) - strike) < 1:
                        iv = c.get('impliedVolatility', 0.30) or 0.30
                        break
            
            # Monte Carlo Simulation
            days = 5
            simulations = 500
            dt = 1/252
            r = 0.05  # Risk-free rate
            
            paths = np.zeros((simulations, days + 1))
            paths[:, 0] = spot
            
            for t in range(1, days + 1):
                z = np.random.standard_normal(simulations)
                paths[:, t] = paths[:, t-1] * np.exp((r - 0.5 * iv**2) * dt + iv * np.sqrt(dt) * z)
            
            # Calculate option payoffs at end
            final_prices = paths[:, -1]
            if option_type == 'call':
                payoffs = np.maximum(final_prices - strike, 0)
            else:
                payoffs = np.maximum(strike - final_prices, 0)
            
            # Statistics
            forecast_price = np.median(final_prices)
            price_low = np.percentile(final_prices, 10)
            price_high = np.percentile(final_prices, 90)
            prob_profit = np.mean(payoffs > 0) * 100
            expected_payoff = np.mean(payoffs)
            
            # Price change
            price_change_pct = ((forecast_price - spot) / spot) * 100
            
            # Determine signal
            if price_change_pct > 5:
                signal = "🚀 STRONG BUY"
                signal_color = '#4caf50'
            elif price_change_pct > 2:
                signal = "📈 BUY"
                signal_color = '#8bc34a'
            elif price_change_pct < -5:
                signal = "🔻 STRONG SELL"
                signal_color = '#f44336'
            elif price_change_pct < -2:
                signal = "📉 SELL"
                signal_color = '#ff5722'
            else:
                signal = "➡️ NEUTRAL"
                signal_color = '#FF9800'
            
            # Create forecast chart
            dates = [(datetime.now() + timedelta(days=i)).strftime('%m/%d') for i in range(days + 1)]
            
            fig = go.Figure()
            
            # Confidence bands
            upper = [np.percentile(paths[:, i], 90) for i in range(days + 1)]
            lower = [np.percentile(paths[:, i], 10) for i in range(days + 1)]
            median = [np.median(paths[:, i]) for i in range(days + 1)]
            
            fig.add_trace(go.Scatter(x=dates, y=upper, mode='lines', line=dict(width=0), showlegend=False))
            fig.add_trace(go.Scatter(x=dates, y=lower, mode='lines', line=dict(width=0),
                                    fill='tonexty', fillcolor='rgba(33,150,243,0.2)', showlegend=False))
            fig.add_trace(go.Scatter(x=dates, y=median, mode='lines+markers',
                                    line=dict(color='#2196F3', width=2), name='Forecast'))
            fig.add_hline(y=spot, line_dash="dash", line_color="gray", annotation_text=f"Current: ${spot:.2f}")
            fig.add_hline(y=strike, line_dash="dot", line_color="orange", annotation_text=f"Strike: ${strike:.0f}")
            
            fig.update_layout(
                title=f"5-Day Monte Carlo Forecast",
                xaxis_title="Date",
                yaxis_title="Stock Price ($)",
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(30,33,48,0.8)',
                height=250,
                margin=dict(l=40, r=40, t=40, b=40)
            )
            
            return html.Div([
                # Signal header
                html.Div([
                    html.Span(signal, style={'fontSize': '18px', 'fontWeight': 'bold', 'color': signal_color}),
                    html.Span(f" | {ticker} {option_type.upper()} ${strike:.0f}", style={'color': '#aaa', 'marginLeft': '10px'})
                ], style={'marginBottom': '10px'}),
                
                # Metrics row
                html.Div([
                    html.Div([
                        html.Div("Forecast", style={'color': '#6b7280', 'fontSize': '10px'}),
                        html.Div(f"${forecast_price:.2f}", style={'color': signal_color, 'fontWeight': 'bold'})
                    ], style={'flex': '1', 'textAlign': 'center'}),
                    html.Div([
                        html.Div("Change", style={'color': '#6b7280', 'fontSize': '10px'}),
                        html.Div(f"{price_change_pct:+.1f}%", style={'color': signal_color, 'fontWeight': 'bold'})
                    ], style={'flex': '1', 'textAlign': 'center'}),
                    html.Div([
                        html.Div("Prob. Profit", style={'color': '#6b7280', 'fontSize': '10px'}),
                        html.Div(f"{prob_profit:.0f}%", style={'color': '#2196F3', 'fontWeight': 'bold'})
                    ], style={'flex': '1', 'textAlign': 'center'}),
                    html.Div([
                        html.Div("Exp. Payoff", style={'color': '#6b7280', 'fontSize': '10px'}),
                        html.Div(f"${expected_payoff:.2f}", style={'color': '#4caf50', 'fontWeight': 'bold'})
                    ], style={'flex': '1', 'textAlign': 'center'}),
                ], style={'display': 'flex', 'marginBottom': '10px', 'backgroundColor': '#1a1a2e', 'padding': '10px', 'borderRadius': '4px'}),
                
                # Chart
                dcc.Graph(figure=fig, config={'displayModeBar': False}),
                
                # Range info
                html.Div([
                    html.Span("5-Day Range: ", style={'color': '#aaa'}),
                    html.Span(f"${price_low:.2f} - ${price_high:.2f}", style={'color': '#e0e0e0'}),
                    html.Span(f" | IV: {iv*100:.1f}%", style={'color': '#FF9800', 'marginLeft': '15px'})
                ], style={'fontSize': '12px', 'marginTop': '5px'})
            ])
            
        except Exception as e:
            logger.error(f"Forecast error: {e}")
            return html.Div(f"Error: {str(e)}", style={'color': 'red'})
    
    
    logger.info("✅ Enhanced callbacks registered successfully")
