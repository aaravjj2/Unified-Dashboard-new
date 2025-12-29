"""
Portfolio Tracker Layout - Phase 1 Risk Optimization UI

Contains Dash components for Riskfolio-Lib integration.
Includes Risk Optimization card with efficient frontier visualization.

Author: Agent-P1
Date: 2025-12-28
"""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Default tickers for portfolio optimization
DEFAULT_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']


def create_risk_optimization_card() -> dbc.Card:
    """
    Create the Risk Optimization card component.
    
    Contains:
    - Ticker input
    - Risk measure dropdown (CDaR/EVaR)
    - Optimize button
    - Results display
    - Efficient frontier graph
    """
    return dbc.Card([
        dbc.CardHeader([
            html.H5([
                html.I(className="fas fa-chart-pie me-2"),
                "Tail-Risk Portfolio Optimizer"
            ], className="mb-0 d-flex align-items-center"),
            html.Small("Powered by Riskfolio-Lib", className="text-muted")
        ]),
        dbc.CardBody([
            # Input Row
            dbc.Row([
                # Ticker Input
                dbc.Col([
                    dbc.Label("Tickers (comma-separated)", className="fw-bold"),
                    dbc.Input(
                        id="input-tickers-risk",
                        type="text",
                        value=",".join(DEFAULT_TICKERS),
                        placeholder="AAPL,MSFT,GOOGL...",
                        className="mb-2"
                    ),
                ], md=6),
                
                # Risk Measure Dropdown
                dbc.Col([
                    dbc.Label("Risk Measure", className="fw-bold"),
                    dcc.Dropdown(
                        id="dropdown-risk-measure",
                        options=[
                            {'label': 'CDaR (Conditional Drawdown at Risk)', 'value': 'CDaR'},
                            {'label': 'EVaR (Entropic Value at Risk)', 'value': 'EVaR'},
                            {'label': 'CVaR (Conditional Value at Risk)', 'value': 'CVaR'},
                            {'label': 'Mean-Variance (Standard Dev)', 'value': 'MV'},
                        ],
                        value='CDaR',
                        clearable=False,
                        className="mb-2"
                    ),
                ], md=4),
                
                # Optimize Button
                dbc.Col([
                    dbc.Label(" ", className="fw-bold d-block"),  # Spacer
                    dbc.Button(
                        [html.I(className="fas fa-cogs me-2"), "Optimize"],
                        id="btn-optimize-risk",
                        color="primary",
                        className="w-100"
                    ),
                ], md=2),
            ], className="mb-3"),
            
            # Loading indicator
            dcc.Loading(
                id="loading-optimization",
                type="circle",
                children=[
                    # Results Container
                    html.Div(id="div-optimization-results", className="mb-3"),
                    
                    # Efficient Frontier Graph
                    dcc.Graph(
                        id="graph-efficient-frontier",
                        config={'displayModeBar': True, 'displaylogo': False},
                        style={'height': '450px'}
                    ),
                ]
            ),
            
            # Weights Table
            html.Div(id="div-weights-table", className="mt-3"),
        ])
    ], className="shadow-sm mb-4")


def create_optimization_results_display(result: Dict[str, Any]) -> html.Div:
    """
    Create results display from optimization result.
    
    Args:
        result: OptimizationResult as dict
        
    Returns:
        Dash HTML component
    """
    if not result.get('success', False):
        return dbc.Alert([
            html.I(className="fas fa-exclamation-triangle me-2"),
            f"Optimization failed: {result.get('error_message', 'Unknown error')}"
        ], color="warning")
    
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Expected Return", className="text-muted mb-1"),
                    html.H4(f"{result['expected_return']*100:.2f}%", className="text-success mb-0")
                ])
            ], className="text-center")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6(f"{result['risk_measure']} Risk", className="text-muted mb-1"),
                    html.H4(f"{result['risk']*100:.2f}%", className="text-danger mb-0")
                ])
            ], className="text-center")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Sharpe Ratio", className="text-muted mb-1"),
                    html.H4(f"{result['sharpe_ratio']:.3f}", className="text-primary mb-0")
                ])
            ], className="text-center")
        ], md=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Optimization Time", className="text-muted mb-1"),
                    html.H4(f"{result['optimization_time']:.2f}s", className="text-info mb-0")
                ])
            ], className="text-center")
        ], md=3),
    ], className="g-2")


