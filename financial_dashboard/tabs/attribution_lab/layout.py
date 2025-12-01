"""
Attribution Lab Layout Module

Defines UI structure for 4 core subtabs:
1. Performance Overview - Portfolio vs Benchmark comparison
2. Factor Contribution - Factor-based attribution
3. Sector/Asset Analysis - Sector breakdown
4. Residual Attribution - Alpha and unexplained returns
"""

import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table
from datetime import datetime, timedelta

def layout():
    """
    Main layout for Attribution Lab tab.
    
    Returns:
        Dash component tree
    """
    return dbc.Container([
        # Header
        html.Div([
            html.H3("📊 Attribution Analysis Lab", className="mb-2"),
            html.P(
                "Comprehensive portfolio attribution: performance, factors, sectors, and alpha generation",
                className="mb-3",
                style={'color': '#000000'}
            ),
            
            # Beginner-Friendly Overview
            dbc.Accordion([
                dbc.AccordionItem([
                    dcc.Markdown("""
**📊 What This Lab Does:**

Attribution Analysis breaks down your portfolio performance to understand **WHY** you made or lost money. Instead of just seeing total returns, you'll discover which specific factors drove your results:
- **Market movements** (did the overall market go up or down?)
- **Sector allocation** (were you in the right industries?)
- **Stock selection** (did you pick winners within sectors?)
- **Factor exposures** (momentum, value, size, quality)

**💡 Key Features:**

- **Performance Overview**: Compare your returns vs benchmarks (S&P 500, NASDAQ, etc.)
- **Factor Attribution**: See how much each Fama-French factor contributed (Market, Size, Value, Momentum)
- **Sector Analysis**: Identify which industries drove performance (Technology, Healthcare, Financials, etc.)
- **Alpha Calculation**: Measure your skill vs luck (positive alpha = beating the market after adjusting for risk)

**🎯 How to Use:**

1. **Select Portfolio**: Choose "Current Portfolio", "Weekly Picks", or "Monthly Picks"
2. **Choose Benchmark**: Pick S&P 500 (SPY) for large-cap comparison, NASDAQ (QQQ) for tech-heavy, etc.
3. **Set Date Range**: Default is last 365 days, adjust as needed
4. **Click "Refresh Analysis"**: Wait 2-3 seconds for calculations
5. **Navigate Subtabs**: Review each section (Performance → Factors → Sectors → Alpha)

**🎓 Understanding Factor Attribution (Fama-French Model):**

- **Market Factor (Mkt-RF)**: Excess return above risk-free rate (most portfolios are +0.8 to +1.2)
- **Size Factor (SMB)**: Small Minus Big - do you favor small-cap or large-cap stocks?
- **Value Factor (HML)**: High Minus Low book/market - are you value or growth oriented?
- **Momentum Factor (MOM)**: Do you chase recent winners or contrarian plays?
- **Residual (Alpha)**: The "magic" - returns unexplained by factors (your true skill)

**💡 Quick Tips:**

- Green bars = positive contribution (good for returns)
- Red bars = negative contribution (hurt your returns)
- Larger bars = bigger impact on performance
- High alpha = you're beating the market consistently (aim for >2% annually)

**📖 Learn More:** For academic details, see Fama & French (1993) "Common risk factors in the returns on stocks and bonds"
                    """, style={'color': '#000000', 'fontSize': '14px'})
                ], title="📚 Beginner's Guide to Attribution Analysis", className="mb-3")
            ], start_collapsed=True, className="mb-4")
        ]),
        
        # Global Controls Row
        dbc.Row([
            dbc.Col([
                dbc.Label("Portfolio", style={'color': '#ffffff', 'fontWeight': '500'}),
                dcc.Dropdown(
                    id='attr-portfolio-dropdown',
                    options=[
                        {'label': 'Current Portfolio', 'value': 'current'},
                        {'label': 'Weekly Picks', 'value': 'weekly'},
                        {'label': 'Monthly Picks', 'value': 'monthly'}
                    ],
                    value='current',
                    style={'backgroundColor': '#ffffff', 'color': '#000000'},
                    className='attr-portfolio-dropdown'
                )
            ], width=3),
            dbc.Col([
                dbc.Label("Benchmark", style={'color': '#ffffff', 'fontWeight': '500'}),
                dcc.Dropdown(
                    id='attr-benchmark-dropdown',
                    options=[
                        {'label': 'S&P 500 (SPY)', 'value': 'SPY'},
                        {'label': 'NASDAQ 100 (QQQ)', 'value': 'QQQ'},
                        {'label': 'Russell 2000 (IWM)', 'value': 'IWM'},
                        {'label': 'Total Market (VTI)', 'value': 'VTI'}
                    ],
                    value='SPY',
                    style={'backgroundColor': '#ffffff', 'color': '#000000'},
                    className='attr-benchmark-dropdown'
                )
            ], width=3),
            dbc.Col([
                dbc.Label("Date Range", style={'color': '#ffffff', 'fontWeight': '500'}),
                dcc.DatePickerRange(
                    id='attr-date-range',
                    start_date=datetime.now() - timedelta(days=365),
                    end_date=datetime.now(),
                    display_format='YYYY-MM-DD',
                    className='attr-date-range'
                )
            ], width=4),
            dbc.Col([
                dbc.Button(
                    "🔄 Refresh Analysis",
                    id='attr-refresh-btn',
                    color='primary',
                    className='mt-4 attr-refresh-btn',
                    n_clicks=0
                )
            ], width=2)
        ], className="mb-4"),
        
        # Status Message
        html.Div(id='attr-status-message', className='mb-3'),
        
        # Subtabs Navigation
        dbc.Tabs(
            id="attr-subtabs",
            active_tab="performance",
            className="mb-4 attr-subtabs",
            children=[
                dbc.Tab(
                    label="📈 Performance Overview",
                    tab_id="performance",
                    className="attr-tab-performance",
                    children=[_create_performance_layout()]
                ),
                dbc.Tab(
                    label="🔍 Factor Contribution",
                    tab_id="factors",
                    className="attr-tab-factors",
                    children=[_create_factors_layout()]
                ),
                dbc.Tab(
                    label="🏢 Sector Analysis",
                    tab_id="sectors",
                    className="attr-tab-sectors",
                    children=[_create_sectors_layout()]
                ),
                dbc.Tab(
                    label="✨ Residual & Alpha",
                    tab_id="residual",
                    className="attr-tab-residual",
                    children=[_create_residual_layout()]
                )
            ]
        ),
        
        # Hidden stores for data
        dcc.Store(id='attr-portfolio-data'),
        dcc.Store(id='attr-benchmark-data'),
        dcc.Store(id='attr-factor-data'),
        dcc.Store(id='attr-metrics-data'),
        
        # Download components
        dcc.Download(id='attr-download-csv'),
        dcc.Download(id='attr-download-report')
        
    ], fluid=True)


