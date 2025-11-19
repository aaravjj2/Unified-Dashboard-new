"""
Scenario Analysis Interactive Tab

Provides an interactive UI to test "what-if" scenarios on forecast models:
- Sliders for macro inputs (VIX, TNX, Oil, SPY)
- Apply deltas to features and rerun predictions
- Show before/after predictions
- Display winners/losers from scenario changes
- Impact visualization

Usage:
    from tabs import scenario_analysis
    app.layout = html.Div([scenario_analysis.layout()])
    scenario_analysis.register_callbacks(app)
"""

import os
import json
import logging
from datetime import datetime
import pandas as pd
import numpy as np
from dash import dcc, html, Input, Output, State, dash_table, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import joblib

from financial_dashboard from financial_dashboard import _shared as SH
# add canonical key helper
from financial_dashboard import key_names as KN

logger = logging.getLogger(__name__)


def layout():
    """Build the Scenario Analysis tab layout."""
    return dbc.Container([
        html.H2("Scenario Analysis", className="mt-3 mb-3"),
        html.P("Test how changes in market conditions affect stock predictions", 
               className="text-muted mb-4"),
        
        # Scenario Configuration
        dbc.Card([
            dbc.CardBody([
                html.H5("Scenario Configuration", className="mb-3"),
                
                dbc.Row([
                    # VIX Delta
                    dbc.Col([
                        html.Label("VIX Change:"),
                        dcc.Slider(
                            id='scenario-vix-change',
                            min=-10,
                            max=10,
                            step=0.5,
                            value=0,
                            marks={i: f"{i:+.0f}" for i in range(-10, 11, 2)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        ),
                        html.Small("Change in VIX points", className="text-muted")
                    ], width=6),
                    
                    # TNX Delta
                    dbc.Col([
                        html.Label("10Y Treasury Yield Change:"),
                        dcc.Slider(
                            id='scenario-tnx-change',
                            min=-1,
                            max=1,
                            step=0.1,
                            value=0,
                            marks={i/10: f"{i/10:+.1f}%" for i in range(-10, 11, 2)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        ),
                        html.Small("Change in yield percentage", className="text-muted")
                    ], width=6)
                ], className="mb-3"),
                
                dbc.Row([
                    # Oil Delta
                    dbc.Col([
                        html.Label("Oil Price Change:"),
                        dcc.Slider(
                            id='scenario-oil-change',
                            min=-20,
                            max=20,
                            step=1,
                            value=0,
                            marks={i: f"{i:+d}%" for i in range(-20, 21, 5)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        ),
                        html.Small("Percentage change in oil price", className="text-muted")
                    ], width=6),
                    
                    # SPY Delta
                    dbc.Col([
                        html.Label("SPY Return Change:"),
                        dcc.Slider(
                            id='scenario-spy-change',
                            min=-10,
                            max=10,
                            step=0.5,
                            value=0,
                            marks={i: f"{i:+d}%" for i in range(-10, 11, 2)},
                            tooltip={"placement": "bottom", "always_visible": True}
                        ),
                        html.Small("Change in SPY return", className="text-muted")
                    ], width=6)
                ], className="mb-3"),
                
                dbc.Row([
                    dbc.Col([
                        html.Label("Universe:"),
                        dcc.Dropdown(
                            id='scenario-universe',
                            options=[
                                {'label': 'Top 200 Stocks', 'value': 'top200'},
                                {'label': 'S&P 500', 'value': 'sp500'},
                                {'label': 'Weekly Picks', 'value': 'weekly'}
                            ],
                            value='top200',
                            clearable=False
                        )
                    ], width=4),
                    dbc.Col([
                        html.Label("Model:"),
                        dcc.Dropdown(
                            id='scenario-model',
                            options=[
                                {'label': 'LightGBM', 'value': 'lgb'},
                                {'label': 'Meta Model', 'value': 'meta'},
                                {'label': 'FT Small', 'value': 'ft'}
                            ],
                            value='lgb',
                            clearable=False
                        )
                    ], width=3),
                    dbc.Col([
                        html.Label("Scenario Type:"),
                        dcc.Dropdown(
                            id='scenario-type',
                            options=[
                                {'label': 'Macro (Market Shocks)', 'value': 'macro'},
                                {'label': 'Factor (Style) Shock', 'value': 'factor'}
                            ],
                            value='macro',
                            clearable=False
                        )
                    ], width=3),
                    dbc.Col([
                        dbc.Button(
                            "Run Scenario",
                            id='scenario-run-btn',
                            color='primary',
                            size='lg',
                            className="mt-4 w-100"
                        )
                    ], width=3),
                    dbc.Col([
                        html.Div(id='scenario-preset-container', children=[
                            html.Label("Preset:"),
                            dcc.Dropdown(
                                id='scenario-preset',
                                options=[],
                                placeholder='Select a preset (optional)'
                            )
                        ])
                    ], width=3)
                ])
            ])
        ], className="mb-4"),
        
        # Status
        dbc.Alert(
            id='scenario-status',
            color='info',
            is_open=False,
            duration=4000
        ),
        
        # Results
        html.Div(id='scenario-results-container', children=[
            # Impact Summary Cards
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Average Impact", className="text-muted"),
                            html.H4(id='scenario-avg-impact', children="--")
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Winners", className="text-muted"),
                            html.H4(id='scenario-winners-count', children="--", 
                                   style={'color': '#10b981'})
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Losers", className="text-muted"),
                            html.H4(id='scenario-losers-count', children="--",
                                   style={'color': '#ef4444'})
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Max Impact", className="text-muted"),
                            html.H4(id='scenario-max-impact', children="--")
                        ])
                    ])
                ], width=3)
            ], className="mb-4"),
            
            # Impact Distribution Chart
            dbc.Card([
                dbc.CardBody([
                    html.H5("Prediction Impact Distribution", className="mb-3"),
                    dcc.Graph(id='scenario-impact-dist')
                ])
            ], className="mb-4"),
            
            # Winners and Losers Tables
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Top Winners", className="mb-3"),
                            html.Div(id='scenario-winners-table')
                        ])
                    ])
                ], width=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H5("Top Losers", className="mb-3"),
                            html.Div(id='scenario-losers-table')
                        ])
                    ])
                ], width=6)
            ], className="mb-4"),
            
            # Sector Impact
            dbc.Card([
                dbc.CardBody([
                    html.H5("Sector Impact Analysis", className="mb-3"),
                    dcc.Graph(id='scenario-sector-chart')
                ])
            ]),

            # Hedging candidates
            dbc.Card([
                dbc.CardBody([
                    html.H5("Hedging Candidates", className="mb-3"),
                    html.Div(id='scenario-hedging-table')
                ])
            ], className='mb-4'),

            # Visible results anchor for tests
            html.Div(id='scenario-results'),

        ]),
        
        # Hidden stores
        dcc.Store(id='scenario-results-store'),
        dcc.Store(id='scenario-baseline-store')
        
    ], fluid=True)


