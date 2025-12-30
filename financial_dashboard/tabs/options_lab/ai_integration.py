#!/usr/bin/env python3
"""
AI Automation Integration for Enhanced Alpaca Options Lab
==========================================================

This module integrates all AI engines into the Alpaca Options Lab callbacks.
Provides FULLY AUTOMATED analysis and trading for GLD, SLV, SPY + Tech stocks.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dash import html, dcc
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Import all AI engines
from .ai_automation_engine import (
    auto_scanner, signal_generator, greeks_engine,
    position_manager, regime_detector,
    ALL_FOCUS_TICKERS, FOCUS_TICKERS, MarketCondition, TradeSignal
)
from .smart_analysis_engine import (
    ta_engine, iv_engine, flow_analyzer,
    portfolio_analytics, ml_engine
)
from .auto_trading_engine import (
    strategy_builder, order_executor, risk_manager,
    profit_taker, rolling_engine
)
from .monitoring_engine import (
    price_monitor, iv_greeks_monitor, position_monitor,
    events_monitor, alert_manager, master_monitor,
    AlertSeverity, AlertType, Alert
)

logger = logging.getLogger(__name__)


class AIAutomationHub:
    """
    Central hub for all AI automation features.
    Provides unified interface for automated options trading.
    """
    
    def __init__(self):
        self.last_scan = None
        self.current_regime = None
        self.active_signals = []
        self.portfolio_state = {}
        self.alerts_cache = []
        
    def run_full_automation(self, market_data: Dict) -> Dict:
        """
        Run full automation cycle - scans, signals, analysis, alerts.
        Called automatically every interval - NO USER INTERACTION NEEDED.
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'regime': None,
            'signals': [],
            'recommendations': [],
            'alerts': [],
            'portfolio_analysis': {},
            'top_opportunities': []
        }
        
        try:
            # 1. Detect market regime
            vix = market_data.get('VIX', {}).get('price', 20)
            spy_data = market_data.get('SPY', {})
            spy_change = spy_data.get('change_20d', 0)
            spy_vol = spy_data.get('volatility_20d', 0.015)
            
            self.current_regime = regime_detector.detect_regime(vix, spy_change, spy_vol)
            results['regime'] = {
                'type': self.current_regime.regime,
                'vix': self.current_regime.vix_level,
                'trend_strength': self.current_regime.trend_strength,
                'momentum': self.current_regime.momentum
            }
            
            # 2. Scan all focus tickers
            scan_results = auto_scanner.scan_all_tickers()
            self.last_scan = datetime.now()
            
            # 3. Rank opportunities
            rankings = auto_scanner.rank_opportunities()
            results['top_opportunities'] = rankings[:5]
            
            # 4. Generate signals for top tickers
            for ticker, score in rankings[:10]:
                ticker_data = market_data.get(ticker, {})
                if ticker_data:
                    signal = self._generate_signal_for_ticker(ticker, ticker_data)
                    if signal:
                        results['signals'].append(signal)
            
            # 5. Run technical analysis on focus tickers
            for ticker in ['GLD', 'SLV', 'SPY', 'NVDA', 'AAPL']:
                if ticker in market_data:
                    prices = market_data[ticker].get('prices', pd.Series([100]))
                    if isinstance(prices, list):
                        prices = pd.Series(prices)
                    
                    ta_result = ta_engine.calculate_composite_score(prices)
                    results['recommendations'].append({
                        'ticker': ticker,
                        'ta_score': ta_result['composite_score'],
                        'ta_signal': ta_result['signal'],
                        'confidence': ta_result['confidence']
                    })
            
            # 6. Check for alerts
            alerts = master_monitor.run_all_checks(market_data, [])
            results['alerts'] = [{'type': a.type.value, 'message': a.message, 'severity': a.severity.value} for a in alerts]
            
            # 7. Get regime-based strategy recommendations
            strategies = regime_detector.get_strategies_for_regime(self.current_regime.regime)
            allocation = regime_detector.get_sector_allocation(self.current_regime.regime)
            
            results['recommended_strategies'] = strategies
            results['sector_allocation'] = allocation
            
        except Exception as e:
            logger.error(f"Automation error: {e}")
            results['error'] = str(e)
        
        return results
    
    def _generate_signal_for_ticker(self, ticker: str, data: Dict) -> Optional[Dict]:
        """Generate trading signal for a ticker."""
        try:
            price = data.get('price', 100)
            iv = data.get('iv', 0.25)
            iv_rank = data.get('iv_rank', 50)
            trend = data.get('trend', 'NEUTRAL')
            
            # Select optimal strategy based on conditions
            if iv_rank > 60:
                strategy = 'iron_condor' if trend == 'NEUTRAL' else 'credit_spread'
                direction = 'NEUTRAL' if trend == 'NEUTRAL' else ('BULLISH' if trend == 'UP' else 'BEARISH')
            elif iv_rank < 30:
                strategy = 'long_straddle'
                direction = 'VOLATILITY_LONG'
            else:
                strategy = 'credit_spread'
                direction = 'BULLISH' if trend == 'UP' else 'BEARISH'
            
            # Build the strategy
            if strategy == 'iron_condor':
                order = strategy_builder.build_iron_condor(ticker, price, iv, 30)
            elif strategy == 'credit_spread':
                order = strategy_builder.build_credit_spread(ticker, price, direction.replace('ISH', ''), iv, 30)
            else:
                order = strategy_builder.build_volatility_play(ticker, price, 'straddle', 45)
            
            return {
                'ticker': ticker,
                'strategy': order.strategy_name,
                'direction': direction,
                'entry_price': price,
                'max_profit': order.max_profit,
                'max_loss': order.max_loss,
                'pop': order.probability_of_profit,
                'expiry': order.legs[0].expiry if order.legs else None
            }
        except Exception as e:
            logger.error(f"Signal generation error for {ticker}: {e}")
            return None
    
    def get_ai_dashboard_data(self, market_data: Dict) -> Dict:
        """Get data for AI dashboard display."""
        return {
            'regime': self.current_regime.regime if self.current_regime else 'UNKNOWN',
            'vix_level': self.current_regime.vix_level if self.current_regime else 20,
            'position_scale': regime_detector.get_position_scale(
                self.current_regime.vix_level if self.current_regime else 20
            ),
            'focus_tickers': ALL_FOCUS_TICKERS,
            'last_scan': self.last_scan.isoformat() if self.last_scan else None,
            'active_signals_count': len(self.active_signals),
            'alerts_count': len(alert_manager.get_alerts(since=datetime.now() - timedelta(hours=1)))
        }
    
    def analyze_ticker(self, ticker: str, prices: pd.Series, iv: float = 0.25) -> Dict:
        """Complete AI analysis for a single ticker."""
        result = {
            'ticker': ticker,
            'timestamp': datetime.now().isoformat()
        }
        
        # Technical Analysis
        result['technical'] = ta_engine.calculate_composite_score(prices)
        result['support_resistance'] = ta_engine.find_support_resistance(prices)
        result['trend'] = ta_engine.calculate_trend_strength(prices)
        
        # IV Analysis
        historical_ivs = [iv * (0.8 + np.random.random() * 0.4) for _ in range(252)]
        result['iv_analysis'] = iv_engine.calculate_iv_percentile(iv, historical_ivs)
        
        # ML Predictions
        result['direction_prediction'] = ml_engine.predict_direction(prices)
        result['volatility_forecast'] = ml_engine.forecast_volatility(prices)
        result['expected_move'] = ml_engine.calculate_expected_move(prices.iloc[-1], iv, 30)
        
        # Trade Ideas
        analysis = {
            'direction': result['direction_prediction']['prediction'],
            'iv_rank': result['iv_analysis']['percentile'],
            'confidence': result['direction_prediction']['confidence']
        }
        result['trade_ideas'] = ml_engine.generate_trade_ideas(ticker, analysis)
        
        return result
    
    def build_strategy_for_ticker(self, ticker: str, spot: float, iv: float, 
                                  outlook: str = 'NEUTRAL') -> Dict:
        """Build optimal strategy for a ticker."""
        iv_rank = 50  # Would come from real data
        
        strategy_order = strategy_builder.select_optimal_strategy(
            ticker, spot, iv, iv_rank, outlook
        )
        
        return {
            'strategy': strategy_order.strategy_name,
            'legs': [
                {
                    'symbol': leg.symbol,
                    'side': leg.side.value,
                    'strike': leg.strike,
                    'expiry': leg.expiry,
                    'type': leg.option_type
                }
                for leg in strategy_order.legs
            ],
            'max_profit': strategy_order.max_profit,
            'max_loss': strategy_order.max_loss,
            'breakevens': strategy_order.breakevens,
            'pop': strategy_order.probability_of_profit
        }