def _create_performance_layout():
    """Create layout for Performance Overview subtab."""
    return dbc.Container([
        html.Div([
            html.H5("Performance Overview", className="mt-3 mb-3"),
            html.P("Portfolio vs benchmark performance comparison", className="text-muted mb-4"),
            
            # Summary Metrics Cards
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Total Return", className="text-muted mb-1"),
                            html.H4(id='perf-total-return', children="--", className="text-success"),
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Excess Return", className="text-muted mb-1"),
                            html.H4(id='perf-excess-return', children="--"),
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Sharpe Ratio", className="text-muted mb-1"),
                            html.H4(id='perf-sharpe', children="--"),
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Information Ratio", className="text-muted mb-1"),
                            html.H4(id='perf-info-ratio', children="--"),
                        ])
                    ])
                ], width=3)
            ], className="mb-4"),
            
            # Cumulative Returns Chart
            dbc.Row([
                dbc.Col([
                    html.H6("Cumulative Returns", className="mb-2"),
                    dbc.Spinner(
                        dcc.Graph(
                            id='perf-cumulative-chart',
                            config={'displayModeBar': True},
                            style={'height': '400px'}
                        ),
                        color="primary"
                    )
                ], width=12)
            ], className="mb-4"),
            
            # Monthly Returns Bar Chart
            dbc.Row([
                dbc.Col([
                    html.H6("Monthly Returns Comparison", className="mb-2"),
                    dbc.Spinner(
                        dcc.Graph(
                            id='perf-monthly-chart',
                            config={'displayModeBar': True},
                            style={'height': '350px'}
                        ),
                        color="primary"
                    )
                ], width=12)
            ], className="mb-4"),
            
            # Detailed Metrics Table
            dbc.Row([
                dbc.Col([
                    html.H6("Detailed Metrics", className="mb-2"),
                    html.Div(id='perf-metrics-table')
                ], width=12)
            ]),
            
            # Export Button
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        "📥 Export Performance Report",
                        id='perf-export-btn',
                        color='success',
                        outline=True,
                        className="mt-3 perf-export-btn",
                        n_clicks=0
                    )
                ])
            ])
        ])
    ], fluid=True)