def create_weights_table(weights: Dict[str, float]) -> html.Div:
    """
    Create allocation weights table.
    
    Args:
        weights: Dict of ticker -> weight
        
    Returns:
        Dash HTML component with table
    """
    # Sort by weight descending
    sorted_weights = sorted(weights.items(), key=lambda x: x[1], reverse=True)
    
    rows = []
    for ticker, weight in sorted_weights:
        # Color bar width based on weight
        bar_width = f"{weight * 100:.1f}%"
        
        rows.append(
            html.Tr([
                html.Td(ticker, className="fw-bold"),
                html.Td(f"{weight*100:.2f}%", className="text-end"),
                html.Td([
                    html.Div(
                        style={
                            'width': bar_width,
                            'height': '20px',
                            'backgroundColor': '#0d6efd',
                            'borderRadius': '3px',
                            'minWidth': '5px'
                        }
                    )
                ], style={'width': '200px'})
            ])
        )
    
    return html.Div([
        html.H6([
            html.I(className="fas fa-balance-scale me-2"),
            "Optimal Allocation Weights"
        ], className="mb-3"),
        dbc.Table([
            html.Thead([
                html.Tr([
                    html.Th("Ticker"),
                    html.Th("Weight", className="text-end"),
                    html.Th("Allocation")
                ])
            ]),
            html.Tbody(rows)
        ], bordered=True, hover=True, size="sm", className="mb-0")
    ])


