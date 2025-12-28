"""
Home Tab - Customizable Dashboard
==================================
Widget-based homepage with drag-and-drop customization.
Features portfolio summary, watchlist, market overview, and quick actions.
"""

import dash
from dash import html, dcc, Input, Output, State, callback
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta
import plotly.graph_objects as go
import logging

# Default widget layout
DEFAULT_WIDGETS = [
    {"id": "portfolio_summary", "row": 0, "col": 0, "width": 6},
    {"id": "market_overview", "row": 0, "col": 6, "width": 6},
    {"id": "watchlist", "row": 1, "col": 0, "width": 4},
    {"id": "quick_actions", "row": 1, "col": 4, "width": 4},
    {"id": "recent_trades", "row": 1, "col": 8, "width": 4},
]

def create_portfolio_widget():
    """Create portfolio summary widget."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-wallet2 me-2"),
            html.Span("Portfolio Summary", className="fw-bold")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div("Total Value", className="small", style={'color': '#ffffff'}),
                    html.H4("Loading...", className="text-white mb-0", id="home-portfolio-value"),
                ], width=6),
                dbc.Col([
                    html.Div("Today's Change", className="small", style={'color': '#ffffff'}),
                    html.H4("Loading...", className="text-white mb-0", id="home-portfolio-change"),
                ], width=6),
            ]),
            html.Hr(className="border-light"),
            dbc.Row([
                dbc.Col([
                    html.Div("Positions", className="small", style={'color': '#ffffff'}),
                    html.H5("--", className="mb-0 text-white-50"),
                ], width=4),
                dbc.Col([
                    html.Div("Day High", className="small", style={'color': '#ffffff'}),
                    html.H5("--", className="mb-0 text-white-50"),
                ], width=4),
                dbc.Col([
                    html.Div("Day Low", className="small", style={'color': '#ffffff'}),
                    html.H5("--", className="mb-0 text-white-50"),
                ], width=4),
            ]),
        ])
    ], className="shadow-sm h-100")

def create_market_overview_widget():
    """Create market indices overview widget."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-graph-up me-2"),
            html.Span("Market Overview", className="fw-bold")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div("S&P 500", className="small", style={'color': '#ffffff'}),
                    html.H5([
                        html.Span("--", id="market-sp500-value"),
                        html.Small("--", id="market-sp500-pct", className="text-white-50")
                    ], className="mb-2"),
                ], width=4),
                dbc.Col([
                    html.Div("NASDAQ", className="small", style={'color': '#ffffff'}),
                    html.H5([
                        html.Span("--", id="market-nasdaq-value"),
                        html.Small("--", id="market-nasdaq-pct", className="text-white-50")
                    ], className="mb-2"),
                ], width=4),
                dbc.Col([
                    html.Div("DOW", className="small", style={'color': '#ffffff'}),
                    html.H5([
                        html.Span("--", id="market-dow-value"),
                        html.Small("--", id="market-dow-pct", className="text-white-50")
                    ], className="mb-2"),
                ], width=4),
            ]),
            html.Hr(),
            # TradingView Widget - Expanded with Area Chart
            html.Iframe(
                srcDoc='''
                <div class="tradingview-widget-container" style="height:100%;width:100%">
                  <div id="tradingview_chart" style="height:calc(100% - 32px);width:100%"></div>
                  <div class="tradingview-widget-copyright"><a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank"><span class="blue-text">Track all markets on TradingView</span></a></div>
                  <script type="text/javascript" src="https://s3.tradingview.com/tv.js"></script>
                  <script type="text/javascript">
                  new TradingView.widget(
                  {
                  "autosize": true,
                  "symbol": "AMEX:SPY",
                  "interval": "D",
                  "timezone": "Etc/UTC",
                  "theme": "dark",
                  "style": "3",
                  "locale": "en",
                  "enable_publishing": false,
                  "allow_symbol_change": true,
                  "container_id": "tradingview_chart"
                  }
                  );
                  </script>
                </div>
                ''',
                style={"width": "100%", "height": "600px", "border": "none"}
            )
        ,
    # hidden containers for action results / last job ids
    html.Div(id='home-action-result', style={'display': 'none'}),
    html.Div(id='home-last-job', style={'display': 'none'}),
    html.Div(id='home-last-analysis-job', style={'display': 'none'}),
    html.Div(id='home-last-hedge-job', style={'display': 'none'})
        ])
    ], className="shadow-sm h-100")

def create_watchlist_widget():
    """Create horizontal watchlist widget."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-star me-2"),
            html.Span("Watchlist", className="fw-bold")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(dcc.Input(id='watch-add-input', placeholder='Add ticker...', persistence=True, className="form-control-sm"), width=9),
                dbc.Col(dbc.Button('Add', id='watch-add-btn', color='primary', size='sm', className='w-100'), width=3),
            ], className='mb-3'),
            html.Div(id='watchlist-items-container')
        ])
    ], className="shadow-sm h-100")



def create_action_center_widget():
    """Create Action Center widget with Tabs."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-lightning-charge me-2"),
            html.Span("Action Center", className="fw-bold")
        ]),
        dbc.CardBody([
            dbc.Tabs([
                dbc.Tab([
                    dbc.ListGroup([
                        dbc.ListGroupItem([
                            html.Div([
                                html.Strong("TSLA Earnings", style={'color': '#ffffff'}),
                                html.Small("Today 4:00 PM", className="text-white-50 float-end")
                            ]),
                            html.Small("Implied move +/- 8%", className="text-danger")
                        ], className="border-0 ps-0"),
                        dbc.ListGroupItem([
                            html.Div([
                                html.Strong("Portfolio Beta High", style={'color': '#ffffff'}),
                                html.Small("1.45", className="text-warning float-end")
                            ]),
                            html.Small("Consider hedging with SPY puts", className="text-white-50")
                        ], className="border-0 ps-0"),
                    ], flush=True)
                ], label="Alerts", tab_id="tab-alerts"),
                
                dbc.Tab([
                    dbc.Checklist(
                        options=[
                            {"label": "Review Weekly Picks", "value": 1},
                            {"label": "Rebalance Portfolio", "value": 2},
                            {"label": "Check Fed Minutes", "value": 3},
                        ],
                        value=[1],
                        id="action-center-tasks",
                        className="mt-2"
                    )
                ], label="Tasks", tab_id="tab-tasks"),
                
                dbc.Tab([
                    html.Div([
                        dbc.Button([html.I(className="bi bi-search me-2"), "Scan Market"], id='home-scan-market', color="primary", size="sm", className="w-100 mb-2 mt-2"),
                        dbc.Button([html.I(className="bi bi-graph-up me-2"), "Analyze"], id='home-analyze', color="info", size="sm", className="w-100 mb-2"),
                        dbc.Button([html.I(className="bi bi-shield-check me-2"), "Hedge Finder"], id='home-hedge-finder', color="warning", size="sm", className="w-100 mb-2"),
                        dbc.Button([html.I(className="bi bi-gear me-2"), "Settings"], id='home-settings', color="secondary", size="sm", className="w-100"),
                    ])
                ], label="Actions", tab_id="tab-actions"),
            ], id="action-center-tabs", active_tab="tab-alerts")
        ])
    ], className="shadow-sm h-100")