def register_callbacks(app):
    """Register all callbacks for the Scenario Analysis tab."""
    
    @app.callback(
       [Output('scenario-status', 'children'),
        Output('scenario-status', 'is_open'),
        Output('scenario-status', 'color'),
        Output('scenario-results-store', 'data'),
        Output('scenario-baseline-store', 'data'),
        Output('scenario-results-container', 'style'),
        Output('scenario-results', 'children')],
       [Input('scenario-run-btn', 'n_clicks')],
       [State('scenario-vix-change', 'value'),
        State('scenario-tnx-change', 'value'),
        State('scenario-oil-change', 'value'),
        State('scenario-spy-change', 'value'),
        State('scenario-universe', 'value'),
        State('scenario-model', 'value')]
    )
    def run_scenario_analysis(n_clicks, vix_delta, tnx_delta, oil_delta, spy_delta,
                              universe, model_type):
        """Run scenario analysis when button is clicked."""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            # Load model
            model = _load_model(model_type)
            if model is None:
                return ("Model not found", True, 'danger', None, None, {'display': 'none'}, html.Div())
            
            # Get universe tickers
            tickers = _get_universe_tickers(universe)
            if not tickers:
                return ("No tickers found", True, 'warning', None, None, {'display': 'none'}, html.Div())
            
            # Generate baseline features
            baseline_features = _generate_features(tickers, {})
            if baseline_features is None or baseline_features.empty:
                return ("Could not generate features", True, 'danger', 
                       None, None, {'display': 'none'}, html.Div())
            
            # Baseline predictions
            baseline_preds = _make_predictions(model, baseline_features)
            
            # Scenario features (with deltas applied)
            scenario_deltas = {
                'vix': vix_delta,
                'tnx': tnx_delta / 100,  # Convert to decimal
                'oil': oil_delta / 100,
                'spy': spy_delta / 100
            }
            
            scenario_features = _generate_features(tickers, scenario_deltas)
            scenario_preds = _make_predictions(model, scenario_features)
            
            # Calculate impacts
            results = _calculate_scenario_impacts(
                baseline_features, 
                baseline_preds, 
                scenario_preds
            )
            
            if not results:
                return ("Analysis failed", True, 'danger', None, None, {'display': 'none'}, html.Div())

            # Create a simple visible summary for Playwright tests
            summary_html = html.Div([
                html.H6(f"Analyzed {len(results)} stocks"),
                html.P("Scenario analysis complete")
            ])

            return (f"Scenario analysis complete: {len(results)} stocks analyzed",
                   True, 'success',
                   results,
                   {'tickers': tickers, 'deltas': scenario_deltas},
                   {'display': 'block'},
                   summary_html)
            
        except Exception as e:
            logger.error(f"Error running scenario analysis: {e}", exc_info=True)
            return (f"Error: {str(e)}", True, 'danger', None, None, {'display': 'none'}, html.Div())
    
    
    @app.callback(
        [Output('scenario-avg-impact', 'children'),
         Output('scenario-winners-count', 'children'),
         Output('scenario-losers-count', 'children'),
         Output('scenario-max-impact', 'children')],
        [Input('scenario-results-store', 'data')]
    )
    def update_summary_cards(results):
        """Update summary metric cards."""
        if not results:
            raise PreventUpdate
        
        impacts = [r['impact'] for r in results]
        avg_impact = np.mean(impacts)
        winners = sum(1 for i in impacts if i > 0)
        losers = sum(1 for i in impacts if i < 0)
        max_impact = max(abs(i) for i in impacts)
        
        return (
            f"{avg_impact:+.2%}",
            str(winners),
            str(losers),
            f"{max_impact:.2%}"
        )
    
    
    @app.callback(
        Output('scenario-impact-dist', 'figure'),
        [Input('scenario-results-store', 'data')]
    )
    def update_impact_distribution(results):
        """Create histogram of prediction impacts."""
        if not results:
            return go.Figure()
        
        impacts = [r['impact'] * 100 for r in results]  # Convert to percentage
        
        fig = go.Figure()
        fig.add_trace(go.Histogram(
            x=impacts,
            nbinsx=30,
            marker_color='rgb(59, 130, 246)',
            name='Impact Distribution'
        ))
        
        fig.add_vline(x=0, line_dash="dash", line_color="white", opacity=0.5)
        fig.add_vline(x=np.mean(impacts), line_dash="dot", 
                     line_color="yellow", opacity=0.7,
                     annotation_text="Mean")
        
        fig.update_layout(
            title="Distribution of Prediction Impacts",
            xaxis_title="Impact on Prediction (%)",
            yaxis_title="Number of Stocks",
            template='plotly_dark',
            showlegend=False
        )
        
        return fig
    
    
    @app.callback(
        Output('scenario-winners-table', 'children'),
        [Input('scenario-results-store', 'data')]
    )
    def update_winners_table(results):
        """Display top winners table."""
        if not results:
            raise PreventUpdate
        
        # Sort by impact descending
        sorted_results = sorted(results, key=lambda x: x['impact'], reverse=True)
        top_winners = sorted_results[:10]
        
        df = pd.DataFrame(top_winners)
        df['baseline'] = df['baseline'].apply(lambda x: f"{x:.2%}")
        df['scenario'] = df['scenario'].apply(lambda x: f"{x:.2%}")
        df['impact'] = df['impact'].apply(lambda x: f"{x:+.2%}")
        
        return dash_table.DataTable(
            data=df[['ticker', 'baseline', 'scenario', 'impact', 'sector']].to_dict('records'),
            columns=[
                {'name': 'Ticker', 'id': 'ticker'},
                {'name': 'Baseline', 'id': 'baseline'},
                {'name': 'Scenario', 'id': 'scenario'},
                {'name': 'Impact', 'id': 'impact'},
                {'name': 'Sector', 'id': 'sector'}
            ],
            style_table={'overflowX': 'auto'},
            style_cell={
                'backgroundColor': 'rgb(17, 24, 39)',
                'color': 'white',
                'textAlign': 'left',
                'padding': '8px'
            },
            style_header={
                'backgroundColor': 'rgb(31, 41, 55)',
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {
                    'if': {'column_id': 'impact'},
                    'color': '#10b981',
                    'fontWeight': 'bold'
                }
            ]
        )
    
    
    @app.callback(
        Output('scenario-losers-table', 'children'),
        [Input('scenario-results-store', 'data')]
    )
    def update_losers_table(results):
        """Display top losers table."""
        if not results:
            raise PreventUpdate
        
        # Sort by impact ascending
        sorted_results = sorted(results, key=lambda x: x['impact'])
        top_losers = sorted_results[:10]
        
        df = pd.DataFrame(top_losers)
        df['baseline'] = df['baseline'].apply(lambda x: f"{x:.2%}")
        df['scenario'] = df['scenario'].apply(lambda x: f"{x:.2%}")
        df['impact'] = df['impact'].apply(lambda x: f"{x:+.2%}")
        
        return dash_table.DataTable(
            data=df[['ticker', 'baseline', 'scenario', 'impact', 'sector']].to_dict('records'),
            columns=[
                {'name': 'Ticker', 'id': 'ticker'},
                {'name': 'Baseline', 'id': 'baseline'},
                {'name': 'Scenario', 'id': 'scenario'},
                {'name': 'Impact', 'id': 'impact'},
                {'name': 'Sector', 'id': 'sector'}
            ],
            style_table={'overflowX': 'auto'},
            style_cell={
                'backgroundColor': 'rgb(17, 24, 39)',
                'color': 'white',
                'textAlign': 'left',
                'padding': '8px'
            },
            style_header={
                'backgroundColor': 'rgb(31, 41, 55)',
                'fontWeight': 'bold'
            },
            style_data_conditional=[
                {
                    'if': {'column_id': 'impact'},
                    'color': '#ef4444',
                    'fontWeight': 'bold'
                }
            ]
        )
    
    
    @app.callback(
        Output('scenario-sector-chart', 'figure'),
        [Input('scenario-results-store', 'data')]
    )
    def update_sector_chart(results):
        """Create sector-level impact analysis."""
        if not results:
            return go.Figure()
        
        df = pd.DataFrame(results)
        
        # Group by sector
        sector_impact = df.groupby('sector')['impact'].agg(['mean', 'count']).reset_index()
        sector_impact = sector_impact.sort_values('mean', ascending=True)
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            y=sector_impact['sector'],
            x=sector_impact['mean'] * 100,
            orientation='h',
            marker_color=['#ef4444' if x < 0 else '#10b981' 
                         for x in sector_impact['mean']],
            text=[f"{x:.2f}%" for x in sector_impact['mean'] * 100],
            textposition='auto'
        ))
        
        fig.add_vline(x=0, line_dash="dash", line_color="white", opacity=0.5)
        
        fig.update_layout(
            title="Average Impact by Sector",
            xaxis_title="Average Impact (%)",
            yaxis_title="Sector",
            template='plotly_dark',
            showlegend=False,
            height=400
        )
        
        return fig

    # Register additional UI callbacks (presets, hedging) into the same app
    try:
        register_extra_callbacks(app)
        logger.info("Registered extra scenario callbacks (presets, hedging)")
    except Exception as e:
        logger.exception("Failed to register extra scenario callbacks: %s", e)


