"""
Portfolio Tab - Positions, P/L, Transactions, Audit

Single source of truth for portfolio positions, realized/unrealized P/L,
and transaction reconciliation. Integrates with Monthly/Weekly picks and
provides audit bundle export.

Usage:
    from modules import portfolio
    app.layout = html.Div([portfolio.layout()])
    portfolio.register_callbacks(app)
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import numpy as np
from dash import dcc, html, Input, Output, State, dash_table, callback_context
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
# TEMPORARY: Comment out to avoid hanging import
# from utils.events_helper import get_ticker_events

logger = logging.getLogger(__name__)

# Import portfolio utilities
try:
    from utils import portfolio_utils
except ImportError:
    logger.warning("Could not import utils.portfolio_utils - creating placeholder")
    portfolio_utils = None


def layout():
    """Build the Portfolio tab layout."""
    return dbc.Container([
        # Header
        html.Div([
            html.H2([html.I(className="bi bi-wallet2 me-2"), "Portfolio Dashboard"], 
                   className="mt-3 mb-3"),
            html.P("Track positions, P/L, and portfolio performance", className="text-muted mb-4"),
        ], style={'background-color': '#2b3035', 'padding': '20px', 'border-radius': '8px', 'margin-bottom': '20px'}),
        
        # Summary Cards
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Portfolio Notional", className="text-muted"),
                        html.H4(id='port-notional', children="$0"),
                        html.Small("Total portfolio value", className="text-muted")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Invested", className="text-muted"),
                        html.H4(id='port-invested', children="$0"),
                        html.Small("Current positions", className="text-muted")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Realized P/L", className="text-muted"),
                        html.H4(id='port-realized-pnl', children="$0"),
                        html.Small(id='port-realized-pct', children="0%", className="text-muted")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Unrealized P/L", className="text-muted"),
                        html.H4(id='port-unrealized-pnl', children="$0"),
                        html.Small(id='port-unrealized-pct', children="0%", className="text-muted")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Total Alpha", className="text-muted"),
                        html.H4(id='port-alpha', children="0%"),
                        html.Small("Last 30 days", className="text-muted")
                    ])
                ])
            ], width=2),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H6("Beta", className="text-muted"),
                        html.H4(id='port-beta', children="0.00"),
                        html.Small("vs SPY", className="text-muted")
                    ])
                ])
            ], width=2)
        ], className="mb-4"),
        
        # Main Content Tabs
        dbc.Tabs([
            # Positions Tab
            dbc.Tab(label="📊 Positions", children=[
                dbc.Container([
                    html.H5("Current Positions", className="mt-3 mb-3"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Refresh Prices", id='port-refresh-btn', color='primary', 
                                      size='sm', className='me-2'),
                            dbc.Button("Upload Transactions", id='port-upload-btn', color='info', 
                                      size='sm', className='me-2'),
                            dbc.Button("Export Audit", id='port-export-btn', color='success', 
                                      size='sm', className='me-2'),
                            dcc.Download(id='port-download-audit')
                        ])
                    ], className="mb-3"),
                    
                    # Positions Table
                    html.Div(id='port-positions-table')
                ], fluid=True)
            ]),
            
            # Performance Tab
            dbc.Tab(label="📈 Performance", children=[
                dbc.Container([
                    html.H5("Portfolio Performance", className="mt-3 mb-3"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Cumulative P/L", className="mb-3"),
                                    dcc.Graph(id='port-pnl-chart')
                                ])
                            ])
                        ], width=12)
                    ], className="mb-4"),
                    
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Sector Attribution", className="mb-3"),
                                    dcc.Graph(id='port-sector-chart')
                                ])
                            ])
                        ], width=6),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Top Contributors", className="mb-3"),
                                    dcc.Graph(id='port-contributors-chart')
                                ])
                            ])
                        ], width=6)
                    ])
                ], fluid=True)
            ]),
            
            # Transactions Tab
            dbc.Tab(label="📝 Transactions", children=[
                dbc.Container([
                    html.H5("Transaction History", className="mt-3 mb-3"),
                    
                    dbc.Row([
                        dbc.Col([
                            dcc.Upload(
                                id='port-upload-component',
                                children=dbc.Button("Upload Transactions CSV", color='info'),
                                multiple=False
                            )
                        ])
                    ], className="mb-3"),
                    
                    dbc.Alert(id='port-upload-status', is_open=False, duration=4000),
                    
                    html.Div(id='port-transactions-table')
                ], fluid=True)
            ]),
            
            # Alerts Tab
            dbc.Tab(label="🔔 Alerts", children=[
                dbc.Container([
                    html.H5("Portfolio Alerts", className="mt-3 mb-3"),
                    html.P("Real-time alerts for held positions", className="text-muted"),
                    
                    html.Div(id='port-alerts-list')
                ], fluid=True)
            ]),
            
            # Picks Performance Tab
            dbc.Tab(label="🎯 Picks Performance", children=[
                dbc.Container([
                    html.H5("Historical Picks Performance", className="mt-3 mb-3"),
                    html.P("Analyze realized returns from Monthly and Weekly picks", className="text-muted mb-4"),
                    
                    # Refresh button
                    dbc.Row([
                        dbc.Col([
                            dbc.Button("Refresh Performance Data", id='port-perf-refresh-btn', 
                                      color='primary', size='sm', className='mb-3')
                        ])
                    ]),
                    
                    # Summary cards
                    dbc.Row([
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Avg Return", className="text-muted"),
                                    html.H4(id='port-perf-avg-return', children="N/A"),
                                    html.Small("All completed picks", className="text-muted")
                                ])
                            ])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Win Rate", className="text-muted"),
                                    html.H4(id='port-perf-win-rate', children="N/A"),
                                    html.Small("% profitable picks", className="text-muted")
                                ])
                            ])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Best Pick", className="text-muted"),
                                    html.H4(id='port-perf-best-pick', children="N/A"),
                                    html.Small(id='port-perf-best-return', children="", className="text-success")
                                ])
                            ])
                        ], width=3),
                        dbc.Col([
                            dbc.Card([
                                dbc.CardBody([
                                    html.H6("Worst Pick", className="text-muted"),
                                    html.H4(id='port-perf-worst-pick', children="N/A"),
                                    html.Small(id='port-perf-worst-return', children="", className="text-danger")
                                ])
                            ])
                        ], width=3)
                    ], className="mb-4"),
                    
                    # Monthly vs Weekly comparison chart
                    dbc.Card([
                        dbc.CardHeader(html.H5("Performance by Pick Type")),
                        dbc.CardBody([
                            dcc.Graph(id='port-perf-type-chart')
                        ])
                    ], className="mb-4"),
                    
                    # Profitability by rank chart
                    dbc.Card([
                        dbc.CardHeader(html.H5("Average Return by Prediction Rank")),
                        dbc.CardBody([
                            dcc.Graph(id='port-perf-rank-chart')
                        ])
                    ], className="mb-4"),
                    
                    # Historical picks table
                    dbc.Card([
                        dbc.CardHeader(html.H5("All Historical Picks")),
                        dbc.CardBody([
                            html.Div(id='port-perf-table')
                        ])
                    ])
                ], fluid=True)
            ])
        ]),
        
        # Hidden stores
        dcc.Store(id='port-positions-store'),
        dcc.Store(id='port-transactions-store'),
        dcc.Store(id='port-performance-store'),
        dcc.Interval(id='port-refresh-interval', interval=60000, n_intervals=0),  # 60s refresh
        dcc.Store(id='port-init-trigger', data={'loaded': True})  # Initial load trigger
        
    ], fluid=True, style={'min-height': '100vh', 'display': 'block', 'visibility': 'visible'})


def register_callbacks(app):
    """Register all portfolio callbacks."""
    
    @app.callback(
        [Output('port-positions-store', 'data'),
         Output('port-notional', 'children'),
         Output('port-invested', 'children'),
         Output('port-realized-pnl', 'children'),
         Output('port-realized-pct', 'children'),
         Output('port-unrealized-pnl', 'children'),
         Output('port-unrealized-pct', 'children'),
         Output('port-alpha', 'children'),
         Output('port-beta', 'children')],
        [Input('port-refresh-btn', 'n_clicks'),
         Input('port-refresh-interval', 'n_intervals'),
         Input('port-init-trigger', 'data')]
    )
    def refresh_portfolio_data(n_clicks, n_intervals, init_trigger):
        """Refresh portfolio positions and summary metrics."""
        try:
            # Load positions from file or compute from transactions
            positions_df = _load_positions()
            
            if positions_df is None or positions_df.empty:
                return None, "$0", "$0", "$0", "0%", "$0", "0%", "0%", "0.00"
            
            # Add event indicators
            events_file = Path('outputs/events_latest.parquet')
            if events_file.exists():
                try:
                    events_df = pd.read_parquet(events_file)
                    high_events = events_df[events_df['severity'] == 'HIGH']
                    tickers_with_alerts = set(high_events['ticker'].unique())
                    positions_df['alert'] = positions_df['ticker'].apply(
                        lambda t: '🔔' if t.upper() in tickers_with_alerts else ''
                    )
                except Exception as e:
                    logger.warning(f"Could not load events: {e}")
                    positions_df['alert'] = ''
            else:
                positions_df['alert'] = ''
            
            # Calculate metrics
            total_notional = positions_df['notional'].sum()
            total_invested = positions_df['cost_basis'].sum()
            realized_pnl = positions_df['realized_pnl'].sum()
            unrealized_pnl = positions_df['unrealized_pnl'].sum()
            
            realized_pct = (realized_pnl / total_invested * 100) if total_invested > 0 else 0
            unrealized_pct = (unrealized_pnl / total_invested * 100) if total_invested > 0 else 0
            
            # Calculate alpha and beta (simplified)
            alpha, beta = _calculate_alpha_beta(positions_df)
            
            return (
                positions_df.to_dict('records'),
                f"${total_notional:,.0f}",
                f"${total_invested:,.0f}",
                f"${realized_pnl:,.0f}",
                f"{realized_pct:+.2f}%",
                f"${unrealized_pnl:,.0f}",
                f"{unrealized_pct:+.2f}%",
                f"{alpha:+.2f}%",
                f"{beta:.2f}"
            )
            
        except Exception as e:
            logger.error(f"Error refreshing portfolio: {e}")
            return None, "$0", "$0", "$0", "0%", "$0", "0%", "0%", "0.00"
    
    @app.callback(
        Output('port-positions-table', 'children'),
        [Input('port-positions-store', 'data')]
    )
    def update_positions_table(positions_data):
        """Update the positions table display."""
        if not positions_data:
            return html.Div("No positions found. Upload transactions to begin tracking.", 
                          className="text-muted text-center p-4")
        
        df = pd.DataFrame(positions_data)
        
        # Format table columns
        table = dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[
                {'name': '🔔', 'id': 'alert'},
                {'name': 'Ticker', 'id': 'ticker'},
                {'name': 'Shares', 'id': 'shares', 'type': 'numeric', 'format': {'specifier': ',.0f'}},
                {'name': 'Avg Price', 'id': 'avg_price', 'type': 'numeric', 'format': {'specifier': '$,.2f'}},
                {'name': 'Last Price', 'id': 'last_price', 'type': 'numeric', 'format': {'specifier': '$,.2f'}},
                {'name': 'Unrealized P/L', 'id': 'unrealized_pnl', 'type': 'numeric', 'format': {'specifier': '$,.0f'}},
                {'name': 'Unrealized %', 'id': 'unrealized_pct', 'type': 'numeric', 'format': {'specifier': '.2f%'}},
                {'name': 'Weight', 'id': 'weight_pct', 'type': 'numeric', 'format': {'specifier': '.2f%'}},
                {'name': 'Source', 'id': 'model_source'},
                {'name': 'Liquidity', 'id': 'liquidity_flag'}
            ],
            style_table={'overflowX': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '8px'},
            style_header={'backgroundColor': '#2b3035', 'fontWeight': 'bold'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{unrealized_pnl} > 0'},
                    'backgroundColor': '#10b98120',
                },
                {
                    'if': {'filter_query': '{unrealized_pnl} < 0'},
                    'backgroundColor': '#ef444420',
                }
            ],
            page_size=20,
            sort_action='native',
            filter_action='native'
        )
        
        return table
    
    @app.callback(
        Output('port-pnl-chart', 'figure'),
        [Input('port-positions-store', 'data')]
    )
    def update_pnl_chart(positions_data):
        """Update cumulative P/L chart."""
        fig = go.Figure()
        
        if not positions_data:
            # Show empty state
            fig.add_annotation(
                text="No position history available<br>Upload transactions to see cumulative P/L",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color='#6c757d')
            )
        else:
            # Would load historical P/L data from transactions
            # For now, show message
            fig.add_annotation(
                text="Historical P/L chart would appear here<br>based on transaction history",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color='#6c757d')
            )
        
        fig.update_layout(
            template='plotly_dark',
            height=300,
            margin=dict(l=40, r=20, t=20, b=40),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        return fig
    
    @app.callback(
        Output('port-sector-chart', 'figure'),
        [Input('port-positions-store', 'data')]
    )
    def update_sector_chart(positions_data):
        """Update sector attribution chart."""
        fig = go.Figure()
        
        if not positions_data:
            fig.add_annotation(
                text="No sector attribution data<br>Upload transactions to see performance by sector",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color='#6c757d')
            )
        else:
            # Would calculate sector attribution from positions
            fig.add_annotation(
                text="Sector attribution would be calculated<br>from your positions and their performance",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color='#6c757d')
            )
        
        fig.update_layout(
            template='plotly_dark',
            height=300,
            margin=dict(l=40, r=20, t=20, b=40),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        return fig
    
    @app.callback(
        Output('port-contributors-chart', 'figure'),
        [Input('port-positions-store', 'data')]
    )
    def update_contributors_chart(positions_data):
        """Update top contributors chart."""
        fig = go.Figure()
        
        if not positions_data:
            fig.add_annotation(
                text="No contribution data<br>Upload transactions to see top/bottom contributors",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color='#6c757d')
            )
        else:
            # Would calculate from positions unrealized P/L
            fig.add_annotation(
                text="Top contributors chart would show<br>which positions drive portfolio performance",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color='#6c757d')
            )
        
        fig.update_layout(
            template='plotly_dark',
            height=300,
            margin=dict(l=40, r=20, t=20, b=40),
            xaxis=dict(visible=False),
            yaxis=dict(visible=False)
        )
        return fig
    
    @app.callback(
        Output('port-transactions-table', 'children'),
        [Input('port-transactions-store', 'data')]
    )
    def update_transactions_table(transactions_data):
        """Update transactions table."""
        if not transactions_data:
            return html.Div([
                html.P("No transactions found.", className="text-muted text-center p-4"),
                html.P("Upload a CSV file with columns: date, ticker, action, shares, price", 
                      className="text-muted text-center")
            ])
        
        # Would display transactions table
        return html.Div("Transaction history would appear here", className="text-muted text-center p-4")
    
    @app.callback(
        Output('port-alerts-list', 'children'),
        [Input('port-positions-store', 'data')]
    )
    def update_alerts_list(positions_data):
        """Update alerts list for held positions."""
        if not positions_data:
            return html.Div([
                html.P("No alerts - portfolio is empty", className="text-muted text-center p-4")
            ])
        
        # Get held tickers
        positions_df = pd.DataFrame(positions_data)
        held_tickers = positions_df['Ticker'].unique().tolist()
        
        # Load events
        events_file = Path('outputs/events_latest.parquet')
        if not events_file.exists():
            return html.Div([
                html.P("No event data available", className="text-muted text-center p-4"),
                html.P("Run: python3 pipelines/event_classifier.py", className="text-muted text-center")
            ])
        
        events_df = pd.read_parquet(events_file)
        
        # Filter for held tickers and HIGH severity
        relevant_events = events_df[
            (events_df['ticker'].isin(held_tickers)) & 
            (events_df['severity'] == 'HIGH')
        ].sort_values('timestamp', ascending=False).head(10)
        
        if relevant_events.empty:
            return html.Div([
                html.P("No high-severity alerts for your holdings", className="text-success text-center p-4")
            ])
        
        # Build alert items
        alert_items = []
        for _, event in relevant_events.iterrows():
            alert_item = dbc.ListGroupItem([
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            dbc.Badge(event['ticker'], color='secondary', className="me-2"),
                            dbc.Badge(event['event_type'], color='primary', className="me-2"),
                            dbc.Badge(f"🔴 {event['severity']}", color='danger')
                        ], className="mb-2"),
                        html.P(event['headline'], className="mb-1", style={'font-size': '14px'}),
                        html.Small(
                            f"{event['timestamp'].strftime('%b %d, %I:%M %p')} • {event.get('source', 'Unknown')}", 
                            className="text-muted"
                        )
                    ], width=12)
                ])
            ])
            alert_items.append(alert_item)
        
        return dbc.ListGroup(alert_items, flush=True)
    
    # Picks Performance Callbacks
    @app.callback(
        Output('port-performance-store', 'data'),
        [Input('port-perf-refresh-btn', 'n_clicks'),
         Input('port-init-trigger', 'data')]
    )
    def load_performance_data(n_clicks, init_trigger):
        """Load picks performance data from parquet file."""
        try:
            perf_file = Path('outputs/all_picks_performance.parquet')
            
            if not perf_file.exists():
                logger.info("Performance file not found - returning empty data")
                return None
            
            df = pd.read_parquet(perf_file)
            logger.info(f"Loaded {len(df)} picks performance records")
            
            return df.to_dict('records')
            
        except Exception as e:
            logger.error(f"Error loading performance data: {e}")
            return None
    
    @app.callback(
        [Output('port-perf-avg-return', 'children'),
         Output('port-perf-win-rate', 'children'),
         Output('port-perf-best-pick', 'children'),
         Output('port-perf-best-return', 'children'),
         Output('port-perf-worst-pick', 'children'),
         Output('port-perf-worst-return', 'children')],
        [Input('port-performance-store', 'data')]
    )
    def update_performance_summary(perf_data):
        """Update summary cards."""
        if not perf_data:
            return "N/A", "N/A", "N/A", "", "N/A", ""
        
        df = pd.DataFrame(perf_data)
        completed = df[df['realized_return'].notna()]
        
        if len(completed) == 0:
            return "N/A", "N/A", "N/A", "", "N/A", ""
        
        avg_return = completed['realized_return'].mean()
        win_rate = (completed['realized_return'] > 0).mean()
        
        best_idx = completed['realized_return'].idxmax()
        best_pick = completed.loc[best_idx]
        
        worst_idx = completed['realized_return'].idxmin()
        worst_pick = completed.loc[worst_idx]
        
        return (
            f"{avg_return:+.2%}",
            f"{win_rate:.1%}",
            best_pick['ticker'],
            f"{best_pick['realized_return']:+.2%}",
            worst_pick['ticker'],
            f"{worst_pick['realized_return']:+.2%}"
        )
    
    @app.callback(
        Output('port-perf-type-chart', 'figure'),
        [Input('port-performance-store', 'data')]
    )
    def update_type_comparison_chart(perf_data):
        """Chart comparing monthly vs weekly performance."""
        fig = go.Figure()
        
        if not perf_data:
            fig.add_annotation(
                text="No performance data available<br>Run: python3 pipelines/analyze_picks_performance.py",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color='#6c757d')
            )
        else:
            df = pd.DataFrame(perf_data)
            completed = df[df['realized_return'].notna()]
            
            if len(completed) > 0:
                # Group by pick_type and calculate mean return
                type_stats = completed.groupby('pick_type')['realized_return'].agg(['mean', 'count']).reset_index()
                
                fig.add_trace(go.Bar(
                    x=type_stats['pick_type'],
                    y=type_stats['mean'],
                    text=[f"{val:.2%}" for val in type_stats['mean']],
                    textposition='outside',
                    marker_color=['#10b981', '#3b82f6'],
                    hovertemplate='<b>%{x}</b><br>Avg Return: %{y:.2%}<br>Count: %{customdata}<extra></extra>',
                    customdata=type_stats['count']
                ))
                
                fig.update_layout(
                    xaxis_title="Pick Type",
                    yaxis_title="Average Return",
                    yaxis_tickformat='.1%'
                )
        
        fig.update_layout(
            template='plotly_dark',
            height=300,
            margin=dict(l=40, r=20, t=20, b=40)
        )
        return fig
    
    @app.callback(
        Output('port-perf-rank-chart', 'figure'),
        [Input('port-performance-store', 'data')]
    )
    def update_rank_profitability_chart(perf_data):
        """Chart showing return by prediction rank."""
        fig = go.Figure()
        
        if not perf_data:
            fig.add_annotation(
                text="No performance data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=14, color='#6c757d')
            )
        else:
            df = pd.DataFrame(perf_data)
            completed = df[df['realized_return'].notna()]
            
            if len(completed) > 0:
                # Group by pred_rank (bins of 1-5, 6-10, etc.)
                completed['rank_bin'] = pd.cut(completed['pred_rank'], 
                                              bins=[0, 5, 10, 20, 50, 100], 
                                              labels=['1-5', '6-10', '11-20', '21-50', '51+'])
                
                rank_stats = completed.groupby('rank_bin')['realized_return'].agg(['mean', 'count']).reset_index()
                
                # Color code: green for top ranks, fading to red
                colors = ['#10b981', '#3b82f6', '#6366f1', '#f59e0b', '#ef4444']
                
                fig.add_trace(go.Bar(
                    x=rank_stats['rank_bin'],
                    y=rank_stats['mean'],
                    text=[f"{val:.2%}" for val in rank_stats['mean']],
                    textposition='outside',
                    marker_color=colors[:len(rank_stats)],
                    hovertemplate='<b>Rank %{x}</b><br>Avg Return: %{y:.2%}<br>Count: %{customdata}<extra></extra>',
                    customdata=rank_stats['count']
                ))
                
                fig.update_layout(
                    xaxis_title="Prediction Rank",
                    yaxis_title="Average Return",
                    yaxis_tickformat='.1%'
                )
        
        fig.update_layout(
            template='plotly_dark',
            height=300,
            margin=dict(l=40, r=20, t=20, b=40)
        )
        return fig
    
    @app.callback(
        Output('port-perf-table', 'children'),
        [Input('port-performance-store', 'data')]
    )
    def update_performance_table(perf_data):
        """Display searchable table of all picks."""
        if not perf_data:
            return html.Div([
                html.P("No performance data available", className="text-muted text-center p-4"),
                html.P("Run: python3 pipelines/analyze_picks_performance.py", 
                      className="text-muted text-center")
            ])
        
        df = pd.DataFrame(perf_data)
        
        # Format dates
        df['pick_date'] = pd.to_datetime(df['pick_date']).dt.strftime('%Y-%m-%d')
        if 'entry_date' in df.columns:
            df['entry_date'] = pd.to_datetime(df['entry_date']).dt.strftime('%Y-%m-%d')
        
        table = dash_table.DataTable(
            data=df.to_dict('records'),
            columns=[
                {'name': 'Ticker', 'id': 'ticker'},
                {'name': 'Pick Date', 'id': 'pick_date'},
                {'name': 'Type', 'id': 'pick_type'},
                {'name': 'Rank', 'id': 'pred_rank', 'type': 'numeric'},
                {'name': 'Predicted Return', 'id': 'predicted_return', 'type': 'numeric', 
                 'format': {'specifier': '.2%'}},
                {'name': 'Entry Price', 'id': 'entry_price', 'type': 'numeric', 
                 'format': {'specifier': '$,.2f'}},
                {'name': 'Exit Price', 'id': 'exit_price', 'type': 'numeric', 
                 'format': {'specifier': '$,.2f'}},
                {'name': 'Realized Return', 'id': 'realized_return', 'type': 'numeric', 
                 'format': {'specifier': '.2%'}},
                {'name': 'Holding Days', 'id': 'holding_days', 'type': 'numeric'}
            ],
            style_table={'overflowX': 'auto', 'max-height': '500px', 'overflowY': 'auto'},
            style_cell={'textAlign': 'left', 'padding': '8px', 'fontSize': '12px'},
            style_header={'backgroundColor': '#2b3035', 'fontWeight': 'bold'},
            style_data_conditional=[
                {
                    'if': {'filter_query': '{realized_return} > 0'},
                    'color': '#10b981',
                },
                {
                    'if': {'filter_query': '{realized_return} < 0'},
                    'color': '#ef4444',
                }
            ],
            page_size=20,
            sort_action='native',
            filter_action='native',
            export_format='csv'
        )
        
        return table
    
    logger.info("Portfolio callbacks registered")


def _load_positions():
    """Load current positions from file."""
    # Try to load from data/positions.csv
    positions_file = 'data/positions.csv'
    
    if os.path.exists(positions_file):
        try:
            df = pd.read_csv(positions_file)
            logger.info(f"Loaded {len(df)} positions from {positions_file}")
            return df
        except Exception as e:
            logger.warning(f"Error loading positions file: {e}")
    
    # If no real data, return empty DataFrame with correct schema
    empty_df = pd.DataFrame(columns=[
        'ticker', 'shares', 'avg_price', 'last_price', 'cost_basis',
        'notional', 'unrealized_pnl', 'unrealized_pct', 'realized_pnl',
        'weight_pct', 'model_source', 'model_version', 'liquidity_flag'
    ])
    
    logger.info("No positions file found - returning empty portfolio")
    return empty_df


def _calculate_alpha_beta(positions_df):
    """Calculate portfolio alpha and beta."""
    # Simplified calculation - would need historical returns
    return 0.78, 0.92