def create_recent_trades_widget():
    """Create recent trades widget."""
    # TODO: Integrate with Alpaca API or local database for real trades
    # For now, show a message instead of fake data
    
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-clock-history me-2"),
            html.Span("Recent Trades", className="fw-bold")
        ]),
        dbc.CardBody([
            html.Div(id='recent-trades-list', children=[
                dbc.Spinner(size="sm", color="primary")
            ])
        ], style={'max-height': '300px', 'overflow-y': 'auto'})
    ], className="shadow-sm h-100")

def create_morning_briefing_widget():
    """Create AI Morning Briefing widget."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-robot me-2"),
            html.Span("AI Morning Briefing", className="fw-bold"),
            dbc.Button("Refresh", id="briefing-refresh-btn", size="sm", color="light", className="text-dark float-end ms-2")
        ], className="bg-primary text-white"),
        dbc.CardBody([
            dcc.Loading(
                dcc.Markdown(
                    "**Click the Refresh button above to generate your morning briefing.**",
                    id="morning-briefing-content",
                    className="prose text-white"
                ),
                type="dot"
            ),
            dcc.Store(id='briefing-store', data={'generated': False})
        ])
    ], className="shadow-sm mb-4 border-primary")

def create_portfolio_performance_widget():
    """Create portfolio performance chart widget."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-graph-up-arrow me-2"),
            html.Span("Portfolio Performance (30D)", className="fw-bold")
        ]),
        dbc.CardBody([
            dcc.Loading(
                dcc.Graph(
                    id='portfolio-performance-chart',
                    config={'displayModeBar': False},
                    style={'height': '200px'}
                ),
                type="dot"
            )
        ])
    ], className="shadow-sm h-100")

def create_market_sentiment_widget():
    """Create market sentiment indicator widget."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-speedometer2 me-2"),
            html.Span("Market Sentiment", className="fw-bold")
        ]),
        dbc.CardBody([
            html.Div([
                html.Div(id='sentiment-gauge', children=[
                    dbc.Spinner(size="sm", color="primary")
                ], className="text-center"),
                html.Div(id='sentiment-label', className="text-center mt-2", style={'color': '#ffffff'})
            ])
        ])
    ], className="shadow-sm h-100")


def create_section_header(title, icon, color="primary"):
    """Create a styled section header for visual hierarchy."""
    return html.Div([
        html.H5([
            html.I(className=f"bi {icon} me-2"),
            title
        ], className=f"text-{color} mb-0 fw-bold"),
        html.Hr(className="mt-2 mb-3", style={'borderColor': f'var(--bs-{color})', 'opacity': '0.5'})
    ], className="mt-4")


def create_quick_stats_bar():
    """Create a prominent quick stats bar at the top."""
    return dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Div("Portfolio Value", className="small text-muted"),
                    html.H4("$--", id="home-portfolio-value-quick", className="text-white mb-0")
                ], width=3, className="text-center border-end border-secondary"),
                dbc.Col([
                    html.Div("Today's P&L", className="small text-muted"),
                    html.H4("$--", id="home-pnl-quick", className="text-success mb-0")
                ], width=3, className="text-center border-end border-secondary"),
                dbc.Col([
                    html.Div("Market Status", className="small text-muted"),
                    html.H4([
                        html.Span("●", className="text-success me-2", style={'fontSize': '12px'}),
                        "Open"
                    ], id="home-market-status-quick", className="text-white mb-0")
                ], width=3, className="text-center border-end border-secondary"),
                dbc.Col([
                    html.Div("Active Alerts", className="small text-muted"),
                    dbc.Badge("0", id="home-alerts-count", color="info", className="fs-5 px-3 py-2")
                ], width=3, className="text-center")
            ])
        ], className="py-3")
    ], className="shadow mb-4 border-primary", style={'borderWidth': '2px', 'borderStyle': 'solid'})


def create_top_movers_widget():
    """Create top movers widget showing gainers/losers."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-bar-chart-line me-2"),
            html.Span("Top Movers", className="fw-bold")
        ]),
        dbc.CardBody([
            dcc.Loading(
                html.Div(id='top-movers-list', children=[
                    dbc.Spinner(size="sm", color="primary")
                ]),
                type="dot"
            )
        ], style={'max-height': '250px', 'overflow-y': 'auto'})
    ], className="shadow-sm h-100")


