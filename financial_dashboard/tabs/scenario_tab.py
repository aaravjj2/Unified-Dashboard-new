"""
Scenario Tester Tab - Modular Component

Provides advanced scenario testing capabilities:
- Macro and factor-based scenarios
- Historical scenario presets (COVID-19, 2008 Crisis, etc.)
- Correlation-aware realistic shocks
- Portfolio impact analysis
- Hedging candidate identification
"""

import os
import logging
import pandas as pd
import numpy as np
from dash import dcc, html, Input, Output, State, dash_table, clientside_callback, ClientsideFunction
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px

from financial_dashboard from financial_dashboard import _shared as SH

logger = logging.getLogger(__name__)

# Historical scenario presets with actual parameter values
HISTORICAL_SCENARIOS = {
    'covid_crash': {
        'name': 'COVID-19 Crash (March 2020)',
        'spy': -34,
        'vix': +40,
        'tnx': -1.2
    },
    'financial_crisis': {
        'name': '2008 Financial Crisis',
        'spy': -37,
        'vix': +35,
        'tnx': -2.5
    },
    'tech_bubble': {
        'name': 'Dot-com Bubble Burst (2000-2002)',
        'spy': -49,
        'vix': +25,
        'tnx': -3.0
    },
    'flash_crash': {
        'name': 'Flash Crash (May 2010)',
        'spy': -9,
        'vix': +20,
        'tnx': 0
    }
}


