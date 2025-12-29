"""
Focus Assets UI Components
==========================

UI components specifically for GLD, SLV, SPY, and major tech stocks.
"""

from dash import html, dcc
import dash_bootstrap_components as dbc
from typing import Dict, List, Optional

# Focus asset configuration
FOCUS_ASSETS = {
    'precious_metals': {
        'tickers': ['GLD', 'SLV'],
        'color': '#FFD700',  # Gold
        'icon': '🥇'
    },
    'market_etfs': {
        'tickers': ['SPY', 'QQQ', 'IWM'],
        'color': '#4169E1',  # Royal Blue
        'icon': '📊'
    },
    'major_tech': {
        'tickers': ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA'],
        'color': '#00CED1',  # Dark Cyan
        'icon': '💻'
    }
}


def create_focus_watchlist_card():
    """Create a focus watchlist card with quick access to key tickers."""
    
    ticker_buttons = []
    
    for category, config in FOCUS_ASSETS.items():
        category_label = category.replace('_', ' ').title()
        ticker_buttons.append(
            html.Div([
                html.Span(f"{config['icon']} {category_label}", 
                         style={'fontWeight': 'bold', 'color': config['color'], 'marginRight': '10px'}),
                html.Div([
                    dbc.Button(
                        ticker,
                        id={'type': 'focus-ticker-btn', 'ticker': ticker},
                        color='dark',
                        size='sm',
                        outline=True,
                        className='me-1 mb-1',
                        style={'borderColor': config['color']}
                    )
                    for ticker in config['tickers']
                ], style={'display': 'inline-block'})
            ], className='mb-2')
        )
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-star me-2"),
            "Focus Watchlist"
        ], style={'backgroundColor': '#1a1a2e', 'color': 'white'}),
        dbc.CardBody(ticker_buttons)
    ], className='mb-3')


def create_precious_metals_widget():
    """Create precious metals overview widget (GLD/SLV)."""
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-coins me-2"),
            "🥇 Precious Metals Overview"
        ], style={'backgroundColor': '#2d2d44', 'color': '#FFD700'}),
        dbc.CardBody([
            dbc.Row([
                # GLD Card
                dbc.Col([
                    html.Div([
                        html.H5("GLD (Gold)", className='text-warning mb-1'),
                        html.Div(id='gld-price', children='Loading...', 
                                style={'fontSize': '24px', 'fontWeight': 'bold'}),
                        html.Div(id='gld-change', children='', 
                                style={'fontSize': '14px'})
                    ], className='text-center p-3', 
                       style={'backgroundColor': '#1a1a2e', 'borderRadius': '8px'})
                ], width=6),
                
                # SLV Card
                dbc.Col([
                    html.Div([
                        html.H5("SLV (Silver)", className='text-info mb-1'),
                        html.Div(id='slv-price', children='Loading...', 
                                style={'fontSize': '24px', 'fontWeight': 'bold'}),
                        html.Div(id='slv-change', children='', 
                                style={'fontSize': '14px'})
                    ], className='text-center p-3', 
                       style={'backgroundColor': '#1a1a2e', 'borderRadius': '8px'})
                ], width=6),
            ], className='mb-3'),
            
            # Gold-Silver Ratio
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H6("Gold/Silver Ratio", className='text-muted mb-1'),
                        html.Div(id='gold-silver-ratio', children='--', 
                                style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#FFD700'}),
                        html.Small(id='ratio-signal', children='Historical avg: ~70', 
                                  className='text-muted')
                    ], className='text-center p-2')
                ])
            ]),
            
            # Action buttons
            dbc.Row([
                dbc.Col([
                    dbc.ButtonGroup([
                        dbc.Button("Analyze GLD", id='analyze-gld-btn', color='warning', size='sm', outline=True),
                        dbc.Button("Analyze SLV", id='analyze-slv-btn', color='info', size='sm', outline=True),
                        dbc.Button("Compare", id='compare-metals-btn', color='secondary', size='sm', outline=True),
                    ], className='d-flex justify-content-center')
                ])
            ], className='mt-3')
        ])
    ], className='mb-3', style={'borderColor': '#FFD700'})


