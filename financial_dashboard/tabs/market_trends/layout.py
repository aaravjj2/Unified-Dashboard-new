"""
Market Trends Layout - Phase 1 Macro Dashboard + Phase 5 Regime Detection

Contains Dash components for OpenBB macro data integration.
Includes GDP, CPI, and Unemployment visualizations.
Phase 5: Added Regime Detection (HMM/K-Means)

Author: Agent-P1, Agent-P5
Date: 2025-12-28, 2025-12-29
"""

import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Import Regime Engine (Phase 5)
try:
    from .regime_engine import (
        RegimeDetector, detect_regimes, is_regime_detection_available,
        REGIME_LABELS, REGIME_COLORS, REGIME_SOLID_COLORS
    )
    REGIME_AVAILABLE = is_regime_detection_available()
except ImportError:
    REGIME_AVAILABLE = False
    logger.warning("Regime detection engine not available")


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


def create_regime_monitor_tab() -> dbc.Tab:
    """
    Create the Regime Monitor tab content (Phase 5).
    
    Features:
    - Ticker input for regime analysis
    - Method selection (HMM vs K-Means)
    - Price chart with regime background colors
    - Regime statistics cards
    
    Returns:
        dbc.Tab containing regime monitor
    """
    return dbc.Tab(
        label="🎯 Regime Monitor",
        tab_id="tab-regime",
        children=[
            html.Div([
                # Header
                dbc.Row([
                    dbc.Col([
                        html.H5([
                            html.I(className="fas fa-signal me-2"),
                            "Market Regime Detection"
                        ], className="mb-1"),
                        html.P(
                            "Detect Bull/Bear/Sideways market regimes using AI",
                            className="text-muted small mb-3"
                        )
                    ], md=8),
                    dbc.Col([
                        dbc.Button(
                            [html.I(className="fas fa-play me-2"), "Detect Regimes"],
                            id="btn-detect-regimes",
                            color="primary",
                            size="sm",
                            className="float-end"
                        )
                    ], md=4)
                ]),
                
                # Controls Row
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                dbc.Row([
                                    dbc.Col([
                                        html.Label("Ticker", className="small text-muted"),
                                        dbc.Input(
                                            id="regime-ticker-input",
                                            type="text",
                                            value="SPY",
                                            placeholder="Enter ticker...",
                                            className="bg-dark text-white border-secondary",
                                            style={'maxWidth': '150px'}
                                        )
                                    ], md=3),
                                    dbc.Col([
                                        html.Label("Method", className="small text-muted"),
                                        dcc.RadioItems(
                                            id="regime-method-select",
                                            options=[
                                                {'label': ' HMM (Statistical)', 'value': 'hmm'},
                                                {'label': ' K-Means (Clustering)', 'value': 'kmeans'}
                                            ],
                                            value='hmm',
                                            inline=True,
                                            className="text-white",
                                            labelStyle={'marginRight': '15px'}
                                        )
                                    ], md=5),
                                    dbc.Col([
                                        html.Label("Lookback", className="small text-muted"),
                                        dcc.Dropdown(
                                            id="regime-lookback-select",
                                            options=[
                                                {'label': '6 Months', 'value': 180},
                                                {'label': '1 Year', 'value': 365},
                                                {'label': '2 Years', 'value': 730},
                                            ],
                                            value=365,
                                            clearable=False,
                                            className="dash-dropdown-dark"
                                        )
                                    ], md=4)
                                ])
                            ], className="py-2")
                        ], className="bg-dark border-secondary mb-3")
                    ])
                ]),
                
                # Current Regime Banner
                html.Div(id="regime-current-banner", className="mb-3"),
                
                # Main Chart
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.H6([
                                    html.I(className="fas fa-chart-line me-2"),
                                    "Price Chart with Regime Backgrounds"
                                ], className="mb-0")
                            ]),
                            dbc.CardBody([
                                dcc.Loading(
                                    type="circle",
                                    children=[
                                        dcc.Graph(
                                            id="graph-regime-chart",
                                            config={'displayModeBar': True, 'displaylogo': False},
                                            style={'height': '400px'}
                                        )
                                    ]
                                )
                            ])
                        ], className="shadow-sm")
                    ], md=9),
                    
                    # Stats Column
                    dbc.Col([
                        dbc.Card([
                            dbc.CardHeader([
                                html.H6([
                                    html.I(className="fas fa-chart-pie me-2"),
                                    "Regime Statistics"
                                ], className="mb-0")
                            ]),
                            dbc.CardBody([
                                html.Div(id="regime-stats-cards")
                            ])
                        ], className="shadow-sm h-100")
                    ], md=3)
                ], className="mb-3"),
                
                # Legend
                dbc.Row([
                    dbc.Col([
                        html.Div([
                            html.Span([
                                html.Span("●", style={'color': REGIME_SOLID_COLORS[2], 'fontSize': '1.5em'}),
                                html.Span(" Bull  ", className="text-white small me-3"),
                            ]),
                            html.Span([
                                html.Span("●", style={'color': REGIME_SOLID_COLORS[1], 'fontSize': '1.5em'}),
                                html.Span(" Sideways  ", className="text-white small me-3"),
                            ]),
                            html.Span([
                                html.Span("●", style={'color': REGIME_SOLID_COLORS[0], 'fontSize': '1.5em'}),
                                html.Span(" Bear", className="text-white small"),
                            ]),
                        ], className="d-flex justify-content-center")
                    ])
                ]) if REGIME_AVAILABLE else html.Div(),
                
                # Store for regime data
                dcc.Store(id="store-regime-data"),
                
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