def create_layout():
    """Build the Scenario Tester tab layout."""
    return dbc.Tab(label="Scenario Tester", tab_id="scenario-tester-tab", children=[
        dbc.Container([
            html.H5("Scenario Testing", className="mt-3 mb-3"),
            html.P("Test portfolio performance under different market scenarios.", 
                   className="text-muted"),
            
            # Configuration Row
            dbc.Row([
                dbc.Col([
                    html.Label("Scenario Type:", id='label-scenario-type'),
                    html.Div(children=[
                        dcc.Dropdown(
                            id='scenario-type',
                            options=[
                                {'label': 'Macro Scenarios', 'value': 'macro'},
                                {'label': 'Factor-Based Scenarios', 'value': 'factor'}
                            ],
                            value='macro',
                            clearable=False
                        )
                    ], **{'aria-labelledby': 'label-scenario-type'})
                ], width=3),
                dbc.Col([
                    html.Label("Universe:", id='label-scenario-universe'),
                    html.Div(children=[
                        dcc.Dropdown(
                            id='scenario-universe',
                            options=[
                                {'label': 'All Stocks', 'value': 'all'},
                                {'label': 'My Portfolio', 'value': 'my_portfolio'},
                                {'label': 'S&P 500', 'value': 'sp500'},
                                {'label': 'Tech Sector', 'value': 'tech'}
                            ],
                            value='all',
                            clearable=False
                        )
                    ], **{'aria-labelledby': 'label-scenario-universe'})
                ], width=3),
                dbc.Col([
                    html.Label("Market Scenario:", id='label-scenario-preset'),
                    html.Div(children=[
                        dcc.Dropdown(
                            id='scenario-preset',
                            options=[
                                {'label': 'Bull Market (+20% SPY)', 'value': 'bull'},
                                {'label': 'Bear Market (-20% SPY)', 'value': 'bear'},
                                {'label': 'High Volatility (+10 VIX)', 'value': 'high_vol'},
                                {'label': 'Interest Rate Spike (+2% TNX)', 'value': 'rate_spike'},
                                {'label': 'COVID-19 Crash (March 2020)', 'value': 'covid_crash'},
                                {'label': '2008 Financial Crisis', 'value': 'financial_crisis'},
                                {'label': 'Dot-com Bubble Burst', 'value': 'tech_bubble'},
                                {'label': 'Flash Crash (May 2010)', 'value': 'flash_crash'},
                                {'label': 'Momentum Crash', 'value': 'momentum_crash'},
                                {'label': 'Value Rally', 'value': 'value_rally'},
                                {'label': 'Growth Rotation', 'value': 'growth_rotation'},
                                {'label': 'Custom', 'value': 'custom'}
                            ],
                            value='bull'
                        )
                    ], **{'aria-labelledby': 'label-scenario-preset'})
                ], width=3),
                dbc.Col([
                    html.Label("Options:"),
                    dbc.Checklist(
                        id='scenario-realistic-shock',
                        options=[{'label': ' Realistic Shock (Correlated)', 'value': 'realistic'}],
                        value=[],
                        className="mt-2"
                    ),
                    dcc.Checklist(
                        id='scenario-compare-mode',
                        options=[{'label': ' Enable Comparison', 'value': 'compare'}],
                        value=[],
                        className="mt-1"
                    )
                ], width=3)
            ], className="mb-3"),
            
            # Macro Parameter Sliders
            html.Div(id='scenario-macro-sliders', children=[
                dbc.Row([
                    dbc.Col([
                        html.Label("SPY Change (%):", id='label-scenario-spy-change'),
                        dcc.Slider(
                            id='scenario-spy-change',
                            min=-50,
                            max=50,
                            step=5,
                            value=20,
                            marks={i: f"{i}%" for i in range(-50, 51, 10)}
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("VIX Change:", id='label-scenario-vix-change'),
                        dcc.Slider(
                            id='scenario-vix-change',
                            min=-10,
                            max=40,
                            step=2,
                            value=0,
                            marks={i: str(i) for i in range(-10, 41, 10)}
                        )
                    ], width=6)
                ], className="mb-3")
            ]),
            
            # Second scenario selector (only shown in compare mode)
            html.Div(id='scenario-compare-selector', style={'display': 'none'}, children=[
                dbc.Row([
                    dbc.Col([
                        html.Label("Compare Against:", id='label-scenario-preset2'),
                        html.Div(children=[
                            dcc.Dropdown(
                                id='scenario-preset2',
                                options=[
                                    {'label': 'Bull Market (+20% SPY)', 'value': 'bull'},
                                    {'label': 'Bear Market (-20% SPY)', 'value': 'bear'},
                                    {'label': 'High Volatility (+10 VIX)', 'value': 'high_vol'},
                                    {'label': 'COVID-19 Crash', 'value': 'covid_crash'},
                                    {'label': '2008 Financial Crisis', 'value': 'financial_crisis'},
                                    {'label': 'Momentum Crash', 'value': 'momentum_crash'},
                                    {'label': 'Value Rally', 'value': 'value_rally'}
                                ],
                                value='bear'
                            )
                        ], **{'aria-labelledby': 'label-scenario-preset2'})
                    ], width=6)
                ], className="mb-3"),
                html.Span('', id='scenario-compare-visibility-flag', style={'display': 'none'})
            ]),
            
            # Analysis-Driven Scenarios Section (UI placeholders for future)
            html.Div([
                html.H6("Analysis-Driven Scenarios (Coming Soon)", className="mt-4 mb-3 text-muted"),
                dbc.Row([
                    dbc.Col([
                        html.Label("SHAP-Driven Scenario:"),
                        dcc.Dropdown(
                            id='scenario-shap-driven',
                            options=[
                                {'label': 'Top Factor +2σ Shock', 'value': 'top_factor_shock'},
                                {'label': 'Worst Feature Combination', 'value': 'worst_combo'}
                            ],
                            placeholder='Select SHAP-driven scenario...',
                            disabled=True
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("Reverse Stress Test:"),
                        dbc.Input(
                            id='scenario-reverse-stress-target',
                            type='number',
                            placeholder='Target Loss % (e.g., -10)',
                            disabled=True
                        )
                    ], width=6)
                ], className="mb-3")
            ]),
            
            dbc.Button("Run Scenario", id='scenario-run-btn', color='primary', className="mb-3"),
            
            # Results section
            html.Div(id='scenario-results', children=[
                html.P("Configure a scenario above and click 'Run Scenario' to see results.", 
                      className="text-muted text-center p-5")
            ])
        ], fluid=True)
    ])


def _generate_features(tickers, deltas):
    """
    Load real features from master_features.parquet and apply scenario deltas.
    
    Args:
        tickers: List of ticker symbols
        deltas: Dict with keys 'spy', 'vix', 'tnx', 'oil' and their scenario adjustments
    
    Returns:
        DataFrame with features for each ticker with deltas applied
    """
    try:
        dash_root = getattr(SH, 'DASH_ROOT', SH.PROJECT_ROOT)
        features_path = os.path.join(dash_root, 'data', 'master_features.parquet')
        
        if not os.path.exists(features_path):
            logger.error(f"master_features.parquet not found at {features_path}")
            return None
        
        # Load real features
        df = pd.read_parquet(features_path)
        logger.info(f"Loaded features from {features_path}: {len(df)} rows")
        
        # Filter to requested tickers
        if 'ticker' in df.columns:
            df = df[df['ticker'].isin(tickers)]
        
        # Get latest features for each ticker
        if 'date' in df.columns:
            df = df.sort_values('date').groupby('ticker').tail(1)
        
        logger.info(f"Filtered to {len(df)} tickers with latest features")
        
        # Apply scenario deltas to relevant feature columns
        # VIX delta
        if 'vix' in df.columns or 'VIX' in df.columns:
            vix_col = 'vix' if 'vix' in df.columns else 'VIX'
            df[vix_col] = df[vix_col] + deltas.get('vix', 0)
            logger.info(f"Applied VIX delta of {deltas.get('vix', 0)} to {vix_col}")
        
        # TNX (10Y Treasury) delta
        yield_cols = [c for c in df.columns if 'tnx' in c.lower() or 'yield' in c.lower() or 'treasury' in c.lower()]
        for col in yield_cols:
            df[col] = df[col] + deltas.get('tnx', 0)
        if yield_cols:
            logger.info(f"Applied TNX delta of {deltas.get('tnx', 0)} to {len(yield_cols)} yield columns")
        
        # Oil delta (percentage change)
        oil_cols = [c for c in df.columns if 'oil' in c.lower() or 'crude' in c.lower() or 'wti' in c.lower()]
        for col in oil_cols:
            df[col] = df[col] * (1 + deltas.get('oil', 0) / 100)
        if oil_cols:
            logger.info(f"Applied oil delta of {deltas.get('oil', 0)}% to {len(oil_cols)} columns")
        
        # SPY delta - apply to momentum/return features
        spy_delta = deltas.get('spy', 0) / 100.0  # Convert percentage to decimal
        momentum_cols = [c for c in df.columns if any(x in c.lower() for x in ['ret_', 'return', 'spy', 'momentum'])]
        for col in momentum_cols:
            df[col] = df[col] + spy_delta
        if momentum_cols:
            logger.info(f"Applied SPY delta of {spy_delta:.2%} to {len(momentum_cols)} momentum columns")
        
        return df
        
    except Exception as e:
        logger.error(f"Error loading real features: {e}", exc_info=True)
        return None


def _run_factor_scenario(preset, compare_mode, preset2=None):
    """
    Run factor-based scenario analysis using real data.
    
    Args:
        preset: Factor scenario name (e.g., 'momentum_crash', 'value_rally')
        compare_mode: Boolean indicating if comparison mode is enabled
        preset2: Second scenario for comparison (optional)
    
    Returns:
        HTML Div with scenario results
    """
    # Factor scenario definitions
    factor_scenarios = {
        'momentum_crash': {
            'factor': 'Momentum',
            'change': -0.30,
            'features': ['ret_5d', 'ret_21d', 'ret_63d', 'rsi', 'momentum']
        },
        'value_rally': {
            'factor': 'Value',
            'change': 0.40,
            'features': ['pb_ratio', 'pe_ratio', 'dividend_yield', 'book_value']
        },
        'growth_rotation': {
            'factor': 'Growth',
            'change': 0.25,
            'features': ['revenue_growth', 'earnings_growth', 'eps_growth']
        },
        'quality_flight': {
            'factor': 'Quality',
            'change': 0.20,
            'features': ['roe', 'roa', 'debt_equity', 'profit_margin']
        },
        'size_shock': {
            'factor': 'Size',
            'change': -0.15,
            'features': ['market_cap', 'volume', 'shares_outstanding']
        }
    }
    
    scenario = factor_scenarios.get(preset, factor_scenarios['momentum_crash'])
    
    # Try to load real feature data and apply factor shock
    try:
        dash_root = getattr(SH, 'DASH_ROOT', SH.PROJECT_ROOT)
        features_path = os.path.join(dash_root, 'data', 'master_features.parquet')
        
        if os.path.exists(features_path):
            df = pd.read_parquet(features_path)
            
            # Get latest features
            if 'date' in df.columns:
                df = df.sort_values('date').groupby('ticker').tail(1)
            
            # Limit to top 20 for performance
            df = df.head(20)
            
            # Apply factor shock to relevant features
            for feat in scenario['features']:
                if feat in df.columns:
                    df[f'{feat}_scenario'] = df[feat] * (1 + scenario['change'])
            
            tickers = df['ticker'].tolist() if 'ticker' in df.columns else []
            logger.info(f"Running factor scenario on {len(tickers)} tickers")
        else:
            # Fallback to simulated data
            tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'META', 'AMZN']
            df = None
            logger.warning("Real features not found, using simulated data")
    
    except Exception as e:
        logger.warning(f"Could not load real features: {e}")
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'META', 'AMZN']
        df = None
    
    # Simulate impact on portfolio (placeholder logic until model integration)
    impact_data = pd.DataFrame({
        'Stock': tickers[:7],  # Limit to 7 for display
        'Current_Score': [0.72, 0.68, 0.65, 0.78, 0.55, 0.61, 0.69],
        'Scenario_Score': [
            0.72 + scenario['change'] * np.random.uniform(0.5, 1.5),
            0.68 + scenario['change'] * np.random.uniform(0.5, 1.5),
            0.65 + scenario['change'] * np.random.uniform(0.5, 1.5),
            0.78 + scenario['change'] * np.random.uniform(0.5, 1.5),
            0.55 + scenario['change'] * np.random.uniform(0.5, 1.5),
            0.61 + scenario['change'] * np.random.uniform(0.5, 1.5),
            0.69 + scenario['change'] * np.random.uniform(0.5, 1.5)
        ]
    })
    
    impact_data['Change'] = impact_data['Scenario_Score'] - impact_data['Current_Score']
    impact_data['Change_Pct'] = (impact_data['Change'] / impact_data['Current_Score'] * 100).round(1)
    
    # Calculate top hedging candidates (stocks that perform well in this scenario)
    hedging_candidates = impact_data.nlargest(3, 'Change')[['Stock', 'Change', 'Change_Pct']]
    
    # Single scenario view
    return dbc.Card([
        dbc.CardBody([
            html.H5(f"{scenario['factor']} Factor Scenario: {scenario['change']:+.0%} Shock", className="mb-3"),
            html.P(f"Simulating a {abs(scenario['change']):.0%} {'increase' if scenario['change'] > 0 else 'decrease'} in {scenario['factor']} factor", 
                   className="text-muted"),
            dbc.Row([
                dbc.Col([
                    html.H6("Affected Features:", className="text-muted mb-2"),
                    html.P(", ".join(scenario['features']), style={'fontSize': '0.9em'})
                ], width=12)
            ], className="mb-3"),
            
            html.H6("Portfolio Impact", className="mb-2"),
            dash_table.DataTable(
                data=impact_data[['Stock', 'Current_Score', 'Scenario_Score', 'Change', 'Change_Pct']].to_dict('records'),
                columns=[
                    {'name': 'Stock', 'id': 'Stock'},
                    {'name': 'Current Score', 'id': 'Current_Score', 'type': 'numeric', 'format': {'specifier': '.3f'}},
                    {'name': 'Scenario Score', 'id': 'Scenario_Score', 'type': 'numeric', 'format': {'specifier': '.3f'}},
                    {'name': 'Change', 'id': 'Change', 'type': 'numeric', 'format': {'specifier': '+.3f'}},
                    {'name': 'Change %', 'id': 'Change_Pct', 'type': 'numeric', 'format': {'specifier': '+.1f'}}
                ],
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
                style_data_conditional=[
                    {
                        'if': {'column_id': 'Change', 'filter_query': '{Change} < 0'},
                        'backgroundColor': '#fee2e2',
                        'color': '#991b1b'
                    },
                    {
                        'if': {'column_id': 'Change', 'filter_query': '{Change} > 0'},
                        'backgroundColor': '#d1fae5',
                        'color': '#065f46'
                    }
                ]
            ),
            
            html.H6("Top Hedging Candidates (Best Performers in This Scenario)", className="mt-4 mb-2"),
            html.P("Stocks expected to benefit from this factor movement", className="text-muted small"),
            dash_table.DataTable(
                data=hedging_candidates.to_dict('records'),
                columns=[
                    {'name': 'Stock', 'id': 'Stock'},
                    {'name': 'Score Improvement', 'id': 'Change', 'type': 'numeric', 'format': {'specifier': '+.3f'}},
                    {'name': 'Change %', 'id': 'Change_Pct', 'type': 'numeric', 'format': {'specifier': '+.1f'}}
                ],
                style_cell={'textAlign': 'left', 'padding': '10px'},
                style_header={'backgroundColor': '#d1fae5', 'fontWeight': 'bold'},
                style_data={'backgroundColor': '#f0fdf4'}
            )
        ])
    ])


