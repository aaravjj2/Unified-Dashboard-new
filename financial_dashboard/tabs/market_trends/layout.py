"""
Market Trends Layout - Phase 1 Macro Dashboard

Contains Dash components for OpenBB macro data integration.
Includes GDP, CPI, and Unemployment visualizations.

Author: Agent-P1
Date: 2025-12-28
"""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def create_macro_indicator_card(
    indicator_id: str,
    title: str,
    icon: str,
    description: str
) -> dbc.Card:
    """
    Create a card for a single macro indicator.
    
    Args:
        indicator_id: ID for the graph component
        title: Card title
        icon: FontAwesome icon class
        description: Card description
        
    Returns:
        dbc.Card component
    """
    return dbc.Card([
        dbc.CardHeader([
            html.H6([
                html.I(className=f"{icon} me-2"),
                title
            ], className="mb-0"),
            html.Small(description, className="text-muted")
        ]),
        dbc.CardBody([
            dcc.Loading(
                type="circle",
                children=[
                    dcc.Graph(
                        id=indicator_id,
                        config={'displayModeBar': False},
                        style={'height': '250px'}
                    )
                ]
            )
        ], className="p-2")
    ], className="h-100 shadow-sm")


def create_macro_dashboard_tab() -> dbc.Tab:
    """
    Create the Macro Dashboard tab content.
    
    Returns:
        dbc.Tab containing macro dashboard
    """
    return dbc.Tab(
        label="Macro Dashboard",
        tab_id="tab-macro",
        children=[
            html.Div([
                # Header
                dbc.Row([
                    dbc.Col([
                        html.H5([
                            html.I(className="fas fa-globe me-2"),
                            "Macro Economic Dashboard"
                        ], className="mb-1"),
                        html.P(
                            "Key economic indicators powered by OpenBB",
                            className="text-muted small mb-3"
                        )
                    ], md=8),
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="fas fa-sync-alt me-2"), "Refresh Data"],
                            id="btn-refresh-macro",
                            color="outline-primary",
                            size="sm",
                            className="float-end"
                        )
                    ], md=4)
                ]),
                
                # Main Indicators Row
                dbc.Row([
                    dbc.Col([
                        create_macro_indicator_card(
                            "graph-gdp",
                            "GDP Growth",
                            "fas fa-chart-line",
                            "Quarterly GDP Growth Rate"
                        )
                    ], md=4),
                    dbc.Col([
                        create_macro_indicator_card(
                            "graph-cpi",
                            "CPI Inflation",
                            "fas fa-percentage",
                            "Year-over-Year Inflation"
                        )
                    ], md=4),
                    dbc.Col([
                        create_macro_indicator_card(
                            "graph-unemployment",
                            "Unemployment",
                            "fas fa-users",
                            "Civilian Unemployment Rate"
                        )
                    ], md=4),
                ], className="g-3 mb-4"),
                
                # Correlation Analysis
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.H6([
                                    html.I(className="fas fa-project-diagram me-2"),
                                    "Macro vs. Market Correlation"
                                ], className="mb-0")
                            ]),
                            dbc.CardBody([
                                dcc.Loading(
                                    type="circle",
                                    children=[
                                        dcc.Graph(
                                            id="graph-macro-correlation",
                                            config={'displayModeBar': True, 'displaylogo': False},
                                            style={'height': '300px'}
                                        )
                                    ]
                                )
                            ])
                        ], className="shadow-sm")
                    ])
                ]),
                
                # Store for macro data
                dcc.Store(id="store-macro-data"),
                
            ], className="p-3")
        ]
    )


