"""
Research Lab - Components Module
Reusable UI components for research brief interface.
"""

from dash import html, dcc, dash_table
import dash_bootstrap_components as dbc
import pandas as pd


def empty_brief_list():
    """Component shown when no briefs exist."""
    return html.Div([
        html.I(className="bi bi-inbox", style={'font-size': '3rem', 'opacity': '0.3'}),
        html.P(
            "No briefs found — click New Brief or Load Demo",
            className="text-muted text-center mt-3"
        )
    ], className="text-center p-4")


def empty_detail_panel():
    """Component shown when no brief is selected."""
    return html.Div([
        html.I(className="bi bi-arrow-left-circle me-2", style={'font-size': '3rem'}),
        html.H5("Select a brief from the list to view details", className="text-muted mt-3")
    ], className="text-center p-5")


def error_panel(message):
    """Component for displaying errors."""
    return dbc.Alert([
        html.I(className="bi bi-exclamation-triangle me-2"),
        message
    ], color="danger")


def loading_panel(message="Loading..."):
    """Component for loading states."""
    return html.Div([
        dbc.Spinner(size="lg"),
        html.P(message, className="text-muted mt-3")
    ], className="text-center p-4")


def render_screen_results(results):
    """
    Render screening results as a table with summary.
    
    Args:
        results: Dictionary with screening results
        
    Returns:
        Dash component with rendered results
    """
    if not results or 'tickers' not in results:
        return error_panel("No screening results available")
    
    tickers = results.get('tickers', [])
    summary = results.get('summary', {})
    
    # Create DataFrame for table
    df = pd.DataFrame(tickers)
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-check-circle me-2 text-success"),
            html.H6("Screening Results", className="d-inline mb-0")
        ]),
        dbc.CardBody([
            # Summary metrics
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Total Matches", className="text-muted small"),
                            html.H4(summary.get('total_matches', len(tickers)))
                        ])
                    ])
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Avg Score", className="text-muted small"),
                            html.H4(f"{summary.get('avg_score', 0):.2f}")
                        ])
                    ])
                ], width=4),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Screen Type", className="text-muted small"),
                            html.H4(summary.get('type', 'Momentum').upper())
                        ])
                    ])
                ], width=4)
            ], className="mb-3"),
            
            # Results table
            html.H6("Top Tickers", className="mt-3 mb-2"),
            dash_table.DataTable(
                data=df.to_dict('records'),
                columns=[
                    {'name': 'Ticker', 'id': 'ticker'},
                    {'name': 'Score', 'id': 'score', 'type': 'numeric', 'format': {'specifier': '.2f'}},
                    {'name': 'Volatility', 'id': 'volatility', 'type': 'numeric', 'format': {'specifier': '.2%'}},
                    {'name': 'Return 1M', 'id': 'return_1m', 'type': 'numeric', 'format': {'specifier': '.2%'}},
                ],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '8px'},
                style_header={'backgroundColor': '#2b3035', 'fontWeight': 'bold', 'color': 'white'},
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{score} > 7'},
                        'backgroundColor': '#10b98120',
                    }
                ],
                page_size=10,
                sort_action='native'
            )
        ])
    ], className="mt-3")


def render_backtest_results(results):
    """
    Render backtest preview results.
    
    Args:
        results: Dictionary with backtest results
        
    Returns:
        Dash component with rendered results
    """
    if not results or 'metrics' not in results:
        return error_panel("No backtest results available")
    
    metrics = results.get('metrics', {})
    trades = results.get('sample_trades', [])
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-bar-chart me-2 text-primary"),
            html.H6("Backtest Preview Results", className="d-inline mb-0")
        ]),
        dbc.CardBody([
            # Performance metrics
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Total Return", className="text-muted small"),
                            html.H4(
                                f"{metrics.get('total_return', 0):.2%}",
                                className="text-success" if metrics.get('total_return', 0) > 0 else "text-danger"
                            )
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Sharpe Ratio", className="text-muted small"),
                            html.H4(f"{metrics.get('sharpe', 0):.2f}")
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Max Drawdown", className="text-muted small"),
                            html.H4(
                                f"{metrics.get('max_drawdown', 0):.2%}",
                                className="text-danger"
                            )
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Win Rate", className="text-muted small"),
                            html.H4(f"{metrics.get('win_rate', 0):.2%}")
                        ])
                    ])
                ], width=3)
            ], className="mb-3"),
            
            # Sample trades table
            html.H6("Sample Trades", className="mt-3 mb-2"),
            dash_table.DataTable(
                data=trades,
                columns=[
                    {'name': 'Date', 'id': 'date'},
                    {'name': 'Ticker', 'id': 'ticker'},
                    {'name': 'Action', 'id': 'action'},
                    {'name': 'Price', 'id': 'price', 'type': 'numeric', 'format': {'specifier': '$.2f'}},
                    {'name': 'Return', 'id': 'return', 'type': 'numeric', 'format': {'specifier': '.2%'}},
                ],
                style_table={'overflowX': 'auto'},
                style_cell={'textAlign': 'left', 'padding': '8px'},
                style_header={'backgroundColor': '#2b3035', 'fontWeight': 'bold', 'color': 'white'},
                style_data_conditional=[
                    {
                        'if': {'filter_query': '{return} > 0'},
                        'backgroundColor': '#10b98120',
                    },
                    {
                        'if': {'filter_query': '{return} < 0'},
                        'backgroundColor': '#ef444420',
                    }
                ],
                page_size=10
            ),
            
            html.P(
                f"Showing {len(trades)} sample trades. Full backtest available on export.",
                className="text-muted small mt-2"
            )
        ])
    ], className="mt-3")
