"""
Phase 4: Advanced Portfolio Tab
Provides portfolio optimization, risk analysis, and backtesting capabilities
"""

from dash import dcc, html, Input, Output, State, dash_table
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Import portfolio utilities
try:
    from financial_dashboard.utils.portfolio import PortfolioOptimizer, RiskMetrics, Backtester, calculate_portfolio_metrics
except ImportError:
    logger.warning("Could not import utils.portfolio")
    PortfolioOptimizer = None


def layout():
    """Build Phase 4 Advanced Portfolio layout."""
    return html.Div([
        html.H3('Phase 4: Advanced Portfolio Analytics', style={'marginBottom': '20px'}),
        
        # Tabs for different sections
        dcc.Tabs(id='phase4-tabs', value='optimization', children=[
            dcc.Tab(label='Portfolio Optimization', value='optimization', children=[
                html.Div([
                    html.H4('Portfolio Optimization', style={'marginTop': '20px'}),
                    html.P('Optimize your portfolio using various strategies to maximize returns or minimize risk.'),
                    
                    # Input section
                    dbc.Row([
                        dbc.Col([
                            html.Label('Tickers (comma-separated)'),
                            dcc.Input(
                                id='opt-tickers',
                                type='text',
                                value='AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSLA,JPM,V,JNJ',
                                style={'width': '100%', 'padding': '8px'}
                            )
                        ], width=8),
                        dbc.Col([
                            html.Label('Optimization Method'),
                            dcc.Dropdown(
                                id='opt-method',
                                options=[
                                    {'label': 'Maximum Sharpe Ratio', 'value': 'sharpe'},
                                    {'label': 'Minimum Variance', 'value': 'min_var'},
                                    {'label': 'Risk Parity', 'value': 'risk_parity'}
                                ],
                                value='sharpe'
                            )
                        ], width=4)
                    ], style={'marginBottom': '15px'}),
                    
                    html.Button('Optimize Portfolio', id='opt-run-btn', n_clicks=0, 
                               style={'marginTop': '10px', 'padding': '10px 20px'}),
                    
                    # Status message
                    dbc.Alert(id='opt-status', is_open=False, duration=4000, style={'marginTop': '15px'}),
                    
                    # Results section
                    html.Div(id='opt-results', style={'marginTop': '20px'})
                ], style={'padding': '20px'})
            ]),
            
            dcc.Tab(label='Risk Analysis', value='risk', children=[
                html.Div([
                    html.H4('Portfolio Risk Analysis', style={'marginTop': '20px'}),
                    html.P('Analyze risk metrics for your portfolio including VaR, CVaR, and drawdowns.'),
                    
                    # Input section
                    dbc.Row([
                        dbc.Col([
                            html.Label('Tickers (comma-separated)'),
                            dcc.Input(
                                id='risk-tickers',
                                type='text',
                                value='AAPL,MSFT,GOOGL,AMZN,NVDA',
                                style={'width': '100%', 'padding': '8px'}
                            )
                        ], width=6),
                        dbc.Col([
                            html.Label('Analysis Period'),
                            dcc.Dropdown(
                                id='risk-period',
                                options=[
                                    {'label': '3 Months', 'value': '3m'},
                                    {'label': '6 Months', 'value': '6m'},
                                    {'label': '1 Year', 'value': '1y'},
                                    {'label': '2 Years', 'value': '2y'}
                                ],
                                value='1y'
                            )
                        ], width=3),
                        dbc.Col([
                            html.Label('Confidence Level'),
                            dcc.Dropdown(
                                id='risk-confidence',
                                options=[
                                    {'label': '90%', 'value': 0.90},
                                    {'label': '95%', 'value': 0.95},
                                    {'label': '99%', 'value': 0.99}
                                ],
                                value=0.95
                            )
                        ], width=3)
                    ], style={'marginBottom': '15px'}),
                    
                    html.Button('Analyze Risk', id='risk-run-btn', n_clicks=0,
                               style={'marginTop': '10px', 'padding': '10px 20px'}),
                    
                    dbc.Alert(id='risk-status', is_open=False, duration=4000, style={'marginTop': '15px'}),
                    
                    html.Div(id='risk-results', style={'marginTop': '20px'})
                ], style={'padding': '20px'})
            ]),
            
            dcc.Tab(label='Backtesting', value='backtest', children=[
                html.Div([
                    html.H4('Portfolio Backtesting', style={'marginTop': '20px'}),
                    html.P('Test historical performance of portfolio strategies.'),
                    
                    # Input section
                    dbc.Row([
                        dbc.Col([
                            html.Label('Tickers (comma-separated)'),
                            dcc.Input(
                                id='bt-tickers',
                                type='text',
                                value='AAPL,MSFT,GOOGL,AMZN,NVDA',
                                style={'width': '100%', 'padding': '8px'}
                            )
                        ], width=6),
                        dbc.Col([
                            html.Label('Backtest Period'),
                            dcc.Dropdown(
                                id='bt-period',
                                options=[
                                    {'label': '6 Months', 'value': '6m'},
                                    {'label': '1 Year', 'value': '1y'},
                                    {'label': '2 Years', 'value': '2y'},
                                    {'label': '3 Years', 'value': '3y'}
                                ],
                                value='1y'
                            )
                        ], width=3),
                        dbc.Col([
                            html.Label('Weight Strategy'),
                            dcc.Dropdown(
                                id='bt-strategy',
                                options=[
                                    {'label': 'Equal Weight', 'value': 'equal'},
                                    {'label': 'Market Cap Weight', 'value': 'mcap'},
                                    {'label': 'Risk Parity', 'value': 'risk_parity'}
                                ],
                                value='equal'
                            )
                        ], width=3)
                    ], style={'marginBottom': '15px'}),
                    
                    html.Button('Run Backtest', id='bt-run-btn', n_clicks=0,
                               style={'marginTop': '10px', 'padding': '10px 20px'}),
                    
                    dbc.Alert(id='bt-status', is_open=False, duration=4000, style={'marginTop': '15px'}),
                    
                    html.Div(id='bt-results', style={'marginTop': '20px'})
                ], style={'padding': '20px'})
            ]),
            
            dcc.Tab(label='Correlation Analysis', value='correlation', children=[
                html.Div([
                    html.H4('Correlation & Factor Analysis', style={'marginTop': '20px'}),
                    html.P('Analyze correlations and factor exposures across assets.'),
                    
                    # Input section
                    dbc.Row([
                        dbc.Col([
                            html.Label('Tickers (comma-separated)'),
                            dcc.Input(
                                id='corr-tickers',
                                type='text',
                                value='AAPL,MSFT,GOOGL,AMZN,NVDA,META,TSLA,SPY,QQQ',
                                style={'width': '100%', 'padding': '8px'}
                            )
                        ], width=8),
                        dbc.Col([
                            html.Label('Analysis Period'),
                            dcc.Dropdown(
                                id='corr-period',
                                options=[
                                    {'label': '3 Months', 'value': '3m'},
                                    {'label': '6 Months', 'value': '6m'},
                                    {'label': '1 Year', 'value': '1y'}
                                ],
                                value='6m'
                            )
                        ], width=4)
                    ], style={'marginBottom': '15px'}),
                    
                    html.Button('Analyze Correlation', id='corr-run-btn', n_clicks=0,
                               style={'marginTop': '10px', 'padding': '10px 20px'}),
                    
                    dbc.Alert(id='corr-status', is_open=False, duration=4000, style={'marginTop': '15px'}),
                    
                    html.Div(id='corr-results', style={'marginTop': '20px'})
                ], style={'padding': '20px'})
            ])
        ])
    ], style={'padding': '20px'})


