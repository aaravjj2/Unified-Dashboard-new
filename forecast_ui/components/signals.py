"""
Signal Components Module - Phase 2 ML Forecast Engine

Provides reusable signal visualization components:
- Signal badges
- Direction indicators
- Confidence meters
"""

from dash import html
import dash_bootstrap_components as dbc


def create_direction_badge(direction: str) -> dbc.Badge:
    """
    Create a direction indicator badge.
    
    Args:
        direction: BULLISH, BEARISH, or NEUTRAL
    """
    config = {
        "BULLISH": {"icon": "📈", "color": "success", "text": "BULLISH"},
        "BEARISH": {"icon": "📉", "color": "danger", "text": "BEARISH"},
        "NEUTRAL": {"icon": "➡️", "color": "warning", "text": "NEUTRAL"}
    }
    
    cfg = config.get(direction, config["NEUTRAL"])
    
    return dbc.Badge(
        [html.Span(cfg["icon"], style={'marginRight': '5px'}), cfg["text"]],
        color=cfg["color"],
        style={'fontSize': '12px', 'padding': '6px 10px'}
    )


def create_confidence_meter(confidence: float) -> html.Div:
    """
    Create a confidence meter visualization.
    
    Args:
        confidence: 0-100 confidence value
    """
    # Determine color based on confidence
    if confidence >= 70:
        color = "#4caf50"
        label = "High"
    elif confidence >= 40:
        color = "#ff9800"
        label = "Medium"
    else:
        color = "#f44336"
        label = "Low"
    
    return html.Div([
        html.Div([
            html.Span("Confidence: ", style={'color': '#9ca3af', 'fontSize': '11px'}),
            html.Span(f"{confidence:.0f}%", style={'color': color, 'fontWeight': 'bold'})
        ]),
        html.Div([
            html.Div(
                style={
                    'width': f'{confidence}%',
                    'height': '6px',
                    'backgroundColor': color,
                    'borderRadius': '3px',
                    'transition': 'width 0.3s ease'
                }
            )
        ], style={
            'width': '100%',
            'height': '6px',
            'backgroundColor': '#2a2d3a',
            'borderRadius': '3px',
            'marginTop': '4px'
        }),
        html.Span(label, style={'color': color, 'fontSize': '10px'})
    ])


def create_signal_card(
    ticker: str,
    direction: str,
    confidence: float,
    target_price: float,
    change_pct: float
) -> html.Div:
    """
    Create a compact signal card.
    
    Args:
        ticker: Stock ticker symbol
        direction: BULLISH, BEARISH, or NEUTRAL
        confidence: 0-100 confidence value
        target_price: Target price
        change_pct: Expected change percentage
    """
    direction_colors = {
        "BULLISH": "#4caf50",
        "BEARISH": "#f44336",
        "NEUTRAL": "#ff9800"
    }
    color = direction_colors.get(direction, "#ff9800")
    
    return html.Div([
        html.Div([
            html.Span(ticker, style={'color': '#fff', 'fontWeight': 'bold', 'fontSize': '16px'}),
            create_direction_badge(direction)
        ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '10px'}),
        
        html.Div([
            html.Div([
                html.Div("Target", style={'color': '#6b7280', 'fontSize': '10px'}),
                html.Div(f"${target_price:.2f}", style={'color': '#fff', 'fontSize': '14px', 'fontWeight': 'bold'})
            ], style={'flex': '1'}),
            html.Div([
                html.Div("Change", style={'color': '#6b7280', 'fontSize': '10px'}),
                html.Div(f"{change_pct:+.1f}%", style={'color': color, 'fontSize': '14px', 'fontWeight': 'bold'})
            ], style={'flex': '1', 'textAlign': 'right'})
        ], style={'display': 'flex', 'marginBottom': '8px'}),
        
        create_confidence_meter(confidence)
    ], style={
        'backgroundColor': '#262a3d',
        'padding': '12px',
        'borderRadius': '8px',
        'borderLeft': f'3px solid {color}'
    })