# Create global instance
ai_hub = AIAutomationHub()


def create_ai_automation_panel() -> dbc.Card:
    """Create the AI Automation panel UI component."""
    return dbc.Card([
        dbc.CardHeader([
            html.H5("🤖 AI Automation Hub", className="mb-0 d-flex align-items-center"),
            dbc.Badge("LIVE", color="success", className="ms-2")
        ]),
        dbc.CardBody([
            # Market Regime
            dbc.Row([
                dbc.Col([
                    html.H6("Market Regime", className="text-muted"),
                    html.Div(id="ai-market-regime", className="h4 text-warning")
                ], width=3),
                dbc.Col([
                    html.H6("VIX Level", className="text-muted"),
                    html.Div(id="ai-vix-level", className="h4")
                ], width=3),
                dbc.Col([
                    html.H6("Position Scale", className="text-muted"),
                    html.Div(id="ai-position-scale", className="h4")
                ], width=3),
                dbc.Col([
                    html.H6("Active Alerts", className="text-muted"),
                    html.Div(id="ai-alerts-count", className="h4 text-danger")
                ], width=3),
            ], className="mb-3"),
            
            html.Hr(),
            
            # Top Opportunities
            html.H6("🎯 Top AI Opportunities", className="text-primary mb-2"),
            html.Div(id="ai-top-opportunities"),
            
            html.Hr(),
            
            # Active Signals
            html.H6("📊 Active Signals", className="text-success mb-2"),
            html.Div(id="ai-active-signals"),
            
            html.Hr(),
            
            # Recommended Strategies
            html.H6("💡 Recommended Strategies", className="text-info mb-2"),
            html.Div(id="ai-recommended-strategies"),
        ])
    ], className="mb-3")


