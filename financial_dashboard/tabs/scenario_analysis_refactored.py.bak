"""
Scenario Analysis Tab - Refactored (Application Shell)
======================================================
Lightweight UI that calls Research Lab Service backend via API Gateway.
This module contains only presentation logic.

Business logic lives in: services/research_lab_service.py
API calls route through: api_gateway.py (port 8049)
"""

import logging
from datetime import datetime
import requests
from dash import dcc, html, Input, Output, State, callback_context, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

logger = logging.getLogger(__name__)

# API Gateway URL
API_GATEWAY_URL = "http://localhost:8049"


def layout():
    """Build lightweight scenario analysis layout."""
    return dbc.Container([
        html.H2("Research Lab & Scenario Analysis", className="mt-3 mb-3"),
        html.P("Test new strategies and run what-if scenarios", className="text-muted"),
        
        # Job type selector
        dbc.Row([
            dbc.Col([
                dbc.Label("Analysis Type:"),
                dcc.Dropdown(
                    id='research-job-type',
                    options=[
                        {'label': '📊 Scenario Analysis', 'value': 'scenario'},
                        {'label': '🔬 New Experiment', 'value': 'experiment'},
                        {'label': '📈 Backtest Strategy', 'value': 'backtest'},
                        {'label': '🧪 Ablation Study', 'value': 'ablation'}
                    ],
                    value='scenario',
                    clearable=False
                )
            ], width=4)
        ], className="mb-4"),
        
        # Conditional inputs based on job type
        html.Div(id='research-input-area'),
        
        # Control buttons
        dbc.Row([
            dbc.Col([
                dbc.Button(
                    "🚀 Run Analysis",
                    id='research-run-btn',
                    color='primary',
                    size='lg'
                )
            ], width=2)
        ], className="mb-4"),
        
        # Status and progress
        dbc.Alert(
            id='research-status-alert',
            is_open=False,
            duration=4000,
            className="mb-3"
        ),
        dbc.Progress(
            id='research-progress-bar',
            value=0,
            striped=True,
            animated=True,
            className="mb-3",
            style={'display': 'none'}
        ),
        
        # Results area
        html.Div(id='research-results-area'),
        
        # Hidden stores for job tracking
        dcc.Store(id='research-current-job-id'),
        dcc.Interval(
            id='research-poll-interval',
            interval=1500,  # Poll every 1.5 seconds
            disabled=True
        ),
    ], fluid=True)