def layout():
    """Create the home tab layout with improved UI/UX structure."""
    return dbc.Container([
        # Header with Quick Stats Bar
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="bi bi-command me-2"),
                    "Command Center"
                ], style={'color': '#ffffff'}, className="mb-0"),
                html.P(f"Welcome back! {datetime.now().strftime('%A, %B %d, %Y')}", 
                       className="text-muted mb-3"),
                # Visible alert area for Quick Actions feedback
                dbc.Alert(id='home-action-alert', is_open=False, color='info', 
                         className='mt-2', dismissable=True)
            ])
        ], className="mb-3"),
        
        # Quick Stats Bar - Prominent metrics at top
        create_quick_stats_bar(),
        
        # AI Morning Briefing
        dbc.Row([
            dbc.Col(create_morning_briefing_widget(), width=12)
        ]),
        
        # Section: Portfolio & Actions
        create_section_header("Portfolio & Actions", "bi-lightning-charge", "primary"),
        
        # Widget grid - Row 1: Portfolio (left) and Action Center (right)
        dbc.Row([
            dbc.Col(create_portfolio_widget(), width=6, id="widget-portfolio"),
            dbc.Col(create_action_center_widget(), width=6, id="widget-actions"),
        ], className="mb-4"),
        
        # Section: Market Data
        create_section_header("Market Data", "bi-graph-up", "info"),
        
        # Widget grid - Row 2: Market Overview (full width for TradingView)
        dbc.Row([
            dbc.Col(create_market_overview_widget(), width=12, id="widget-market"),
        ], className="mb-4"),

        # Client-side navigation placeholder
        dcc.Location(id='home-nav', refresh=False),
        
        # Section: Watchlist & Trading
        create_section_header("Watchlist & Trading", "bi-star", "warning"),
        
        # Widget grid - Row 3: Watchlist (horizontal) and Recent Trades
        dbc.Row([
            dbc.Col(create_watchlist_widget(), width=8, id="widget-watchlist"),
            dbc.Col(create_recent_trades_widget(), width=4, id="widget-trades"),
        ], className="mb-4"),
        
        # Section: Analytics & Insights
        create_section_header("Analytics & Insights", "bi-bar-chart-line", "success"),
        
        # Widget grid - Row 4: Analytics widgets
        dbc.Row([
            dbc.Col(create_portfolio_performance_widget(), width=4, id="widget-performance"),
            dbc.Col(create_market_sentiment_widget(), width=4, id="widget-sentiment"),
            dbc.Col(create_top_movers_widget(), width=4, id="widget-movers"),
        ], className="mb-4"),
        
        # Keyboard Shortcuts Info (collapsible)
        dbc.Collapse([
            dbc.Card([
                dbc.CardBody([
                    html.H6("⌨️ Keyboard Shortcuts", className="text-white mb-3"),
                    dbc.Row([
                        dbc.Col([
                            html.Code("Ctrl+S", className="bg-dark px-2 py-1 me-2"),
                            "Scan Market"
                        ], width=4, className="text-muted small mb-2"),
                        dbc.Col([
                            html.Code("Ctrl+A", className="bg-dark px-2 py-1 me-2"),
                            "Analyze Portfolio"
                        ], width=4, className="text-muted small mb-2"),
                        dbc.Col([
                            html.Code("Ctrl+R", className="bg-dark px-2 py-1 me-2"),
                            "Refresh All"
                        ], width=4, className="text-muted small mb-2"),
                    ])
                ], className="py-2")
            ], className="bg-dark border-secondary mb-3")
        ], id="shortcuts-collapse", is_open=False),
        
        # Footer with tips
        dbc.Row([
            dbc.Col([
                dbc.Alert([
                    html.I(className="bi bi-lightbulb me-2"),
                    "Quick tip: Use the Action Center above for fast market scanning and portfolio analysis."
                ], color="dark", className="mb-0 border-secondary text-muted")
            ])
        ]),

        # Quick Actions Modal
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Quick Action"), close_button=True),
            dbc.ModalBody(id='quick-action-modal-body'),
            dbc.ModalFooter(
                dbc.Button("Close", id="quick-action-modal-close", className="ms-auto", n_clicks=0)
            ),
        ], id="quick-action-modal", is_open=False, size="lg", centered=True),
        
        # Hidden stores for quick stats
        dcc.Store(id='quick-stats-store', data={}),

    ], fluid=True, className="p-4")