def _load_model(model_type):
    """Load the specified model."""
    try:
        # Find the most recent model file
        import glob
        
        # Use DASH_ROOT to find models in the Dash directory
        dash_root = getattr(SH, 'DASH_ROOT', SH.PROJECT_ROOT)
        
        # Search in both models/ and models/full_run/ directories
        search_dirs = [
            os.path.join(dash_root, 'models', 'full_run'),
            os.path.join(dash_root, 'models')
        ]
        
        if model_type == 'lgb':
            filename_pattern = 'lightgbm_fold*_*.joblib'
        elif model_type == 'meta':
            filename_pattern = 'stacker_ridge_*.joblib'
        else:
            filename_pattern = 'lightgbm_fold*_*.joblib'
        
        # Search in all directories
        model_files = []
        for search_dir in search_dirs:
            pattern = os.path.join(search_dir, filename_pattern)
            model_files.extend(glob.glob(pattern))
        
        if not model_files:
            logger.warning(f"No model files found matching: {filename_pattern} in {search_dirs}")
            return None
        
        # Sort by filename (which includes date) and get the most recent
        latest_model = sorted(model_files)[-1]
        logger.info(f"Loading model: {latest_model}")
        
        return joblib.load(latest_model)
        
    except Exception as e:
        logger.error(f"Error loading model: {e}")
        return None