def _create_factors_layout():
    """Create layout for Factor Contribution subtab."""
    return dbc.Container([
        html.Div([
            html.H5("Factor Contribution Analysis", className="mt-3 mb-3"),
            html.P("Attribution of returns to systematic risk factors", className="text-muted mb-4"),
            
            # Factor Selection
            dbc.Row([
                dbc.Col([
                    dbc.Label("Select Factors", style={'color': '#ffffff', 'fontWeight': '500'}),
                    dcc.Dropdown(
                        id='factors-selection',
                        options=[
                            {'label': 'Market (Mkt-RF)', 'value': 'market'},
                            {'label': 'Size (SMB)', 'value': 'size'},
                            {'label': 'Value (HML)', 'value': 'value'},
                            {'label': 'Momentum (MOM)', 'value': 'momentum'},
                            {'label': 'Quality', 'value': 'quality'}
                        ],
                        value=['market', 'size', 'value', 'momentum'],
                        multi=True,
                        style={'backgroundColor': '#ffffff', 'color': '#000000'},
                        className='factors-selection'
                    )
                ], width=12)
            ], className="mb-4"),
            
            # Factor Exposures Summary
            dbc.Row([
                dbc.Col([
                    html.H6("Factor Exposures (Beta)", className="mb-2"),
                    html.Div(id='factors-exposures-container')
                ], width=12)
            ], className="mb-4"),
            
            # Factor Contribution Chart
            dbc.Row([
                dbc.Col([
                    html.H6("Factor Contribution to Returns", className="mb-2"),
                    dbc.Spinner(
                        dcc.Graph(
                            id='factors-contribution-chart',
                            config={'displayModeBar': True},
                            style={'height': '450px'}
                        ),
                        color="primary"
                    )
                ], width=12)
            ], className="mb-4"),
            
            # Time Series Factor Contributions
            dbc.Row([
                dbc.Col([
                    html.H6("Cumulative Factor Contributions", className="mb-2"),
                    dbc.Spinner(
                        dcc.Graph(
                            id='factors-timeseries-chart',
                            config={'displayModeBar': True},
                            style={'height': '400px'}
                        ),
                        color="primary"
                    )
                ], width=12)
            ], className="mb-4"),
            
            # Export Button
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        "📥 Export Factor Analysis",
                        id='factors-export-btn',
                        color='success',
                        outline=True,
                        className="mt-3 factors-export-btn",
                        n_clicks=0
                    )
                ])
            ])
        ])
    ], fluid=True)


