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
                    html.H4("Loading...", className="text-muted mb-0", id="home-portfolio-value"),
                ], width=6),
                dbc.Col([
                    html.Div("Today's Change", className="small", style={'color': '#ffffff'}),
                    html.H4("Loading...", className="text-muted mb-0", id="home-portfolio-change"),
                ], width=6),
            ]),
            html.Hr(),
            dbc.Row([
                dbc.Col([
                    html.Div("Positions", className="small", style={'color': '#ffffff'}),
                    html.H5("--", className="mb-0 text-muted"),
                ], width=4),
                dbc.Col([
                    html.Div("Day High", className="small", style={'color': '#ffffff'}),
                    html.H5("--", className="mb-0 text-muted"),
                ], width=4),
                dbc.Col([
                    html.Div("Day Low", className="small", style={'color': '#ffffff'}),
                    html.H5("--", className="mb-0 text-muted"),
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
                        html.Small("--", id="market-sp500-pct", className="text-muted")
                    ], className="mb-2"),
                ], width=4),
                dbc.Col([
                    html.Div("NASDAQ", className="small", style={'color': '#ffffff'}),
                    html.H5([
                        html.Span("--", id="market-nasdaq-value"),
                        html.Small("--", id="market-nasdaq-pct", className="text-muted")
                    ], className="mb-2"),
                ], width=4),
                dbc.Col([
                    html.Div("DOW", className="small", style={'color': '#ffffff'}),
                    html.H5([
                        html.Span("--", id="market-dow-value"),
                        html.Small("--", id="market-dow-pct", className="text-muted")
                    ], className="mb-2"),
                ], width=4),
            ]),
            html.Hr(),
            # TradingView Widget - Iframe Embed (More Reliable)
            html.Iframe(
                src="https://s.tradingview.com/widgetembed/?frameElementId=tradingview_widget&symbol=SP%3ASPX&interval=D&hidesidetoolbar=0&symboledit=1&saveimage=1&toolbarbg=f1f3f6&theme=dark&style=1&timezone=Etc%2FUTC&studies=%5B%5D&locale=en&utm_source=localhost&utm_medium=widget&utm_campaign=chart&utm_term=SP%3ASPX",
                style={"height": "350px", "width": "100%", "border": "none"},
                id="tradingview_widget"
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
    """Create watchlist widget. Uses `data/watchlist.json` for persistence."""
    # Render container; items are filled by callbacks
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-star me-2"),
            html.Span("Watchlist", className="fw-bold")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col(dcc.Input(id='watch-add-input', placeholder='Enter ticker (e.g. AAPL)', persistence=True), width=7),
                dbc.Col(dbc.Button('Add', id='watch-add-btn', color='primary', className='w-100'), width=5),
            ], className='mb-3'),
            html.Div(id='watchlist-items-container')
        ])
    ], className="shadow-sm h-100")

def create_quick_actions_widget():
    """Create quick actions widget."""
    return dbc.Card([
        dbc.CardHeader([
            html.I(className="bi bi-lightning me-2"),
            html.Span("Quick Actions", className="fw-bold")
        ]),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Button([
                        html.I(className="bi bi-search me-2"),
                        "Scan Market"
                    ], id='home-scan-market', color="primary", className="w-100 mb-2"),
                ], width=12),
                dbc.Col([
                    dbc.Button([
                        html.I(className="bi bi-graph-up me-2"),
                        "Analyze"
                    ], id='home-analyze', color="info", className="w-100 mb-2"),
                ], width=12),
                dbc.Col([
                    dbc.Button([
                        html.I(className="bi bi-shield-check me-2"),
                        "Hedge Finder"
                    ], id='home-hedge-finder', color="warning", className="w-100 mb-2"),
                ], width=12),
                dbc.Col([
                    dbc.Button([
                        html.I(className="bi bi-gear me-2"),
                        "Settings"
                    ], id='home-settings', color="secondary", className="w-100"),
                ], width=12),
            ])
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

