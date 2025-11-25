"""
Research Lab Tab - Experiment Sandbox

Controlled environment for testing new features, models, and strategies.
Provides reproducible experiment tracking with artifacts and promotion to production.

Usage:
    from modules import research_lab
    app.layout = html.Div([research_lab.layout()])
    research_lab.register_callbacks(app)
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
import yaml
from dash import dcc, html, Input, Output, State, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

# Import scenario analysis tab lazily to avoid top-level absolute import
import importlib.util
import types


def _load_scenario_analysis():
    """Dynamically load the scenario_analysis module from the tabs
    directory next to the financial_dashboard package. This avoids
    relying on package-level imports at module-import time which can
    fail when the package isn't installed in sys.path during dynamic
    exec_module calls performed by the app loader.
    """
    try:
        # Determine path to tabs/scenario_analysis.py relative to this file
        base_dir = os.path.dirname(os.path.dirname(__file__))  # financial_dashboard/
        scenario_path = os.path.join(base_dir, 'tabs', 'scenario_analysis.py')
        if not os.path.exists(scenario_path):
            logger.warning(f"scenario_analysis not found at {scenario_path}")
            return None

        module_name = 'financial_dashboard.tabs.scenario_analysis'
        spec = importlib.util.spec_from_file_location(module_name, scenario_path)
        if spec is None or spec.loader is None:
            logger.warning(f"Could not create spec for scenario_analysis at {scenario_path}")
            return None

        mod = importlib.util.module_from_spec(spec)
        # Set package so intra-package imports inside scenario_analysis can work
        mod.__package__ = 'financial_dashboard.tabs'
        spec.loader.exec_module(mod)
        logger.info("Loaded scenario_analysis module dynamically for Research Lab")
        return mod
    except Exception as e:
        logger.exception(f"Failed to dynamically load scenario_analysis: {e}")
        return None

logger = logging.getLogger(__name__)


def layout():
    """Build the Research Lab tab layout."""
    return dbc.Container([
        # Header
        html.Div([
            html.H2([html.I(className="bi bi-flask me-2"), "Research Lab"], 
                   className="mt-3 mb-3"),
            html.P("Experiment sandbox for testing new features and strategies", className="text-muted mb-4"),
        ], style={'background-color': '#2b3035', 'padding': '20px', 'border-radius': '8px', 'margin-bottom': '20px'}),
        
    # Main Tabs
    dbc.Tabs([
            # New Experiment Tab
            dbc.Tab(label="New Experiment", tab_id='tab-new-exp', children=[
                dbc.Container([
                    html.H5("Create New Experiment", className="mt-3 mb-3"),
                    
                    dbc.Card([
                        dbc.CardBody([
                            # Experiment Config
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Experiment Name:"),
                                    dcc.Input(id='exp-name', type='text', 
                                            placeholder='e.g., momentum_ablation_test',
                                            className='form-control mb-3')
                                ], width=6),
                                dbc.Col([
                                    html.Label("Description:"),
                                    dcc.Input(id='exp-description', type='text',
                                            placeholder='Brief description of experiment',
                                            className='form-control mb-3')
                                ], width=6)
                            ]),
                            
                            dbc.Row([
                                dbc.Col([
                                    html.Label("Universe:"),
                                    dcc.Dropdown(
                                        id='exp-universe',
                                        options=[
                                            {'label': 'Top 200 ADV', 'value': 'top200'},
                                            {'label': 'Top 1800 ADV', 'value': 'top1800'},
                                            {'label': 'S&P 500', 'value': 'sp500'},
                                            {'label': 'Custom', 'value': 'custom'}
                                        ],
                                        value='top200'
                                    )
                                ], width=4),
                                dbc.Col([
                                    html.Label("Target Horizon:"),
                                    dcc.Dropdown(
                                        id='exp-horizon',
                                        options=[
                                            {'label': '1 Week', 'value': '1w'},
                                            {'label': '1 Month', 'value': '1m'},
                                            {'label': '3 Months', 'value': '3m'}
                                        ],
                                        value='1m'
                                    )
                                ], width=4),
                                dbc.Col([
                                    html.Label("Model Type:"),
                                    dcc.Dropdown(
                                        id='exp-model',
                                        options=[
                                            {'label': 'LightGBM', 'value': 'lgb'},
                                            {'label': 'FineTune Small', 'value': 'ft_small'},
                                            {'label': 'NGBoost', 'value': 'ngboost'},
                                            {'label': 'Meta Ensemble', 'value': 'meta'}
                                        ],
                                        value='lgb'
                                    )
                                ], width=4)
                            ], className='mb-3'),
                            
                            html.H6("Feature Selection", className='mt-3 mb-2'),
                            dbc.Checklist(
                                id='exp-features',
                                options=[
                                    {'label': ' Momentum Features (ret_1m, ret_3m, ret_6m)', 'value': 'momentum'},
                                    {'label': ' Sentiment Features (finbert, pca_text)', 'value': 'sentiment'},
                                    {'label': ' Technical Indicators (RSI, MACD, Bollinger)', 'value': 'technical'},
                                    {'label': ' Fundamental (P/E, P/B, ROE)', 'value': 'fundamental'},
                                    {'label': ' Macro Features (VIX, TNX, oil)', 'value': 'macro'},
                                    {'label': ' Size/Liquidity (mktcap, adv)', 'value': 'size'}
                                ],
                                value=['momentum', 'sentiment', 'technical'],
                                inline=False,
                                switch=True
                            ),
                            
                            html.H6("Date Range", className='mt-3 mb-2'),
                            dcc.DatePickerRange(
                                id='exp-date-range',
                                start_date='2018-01-01',
                                end_date=datetime.now().date(),
                                display_format='YYYY-MM-DD'
                            ),
                            
                            dbc.Button("Run Experiment", id='exp-run-btn', 
                                      color='primary', size='lg', className='mt-4 w-100')
                        ])
                    ], className='mb-4'),
                    
                    dbc.Alert(id='exp-status', is_open=False, duration=4000),
                    
                    # Job Monitor
                    html.Div(id='exp-job-monitor')
                    
                ], fluid=True)
            ]),
            
            # Experiment History Tab
            dbc.Tab(label="Experiments", tab_id='tab-experiments', children=[
                dbc.Container([
                    html.H5("Experiment History", className="mt-3 mb-3"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Refresh", id='exp-refresh-btn', 
                                      color='primary', size='sm', className='me-2'),
                            dbc.Button("Compare Selected", id='exp-compare-btn',
                                      color='info', size='sm')
                        ])
                    ], className='mb-3'),
                    
                    html.Div(id='exp-history-table')
                    
                ], fluid=True)
            ]),
            
            # Results Tab
            dbc.Tab(label="Results", tab_id='tab-results', children=[
                dbc.Container([
                    html.H5("Experiment Results", className="mt-3 mb-3"),
                    
                    # Experiment Selection
                    dbc.Row([
                        dbc.Col([
                            html.Label("Select Experiment:"),
                            dcc.Dropdown(
                                id='exp-results-selector',
                                placeholder='Select an experiment to view results...',
                                options=[]  # Will be populated by callback
                            )
                        ], width=8),
                        dbc.Col([
                            dbc.Button("🔄 Refresh List", id='exp-results-refresh-btn',
                                      color='secondary', size='sm', className='mt-4')
                        ], width=4)
                    ], className='mb-4'),
                    
                    html.Div(id='exp-results-content', children=[
                        html.P("Select an experiment from the dropdown above to view results.", 
                              className="text-muted text-center p-5")
                    ])
                    
                ], fluid=True)
            ])
            ,
            # Scenario Lab Tab (embedded from tabs/scenario_analysis)
            dbc.Tab(label="Scenario Lab", tab_id='tab-scenario', children=[
                # Load layout lazily so imports don't fail during module load
                (lambda: (_load_scenario_analysis().layout() if _load_scenario_analysis() else html.Div("Scenario Lab unavailable")))()
            ])
    ], active_tab='tab-scenario'),
        
        # Experiment Details Modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle(id='exp-modal-title')),
            dbc.ModalBody(id='exp-modal-body'),
            dbc.ModalFooter([
                dbc.Button("Promote to Production", id='exp-modal-promote-btn', color='success'),
                dbc.Button("Download Artifacts", id='exp-modal-download-btn', color='info'),
                dbc.Button("Close", id='exp-modal-close-btn', color='secondary')
            ])
        ], id='exp-modal', size='xl', is_open=False),
        
        # Hidden stores
        dcc.Store(id='exp-list-store'),
        dcc.Store(id='selected-exp-store')
        
    ], fluid=True)


def register_callbacks(app):
    """Register all research lab callbacks."""
    # Ensure Scenario Analysis callbacks are registered once at startup so the
    # embedded tab functions immediately (prevents the tab being inert until an
    # experiment is run).
    try:
        sa = _load_scenario_analysis()
        if sa and hasattr(sa, 'register_callbacks'):
            sa.register_callbacks(app)
            logger.info("Scenario Analysis callbacks registered at Research Lab startup")
        else:
            logger.info("Scenario Analysis not available to register callbacks at Research Lab startup")
    except Exception as e:
        logger.exception("Failed to register scenario_analysis callbacks at startup: %s", e)
    
    @app.callback(
        [Output('exp-status', 'children'),
         Output('exp-status', 'color'),
         Output('exp-status', 'is_open')],
        [Input('exp-run-btn', 'n_clicks')],
        [State('exp-name', 'value'),
         State('exp-description', 'value'),
         State('exp-universe', 'value'),
         State('exp-horizon', 'value'),
         State('exp-model', 'value'),
         State('exp-features', 'value'),
         State('exp-date-range', 'start_date'),
         State('exp-date-range', 'end_date')]
    )
    def run_experiment(n_clicks, name, desc, universe, horizon, model, features, 
                      start_date, end_date):
        """Submit a new experiment job."""
        if not n_clicks:
            raise PreventUpdate
        
        if not name:
            return "Experiment name is required", "warning", True

        # Scenario Analysis callbacks are registered at app startup
        
        try:
            # Create experiment config
            exp_config = {
                'name': name,
                'description': desc or '',
                'universe': universe,
                'horizon': horizon,
                'model': model,
                'features': features,
                'start_date': start_date,
                'end_date': end_date,
                'created_at': datetime.now().isoformat(),
                'status': 'running'  # Start as running instead of queued
            }
            
            # Save config to research/experiments/ and cache for immediate display
            exp_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            exp_dir = f"research/experiments/{exp_id}"
            os.makedirs(exp_dir, exist_ok=True)
            
            with open(f"{exp_dir}/config.yaml", 'w') as f:
                yaml.dump(exp_config, f)
            
            # Also save to cache for immediate UI update
            cache_file = "cache/research_experiments.json"
            os.makedirs(os.path.dirname(cache_file), exist_ok=True)
            
            try:
                with open(cache_file, 'r') as f:
                    experiments = json.load(f)
                # Ensure experiments is a list, not a dict
                if not isinstance(experiments, list):
                    experiments = []
            except (FileNotFoundError, json.JSONDecodeError):
                experiments = []
            
            # Add new experiment to cache with result placeholders
            experiments.append({
                'exp_id': exp_id,
                'name': name,
                'description': desc or '',
                'model': model,
                'horizon': horizon,
                'universe': universe,
                'features': features,
                'oof_ic': 0.0,  # Placeholder - will be updated when runner completes
                'sharpe': 0.0,  # Placeholder
                'status': 'running',
                'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            with open(cache_file, 'w') as f:
                json.dump(experiments, f, indent=2)
            
            # Launch backend runner as subprocess with robust error handling
            import subprocess
            import sys
            
            # Use sys.executable for reliable Python path
            runner_script = os.path.join(os.getcwd(), 'research', 'runner.py')
            runner_cmd = [sys.executable, runner_script, '--exp-id', exp_id]
            
            # Per-experiment log file
            log_file = os.path.join(exp_dir, 'runner.log')
            pid_file = os.path.join(exp_dir, 'runner.pid')
            
            try:
                # Start runner in background with log redirection
                with open(log_file, 'w') as log_fh:
                    process = subprocess.Popen(
                        runner_cmd,
                        stdout=log_fh,
                        stderr=subprocess.STDOUT,
                        cwd=os.getcwd(),
                        start_new_session=True  # Detach from parent process group
                    )
                
                # Save PID for tracking
                with open(pid_file, 'w') as f:
                    f.write(str(process.pid))
                
                logger.info(f"Launched runner for experiment '{name}' (ID: {exp_id}, PID: {process.pid})")
                logger.info(f"Runner logs: {log_file}")
                
                return (f"✅ Experiment '{name}' started! ID: {exp_id}, PID: {process.pid}. "
                       f"Running in background - check Experiments tab for results. Logs: {log_file}", 
                       "success", True)
            except Exception as e:
                logger.exception(f"Failed to launch runner for experiment '{name}': {e}")
                
                # Update cache to mark as failed
                try:
                    for exp in experiments:
                        if exp['exp_id'] == exp_id:
                            exp['status'] = 'failed'
                            exp['error'] = str(e)
                            break
                    with open(cache_file, 'w') as f:
                        json.dump(experiments, f, indent=2)
                except Exception as cache_err:
                    logger.error(f"Failed to update cache with error status: {cache_err}")
                
                return (f"❌ Experiment '{name}' created but runner failed to start: {str(e)}", 
                       "danger", True)
            
        except Exception as e:
            logger.error(f"Error running experiment: {e}")
            return f"Error: {str(e)}", "danger", True
    
    @app.callback(
        Output('exp-list-store', 'data'),
        [Input('exp-refresh-btn', 'n_clicks')]
    )
    def refresh_experiments(n_clicks):
        """Load experiment history."""
        try:
            experiments = _load_experiment_history()
            return experiments
        except Exception as e:
            logger.error(f"Error loading experiments: {e}")
            return []
    
    @app.callback(
        Output('exp-history-table', 'children'),
        [Input('exp-list-store', 'data')]
    )
    def update_history_table(experiments):
        """Update experiment history table."""
        if not experiments:
            return html.Div("No experiments found. Create one to get started!", 
                          className="text-muted text-center p-4")
        
        df = pd.DataFrame(experiments)
        
        table = dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[
                {'name': 'ID', 'id': 'exp_id'},
                {'name': 'Name', 'id': 'name'},
                {'name': 'Model', 'id': 'model'},
                {'name': 'Horizon', 'id': 'horizon'},
                {'name': 'OOF IC', 'id': 'oof_ic', 'type': 'numeric', 'format': {'specifier': '.4f'}},
                {'name': 'Sharpe', 'id': 'sharpe', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                {'name': 'Status', 'id': 'status'},
                {'name': 'Created', 'id': 'created_at'}
            ],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': '#2b3035', 'fontWeight': 'bold'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{status} = "completed"'},
                    'backgroundColor': '#10b98120',
                },
                {
                    'if': {'filter_query': '{status} = "failed"'},
                    'backgroundColor': '#ef444420',
                }
            ],
            page_size=20,
            sort_action='native',
            filter_action='native',
            row_selectable='multi'
        )
        
        return table
    
    # Callback to populate experiment results dropdown
    @app.callback(
        Output('exp-results-selector', 'options'),
        [Input('exp-results-refresh-btn', 'n_clicks'),
         Input('exp-list-store', 'data')]
    )
    def populate_results_dropdown(n_clicks, experiments):
        """Populate the results dropdown with completed experiments."""
        try:
            # Normalize possible shapes of 'experiments' coming from dcc.Store
            if not experiments:
                return []

            # If experiments was serialized as a JSON string, try to decode it
            if isinstance(experiments, str):
                try:
                    experiments = json.loads(experiments)
                except Exception:
                    logger.exception("Failed to json-decode experiments store value")
                    return []

            # Some callers may wrap the list in a dict under a key like 'experiments'
            if isinstance(experiments, dict) and 'experiments' in experiments:
                experiments = experiments.get('experiments')

            # Ensure we have a list
            if not isinstance(experiments, list):
                logger.warning("Unexpected experiments store type: %s", type(experiments))
                return []

            # Filter for completed experiments only
            completed_exps = [exp for exp in experiments if isinstance(exp, dict) and exp.get('status') == 'completed']

            options = [
                {'label': f"{exp.get('name', 'unnamed')} ({exp.get('exp_id', 'unknown')}) - IC: {exp.get('oof_ic', 0):.4f}",
                 'value': exp.get('exp_id')}
                for exp in completed_exps if exp.get('exp_id')
            ]

            return options
        except Exception as e:
            # Catch all to avoid raising an exception that becomes a 500 in Dash
            logger.exception("Error populating exp-results-selector options: %s", e)
            return []
    
    # Callback to display experiment results
    @app.callback(
        Output('exp-results-content', 'children'),
        [Input('exp-results-selector', 'value')]
    )
    def display_experiment_results(exp_id):
        """Display detailed results for selected experiment."""
        if not exp_id:
            return html.P("Select an experiment from the dropdown above to view results.", 
                         className="text-muted text-center p-5")
        
        try:
            # Load experiment data
            experiments = _load_experiment_history()
            exp_data = next((exp for exp in experiments if exp['exp_id'] == exp_id), None)
            
            if not exp_data:
                return html.Div("Experiment not found.", className="text-danger text-center p-4")
            
            # Build results display
            return dbc.Container([
                # Summary Cards
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Out-of-Fold IC", className="text-muted"),
                                html.H3(f"{exp_data.get('oof_ic', 0):.4f}", 
                                       className="text-success" if exp_data.get('oof_ic', 0) > 0.04 else "")
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Sharpe Ratio", className="text-muted"),
                                html.H3(f"{exp_data.get('sharpe', 0):.2f}",
                                       className="text-success" if exp_data.get('sharpe', 0) > 1.0 else "")
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Model Type", className="text-muted"),
                                html.H3(exp_data.get('model', 'N/A').upper())
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Status", className="text-muted"),
                                html.H3(exp_data.get('status', 'N/A').upper(),
                                       className="text-success")
                            ])
                        ])
                    ], width=3)
                ], className="mb-4"),
                
                # Experiment Details
                dbc.Card([
                    dbc.CardHeader(html.H5("Experiment Configuration")),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Strong("Name: "),
                                html.Span(exp_data.get('name', 'N/A'))
                            ], width=6),
                            dbc.Col([
                                html.Strong("Horizon: "),
                                html.Span(exp_data.get('horizon', 'N/A'))
                            ], width=6)
                        ], className="mb-2"),
                        dbc.Row([
                            dbc.Col([
                                html.Strong("Created: "),
                                html.Span(exp_data.get('created_at', 'N/A'))
                            ], width=6),
                            dbc.Col([
                                html.Strong("Experiment ID: "),
                                html.Code(exp_data.get('exp_id', 'N/A'))
                            ], width=6)
                        ])
                    ])
                ], className="mb-4"),
                
                # Load actual artifacts if available
                dbc.Card([
                    dbc.CardHeader(html.H5("Performance Metrics")),
                    dbc.CardBody([
                        _load_experiment_artifacts(exp_id)
                    ])
                ], className="mb-4"),
                
                # OOF Predictions Preview
                dbc.Card([
                    dbc.CardHeader(html.H5("Out-of-Fold Predictions (Preview)")),
                    dbc.CardBody([
                        _load_oof_predictions_preview(exp_id)
                    ])
                ])
            ], fluid=True)
            
        except Exception as e:
            # Log full traceback to help debugging server-side 500s
            logger.exception("Error displaying experiment results: %s", e)
            return html.Div(f"Error loading results: {str(e)}", className="text-danger text-center p-4")
    
    logger.info("Research Lab callbacks registered")


def _load_experiment_history():
    """Load experiment history from cache file."""
    cache_file = "cache/research_experiments.json"
    
    try:
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                experiments = json.load(f)
                return experiments
    except Exception as e:
        logger.error(f"Error loading experiment cache: {e}")
    
    # Return sample data if cache doesn't exist
    sample_data = [
        {
            'exp_id': 'exp_20250901_120000',
            'name': 'momentum_ablation',
            'model': 'lgb',
            'horizon': '1m',
            'oof_ic': 0.0453,
            'sharpe': 1.23,
            'status': 'completed',
            'created_at': '2025-09-01 12:00:00'
        },
        {
            'exp_id': 'exp_20250915_080000',
            'name': 'sentiment_only',
            'model': 'lgb',
            'horizon': '1m',
            'oof_ic': 0.0312,
            'sharpe': 0.89,
            'status': 'completed',
            'created_at': '2025-09-15 08:00:00'
        },
        {
            'exp_id': 'exp_20251001_140000',
            'name': 'meta_ensemble_test',
            'model': 'meta',
            'horizon': '1m',
            'oof_ic': 0.0521,
            'sharpe': 1.45,
            'status': 'completed',
            'created_at': '2025-10-01 14:00:00'
        }
    ]
    
    # Save sample data to cache on first run
    os.makedirs(os.path.dirname(cache_file), exist_ok=True)
    with open(cache_file, 'w') as f:
        json.dump(sample_data, f, indent=2)
    
    return sample_data


def _load_experiment_artifacts(exp_id: str):
    """Load and display experiment artifacts (feature importance, OOF scatter)"""
    exp_dir = Path(f'research/experiments/{exp_id}')
    
    if not exp_dir.exists():
        return html.P("Experiment directory not found.", className="text-muted")
    
    # Load report.json
    report_file = exp_dir / 'report.json'
    if report_file.exists():
        with open(report_file, 'r') as f:
            report = json.load(f)
        
        metrics = report.get('metrics', {})
        
        components = []
        
        # Metrics table
        metrics_table = dbc.Table([
            html.Thead([
                html.Tr([html.Th("Metric"), html.Th("Value")])
            ]),
            html.Tbody([
                html.Tr([html.Td("Out-of-Fold IC"), html.Td(f"{metrics.get('oof_ic', 0):.4f}")]),
                html.Tr([html.Td("Rank IC"), html.Td(f"{metrics.get('rank_ic', 0):.4f}")]),
                html.Tr([html.Td("Hit Rate"), html.Td(f"{metrics.get('hit_rate', 0):.2%}")]),
                html.Tr([html.Td("Sharpe Ratio"), html.Td(f"{metrics.get('sharpe', 0):.2f}")]),
                html.Tr([html.Td("Mean Return"), html.Td(f"{metrics.get('mean_return', 0):.4f}")]),
                html.Tr([html.Td("Volatility"), html.Td(f"{metrics.get('volatility', 0):.4f}")])
            ])
        ], bordered=True, striped=True, className="mb-3")
        
        components.append(metrics_table)
        
        # Feature importance plot
        feat_imp_file = exp_dir / 'feature_importance.png'
        if feat_imp_file.exists():
            import base64
            with open(feat_imp_file, 'rb') as f:
                img_data = base64.b64encode(f.read()).decode()
            
            components.append(
                html.Div([
                    html.H6("Feature Importance", className="mt-3 mb-2"),
                    html.Img(src=f"data:image/png;base64,{img_data}", 
                            style={'max-width': '100%', 'height': 'auto'})
                ])
            )
        
        return html.Div(components)
    else:
        return html.P("Report not yet available. Experiment may still be running.", 
                     className="text-muted")


def _load_oof_predictions_preview(exp_id: str):
    """Load and preview OOF predictions CSV"""
    exp_dir = Path(f'research/experiments/{exp_id}')
    oof_file = exp_dir / 'oof_preds.csv'
    
    if not oof_file.exists():
        return html.P("OOF predictions not yet available.", className="text-muted")
    
    # Load and display first 50 rows
    df = pd.read_csv(oof_file)
    
    # Add prediction error column
    df['error'] = df['y_pred'] - df['y_true']
    
    preview_df = df.head(50)[['date', 'ticker', 'y_true', 'y_pred', 'error', 'fold']]
    
    return html.Div([
        html.P(f"Showing first 50 of {len(df)} predictions", className="text-muted mb-2"),
        dash_table.DataTable(
            data=preview_df.to_dict('records'),
            columns=[
                {'name': 'Date', 'id': 'date'},
                {'name': 'Ticker', 'id': 'ticker'},
                {'name': 'True Return', 'id': 'y_true', 'type': 'numeric', 'format': {'specifier': '.4f'}},
                {'name': 'Predicted Return', 'id': 'y_pred', 'type': 'numeric', 'format': {'specifier': '.4f'}},
                {'name': 'Error', 'id': 'error', 'type': 'numeric', 'format': {'specifier': '.4f'}},
                {'name': 'Fold', 'id': 'fold', 'type': 'numeric'}
            ],
            style_table={'overflowX': 'auto', 'max-height': '400px', 'overflowY': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px'},
            style_header={'backgroundColor': '#2b3035', 'fontWeight': 'bold'},
            page_size=50,
            sort_action='native',
            filter_action='native'
        )
    ])