def _get_universe_tickers(universe):
    """Get list of tickers for the specified universe."""
    try:
        dash_root = getattr(SH, 'DASH_ROOT', SH.PROJECT_ROOT)
        
        if universe == 'top200':
            # Try to load from a universe file
            universe_path = os.path.join(dash_root, 'data', 'universe_top200.txt')
            if os.path.exists(universe_path):
                with open(universe_path, 'r') as f:
                    return [line.strip() for line in f if line.strip()]
            
            # Fallback to S&P 100 sample
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B',
                   'JPM', 'JNJ', 'V', 'PG', 'UNH', 'MA', 'HD', 'DIS', 'BAC', 'ADBE']
        
        elif universe == 'sp500':
            # Load S&P 500 tickers
            try:
                import yfinance as yf
                sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
                return sp500['Symbol'].tolist()[:100]  # Limit for demo
            except:
                return _get_universe_tickers('top200')  # Fallback
        
        elif universe == 'weekly':
            # Load from latest weekly picks
            weekly_path = os.path.join(SH.PROJECT_ROOT, 'models', 'weekly_run')
            import glob
            csv_files = glob.glob(os.path.join(weekly_path, 'picks_*.csv'))
            if csv_files:
                latest = max(csv_files, key=os.path.getmtime)
                df = pd.read_csv(latest)
                return df['ticker'].unique().tolist()
            return _get_universe_tickers('top200')  # Fallback
        
        return []
        
    except Exception as e:
        logger.error(f"Error getting universe tickers: {e}")
        return []


