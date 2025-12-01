"""
Command Center Callbacks
Thin callback layer that delegates to server endpoints.
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
        """Load portfolio snapshot from API"""
        try:
            # Prefer internal Flask test client when Dash app server is available
            data = None
            try:
                if hasattr(app, "server") and app.server:
                    with app.server.test_client() as client:
                        r = client.get("/api/cc/portfolio_snapshot")
                        if r.status_code == 200:
                            data = r.get_json()
                        else:
                            raise Exception(f"Internal request failed: {r.status_code}")
                else:
                    raise RuntimeError("No app.server available")
            except Exception:
                # Fallback to HTTP request using CC_BASE_URL
                response = httpx.get(
                    f"{CC_BASE_URL}/api/cc/portfolio_snapshot",
                    timeout=10.0
                )
                response.raise_for_status()
                data = response.json()
            
            # Simple rendering
            from dash import html
            if data.get("positions"):
                return html.Ul([
                    html.Li(f"{p['symbol']}: {p.get('qty', 0)} shares @ ${p.get('current_price', 0):.2f}")
                    for p in data["positions"][:3]
                ])
            else:
                return html.P("No positions", className="text-muted")
        except Exception as e:
            logger.warning(f"Portfolio snapshot error: {e}")
            from dash import html
            return html.P("Portfolio data unavailable - connect services to view", className="text-muted")

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
        prevent_initial_call=False
    )
    def load_picks_status(refresh_clicks, n_intervals, run_clicks):
        """Load picks status from API"""
        ctx = callback_context
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None
        
        try:
            from dash import html
            
            # If run button clicked, trigger dry run
            if trigger_id == "cc-picks-run-btn" and run_clicks:
                try:
                    response = httpx.post(
                        f"{CC_BASE_URL}/api/picks/run",
                        json={"dry_run": True},
                        timeout=30.0
                    )
                    response.raise_for_status()
                    result = response.json()
                    run_id = result.get("run_id", "N/A")
                except Exception as e:
                    run_id = f"Error: {str(e)[:30]}"
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
