"""
Market Forecast Tab - Upgraded with Multi-Model, Scenarios, and Fan Charts
============================================================================

Features:
- Multi-model forecasting (Prophet, ARIMA, LSTM, Ensemble)
- Confidence interval visualization (fan charts)
- Scenario analysis ("What-If" simulator)
- Model performance comparison
"""

import logging
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Component IDs
COMPONENT_IDS = {
    'ticker_input': 'mf-ticker-input',
    'horizon_select': 'mf-horizon-select',
    'model_checklist': 'mf-model-checklist',
    'interval_checklist': 'mf-interval-checklist',
    'scenario_select': 'mf-scenario-select',
    'scenario_param': 'mf-scenario-param',
    'scenario_apply_btn': 'mf-scenario-apply-btn',
    'run_btn': 'mf-run-btn',
    'forecast_chart': 'mf-forecast-chart',
    'scenario_chart': 'mf-scenario-chart',
    'model_metrics': 'mf-model-metrics',
    'status_banner': 'mf-status-banner',
    'forecast_store': 'mf-forecast-store',
}


def create_inputs_panel():
    """Enhanced inputs panel with model selection and scenarios."""
    return dbc.Card([
        dbc.CardHeader(html.H5("📊 Forecast Configuration", className="mb-0")),
        dbc.CardBody([
            # Ticker and Horizon
            dbc.Row([
                dbc.Col([
                    html.Label("Ticker", className="small fw-bold text-white"),
                    dcc.Input(
                        id=COMPONENT_IDS['ticker_input'],
                        type='text',
                        value='AAPL',
                        placeholder='Enter ticker',
                        className="form-control form-control-sm"
                    )
                ], width=6),
                dbc.Col([
                    html.Label("Horizon (days)", className="small fw-bold text-white"),
                    dcc.Dropdown(
                        id=COMPONENT_IDS['horizon_select'],
                        options=[
                            {'label': '1 Week (7 days)', 'value': 7},
                            {'label': '2 Weeks (14 days)', 'value': 14},
                            {'label': '1 Month (30 days)', 'value': 30},
                        ],
                        value=14,
                        clearable=False,
                        className="form-select-sm"
                    )
                ], width=6),
            ], className="mb-3"),
            
            # Model Selection
            html.Label("Models", className="small fw-bold text-white"),
            dcc.Checklist(
                id=COMPONENT_IDS['model_checklist'],
                options=[
                    {'label': ' Prophet (Trend + Seasonality)', 'value': 'prophet'},
                    {'label': ' ARIMA (Autoregression)', 'value': 'arima'},
                    {'label': ' LSTM (Deep Learning)', 'value': 'lstm'},
                    {'label': ' Ensemble (Weighted Average)', 'value': 'ensemble'},
                ],
                value=['prophet', 'ensemble'],
                className="text-white-50 small mb-3",
                labelStyle={'display': 'block', 'marginBottom': '5px'}
            ),
            
            # Confidence Intervals
            html.Label("Confidence Intervals", className="small fw-bold text-white"),
            dcc.Checklist(
                id=COMPONENT_IDS['interval_checklist'],
                options=[
                    {'label': ' 50% (dark)', 'value': '50'},
                    {'label': ' 80% (medium)', 'value': '80'},
                    {'label': ' 95% (light)', 'value': '95'},
                ],
                value=['80', '95'],
                className="text-white-50 small mb-3",
                labelStyle={'display': 'block', 'marginBottom': '5px'}
            ),
            
            # Run Button
            dbc.Button(
                "▶ Generate Forecast",
                id=COMPONENT_IDS['run_btn'],
                color="success",
                size="lg",
                className="w-100"
            ),
        ])
    ], className="h-100")


def create_scenario_panel():
    """Scenario analysis ("What-If") panel."""
    from ..utils.scenario_simulator import ScenarioSimulator
    
    return dbc.Card([
        dbc.CardHeader(html.H5("🎯 Scenario Analysis", className="mb-0")),
        dbc.CardBody([
            html.P("Test market reactions to economic events", className="small text-white-50 mb-3"),
            
            # Scenario selector
            html.Label("Scenario", className="small fw-bold text-white"),
            dcc.Dropdown(
                id=COMPONENT_IDS['scenario_select'],
                options=ScenarioSimulator.get_scenario_options(),
                placeholder="Select a scenario...",
                className="form-select-sm mb-3"
            ),
            
            # Parameter input
            html.Div(id='scenario-param-container', children=[
                html.Label("Parameter", className="small fw-bold text-white"),
                dcc.Slider(
                    id=COMPONENT_IDS['scenario_param'],
                    min=-50,
                    max=50,
                    step=5,
                    value=0,
                    marks={i: str(i) for i in range(-50, 51, 25)},
                    className="mb-3"
                )
            ]),
            
            # Apply button
            dbc.Button(
                "Apply Scenario",
                id=COMPONENT_IDS['scenario_apply_btn'],
                color="warning",
                size="sm",
                className="w-100",
                disabled=True
            ),
        ])
    ], className="h-100")