def _generate_features(tickers, deltas):
    """
    Load real features from master_features.parquet and apply scenario deltas.

    Args:
        tickers: List of ticker symbols
        deltas: Dict with keys 'vix', 'tnx', 'oil', 'spy' and their scenario adjustments

    Returns:
        DataFrame with features for each ticker with deltas applied, or None on error
    """
    try:
        dash_root = getattr(SH, 'DASH_ROOT', SH.PROJECT_ROOT)
        features_path = os.path.join(dash_root, 'data', 'master_features.parquet')

        if not os.path.exists(features_path):
            logger.error(f"master_features.parquet not found at {features_path}")
            logger.info("Falling back to yfinance placeholder data")
            # Fallback to original yfinance implementation
            return _generate_features_fallback(tickers, deltas)

        # Load real features from parquet
        df = pd.read_parquet(features_path)
        logger.info(f"Loaded features from {features_path}: {len(df)} rows")

        # Filter to requested tickers
        if 'ticker' in df.columns:
            df = df[df['ticker'].isin(tickers)]
        else:
            logger.warning("No 'ticker' column in features dataframe")
            return None

        # Get latest features for each ticker
        if 'date' in df.columns:
            df = df.sort_values('date').groupby('ticker').tail(1)

        logger.info(f"Filtered to {len(df)} tickers with latest features")

        if df.empty:
            logger.warning("No features found for requested tickers")
            return None

        # Apply scenario deltas to relevant feature columns using KN helpers
        # VIX delta - add to VIX columns
        vix_cols = KN.find_matching_columns(df.columns, 'vix')
        for col in vix_cols:
            df[col] = df[col] + deltas.get('vix', 0)
        if vix_cols:
            logger.info(f"Applied VIX delta of {deltas.get('vix', 0)} to {len(vix_cols)} columns")

        # TNX (10Y Treasury) delta - add to yield columns
        yield_cols = KN.find_matching_columns(df.columns, 'treasury_10y')
        # also try alias 'tnx'
        yield_cols = list(set(yield_cols + KN.find_matching_columns(df.columns, 'tnx')))
        for col in yield_cols:
            df[col] = df[col] + deltas.get('tnx', 0)
        if yield_cols:
            logger.info(f"Applied TNX delta of {deltas.get('tnx', 0)} to {len(yield_cols)} columns")

        # Oil delta - multiply oil columns by (1 + delta%)
        oil_cols = KN.find_matching_columns(df.columns, 'oil_price')
        for col in oil_cols:
            df[col] = df[col] * (1 + deltas.get('oil', 0) / 100)
        if oil_cols:
            logger.info(f"Applied oil delta of {deltas.get('oil', 0)}% to {len(oil_cols)} columns")

        # SPY delta - add to momentum/return features
        # find momentum-like columns via aliases
        momentum_cols = []
        for candidate in ['spy_momentum', 'momentum', 'returns_1m', 'returns_1w']:
            momentum_cols.extend(KN.find_matching_columns(df.columns, candidate))
        momentum_cols = list(set(momentum_cols))
        spy_delta = deltas.get('spy', 0) / 100.0  # Convert percentage to decimal
        for col in momentum_cols:
            try:
                df[col] = df[col] + spy_delta
            except Exception:
                # if column isn't numeric, ignore
                pass
        if momentum_cols:
            logger.info(f"Applied SPY delta of {spy_delta:.2%} to {len(momentum_cols)} momentum columns")

        return df

    except Exception as e:
        logger.error(f"Error loading real features: {e}", exc_info=True)
        return None