def create_spy_overview_widget():
    """Create SPY market overview widget."""
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-chart-line me-2"),
            "📊 SPY Market Overview"
        ], style={'backgroundColor': '#2d2d44', 'color': '#4169E1'}),
        dbc.CardBody([
            dbc.Row([
                # SPY Price
                dbc.Col([
                    html.Div([
                        html.H5("SPY", className='text-primary mb-1'),
                        html.Div(id='spy-price-display', children='Loading...', 
                                style={'fontSize': '28px', 'fontWeight': 'bold'}),
                        html.Div(id='spy-change-display', children='', 
                                style={'fontSize': '14px'})
                    ], className='text-center')
                ], width=4),
                
                # VIX
                dbc.Col([
                    html.Div([
                        html.H5("VIX", className='text-danger mb-1'),
                        html.Div(id='vix-display', children='--', 
                                style={'fontSize': '28px', 'fontWeight': 'bold', 'color': '#dc3545'}),
                        html.Small("Fear Index", className='text-muted')
                    ], className='text-center')
                ], width=4),
                
                # Market Status
                dbc.Col([
                    html.Div([
                        html.H5("Market", className='text-success mb-1'),
                        html.Div(id='market-status-display', children='OPEN', 
                                style={'fontSize': '20px', 'fontWeight': 'bold'}),
                        html.Div(id='market-regime', children='Normal', 
                                className='badge bg-success')
                    ], className='text-center')
                ], width=4),
            ], className='mb-3'),
            
            # Key Levels
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Small("Support", className='text-danger'),
                        html.Div(id='spy-support', children='--', style={'fontWeight': 'bold'})
                    ], className='text-center')
                ], width=4),
                dbc.Col([
                    html.Div([
                        html.Small("Pivot", className='text-warning'),
                        html.Div(id='spy-pivot', children='--', style={'fontWeight': 'bold'})
                    ], className='text-center')
                ], width=4),
                dbc.Col([
                    html.Div([
                        html.Small("Resistance", className='text-success'),
                        html.Div(id='spy-resistance', children='--', style={'fontWeight': 'bold'})
                    ], className='text-center')
                ], width=4),
            ])
        ])
    ], className='mb-3', style={'borderColor': '#4169E1'})


def create_mag7_widget():
    """Create Magnificent 7 overview widget."""
    
    mag7 = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA']
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-microchip me-2"),
            "💻 Magnificent 7 Tech"
        ], style={'backgroundColor': '#2d2d44', 'color': '#00CED1'}),
        dbc.CardBody([
            # Ticker grid
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.Strong(ticker, style={'color': '#00CED1'}),
                        html.Div(id=f'mag7-{ticker.lower()}-price', children='--', 
                                style={'fontSize': '14px'}),
                        html.Small(id=f'mag7-{ticker.lower()}-change', children='')
                    ], className='text-center p-2', 
                       style={'backgroundColor': '#1a1a2e', 'borderRadius': '5px', 'margin': '2px'})
                ], width=3 if i < 4 else 3)
                for i, ticker in enumerate(mag7[:4])
            ] + [
                dbc.Col([
                    html.Div([
                        html.Strong(ticker, style={'color': '#00CED1'}),
                        html.Div(id=f'mag7-{ticker.lower()}-price', children='--', 
                                style={'fontSize': '14px'}),
                        html.Small(id=f'mag7-{ticker.lower()}-change', children='')
                    ], className='text-center p-2', 
                       style={'backgroundColor': '#1a1a2e', 'borderRadius': '5px', 'margin': '2px'})
                ], width=4)
                for ticker in mag7[4:]
            ], className='g-1'),
            
            # Summary row
            html.Hr(style={'borderColor': '#00CED1'}),
            dbc.Row([
                dbc.Col([
                    html.Small("Avg Return:", className='text-muted'),
                    html.Span(id='mag7-avg-return', children='--', className='ms-2')
                ], width=4),
                dbc.Col([
                    html.Small("Leaders:", className='text-muted'),
                    html.Span(id='mag7-leaders', children='--', className='ms-2 text-success')
                ], width=4),
                dbc.Col([
                    html.Small("Laggards:", className='text-muted'),
                    html.Span(id='mag7-laggards', children='--', className='ms-2 text-danger')
                ], width=4),
            ])
        ])
    ], className='mb-3', style={'borderColor': '#00CED1'})


def create_quick_options_scanner():
    """Create a quick options scanner for focus tickers."""
    
    all_tickers = ['GLD', 'SLV', 'SPY', 'QQQ', 'AAPL', 'MSFT', 'NVDA', 'GOOGL', 'AMZN', 'META', 'TSLA', 'AMD']
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-search-dollar me-2"),
            "⚡ Quick Options Scanner"
        ], style={'backgroundColor': '#2d2d44', 'color': '#9370DB'}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Ticker", className='text-muted'),
                    dcc.Dropdown(
                        id='quick-scan-ticker',
                        options=[{'label': t, 'value': t} for t in all_tickers],
                        value='SPY',
                        className='dark-dropdown'
                    )
                ], width=4),
                dbc.Col([
                    dbc.Label("Strategy", className='text-muted'),
                    dcc.Dropdown(
                        id='quick-scan-strategy',
                        options=[
                            {'label': 'High IV - Sell Premium', 'value': 'sell_premium'},
                            {'label': 'Low IV - Buy Options', 'value': 'buy_options'},
                            {'label': 'Earnings Play', 'value': 'earnings'},
                            {'label': 'Momentum', 'value': 'momentum'},
                        ],
                        value='sell_premium',
                        className='dark-dropdown'
                    )
                ], width=5),
                dbc.Col([
                    dbc.Label(" ", className='text-muted'),
                    dbc.Button("Scan", id='quick-scan-btn', color='primary', className='w-100')
                ], width=3)
            ], className='mb-3'),
            
            # Results area
            html.Div(id='quick-scan-results', children=[
                html.P("Select a ticker and strategy to scan for opportunities", 
                      className='text-muted text-center')
            ])
        ])
    ], className='mb-3', style={'borderColor': '#9370DB'})