def register_callbacks(app):
    """Register all Phase 4 callbacks."""
    
    # Portfolio Optimization callback
    @app.callback(
        [Output('opt-status', 'children'),
         Output('opt-status', 'is_open'),
         Output('opt-status', 'color'),
         Output('opt-results', 'children')],
        [Input('opt-run-btn', 'n_clicks')],
        [State('opt-tickers', 'value'),
         State('opt-method', 'value')]
    )
    def run_optimization(n_clicks, tickers_str, method):
        if not n_clicks:
            raise PreventUpdate
        
        try:
            tickers = [t.strip() for t in tickers_str.split(',') if t.strip()]
            if len(tickers) < 2:
                return ("Please provide at least 2 tickers", True, 'warning', html.Div())
            
            optimizer = PortfolioOptimizer(tickers)
            
            if method == 'sharpe':
                result = optimizer.optimize_sharpe()
            elif method == 'min_var':
                result = optimizer.optimize_min_variance()
            else:  # risk_parity
                result = optimizer.risk_parity()
            
            if not result:
                return ("Optimization failed", True, 'danger', html.Div())
            
            # Create results display
            results_div = html.Div([
                html.H5(f"{result['optimization']} Results"),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Expected Annual Return', className='card-subtitle'),
                                html.H4(f"{result['expected_return']:.2%}", className='card-title')
                            ])
                        ])
                    ], width=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Annual Volatility', className='card-subtitle'),
                                html.H4(f"{result['volatility']:.2%}", className='card-title')
                            ])
                        ])
                    ], width=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Sharpe Ratio', className='card-subtitle'),
                                html.H4(f"{result.get('sharpe_ratio', 0):.2f}", className='card-title')
                            ])
                        ])
                    ], width=4)
                ], style={'marginTop': '20px', 'marginBottom': '20px'}),
                
                html.H6('Optimal Weights'),
                dash_table.DataTable(
                    data=[{'Ticker': k, 'Weight': f"{v:.2%}"} for k, v in sorted(result['weights'].items(), key=lambda x: x[1], reverse=True)],
                    columns=[{'name': 'Ticker', 'id': 'Ticker'}, {'name': 'Weight', 'id': 'Weight'}],
                    style_cell={'textAlign': 'left', 'padding': '10px'},
                    style_header={'backgroundColor': 'rgb(31, 41, 55)', 'color': 'white', 'fontWeight': 'bold'},
                    style_data_conditional=[
                        {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 249, 250)'}
                    ]
                )
            ])
            
            return (f"Optimization complete for {len(tickers)} assets", True, 'success', results_div)
        
        except Exception as e:
            logger.error(f"Optimization error: {e}", exc_info=True)
            return (f"Error: {str(e)}", True, 'danger', html.Div())
    
    
    # Risk Analysis callback
    @app.callback(
        [Output('risk-status', 'children'),
         Output('risk-status', 'is_open'),
         Output('risk-status', 'color'),
         Output('risk-results', 'children')],
        [Input('risk-run-btn', 'n_clicks')],
        [State('risk-tickers', 'value'),
         State('risk-period', 'value'),
         State('risk-confidence', 'value')]
    )
    def run_risk_analysis(n_clicks, tickers_str, period, confidence):
        if not n_clicks:
            raise PreventUpdate
        
        try:
            tickers = [t.strip() for t in tickers_str.split(',') if t.strip()]
            
            # Calculate date range
            end_date = datetime.now()
            days_map = {'3m': 90, '6m': 180, '1y': 365, '2y': 730}
            start_date = end_date - timedelta(days=days_map.get(period, 365))
            
            # Equal weight portfolio
            weights = {ticker: 1/len(tickers) for ticker in tickers}
            metrics = calculate_portfolio_metrics(tickers, weights, start_date, end_date)
            
            if not metrics:
                return ("Analysis failed", True, 'danger', html.Div())
            
            # Create results display
            results_div = html.Div([
                html.H5('Risk Metrics'),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Total Return', className='card-subtitle'),
                                html.H4(f"{metrics['total_return']:.2%}", className='card-title')
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Sharpe Ratio', className='card-subtitle'),
                                html.H4(f"{metrics['sharpe_ratio']:.2f}", className='card-title')
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Max Drawdown', className='card-subtitle'),
                                html.H4(f"{metrics['max_drawdown']:.2%}", className='card-title', style={'color': '#ef4444'})
                            ])
                        ])
                    ], width=3),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6(f'VaR ({confidence:.0%})', className='card-subtitle'),
                                html.H4(f"{metrics['var_95']:.2%}", className='card-title', style={'color': '#f59e0b'})
                            ])
                        ])
                    ], width=3)
                ], style={'marginTop': '20px', 'marginBottom': '20px'}),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Annualized Return', className='card-subtitle'),
                                html.P(f"{metrics['annualized_return']:.2%}")
                            ])
                        ])
                    ], width=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Annualized Volatility', className='card-subtitle'),
                                html.P(f"{metrics['annualized_volatility']:.2%}")
                            ])
                        ])
                    ], width=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Sortino Ratio', className='card-subtitle'),
                                html.P(f"{metrics['sortino_ratio']:.2f}")
                            ])
                        ])
                    ], width=4)
                ], style={'marginBottom': '20px'}),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Win Rate', className='card-subtitle'),
                                html.P(f"{metrics['win_rate']:.1%}")
                            ])
                        ])
                    ], width=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Best Day', className='card-subtitle'),
                                html.P(f"{metrics['best_day']:.2%}", style={'color': '#10b981'})
                            ])
                        ])
                    ], width=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Worst Day', className='card-subtitle'),
                                html.P(f"{metrics['worst_day']:.2%}", style={'color': '#ef4444'})
                            ])
                        ])
                    ], width=4)
                ])
            ])
            
            return (f"Risk analysis complete for {len(tickers)} assets over {period}", True, 'success', results_div)
        
        except Exception as e:
            logger.error(f"Risk analysis error: {e}", exc_info=True)
            return (f"Error: {str(e)}", True, 'danger', html.Div())
    
    
    # Backtesting callback
    @app.callback(
        [Output('bt-status', 'children'),
         Output('bt-status', 'is_open'),
         Output('bt-status', 'color'),
         Output('bt-results', 'children')],
        [Input('bt-run-btn', 'n_clicks')],
        [State('bt-tickers', 'value'),
         State('bt-period', 'value'),
         State('bt-strategy', 'value')]
    )
    def run_backtest(n_clicks, tickers_str, period, strategy):
        if not n_clicks:
            raise PreventUpdate
        
        try:
            tickers = [t.strip() for t in tickers_str.split(',') if t.strip()]
            
            # Calculate date range
            end_date = datetime.now()
            days_map = {'6m': 180, '1y': 365, '2y': 730, '3y': 1095}
            start_date = end_date - timedelta(days=days_map.get(period, 365))
            
            # Determine weights based on strategy
            if strategy == 'equal':
                weights = {ticker: 1/len(tickers) for ticker in tickers}
            elif strategy == 'risk_parity':
                optimizer = PortfolioOptimizer(tickers, start_date, end_date)
                result = optimizer.risk_parity()
                weights = result['weights'] if result else {ticker: 1/len(tickers) for ticker in tickers}
            else:  # mcap - for now, use equal (would need market cap data)
                weights = {ticker: 1/len(tickers) for ticker in tickers}
            
            # Run backtest
            backtester = Backtester(tickers, weights, start_date, end_date)
            bt_results = backtester.run()
            
            if not bt_results:
                return ("Backtest failed", True, 'danger', html.Div())
            
            metrics = bt_results['metrics']
            
            # Create portfolio value chart
            portfolio_df = pd.DataFrame({'date': list(bt_results['portfolio_value'].keys()),
                                        'value': list(bt_results['portfolio_value'].values())})
            portfolio_df['date'] = pd.to_datetime(portfolio_df['date'])
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=portfolio_df['date'],
                y=portfolio_df['value'],
                mode='lines',
                name='Portfolio Value',
                line=dict(color='#3b82f6', width=2)
            ))
            fig.update_layout(
                title='Portfolio Performance',
                xaxis_title='Date',
                yaxis_title='Portfolio Value ($)',
                template='plotly_dark',
                height=400
            )
            
            # Create results display
            results_div = html.Div([
                html.H5('Backtest Results'),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Total Return', className='card-subtitle'),
                                html.H4(f"{metrics['total_return']:.2%}", className='card-title')
                            ])
                        ])
                    ], width=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Sharpe Ratio', className='card-subtitle'),
                                html.H4(f"{metrics['sharpe_ratio']:.2f}", className='card-title')
                            ])
                        ])
                    ], width=4),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6('Max Drawdown', className='card-subtitle'),
                                html.H4(f"{metrics['max_drawdown']:.2%}", className='card-title', style={'color': '#ef4444'})
                            ])
                        ])
                    ], width=4)
                ], style={'marginTop': '20px', 'marginBottom': '20px'}),
                
                dcc.Graph(figure=fig),
                
                html.H6('Performance Metrics', style={'marginTop': '20px'}),
                dash_table.DataTable(
                    data=[
                        {'Metric': 'Annualized Return', 'Value': f"{metrics['annualized_return']:.2%}"},
                        {'Metric': 'Annualized Volatility', 'Value': f"{metrics['annualized_volatility']:.2%}"},
                        {'Metric': 'Sharpe Ratio', 'Value': f"{metrics['sharpe_ratio']:.2f}"},
                        {'Metric': 'Max Drawdown', 'Value': f"{metrics['max_drawdown']:.2%}"},
                        {'Metric': 'VaR (95%)', 'Value': f"{metrics['var_95']:.2%}"},
                        {'Metric': 'CVaR (95%)', 'Value': f"{metrics['cvar_95']:.2%}"}
                    ],
                    columns=[{'name': 'Metric', 'id': 'Metric'}, {'name': 'Value', 'id': 'Value'}],
                    style_cell={'textAlign': 'left', 'padding': '10px'},
                    style_header={'backgroundColor': 'rgb(31, 41, 55)', 'color': 'white', 'fontWeight': 'bold'},
                    style_data_conditional=[
                        {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgb(248, 249, 250)'}
                    ]
                )
            ])
            
            return (f"Backtest complete: {period} period, {strategy} strategy", True, 'success', results_div)
        
        except Exception as e:
            logger.error(f"Backtest error: {e}", exc_info=True)
            return (f"Error: {str(e)}", True, 'danger', html.Div())
    
    
    # Correlation Analysis callback
    @app.callback(
        [Output('corr-status', 'children'),
         Output('corr-status', 'is_open'),
         Output('corr-status', 'color'),
         Output('corr-results', 'children')],
        [Input('corr-run-btn', 'n_clicks')],
        [State('corr-tickers', 'value'),
         State('corr-period', 'value')]
    )
    def run_correlation_analysis(n_clicks, tickers_str, period):
        if not n_clicks:
            raise PreventUpdate
        
        try:
            import yfinance as yf
            
            tickers = [t.strip() for t in tickers_str.split(',') if t.strip()]
            
            # Calculate date range
            end_date = datetime.now()
            days_map = {'3m': 90, '6m': 180, '1y': 365}
            start_date = end_date - timedelta(days=days_map.get(period, 180))
            
            # Fetch data
            prices = yf.download(tickers, start=start_date, end=end_date, progress=False)['Adj Close']
            if isinstance(prices, pd.Series):
                prices = prices.to_frame(name=tickers[0])
            returns = prices.pct_change().dropna()
            
            # Calculate correlation matrix
            corr_matrix = returns.corr()
            
            # Create heatmap
            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.index,
                colorscale='RdBu',
                zmid=0,
                text=corr_matrix.values,
                texttemplate='%{text:.2f}',
                textfont={"size": 10},
                colorbar=dict(title="Correlation")
            ))
            fig.update_layout(
                title='Correlation Heatmap',
                template='plotly_dark',
                height=600,
                width=800
            )
            
            # Create results display
            results_div = html.Div([
                html.H5('Correlation Analysis'),
                dcc.Graph(figure=fig),
                
                html.H6('Highest Correlations', style={'marginTop': '20px'}),
                html.P('Pairs with correlation > 0.7'),
                dash_table.DataTable(
                    data=[
                        {'Asset 1': corr_matrix.index[i], 'Asset 2': corr_matrix.columns[j], 
                         'Correlation': f"{corr_matrix.iloc[i, j]:.3f}"}
                        for i in range(len(corr_matrix))
                        for j in range(i+1, len(corr_matrix.columns))
                        if abs(corr_matrix.iloc[i, j]) > 0.7
                    ][:10],  # Top 10
                    columns=[
                        {'name': 'Asset 1', 'id': 'Asset 1'},
                        {'name': 'Asset 2', 'id': 'Asset 2'},
                        {'name': 'Correlation', 'id': 'Correlation'}
                    ],
                    style_cell={'textAlign': 'left', 'padding': '10px'},
                    style_header={'backgroundColor': 'rgb(31, 41, 55)', 'color': 'white', 'fontWeight': 'bold'}
                )
            ])
            
            return (f"Correlation analysis complete for {len(tickers)} assets", True, 'success', results_div)
        
        except Exception as e:
            logger.error(f"Correlation analysis error: {e}", exc_info=True)
            return (f"Error: {str(e)}", True, 'danger', html.Div())