def register_callbacks(app):
    """Register callbacks for research lab tab."""
    
    @app.callback(
        Output('research-input-area', 'children'),
        [Input('research-job-type', 'value')]
    )
    def update_input_form(job_type):
        """Update input form based on selected job type."""
        if job_type == 'scenario':
            return dbc.Card([
                dbc.CardBody([
                    html.H5("Scenario Parameters", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Scenario Name:"),
                            dcc.Input(
                                id='research-scenario-name',
                                type='text',
                                placeholder='e.g., Bull Market Recovery',
                                className='form-control mb-3',
                                value='Test Scenario'
                            )
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Universe:"),
                            dcc.Dropdown(
                                id='research-universe',
                                options=[
                                    {'label': 'Top 200 ADV', 'value': 'top200'},
                                    {'label': 'Top 1800 ADV', 'value': 'top1800'},
                                    {'label': 'S&P 500', 'value': 'sp500'}
                                ],
                                value='top200'
                            )
                        ], width=3),
                        dbc.Col([
                            dbc.Label("Horizon:"),
                            dcc.Dropdown(
                                id='research-horizon',
                                options=[
                                    {'label': '1 Week', 'value': '1w'},
                                    {'label': '1 Month', 'value': '1m'},
                                    {'label': '3 Months', 'value': '3m'}
                                ],
                                value='1m'
                            )
                        ], width=3)
                    ])
                ])
            ], className="mb-3")
        
        elif job_type == 'experiment':
            return dbc.Card([
                dbc.CardBody([
                    html.H5("Experiment Configuration", className="mb-3"),
                    dbc.Row([
                        dbc.Col([
                            dbc.Label("Experiment Name:"),
                            dcc.Input(
                                id='research-experiment-name',
                                type='text',
                                placeholder='e.g., momentum_ablation_test',
                                className='form-control mb-3',
                                value='Test Experiment'
                            )
                        ], width=6),
                        dbc.Col([
                            dbc.Label("Model Type:"),
                            dcc.Dropdown(
                                id='research-model-type',
                                options=[
                                    {'label': 'LightGBM', 'value': 'lgb'},
                                    {'label': 'XGBoost', 'value': 'xgb'},
                                    {'label': 'Neural Network', 'value': 'nn'},
                                    {'label': 'Ensemble', 'value': 'ensemble'}
                                ],
                                value='lgb'
                            )
                        ], width=6)
                    ])
                ])
            ], className="mb-3")
        
        else:
            return dbc.Card([
                dbc.CardBody([
                    html.H5(f"{job_type.title()} Parameters", className="mb-3"),
                    html.P("Configuration form coming soon...", className="text-muted")
                ])
            ], className="mb-3")
    
    @app.callback(
        [
            Output('research-current-job-id', 'data'),
            Output('research-poll-interval', 'disabled'),
            Output('research-status-alert', 'children'),
            Output('research-status-alert', 'color'),
            Output('research-status-alert', 'is_open'),
        ],
        [Input('research-run-btn', 'n_clicks')],
        [
            State('research-job-type', 'value'),
            State('research-scenario-name', 'value'),
            State('research-universe', 'value'),
            State('research-horizon', 'value'),
            State('research-experiment-name', 'value'),
            State('research-model-type', 'value'),
        ],
        prevent_initial_call=True
    )
    def start_research_job(n_clicks, job_type, scenario_name, universe, horizon, 
                          experiment_name, model_type):
        """Start a research/scenario job."""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            # Prepare request based on job type
            payload = {
                "job_type": job_type,
                "parameters": {}
            }
            
            if job_type == 'scenario':
                payload["scenario_name"] = scenario_name or "Test Scenario"
                payload["universe"] = universe or "top200"
                payload["horizon"] = horizon or "1m"
            elif job_type == 'experiment':
                payload["experiment_name"] = experiment_name or "Test Experiment"
                payload["model_type"] = model_type or "lgb"
            
            # Call backend via API Gateway
            response = requests.post(
                f"{API_GATEWAY_URL}/api/research/jobs",
                json=payload,
                timeout=10
            )
            
            if response.status_code != 200:
                return None, True, f"Error: {response.text}", "danger", True
            
            data = response.json()
            job_id = data.get("job_id")
            
            logger.info(f"Started research job: {job_id}")
            
            return (
                job_id,
                False,  # Enable polling
                f"{job_type.title()} analysis started...",
                "info",
                True
            )
            
        except Exception as e:
            logger.error(f"Error starting research job: {e}")
            return None, True, f"Error: {str(e)}", "danger", True
    
    @app.callback(
        [
            Output('research-results-area', 'children'),
            Output('research-progress-bar', 'value'),
            Output('research-progress-bar', 'style'),
            Output('research-poll-interval', 'disabled', allow_duplicate=True),
            Output('research-status-alert', 'children', allow_duplicate=True),
            Output('research-status-alert', 'color', allow_duplicate=True),
            Output('research-status-alert', 'is_open', allow_duplicate=True),
        ],
        [Input('research-poll-interval', 'n_intervals')],
        [State('research-current-job-id', 'data')],
        prevent_initial_call=True
    )
    def poll_research_status(n_intervals, job_id):
        """Poll for research job status and display results."""
        if not job_id:
            raise PreventUpdate
        
        try:
            # Check job status
            response = requests.get(
                f"{API_GATEWAY_URL}/api/research/jobs/{job_id}",
                timeout=5
            )
            
            if response.status_code != 200:
                return (
                    html.Div("Error checking job status", className="text-danger"),
                    0,
                    {'display': 'none'},
                    True,
                    f"Error: {response.text}",
                    "danger",
                    True
                )
            
            data = response.json()
            status = data.get("status")
            progress = data.get("progress", 0) * 100
            message = data.get("message", "")
            
            # Update progress bar
            progress_style = {'display': 'block'} if status in ["pending", "running"] else {'display': 'none'}
            
            if status == "completed":
                # Job finished - render results
                result = data.get("result", {})
                results_ui = render_research_results(result)
                
                return (
                    results_ui,
                    100,
                    {'display': 'none'},
                    True,
                    "✓ Analysis complete",
                    "success",
                    True
                )
            
            elif status == "failed":
                error = data.get("error", "Unknown error")
                return (
                    html.Div([
                        html.H5("❌ Job Failed", className="text-danger"),
                        html.P(error)
                    ]),
                    0,
                    {'display': 'none'},
                    True,
                    f"Error: {error}",
                    "danger",
                    True
                )
            
            else:
                # Still running - keep polling
                return (
                    html.Div([
                        html.H5("Processing...", className="text-info"),
                        html.P(message)
                    ]),
                    progress,
                    progress_style,
                    False,
                    message,
                    "info",
                    True
                )
        
        except Exception as e:
            logger.error(f"Error polling research status: {e}")
            return (
                html.Div(f"Error: {str(e)}", className="text-danger"),
                0,
                {'display': 'none'},
                True,
                f"Error: {str(e)}",
                "danger",
                True
            )