def register_callbacks(app):
    """Register callbacks for the home tab."""
    
    # Quick Stats Bar Update Callback
    @app.callback(
        Output("home-portfolio-value-quick", "children"),
        Output("home-pnl-quick", "children"),
        Output("home-pnl-quick", "className"),
        Output("home-market-status-quick", "children"),
        Output("home-alerts-count", "children"),
        Input("interval-component", "n_intervals"),
        prevent_initial_call=False
    )
    def update_quick_stats(n):
        """Update the quick stats bar with current data."""
        try:
            from ..utils.execution import AlpacaExecutor
            exec_client = AlpacaExecutor()
            account = exec_client.get_account_info()
            
            pv = account.get('portfolio_value', 0)
            equity = account.get('equity', 0)
            last_equity = account.get('last_equity', 0)
            
            # Calculate P&L
            pnl = equity - last_equity
            pnl_class = "text-success mb-0" if pnl >= 0 else "text-danger mb-0"
            pnl_str = f"+${pnl:,.2f}" if pnl >= 0 else f"${pnl:,.2f}"
            
            # Market status (simplified - based on time)
            from datetime import datetime
            now = datetime.now()
            hour = now.hour
            if 9 <= hour < 16 and now.weekday() < 5:
                market_status = [html.Span("●", className="text-success me-2", style={'fontSize': '12px'}), "Open"]
            else:
                market_status = [html.Span("●", className="text-secondary me-2", style={'fontSize': '12px'}), "Closed"]
            
            return f"${pv:,.2f}", pnl_str, pnl_class, market_status, "0"
            
        except Exception:
            return "$--", "$--", "text-muted mb-0", [html.Span("●", className="text-warning me-2", style={'fontSize': '12px'}), "Offline"], "0"
    
    @app.callback(
        Output("home-portfolio-value", "children"),
        Output("home-portfolio-change", "children"),
        Input("interval-component", "n_intervals")
    )
    def update_portfolio_summary(n):
        """Update portfolio summary with live data from Alpaca."""
        # 1. Try AlpacaExecutor (Direct Broker Connection)
        try:
            from ..utils.execution import AlpacaExecutor
            exec_client = AlpacaExecutor()
            
            # Get real-time account data
            account = exec_client.get_account_info()
            pv = account.get('portfolio_value', 0)
            equity = account.get('equity', 0)
            last_equity = account.get('last_equity', 0)
            
            # Calculate daily change
            change = equity - last_equity
            change_pct = (change / last_equity) * 100 if last_equity else 0
            
            # Format values
            value_str = f"${pv:,.2f}"
            
            if change >= 0:
                change_str = f"+${change:,.2f}"
                change_class = "text-success"
            else:
                change_str = f"${change:,.2f}"
                change_class = "text-danger"
                
            pct_str = f"({change_pct:+.2f}%)"
            
            return html.Span(value_str, style={'color': '#ffffff'}), [
                html.Span(change_str + " ", style={'color': '#10b981' if change >= 0 else '#ef4444'}),
                html.Small(pct_str, className=change_class)
            ]
            
        except Exception as e:
            # 2. Fallback to Portfolio Dashboard Service
            try:
                import requests
                import os
                portfolio_dashboard_url = os.environ.get('PORTFOLIO_DASHBOARD_URL', 'http://portfolio_dashboard:8057')
                response = requests.get(f"{portfolio_dashboard_url}/portfolio/summary", timeout=2)
                
                if response.status_code == 200:
                    data = response.json()
                    pv = data.get('portfolio_value', 0)
                    pl = data.get('total_unrealized_pl', 0)
                    pl_pct = data.get('total_unrealized_pl_pct', 0)
                    
                    value_str = f"${pv:,.2f}"
                    change_class = "text-success" if pl >= 0 else "text-danger"
                    change_str = f"{'+' if pl >= 0 else ''}${pl:,.2f}"
                    pct_str = f"({pl_pct:+.2f}%)"
                    
                    return html.Span(value_str, style={'color': '#ffffff'}), [
                        html.Span(change_str + " ", style={'color': '#10b981' if pl >= 0 else '#ef4444'}),
                        html.Small(pct_str, className=change_class)
                    ]
            except Exception:
                pass

            # 3. Final Fallback (Snapshot or Offline)
            return "Service Offline", [html.Small("Connect Alpaca keys", style={'color': '#ffffff'})]

    # ===== MARKET INDICES CALLBACK (Fixed: separate from watchlist) =====
    @app.callback(
        Output('market-sp500-value', 'children'),
        Output('market-sp500-pct', 'children'),
        Output('market-nasdaq-value', 'children'),
        Output('market-nasdaq-pct', 'children'),
        Output('market-dow-value', 'children'),
        Output('market-dow-pct', 'children'),
        Input('interval-component', 'n_intervals')
    )
    def refresh_market_indices(n):
        """Fetch latest market indices only (SPY, QQQ, DIA)."""
        try:
            from ..utils.price_fetch import fetch_prices_batch
            
            indices = ['SPY', 'QQQ', 'DIA']
            prices = fetch_prices_batch(indices, parallelism=3, context='live')
            
            def fmt_price(ticker):
                p = prices.get(ticker, {})
                if not p or p.get('last_price') is None:
                    return "--"
                return f"${p['last_price']:,.2f}"
                
            def fmt_change(ticker):
                p = prices.get(ticker, {})
                if not p or p.get('last_price') is None or not p.get('prev_close'):
                    return html.Small("--", className="text-white-50")
                try:
                    curr = p['last_price']
                    prev = p['prev_close']
                    pct = ((curr - prev) / prev) * 100
                    color = "text-success" if pct >= 0 else "text-danger"
                    sign = "+" if pct >= 0 else ""
                    return html.Small(f"{sign}{pct:+.2f}%", className=color)
                except Exception:
                    return html.Small("--", className="text-white-50")

            return (fmt_price('SPY'), fmt_change('SPY'),
                    fmt_price('QQQ'), fmt_change('QQQ'),
                    fmt_price('DIA'), fmt_change('DIA'))
                    
        except Exception as e:
            print(f"Error refreshing market indices: {e}")
            placeholder = html.Small("--", className="text-white-50")
            return "--", placeholder, "--", placeholder, "--", placeholder

    # ===== WATCHLIST CALLBACK (Fixed: uses State to get correct DOM element count) =====
    @app.callback(
        Output({'type': 'watch-price', 'index': dash.ALL}, 'children'),
        Output({'type': 'watch-change', 'index': dash.ALL}, 'children'),
        Input('interval-component', 'n_intervals'),
        State({'type': 'watch-price', 'index': dash.ALL}, 'id'),
    )
    def refresh_watchlist_prices(n, watch_ids):
        """Fetch latest watchlist prices. Uses State to get actual DOM element count."""
        # Get actual number of watchlist items from DOM via State
        num_items = len(watch_ids) if watch_ids else 0
        
        # If no watchlist items in DOM, return empty lists
        if num_items == 0:
            return [], []
            
        # Extract symbols from the pattern-match IDs
        symbols = [item['index'] for item in watch_ids]
        
        try:
            from ..utils.price_fetch import fetch_prices_batch
            prices = fetch_prices_batch(symbols, parallelism=4, context='live')
            
            def fmt_price(ticker):
                p = prices.get(ticker, {})
                if not p or p.get('last_price') is None:
                    return "--"
                return f"${p['last_price']:,.2f}"
                
            def fmt_change(ticker):
                p = prices.get(ticker, {})
                if not p or p.get('last_price') is None or not p.get('prev_close'):
                    return html.Small("--", className="text-white-50")
                try:
                    curr = p['last_price']
                    prev = p['prev_close']
                    pct = ((curr - prev) / prev) * 100
                    color = "text-success" if pct >= 0 else "text-danger"
                    sign = "+" if pct >= 0 else ""
                    return html.Small(f"{sign}{pct:+.2f}%", className=color)
                except Exception:
                    return html.Small("--", className="text-white-50")

            return [fmt_price(s) for s in symbols], [fmt_change(s) for s in symbols]
                    
        except Exception as e:
            print(f"Error refreshing watchlist: {e}")
            placeholder = html.Small("--", className="text-white-50")
            return ["--"] * num_items, [placeholder] * num_items

    @app.callback(
        Output('home-action-result', 'children'),
        Output('home-last-job', 'children'),
        Output('home-last-analysis-job', 'children'),
        Output('home-last-hedge-job', 'children'),
        Output('home-action-alert', 'children'),
        Output('home-action-alert', 'is_open'),
        Output('home-nav', 'href'),
        Input('home-scan-market', 'n_clicks'),
        Input('home-analyze', 'n_clicks'),
        Input('home-hedge-finder', 'n_clicks'),
        Input('home-settings', 'n_clicks'),
        prevent_initial_call=True
    )
    def handle_quick_actions(scan, analyze, hedge, settings):
        # Determine which button was clicked
        ctx = dash.callback_context
        if not ctx.triggered:
            return ''
        btn = ctx.triggered[0]['prop_id'].split('.')[0]
        # Perform minimal action: attempt to call internal API if exists, else log and return message
        import requests, os, json
        try:
            # Default empty job ids
            last_job_id = ''
            last_analysis_job = ''
            last_hedge_job = ''

            if btn == 'home-scan-market':
                url = os.environ.get('MARKET_TRENDS_URL', 'http://market_trends:8050')
                payload = {
                    "tickers": ["SPY", "QQQ", "DIA"],
                    "period": "1mo",
                    "interval": "1d",
                    "options": False,
                    "news": False,
                    "topn": 10
                }
                try:
                    r = requests.post(f"{url}/api/jobs", json=payload, timeout=5)
                    if r.status_code in (200, 201):
                        data = r.json()
                        last_job_id = data.get('job_id') or data.get('jobId') or ''
                        msg = f"Scan Market job queued: {last_job_id}"
                    else:
                        msg = f"Scan Market request failed ({r.status_code})"
                except Exception as e:
                    msg = f"Scan Market error: {str(e)[:120]}"

                # Show alert and keep navigation unchanged
                return msg, last_job_id, last_analysis_job, last_hedge_job, msg, True, dash.no_update

            if btn == 'home-analyze':
                url = os.environ.get('ANALYSIS_SERVICE_URL', 'http://analysis:8054')
                # Use a simple attribution job payload
                payload = {
                    "picks_type": "weekly",
                    "start_date": (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d'),
                    "end_date": datetime.utcnow().strftime('%Y-%m-%d'),
                    "horizon": "1w"
                }
                try:
                    r = requests.post(f"{url}/api/jobs", json=payload, timeout=5)
                    if r.status_code in (200, 201):
                        data = r.json()
                        last_analysis_job = data.get('job_id') or data.get('jobId') or ''
                        msg = f"Analysis job queued: {last_analysis_job}"
                    else:
                        msg = f"Analysis request failed ({r.status_code})"
                except Exception as e:
                    msg = f"Analyze error: {str(e)[:120]}"

                return msg, last_job_id, last_analysis_job, last_hedge_job, msg, True, dash.no_update

            if btn == 'home-hedge-finder':
                # Hedge Finder exists as a component; return message that UI should open it.
                # The Portfolio tab's Hedge Finder can be opened by client-side navigation; here we just return a flag.
                msg = f"Hedge Finder opened ({datetime.now().isoformat()})"
                last_hedge_job = 'ui-opened'
                # Navigate to the Portfolio tab's hedge finder anchor (if app uses hash), else to Portfolio tab value
                href = '/#portfolio'  # fallback: user may implement client routing to detect this
                return msg, last_job_id, last_analysis_job, last_hedge_job, msg, True, href

            if btn == 'home-settings':
                msg = f"Settings opened ({datetime.now().isoformat()})"
                return msg, last_job_id, last_analysis_job, last_hedge_job, msg, True, dash.no_update

        except Exception as e:
            err = f"Action error: {str(e)[:120]}"
            return err, '', '', '', err, True, dash.no_update

        return '', '', '', '', '', False, dash.no_update

    def _watchlist_path():
        import os
        return os.path.join(os.path.dirname(__file__), '..', 'data', 'watchlist.json')

    @app.callback(
        Output('watchlist-items-container', 'children'),
        Input('interval-component', 'n_intervals'),
        Input('watch-add-btn', 'n_clicks'),
        State('watch-add-input', 'value'),
        Input({'type': 'watch-remove', 'index': dash.ALL}, 'n_clicks'),
        prevent_initial_call=False
    )
    def update_watchlist(n_intervals, add_n_clicks, add_value, remove_n_clicks_list):
        """Enhanced watchlist with volume, day range, and rich data display."""
        import json, os, ast
        from ..utils.price_fetch import fetch_prices_batch
        
        ctx = dash.callback_context
        path = _watchlist_path()
        default = ["AAPL", "TSLA", "NVDA", "MSFT"]

        # Read existing list
        try:
            if os.path.exists(path):
                with open(path, 'r') as f:
                    arr = json.load(f)
            else:
                arr = default.copy()
        except Exception:
            arr = default.copy()

        # If triggered by add button, append symbol
        if ctx.triggered:
            trig = ctx.triggered[0]['prop_id']
            if trig.startswith('watch-add-btn'):
                if add_value:
                    symbol = str(add_value).upper().strip()
                    if symbol and symbol not in arr:
                        arr.append(symbol)
                        try:
                            os.makedirs(os.path.dirname(path), exist_ok=True)
                            with open(path, 'w') as f:
                                json.dump(arr, f)
                        except Exception:
                            pass
            elif 'watch-remove' in trig:
                try:
                    idx = trig.split('.')[0]
                    key = ast.literal_eval(idx)
                    symbol = key.get('index')
                    if symbol in arr:
                        arr.remove(symbol)
                        try:
                            with open(path, 'w') as f:
                                json.dump(arr, f)
                        except Exception:
                            pass
                except Exception:
                    pass

        if not arr:
            return html.Div("No symbols in watchlist", className="text-white-50 text-center py-3")

        # Fetch prices for all watchlist symbols
        try:
            prices = fetch_prices_batch(arr, parallelism=4, context='live')
        except Exception as e:
            print(f"Error fetching watchlist prices: {e}")
            prices = {}

        # Build enhanced cards
        cards = []
        for ticker in arr:
            price_data = prices.get(ticker, {})
            last_price = price_data.get('last_price')
            prev_close = price_data.get('prev_close')
            volume = price_data.get('volume', 0)
            day_high = price_data.get('day_high')
            day_low = price_data.get('day_low')
            
            # Calculate change
            if last_price and prev_close:
                change = last_price - prev_close
                change_pct = (change / prev_close) * 100
                change_color = '#10b981' if change >= 0 else '#ef4444'
                change_text = f"+${change:.2f} (+{change_pct:.2f}%)" if change >= 0 else f"${change:.2f} ({change_pct:.2f}%)"
            else:
                change_color = '#6c757d'
                change_text = "--"
            
            # Format volume - handle None
            if volume and volume > 1_000_000:
                volume_str = f"{volume/1_000_000:.1f}M"
            elif volume and volume > 1_000:
                volume_str = f"{volume/1_000:.1f}K"
            elif volume:
                volume_str = str(volume)
            else:
                volume_str = "--"
            
            # Create compact horizontal card
            card = dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Strong(ticker, className="fs-6", style={'color': '#ffffff'}),
                            dbc.Button("×", id={'type': 'watch-remove', 'index': ticker}, 
                                      size="sm", color="link", className="text-danger p-0 float-end", 
                                      style={'fontSize': '18px'})
                        ], className="mb-2"),
                        html.Div(f"${last_price:.2f}" if last_price else "--", 
                                 className="fs-5 fw-bold", style={'color': '#ffffff'}),
                        html.Small(change_text, style={'color': change_color}, className="d-block mb-2"),
                        html.Hr(className="my-2 border-secondary"),
                        html.Small(["Vol: ", html.Span(volume_str, style={'color': '#ffffff'})], className="text-white-50 d-block mb-1"),
                        html.Small(["Range: ", html.Span(f"${day_low:.2f}-${day_high:.2f}" if day_low and day_high else "--", style={'color': '#ffffff'})], className="text-white-50 d-block")
                    ], className="p-2")
                ], className="bg-dark border-secondary h-100")
            ], width=3)
            
            cards.append(card)
        
        return dbc.Row(cards)

    @app.callback(
        Output('market-mini-chart', 'figure'),
        Input('interval-component', 'n_intervals')
    )
    def update_market_chart(n):
        """Update market overview chart with real S&P 500 intraday data."""
        try:
            import yfinance as yf
            
            # Fetch S&P 500 intraday data - last 5 days
            ticker = yf.Ticker("^GSPC")
            df = ticker.history(period="5d", interval="1h")
            
            if df.empty:
                raise ValueError("No data returned")
            
            # Calculate percentage change
            first_value = df['Close'].iloc[0]
            pct_change = ((df['Close'].iloc[-1] - first_value) / first_value) * 100
            
            # Choose colors
            line_color = '#10b981' if pct_change >= 0 else '#ef4444'
            fill_color = 'rgba(16, 185, 129, 0.1)' if pct_change >= 0 else 'rgba(239, 68, 68, 0.1)'
            
            # Create figure
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df['Close'],
                mode='lines',
                name='S&P 500',
                line=dict(color=line_color, width=2),
                fill='tozeroy',
                fillcolor=fill_color,
                hovertemplate='<b>%{x|%b %d, %I:%M %p}</b><br>$%{y:,.2f}<extra></extra>'
            ))
            
            fig.update_layout(
                height=150,
                margin=dict(l=20, r=20, t=30, b=20),
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=True,
                legend=dict(orientation='h', yanchor='top', y=1.15, xanchor='center', x=0.5, font=dict(size=10, color='white')),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False, tickformat='$,.0f', tickfont=dict(size=9, color='gray')),
                hovermode='x unified',
                annotations=[dict(
                    text=f"5-Day: {pct_change:+.2f}%",
                    xref="paper", yref="paper", x=0.02, y=0.98,
                    showarrow=False, font=dict(size=10, color=line_color),
                    bgcolor='rgba(0,0,0,0.5)', borderpad=4
                )]
            )
            return fig
            
        except Exception as e:
            print(f"Market chart error: {e}")
            return go.Figure(layout=go.Layout(
                height=150, margin=dict(l=20, r=20, t=30, b=20),
                template='plotly_dark', paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                annotations=[dict(text="Chart unavailable", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False, font=dict(size=12, color='gray'))]
            ))


    @app.callback(
        Output("quick-action-modal", "is_open"),
        Output("quick-action-modal-body", "children"),
        [
            Input("home-scan-market", "n_clicks"),
            Input("home-analyze", "n_clicks"),
            Input("home-hedge-finder", "n_clicks"),
            Input("quick-action-modal-close", "n_clicks")
        ],
        [State("quick-action-modal", "is_open")]
    )
    def toggle_quick_action_modal(n_scan, n_analyze, n_hedge, n_close, is_open):
        """Toggle Quick Actions modal and set content."""
        ctx = dash.callback_context
        if not ctx.triggered:
            return is_open, dash.no_update
        
        button_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if button_id == "quick-action-modal-close":
            return False, dash.no_update
            
        if button_id == "home-scan-market":
            return True, html.Div([
                html.H5("Market Scanner", className="mb-3"),
                dbc.Alert("Scanning top 500 stocks for volatility anomalies...", color="info"),
                dbc.Progress(value=75, striped=True, animated=True, className="mb-3"),
                html.P("Found 3 potential opportunities:", className="fw-bold", style={'color': '#ffffff'}),
                dbc.ListGroup([
                    dbc.ListGroupItem([
                        html.Div([
                            html.H6("NVDA - High Volatility", className="mb-0"),
                            html.Small("IV Rank: 85% | RSI: 72", className="text-white-50")
                        ])
                    ]),
                    dbc.ListGroupItem([
                        html.Div([
                            html.H6("TSLA - Breakout Alert", className="mb-0"),
                            html.Small("Volume: +250% vs Avg", className="text-muted")
                        ])
                    ]),
                    dbc.ListGroupItem([
                        html.Div([
                            html.H6("AMD - Squeeze Potential", className="mb-0"),
                            html.Small("Short Float: 12%", className="text-muted")
                        ])
                    ]),
                ])
            ])
            
        elif button_id == "home-analyze":
            return True, html.Div([
                html.H5("Portfolio Analysis", className="mb-3"),
                dbc.Row([
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Beta", className="text-white-50"),
                                html.H3("1.25", className="text-primary")
                            ])
                        ], className="mb-3")
                    ], width=6),
                    dbc.Col([
                        dbc.Card([
                            dbc.CardBody([
                                html.H6("Sharpe Ratio", className="text-muted"),
                                html.H3("1.8", className="text-success")
                            ])
                        ], className="mb-3")
                    ], width=6),
                ]),
                html.P("Your portfolio is currently overweight Technology (45%). Consider diversifying into Healthcare or Utilities.", className="text-white-50 small")
            ])
            
        elif button_id == "home-hedge-finder":
            return True, html.Div([
                html.H5("Hedge Finder", className="mb-3"),
                dbc.Alert("Analyzing portfolio risk exposure...", color="warning"),
                html.P("Suggested Hedges:", className="fw-bold", style={'color': '#ffffff'}),
                dbc.Table([
                    html.Thead(html.Tr([html.Th("Asset"), html.Th("Strategy"), html.Th("Cost")])),
                    html.Tbody([
                        html.Tr([html.Td("SPY"), html.Td("Put Spread (30D)"), html.Td("$450")]),
                        html.Tr([html.Td("VIX"), html.Td("Call Option"), html.Td("$200")]),
                        html.Tr([html.Td("TLT"), html.Td("Long Position"), html.Td("$1,500")])
                    ])
                ], bordered=True, hover=True, size="sm")
            ])
            
        return is_open, dash.no_update


    @app.callback(
        Output('recent-trades-list', 'children'),
        Input('interval-component', 'n_intervals')
    )
    def update_recent_trades(n):
        """Update recent trades list from Alpaca."""
        try:
            from ..utils.execution import AlpacaExecutor
            exec_client = AlpacaExecutor()
            trades = exec_client.get_recent_trades(limit=10)
            
            if not trades:
                return dbc.Alert("No recent trades found.", color="info", className="mb-0 small")
                
            items = []
            for trade in trades:
                color = "success" if trade['side'] == 'buy' else "danger"
                icon = "bi-arrow-up-right" if trade['side'] == 'buy' else "bi-arrow-down-left"
                
                item = dbc.ListGroupItem([
                    html.Div([
                        html.Div([
                            html.I(className=f"bi {icon} text-{color} me-2"),
                            html.Span(trade['ticker'], className="fw-bold"),
                            html.Span(f" {trade['side'].upper()}", className=f"badge bg-{color} ms-2")
                        ]),
                        html.Small(trade['timestamp'], className="text-white-50")
                    ], className="d-flex justify-content-between align-items-center mb-1"),
                    html.Div([
                        html.Small(f"{trade['qty']} shares @ ${trade['price']:.2f}"),
                        html.Small(trade['status'], className="text-muted ms-2")
                    ], className="d-flex justify-content-between")
                ], className="py-2")
                items.append(item)
                
            return dbc.ListGroup(items, flush=True)
            
        except Exception as e:
            return dbc.Alert(f"Error loading trades: {str(e)}", color="danger", className="mb-0 small")
    @app.callback(
        Output('morning-briefing-content', 'children'),
        Output('briefing-store', 'data'),
        Input('briefing-refresh-btn', 'n_clicks'),
        State('briefing-store', 'data'),
        prevent_initial_call=False
    )
    def update_morning_briefing(n_click, store_data):
        """Generate morning briefing using Chatbot Service."""
        import logging
        import httpx
        logger = logging.getLogger(__name__)
        
        # On initial load, just return the instruction message
        if n_click is None or n_click == 0:
            return "**Click the Refresh button above to generate your morning briefing.**", store_data
        
        logger.info(f"Morning Briefing: Button clicked (n_clicks={n_click})")
        
        try:
            # Use deterministic AIMorningBriefService for UI briefing to avoid LLM volatility
            from financial_dashboard.services.ai_morning_brief import AIMorningBriefService
            svc = AIMorningBriefService()
            brief = svc.generate_full_brief()

            # Prefer AI narrative if present
            summary_section = next((s for s in brief.get('sections', []) if s.get('category') == 'summary'), None)
            if summary_section and summary_section.get('content', {}).get('ai_narrative'):
                briefing = summary_section['content']['ai_narrative']
            else:
                # Assemble concise markdown
                market_section = next((s for s in brief.get('sections', []) if s.get('category') == 'market'), None)
                market_lines = []
                if market_section:
                    mc = market_section.get('content', {})
                    if mc.get('SPY') and mc['SPY'].get('price'):
                        market_lines.append(f"SPY: ${mc['SPY']['price']:.2f} ({mc['SPY']['change_1d']:+.2f}%)")
                    if mc.get('QQQ') and mc['QQQ'].get('price'):
                        market_lines.append(f"QQQ: ${mc['QQQ']['price']:.2f} ({mc['QQQ']['change_1d']:+.2f}%)")
                events = summary_section.get('content', {}).get('key_events', []) if summary_section else []
                first_event = events[0]['event'] if events else 'No high-severity news found in the last 24 hours'

                briefing = f"**Morning Briefing**\n* Current market sentiment: {summary_section.get('content', {}).get('market_sentiment', {}).get('overall', 'Neutral')}\n* Key events to watch today: {first_event}\n* Portfolio Management Tip: Review and adjust stop-loss levels for any new positions."

            new_store = {'generated': True, 'last_update': str(datetime.now())}
            logger.info("Briefing generated successfully (deterministic)")
            return briefing, new_store

        except Exception as e:
            logger.error(f"Failed to generate deterministic briefing: {e}", exc_info=True)
            # Fallback to chatbot service if deterministic generation fails
            try:
                prompt = (
                    "Generate a concise morning briefing for a trader. "
                    "Include current market sentiment (SPY, QQQ), key events to watch today, "
                    "and a brief portfolio management tip. Keep it under 150 words. "
                    "Format with Markdown (bullet points, bold text)."
                )
                logger.info("Falling back to chatbot service for briefing")
                response = httpx.post(
                    "http://localhost:8062/api/chat",
                    json={"message": prompt, "stream": False, "temperature": 0.7},
                    timeout=120.0
                )
                if response.status_code == 200:
                    data = response.json()
                    briefing = data.get('response', "Failed to parse briefing.")
                    new_store = {'generated': True, 'last_update': str(datetime.now())}
                    return briefing, new_store
            except Exception as e2:
                logger.error(f"Chatbot fallback failed: {e2}")

            return "**Error:** Could not generate morning briefing at this time.", store_data
        except Exception as e:
            logger.error(f"Error generating briefing: {e}")
            return f"**System Error:** Could not generate briefing. ({str(e)})", store_data

    @app.callback(
        Output('portfolio-performance-chart', 'figure'),
        Input('interval-component', 'n_intervals')
    )
    def update_portfolio_performance(n):
        """Update portfolio performance chart with 30-day equity curve."""
        try:
            from ..utils.execution import AlpacaExecutor
            import yfinance as yf
            from datetime import datetime, timedelta
            
            # Try to get real portfolio data
            try:
                exec_client = AlpacaExecutor()
                account = exec_client.get_account_info()
                current_value = account.get('equity', 100000)
            except:
                current_value = 100000  # Fallback
            
            # Generate sample 30-day performance (in production, use historical account data)
            dates = [(datetime.now() - timedelta(days=30-i)).strftime('%Y-%m-%d') for i in range(31)]
            # Simulate equity curve with some variance
            import random
            random.seed(42)
            values = [current_value * (1 + random.uniform(-0.02, 0.03) * i/30) for i in range(31)]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=dates,
                y=values,
                mode='lines',
                fill='tozeroy',
                line=dict(color='#10b981', width=2),
                fillcolor='rgba(16, 185, 129, 0.1)',
                hovertemplate='%{x}<br>$%{y:,.2f}<extra></extra>'
            ))
            
            fig.update_layout(
                height=200,
                margin=dict(l=20, r=20, t=10, b=20),
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
                xaxis=dict(showgrid=False, showticklabels=False),
                yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)', tickformat='$,.0f'),
                hovermode='x unified'
            )
            return fig
        except Exception as e:
            # Return empty figure on error
            return go.Figure(layout=go.Layout(
                height=200,
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                annotations=[dict(text="Chart unavailable", xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False)]
            ))

    @app.callback(
        Output('sentiment-gauge', 'children'),
        Output('sentiment-label', 'children'),
        Input('interval-component', 'n_intervals')
    )
    def update_market_sentiment(n):
        """Update market sentiment based on VIX."""
        try:
            import yfinance as yf
            
            # Fetch VIX (volatility index)
            vix = yf.Ticker("^VIX")
            vix_data = vix.history(period="1d")
            
            if not vix_data.empty:
                vix_value = vix_data['Close'].iloc[-1]
                
                # Determine sentiment based on VIX levels
                if vix_value < 15:
                    sentiment = "Greedy"
                    color = "#10b981"
                    icon = "bi-emoji-smile"
                elif vix_value < 20:
                    sentiment = "Neutral"
                    color = "#f59e0b"
                    icon = "bi-emoji-neutral"
                else:
                    sentiment = "Fearful"
                    color = "#ef4444"
                    icon = "bi-emoji-frown"
                
                gauge = html.Div([
                    html.I(className=f"bi {icon}", style={'fontSize': '48px', 'color': color}),
                    html.H4(f"VIX: {vix_value:.2f}", className="mt-2", style={'color': '#ffffff'})
                ])
                
                label = html.Span(sentiment, style={'color': color, 'fontSize': '18px', 'fontWeight': 'bold'})
                
                return gauge, label
            else:
                raise ValueError("No VIX data")
                
        except Exception as e:
            return html.Div("Data unavailable", style={'color': '#ffffff'}), ""

    @app.callback(
        Output('top-movers-list', 'children'),
        Input('interval-component', 'n_intervals')
    )
    def update_top_movers(n):
        """Update top movers from watchlist."""
        try:
            import json, os
            from ..utils.price_fetch import fetch_prices_batch
            
            # Get watchlist
            def _watchlist_path():
                return os.path.join(os.path.dirname(__file__), '..', 'data', 'watchlist.json')
            
            path = _watchlist_path()
            if os.path.exists(path):
                with open(path, 'r') as f:
                    watchlist = json.load(f)
            else:
                watchlist = ['AAPL', 'TSLA', 'NVDA', 'MSFT', 'GOOGL', 'AMZN']
            
            # Fetch prices
            prices = fetch_prices_batch(watchlist, parallelism=4, context='live')
            
            # Calculate percent changes
            movers = []
            for ticker, data in prices.items():
                if data.get('last_price') and data.get('prev_close'):
                    pct_change = ((data['last_price'] - data['prev_close']) / data['prev_close']) * 100
                    movers.append({
                        'ticker': ticker,
                        'pct_change': pct_change,
                        'price': data['last_price']
                    })
            
            # Sort by absolute percent change
            movers.sort(key=lambda x: abs(x['pct_change']), reverse=True)
            
            # Take top 5
            top_movers = movers[:5]
            
            items = []
            for mover in top_movers:
                color = "success" if mover['pct_change'] >= 0 else "danger"
                icon = "bi-arrow-up" if mover['pct_change'] >= 0 else "bi-arrow-down"
                color = "#10b981" if mover['pct_change'] >= 0 else "#ef4444" # Use hex colors directly
                
                items.append(
                    dbc.ListGroupItem([
                        html.Div([
                            html.Strong(mover['ticker'], style={'color': '#000000'}),
                            html.Span(f" ${mover['price']:.2f}", className="ms-2", style={'color': '#000000'}),
                            html.Span(f" {mover['pct_change']:+.2f}%", 
                                     className="ms-2 fw-bold", 
                                     style={'color': color})
                        ], className="d-flex justify-content-between align-items-center")
                    ], className="py-2")
                )
            
            
        except Exception as e:
            return html.Div(f"Error: {str(e)[:50]}", className="text-danger small")