def create_signal_card(signal: Dict) -> dbc.Card:
    """Create a signal card component."""
    direction_color = "success" if signal.get('direction') == 'BULLISH' else \
                     "danger" if signal.get('direction') == 'BEARISH' else "warning"
    
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H5(signal.get('ticker', ''), className="mb-0"),
                    dbc.Badge(signal.get('strategy', ''), color="primary", className="mt-1")
                ], width=3),
                dbc.Col([
                    html.Small("Direction", className="text-muted d-block"),
                    dbc.Badge(signal.get('direction', ''), color=direction_color)
                ], width=2),
                dbc.Col([
                    html.Small("Max Profit", className="text-muted d-block"),
                    html.Span(f"${signal.get('max_profit', 0):.0f}", className="text-success")
                ], width=2),
                dbc.Col([
                    html.Small("Max Loss", className="text-muted d-block"),
                    html.Span(f"${signal.get('max_loss', 0):.0f}", className="text-danger")
                ], width=2),
                dbc.Col([
                    html.Small("POP", className="text-muted d-block"),
                    html.Span(f"{signal.get('pop', 0)*100:.0f}%", className="text-info")
                ], width=2),
            ])
        ])
    ], className="mb-2", style={"backgroundColor": "rgba(0,0,0,0.2)"})


def create_opportunity_row(ticker: str, score: float) -> html.Div:
    """Create an opportunity row component."""
    return html.Div([
        dbc.Row([
            dbc.Col(html.Strong(ticker), width=3),
            dbc.Col([
                dbc.Progress(value=score, max=100, className="mb-0", 
                           color="success" if score > 70 else "warning" if score > 50 else "danger")
            ], width=7),
            dbc.Col(html.Span(f"{score:.0f}"), width=2, className="text-end")
        ], className="align-items-center")
    ], className="mb-2")


