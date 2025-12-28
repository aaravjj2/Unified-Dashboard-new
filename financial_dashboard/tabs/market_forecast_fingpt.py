"""
FinGPT Forecast Panel - Integration for Market Forecast Tab
============================================================
Provides LLM-powered stock price movement predictions using:
- News sentiment analysis
- Fundamental data integration
- RAG-based context retrieval
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from dash import dcc, html, callback_context
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


# ==============================================================================
# COMPONENT IDS
# ==============================================================================

FINGPT_IDS = {
    'ticker_input': 'fingpt-ticker-input',
    'run_btn': 'fingpt-run-btn',
    'weeks_slider': 'fingpt-weeks-slider',
    'include_financials': 'fingpt-include-financials',
    'model_select': 'fingpt-model-select',
    'prediction_display': 'fingpt-prediction-display',
    'confidence_gauge': 'fingpt-confidence-gauge',
    'analysis_text': 'fingpt-analysis-text',
    'rationale_text': 'fingpt-rationale-text',
    'provenance_info': 'fingpt-provenance-info',
    'store': 'fingpt-store',
    'status': 'fingpt-status',
    'history_table': 'fingpt-history-table',
}


# ==============================================================================
# COLORS
# ==============================================================================

COLORS = {
    'background': '#0d1117',
    'card': '#161b22',
    'border': '#30363d',
    'text': '#f0f6fc',
    'muted': '#8b949e',
    'success': '#3fb950',
    'danger': '#f85149',
    'warning': '#d29922',
    'info': '#58a6ff',
    'primary': '#238636',
    'up': '#00C805',
    'down': '#FF5252',
    'neutral': '#FFC107',
}


# ==============================================================================
# LAYOUT
# ==============================================================================

def create_fingpt_panel() -> html.Div:
    """Create the FinGPT Forecast panel for Market Forecast tab."""
    
    return html.Div([
        # Header
        dbc.Card([
            dbc.CardHeader([
                html.Div([
                    html.I(className="bi bi-robot me-2", style={'color': COLORS['info']}),
                    html.Span("FinGPT AI Forecast", className="fw-bold"),
                    dbc.Badge("LLM", color="info", className="ms-2", pill=True),
                ], className="d-flex align-items-center"),
            ], className="bg-dark border-secondary"),
            
            dbc.CardBody([
                # Input Row
                dbc.Row([
                    # Ticker Input
                    dbc.Col([
                        dbc.Label("Symbol", className="small text-muted"),
                        dbc.Input(
                            id=FINGPT_IDS['ticker_input'],
                            type="text",
                            placeholder="AAPL",
                            value="AAPL",
                            className="bg-dark text-white border-secondary",
                        ),
                    ], width=4),
                    
                    # News History
                    dbc.Col([
                        dbc.Label("News Weeks", className="small text-muted"),
                        dcc.Slider(
                            id=FINGPT_IDS['weeks_slider'],
                            min=1,
                            max=8,
                            step=1,
                            value=4,
                            marks={i: str(i) for i in [1, 2, 4, 8]},
                            className="mt-2",
                        ),
                    ], width=4),
                    
                    # Run Button
                    dbc.Col([
                        dbc.Label("\u00a0", className="small text-muted d-block"),  # Spacer
                        dbc.Button([
                            html.I(className="bi bi-lightning-charge me-2"),
                            "Predict"
                        ],
                            id=FINGPT_IDS['run_btn'],
                            color="success",
                            className="w-100",
                        ),
                    ], width=4),
                ], className="mb-3"),
                
                # Options Row
                dbc.Row([
                    dbc.Col([
                        dbc.Checklist(
                            id=FINGPT_IDS['include_financials'],
                            options=[{'label': ' Include Fundamentals', 'value': 'include'}],
                            value=['include'],
                            inline=True,
                            className="small text-muted",
                        ),
                    ], width=6),
                    dbc.Col([
                        dcc.Dropdown(
                            id=FINGPT_IDS['model_select'],
                            options=[
                                {'label': 'Default (GPT-4o-mini)', 'value': 'default'},
                                {'label': 'OpenAI GPT-4', 'value': 'gpt4'},
                                {'label': 'Claude 3.5', 'value': 'claude'},
                                {'label': 'Mock (Testing)', 'value': 'mock'},
                            ],
                            value='default',
                            className="bg-dark",
                            style={'fontSize': '0.85rem'},
                        ),
                    ], width=6),
                ]),
                
                # Status
                html.Div(id=FINGPT_IDS['status'], className="mt-2"),
                
            ], className="bg-dark"),
        ], className="bg-dark border-secondary mb-3"),
        
        # Prediction Results Card
        dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-graph-up-arrow me-2"),
                "Prediction Results"
            ], className="bg-dark border-secondary"),
            
            dbc.CardBody([
                # Prediction Display
                html.Div(
                    id=FINGPT_IDS['prediction_display'],
                    children=_empty_prediction_display(),
                ),
                
                html.Hr(className="border-secondary my-3"),
                
                # Analysis Section
                html.Div([
                    html.H6([
                        html.I(className="bi bi-chat-text me-2"),
                        "Analysis"
                    ], className="text-muted"),
                    html.Div(
                        id=FINGPT_IDS['analysis_text'],
                        className="p-2 rounded",
                        style={'backgroundColor': COLORS['card'], 'minHeight': '60px'},
                        children=html.Span("Run prediction to see AI analysis", className="text-muted small"),
                    ),
                ], className="mb-3"),
                
                # Rationale Section
                html.Div([
                    html.H6([
                        html.I(className="bi bi-lightbulb me-2"),
                        "Rationale"
                    ], className="text-muted"),
                    html.Div(
                        id=FINGPT_IDS['rationale_text'],
                        className="p-2 rounded",
                        style={'backgroundColor': COLORS['card'], 'minHeight': '40px'},
                        children=html.Span("Rationale will appear here", className="text-muted small"),
                    ),
                ], className="mb-3"),
                
                # Provenance Info
                html.Div([
                    html.Small([
                        html.I(className="bi bi-info-circle me-1"),
                        html.Span(id=FINGPT_IDS['provenance_info'], children="No prediction yet"),
                    ], className="text-muted"),
                ]),
                
            ], className="bg-dark"),
        ], className="bg-dark border-secondary mb-3"),
        
        # Confidence Gauge
        dbc.Card([
            dbc.CardBody([
                dcc.Graph(
                    id=FINGPT_IDS['confidence_gauge'],
                    figure=_create_confidence_gauge(0.5, "neutral"),
                    config={'displayModeBar': False},
                    style={'height': '150px'},
                ),
            ], className="bg-dark p-1"),
        ], className="bg-dark border-secondary mb-3"),
        
        # Prediction History
        dbc.Card([
            dbc.CardHeader([
                html.I(className="bi bi-clock-history me-2"),
                "Recent Predictions"
            ], className="bg-dark border-secondary"),
            dbc.CardBody([
                html.Div(
                    id=FINGPT_IDS['history_table'],
                    children=html.Span("No prediction history yet", className="text-muted small"),
                ),
            ], className="bg-dark"),
        ], className="bg-dark border-secondary"),
        
        # Store for prediction data
        dcc.Store(id=FINGPT_IDS['store'], data={'history': []}),
        
    ], className="p-2")


def _empty_prediction_display() -> html.Div:
    """Create empty prediction display."""
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className="bi bi-question-circle", 
                           style={'fontSize': '3rem', 'color': COLORS['muted']}),
                    html.H4("--", className="text-muted mt-2"),
                    html.Small("Prediction", className="text-muted"),
                ], className="text-center"),
            ], width=4),
            dbc.Col([
                html.Div([
                    html.Span("0%", style={'fontSize': '2.5rem', 'color': COLORS['muted']}),
                    html.Div("Confidence", className="text-muted small"),
                ], className="text-center"),
            ], width=4),
            dbc.Col([
                html.Div([
                    html.Span("--", style={'fontSize': '2rem', 'color': COLORS['muted']}),
                    html.Div("Ticker", className="text-muted small"),
                ], className="text-center"),
            ], width=4),
        ]),
    ], className="py-3")


def _create_prediction_display(ticker: str, prediction: str, confidence: float) -> html.Div:
    """Create populated prediction display."""
    # Determine colors and icons based on prediction
    if prediction == 'up':
        color = COLORS['up']
        icon = 'bi-arrow-up-circle-fill'
        text = "BULLISH"
    elif prediction == 'down':
        color = COLORS['down']
        icon = 'bi-arrow-down-circle-fill'
        text = "BEARISH"
    else:
        color = COLORS['neutral']
        icon = 'bi-dash-circle-fill'
        text = "NEUTRAL"
    
    confidence_pct = int(confidence * 100)
    
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.I(className=f"bi {icon}", 
                           style={'fontSize': '3rem', 'color': color}),
                    html.H4(text, className="mt-2", style={'color': color}),
                    html.Small("Prediction", className="text-muted"),
                ], className="text-center"),
            ], width=4),
            dbc.Col([
                html.Div([
                    html.Span(f"{confidence_pct}%", 
                              style={'fontSize': '2.5rem', 'color': color}),
                    html.Div("Confidence", className="text-muted small"),
                ], className="text-center"),
            ], width=4),
            dbc.Col([
                html.Div([
                    html.Span(ticker, style={'fontSize': '2rem', 'color': COLORS['info']}),
                    html.Div("Ticker", className="text-muted small"),
                ], className="text-center"),
            ], width=4),
        ]),
    ], className="py-3")


def _create_confidence_gauge(confidence: float, prediction: str) -> go.Figure:
    """Create a confidence gauge chart."""
    
    # Color based on prediction
    if prediction == 'up':
        bar_color = COLORS['up']
    elif prediction == 'down':
        bar_color = COLORS['down']
    else:
        bar_color = COLORS['neutral']
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=confidence * 100,
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'suffix': '%', 'font': {'size': 24, 'color': COLORS['text']}},
        gauge={
            'axis': {
                'range': [0, 100],
                'tickwidth': 1,
                'tickcolor': COLORS['border'],
                'tickfont': {'color': COLORS['muted'], 'size': 10},
            },
            'bar': {'color': bar_color, 'thickness': 0.3},
            'bgcolor': COLORS['card'],
            'borderwidth': 0,
            'steps': [
                {'range': [0, 33], 'color': 'rgba(255, 82, 82, 0.1)'},
                {'range': [33, 66], 'color': 'rgba(255, 193, 7, 0.1)'},
                {'range': [66, 100], 'color': 'rgba(0, 200, 5, 0.1)'},
            ],
            'threshold': {
                'line': {'color': COLORS['text'], 'width': 2},
                'thickness': 0.75,
                'value': confidence * 100,
            },
        },
        title={
            'text': "Confidence Level",
            'font': {'size': 12, 'color': COLORS['muted']},
        },
    ))
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=40, b=10),
        height=150,
    )
    
    return fig


def _create_history_table(history: List[Dict]) -> html.Div:
    """Create prediction history table."""
    if not history:
        return html.Span("No prediction history yet", className="text-muted small")
    
    rows = []
    for pred in history[-5:]:  # Last 5 predictions
        # Format prediction indicator
        if pred['prediction'] == 'up':
            pred_badge = dbc.Badge("↑ UP", color="success", className="me-2")
        elif pred['prediction'] == 'down':
            pred_badge = dbc.Badge("↓ DOWN", color="danger", className="me-2")
        else:
            pred_badge = dbc.Badge("— NEUTRAL", color="warning", className="me-2")
        
        rows.append(html.Tr([
            html.Td(pred.get('ticker', '--'), className="text-info"),
            html.Td(pred_badge),
            html.Td(f"{pred.get('confidence', 0)*100:.0f}%"),
            html.Td(pred.get('timestamp', '--')[:16], className="small text-muted"),
        ]))
    
    return html.Table([
        html.Thead(html.Tr([
            html.Th("Ticker"),
            html.Th("Prediction"),
            html.Th("Confidence"),
            html.Th("Time"),
        ])),
        html.Tbody(rows),
    ], className="table table-dark table-sm")


# ==============================================================================
# CALLBACKS
# ==============================================================================

def register_fingpt_callbacks(app):
    """Register FinGPT panel callbacks."""
    from dash.exceptions import PreventUpdate
    
    @app.callback(
        Output(FINGPT_IDS['prediction_display'], 'children'),
        Output(FINGPT_IDS['confidence_gauge'], 'figure'),
        Output(FINGPT_IDS['analysis_text'], 'children'),
        Output(FINGPT_IDS['rationale_text'], 'children'),
        Output(FINGPT_IDS['provenance_info'], 'children'),
        Output(FINGPT_IDS['status'], 'children'),
        Output(FINGPT_IDS['store'], 'data'),
        Output(FINGPT_IDS['history_table'], 'children'),
        Input(FINGPT_IDS['run_btn'], 'n_clicks'),
        State(FINGPT_IDS['ticker_input'], 'value'),
        State(FINGPT_IDS['weeks_slider'], 'value'),
        State(FINGPT_IDS['include_financials'], 'value'),
        State(FINGPT_IDS['model_select'], 'value'),
        State(FINGPT_IDS['store'], 'data'),
        prevent_initial_call=True,
    )
    def run_fingpt_prediction(n_clicks, ticker, n_weeks, include_financials, model_select, store_data):
        """Run FinGPT prediction."""
        if not n_clicks or not ticker:
            raise PreventUpdate
        
        ticker = ticker.strip().upper()
        include_fin = 'include' in (include_financials or [])
        
        try:
            # Import and run forecaster
            from financial_dashboard.services.forecaster import run_forecast
            
            result = run_forecast(
                ticker=ticker,
                n_weeks=n_weeks,
                include_financials=include_fin,
                model_provider=model_select if model_select != 'default' else None,
            )
            
            prediction = result.get('prediction', 'neutral')
            confidence = result.get('confidence', 0.5)
            analysis = result.get('analysis', 'No analysis available')
            rationale = result.get('rationale', 'No rationale provided')
            provenance = result.get('provenance', {})
            
            # Update store with history
            history = store_data.get('history', []) if store_data else []
            history.append({
                'ticker': ticker,
                'prediction': prediction,
                'confidence': confidence,
                'timestamp': datetime.now().isoformat(),
            })
            new_store = {'history': history[-10:]}  # Keep last 10
            
            # Format provenance
            prov_text = f"News items: {provenance.get('news_items', 0)} | " \
                       f"Financials: {'Yes' if provenance.get('included_financials') else 'No'} | " \
                       f"Model: {provenance.get('model', 'unknown')}"
            
            # Status
            status = dbc.Alert([
                html.I(className="bi bi-check-circle me-2"),
                f"Prediction generated for {ticker}"
            ], color="success", dismissable=True, duration=3000)
            
            return (
                _create_prediction_display(ticker, prediction, confidence),
                _create_confidence_gauge(confidence, prediction),
                html.Span(analysis, className="small"),
                html.Span(rationale, className="small"),
                prov_text,
                status,
                new_store,
                _create_history_table(history),
            )
            
        except Exception as e:
            logger.error(f"FinGPT prediction failed: {e}")
            status = dbc.Alert([
                html.I(className="bi bi-exclamation-triangle me-2"),
                f"Prediction failed: {str(e)}"
            ], color="danger", dismissable=True)
            
            return (
                _empty_prediction_display(),
                _create_confidence_gauge(0.5, "neutral"),
                html.Span(f"Error: {str(e)}", className="small text-danger"),
                html.Span("--", className="small text-muted"),
                "Error occurred",
                status,
                store_data or {'history': []},
                _create_history_table(store_data.get('history', []) if store_data else []),
            )