def _create_sectors_layout():
    """Create layout for Sector/Asset Class Analysis subtab."""
    return dbc.Container([
        html.Div([
            html.H5("Sector & Asset Class Attribution", className="mt-3 mb-3"),
            html.P("Returns attribution by sector and asset class", className="text-muted mb-4"),
            
            # Sector Contribution Summary
            dbc.Row([
                dbc.Col([
                    html.H6("Sector Weights", className="mb-2"),
                    dbc.Spinner(
                        dcc.Graph(
                            id='sectors-weights-pie',
                            config={'displayModeBar': False},
                            style={'height': '400px'}
                        ),
                        color="primary"
                    )
                ], width=6),
                dbc.Col([
                    html.H6("Sector Contribution to Returns", className="mb-2"),
                    dbc.Spinner(
                        dcc.Graph(
                            id='sectors-contribution-bar',
                            config={'displayModeBar': True},
                            style={'height': '400px'}
                        ),
                        color="primary"
                    )
                ], width=6)
            ], className="mb-4"),
            
            # Detailed Sector Table
            dbc.Row([
                dbc.Col([
                    html.H6("Detailed Sector Breakdown", className="mb-2"),
                    html.Div(id='sectors-table-container')
                ], width=12)
            ], className="mb-4"),
            
            # Sector Performance Heatmap
            dbc.Row([
                dbc.Col([
                    html.H6("Sector Performance Heatmap", className="mb-2"),
                    dbc.Spinner(
                        dcc.Graph(
                            id='sectors-heatmap',
                            config={'displayModeBar': True},
                            style={'height': '350px'}
                        ),
                        color="primary"
                    )
                ], width=12)
            ], className="mb-4"),
            
            # Export Button
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        "📥 Export Sector Analysis",
                        id='sectors-export-btn',
                        color='success',
                        outline=True,
                        className="mt-3 sectors-export-btn",
                        n_clicks=0
                    )
                ])
            ])
        ])
    ], fluid=True)


def _create_residual_layout():
    """Create layout for Residual & Alpha Attribution subtab."""
    return dbc.Container([
        html.Div([
            html.H5("Residual & Alpha Analysis", className="mt-3 mb-3"),
            html.P("Unexplained returns and alpha generation analysis", className="text-muted mb-4"),
            
            # Alpha Metrics Cards
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Jensen's Alpha", className="text-muted mb-1"),
                            html.H4(id='residual-alpha', children="--"),
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Beta", className="text-muted mb-1"),
                            html.H4(id='residual-beta', children="--"),
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Tracking Error", className="text-muted mb-1"),
                            html.H4(id='residual-tracking', children="--"),
                        ])
                    ])
                ], width=3),
                dbc.Col([
                    dbc.Card([
                        dbc.CardBody([
                            html.H6("Residual Volatility", className="text-muted mb-1"),
                            html.H4(id='residual-vol', children="--"),
                        ])
                    ])
                ], width=3)
            ], className="mb-4"),
            
            # Residual Returns Time Series
            dbc.Row([
                dbc.Col([
                    html.H6("Cumulative Residual Returns", className="mb-2"),
                    dbc.Spinner(
                        dcc.Graph(
                            id='residual-timeseries-chart',
                            config={'displayModeBar': True},
                            style={'height': '400px'}
                        ),
                        color="primary"
                    )
                ], width=12)
            ], className="mb-4"),
            
            # Residual Distribution
            dbc.Row([
                dbc.Col([
                    html.H6("Residual Returns Distribution", className="mb-2"),
                    dbc.Spinner(
                        dcc.Graph(
                            id='residual-histogram',
                            config={'displayModeBar': True},
                            style={'height': '350px'}
                        ),
                        color="primary"
                    )
                ], width=6),
                dbc.Col([
                    html.H6("Explained vs Unexplained Returns", className="mb-2"),
                    dbc.Spinner(
                        dcc.Graph(
                            id='residual-explained-pie',
                            config={'displayModeBar': False},
                            style={'height': '350px'}
                        ),
                        color="primary"
                    )
                ], width=6)
            ], className="mb-4"),
            
            # Scatter Plot: Portfolio vs Benchmark
            dbc.Row([
                dbc.Col([
                    html.H6("Portfolio vs Benchmark Scatter", className="mb-2"),
                    dbc.Spinner(
                        dcc.Graph(
                            id='residual-scatter-chart',
                            config={'displayModeBar': True},
                            style={'height': '400px'}
                        ),
                        color="primary"
                    )
                ], width=12)
            ], className="mb-4"),
            
            # Export Button
            dbc.Row([
                dbc.Col([
                    dbc.Button(
                        "📥 Export Residual Analysis",
                        id='residual-export-btn',
                        color='success',
                        outline=True,
                        className="mt-3 residual-export-btn",
                        n_clicks=0
                    )
                ])
            ])
        ])
    ], fluid=True)