def _generate_features_fallback(tickers, deltas):
    """Fallback feature generation using yfinance (placeholder data)."""
    try:
        import yfinance as yf
        from datetime import datetime, timedelta
        
        features_list = []
        
        for ticker in tickers:
            try:
                stock = yf.Ticker(ticker)
                info = stock.info
                
                # Basic features (simplified)
                features = {
                    'ticker': ticker,
                    'sector': info.get('sector', 'Unknown'),
                    'beta': info.get('beta', 1.0),
                    'market_cap': info.get('marketCap', 0),
                    'vix': 20.0 + deltas.get('vix', 0),
                    'tnx': 0.04 + deltas.get('tnx', 0),
                    'oil': 80.0 * (1 + deltas.get('oil', 0)),
                    'spy_return': 0.0 + deltas.get('spy', 0)
                }
                
                # Get price history for momentum
                hist = stock.history(period='3mo')
                if not hist.empty and len(hist) >= 20:
                    features['momentum_1m'] = (hist['Close'].iloc[-1] / hist['Close'].iloc[-20] - 1)
                    features['volatility'] = hist['Close'].pct_change().std() * np.sqrt(252)
                else:
                    features['momentum_1m'] = 0
                    features['volatility'] = 0.2
                
                features_list.append(features)
                
            except Exception as e:
                logger.warning(f"Error processing {ticker}: {e}")
                continue
        
        if not features_list:
            return None
        
        return pd.DataFrame(features_list)
        
    except Exception as e:
        logger.error(f"Error generating features: {e}")
        return None


def _make_predictions(model, features):
    """Make predictions using the model."""
    try:
        # If model provides an ordered feature list, use it to align columns
        feature_cols = None
        try:
            if hasattr(model, 'feature_name_'):
                feature_cols = list(model.feature_name_)
            elif hasattr(model, 'feature_names_in_'):
                feature_cols = list(model.feature_names_in_)
            elif isinstance(model, dict) and model.get('feature_columns'):
                feature_cols = list(model.get('feature_columns'))
        except Exception:
            feature_cols = None

        if feature_cols:
            # ensure all expected columns exist; fill missing with 0
            missing = [c for c in feature_cols if c not in features.columns]
            for m in missing:
                features[m] = 0
            X = features[feature_cols].fillna(0)
        else:
            # Extract numeric features only (exclude ticker, sector)
            numeric_cols = [col for col in features.columns
                           if col not in ['ticker', 'sector']]
            X = features[numeric_cols].fillna(0)

        # Make predictions
        preds = model.predict(X)

        return preds

    except Exception as e:
        logger.error(f"Error making predictions: {e}")
        return np.zeros(len(features))