def create_gdp_figure(data: Dict[str, Any]) -> go.Figure:
    """
    Create GDP growth chart.
    
    Args:
        data: MacroDataResult as dict
        
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    if not data.get('dates') or not data.get('values'):
        fig.add_annotation(
            text="No GDP data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color='gray')
        )
        _apply_dark_theme(fig)
        return fig
    
    values = data['values']
    dates = data['dates']
    
    # Color bars based on positive/negative
    colors = ['#28a745' if v >= 0 else '#dc3545' for v in values]
    
    fig.add_trace(go.Bar(
        x=dates,
        y=values,
        marker_color=colors,
        name='GDP Growth',
        hovertemplate='%{x}<br>Growth: %{y:.2f}%<extra></extra>'
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="dash", line_color="gray", line_width=1)
    
    # Add trend line
    if len(values) > 3:
        import numpy as np
        z = np.polyfit(range(len(values)), values, 1)
        p = np.poly1d(z)
        fig.add_trace(go.Scatter(
            x=dates,
            y=[p(i) for i in range(len(dates))],
            mode='lines',
            name='Trend',
            line=dict(color='yellow', dash='dot', width=2)
        ))
    
    fig.update_layout(
        title=dict(text=f"GDP Growth ({data.get('country', 'USA')})", font=dict(size=12)),
        xaxis_title="",
        yaxis_title="Growth Rate (%)",
        showlegend=False,
        margin=dict(l=40, r=20, t=40, b=30)
    )
    
    _apply_dark_theme(fig)
    return fig


def create_cpi_figure(data: Dict[str, Any]) -> go.Figure:
    """
    Create CPI inflation chart.
    
    Args:
        data: MacroDataResult as dict
        
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    if not data.get('dates') or not data.get('values'):
        fig.add_annotation(
            text="No CPI data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color='gray')
        )
        _apply_dark_theme(fig)
        return fig
    
    values = data['values']
    dates = data['dates']
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode='lines+markers',
        name='CPI',
        line=dict(color='#ffc107', width=2),
        marker=dict(size=4),
        fill='tozeroy',
        fillcolor='rgba(255, 193, 7, 0.2)',
        hovertemplate='%{x}<br>Inflation: %{y:.2f}%<extra></extra>'
    ))
    
    # Add Fed target line (2%)
    fig.add_hline(
        y=2.0,
        line_dash="dash",
        line_color="red",
        line_width=1,
        annotation_text="Fed Target (2%)",
        annotation_position="bottom right"
    )
    
    fig.update_layout(
        title=dict(text=f"CPI Inflation ({data.get('country', 'USA')})", font=dict(size=12)),
        xaxis_title="",
        yaxis_title="YoY Change (%)",
        showlegend=False,
        margin=dict(l=40, r=20, t=40, b=30)
    )
    
    _apply_dark_theme(fig)
    return fig


def create_unemployment_figure(data: Dict[str, Any]) -> go.Figure:
    """
    Create unemployment rate chart.
    
    Args:
        data: MacroDataResult as dict
        
    Returns:
        Plotly Figure
    """
    fig = go.Figure()
    
    if not data.get('dates') or not data.get('values'):
        fig.add_annotation(
            text="No unemployment data available",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=14, color='gray')
        )
        _apply_dark_theme(fig)
        return fig
    
    values = data['values']
    dates = data['dates']
    
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode='lines+markers',
        name='Unemployment',
        line=dict(color='#17a2b8', width=2),
        marker=dict(size=4),
        fill='tozeroy',
        fillcolor='rgba(23, 162, 184, 0.2)',
        hovertemplate='%{x}<br>Rate: %{y:.2f}%<extra></extra>'
    ))
    
    # Add natural rate reference (4%)
    fig.add_hline(
        y=4.0,
        line_dash="dash",
        line_color="green",
        line_width=1,
        annotation_text="Natural Rate (~4%)",
        annotation_position="bottom right"
    )
    
    fig.update_layout(
        title=dict(text=f"Unemployment Rate ({data.get('country', 'USA')})", font=dict(size=12)),
        xaxis_title="",
        yaxis_title="Rate (%)",
        showlegend=False,
        margin=dict(l=40, r=20, t=40, b=30)
    )
    
    _apply_dark_theme(fig)
    return fig


def create_correlation_figure(macro_data: Dict[str, Any]) -> go.Figure:
    """
    Create macro vs market correlation heatmap.
    
    Args:
        macro_data: Dict with all macro indicators
        
    Returns:
        Plotly Figure
    """
    import numpy as np
    
    # Generate correlation matrix (simulated for demo)
    indicators = ['GDP', 'CPI', 'Unemployment', 'S&P 500']
    n = len(indicators)
    
    np.random.seed(46)
    
    # Typical correlations:
    # GDP vs S&P: positive (~0.4)
    # CPI vs S&P: negative (~-0.2)
    # Unemployment vs S&P: negative (~-0.5)
    corr_matrix = np.array([
        [1.0,  0.2, -0.3,  0.4],   # GDP
        [0.2,  1.0, -0.1, -0.2],   # CPI
        [-0.3, -0.1, 1.0, -0.5],   # Unemployment
        [0.4, -0.2, -0.5,  1.0]    # S&P 500
    ])
    
    # Add some noise
    noise = np.random.randn(n, n) * 0.1
    corr_matrix = corr_matrix + noise
    corr_matrix = (corr_matrix + corr_matrix.T) / 2  # Symmetrize
    np.fill_diagonal(corr_matrix, 1.0)
    corr_matrix = np.clip(corr_matrix, -1, 1)
    
    fig = go.Figure(data=go.Heatmap(
        z=corr_matrix,
        x=indicators,
        y=indicators,
        colorscale='RdBu_r',
        zmin=-1,
        zmax=1,
        text=np.round(corr_matrix, 2),
        texttemplate='%{text}',
        textfont=dict(size=12),
        hovertemplate='%{x} vs %{y}<br>Correlation: %{z:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text="Indicator Correlations", font=dict(size=12)),
        margin=dict(l=60, r=20, t=40, b=60),
        xaxis=dict(side='bottom'),
        yaxis=dict(autorange='reversed')
    )
    
    _apply_dark_theme(fig)
    return fig


def _apply_dark_theme(fig: go.Figure) -> None:
    """Apply dark theme to figure."""
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='white'),
        xaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
        yaxis=dict(gridcolor='rgba(128,128,128,0.2)')
    )


