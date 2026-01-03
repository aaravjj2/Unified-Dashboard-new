"""
Research Lab Tab

Provides UI for historical backtesting of options strategies.
"""

from datetime import date, datetime, timedelta
from dash import html, dcc, callback, Input, Output, State, no_update
import dash_bootstrap_components as dbc

from engines.backtest.runner import StrategyType


def create_research_tab() -> dbc.Container:
    """
    Create the Research Lab tab content.
    
    Returns:
        Container with backtest configuration and results display
    """
    
    # Default date range: last 90 days
    end_date = date.today()
    start_date = end_date - timedelta(days=90)
    
    return dbc.Container([
        # Header
        dbc.Row([
            dbc.Col([
                html.H4("📊 Research Lab - Historical Backtester", className="mb-0"),
                html.P("Test strategies against historical data", className="text-muted small"),
            ], width=8),
            dbc.Col([
                html.Div(id="backtest-status", className="text-end"),
            ], width=4),
        ], className="mb-3 align-items-center"),
        
        # Configuration Panel
        dbc.Card([
            dbc.CardHeader([
                html.I(className="fas fa-cog me-2"),
                "Backtest Configuration"
            ]),
            dbc.CardBody([
                dbc.Row([
                    # Date Range
                    dbc.Col([
                        dbc.Label("Start Date"),
                        dcc.DatePickerSingle(
                            id="input-start-date",
                            date=start_date,
                            display_format="YYYY-MM-DD",
                            className="w-100"
                        ),
                    ], md=3),
                    dbc.Col([
                        dbc.Label("End Date"),
                        dcc.DatePickerSingle(
                            id="input-end-date",
                            date=end_date,
                            display_format="YYYY-MM-DD",
                            className="w-100"
                        ),
                    ], md=3),
                    
                    # Initial Capital
                    dbc.Col([
                        dbc.Label("Initial Capital ($)"),
                        dbc.Input(
                            id="input-capital",
                            type="number",
                            value=100000,
                            min=10000,
                            max=10000000,
                            step=10000,
                        ),
                    ], md=3),
                    
                    # Symbol
                    dbc.Col([
                        dbc.Label("Symbol"),
                        dbc.Select(
                            id="input-symbol",
                            options=[
                                {"label": "SPY - S&P 500 ETF", "value": "SPY"},
                                {"label": "QQQ - Nasdaq 100 ETF", "value": "QQQ"},
                                {"label": "IWM - Russell 2000 ETF", "value": "IWM"},
                                {"label": "GLD - Gold ETF", "value": "GLD"},
                                {"label": "AAPL - Apple Inc.", "value": "AAPL"},
                                {"label": "MSFT - Microsoft Corp.", "value": "MSFT"},
                                {"label": "NVDA - NVIDIA Corp.", "value": "NVDA"},
                            ],
                            value="SPY",
                        ),
                    ], md=3),
                ], className="mb-3"),
                
                dbc.Row([
                    # Strategy Type
                    dbc.Col([
                        dbc.Label("Strategy Type"),
                        dbc.Select(
                            id="input-strategy",
                            options=[
                                {"label": "Iron Condor", "value": StrategyType.IRON_CONDOR.value},
                                {"label": "Covered Call", "value": StrategyType.COVERED_CALL.value},
                                {"label": "Cash Secured Put", "value": StrategyType.CASH_SECURED_PUT.value},
                                {"label": "Long Call", "value": StrategyType.LONG_CALL.value},
                                {"label": "Long Put", "value": StrategyType.LONG_PUT.value},
                            ],
                            value=StrategyType.IRON_CONDOR.value,
                        ),
                    ], md=3),
                    
                    # Position Size
                    dbc.Col([
                        dbc.Label("Position Size (%)"),
                        dbc.Input(
                            id="input-position-size",
                            type="number",
                            value=10,
                            min=1,
                            max=50,
                            step=1,
                        ),
                    ], md=2),
                    
                    # Days to Expiration
                    dbc.Col([
                        dbc.Label("Days to Expiration"),
                        dbc.Input(
                            id="input-dte",
                            type="number",
                            value=30,
                            min=7,
                            max=90,
                            step=1,
                        ),
                    ], md=2),
                    
                    # Profit Target
                    dbc.Col([
                        dbc.Label("Profit Target (%)"),
                        dbc.Input(
                            id="input-profit-target",
                            type="number",
                            value=50,
                            min=10,
                            max=100,
                            step=5,
                        ),
                    ], md=2),
                    
                    # Stop Loss
                    dbc.Col([
                        dbc.Label("Stop Loss (%)"),
                        dbc.Input(
                            id="input-stop-loss",
                            type="number",
                            value=200,
                            min=50,
                            max=500,
                            step=25,
                        ),
                    ], md=2),
                ], className="mb-3"),
                
                # Run Button
                dbc.Row([
                    dbc.Col([
                        dbc.Button(
                            [
                                html.I(className="fas fa-play me-2"),
                                "Run Backtest"
                            ],
                            id="btn-run-backtest",
                            color="success",
                            size="lg",
                            className="me-2"
                        ),
                        dbc.Button(
                            [
                                html.I(className="fas fa-stop me-2"),
                                "Cancel"
                            ],
                            id="btn-cancel-backtest",
                            color="danger",
                            outline=True,
                            disabled=True,
                        ),
                    ], className="text-center"),
                ]),
            ]),
        ], className="mb-4"),
        
        # Progress Bar (hidden until running)
        html.Div(
            id="backtest-progress-container",
            children=[
                dbc.Progress(
                    id="backtest-progress",
                    value=0,
                    striped=True,
                    animated=True,
                    className="mb-3",
                    style={"height": "25px"}
                ),
            ],
            style={"display": "none"}
        ),
        
        # Results Section
        html.Div(id="backtest-results", children=[
            # Placeholder - will be populated after backtest runs
            dbc.Alert(
                [
                    html.I(className="fas fa-info-circle me-2"),
                    "Configure parameters above and click 'Run Backtest' to see results."
                ],
                color="info",
                className="text-center"
            )
        ]),
        
        # Hidden stores for state management
        dcc.Store(id="store-backtest-config"),
        dcc.Store(id="store-backtest-results"),
        dcc.Interval(id="interval-backtest-progress", interval=500, disabled=True),
        
    ], fluid=True, className="py-3")


