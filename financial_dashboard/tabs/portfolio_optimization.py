"""
Portfolio Optimization Tab - Advanced Portfolio Optimization
Part of refactored Portfolio Tracker module

Integrates with PortfolioOptimizer from utils/portfolio.py
"""

import os
import logging
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dash import dcc, html, Input, Output, State, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go

logger = logging.getLogger(__name__)


def layout():
    """Build optimization tab layout."""
    return dbc.Container([
        html.H5("Portfolio Optimization", className="mt-3 mb-3"),
        dbc.Card([
            dbc.CardBody([
                html.H6("Configuration", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.Label("Current Holdings (comma-separated):"),
                        dcc.Input(
                            id='opt-tickers-input',
                            type='text',
                            placeholder='AAPL,MSFT,GOOGL,TSLA',
                            className='form-control mb-2',
                            style={'width': '100%'}
                        )
                    ], width=6),
                    dbc.Col([
                        html.Label("Optimization Strategy:"),
                        dcc.Dropdown(
                            id='opt-strategy',
                            options=[
                                {'label': 'Maximize Sharpe Ratio', 'value': 'max_sharpe'},
                                {'label': 'Minimize Volatility (Risk Parity)', 'value': 'min_volatility'},
                                {'label': 'Maximize Return', 'value': 'max_return'},
                                {'label': 'Equal Weight', 'value': 'equal_weight'}
                            ],
                            value='max_sharpe',
                            className='mb-2'
                        )
                    ], width=6)
                ], className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        html.Label("Historical Data Period (days):"),
                        dcc.Slider(
                            id='opt-period-slider',
                            min=30,
                            max=730,
                            step=30,
                            value=365,
                            marks={30: '1M', 180: '6M', 365: '1Y', 730: '2Y'},
                            tooltip={"placement": "bottom", "always_visible": True}
                        )
                    ], width=6),
                    dbc.Col([
                        dbc.Button(
                            "Optimize Portfolio",
                            id='opt-run-btn',
                            color='primary',
                            className='mt-4',
                            size='lg',
                            style={'width': '100%'}
                        )
                    ], width=6)
                ])
            ])
        ], className="mb-4"),
        
        html.Div(id='opt-results-container')
    ], fluid=True)