def layout():
    """Create the home tab layout."""
    return dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H3([
                    html.I(className="bi bi-house-door me-2"),
                    "Dashboard Home"
                ]),
                html.P(f"Welcome back! Last login: {datetime.now().strftime('%Y-%m-%d %H:%M')}", style={'color': '#ffffff'}),
                # Visible alert area for Quick Actions feedback
                dbc.Alert(id='home-action-alert', is_open=False, color='info', className='mt-2', style={'display': 'none'})
            ])
        ], className="mb-4"),
        
        # Widget grid - Row 1
        dbc.Row([
            dbc.Col(create_portfolio_widget(), width=6, id="widget-portfolio"),
            dbc.Col(create_market_overview_widget(), width=6, id="widget-market"),
        ], className="mb-4"),

        # Client-side navigation placeholder
        dcc.Location(id='home-nav', refresh=False),
        
        # Widget grid - Row 2
        dbc.Row([
            dbc.Col(create_watchlist_widget(), width=4, id="widget-watchlist"),
            dbc.Col(create_quick_actions_widget(), width=4, id="widget-actions"),
            dbc.Col(create_recent_trades_widget(), width=4, id="widget-trades"),
        ], className="mb-4"),
        
        # Customization hint
        dbc.Row([
            dbc.Col([
                dbc.Alert([
                    html.I(className="bi bi-info-circle me-2"),
                    "Tip: Customize your dashboard layout in Settings (drag & drop coming soon!)"
                ], color="info", className="mb-0")
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

    ], fluid=True, className="p-4")

def register_callbacks(app):
    """Register callbacks for the home tab."""
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
            
            return value_str, [
                change_str + " ",
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
                    
                    return value_str, [change_str + " ", html.Small(f"({pl_pct:+.2f}%)", className=change_class)]
            except Exception:
                pass

            # 3. Final Fallback (Snapshot or Offline)
            return "Service Offline", [html.Small("Connect Alpaca keys", style={'color': '#6c757d'})]

    @app.callback(
        Output('market-sp500-value', 'children'),
        Output('market-sp500-pct', 'children'),
        Output('market-nasdaq-value', 'children'),
        Output('market-nasdaq-pct', 'children'),
        Output('market-dow-value', 'children'),
        Output('market-dow-pct', 'children'),
        Output({'type': 'watch-price', 'index': dash.ALL}, 'children'),
        Output({'type': 'watch-change', 'index': dash.ALL}, 'children'),
        Input('interval-component', 'n_intervals')
    )
    def refresh_market_and_watchlist(n):
        """Fetch latest market indices and watchlist prices."""
        try:
            from ..utils.price_fetch import fetch_prices_batch
            
            # 1. Fetch Market Indices (SPY, QQQ, DIA)
            indices = ['SPY', 'QQQ', 'DIA']
            
            # 2. Fetch Watchlist Symbols
            try:
                import json, os
                wl_path = _watchlist_path()
                if os.path.exists(wl_path):
                    with open(wl_path, 'r') as f:
                        watchlist = json.load(f)
                else:
                    watchlist = ['AAPL', 'TSLA', 'NVDA', 'MSFT']
            except Exception:
                watchlist = ['AAPL', 'TSLA', 'NVDA', 'MSFT']
                
            # Combine all tickers for batch fetch
            all_tickers = indices + watchlist
            prices = fetch_prices_batch(all_tickers, parallelism=4, context='live')
            
            # Helper to format price
            def fmt_price(ticker):
                p = prices.get(ticker, {})
                if not p or p.get('last_price') is None:
                    return "--"
                return f"${p['last_price']:,.2f}"
                
            # Helper to format change
            def fmt_change(ticker):
                p = prices.get(ticker, {})
                if not p or p.get('last_price') is None or not p.get('prev_close'):
                    return html.Small("--", className="text-muted")
                
                try:
                    curr = p['last_price']
                    prev = p['prev_close']
                    pct = ((curr - prev) / prev) * 100
                    
                    color = "text-success" if pct >= 0 else "text-danger"
                    sign = "+" if pct >= 0 else ""
                    return html.Small(f"{sign}{pct:+.2f}%", className=color)
                except Exception:
                    return html.Small("--", className="text-muted")

            # Format Indices
            sp500_val, sp500_pct = fmt_price('SPY'), fmt_change('SPY')
            nasdaq_val, nasdaq_pct = fmt_price('QQQ'), fmt_change('QQQ')
            dow_val, dow_pct = fmt_price('DIA'), fmt_change('DIA')
            
            # Format Watchlist
            w_prices = [fmt_price(s) for s in watchlist]
            w_changes = [fmt_change(s) for s in watchlist]
            
            return sp500_val, sp500_pct, nasdaq_val, nasdaq_pct, dow_val, dow_pct, w_prices, w_changes
            
        except Exception as e:
            print(f"Error refreshing market data: {e}")
            # Return placeholders on error
            # We need to know the length of watchlist to return correct number of placeholders
            # If watchlist fetching also failed, default to a known list
            try:
                import json, os
                wl_path = _watchlist_path()
                if os.path.exists(wl_path):
                    with open(wl_path, 'r') as f:
                        watchlist_len = len(json.load(f))
                else:
                    watchlist_len = len(['AAPL', 'TSLA', 'NVDA', 'MSFT'])
            except Exception:
                watchlist_len = len(['AAPL', 'TSLA', 'NVDA', 'MSFT']) # Fallback if even path reading fails

            return "--", html.Small("--", className="text-muted"), \
                   "--", html.Small("--", className="text-muted"), \
                   "--", html.Small("--", className="text-muted"), \
                   ["--"] * watchlist_len, \
                   [html.Small("--", className="text-muted")] * watchlist_len

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
        """Unified watchlist handler: interval refresh, add item, and remove item all use the same output.

        Using a single callback prevents Dash 'Duplicate callback outputs' errors and keeps state persistence simple.
        """
        import json, os, ast
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
                # parse the pattern-matching id to get the symbol
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

        # Build rows for current list
        rows = []
        for s in arr:
            rows.append(
                dbc.Row([
                    dbc.Col(html.Strong(s, style={'color': '#ffffff'}), width=3),
                    dbc.Col(html.Span("--", id={'type':'watch-price', 'index': s},style={'color': '#ffffff'}), width=3),
                    dbc.Col(html.Span("--", id={'type':'watch-change', 'index': s}), width=4),
                    dbc.Col(dbc.Button('×', id={'type':'watch-remove', 'index': s}, color='danger', size='sm', className='btn-sm'), width=2),
                ], className='mb-2 align-items-center', style={'min-height': '32px'})
            )
        return rows

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
                html.P("Found 3 potential opportunities:", className="fw-bold"),
                dbc.ListGroup([
                    dbc.ListGroupItem([
                        html.Div([
                            html.H6("NVDA - High Volatility", className="mb-0"),
                            html.Small("IV Rank: 85% | RSI: 72", className="text-muted")
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
                                html.H6("Beta", className="text-muted"),
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
                html.P("Your portfolio is currently overweight Technology (45%). Consider diversifying into Healthcare or Utilities.", className="text-muted small")
            ])
            
        elif button_id == "home-hedge-finder":
            return True, html.Div([
                html.H5("Hedge Finder", className="mb-3"),
                dbc.Alert("Analyzing portfolio risk exposure...", color="warning"),
                html.P("Suggested Hedges:", className="fw-bold"),
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
                        html.Small(trade['timestamp'], className="text-muted")
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
