"""
Phase 2 AI/ML Dashboard Layout

Integrated dashboard tab for Phase 2 AI/ML features:
- Neural Price Forecasting (N-BEATS/NHITS)
- Market Regime Detection (HMM)
- Sentiment Consensus (FinBERT)

Author: Agent-P2
Date: 2025-12-28
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Any, Optional

import dash
from dash import dcc, html, Input, Output, State, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)

# Import Phase 2 engines
try:
    from financial_dashboard.engines.neural_forecaster import (
        get_neural_forecaster, quick_forecast
    )
    NEURAL_FORECAST_AVAILABLE = True
except ImportError:
    NEURAL_FORECAST_AVAILABLE = False
    logger.warning("Neural forecaster not available")

try:
    from financial_dashboard.engines.hmm_regime_detector import (
        get_regime_detector, quick_regime_detection
    )
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    logger.warning("HMM regime detector not available")

try:
    from financial_dashboard.engines.sentiment_consensus import (
        get_sentiment_analyzer, quick_sentiment
    )
    SENTIMENT_AVAILABLE = True
except ImportError:
    SENTIMENT_AVAILABLE = False
    logger.warning("Sentiment analyzer not available")


# Component IDs
ID_PREFIX = "phase2-aiml"
ID_TICKER_INPUT = f"{ID_PREFIX}-ticker-input"
ID_ANALYZE_BTN = f"{ID_PREFIX}-analyze-btn"
ID_MODEL_DROPDOWN = f"{ID_PREFIX}-model-dropdown"
ID_HORIZON_SLIDER = f"{ID_PREFIX}-horizon-slider"
ID_FORECAST_GRAPH = f"{ID_PREFIX}-forecast-graph"
ID_REGIME_GRAPH = f"{ID_PREFIX}-regime-graph"
ID_SENTIMENT_GAUGE = f"{ID_PREFIX}-sentiment-gauge"
ID_SENTIMENT_DIST = f"{ID_PREFIX}-sentiment-dist"
ID_TRANSITION_MATRIX = f"{ID_PREFIX}-transition-matrix"
ID_METRICS_TABLE = f"{ID_PREFIX}-metrics-table"
ID_HEADLINES_TABLE = f"{ID_PREFIX}-headlines-table"
ID_STATUS_DIV = f"{ID_PREFIX}-status"
ID_TABS = f"{ID_PREFIX}-tabs"


def create_layout() -> dbc.Container:
    """Create Phase 2 AI/ML dashboard layout."""
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H2("🧠 AI/ML Analytics Lab", className="text-primary mb-2"),
                html.P(
                    "Deep learning price forecasting, market regime detection, and sentiment analysis",
                    className="text-muted"
                ),
            ])
        ], className="mb-4"),
        
        # Control Panel
        dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    # Ticker input
                    dbc.Col([
                        dbc.Label("Stock Symbol"),
                        dbc.Input(
                            id=ID_TICKER_INPUT,
                            type="text",
                            value="SPY",
                            placeholder="Enter ticker (e.g., SPY, AAPL)",
                            className="mb-2"
                        ),
                    ], width=3),
                    
                    # Model selection
                    dbc.Col([
                        dbc.Label("Forecast Model"),
                        dcc.Dropdown(
                            id=ID_MODEL_DROPDOWN,
                            options=[
                                {'label': 'N-BEATS (Trend + Seasonality)', 'value': 'nbeats'},
                                {'label': 'NHITS (Hierarchical)', 'value': 'nhits'},
                            ],
                            value='nbeats',
                            clearable=False
                        ),
                    ], width=3),
                    
                    # Horizon slider
                    dbc.Col([
                        dbc.Label(f"Forecast Horizon (days)"),
                        dcc.Slider(
                            id=ID_HORIZON_SLIDER,
                            min=7,
                            max=60,
                            step=7,
                            value=30,
                            marks={7: '7d', 14: '14d', 30: '30d', 60: '60d'},
                        ),
                    ], width=4),
                    
                    # Analyze button
                    dbc.Col([
                        dbc.Label(" "),
                        dbc.Button(
                            "🔍 Analyze",
                            id=ID_ANALYZE_BTN,
                            color="primary",
                            className="w-100 mt-1"
                        ),
                    ], width=2),
                ]),
            ])
        ], className="mb-4"),
        
        # Status message
        html.Div(id=ID_STATUS_DIV, className="mb-3"),
        
        # Main content tabs
        dbc.Tabs([
            # Tab 1: Neural Forecast
            dbc.Tab([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("📈 Neural Price Forecast"),
                            dbc.CardBody([
                                dcc.Graph(
                                    id=ID_FORECAST_GRAPH,
                                    config={'displayModeBar': True},
                                    style={'height': '450px'}
                                ),
                            ])
                        ])
                    ], width=8),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("📊 Forecast Metrics"),
                            dbc.CardBody([
                                html.Div(id=ID_METRICS_TABLE)
                            ])
                        ])
                    ], width=4),
                ], className="mt-3"),
            ], label="🔮 Neural Forecast", tab_id="tab-forecast"),
            
            # Tab 2: Regime Detection
            dbc.Tab([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("📊 Market Regime Detection"),
                            dbc.CardBody([
                                dcc.Graph(
                                    id=ID_REGIME_GRAPH,
                                    config={'displayModeBar': True},
                                    style={'height': '450px'}
                                ),
                            ])
                        ])
                    ], width=8),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("🔄 Transition Matrix"),
                            dbc.CardBody([
                                dcc.Graph(
                                    id=ID_TRANSITION_MATRIX,
                                    config={'displayModeBar': False},
                                    style={'height': '350px'}
                                ),
                            ])
                        ])
                    ], width=4),
                ], className="mt-3"),
            ], label="📈 Regime Analysis", tab_id="tab-regime"),
            
            # Tab 3: Sentiment Analysis
            dbc.Tab([
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("🎯 Fear & Greed Index"),
                            dbc.CardBody([
                                dcc.Graph(
                                    id=ID_SENTIMENT_GAUGE,
                                    config={'displayModeBar': False},
                                    style={'height': '300px'}
                                ),
                            ])
                        ]),
                        dbc.Card([
                            dbc.CardHeader("📊 Sentiment Distribution"),
                            dbc.CardBody([
                                dcc.Graph(
                                    id=ID_SENTIMENT_DIST,
                                    config={'displayModeBar': False},
                                    style={'height': '200px'}
                                ),
                            ])
                        ], className="mt-3"),
                    ], width=5),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("📰 Recent Headlines"),
                            dbc.CardBody([
                                html.Div(
                                    id=ID_HEADLINES_TABLE,
                                    style={'maxHeight': '500px', 'overflowY': 'auto'}
                                )
                            ])
                        ])
                    ], width=7),
                ], className="mt-3"),
            ], label="💭 Sentiment", tab_id="tab-sentiment"),
        ], id=ID_TABS, active_tab="tab-forecast"),
        
    ], fluid=True, className="p-4")


def register_callbacks(app: dash.Dash):
    """Register callbacks for Phase 2 dashboard."""
    
    @app.callback(
        [
            Output(ID_FORECAST_GRAPH, 'figure'),
            Output(ID_REGIME_GRAPH, 'figure'),
            Output(ID_SENTIMENT_GAUGE, 'figure'),
            Output(ID_SENTIMENT_DIST, 'figure'),
            Output(ID_TRANSITION_MATRIX, 'figure'),
            Output(ID_METRICS_TABLE, 'children'),
            Output(ID_HEADLINES_TABLE, 'children'),
            Output(ID_STATUS_DIV, 'children'),
        ],
        [Input(ID_ANALYZE_BTN, 'n_clicks')],
        [
            State(ID_TICKER_INPUT, 'value'),
            State(ID_MODEL_DROPDOWN, 'value'),
            State(ID_HORIZON_SLIDER, 'value'),
        ],
        prevent_initial_call=False
    )
    def update_analysis(n_clicks, ticker, model, horizon):
        """Update all analysis components."""
        ticker = ticker.upper().strip() if ticker else 'SPY'
        
        try:
            # Generate forecast
            forecast_fig = create_forecast_chart(ticker, model, horizon)
            
            # Generate regime chart
            regime_fig, trans_fig = create_regime_charts(ticker)
            
            # Generate sentiment charts
            gauge_fig, dist_fig, headlines = create_sentiment_charts(ticker)
            
            # Create metrics table
            metrics_table = create_metrics_table(ticker, model, horizon)
            
            # Success status
            status = dbc.Alert(
                f"✅ Analysis complete for {ticker}",
                color="success",
                dismissable=True
            )
            
            return (
                forecast_fig,
                regime_fig,
                gauge_fig,
                dist_fig,
                trans_fig,
                metrics_table,
                headlines,
                status
            )
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            
            # Error status
            status = dbc.Alert(
                f"❌ Analysis failed: {str(e)}",
                color="danger",
                dismissable=True
            )
            
            # Return empty figures
            empty_fig = go.Figure()
            empty_fig.add_annotation(
                text="Error loading data",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False
            )
            
            return (
                empty_fig, empty_fig, empty_fig, empty_fig, empty_fig,
                html.P("Error loading metrics"),
                html.P("Error loading headlines"),
                status
            )


def create_forecast_chart(ticker: str, model: str, horizon: int) -> go.Figure:
    """Create neural forecast fan chart."""
    try:
        data = quick_forecast(ticker, horizon=horizon, model=model)
        
        fig = go.Figure()
        
        # Historical prices
        fig.add_trace(go.Scatter(
            x=data['historical_dates'],
            y=data['historical_prices'],
            mode='lines',
            name='Historical',
            line=dict(color='#2196F3', width=2)
        ))
        
        # 95% confidence interval
        if data['forecast_hi_95'] and data['forecast_lo_95']:
            fig.add_trace(go.Scatter(
                x=data['forecast_dates'] + data['forecast_dates'][::-1],
                y=data['forecast_hi_95'] + data['forecast_lo_95'][::-1],
                fill='toself',
                fillcolor='rgba(255, 165, 0, 0.2)',
                line=dict(color='rgba(255,255,255,0)'),
                name='95% CI'
            ))
        
        # 80% confidence interval
        if data['forecast_hi_80'] and data['forecast_lo_80']:
            fig.add_trace(go.Scatter(
                x=data['forecast_dates'] + data['forecast_dates'][::-1],
                y=data['forecast_hi_80'] + data['forecast_lo_80'][::-1],
                fill='toself',
                fillcolor='rgba(255, 165, 0, 0.4)',
                line=dict(color='rgba(255,255,255,0)'),
                name='80% CI'
            ))
        
        # Forecast mean
        fig.add_trace(go.Scatter(
            x=data['forecast_dates'],
            y=data['forecast_prices'],
            mode='lines',
            name='Forecast',
            line=dict(color='#FF9800', width=2, dash='dash')
        ))
        
        fig.update_layout(
            title=f"{ticker} - {model.upper()} {horizon}-Day Forecast",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
            template="plotly_white",
            hovermode="x unified"
        )
        
        return fig
        
    except Exception as e:
        logger.error(f"Forecast chart error: {e}")
        fig = go.Figure()
        fig.add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5)
        return fig


def create_regime_charts(ticker: str) -> Tuple[go.Figure, go.Figure]:
    """Create regime detection charts."""
    try:
        data = quick_regime_detection(ticker)
        
        # Main price chart with regime backgrounds
        fig = go.Figure()
        
        # Price line
        fig.add_trace(go.Scatter(
            x=data['dates'],
            y=data['prices'],
            mode='lines',
            name='Price',
            line=dict(color='black', width=1.5)
        ))
        
        # Add colored regions for regimes
        regime_colors = {
            'Bull': 'rgba(0, 200, 0, 0.15)',
            'Bear': 'rgba(200, 0, 0, 0.15)',
            'Sideways': 'rgba(128, 128, 128, 0.15)'
        }
        
        # Group consecutive regimes
        current_regime = None
        start_idx = 0
        
        for i, regime in enumerate(data['regimes']):
            if regime != current_regime:
                if current_regime is not None:
                    fig.add_vrect(
                        x0=data['dates'][start_idx],
                        x1=data['dates'][i-1],
                        fillcolor=regime_colors.get(current_regime, 'rgba(128,128,128,0.1)'),
                        layer="below",
                        line_width=0,
                    )
                current_regime = regime
                start_idx = i
        
        # Add final region
        if current_regime is not None:
            fig.add_vrect(
                x0=data['dates'][start_idx],
                x1=data['dates'][-1],
                fillcolor=regime_colors.get(current_regime, 'rgba(128,128,128,0.1)'),
                layer="below",
                line_width=0,
            )
        
        # Add current regime annotation
        fig.add_annotation(
            x=0.02, y=0.98,
            xref="paper", yref="paper",
            text=f"Current: {data['current_regime']}",
            showarrow=False,
            font=dict(size=14, color='white'),
            bgcolor=regime_colors.get(data['current_regime'], 'gray').replace('0.15', '0.8'),
            borderpad=4
        )
        
        fig.update_layout(
            title=f"{ticker} Market Regime Analysis",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            template="plotly_white",
            showlegend=False
        )
        
        # Transition matrix heatmap
        trans_fig = go.Figure(data=go.Heatmap(
            z=data['transition_matrix'],
            x=['Bull', 'Bear', 'Sideways'],
            y=['Bull', 'Bear', 'Sideways'],
            colorscale='Blues',
            text=[[f"{v:.2f}" for v in row] for row in data['transition_matrix']],
            texttemplate="%{text}",
            textfont={"size": 12},
            hovertemplate="From %{y} to %{x}: %{z:.2%}<extra></extra>"
        ))
        
        trans_fig.update_layout(
            title="Regime Transition Probabilities",
            xaxis_title="To",
            yaxis_title="From",
            template="plotly_white"
        )
        
        return fig, trans_fig
        
    except Exception as e:
        logger.error(f"Regime chart error: {e}")
        empty_fig = go.Figure()
        empty_fig.add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5)
        return empty_fig, empty_fig


def create_sentiment_charts(ticker: str) -> Tuple[go.Figure, go.Figure, html.Div]:
    """Create sentiment analysis charts."""
    try:
        data = quick_sentiment(ticker)
        
        # Fear & Greed Gauge
        gauge_fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=data['fear_greed_index'],
            domain={'x': [0, 1], 'y': [0, 1]},
            title={'text': f"{ticker} Fear & Greed Index", 'font': {'size': 16}},
            gauge={
                'axis': {'range': [0, 100], 'tickwidth': 1},
                'bar': {'color': data['gauge_data']['color']},
                'bgcolor': "white",
                'borderwidth': 2,
                'bordercolor': "gray",
                'steps': [
                    {'range': [0, 20], 'color': '#FF0000'},
                    {'range': [20, 40], 'color': '#FF6600'},
                    {'range': [40, 60], 'color': '#FFFF00'},
                    {'range': [60, 80], 'color': '#99FF00'},
                    {'range': [80, 100], 'color': '#00FF00'},
                ],
                'threshold': {
                    'line': {'color': "black", 'width': 4},
                    'thickness': 0.75,
                    'value': data['fear_greed_index']
                }
            }
        ))
        
        gauge_fig.add_annotation(
            x=0.5, y=-0.1,
            text=data['gauge_data']['label'],
            font=dict(size=18, color=data['gauge_data']['color']),
            showarrow=False,
            xref="paper", yref="paper"
        )
        
        gauge_fig.update_layout(
            template="plotly_white",
            margin=dict(l=20, r=20, t=60, b=60)
        )
        
        # Sentiment distribution pie chart
        dist_fig = go.Figure(data=[go.Pie(
            labels=['Positive', 'Negative', 'Neutral'],
            values=[
                data['sentiment_distribution']['positive'],
                data['sentiment_distribution']['negative'],
                data['sentiment_distribution']['neutral']
            ],
            marker=dict(colors=['#00CC00', '#CC0000', '#888888']),
            textinfo='label+percent',
            hole=0.4
        )])
        
        dist_fig.update_layout(
            title="Sentiment Distribution",
            template="plotly_white",
            showlegend=False,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        # Headlines table
        headlines_html = []
        for h in data['headline_scores'][:15]:
            color = {
                'positive': '#00CC00',
                'negative': '#CC0000',
                'neutral': '#888888'
            }.get(h['sentiment'], '#888888')
            
            headlines_html.append(
                html.Div([
                    html.Span(
                        f"[{h['sentiment'].upper()}]",
                        style={'color': color, 'fontWeight': 'bold', 'marginRight': '8px'}
                    ),
                    html.Span(h['headline']),
                    html.Span(
                        f" ({h['confidence']:.0%})",
                        style={'color': '#888', 'fontSize': '0.9em'}
                    )
                ], className="mb-2 pb-2 border-bottom")
            )
        
        headlines_div = html.Div(headlines_html)
        
        return gauge_fig, dist_fig, headlines_div
        
    except Exception as e:
        logger.error(f"Sentiment chart error: {e}")
        empty_fig = go.Figure()
        empty_fig.add_annotation(text=f"Error: {str(e)}", xref="paper", yref="paper", x=0.5, y=0.5)
        return empty_fig, empty_fig, html.P(f"Error: {str(e)}")


def create_metrics_table(ticker: str, model: str, horizon: int) -> html.Div:
    """Create forecast metrics table."""
    try:
        data = quick_forecast(ticker, horizon=horizon, model=model)
        metrics = data.get('metrics', {})
        
        rows = [
            html.Tr([html.Td("Last Price"), html.Td(f"${metrics.get('last_price', 0):.2f}")]),
            html.Tr([html.Td("Ann. Return"), html.Td(f"{metrics.get('mean_return', 0):.1%}")]),
            html.Tr([html.Td("Volatility"), html.Td(f"{metrics.get('volatility', 0):.1%}")]),
            html.Tr([html.Td("Sharpe Ratio"), html.Td(f"{metrics.get('sharpe_ratio', 0):.2f}")]),
            html.Tr([html.Td("Max Drawdown"), html.Td(f"{metrics.get('max_drawdown', 0):.1%}")]),
            html.Tr([html.Td("Model"), html.Td(model.upper())]),
            html.Tr([html.Td("Horizon"), html.Td(f"{horizon} days")]),
        ]
        
        return dbc.Table(
            [html.Tbody(rows)],
            bordered=True,
            hover=True,
            size="sm",
            className="mb-0"
        )
        
    except Exception as e:
        return html.P(f"Error: {str(e)}")


# For standalone testing
if __name__ == '__main__':
    import dash_bootstrap_components as dbc
    
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
    app.layout = create_layout()
    register_callbacks(app)
    
    app.run_server(debug=True, port=8052)