def render_research_results(result: dict):
    """Render research/scenario analysis results."""
    if not result:
        return html.Div("No results available", className="text-muted")
    
    job_type = result.get("job_type", "unknown")
    
    if job_type == "scenario":
        return render_scenario_results(result)
    elif job_type == "experiment":
        return render_experiment_results(result)
    else:
        return html.Div([
            html.H4("Results", className="mb-3"),
            html.Pre(str(result))
        ])


def render_scenario_results(result: dict):
    """Render scenario analysis results."""
    metrics = result.get("metrics", {})
    top_picks = result.get("top_picks", [])
    
    # Metrics cards
    cards = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Expected Return", className="text-muted"),
                    html.H3(f"{metrics.get('expected_return', 0):.1f}%")
                ])
            ])
        ], width=2),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Sharpe Ratio", className="text-muted"),
                    html.H3(f"{metrics.get('sharpe_ratio', 0):.2f}")
                ])
            ])
        ], width=2),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Max Drawdown", className="text-muted"),
                    html.H3(f"{metrics.get('max_drawdown', 0):.1f}%", 
                           className="text-danger" if metrics.get('max_drawdown', 0) < 0 else "")
                ])
            ])
        ], width=2),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Win Rate", className="text-muted"),
                    html.H3(f"{metrics.get('win_rate', 0)*100:.0f}%")
                ])
            ])
        ], width=2),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Num Trades", className="text-muted"),
                    html.H3(f"{metrics.get('num_trades', 0)}")
                ])
            ])
        ], width=2)
    ], className="mb-4")
    
    # Top picks table
    if top_picks:
        picks_table = dash_table.DataTable(
            data=top_picks,
            columns=[
                {"name": "Symbol", "id": "symbol"},
                {"name": "Signal", "id": "signal", "type": "numeric", "format": {"specifier": ".2f"}},
                {"name": "Expected Return %", "id": "expected_return", "type": "numeric", "format": {"specifier": ".1f"}},
            ],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': '#1a1d23', 'fontWeight': 'bold'}
        )
    else:
        picks_table = html.Div("No picks generated", className="text-muted")
    
    return html.Div([
        html.H4(f"Scenario: {result.get('scenario_name', 'Unknown')}", className="mb-3"),
        html.P(result.get('summary', ''), className="text-muted"),
        cards,
        html.H5("Top Picks", className="mt-4 mb-3"),
        picks_table,
        html.Hr(),
        html.Small(f"Completed: {result.get('timestamp', 'Unknown')}", className="text-muted")
    ])


def render_experiment_results(result: dict):
    """Render experiment results."""
    metrics = result.get("metrics", {})
    features = metrics.get("feature_importance_top_5", [])
    
    # Metrics cards
    cards = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Train Accuracy", className="text-muted"),
                    html.H3(f"{metrics.get('train_accuracy', 0)*100:.1f}%")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Test Accuracy", className="text-muted"),
                    html.H3(f"{metrics.get('test_accuracy', 0)*100:.1f}%")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Train Sharpe", className="text-muted"),
                    html.H3(f"{metrics.get('train_sharpe', 0):.2f}")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Test Sharpe", className="text-muted"),
                    html.H3(f"{metrics.get('test_sharpe', 0):.2f}")
                ])
            ])
        ], width=3)
    ], className="mb-4")
    
    # Feature importance
    if features:
        feature_table = dash_table.DataTable(
            data=features,
            columns=[
                {"name": "Feature", "id": "feature"},
                {"name": "Importance", "id": "importance", "type": "numeric", "format": {"specifier": ".2f"}},
            ],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '10px'},
            style_header={'backgroundColor': '#1a1d23', 'fontWeight': 'bold'}
        )
    else:
        feature_table = html.Div("No feature importance data", className="text-muted")
    
    return html.Div([
        html.H4(f"Experiment: {result.get('experiment_name', 'Unknown')}", className="mb-3"),
        html.P(f"Model: {result.get('model_type', 'Unknown')}", className="text-muted"),
        cards,
        html.H5("Top Features", className="mt-4 mb-3"),
        feature_table,
        html.Hr(),
        html.Small(f"Completed: {result.get('timestamp', 'Unknown')}", className="text-muted")
    ])