def _calculate_scenario_impacts(features, baseline_preds, scenario_preds):
    """Calculate impact of scenario changes on predictions."""
    try:
        results = []
        
        for i, row in features.iterrows():
            impact = scenario_preds[i] - baseline_preds[i]
            
            results.append({
                'ticker': row['ticker'],
                'sector': row['sector'],
                'baseline': baseline_preds[i],
                'scenario': scenario_preds[i],
                'impact': impact
            })
        
        return results
        
    except Exception as e:
        logger.error(f"Error calculating impacts: {e}")
        return None


def _load_historical_presets():
    """Return a list of historical presets (label,value) pairs.
    For now, this reads from data/scenario_presets.json if available.
    """
    try:
        dash_root = getattr(SH, 'DASH_ROOT', SH.PROJECT_ROOT)
        presets_path = os.path.join(dash_root, 'data', 'scenario_presets.json')
        if os.path.exists(presets_path):
            with open(presets_path, 'r') as f:
                data = json.load(f)
            # Expecting list of {"name":..., "deltas": {...}}
            return [{'label': p.get('name', str(i)), 'value': json.dumps(p.get('deltas', {}))} 
                    for i, p in enumerate(data)]
        return []
    except Exception as e:
        logger.warning(f"Could not load historical presets: {e}")
        return []


def register_extra_callbacks(app):
    """Register additional callbacks for presets and hedging table.
    Call this from register_callbacks(app) to attach these callbacks to the Dash app.
    """

    @app.callback(
        Output('scenario-preset', 'options'),
        [Input('scenario-universe', 'value')]
    )
    def populate_presets(universe):
        # Currently presets are universe-agnostic; keep hook for future
        presets = _load_historical_presets()
        return presets

    @app.callback(
        Output('scenario-preset', 'value'),
        [Input('scenario-preset', 'options')]
    )
    def clear_preset_on_options_change(options):
        return None

    @app.callback(
        Output('scenario-hedging-table', 'children'),
        [Input('scenario-results-store', 'data')]
    )
    def update_hedging_table(results):
        """Generate a simple hedging candidates table from scenario results.
        Picks top losers and suggests hedges as top winners from uncorrelated sectors.
        """
        if not results:
            raise PreventUpdate

        try:
            df = pd.DataFrame(results)
            # Top losers
            losers = df.sort_values('impact').head(10)

            # Simple hedging: for each loser, suggest a winner in a different sector
            winners = df.sort_values('impact', ascending=False)

            hedges = []
            for _, r in losers.iterrows():
                candidate = winners[winners['sector'] != r['sector']].head(1)
                if not candidate.empty:
                    cand = candidate.iloc[0]
                    hedges.append({
                        'ticker': r['ticker'],
                        'sector': r['sector'],
                        'impact': f"{r['impact']:+.2%}",
                        'hedge_ticker': cand['ticker'],
                        'hedge_sector': cand['sector'],
                        'hedge_impact': f"{cand['impact']:+.2%}"
                    })

            if not hedges:
                return html.Div("No hedging candidates available", className='text-muted p-2')

            hedge_df = pd.DataFrame(hedges)
            return dash_table.DataTable(
                data=hedge_df.to_dict('records'),
                columns=[
                    {'name': 'Ticker', 'id': 'ticker'},
                    {'name': 'Sector', 'id': 'sector'},
                    {'name': 'Impact', 'id': 'impact'},
                    {'name': 'Hedge Ticker', 'id': 'hedge_ticker'},
                    {'name': 'Hedge Sector', 'id': 'hedge_sector'},
                    {'name': 'Hedge Impact', 'id': 'hedge_impact'}
                ],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '8px'}
            )
        except Exception as e:
            logger.error(f"Error building hedging table: {e}")
            return html.Div("Error building hedging table", className='text-danger')