def register_callbacks(app):
    """Register callbacks for optimization tab."""
    
    @app.callback(
        Output('opt-tickers-input', 'value'),
        [Input('portfolio-data-store', 'data')]
    )
    def pre_populate_tickers(portfolio_data):
        """FIX: Pre-populate ticker input with current portfolio holdings."""
        if portfolio_data and portfolio_data.get('positions'):
            tickers = [pos['symbol'] for pos in portfolio_data['positions']]
            return ','.join(tickers)
        raise PreventUpdate
    
    @app.callback(
        Output('opt-results-container', 'children'),
        [Input('opt-run-btn', 'n_clicks')],
        [State('opt-tickers-input', 'value'),
         State('opt-strategy', 'value'),
         State('opt-period-slider', 'value'),
         State('portfolio-data-store', 'data')]
    )
    def run_optimization(n_clicks, tickers_input, strategy, period_days, portfolio_data):
        """Run portfolio optimization and display results."""
        if not n_clicks or n_clicks == 0:
            return html.P("Configure parameters above and click 'Optimize Portfolio' to begin.", className="text-muted")
        
        # Parse tickers
        if not tickers_input:
            # Try to use current portfolio holdings
            if portfolio_data and portfolio_data.get('positions'):
                tickers = [pos['symbol'] for pos in portfolio_data['positions']]
            else:
                return dbc.Alert("Please enter tickers or have an active portfolio.", color="warning")
        else:
            tickers = [t.strip().upper() for t in tickers_input.split(',') if t.strip()]
        
        if len(tickers) < 2:
            return dbc.Alert("Please provide at least 2 tickers for optimization.", color="warning")
        
        try:
            from utils.portfolio import PortfolioOptimizer
            
            # Initialize optimizer
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days)
            
            logger.info(f"Optimizing portfolio: {tickers} with strategy '{strategy}'")
            
            optimizer = PortfolioOptimizer(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
                risk_free_rate=0.04
            )
            
            # Run optimization based on strategy
            if strategy == 'max_sharpe':
                result = optimizer.maximize_sharpe()
            elif strategy == 'min_volatility':
                result = optimizer.minimize_volatility()
            elif strategy == 'max_return':
                result = optimizer.maximize_return()
            elif strategy == 'equal_weight':
                result = optimizer.equal_weight()
            else:
                return dbc.Alert(f"Unknown strategy: {strategy}", color="danger")
            
            if not result or 'weights' not in result:
                # FIX: More descriptive error message
                return dbc.Alert([
                    html.H6("Optimization Failed", className="alert-heading"),
                    html.P("Unable to compute optimal weights. Possible causes:"),
                    html.Ul([
                        html.Li("Insufficient historical data (try increasing time period)"),
                        html.Li("Data download errors (check network/yfinance)"),
                        html.Li("Singular covariance matrix (try different tickers)")
                    ]),
                    html.P("Check application logs for detailed error messages.", className="mb-0 small")
                ], color="danger")
            
            # Extract results
            weights_dict = result['weights']  # This is a dict: {'AAPL': 0.25, ...}
            expected_return = result.get('expected_return', 0)
            volatility = result.get('volatility', 0)
            sharpe_ratio = result.get('sharpe_ratio', 0)
            opt_status = result.get('optimization_status', 'unknown')
            
            # Determine alert type and message based on optimization status
            if opt_status.startswith('fallback'):
                alert_color = "warning"
                status_icon = "⚠️"
                status_msg = html.Div([
                    html.H6([status_icon, " Optimization Used Fallback Strategy"], className="alert-heading"),
                    html.P([
                        "The optimizer encountered issues and fell back to equal weighting. ",
                        "This typically happens when:"
                    ]),
                    html.Ul([
                        html.Li("Historical data is too limited (< 30 days)"),
                        html.Li("Covariance matrix is singular or near-singular"),
                        html.Li("Optimization convergence failed")
                    ]),
                    html.P([
                        html.Strong("Recommendation: "),
                        "Try increasing the historical period or selecting different tickers."
                    ], className="mb-0")
                ])
            elif opt_status == 'success_with_shrinkage':
                alert_color = "info"
                status_icon = "ℹ️"
                status_msg = html.Div([
                    html.H6([status_icon, " Optimization Successful (Regularized)"], className="alert-heading"),
                    html.P([
                        "Applied Ledoit-Wolf shrinkage to regularize covariance matrix. ",
                        "This improves stability when correlations are noisy or data is limited."
                    ], className="mb-0")
                ])
            else:
                alert_color = "success"
                status_icon = "✓"
                status_msg = html.Div([
                    html.H6([status_icon, " Optimization Successful"], className="alert-heading"),
                    html.P("Portfolio weights computed using standard mean-variance optimization.", className="mb-0")
                ])
            
            # Update tickers list to match optimized tickers (in case some were dropped)
            optimized_tickers = list(weights_dict.keys())
            
            # Create weights DataFrame with NUMERIC values only (no formatting yet)
            weights_numeric = [float(weights_dict[ticker] * 100) for ticker in optimized_tickers]
            weights_df = pd.DataFrame({
                'Ticker': optimized_tickers,
                'Optimal Weight (%)': weights_numeric,
                'Allocation ($)': [0.0] * len(optimized_tickers)  # Will be calculated if portfolio value is known
            })
            
            # CRITICAL: Ensure weight column is numeric dtype
            weights_df['Optimal Weight (%)'] = pd.to_numeric(weights_df['Optimal Weight (%)'], errors='coerce')
            weights_df['Allocation ($)'] = pd.to_numeric(weights_df['Allocation ($)'], errors='coerce')
            
            # If we have current portfolio value, calculate dollar allocations (still numeric)
            if portfolio_data and portfolio_data.get('account'):
                portfolio_value = portfolio_data['account']['portfolio_value']
                
                # FIX: Robust portfolio_value parsing with comprehensive error handling
                try:
                    if isinstance(portfolio_value, str):
                        # Remove currency symbols, commas, whitespace
                        cleaned_value = portfolio_value.strip().replace('$', '').replace(',', '').replace(' ', '')
                        portfolio_value = float(cleaned_value)
                    elif isinstance(portfolio_value, (int, float)):
                        portfolio_value = float(portfolio_value)
                    else:
                        # Handle unexpected types (list, dict, etc.)
                        logger.warning(f"Unexpected portfolio_value type: {type(portfolio_value)}, attempting str conversion")
                        portfolio_value = float(str(portfolio_value).replace('$', '').replace(',', ''))
                    
                    # Validate the parsed value
                    if portfolio_value <= 0 or not np.isfinite(portfolio_value):
                        raise ValueError(f"Invalid portfolio value: {portfolio_value}")
                    
                except (ValueError, TypeError, AttributeError) as e:
                    logger.error(f"Failed to parse portfolio_value: {portfolio_data['account']['portfolio_value']} - {e}")
                    # Fallback: drop Allocation column if parsing fails
                    portfolio_value = None
                
                # Calculate allocations - explicitly ensure numeric types
                if portfolio_value is not None:
                    # Double-check column is numeric before division
                    weights_col = pd.to_numeric(weights_df['Optimal Weight (%)'], errors='coerce')
                    weights_df['Allocation ($)'] = weights_col / 100.0 * float(portfolio_value)
                else:
                    # If parsing failed, drop the allocation column
                    logger.warning("Dropping Allocation ($) column due to invalid portfolio value")
                    weights_df = weights_df.drop('Allocation ($)', axis=1, errors='ignore')
            
            # NOW format everything at the END (convert numbers to display strings)
            # Create formatted version for display
            weights_display = weights_df.copy()
            weights_display['Optimal Weight (%)'] = weights_df['Optimal Weight (%)'].apply(lambda x: f"{x:.2f}%")
            if 'Allocation ($)' in weights_display.columns and portfolio_data and portfolio_data.get('account'):
                weights_display['Allocation ($)'] = weights_df['Allocation ($)'].apply(lambda x: f"${x:,.2f}")
            else:
                weights_display = weights_display.drop('Allocation ($)', axis=1, errors='ignore')
            
            # Create visualization
            fig_weights = go.Figure(data=[
                go.Bar(
                    x=optimized_tickers,
                    y=[weights_dict[t] * 100 for t in optimized_tickers],
                    marker_color='steelblue',
                    text=[f"{weights_dict[t]*100:.1f}%" for t in optimized_tickers],
                    textposition='auto'
                )
            ])
            fig_weights.update_layout(
                title=f'Optimal Portfolio Weights ({strategy.replace("_", " ").title()})',
                xaxis_title='Ticker',
                yaxis_title='Weight (%)',
                template='plotly_white',
                height=400
            )
            
            # Create efficient frontier if max_sharpe or min_volatility
            if strategy in ['max_sharpe', 'min_volatility']:
                try:
                    frontier_points = optimizer.efficient_frontier(num_points=50)
                    if frontier_points:
                        fig_frontier = go.Figure()
                        fig_frontier.add_trace(go.Scatter(
                            x=frontier_points['volatility'],
                            y=frontier_points['return'],
                            mode='lines+markers',
                            name='Efficient Frontier',
                            marker=dict(size=4, color='lightblue'),
                            line=dict(color='steelblue', width=2)
                        ))
                        
                        # Add optimal point
                        fig_frontier.add_trace(go.Scatter(
                            x=[volatility],
                            y=[expected_return],
                            mode='markers',
                            name='Optimal Portfolio',
                            marker=dict(size=15, color='red', symbol='star')
                        ))
                        
                        fig_frontier.update_layout(
                            title='Efficient Frontier',
                            xaxis_title='Volatility (Risk)',
                            yaxis_title='Expected Return',
                            template='plotly_white',
                            height=400
                        )
                    else:
                        fig_frontier = None
                except Exception as e:
                    logger.warning(f"Could not generate efficient frontier: {e}")
                    fig_frontier = None
            else:
                fig_frontier = None
            
            # Summary card
            summary = dbc.Card([
                dbc.CardBody([
                    html.H5("Optimization Results", className="mb-3"),
                    html.P([
                        html.Strong("Strategy: "),
                        strategy.replace('_', ' ').title()
                    ]),
                    html.P([
                        html.Strong("Expected Annual Return: "),
                        f"{expected_return * 100:.2f}%",
                        html.Span(" (annualized)", className="text-muted small")
                    ]),
                    html.P([
                        html.Strong("Expected Volatility: "),
                        f"{volatility * 100:.2f}%",
                        html.Span(" (annualized std dev)", className="text-muted small")
                    ]),
                    html.P([
                        html.Strong("Sharpe Ratio: "),
                        f"{sharpe_ratio:.2f}",
                        html.Span(" (return/risk)", className="text-muted small")
                    ]),
                    html.P([
                        html.Strong("Number of Assets: "),
                        f"{len(tickers)}"
                    ], className="mb-0")
                ])
            ], className="mb-3", color="success", outline=True)
            
            # Build results layout
            results = html.Div([
                # Status message (success, warning, or info based on optimization)
                dbc.Alert(status_msg, color=alert_color, className="mb-3"),
                
                summary,
                dbc.Row([
                    dbc.Col([
                        dcc.Graph(figure=fig_weights)
                    ], width=6),
                    dbc.Col([
                        dcc.Graph(figure=fig_frontier) if fig_frontier else html.P("Efficient frontier not available for this strategy.", className="text-muted mt-5")
                    ], width=6)
                ], className="mb-4"),
                dbc.Row([
                    dbc.Col([
                        html.H6("Optimal Weights Table", className="mb-3"),
                        dash_table.DataTable(
                            data=weights_display.to_dict('records'),
                            columns=[{'name': c, 'id': c} for c in weights_display.columns],
                            style_table={'overflowX': 'auto'},
                            style_cell={'textAlign': 'left', 'padding': '10px'},
                            style_header={'backgroundColor': '#e7f3ff', 'fontWeight': 'bold'},
                            style_data_conditional=[
                                {
                                    'if': {'row_index': 'odd'},
                                    'backgroundColor': 'rgb(248, 248, 248)'
                                }
                            ]
                        )
                    ], width=12)
                ])
            ])
            
            return results
            
        except ImportError as e:
            logger.error(f"Error importing PortfolioOptimizer: {e}")
            return dbc.Alert([
                html.H6("Import Error", className="alert-heading"),
                html.P("Portfolio optimization module not available."),
                html.P(f"Details: {str(e)}", className="small text-muted")
            ], color="danger")
        except ValueError as e:
            # FIX: Handle specific math/data errors
            logger.error(f"ValueError in optimization: {e}")
            return dbc.Alert([
                html.H6("Data Error", className="alert-heading"),
                html.P("Invalid data encountered during optimization."),
                html.P(f"Details: {str(e)}", className="small"),
                html.P("Try selecting different tickers or increasing the historical period.", className="mb-0")
            ], color="warning")
        except Exception as e:
            # FIX: Catch-all with more details
            logger.error(f"Error running optimization: {e}", exc_info=True)
            return dbc.Alert([
                html.H6("Optimization Error", className="alert-heading"),
                html.P(f"An unexpected error occurred: {str(e)}"),
                html.P("Check server logs for full traceback.", className="mb-0 small text-muted")
            ], color="danger")