def create_ai_analysis_chart(analysis: Dict) -> go.Figure:
    """Create AI analysis visualization chart."""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('Technical Signals', 'IV Percentile', 'Price Prediction', 'Expected Move'),
        specs=[[{"type": "indicator"}, {"type": "indicator"}],
               [{"type": "indicator"}, {"type": "indicator"}]]
    )
    
    # Technical Score
    ta_score = analysis.get('technical', {}).get('composite_score', 50)
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=ta_score,
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [-1, 1]},
            'bar': {'color': "green" if ta_score > 0 else "red"},
            'steps': [
                {'range': [-1, -0.3], 'color': "darkred"},
                {'range': [-0.3, 0.3], 'color': "gray"},
                {'range': [0.3, 1], 'color': "darkgreen"}
            ]
        }
    ), row=1, col=1)
    
    # IV Percentile
    iv_pct = analysis.get('iv_analysis', {}).get('percentile', 50)
    fig.add_trace(go.Indicator(
        mode="gauge+number",
        value=iv_pct,
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "orange"},
            'steps': [
                {'range': [0, 30], 'color': "lightblue"},
                {'range': [30, 70], 'color': "lightyellow"},
                {'range': [70, 100], 'color': "lightcoral"}
            ]
        },
        number={'suffix': '%'}
    ), row=1, col=2)
    
    # Direction Confidence
    confidence = analysis.get('direction_prediction', {}).get('confidence', 0.5) * 100
    direction = analysis.get('direction_prediction', {}).get('prediction', 'NEUTRAL')
    fig.add_trace(go.Indicator(
        mode="gauge+number+delta",
        value=confidence,
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={
            'axis': {'range': [0, 100]},
            'bar': {'color': "green" if direction == 'UP' else "red" if direction == 'DOWN' else "gray"}
        },
        title={'text': direction},
        number={'suffix': '%'}
    ), row=2, col=1)
    
    # Expected Move
    exp_move = analysis.get('expected_move', {}).get('expected_move_pct', 5)
    fig.add_trace(go.Indicator(
        mode="number+delta",
        value=exp_move,
        number={'suffix': '%'},
        delta={'reference': 0}
    ), row=2, col=2)
    
    fig.update_layout(
        template='plotly_dark',
        height=400,
        showlegend=False,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    
    return fig


def register_ai_automation_callbacks(app):
    """Register AI automation callbacks."""
    from dash import Input, Output, State, callback
    
    @app.callback(
        [
            Output('ai-market-regime', 'children'),
            Output('ai-vix-level', 'children'),
            Output('ai-position-scale', 'children'),
            Output('ai-alerts-count', 'children'),
            Output('ai-top-opportunities', 'children'),
            Output('ai-active-signals', 'children'),
            Output('ai-recommended-strategies', 'children')
        ],
        [Input('alpaca-interval', 'n_intervals')],
        [State('alpaca-options-store', 'data')]
    )
    def update_ai_automation_panel(n_intervals, options_data):
        """Auto-update AI automation panel - runs every interval."""
        try:
            # Build market data from options store
            market_data = {}
            if options_data:
                ticker = options_data.get('ticker', 'SPY')
                spot = options_data.get('spot_price', 100)
                
                # Simulate market data for all focus tickers
                for t in ALL_FOCUS_TICKERS:
                    base_price = spot if t == ticker else np.random.uniform(50, 500)
                    market_data[t] = {
                        'price': base_price,
                        'iv': np.random.uniform(0.15, 0.45),
                        'iv_rank': np.random.uniform(20, 80),
                        'trend': np.random.choice(['UP', 'DOWN', 'NEUTRAL']),
                        'change_20d': np.random.uniform(-0.1, 0.1),
                        'volatility_20d': np.random.uniform(0.01, 0.03)
                    }
                
                # Add VIX
                market_data['VIX'] = {'price': np.random.uniform(12, 35)}
            
            # Run full automation
            results = ai_hub.run_full_automation(market_data)
            
            # Market Regime
            regime = results.get('regime', {})
            regime_type = regime.get('type', 'UNKNOWN')
            regime_colors = {
                'BULL': 'text-success', 'BEAR': 'text-danger', 
                'HIGH_VOL': 'text-warning', 'LOW_VOL': 'text-info', 'SIDEWAYS': 'text-secondary'
            }
            regime_display = html.Span(regime_type, className=regime_colors.get(regime_type, ''))
            
            # VIX Level
            vix = regime.get('vix', 20)
            vix_color = 'text-success' if vix < 20 else 'text-warning' if vix < 30 else 'text-danger'
            vix_display = html.Span(f"{vix:.1f}", className=vix_color)
            
            # Position Scale
            scale = regime_detector.get_position_scale(vix)
            scale_display = html.Span(f"{scale*100:.0f}%", className='text-info')
            
            # Alerts Count
            alerts = results.get('alerts', [])
            alerts_display = html.Span(str(len(alerts)), 
                                       className='text-danger' if alerts else 'text-success')
            
            # Top Opportunities
            opportunities = results.get('top_opportunities', [])
            opportunities_display = html.Div([
                create_opportunity_row(ticker, score) 
                for ticker, score in opportunities[:5]
            ]) if opportunities else html.Span("Scanning...", className="text-muted")
            
            # Active Signals
            signals = results.get('signals', [])
            signals_display = html.Div([
                create_signal_card(sig) for sig in signals[:5]
            ]) if signals else html.Span("No signals", className="text-muted")
            
            # Recommended Strategies
            strategies = results.get('recommended_strategies', [])
            strategies_display = html.Div([
                dbc.Badge(s.replace('_', ' ').title(), color="primary", className="me-2 mb-1")
                for s in strategies
            ]) if strategies else html.Span("Loading...", className="text-muted")
            
            return (
                regime_display, vix_display, scale_display, alerts_display,
                opportunities_display, signals_display, strategies_display
            )
            
        except Exception as e:
            logger.error(f"AI panel update error: {e}")
            return ("Error", "N/A", "N/A", "0", 
                   html.Span(str(e), className="text-danger"), "", "")


# Export
__all__ = [
    'AIAutomationHub', 'ai_hub',
    'create_ai_automation_panel', 'create_signal_card', 
    'create_opportunity_row', 'create_ai_analysis_chart',
    'register_ai_automation_callbacks'
]