def create_empty_figure(message: str = "Loading...") -> go.Figure:
    """Create empty placeholder figure."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5, showarrow=False,
        font=dict(size=14, color='gray')
    )
    _apply_dark_theme(fig)
    fig.update_layout(
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
    Get complete Market Trends layout with Macro Dashboard.
    
    Returns:
        Dash HTML Div containing full layout
    """
    return html.Div([
        # Header
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="fas fa-chart-area me-3"),
                    "Market Trends"
                ], className="mb-1"),
                html.P(
                    "Market analysis with macro economic indicators",
                    className="text-muted mb-0"
                )
            ])
        ], className="mb-4"),
        
        # Tabs
        dbc.Tabs([
            # Macro Dashboard Tab
            create_macro_dashboard_tab(),
            
            # Placeholder for other tabs
            dbc.Tab(
                label="Technical Analysis",
                tab_id="tab-technical",
                children=[
                    html.Div([
                        html.P("Technical analysis content here", className="text-muted p-3")
                    ])
                ]
            ),
        ], id="tabs-market-trends", active_tab="tab-macro"),
        
    ], className="p-3")


# =============================================================================
# Callbacks
# =============================================================================

def register_callbacks(app):
    """
    Register Market Trends callbacks with Dash app.
    
    Args:
        app: Dash application instance
    """
    
    @app.callback(
        [
            Output("graph-gdp", "figure"),
            Output("graph-cpi", "figure"),
            Output("graph-unemployment", "figure"),
            Output("graph-macro-correlation", "figure"),
            Output("store-macro-data", "data")
        ],
        [
            Input("tabs-market-trends", "active_tab"),
            Input("btn-refresh-macro", "n_clicks")
        ],
        prevent_initial_call=False
    )
    def update_macro_dashboard(active_tab, refresh_clicks):
        """Load and display macro data when tab is active."""
        
        # Only load if macro tab is active
        if active_tab != "tab-macro":
            return [
                create_empty_figure("Select Macro Dashboard tab"),
                create_empty_figure(""),
                create_empty_figure(""),
                create_empty_figure(""),
                None
            ]
        
        try:
            from financial_dashboard.tabs.market_trends.macro_loader import MacroDataLoader
            
            loader = MacroDataLoader(country='USA')
            
            # Fetch all indicators
            gdp_result = loader.get_gdp()
            cpi_result = loader.get_cpi()
            unemployment_result = loader.get_unemployment()
            
            # Convert to dicts for figures
            gdp_data = {
                'dates': gdp_result.dates,
                'values': gdp_result.values,
                'country': gdp_result.country
            }
            cpi_data = {
                'dates': cpi_result.dates,
                'values': cpi_result.values,
                'country': cpi_result.country
            }
            unemployment_data = {
                'dates': unemployment_result.dates,
                'values': unemployment_result.values,
                'country': unemployment_result.country
            }
            
            # Create figures
            gdp_fig = create_gdp_figure(gdp_data)
            cpi_fig = create_cpi_figure(cpi_data)
            unemployment_fig = create_unemployment_figure(unemployment_data)
            correlation_fig = create_correlation_figure({})
            
            # Store data
            store_data = {
                'gdp': gdp_data,
                'cpi': cpi_data,
                'unemployment': unemployment_data,
                'last_updated': gdp_result.last_updated
            }
            
            logger.info("Macro dashboard updated successfully")
            return [gdp_fig, cpi_fig, unemployment_fig, correlation_fig, store_data]
            
        except Exception as e:
            logger.error(f"Macro dashboard error: {e}")
            return [
                create_empty_figure(f"Error loading GDP: {str(e)[:30]}"),
                create_empty_figure("Error loading CPI"),
                create_empty_figure("Error loading Unemployment"),
                create_empty_figure("Error"),
                None
            ]


# Export
__all__ = ['get_layout', 'register_callbacks', 'create_macro_dashboard_tab']
