"""
Command Center Callbacks
Thin callback layer that delegates to server endpoints or uses direct integrations.
"""

from dash import Input, Output, State, callback_context, html
from dash.exceptions import PreventUpdate
import logging
import httpx
import os
import json
from pathlib import Path

logger = logging.getLogger(__name__)

# Base URLs for internal API calls
CC_BASE_URL = os.getenv("CC_BASE_URL", "http://localhost:8050")


def get_alpaca_positions():
    """Get positions directly from Alpaca API."""
    try:
        from alpaca.trading.client import TradingClient
        
        # Check for Alpaca credentials
        key = os.getenv("APCA_API_KEY_ID") or os.getenv("ALPACA2_KEY")
        secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv("ALPACA2_SECRET")
        
        if not key or not secret:
            return None
            
        client = TradingClient(key, secret, paper=True)
        account = client.get_account()
        positions = client.get_all_positions()
        
        return {
            "account": {
                "equity": float(account.equity),
                "cash": float(account.cash),
                "buying_power": float(account.buying_power)
            },
            "positions": [
                {
                    "symbol": p.symbol,
                    "qty": float(p.qty),
                    "current_price": float(p.current_price),
                    "market_value": float(p.market_value),
                    "unrealized_pl": float(p.unrealized_pl),
                    "unrealized_plpc": float(p.unrealized_plpc) * 100
                }
                for p in positions
            ]
        }
    except Exception as e:
        logger.warning(f"Alpaca positions fetch failed: {e}")
        return None


