"""
AI Recommendations Integration
Integrates the AI Options Forecast engine with the dashboard UI.

Provides callback-ready functions for displaying AI recommendations.
"""

import logging
from typing import Dict, Any, List, Optional
from dash import html
import dash_bootstrap_components as dbc
from datetime import datetime

logger = logging.getLogger(__name__)


def get_ai_recommendations_html(symbol: str) -> html.Div:
    """
    Generate AI recommendations HTML component for a symbol.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Dash HTML component with recommendations
    """
    try:
        from engines.analysis.ai_options_forecast import AIOptionsForecast
        
        forecaster = AIOptionsForecast(confidence_threshold=0.5)
        recommendations = forecaster.get_recommendations(symbol)
        
        if not recommendations:
            return html.Div([
                html.P("No AI recommendations available", style={'color': '#9ca3af'})
            ])
        
        # Build recommendation cards
        cards = []
        for i, rec in enumerate(recommendations[:3]):  # Top 3 recommendations
            signal_color = {
                'bullish': '#4caf50',
                'bearish': '#f44336',
                'neutral': '#9ca3af',
                'volatile': '#ff9800',
            }.get(rec.direction.value, '#9ca3af')
            
            card = html.Div([
                # Header
                html.Div([
                    html.Span(f"#{i+1} ", style={'color': '#6b7280'}),
                    html.Span(rec.strategy.value.replace('_', ' ').title(), 
                             style={'fontWeight': 'bold', 'color': '#ffffff'}),
                    dbc.Badge(f"{rec.confidence:.0%}", color="info", className="ms-2"),
                    dbc.Badge(rec.direction.value.upper(), 
                             style={'backgroundColor': signal_color, 'marginLeft': '5px'}),
                ], style={'marginBottom': '8px'}),
                
                # Details
                html.Div([
                    html.Span(f"Strike: ${rec.strike_price:.2f}" if rec.strike_price else "", 
                             style={'color': '#9ca3af', 'fontSize': '12px', 'marginRight': '15px'}),
                    html.Span(f"DTE: {rec.expiration_dte}", 
                             style={'color': '#9ca3af', 'fontSize': '12px', 'marginRight': '15px'}),
                    html.Span(f"R/R: {rec.risk_reward_ratio:.2f}" if rec.risk_reward_ratio else "", 
                             style={'color': '#4caf50', 'fontSize': '12px'}),
                ]),
                
                # Reasoning
                html.P(rec.reasoning, style={
                    'color': '#6b7280', 
                    'fontSize': '11px', 
                    'marginTop': '5px',
                    'marginBottom': '0'
                }),
                
            ], style={
                'backgroundColor': '#2a2d3a',
                'padding': '12px',
                'borderRadius': '6px',
                'marginBottom': '8px',
                'borderLeft': f'3px solid {signal_color}'
            })
            
            cards.append(card)
        
        return html.Div(cards)
        
    except Exception as e:
        logger.error(f"AI recommendations error: {e}")
        return html.Div([
            html.P(f"Error loading recommendations: {str(e)[:50]}", 
                  style={'color': '#f44336', 'fontSize': '12px'})
        ])


def get_signal_summary_html(symbol: str) -> html.Div:
    """
    Generate AI signal summary HTML component.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Dash HTML component with signal summary
    """
    try:
        from engines.analysis.ai_options_forecast import AIOptionsForecast
        
        forecaster = AIOptionsForecast()
        signals = forecaster.get_signals(symbol)
        
        if not signals:
            return html.Div([
                html.P("No signals available", style={'color': '#9ca3af'})
            ])
        
        # Build signal rows
        rows = []
        for signal in signals:
            color = {
                'bullish': '#4caf50',
                'bearish': '#f44336',
                'neutral': '#9ca3af',
                'volatile': '#ff9800',
            }.get(signal.direction.value, '#9ca3af')
            
            row = html.Div([
                html.Span(signal.source.upper(), style={
                    'color': '#6b7280', 
                    'fontSize': '10px', 
                    'width': '80px',
                    'display': 'inline-block'
                }),
                dbc.Badge(signal.direction.value, style={
                    'backgroundColor': color, 
                    'width': '60px',
                    'textAlign': 'center'
                }),
                html.Span(f"{signal.confidence:.0%}", style={
                    'color': '#ffffff', 
                    'fontSize': '12px',
                    'marginLeft': '10px',
                    'width': '40px',
                    'display': 'inline-block'
                }),
                html.Span(signal.reason[:40] + "..." if len(signal.reason) > 40 else signal.reason, 
                         style={
                    'color': '#6b7280', 
                    'fontSize': '10px',
                    'marginLeft': '10px'
                }),
            ], style={'marginBottom': '5px'})
            
            rows.append(row)
        
        return html.Div(rows)
        
    except Exception as e:
        logger.error(f"Signal summary error: {e}")
        return html.Div([
            html.P(f"Error loading signals", style={'color': '#f44336', 'fontSize': '12px'})
        ])


def get_pattern_summary_html(symbol: str) -> html.Div:
    """
    Generate pattern detection summary HTML.
    
    Args:
        symbol: Stock symbol
        
    Returns:
        Dash HTML component with pattern summary
    """
    try:
        from engines.analysis.talib_patterns import scan_symbol_patterns, TALIB_AVAILABLE
        
        if not TALIB_AVAILABLE:
            return html.Div([
                html.P("TA-Lib not installed", style={'color': '#ff9800', 'fontSize': '12px'})
            ])
        
        result = scan_symbol_patterns(symbol)
        
        if 'error' in result:
            return html.Div([
                html.P(f"Error: {result['error'][:50]}", style={'color': '#f44336', 'fontSize': '12px'})
            ])
        
        patterns = result.get('patterns', [])
        
        if not patterns:
            return html.Div([
                html.P("No recent patterns detected", style={'color': '#9ca3af'})
            ])
        
        # Build pattern chips
        chips = []
        for p in patterns[:8]:
            color = '#4caf50' if p['signal'] == 'bullish' else '#f44336' if p['signal'] == 'bearish' else '#9ca3af'
            chips.append(
                dbc.Badge(p['display_name'], style={
                    'backgroundColor': color,
                    'marginRight': '5px',
                    'marginBottom': '5px',
                    'fontSize': '10px'
                })
            )
        
        return html.Div([
            html.Div(chips),
            html.Div([
                html.Span(f"Signal: ", style={'color': '#6b7280', 'fontSize': '11px'}),
                html.Span(result.get('overall_signal', 'neutral').upper(), style={
                    'color': '#4caf50' if result.get('overall_signal') == 'bullish' else '#f44336' if result.get('overall_signal') == 'bearish' else '#9ca3af',
                    'fontWeight': 'bold',
                    'fontSize': '12px'
                }),
                html.Span(f" | Bullish: {result.get('bullish_count', 0)}", 
                         style={'color': '#4caf50', 'fontSize': '11px', 'marginLeft': '15px'}),
                html.Span(f" | Bearish: {result.get('bearish_count', 0)}", 
                         style={'color': '#f44336', 'fontSize': '11px'}),
            ], style={'marginTop': '8px'})
        ])
        
    except Exception as e:
        logger.error(f"Pattern summary error: {e}")
        return html.Div([
            html.P(f"Error loading patterns", style={'color': '#f44336', 'fontSize': '12px'})
        ])


# Export
__all__ = [
    'get_ai_recommendations_html',
    'get_signal_summary_html', 
    'get_pattern_summary_html',
]