def create_efficient_frontier_figure(
    frontier_data: Dict[str, List[float]],
    optimal_point: Dict[str, float],
    risk_measure: str
) -> go.Figure:
    """
    Create Plotly figure for efficient frontier.
    
    Args:
        frontier_data: Dict with 'risk' and 'return' lists
        optimal_point: Dict with 'risk' and 'return' for optimal portfolio
        risk_measure: Risk measure name
        
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    # Efficient frontier line
    if frontier_data:
        fig.add_trace(go.Scatter(
            x=frontier_data.get('risk', []),
            y=frontier_data.get('return', []),
            mode='lines',
            name='Efficient Frontier',
            line=dict(color='#0d6efd', width=3),
            hovertemplate='Risk: %{x:.2%}<br>Return: %{y:.2%}<extra></extra>'
        ))
        
        # Sharpe ratio color scale
        if 'sharpe' in frontier_data:
            fig.add_trace(go.Scatter(
                x=frontier_data['risk'],
                y=frontier_data['return'],
                mode='markers',
                name='Sharpe Ratio',
                marker=dict(
                    size=8,
                    color=frontier_data['sharpe'],
                    colorscale='RdYlGn',
                    showscale=True,
                    colorbar=dict(title='Sharpe', x=1.02)
                ),
                hovertemplate='Risk: %{x:.2%}<br>Return: %{y:.2%}<br>Sharpe: %{marker.color:.3f}<extra></extra>'
            ))
    
    # Optimal portfolio point
    if optimal_point:
        fig.add_trace(go.Scatter(
            x=[optimal_point.get('risk', 0)],
            y=[optimal_point.get('return', 0)],
            mode='markers',
            name='Optimal Portfolio',
            marker=dict(
                size=20,
                color='#dc3545',
                symbol='star',
                line=dict(color='white', width=2)
            ),
            hovertemplate='<b>OPTIMAL</b><br>Risk: %{x:.2%}<br>Return: %{y:.2%}<extra></extra>'
        ))
    
    # Layout
    fig.update_layout(
        title=dict(
            text=f'Efficient Frontier ({risk_measure})',
            font=dict(size=16)
        ),
        xaxis=dict(
            title=f'{risk_measure} Risk',
            tickformat='.1%',
            gridcolor='rgba(128,128,128,0.2)'
        ),
        yaxis=dict(
            title='Expected Annual Return',
            tickformat='.1%',
            gridcolor='rgba(128,128,128,0.2)'
        ),
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        margin=dict(l=60, r=80, t=60, b=60),
        hovermode='closest'
    )
    
    return fig


def create_empty_frontier_figure() -> go.Figure:
    """Create empty placeholder figure."""
    fig = go.Figure()
    fig.add_annotation(
        text="Click 'Optimize' to compute efficient frontier",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color='gray')
    )
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=20, r=20, t=20, b=20)
    )
    return fig


# =============================================================================
# Main Layout
# =============================================================================

def get_layout() -> html.Div:
    """
    Get complete Portfolio Tracker layout with Risk Optimization.
    
    Returns:
        Dash HTML Div containing full layout
    """
    return html.Div([
        # Header
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="fas fa-briefcase me-3"),
                    "Portfolio Tracker"
                ], className="mb-1"),
                html.P(
                    "Advanced portfolio analytics with tail-risk optimization",
                    className="text-muted mb-0"
                )
            ])
        ], className="mb-4"),
        
        # Risk Optimization Card
        create_risk_optimization_card(),
        
        # Store for optimization results
        dcc.Store(id="store-optimization-result"),
        
    ], className="p-3")


# =============================================================================
# Callbacks (to be registered with app)
# =============================================================================

def register_callbacks(app):
    """
    Register Portfolio Tracker callbacks with Dash app.
    
    Args:
        app: Dash application instance
    """
    
    @app.callback(
        [
            Output("store-optimization-result", "data"),
            Output("graph-efficient-frontier", "figure"),
            Output("div-optimization-results", "children"),
            Output("div-weights-table", "children")
        ],
        Input("btn-optimize-risk", "n_clicks"),
        [
            State("input-tickers-risk", "value"),
            State("dropdown-risk-measure", "value")
        ],
        prevent_initial_call=True
    )
    def run_optimization(n_clicks, tickers_str, risk_measure):
        """Run portfolio optimization on button click."""
        if not n_clicks:
            return dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
        # Parse tickers
        tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
        
        if len(tickers) < 2:
            return (
                None,
                create_empty_frontier_figure(),
                dbc.Alert("Please enter at least 2 tickers", color="warning"),
                None
            )
        
        try:
            # Import optimization engine
            from financial_dashboard.tabs.portfolio_tracker.optimization_engine import (
                RiskfolioOptimizer
            )
            
            # Run optimization
            optimizer = RiskfolioOptimizer(tickers, risk_measure)
            result = optimizer.optimize()
            
            # Compute frontier
            frontier_df = optimizer.compute_efficient_frontier(n_points=30)
            frontier_data = {
                'risk': frontier_df['risk'].tolist(),
                'return': frontier_df['return'].tolist(),
                'sharpe': frontier_df['sharpe'].tolist()
            }
            
            # Create optimal point
            optimal_point = {
                'risk': result.risk,
                'return': result.expected_return
            }
            
            # Create figure
            fig = create_efficient_frontier_figure(frontier_data, optimal_point, risk_measure)
            
            # Create results display
            results_display = create_optimization_results_display({
                'success': result.success,
                'expected_return': result.expected_return,
                'risk': result.risk,
                'sharpe_ratio': result.sharpe_ratio,
                'risk_measure': result.risk_measure,
                'optimization_time': result.optimization_time,
                'error_message': result.error_message
            })
            
            # Create weights table
            weights_table = create_weights_table(result.weights)
            
            # Store data
            store_data = {
                'weights': result.weights,
                'risk': result.risk,
                'expected_return': result.expected_return,
                'sharpe_ratio': result.sharpe_ratio,
                'risk_measure': result.risk_measure,
                'success': result.success
            }
            
            logger.info(f"Optimization complete: {risk_measure}, {len(tickers)} tickers")
            return store_data, fig, results_display, weights_table
            
        except Exception as e:
            logger.error(f"Optimization callback error: {e}")
            return (
                None,
                create_empty_frontier_figure(),
                dbc.Alert(f"Optimization error: {str(e)}", color="danger"),
                None
            )


# Export
__all__ = ['get_layout', 'register_callbacks', 'create_risk_optimization_card']