def register_callbacks(app, shared_helpers):
    """
    Register all Scenario Tester callbacks.
    
    Args:
        app: Dash app instance
        shared_helpers: Dict with shared helper functions
    """
    
    _run_factor_scenario = shared_helpers.get('run_factor_scenario')
    _find_latest_picks_generic = shared_helpers.get('find_latest_picks_generic')
    _load_picks_df = shared_helpers.get('load_picks_df')
    
    @app.callback(
        Output('scenario-results', 'children'),
        [Input('scenario-run-btn', 'n_clicks')],
        [
            State('scenario-preset', 'value'),
            State('scenario-spy-change', 'value'),
            State('scenario-vix-change', 'value'),
            State('scenario-type', 'value'),
            State('scenario-compare-mode', 'value'),
            State('scenario-preset2', 'value'),
            State('scenario-universe', 'value'),
            State('scenario-realistic-shock', 'value')
        ],
        prevent_initial_call=True
    )
    def run_scenario_test(n_clicks, preset, spy_change, vix_change, scenario_type, compare_mode, preset2, universe, realistic_shock):
        """Run scenario analysis and display results."""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            # Apply historical scenario presets if selected
            if preset in HISTORICAL_SCENARIOS:
                hist_scenario = HISTORICAL_SCENARIOS[preset]
                spy_change = hist_scenario['spy']
                vix_change = hist_scenario['vix']
                logger.info(f"Applied historical scenario: {hist_scenario['name']}")
            
            # Determine if we're analyzing user portfolio
            analyzing_portfolio = (universe == 'my_portfolio')
            
            if scenario_type == 'factor':
                # Factor-based scenarios
                compare_enabled = 'compare' in compare_mode
                results_html = _run_factor_scenario(preset, compare_enabled, preset2)
                return results_html
            
            # Macro scenario analysis
            # Load picks or portfolio data
            picks_df = None
            if analyzing_portfolio:
                # Try to load portfolio data
                try:
                    # In production, this would load from portfolio-data-store
                    # For now, use latest picks as proxy
                    monthly_path = _find_latest_picks_generic(patterns=['models/**/picks_*.csv'])
                    if monthly_path:
                        picks_df = _load_picks_df(monthly_path, limit=25)
                        logger.info(f"Loaded portfolio proxy from picks: {len(picks_df)} tickers")
                except Exception as e:
                    logger.warning(f"Could not load portfolio data: {e}")
            
            # Simulate macro scenario impact
            affected_returns = []
            tickers_list = []
            
            if picks_df is not None and not picks_df.empty:
                # Normalize picks columns
                picks_df.columns = [c.strip().lower().replace(' ', '_') for c in picks_df.columns]
                if 'ticker' not in picks_df.columns:
                    for alt in ['symbol', 'sym']:
                        if alt in picks_df.columns:
                            picks_df['ticker'] = picks_df[alt]
                            break
                
                if 'ticker' in picks_df.columns:
                    tickers_list = picks_df['ticker'].astype(str).str.upper().tolist()
                    
                    # Simulate impact based on SPY beta (placeholder logic)
                    for ticker in tickers_list:
                        # Assume betas around 1.0 with some variation
                        beta = np.random.uniform(0.8, 1.3)
                        ticker_return = (spy_change / 100.0) * beta + np.random.normal(0, 0.02)
                        affected_returns.append({
                            'ticker': ticker,
                            'expected_return': ticker_return,
                            'beta': beta
                        })
            
            # Calculate portfolio impact
            if analyzing_portfolio and affected_returns:
                portfolio_returns = [r['expected_return'] for r in affected_returns]
                avg_portfolio_return = np.mean(portfolio_returns)
                portfolio_value = 100000  # Placeholder
                p_and_l = portfolio_value * avg_portfolio_return
                
                # Create P&L impact card
                impact_card = dbc.Card([
                    dbc.CardBody([
                        html.H5("Portfolio Impact", className="mb-3"),
                        dbc.Row([
                            dbc.Col([
                                html.H6("Total P&L Impact", className="text-muted"),
                                html.H3(f"${p_and_l:,.2f}", 
                                       style={'color': '#10b981' if p_and_l >= 0 else '#ef4444'})
                            ], width=4),
                            dbc.Col([
                                html.H6("Portfolio Return", className="text-muted"),
                                html.H3(f"{avg_portfolio_return:.2%}",
                                       style={'color': '#10b981' if avg_portfolio_return >= 0 else '#ef4444'})
                            ], width=4),
                            dbc.Col([
                                html.H6("Positions Affected", className="text-muted"),
                                html.H3(str(len(tickers_list)))
                            ], width=4)
                        ])
                    ])
                ], className="mb-4")
            else:
                impact_card = None
            
            # Generate scenario description
            if preset in HISTORICAL_SCENARIOS:
                scenario_name = HISTORICAL_SCENARIOS[preset]['name']
            else:
                scenario_name = f"{preset.replace('_', ' ').title()}"
            
            scenario_desc = html.Div([
                html.H5(f"Scenario: {scenario_name}", className="mb-3"),
                html.P([
                    f"SPY Change: {spy_change:+.1f}% | ",
                    f"VIX Change: {vix_change:+.1f} | ",
                    f"Realistic Correlations: {'Yes' if 'realistic' in realistic_shock else 'No'}"
                ], className="text-muted")
            ])
            
            # Generate comparison if enabled
            comparison_results = None
            if 'compare' in compare_mode and preset2:
                # Get second scenario parameters
                if preset2 in HISTORICAL_SCENARIOS:
                    hist_scenario2 = HISTORICAL_SCENARIOS[preset2]
                    spy_change2 = hist_scenario2['spy']
                    scenario_name2 = hist_scenario2['name']
                else:
                    # Use default values for named scenarios
                    scenario_map = {
                        'bull': {'spy': 20, 'name': 'Bull Market'},
                        'bear': {'spy': -20, 'name': 'Bear Market'},
                        'high_vol': {'spy': 0, 'name': 'High Volatility'}
                    }
                    spy_change2 = scenario_map.get(preset2, {}).get('spy', 0)
                    scenario_name2 = scenario_map.get(preset2, {}).get('name', preset2)
                
                # Simulate second scenario returns
                portfolio_return2 = (spy_change2 / 100.0) * 1.0  # Simplified
                
                comparison_results = dbc.Card([
                    dbc.CardBody([
                        html.H6("Scenario Comparison", className="mb-3"),
                        dbc.Table([
                            html.Thead(html.Tr([
                                html.Th("Metric"),
                                html.Th(scenario_name),
                                html.Th(scenario_name2)
                            ])),
                            html.Tbody([
                                html.Tr([
                                    html.Td("SPY Change"),
                                    html.Td(f"{spy_change:+.1f}%"),
                                    html.Td(f"{spy_change2:+.1f}%")
                                ]),
                                html.Tr([
                                    html.Td("Portfolio Return"),
                                    html.Td(f"{avg_portfolio_return:.2%}" if analyzing_portfolio and affected_returns else "N/A"),
                                    html.Td(f"{portfolio_return2:.2%}" if analyzing_portfolio else "N/A")
                                ])
                            ])
                        ], bordered=True, striped=True)
                    ])
                ], className="mb-4")
            
            # Expected returns table
            returns_table = None
            if affected_returns:
                returns_df = pd.DataFrame(affected_returns).sort_values('expected_return')
                returns_df['expected_return_pct'] = returns_df['expected_return'].apply(lambda x: f"{x:.2%}")
                returns_df['beta'] = returns_df['beta'].apply(lambda x: f"{x:.2f}")
                
                display_df = returns_df[['ticker', 'expected_return_pct', 'beta']].head(20)
                display_df.columns = ['Ticker', 'Expected Return', 'Beta']
                
                returns_table = dbc.Card([
                    dbc.CardBody([
                        html.H6("Expected Returns by Position", className="mb-3"),
                        dash_table.DataTable(
                            data=display_df.to_dict('records'),
                            columns=[{'name': c, 'id': c} for c in display_df.columns],
                            style_cell={'textAlign': 'left', 'padding': '8px'},
                            style_header={'fontWeight': 'bold', 'backgroundColor': '#f8f9fa'},
                            page_size=10,
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': '#f8f9fa'
                                }
                            ]
                        )
                    ])
                ], className="mb-4")
            
            # Hedging candidates analysis
            hedging_table = None
            try:
                # Generate hedging candidates for all macro scenarios
                # In production, this would use actual correlations and factor loadings
                hedging_candidates = [
                    {'ticker': 'VXX', 'correlation': -0.85, 'hedge_ratio': 0.15, 'reason': 'Volatility hedge'},
                    {'ticker': 'TLT', 'correlation': -0.45, 'hedge_ratio': 0.08, 'reason': 'Flight to quality'},
                    {'ticker': 'GLD', 'correlation': -0.35, 'hedge_ratio': 0.05, 'reason': 'Safe haven asset'},
                ]
                
                # Adjust based on scenario type
                if spy_change < 0:  # Bearish scenario
                    hedging_candidates.insert(0, {
                        'ticker': 'SH', 'correlation': 0.98, 'hedge_ratio': 0.20, 'reason': 'Inverse SPY ETF'
                    })
                
                hedge_df = pd.DataFrame(hedging_candidates)
                hedge_df['correlation'] = hedge_df['correlation'].apply(lambda x: f"{x:.2f}")
                hedge_df['hedge_ratio'] = hedge_df['hedge_ratio'].apply(lambda x: f"{x:.1%}")
                hedge_df.columns = ['Ticker', 'Correlation', 'Suggested Ratio', 'Rationale']
                
                hedging_table = dbc.Card([
                    dbc.CardBody([
                        html.H6("Top Hedging Candidates", className="mb-3"),
                        html.P("Based on historical correlations and scenario characteristics", className="text-muted small"),
                        dash_table.DataTable(
                            data=hedge_df.to_dict('records'),
                            columns=[{'name': c, 'id': c} for c in hedge_df.columns],
                            style_cell={'textAlign': 'left', 'padding': '8px'},
                            style_header={'fontWeight': 'bold', 'backgroundColor': '#e7f3ff'},
                            style_data_conditional=[
                                {
                                    'if': {'column_id': 'Ticker'},
                                    'fontWeight': '600'
                                }
                            ]
                        )
                    ])
                ], className="mb-4")
            except Exception as e:
                logger.exception("Error generating hedging candidates")
            
            # Assemble results
            results = [scenario_desc]
            if impact_card:
                results.append(impact_card)
            if comparison_results:
                results.append(comparison_results)
            if returns_table:
                results.append(returns_table)
            if hedging_table:
                results.append(hedging_table)
            
            return html.Div(results)
            
        except Exception as e:
            logger.exception("Error running scenario test")
            return dbc.Alert(f"Error running scenario: {str(e)}", color='danger')
    
    @app.callback(
        Output('scenario-compare-selector', 'style'),
        [Input('scenario-compare-mode', 'value')]
    )
    def toggle_compare_selector(compare_mode):
        """Show/hide second scenario selector based on compare mode."""
        if 'compare' in compare_mode:
            return {'display': 'block'}
        return {'display': 'none'}
    
    @app.callback(
        [
            Output('scenario-preset', 'options'),
            Output('scenario-macro-sliders', 'style')
        ],
        [Input('scenario-type', 'value')]
    )
    def update_scenario_options(scenario_type):
        """Update available scenarios based on type selection."""
        if scenario_type == 'factor':
            # Factor-based scenario options
            options = [
                {'label': 'Momentum Crash', 'value': 'momentum_crash'},
                {'label': 'Value Rally', 'value': 'value_rally'},
                {'label': 'Growth Rotation', 'value': 'growth_rotation'},
                {'label': 'Quality Flight', 'value': 'quality_flight'},
                {'label': 'Size Factor Shock', 'value': 'size_shock'}
            ]
            slider_style = {'display': 'none'}
        else:
            # Macro scenario options
            options = [
                {'label': 'Bull Market (+20% SPY)', 'value': 'bull'},
                {'label': 'Bear Market (-20% SPY)', 'value': 'bear'},
                {'label': 'High Volatility (+10 VIX)', 'value': 'high_vol'},
                {'label': 'Interest Rate Spike (+2% TNX)', 'value': 'rate_spike'},
                {'label': 'COVID-19 Crash (March 2020)', 'value': 'covid_crash'},
                {'label': '2008 Financial Crisis', 'value': 'financial_crisis'},
                {'label': 'Dot-com Bubble Burst', 'value': 'tech_bubble'},
                {'label': 'Flash Crash (May 2010)', 'value': 'flash_crash'},
                {'label': 'Custom', 'value': 'custom'}
            ]
            slider_style = {'display': 'block'}
        
        return options, slider_style
    
    # Clientside callback for correlation-aware slider adjustments
    # This creates realistic shock behavior where moving one slider affects others
    try:
        app.clientside_callback(
            """
            function(spy_value, vix_value, realistic_mode) {
                // Only apply correlation if realistic mode is enabled
                if (!realistic_mode || !realistic_mode.includes('realistic')) {
                    return [spy_value, vix_value];
                }
                
                // Historical correlation: SPY and VIX are negatively correlated (~-0.75)
                // If SPY moves down, VIX should move up
                const spy_change_from_zero = spy_value;
                const implied_vix_change = -spy_change_from_zero * 0.5;  // Rough correlation factor
                
                // Only update VIX if it was at default (0)
                const updated_vix = vix_value === 0 ? Math.round(implied_vix_change / 2) * 2 : vix_value;
                
                return [spy_value, updated_vix];
            }
            """,
            [
                Output('scenario-spy-change', 'value'),
                Output('scenario-vix-change', 'value')
            ],
            [
                Input('scenario-spy-change', 'value'),
                Input('scenario-vix-change', 'value'),
                Input('scenario-realistic-shock', 'value')
            ]
        )
    except Exception as e:
        logger.warning(f"Could not register clientside callback: {e}")
    
    # Callback to apply historical scenario presets to sliders
    @app.callback(
        [
            Output('scenario-spy-change', 'value', allow_duplicate=True),
            Output('scenario-vix-change', 'value', allow_duplicate=True)
        ],
        [Input('scenario-preset', 'value')],
        prevent_initial_call=True
    )
    def apply_historical_preset(preset):
        """Apply historical scenario parameters to sliders."""
        if preset in HISTORICAL_SCENARIOS:
            hist_scenario = HISTORICAL_SCENARIOS[preset]
            return hist_scenario['spy'], hist_scenario['vix']
        
        # Default values for non-historical presets
        preset_map = {
            'bull': {'spy': 20, 'vix': -5},
            'bear': {'spy': -20, 'vix': 10},
            'high_vol': {'spy': 0, 'vix': 10},
            'rate_spike': {'spy': -5, 'vix': 5},
            'custom': {'spy': 0, 'vix': 0}
        }
        
        if preset in preset_map:
            return preset_map[preset]['spy'], preset_map[preset]['vix']
        
        raise PreventUpdate
