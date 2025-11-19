"""
Global Search Component for Sprint 6
Provides cross-module search functionality with keyboard shortcuts
"""
from dash import html, dcc
import dash_bootstrap_components as dbc

# Search categories and their data sources
SEARCH_CATEGORIES = {
    'tickers': {
        'name': 'Tickers',
        'icon': 'fa-chart-line',
        'color': 'primary'
    },
    'strategies': {
        'name': 'Strategies',
        'icon': 'fa-lightbulb',
        'color': 'success'
    },
    'analyses': {
        'name': 'Saved Analyses',
        'icon': 'fa-folder',
        'color': 'warning'
    },
    'tabs': {
        'name': 'Tabs & Features',
        'icon': 'fa-compass',
        'color': 'info'
    }
}

def create_global_search():
    """Create global search modal and button"""
    return html.Div([
        # Search button in navbar
        dbc.Button(
            [html.I(className="fas fa-search me-2"), "Search (Ctrl+K)"],
            id="global-search-btn",
            color="secondary",
            outline=True,
            size="sm",
            className="me-2"
        ),
        
        # Search modal
        dbc.Modal([
            dbc.ModalHeader([
                html.I(className="fas fa-search me-2"),
                "Global Search"
            ]),
            dbc.ModalBody([
                # Search input
                dbc.Input(
                    id="global-search-input",
                    placeholder="Search tickers, strategies, analyses, tabs...",
                    type="text",
                    className="mb-3",
                    autoFocus=True
                ),
                
                # Search filters
                html.Div([
                    dbc.ButtonGroup([
                        dbc.Button(
                            [html.I(className=f"fas {cat['icon']} me-1"), cat['name']],
                            id=f"search-filter-{key}",
                            color=cat['color'],
                            outline=True,
                            size="sm"
                        )
                        for key, cat in SEARCH_CATEGORIES.items()
                    ], className="mb-3")
                ]),
                
                # Search results
                html.Div(id="global-search-results", children=[
                    html.Div("Type to search...", className="text-muted text-center py-4")
                ])
            ]),
            dbc.ModalFooter([
                html.Small("Press ESC to close | ↑↓ to navigate | Enter to select", 
                          className="text-muted me-auto"),
                dbc.Button("Close", id="global-search-close", size="sm")
            ])
        ],
        id="global-search-modal",
        size="lg",
        is_open=False,
        backdrop=True,
        keyboard=True
        ),
        
        # Keyboard shortcut detector
        dcc.Store(id='search-shortcut-store')
    ])

def format_search_result(result_type, item):
    """Format a single search result"""
    cat = SEARCH_CATEGORIES.get(result_type, SEARCH_CATEGORIES['tickers'])
    
    return dbc.ListGroupItem([
        html.Div([
            html.I(className=f"fas {cat['icon']} me-2 text-{cat['color']}"),
            html.Span(item.get('title', 'Unknown'), className="fw-bold"),
            html.Span(f" • {item.get('description', '')}", className="text-muted ms-2"),
        ])
    ], 
    action=True,
    href=item.get('href', '#'),
    className="search-result-item"
    )

def search_database(query, filters=None):
    """
    Search across all modules
    Returns list of {type, title, description, href} dicts
    """
    results = []
    
    if not query or len(query) < 2:
        return results
    
    query_lower = query.lower()
    
    # Search tickers (example data - replace with actual data source)
    if not filters or 'tickers' in filters:
        tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'SPY', 'QQQ']
        for ticker in tickers:
            if query_lower in ticker.lower():
                results.append({
                    'type': 'tickers',
                    'title': ticker,
                    'description': 'Stock Ticker',
                    'href': f'#market_trends?ticker={ticker}'
                })
    
    # Search strategies
    if not filters or 'strategies' in filters:
        strategies = [
            {'name': 'Iron Condor', 'desc': 'Options Strategy'},
            {'name': 'Covered Call', 'desc': 'Options Strategy'},
            {'name': 'Long Straddle', 'desc': 'Volatility Strategy'},
        ]
        for strat in strategies:
            if query_lower in strat['name'].lower():
                results.append({
                    'type': 'strategies',
                    'title': strat['name'],
                    'description': strat['desc'],
                    'href': '#options_lab'
                })
    
    # Search tabs/features
    if not filters or 'tabs' in filters:
        tabs = [
            {'name': 'Market Trends', 'desc': 'Market analysis and trends'},
            {'name': 'Market Forecast', 'desc': 'Forecasting and predictions'},
            {'name': 'Analysis Hub', 'desc': 'Portfolio attribution analysis'},
            {'name': 'Portfolio', 'desc': 'Portfolio tracking and management'},
            {'name': 'Options Lab', 'desc': 'Options trading and strategies'},
            {'name': 'Research Lab', 'desc': 'Research and backtesting'},
        ]
        for tab in tabs:
            if query_lower in tab['name'].lower() or query_lower in tab['desc'].lower():
                results.append({
                    'type': 'tabs',
                    'title': tab['name'],
                    'description': tab['desc'],
                    'href': f'#'
                })
    
    return results[:10]  # Limit to top 10 results

def register_search_callbacks(app):
    """Register global search callbacks"""
    from dash import Output, Input, State, callback_context, html
    import dash_bootstrap_components as dbc
    
    # Open/close modal
    @app.callback(
        Output('global-search-modal', 'is_open'),
        [Input('global-search-btn', 'n_clicks'),
         Input('global-search-close', 'n_clicks')],
        [State('global-search-modal', 'is_open')],
        prevent_initial_call=True
    )
    def toggle_search_modal(btn_click, close_click, is_open):
        return not is_open
    
    # Perform search
    @app.callback(
        Output('global-search-results', 'children'),
        [Input('global-search-input', 'value')],
        prevent_initial_call=True
    )
    def perform_search(query):
        if not query or len(query) < 2:
            return html.Div("Type at least 2 characters to search...", 
                          className="text-muted text-center py-4")
        
        results = search_database(query)
        
        if not results:
            return html.Div([
                html.I(className="fas fa-search fa-3x text-muted mb-2"),
                html.Div("No results found", className="text-muted")
            ], className="text-center py-4")
        
        return dbc.ListGroup([
            format_search_result(r['type'], r) for r in results
        ])