def create_results_panel():
    """Results panel with fan chart."""
    return dbc.Card([
        dbc.CardHeader(html.H5("📈 Forecast Results", className="mb-0")),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(
                    id=COMPONENT_IDS['forecast_chart'],
                    figure=_empty_chart("Click 'Generate Forecast' to see predictions"),
                    style={'height': '500px'}
                )
            ),
        ])
    ], className="h-100")


def create_scenario_results_panel():
    """Scenario comparison results."""
    return dbc.Card([
        dbc.CardHeader(html.H5("📊 Scenario Impact", className="mb-0")),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(
                    id=COMPONENT_IDS['scenario_chart'],
                    figure=_empty_chart("Apply a scenario to see impact"),
                    style={'height': '400px'}
                )
            ),
        ])
    ])


def create_metrics_panel():
    """Model performance metrics."""
    return dbc.Card([
        dbc.CardHeader(html.H5("📊 Model Performance", className="mb-0")),
        dbc.CardBody([
            html.Div(id=COMPONENT_IDS['model_metrics'], children=[
                html.P("Run forecast to see metrics", className="text-white-50 small text-center py-3")
            ])
        ])
    ])


def _empty_chart(message: str) -> go.Figure:
    """Create empty placeholder chart."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=14, color="#6c757d")
    )
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=50, r=50, t=50, b=50),
    )
    return fig


def layout():
    """Main layout with 4-panel design."""
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="bi bi-graph-up me-2"),
                    "Market Forecast"
                ], className="mb-1 text-white"),
                html.P(
                    "Multi-model forecasting with confidence intervals and scenario analysis",
                    className="text-white-50 small mb-3"
                )
            ])
        ]),
        
        # Status banner
        dbc.Row([
            dbc.Col([
                html.Div(id=COMPONENT_IDS['status_banner'])
            ])
        ], className="mb-3"),
        
        # Main content: 3 columns
        dbc.Row([
            # Left: Inputs
            dbc.Col([
                create_inputs_panel(),
                html.Div(className="mb-3"),
                create_scenario_panel(),
            ], width=3),
            
            # Middle: Forecast Results
            dbc.Col([
                create_results_panel(),
            ], width=6),
            
            # Right: Metrics
            dbc.Col([
                create_metrics_panel(),
                html.Div(className="mb-3"),
                create_scenario_results_panel(),
            ], width=3),
        ], className="mb-4"),
        
        # Hidden stores
        dcc.Store(id=COMPONENT_IDS['forecast_store'], data=None),
        
    ], fluid=True, className="p-4")


def register_callbacks(app):
    """Register all callbacks."""
    logger.info("Registering Market Forecast callbacks")
    
    from dash.exceptions import PreventUpdate
    from ..models import ProphetForecaster, ARIMAForecaster, LSTMForecaster, EnsembleForecaster
    from ..utils.fan_charts import create_fan_chart, create_scenario_comparison_chart
    from ..utils.scenario_simulator import ScenarioSimulator
    
    @app.callback(
        Output(COMPONENT_IDS['forecast_store'], 'data'),
        Output(COMPONENT_IDS['forecast_chart'], 'figure'),
        Output(COMPONENT_IDS['model_metrics'], 'children'),
        Output(COMPONENT_IDS['status_banner'], 'children'),
        Output(COMPONENT_IDS['scenario_apply_btn'], 'disabled'),
        Input(COMPONENT_IDS['run_btn'], 'n_clicks'),
        State(COMPONENT_IDS['ticker_input'], 'value'),
        State(COMPONENT_IDS['horizon_select'], 'value'),
        State(COMPONENT_IDS['model_checklist'], 'value'),
        State(COMPONENT_IDS['interval_checklist'], 'value'),
        prevent_initial_call=True
    )
    def run_forecast(n_clicks, ticker, horizon, selected_models, selected_intervals):
        """Main forecast generation callback."""
        if not n_clicks or not ticker:
            raise PreventUpdate
        
        ticker = ticker.strip().upper()
        
        try:
            # Fetch historical data
            import yfinance as yf
            stock = yf.Ticker(ticker)
            
            # Get 1 year of daily data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=365)
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty:
                status = dbc.Alert(f"No data available for {ticker}", color="danger")
                return None, _empty_chart(f"No data for {ticker}"), [], status, True
            
            # Prepare data for models
            data = pd.DataFrame({
                'ds': hist.index,
                'y': hist['Close'].values
            })
            
            # Train selected models and generate forecasts
            forecasts = {}
            
            if 'prophet' in selected_models:
                try:
                    prophet = ProphetForecaster()
                    prophet.fit(data)
                    forecasts['prophet'] = prophet.predict(horizon)
                except Exception as e:
                    logger.error(f"Prophet error: {e}")
            
            if 'arima' in selected_models:
                try:
                    arima = ARIMAForecaster()
                    arima.fit(data)
                    forecasts['arima'] = arima.predict(horizon)
                except Exception as e:
                    logger.error(f"ARIMA error: {e}")
            
            if 'lstm' in selected_models:
                try:
                    lstm = LSTMForecaster()
                    lstm.fit(data)
                    forecasts['lstm'] = lstm.predict(horizon)
                except Exception as e:
                    logger.error(f"LSTM error: {e}")
            
            if 'ensemble' in selected_models:
                try:
                    ensemble = EnsembleForecaster()
                    ensemble.fit(data)
                    forecasts['ensemble'] = ensemble.predict(horizon)
                except Exception as e:
                    logger.error(f"Ensemble error: {e}")
            
            if not forecasts:
                status = dbc.Alert("All models failed to generate forecasts", color="danger")
                return None, _empty_chart("Model training failed"), [], status, True
            
            # Use first successful forecast for chart (or ensemble if available)
            primary_forecast = forecasts.get('ensemble', list(forecasts.values())[0])
            
            # Create forecast dates
            last_date = data['ds'].iloc[-1]
            forecast_dates = pd.date_range(start=last_date + timedelta(days=1), periods=horizon)
            
            # Create fan chart
            historical_dates = data['ds'].tolist()[-60:]  # Last 60 days
            historical_values = data['y'].tolist()[-60:]
            
            fig = create_fan_chart(
                historical_dates=historical_dates,
                historical_values=historical_values,
                forecast_dates=forecast_dates.tolist(),
                forecast_data=primary_forecast,
                ticker=ticker,
                show_intervals=selected_intervals
            )
            
            # Create metrics table
            metrics_children = []
            for model_name, forecast in forecasts.items():
                last_price = data['y'].iloc[-1]
                predicted_price = forecast['forecast'][-1]
                change_pct = ((predicted_price - last_price) / last_price) * 100
                
                metrics_children.append(
                    dbc.Row([
                        dbc.Col(html.Strong(model_name.upper(), className="text-white"), width=6),
                        dbc.Col(html.Span(f"${predicted_price:.2f}", className="text-white-50"), width=6),
                    ], className="mb-2")
                )
                metrics_children.append(
                    html.Small(f"Change: {change_pct:+.2f}%", 
                              className="text-success" if change_pct >= 0 else "text-danger",
                              style={'display': 'block', 'marginBottom': '10px'})
                )
            
            # Store forecast data
            store_data = {
                'ticker': ticker,
                'horizon': horizon,
                'forecasts': {k: v['forecast'] for k, v in forecasts.items()},
                'primary_forecast': primary_forecast,
                'forecast_dates': [str(d) for d in forecast_dates],
                'last_price': float(data['y'].iloc[-1]),
            }
            
            status = dbc.Alert(f"✓ Forecast generated for {ticker} ({len(forecasts)} models)", 
                             color="success", duration=5000)
            
            return store_data, fig, metrics_children, status, False
            
        except Exception as e:
            logger.exception(f"Forecast error: {e}")
            status = dbc.Alert(f"Error: {str(e)}", color="danger")
            return None, _empty_chart(f"Error: {str(e)}"), [], status, True
    
    @app.callback(
        Output(COMPONENT_IDS['scenario_chart'], 'figure'),
        Output(COMPONENT_IDS['status_banner'], 'children', allow_duplicate=True),
        Input(COMPONENT_IDS['scenario_apply_btn'], 'n_clicks'),
        State(COMPONENT_IDS['forecast_store'], 'data'),
        State(COMPONENT_IDS['scenario_select'], 'value'),
        State(COMPONENT_IDS['scenario_param'], 'value'),
        prevent_initial_call=True
    )
    def apply_scenario(n_clicks, store_data, scenario_type, param_value):
        """Apply scenario to baseline forecast."""
        if not n_clicks or not store_data or not scenario_type:
            raise PreventUpdate
        
        try:
            baseline_forecast = store_data['primary_forecast']['forecast']
            forecast_dates = pd.to_datetime(store_data['forecast_dates'])
            ticker = store_data['ticker']
            
            # Apply scenario
            result = ScenarioSimulator.apply_scenario(
                baseline_forecast=baseline_forecast,
                scenario_type=scenario_type,
                param_value=param_value,
                decay_rate=0.9
            )
            
            # Create comparison chart
            fig = create_scenario_comparison_chart(
                forecast_dates=forecast_dates.tolist(),
                baseline_forecast=baseline_forecast,
                scenario_forecast=result['adjusted_forecast'],
                scenario_name=result['scenario_info']['name'],
                ticker=ticker
            )
            
            status = dbc.Alert(
                f"✓ Scenario applied: {result['scenario_info']['name']} "
                f"(Initial impact: {result['scenario_info']['initial_impact_pct']:.2f}%)",
                color="info", duration=5000
            )
            
            return fig, status
            
        except Exception as e:
            logger.exception(f"Scenario error: {e}")
            status = dbc.Alert(f"Scenario error: {str(e)}", color="danger")
            return _empty_chart(f"Error: {str(e)}"), status


__all__ = ['layout', 'register_callbacks', 'COMPONENT_IDS']