def register_callbacks(app):
    """
    Register Command Center callbacks.
    All callbacks are thin and delegate to server endpoints.
    """
    logger.info("🔧 Registering Command Center callbacks")
    
    # Callback 1: Run smoke tests
    @app.callback(
        Output("cc-smoke-results", "data"),
        Output("cc-system-status", "children"),
        Output("cc-system-status", "color"),
        Input("cc-run-smoke-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def run_smoke_tests(n_clicks):
        """Run smoke tests via API endpoint"""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            response = httpx.post(
                f"{CC_BASE_URL}/api/cc/run_smoke",
                timeout=30.0
            )
            response.raise_for_status()
            results = response.json()
            
            if results.get("all_passed", False):
                return (
                    results,
                    f"✅ All smoke tests passed ({results.get('passed', 0)}/{results.get('total', 0)})",
                    "success"
                )
            else:
                return (
                    results,
                    f"⚠️ Some tests failed ({results.get('passed', 0)}/{results.get('total', 0)})",
                    "warning"
                )
        except Exception as e:
            logger.exception("Smoke test error")
            return (
                {"error": str(e)},
                f"❌ Smoke tests failed: {str(e)[:100]}",
                "danger"
            )
    
    # Callback 2: Load portfolio snapshot
    @app.callback(
        Output("cc-portfolio-snapshot", "children"),
        Input("cc-refresh-btn", "n_clicks"),
        Input("cc-auto-refresh", "n_intervals"),
        prevent_initial_call=False
    )
    def load_portfolio_snapshot(n_clicks, n_intervals):
        """Load portfolio snapshot directly from Alpaca or cache"""
        from dash import html
        import dash_bootstrap_components as dbc
        
        try:
            # Try direct Alpaca integration first
            data = get_alpaca_positions()
            
            if data and data.get("positions"):
                positions = data["positions"]
                account = data.get("account", {})
                
                # Build a nice portfolio card
                position_items = []
                for p in positions[:5]:  # Show top 5
                    pl_color = "text-success" if p['unrealized_pl'] >= 0 else "text-danger"
                    pl_sign = "+" if p['unrealized_pl'] >= 0 else ""
                    position_items.append(
                        html.Div([
                            html.Div([
                                html.Strong(p['symbol'], className="me-2"),
                                html.Span(f"{int(p['qty'])} shares", className="text-muted small")
                            ]),
                            html.Div([
                                html.Span(f"${p['current_price']:.2f}", className="me-2"),
                                html.Span(f"{pl_sign}${p['unrealized_pl']:.2f} ({pl_sign}{p['unrealized_plpc']:.1f}%)", 
                                         className=pl_color + " small")
                            ])
                        ], className="d-flex justify-content-between py-1 border-bottom")
                    )
                
                # Account summary
                equity = account.get('equity', 0)
                cash = account.get('cash', 0)
                
                return html.Div([
                    # Account header
                    html.Div([
                        html.Div([
                            html.Small("Total Equity", className="text-muted d-block"),
                            html.H5(f"${equity:,.2f}", className="text-success mb-0")
                        ], className="me-4"),
                        html.Div([
                            html.Small("Cash", className="text-muted d-block"),
                            html.H6(f"${cash:,.2f}", className="mb-0")
                        ])
                    ], className="d-flex mb-3"),
                    # Positions list
                    html.Div(position_items) if position_items else html.P("No positions", className="text-muted"),
                    # Footer
                    html.Small(f"Showing {len(positions[:5])} of {len(positions)} positions", 
                              className="text-muted mt-2 d-block") if len(positions) > 5 else None
                ])
            else:
                # No Alpaca data - show mock data
                return html.Div([
                    html.Div([
                        html.Small("Demo Portfolio", className="text-muted d-block"),
                        html.H5("$92,939.10", className="text-success mb-0")
                    ], className="mb-3"),
                    html.Div([
                        html.Div([html.Strong("AAPL"), html.Span(" - 50 shares @ $238.76", className="text-muted")]),
                        html.Div([html.Strong("MSFT"), html.Span(" - 30 shares @ $417.89", className="text-muted")]),
                        html.Div([html.Strong("NVDA"), html.Span(" - 20 shares @ $142.55", className="text-muted")]),
                    ]),
                    dbc.Alert("Connect Alpaca for live data", color="info", className="mt-2 mb-0 py-1 small")
                ])
                
        except Exception as e:
            logger.warning(f"Portfolio snapshot error: {e}")
            return html.Div([
                html.P("Portfolio loading...", className="text-muted mb-2"),
                html.Small(f"Error: {str(e)[:50]}", className="text-danger")
            ])

    # Callback X: Load Performance Insights from local metrics cache
    @app.callback(
        Output("cc-perf-insights", "children"),
        Input("cc-auto-refresh", "n_intervals"),
        Input("cc-refresh-btn", "n_clicks"),
        prevent_initial_call=False
    )
    def load_performance_insights(n_intervals, n_clicks):
        """Load performance metrics from outputs/metrics_cache.json with graceful fallback"""
        try:
            metrics_path = Path("outputs/metrics_cache.json")
            if not metrics_path.exists():
                return html.P("Metrics cache missing — no metrics available", className="text-muted")

            with metrics_path.open("r") as fh:
                metrics = json.load(fh)

            # Render a small summary (keys may vary; use .get safely)
            cards = []
            def mk_card(title, value, src=None):
                return html.Div([
                    html.Div(title, className="mb-1 small text-muted"),
                    html.H5(str(value), className="mb-0"),
                    html.Small(f"from {src}", className="text-muted") if src else None
                ], className="col-md-3 mb-2")

            # Support common cache shapes: nested keys under attribution/volatility/research/strategy
            cagr = metrics.get("attribution", {}).get("cagr") or metrics.get("portfolio_cagr")
            forecast_acc = metrics.get("volatility", {}).get("forecast_accuracy") or metrics.get("forecast_accuracy")
            research_score = metrics.get("research", {}).get("research_score") or metrics.get("research_score")
            win_rate = metrics.get("strategy", {}).get("win_rate") or metrics.get("strategy_win_rate")

            cards.append(mk_card("Portfolio CAGR", cagr if cagr is not None else "N/A"))
            cards.append(mk_card("Forecast Accuracy", forecast_acc if forecast_acc is not None else "N/A"))
            cards.append(mk_card("Research Score", research_score if research_score is not None else "N/A"))
            cards.append(mk_card("Strategy Win Rate", win_rate if win_rate is not None else "N/A"))

            return html.Div([html.Div(cards, className="row")])
        except Exception as e:
            logger.warning(f"Performance insights load error: {e}")
            return html.P("Performance metrics unavailable", className="text-muted")
    
    # Callback 3: Update sentiment indicator
    @app.callback(
        Output("cc-sentiment-indicator", "children"),
        Output("cc-sentiment-indicator", "className"),
        Output("cc-sentiment-score", "children"),
        Output("cc-sentiment-last-updated", "children"),
        Input("cc-auto-refresh", "n_intervals"),
        prevent_initial_call=False
    )
    def update_sentiment(n_intervals):
        """Fetch latest market sentiment"""
        try:
            response = httpx.get(
                f"{CC_BASE_URL}/api/cc/market_sentiment",
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            
            score = data.get("score", 0.0)
            
            if score > 0.2:
                label = "Bullish 📈"
                color_class = "text-success"
            elif score < -0.2:
                label = "Bearish 📉"
                color_class = "text-danger"
            else:
                label = "Neutral ➡️"
                color_class = "text-muted"
            
            return (
                label,
                color_class,
                f"Score: {score:.3f}",
                f"Last updated: {data.get('timestamp', 'N/A')}"
            )
        except Exception as e:
            logger.warning(f"Sentiment fetch error: {e}")
            return "Neutral ➡️", "text-muted", "Score: 0.0", "Last updated: N/A"
    
    # Callback 4: Chat query
    @app.callback(
        Output("cc-chat-response", "children"),
        Input("cc-chat-send", "n_clicks"),
        State("cc-chat-input", "value"),
        prevent_initial_call=True
    )
    def handle_chat(n_clicks, query):
        """Handle chat query via API"""
        if not n_clicks or not query:
            raise PreventUpdate
        
        try:
            from dash import html
            response = httpx.post(
                f"{CC_BASE_URL}/api/chat/query",
                json={"query": query, "tab_context": "command_center"},
                timeout=15.0
            )
            response.raise_for_status()
            data = response.json()
            
            return html.Div([
                html.P(data.get("response", "No response"), className="mb-2"),
                html.Small(
                    f"Sources: {', '.join(data.get('sources', []))}",
                    className="text-muted"
                ) if data.get("sources") else None
            ])
        except Exception as e:
            logger.warning(f"Chat error: {e}")
            from dash import html
            return html.P("Chat service unavailable - try again later", className="text-muted")
    
    # Callback 5: Load picks status
    @app.callback(
        Output("cc-picks-card", "children"),
        Output("cc-picks-last-run-id", "children"),
        Input("cc-refresh-btn", "n_clicks"),
        Input("cc-auto-refresh", "n_intervals"),
        Input("cc-picks-run-btn", "n_clicks"),
        Input("cc-picks-run-live-btn", "n_clicks"),
        prevent_initial_call=False
    )
    def load_picks_status(refresh_clicks, n_intervals, run_clicks):
        """Load picks status from API"""
        ctx = callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
        
        try:
            from dash import html
            
            # If run button clicked, trigger dry run (legacy pipeline)
            if trigger_id == "cc-picks-run-btn" and run_clicks:
                try:
                    response = httpx.post(
                        f"{CC_BASE_URL}/api/picks/run",
                        json={"mode": "dryrun"},
                        timeout=30.0
                    )
                    response.raise_for_status()
                    result = response.json()
                    run_id = result.get("run_id", "N/A")
                except Exception as e:
                    run_id = f"Error: {str(e)[:30]}"
            # If live run button clicked, we open a confirmation modal (handled elsewhere)
            elif trigger_id == "cc-picks-run-live-btn" and run_clicks:
                run_id = "Pending confirmation"
            else:
                run_id = "N/A"
            
            # Fetch last run status
            response = httpx.get(
                f"{CC_BASE_URL}/api/cc/last_run",
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()
            
            picks_data = data.get("picks", {})
            return (
                html.Div([
                    html.P(f"Status: {picks_data.get('status', 'unknown')}"),
                    html.Small(f"Count: {picks_data.get('count', 0)} picks"),
                ]),
                f"Last run: {run_id if trigger_id == 'cc-picks-run-btn' else picks_data.get('last_run_id', 'N/A')}"
            )
        except Exception as e:
            logger.warning(f"Picks status error: {e}")
            from dash import html
            return html.P("Picks service unavailable", className="text-muted"), "Last run: N/A"


    # Callback: open/confirm live execution modal and perform live run on confirm
    @app.callback(
        Output("cc-picks-live-confirm-modal", "is_open"),
        Output("cc-picks-last-run-id", "children"),
        Input("cc-picks-run-live-btn", "n_clicks"),
        Input("cc-picks-live-confirm-btn", "n_clicks"),
        Input("cc-picks-live-cancel-btn", "n_clicks"),
        State("cc-picks-live-confirm-modal", "is_open"),
        State("cc-picks-last-run-id", "children"),
        prevent_initial_call=True
    )
    def handle_live_modal(open_clicks, confirm_clicks, cancel_clicks, is_open, last_run_text):
        # If cancel clicked, simply close modal
        if cancel_clicks:
            return False, last_run_text

        # If confirm clicked -> execute live run
        if confirm_clicks:
            try:
                response = httpx.post(
                    f"{CC_BASE_URL}/api/chat/execute_picks",
                    json={"n": 5, "allocation_per_pick": 500, "execute": True},
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                if data.get('success'):
                    run_text = "Live run executed"
                else:
                    run_text = f"Live run: {data.get('error', 'unknown')}"
            except Exception as e:
                run_text = f"Error: {str(e)[:80]}"
            return False, f"Last run: {run_text}"

        # Otherwise (open button clicked), open modal
        if open_clicks:
            return True, last_run_text

        return is_open, last_run_text
    
    # Callback 6: Admin callback map
    @app.callback(
        Output("cc-admin-output", "children"),
        Input("cc-callback-map-btn", "n_clicks"),
        prevent_initial_call=True
    )
    def show_callback_map(n_clicks):
        """Fetch and display callback map"""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            from dash import html
            response = httpx.get(
                f"{CC_BASE_URL}/admin/callback_map",
                timeout=10.0
            )
            response.raise_for_status()
            data = response.json()
            
            return html.Pre(
                str(data)[:500],  # Truncate for display
                style={"fontSize": "10px", "maxHeight": "200px", "overflow": "auto"}
            )
        except Exception as e:
            logger.warning(f"Callback map error: {e}")
            from dash import html
            return html.P("Admin tools unavailable", className="text-muted")
    
    logger.info("✅ Command Center callbacks registered successfully")