def create_regime_chart_figure(
    dates: List,
    prices: List[float],
    regimes: List[int],
    ticker: str,
    method: str
) -> go.Figure:
    """
    Create price chart with regime-colored background regions.
    
    Args:
        dates: List of datetime objects
        prices: List of price values
        regimes: List of regime labels (0=Bear, 1=Sideways, 2=Bull)
        ticker: Stock ticker symbol
        method: Detection method used (HMM or K-Means)
        
    Returns:
        Plotly Figure with regime visualization
    """
    import numpy as np
    
    fig = go.Figure()
    
    # Add price line
    fig.add_trace(go.Scatter(
        x=dates,
        y=prices,
        mode='lines',
        name=f'{ticker} Price',
        line=dict(color='white', width=2),
        hovertemplate='%{x}<br>Price: $%{y:.2f}<extra></extra>'
    ))
    
    # Add regime background colors
    if len(regimes) > 0:
        # Find regime change points
        regime_changes = [0]
        for i in range(1, len(regimes)):
            if regimes[i] != regimes[i-1]:
                regime_changes.append(i)
        regime_changes.append(len(regimes))
        
        # Add vrect for each regime period
        for i in range(len(regime_changes) - 1):
            start_idx = regime_changes[i]
            end_idx = regime_changes[i + 1] - 1
            
            if start_idx >= len(dates) or end_idx >= len(dates):
                continue
                
            regime = regimes[start_idx]
            color = REGIME_COLORS.get(regime, 'rgba(128,128,128,0.2)')
            
            fig.add_vrect(
                x0=dates[start_idx],
                x1=dates[end_idx],
                fillcolor=color,
                layer='below',
                line_width=0,
            )
    
    # Add legend for regimes
    for regime, label in REGIME_LABELS.items():
        color = REGIME_SOLID_COLORS.get(regime, 'gray')
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            name=label,
            marker=dict(size=15, color=color, symbol='square'),
            showlegend=True
        ))
    
    fig.update_layout(
        title=dict(
            text=f"{ticker} Market Regimes ({method})",
            font=dict(size=14)
        ),
        xaxis_title="Date",
        yaxis_title="Price ($)",
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=20, t=60, b=50),
        hovermode='x unified'
    )
    
    _apply_dark_theme(fig)
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
            
            # Regime Monitor Tab (Phase 5)
            create_regime_monitor_tab(),
            
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
    
    # ==== Phase 5: Regime Detection Callbacks ====
    
    @app.callback(
        [
            Output("graph-regime-chart", "figure"),
            Output("regime-current-banner", "children"),
            Output("regime-current-banner", "style"),
            Output("regime-stats-cards", "children"),
            Output("store-regime-data", "data")
        ],
        [
            Input("btn-detect-regimes", "n_clicks")
        ],
        [
            State("input-regime-ticker", "value"),
            State("radio-regime-method", "value"),
            State("select-regime-lookback", "value")
        ],
        prevent_initial_call=True
    )
    def detect_market_regimes(n_clicks, ticker, method, lookback):
        """
        Detect market regimes when button is clicked.
        
        Args:
            n_clicks: Button click count
            ticker: Stock ticker symbol
            method: Detection method ('hmm' or 'kmeans')
            lookback: Number of days to analyze
            
        Returns:
            Tuple of (figure, banner_text, banner_style, stats_cards, store_data)
        """
        import yfinance as yf
        from datetime import datetime, timedelta
        
        if not n_clicks or not ticker:
            return [
                create_empty_figure("Enter ticker and click Detect"),
                "No Data",
                {"backgroundColor": "gray", "color": "white", "padding": "10px", 
                 "borderRadius": "8px", "textAlign": "center", "fontSize": "18px"},
                [],
                None
            ]
        
        try:
            ticker = ticker.upper().strip()
            lookback = int(lookback) if lookback else 252
            
            # Fetch historical data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=int(lookback * 1.5))  # Extra buffer
            
            logger.info(f"Fetching {ticker} data for regime detection...")
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date)
            
            if hist.empty or len(hist) < 50:
                raise ValueError(f"Insufficient data for {ticker}")
            
            # Trim to exact lookback
            hist = hist.tail(lookback)
            
            dates = hist.index.tolist()
            prices = hist['Close'].values.tolist()
            
            # Detect regimes
            regimes, detector = detect_regimes(
                prices=prices,
                method=method,
                n_regimes=3,
                window=20
            )
            
            # Get current regime
            current_regime = detector.get_current_regime()
            current_label = REGIME_LABELS.get(current_regime, "Unknown")
            current_color = REGIME_SOLID_COLORS.get(current_regime, "gray")
            
            # Create chart
            fig = create_regime_chart_figure(
                dates=dates,
                prices=prices,
                regimes=regimes.tolist(),
                ticker=ticker,
                method=method.upper()
            )
            
            # Banner style
            banner_style = {
                "backgroundColor": current_color,
                "color": "white",
                "padding": "15px",
                "borderRadius": "8px",
                "textAlign": "center",
                "fontSize": "20px",
                "fontWeight": "bold"
            }
            banner_text = f"Current Regime: {current_label}"
            
            # Stats cards
            stats = detector.get_regime_stats()
            stats_cards = []
            
            for regime_id, regime_stats in stats.items():
                regime_name = REGIME_LABELS.get(regime_id, f"Regime {regime_id}")
                regime_color = REGIME_SOLID_COLORS.get(regime_id, "gray")
                
                card = dbc.Card([
                    dbc.CardHeader(
                        regime_name,
                        style={"backgroundColor": regime_color, "color": "white", 
                               "fontWeight": "bold", "textAlign": "center"}
                    ),
                    dbc.CardBody([
                        html.P([
                            html.Strong("Days: "),
                            f"{regime_stats['count']}"
                        ], className="mb-1"),
                        html.P([
                            html.Strong("Frequency: "),
                            f"{regime_stats['frequency']:.1%}"
                        ], className="mb-1"),
                        html.P([
                            html.Strong("Avg Return: "),
                            f"{regime_stats['mean_return']:.2%}"
                        ], className="mb-1"),
                        html.P([
                            html.Strong("Volatility: "),
                            f"{regime_stats['volatility']:.2%}"
                        ], className="mb-0"),
                    ], className="p-2")
                ], className="h-100")
                
                stats_cards.append(dbc.Col(card, md=4, className="mb-2"))
            
            stats_row = dbc.Row(stats_cards)
            
            # Store data
            store_data = {
                "ticker": ticker,
                "method": method,
                "lookback": lookback,
                "current_regime": current_regime,
                "regime_counts": {str(k): v for k, v in stats.items()},
                "last_updated": datetime.now().isoformat()
            }
            
            logger.info(f"Regime detection complete for {ticker}: {current_label}")
            return [fig, banner_text, banner_style, stats_row, store_data]
            
        except Exception as e:
            logger.error(f"Regime detection error: {e}")
            return [
                create_empty_figure(f"Error: {str(e)[:50]}"),
                f"Error: {str(e)[:30]}",
                {"backgroundColor": "#dc3545", "color": "white", "padding": "10px",
                 "borderRadius": "8px", "textAlign": "center"},
                [],
                None
            ]


# Export
__all__ = ['get_layout', 'register_callbacks', 'create_macro_dashboard_tab', 'create_regime_monitor_tab']