def create_results_layout(result: dict) -> html.Div:
    """
    Create the results display after backtest completes.
    
    Args:
        result: Backtest results dictionary
        
    Returns:
        Div containing charts and statistics
    """
    from research_ui.components.reports import (
        create_equity_curve_chart,
        create_drawdown_chart,
        create_stats_card,
        create_trade_log_table
    )
    
    return html.Div([
        # Stats Cards Row
        dbc.Row([
            dbc.Col(create_stats_card(result), md=12),
        ], className="mb-4"),
        
        # Charts Row
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📈 Equity Curve"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="chart-equity",
                            figure=create_equity_curve_chart(result),
                            config={"displayModeBar": True}
                        )
                    ])
                ])
            ], md=7),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📉 Drawdown"),
                    dbc.CardBody([
                        dcc.Graph(
                            id="chart-drawdown",
                            figure=create_drawdown_chart(result),
                            config={"displayModeBar": True}
                        )
                    ])
                ])
            ], md=5),
        ], className="mb-4"),
        
        # Trade Log
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("📋 Trade Log"),
                    dbc.CardBody([
                        create_trade_log_table(result.get('trades', []))
                    ])
                ])
            ], md=12),
        ]),
    ])


def register_research_callbacks(app):
    """Register callbacks for the Research tab"""
    
    @app.callback(
        [
            Output("backtest-results", "children"),
            Output("backtest-status", "children"),
            Output("backtest-progress-container", "style"),
            Output("backtest-progress", "value"),
            Output("btn-run-backtest", "disabled"),
            Output("btn-cancel-backtest", "disabled"),
        ],
        [
            Input("btn-run-backtest", "n_clicks"),
        ],
        [
            State("input-start-date", "date"),
            State("input-end-date", "date"),
            State("input-capital", "value"),
            State("input-symbol", "value"),
            State("input-strategy", "value"),
            State("input-position-size", "value"),
            State("input-dte", "value"),
            State("input-profit-target", "value"),
            State("input-stop-loss", "value"),
        ],
        prevent_initial_call=True
    )
    def run_backtest(
        n_clicks,
        start_date,
        end_date,
        capital,
        symbol,
        strategy,
        position_size,
        dte,
        profit_target,
        stop_loss
    ):
        """Run backtest when button is clicked"""
        from datetime import datetime
        from engines.backtest.runner import BacktestRunner, BacktestConfig, StrategyType
        from research_ui.components.reports import (
            create_equity_curve_chart,
            create_drawdown_chart,
            create_stats_card,
            create_trade_log_table
        )
        
        if not n_clicks:
            return no_update, no_update, no_update, no_update, no_update, no_update
        
        # Show progress
        status = dbc.Badge("Running...", color="warning", className="p-2")
        progress_style = {"display": "block"}
        
        try:
            # Parse dates
            if isinstance(start_date, str):
                start_dt = datetime.strptime(start_date[:10], "%Y-%m-%d").date()
            else:
                start_dt = start_date
            
            if isinstance(end_date, str):
                end_dt = datetime.strptime(end_date[:10], "%Y-%m-%d").date()
            else:
                end_dt = end_date
            
            # Create config
            config = BacktestConfig(
                start_date=start_dt,
                end_date=end_dt,
                initial_capital=float(capital or 100000),
                strategy=StrategyType(strategy),
                symbol=symbol or "SPY",
                position_size_pct=float(position_size or 10) / 100,
                days_to_expiration=int(dte or 30),
                profit_target_pct=float(profit_target or 50) / 100,
                stop_loss_pct=float(stop_loss or 200) / 100,
            )
            
            # Run backtest
            runner = BacktestRunner.get_instance()
            result = runner.run(config)
            
            # Convert result to dict for display
            result_dict = {
                'total_return_pct': result.total_return_pct,
                'sharpe_ratio': result.sharpe_ratio,
                'max_drawdown_pct': result.max_drawdown_pct,
                'win_rate': result.win_rate,
                'profit_factor': result.profit_factor,
                'total_trades': result.total_trades,
                'winning_trades': result.winning_trades,
                'losing_trades': result.losing_trades,
                'avg_win': result.avg_win,
                'avg_loss': result.avg_loss,
                'best_trade': result.best_trade,
                'worst_trade': result.worst_trade,
                'avg_days_in_trade': result.avg_days_in_trade,
                'equity_curve': result.equity_curve,
                'drawdown_series': result.drawdown_series,
                'dates': [d.isoformat() for d in result.dates],
                'initial_capital': config.initial_capital,
                'trades': [
                    {
                        'id': t.id,
                        'symbol': t.symbol,
                        'strategy': t.strategy.value,
                        'entry_date': t.entry_date.isoformat(),
                        'exit_date': t.exit_date.isoformat() if t.exit_date else None,
                        'entry_price': t.entry_price,
                        'exit_price': t.exit_price,
                        'pnl': t.pnl,
                        'status': t.status.value,
                    }
                    for t in result.trades
                ]
            }
            
            # Build results display
            results_content = html.Div([
                # Stats Cards Row
                dbc.Row([
                    dbc.Col(create_stats_card(result_dict), md=12),
                ], className="mb-4"),
                
                # Charts Row
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("📈 Equity Curve"),
                            dbc.CardBody([
                                dcc.Graph(
                                    id="chart-equity",
                                    figure=create_equity_curve_chart(result_dict),
                                    config={"displayModeBar": True}
                                )
                            ])
                        ])
                    ], md=7),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("📉 Drawdown"),
                            dbc.CardBody([
                                dcc.Graph(
                                    id="chart-drawdown",
                                    figure=create_drawdown_chart(result_dict),
                                    config={"displayModeBar": True}
                                )
                            ])
                        ])
                    ], md=5),
                ], className="mb-4"),
                
                # Trade Log
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader("📋 Trade Log"),
                            dbc.CardBody([
                                create_trade_log_table(result_dict.get('trades', []))
                            ])
                        ])
                    ], md=12),
                ]),
            ])
            
            status = dbc.Badge("Complete ✓", color="success", className="p-2")
            
            return results_content, status, {"display": "none"}, 100, False, True
            
        except Exception as e:
            import traceback
            error_msg = str(e)
            tb = traceback.format_exc()
            
            results_content = dbc.Alert(
                [
                    html.H5("Backtest Error", className="alert-heading"),
                    html.P(error_msg),
                    html.Hr(),
                    html.Pre(tb, style={"fontSize": "10px", "maxHeight": "200px", "overflow": "auto"})
                ],
                color="danger"
            )
            
            status = dbc.Badge("Error ✗", color="danger", className="p-2")
            
            return results_content, status, {"display": "none"}, 0, False, True
