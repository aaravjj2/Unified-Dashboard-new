"""
Backtesting Lab Tab - Sprint 8
Provides UI for running strategy backtests and viewing results
"""

from dash import dcc, html, Input, Output, State
import plotly.graph_objs as go
from datetime import datetime, timedelta
import requests
import logging

logger = logging.getLogger(__name__)

# Layout
def create_layout():
    """Create the backtesting lab layout"""
    return html.Div([
        html.Div([
            html.H2("🧪 Backtesting Lab", className="text-white mb-3"),
            html.P("Test your trading strategies with historical data", className="text-light")
        ], className="mb-4"),
        
        # Configuration Section
        html.Div([
            html.H5("Backtest Configuration", className="text-white mb-3"),
            
            html.Div([
                # Strategy Selection
                html.Div([
                    html.Label("Strategy", className="text-light"),
                    dcc.Dropdown(
                        id='bt-strategy-select',
                        options=[
                            {'label': 'SMA Crossover', 'value': 'SMA Crossover'},
                            {'label': 'RSI Mean Reversion', 'value': 'RSI Mean Reversion'},
                            {'label': 'Momentum', 'value': 'Momentum'}
                        ],
                        value='SMA Crossover',
                        className="mb-3"
                    )
                ], className="col-md-6"),
                
                # Symbol Input
                html.Div([
                    html.Label("Symbol", className="text-light"),
                    dcc.Input(
                        id='bt-symbol-input',
                        type='text',
                        value='AAPL',
                        className="form-control mb-3"
                    )
                ], className="col-md-6")
            ], className="row"),
            
            html.Div([
                # Start Date
                html.Div([
                    html.Label("Start Date", className="text-light"),
                    dcc.DatePickerSingle(
                        id='bt-start-date',
                        date=(datetime.now() - timedelta(days=365)).date(),
                        display_format='YYYY-MM-DD',
                        className="mb-3"
                    )
                ], className="col-md-4"),
                
                # End Date
                html.Div([
                    html.Label("End Date", className="text-light"),
                    dcc.DatePickerSingle(
                        id='bt-end-date',
                        date=datetime.now().date(),
                        display_format='YYYY-MM-DD',
                        className="mb-3"
                    )
                ], className="col-md-4"),
                
                # Initial Capital
                html.Div([
                    html.Label("Initial Capital ($)", className="text-light"),
                    dcc.Input(
                        id='bt-capital-input',
                        type='number',
                        value=100000,
                        className="form-control mb-3"
                    )
                ], className="col-md-4")
            ], className="row"),
            
            # Run Button
            html.Div([
                html.Button(
                    "Run Backtest",
                    id='bt-run-button',
                    n_clicks=0,
                    className="btn btn-primary btn-lg"
                ),
                html.Span(id='bt-status', className="ms-3 text-light")
            ], className="text-center my-4")
            
        ], className="card bg-dark p-4 mb-4"),
        
        # Results Section
        html.Div([
            html.H5("Results", className="text-white mb-3"),
            
            # KPIs
            html.Div([
                html.Div([
                    html.Div([
                        html.H6("Total Return", className="text-light"),
                        html.H4(id='bt-total-return', className="text-success")
                    ], className="card bg-dark p-3")
                ], className="col-md-3"),
                
                html.Div([
                    html.Div([
                        html.H6("Total Trades", className="text-light"),
                        html.H4(id='bt-total-trades', className="text-info")
                    ], className="card bg-dark p-3")
                ], className="col-md-3"),
                
                html.Div([
                    html.Div([
                        html.H6("Win Rate", className="text-light"),
                        html.H4(id='bt-win-rate', className="text-warning")
                    ], className="card bg-dark p-3")
                ], className="col-md-3"),
                
                html.Div([
                    html.Div([
                        html.H6("Sharpe Ratio", className="text-light"),
                        html.H4(id='bt-sharpe-ratio', className="text-primary")
                    ], className="card bg-dark p-3")
                ], className="col-md-3")
            ], className="row mb-4", id='bt-kpis', style={'display': 'none'}),
            
            # Equity Curve Chart
            html.Div([
                dcc.Graph(id='bt-equity-chart', style={'height': '400px'})
            ], className="mb-4", id='bt-chart-container', style={'display': 'none'}),
            
            # Trade Log Table
            html.Div([
                html.H6("Trade Log", className="text-white mb-3"),
                html.Div(id='bt-trade-table')
            ], id='bt-table-container', style={'display': 'none'})
            
        ], className="card bg-dark p-4"),
        
        # Hidden div to store results
        dcc.Store(id='bt-results-store')
        
    ], className="container-fluid")