def create_alerts_widget():
    """Create real-time alerts widget for focus tickers."""
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-bell me-2"),
            "🔔 Focus Stock Alerts"
        ], style={'backgroundColor': '#2d2d44', 'color': '#FF6347'}),
        dbc.CardBody([
            # Alert settings
            dbc.Row([
                dbc.Col([
                    dbc.Checklist(
                        id='alert-types',
                        options=[
                            {'label': ' Price Alerts', 'value': 'price'},
                            {'label': ' IV Spikes', 'value': 'iv'},
                            {'label': ' Volume Unusual', 'value': 'volume'},
                            {'label': ' Earnings', 'value': 'earnings'},
                        ],
                        value=['price', 'iv'],
                        inline=True,
                        switch=True
                    )
                ])
            ], className='mb-3'),
            
            # Active alerts
            html.Div(id='active-alerts', children=[
                dbc.Alert([
                    html.Strong("NVDA: "), "IV Percentile at 85% - Consider selling premium"
                ], color='warning', className='mb-2 py-2'),
                dbc.Alert([
                    html.Strong("GLD: "), "Breaking above 200 resistance - Momentum signal"
                ], color='success', className='mb-2 py-2'),
            ], style={'maxHeight': '200px', 'overflowY': 'auto'})
        ])
    ], className='mb-3', style={'borderColor': '#FF6347'})


def create_correlation_matrix_mini():
    """Create a mini correlation matrix for focus assets."""
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-table me-2"),
            "📈 Correlation Matrix"
        ], style={'backgroundColor': '#2d2d44', 'color': '#20B2AA'}),
        dbc.CardBody([
            dcc.Graph(
                id='focus-correlation-matrix',
                config={'displayModeBar': False},
                style={'height': '250px'}
            )
        ])
    ], className='mb-3', style={'borderColor': '#20B2AA'})


def create_portfolio_exposure_widget():
    """Create portfolio exposure summary widget."""
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="fas fa-chart-pie me-2"),
            "💼 Portfolio Exposure"
        ], style={'backgroundColor': '#2d2d44', 'color': '#DDA0DD'}),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dcc.Graph(
                        id='exposure-pie-chart',
                        config={'displayModeBar': False},
                        style={'height': '200px'}
                    )
                ], width=6),
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.Span("🥇 Metals: ", style={'color': '#FFD700'}),
                            html.Span(id='metals-exposure', children='0%')
                        ], className='mb-2'),
                        html.Div([
                            html.Span("📊 Market ETFs: ", style={'color': '#4169E1'}),
                            html.Span(id='etf-exposure', children='0%')
                        ], className='mb-2'),
                        html.Div([
                            html.Span("💻 Tech: ", style={'color': '#00CED1'}),
                            html.Span(id='tech-exposure', children='0%')
                        ], className='mb-2'),
                        html.Div([
                            html.Span("💵 Cash: ", style={'color': '#98FB98'}),
                            html.Span(id='cash-exposure', children='0%')
                        ], className='mb-2'),
                    ])
                ], width=6)
            ])
        ])
    ], className='mb-3', style={'borderColor': '#DDA0DD'})


# Main dashboard layout for focus assets
def create_focus_assets_dashboard():
    """Create the complete focus assets dashboard layout."""
    
    return html.Div([
        # Header
        dbc.Row([
            dbc.Col([
                html.H4([
                    html.I(className="fas fa-star me-2"),
                    "Focus Assets Dashboard"
                ], className='text-light mb-3'),
                html.P("GLD • SLV • SPY • Major Tech", className='text-muted')
            ])
        ]),
        
        # Main content
        dbc.Row([
            # Left column
            dbc.Col([
                create_precious_metals_widget(),
                create_spy_overview_widget(),
                create_alerts_widget(),
            ], width=4),
            
            # Center column
            dbc.Col([
                create_mag7_widget(),
                create_quick_options_scanner(),
                create_correlation_matrix_mini(),
            ], width=4),
            
            # Right column
            dbc.Col([
                create_focus_watchlist_card(),
                create_portfolio_exposure_widget(),
            ], width=4),
        ])
    ], style={'padding': '20px'})


# Store component for focus asset data
focus_assets_stores = html.Div([
    dcc.Store(id='focus-gld-data'),
    dcc.Store(id='focus-slv-data'),
    dcc.Store(id='focus-spy-data'),
    dcc.Store(id='focus-mag7-data'),
    dcc.Store(id='focus-alerts-data'),
    dcc.Interval(id='focus-update-interval', interval=30000, n_intervals=0),
])


__all__ = [
    'create_focus_watchlist_card',
    'create_precious_metals_widget',
    'create_spy_overview_widget',
    'create_mag7_widget',
    'create_quick_options_scanner',
    'create_alerts_widget',
    'create_correlation_matrix_mini',
    'create_portfolio_exposure_widget',
    'create_focus_assets_dashboard',
    'focus_assets_stores',
    'FOCUS_ASSETS'
]