def register_callbacks(app):
    """Register Dash callbacks for the Backtesting Lab tab."""

    @app.callback(
        [
            Output('bt-status', 'children'),
            Output('bt-results-store', 'data'),
            Output('bt-kpis', 'style'),
            Output('bt-chart-container', 'style'),
            Output('bt-table-container', 'style')
        ],
        Input('bt-run-button', 'n_clicks'),
        [
            State('bt-strategy-select', 'value'),
            State('bt-symbol-input', 'value'),
            State('bt-start-date', 'date'),
            State('bt-end-date', 'date'),
            State('bt-capital-input', 'value')
        ],
        prevent_initial_call=True
    )
    def run_backtest(n_clicks, strategy, symbol, start_date, end_date, initial_capital):
        """Run backtest when button is clicked."""
        if n_clicks == 0:
            return "", None, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}

        try:
            response = requests.post(
                'http://localhost:8049/api/backtest/run',
                json={
                    'strategy': strategy,
                    'symbol': symbol,
                    'start_date': start_date,
                    'end_date': end_date,
                    'initial_capital': float(initial_capital),
                    'parameters': {}
                },
                timeout=30
            )

            if response.status_code == 200:
                results = response.json()
                return (
                    "✓ Backtest completed successfully",
                    results,
                    {'display': 'block'},
                    {'display': 'block'},
                    {'display': 'block'}
                )

            error_msg = f"Error: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return error_msg, None, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}

        except Exception as exc:
            error_msg = f"Error running backtest: {str(exc)}"
            logger.error(error_msg)
            return error_msg, None, {'display': 'none'}, {'display': 'none'}, {'display': 'none'}

    @app.callback(
        [
            Output('bt-total-return', 'children'),
            Output('bt-total-trades', 'children'),
            Output('bt-win-rate', 'children'),
            Output('bt-sharpe-ratio', 'children')
        ],
        Input('bt-results-store', 'data')
    )
    def update_kpis(results):
        """Update KPI displays."""
        if not results:
            return "—", "—", "—", "—"

        total_return = f"${results.get('total_return', 0):,.2f} ({results.get('total_return_pct', 0):.2f}%)"
        total_trades = str(results.get('total_trades', 0))
        win_rate = f"{results.get('win_rate', 0):.1f}%"
        sharpe_ratio = f"{results.get('sharpe_ratio', 0):.2f}"

        return total_return, total_trades, win_rate, sharpe_ratio

    @app.callback(
        Output('bt-equity-chart', 'figure'),
        Input('bt-results-store', 'data')
    )
    def update_equity_chart(results):
        """Update equity curve chart."""
        if not results or not results.get('equity_curve'):
            return {
                'data': [],
                'layout': go.Layout(
                    title='Equity Curve',
                    template='plotly_dark',
                    height=400
                )
            }

        equity_curve = results['equity_curve']
        dates = [point['date'] for point in equity_curve]
        equity = [point['equity'] for point in equity_curve]

        return {
            'data': [
                go.Scatter(
                    x=dates,
                    y=equity,
                    mode='lines',
                    name='Equity',
                    line=dict(color='#00d9ff', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(0, 217, 255, 0.1)'
                )
            ],
            'layout': go.Layout(
                title=f"Equity Curve - {results.get('strategy', '')} on {results.get('symbol', '')}",
                template='plotly_dark',
                height=400,
                xaxis=dict(title='Date'),
                yaxis=dict(title='Equity ($)', tickformat='$,.0f'),
                hovermode='x unified'
            )
        }

    @app.callback(
        Output('bt-trade-table', 'children'),
        Input('bt-results-store', 'data')
    )
    def update_trade_table(results):
        """Update trade log table."""
        if not results or not results.get('trade_log'):
            return html.P("No trades to display", className="text-light")

        trade_log = results['trade_log']

        table_header = [
            html.Thead(html.Tr([
                html.Th("Entry Date", className="text-light"),
                html.Th("Entry Price", className="text-light"),
                html.Th("Exit Date", className="text-light"),
                html.Th("Exit Price", className="text-light"),
                html.Th("P&L", className="text-light"),
            ]))
        ]

        table_rows = []
        for trade in trade_log[:20]:
            pnl = trade.get('pnl', 0)
            pnl_class = "text-success" if pnl > 0 else "text-danger"

            table_rows.append(html.Tr([
                html.Td(trade.get('entry_date', ''), className="text-light"),
                html.Td(f"${trade.get('entry_price', 0):.2f}", className="text-light"),
                html.Td(trade.get('exit_date', ''), className="text-light"),
                html.Td(f"${trade.get('exit_price', 0):.2f}", className="text-light"),
                html.Td(f"${pnl:.2f}", className=pnl_class)
            ]))

        table_body = [html.Tbody(table_rows)]

        return html.Table(
            table_header + table_body,
            className="table table-dark table-striped table-hover"
        )

# Export layout
layout = create_layout()
