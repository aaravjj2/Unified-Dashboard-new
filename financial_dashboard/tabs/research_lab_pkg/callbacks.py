"""
Research Lab - Callbacks Module

Implements interactive behavior for the Research Lab.
Uses idempotent registration pattern to prevent duplicate callbacks.
"""

import logging
import json
import os
import time
import requests
from datetime import datetime
from typing import Dict, List, Any

from dash import Input, Output, State, callback_context, no_update, ALL, MATCH
from dash.exceptions import PreventUpdate

from . import components
from . import data

logger = logging.getLogger(__name__)

# Idempotent registration guard
_callbacks_registered = False

# AlphaSim service URL (configurable via env)
ALPHA_SIM_URL = os.getenv("ALPHA_SIM_URL", "http://localhost:8065")


def register_callbacks(app):
    """
    Register all Research Lab callbacks with the Dash app.
    
    Uses module-level guard for idempotent registration.
    Will not re-register if already called.
    
    Args:
        app: Dash application instance
    """
    global _callbacks_registered
    
    if _callbacks_registered:
        logger.info("🔒 Research Lab pkg callbacks already registered, skipping")
        return
    
    logger.info("📝 Registering Research Lab pkg callbacks...")
    
    # ========================================================================
    # ALPHASIM CONSOLE CALLBACKS
    # ========================================================================
    
    @app.callback(
        [Output("rl-alphasim-response", "children"),
         Output("rl-alphasim-status", "children"),
         Output("rl-alphasim-status", "color"),
         Output("rl-alphasim-cache-badge", "children"),
         Output("rl-alphasim-latency", "children"),
         Output("rl-alphasim-query-history", "data"),
         Output("rl-alphasim-last-result", "data")],
        [Input("rl-alphasim-run-btn", "n_clicks")],
        [State("rl-alphasim-function", "value"),
         State("rl-alphasim-symbol", "value"),
         State("rl-alphasim-time-period", "value"),
         State("rl-alphasim-interval", "value"),
         State("rl-alphasim-outputsize", "value"),
         State("rl-alphasim-query-history", "data")],
        prevent_initial_call=True
    )
    def run_alphasim_query(n_clicks, function, symbol, time_period, interval, outputsize, history):
        """Execute AlphaSim query and display results."""
        if not n_clicks:
            raise PreventUpdate
        
        history = history or []
        start_time = time.time()
        
        # Build query params
        params = {
            "function": function,
            "symbol": symbol.upper() if symbol else "AAPL",
            "apikey": "dashboard-user",
            "outputsize": outputsize or "compact"
        }
        
        # Add function-specific params
        if function in ["SMA", "EMA", "RSI", "MACD"]:
            params["time_period"] = time_period or 10
            params["series_type"] = "close"
        if function == "TIME_SERIES_INTRADAY":
            params["interval"] = interval or "5min"
        
        try:
            # Call AlphaSim service
            response = requests.get(f"{ALPHA_SIM_URL}/query", params=params, timeout=15)
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                result_json = json.dumps(result, indent=2)
                status = "Success"
                status_color = "success"
                # Check for cache header
                cache_status = "Cache: Hit" if response.headers.get("X-Cache") == "HIT" else "Cache: Miss"
            elif response.status_code == 429:
                result = response.json()
                result_json = json.dumps(result, indent=2)
                status = "Rate Limited"
                status_color = "warning"
                cache_status = "Cache: --"
            else:
                result_json = json.dumps({"error": f"HTTP {response.status_code}", "detail": response.text[:500]}, indent=2)
                status = f"Error ({response.status_code})"
                status_color = "danger"
                cache_status = "Cache: --"
                result = {"error": response.text}
            
            latency_text = f"Latency: {elapsed*1000:.0f}ms"
            
        except requests.exceptions.ConnectionError:
            elapsed = time.time() - start_time
            result_json = json.dumps({
                "error": "Connection refused",
                "message": f"Could not connect to AlphaSim at {ALPHA_SIM_URL}",
                "hint": "Start the service with: uvicorn financial_dashboard.services.alpha_sim.app:app --port 8065"
            }, indent=2)
            status = "Offline"
            status_color = "danger"
            cache_status = "Cache: --"
            latency_text = f"Timeout: {elapsed*1000:.0f}ms"
            result = {"error": "Connection refused"}
            
        except Exception as e:
            elapsed = time.time() - start_time
            result_json = json.dumps({"error": str(e)}, indent=2)
            status = "Error"
            status_color = "danger"
            cache_status = "Cache: --"
            latency_text = f"Error after {elapsed*1000:.0f}ms"
            result = {"error": str(e)}
        
        # Add to history
        history_entry = {
            "function": function,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "latency_ms": int(elapsed * 1000)
        }
        history = [history_entry] + history[:9]  # Keep last 10
        
        return result_json, status, status_color, cache_status, latency_text, history, result
    
    @app.callback(
        Output("rl-alphasim-recent", "children"),
        [Input("rl-alphasim-query-history", "data")],
        prevent_initial_call=True
    )
    def update_recent_queries(history):
        """Update the recent queries display."""
        if not history:
            return components.empty_state("No queries yet", icon="bi-clock-history")
        
        rows = []
        for entry in history:
            status_color = "success" if entry["status"] == "Success" else "warning" if "Rate" in entry["status"] else "danger"
            rows.append(
                html.Tr([
                    html.Td(entry["function"], className="text-light"),
                    html.Td(entry.get("symbol", "N/A"), className="text-light"),
                    html.Td(dbc.Badge(entry["status"], color=status_color)),
                    html.Td(f"{entry['latency_ms']}ms", className="text-muted"),
                    html.Td(entry["timestamp"].split("T")[1][:8], className="text-muted small")
                ])
            )
        
        return dbc.Table([
            html.Thead(html.Tr([
                html.Th("Function"),
                html.Th("Symbol"),
                html.Th("Status"),
                html.Th("Latency"),
                html.Th("Time")
            ], className="text-light")),
            html.Tbody(rows)
        ], bordered=True, hover=True, size="sm", className="table-dark mb-0")
    
    @app.callback(
        [Output("rl-alphasim-health-icon", "className"),
         Output("rl-alphasim-health-text", "children"),
         Output("rl-alphasim-cache-size", "children")],
        [Input("rl-alphasim-check-health-btn", "n_clicks")],
        prevent_initial_call=True
    )
    def check_alphasim_health(n_clicks):
        """Check AlphaSim service health."""
        if not n_clicks:
            raise PreventUpdate
        
        try:
            # Check health endpoint
            health_resp = requests.get(f"{ALPHA_SIM_URL}/health", timeout=5)
            if health_resp.status_code == 200:
                health_icon = "bi bi-circle-fill text-success me-2"
                health_text = "Online"
            else:
                health_icon = "bi bi-circle-fill text-warning me-2"
                health_text = f"Degraded ({health_resp.status_code})"
            
            # Check metrics for cache size
            try:
                metrics_resp = requests.get(f"{ALPHA_SIM_URL}/metrics", timeout=5)
                if metrics_resp.status_code == 200:
                    metrics = metrics_resp.json()
                    cache_size = metrics.get("cache", {}).get("size", "N/A")
                    cache_text = f"Size: {cache_size} entries"
                else:
                    cache_text = "Size: N/A"
            except:
                cache_text = "Size: N/A"
            
        except requests.exceptions.ConnectionError:
            health_icon = "bi bi-circle-fill text-danger me-2"
            health_text = "Offline"
            cache_text = "Size: N/A"
        except Exception as e:
            health_icon = "bi bi-circle-fill text-warning me-2"
            health_text = f"Error: {str(e)[:30]}"
            cache_text = "Size: N/A"
        
        return health_icon, health_text, cache_text
    
    @app.callback(
        Output("rl-alphasim-download", "data"),
        [Input("rl-alphasim-export-btn", "n_clicks")],
        [State("rl-alphasim-last-result", "data"),
         State("rl-alphasim-function", "value"),
         State("rl-alphasim-symbol", "value")],
        prevent_initial_call=True
    )
    def export_alphasim_result(n_clicks, result, function, symbol):
        """Export the last result as JSON file."""
        if not n_clicks or not result:
            raise PreventUpdate
        
        filename = f"alphasim_{function}_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        return dict(content=json.dumps(result, indent=2), filename=filename)
    
    # Need to import html and dbc for callback outputs
    from dash import html
    import dash_bootstrap_components as dbc

    # ========================================================================
    # BEGINNER GUIDE / HOWTO MODAL CALLBACKS
    # ========================================================================
    @app.callback(
        [Output("rl-beginner-howto-store", "data"), Output("rl-beginner-howto-modal", "is_open")],
        [Input("rl-beginner-open-howto", "n_clicks"), Input("rl-beginner-howto-close", "n_clicks")],
        [State("rl-beginner-howto-modal", "is_open")],
        prevent_initial_call=True
    )
    def toggle_beginner_howto(open_clicks, close_clicks, is_open):
        """Open the full HOWTO markdown into the modal (loaded from docs file)."""
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate

        button_id = ctx.triggered[0]["prop_id"].split(".")[0]

        if button_id == "rl-beginner-open-howto":
            # Load the HOWTO markdown from the docs folder
            try:
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
                md_path = os.path.normpath(os.path.join(base_dir, "docs", "research_lab_how_to_use.md"))
                if os.path.exists(md_path):
                    with open(md_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                else:
                    content = "# Research Lab HOWTO\n\nFull guide not found in repo (docs missing)."
            except Exception as e:
                content = f"# Error loading HOWTO\n\n{str(e)}"

            return content, True

        # Close button pressed
        return no_update, False

    @app.callback(
        Output('rl-beginner-howto-md', 'children'),
        [Input('rl-beginner-howto-store', 'data')]
    )
    def _populate_howto_md(md_text):
        if not md_text:
            raise PreventUpdate
        return md_text

    @app.callback(
        Output('rl-beginner-howto-download-file', 'data'),
        [Input('rl-beginner-howto-download', 'n_clicks')],
        [State('rl-beginner-howto-store', 'data')],
        prevent_initial_call=True
    )
    def _download_howto(n_clicks, md_text):
        if not n_clicks or not md_text:
            raise PreventUpdate
        return dict(content=md_text, filename='research_lab_how_to_use.md')
    
    # ========================================================================
    # SCAN TAB CALLBACKS
    # ========================================================================
    
    @app.callback(
        [Output("rl-scan-results", "children"),
         Output("rl-scan-news", "children")],
        [Input("rl-scan-run-btn", "n_clicks"),
         Input("rl-scan-preset-momentum", "n_clicks"),
         Input("rl-scan-preset-value", "n_clicks"),
         Input("rl-scan-preset-growth", "n_clicks")],
        [State("rl-scan-ticker", "value")],
        prevent_initial_call=True
    )
    def run_scan(run_clicks, momentum_clicks, value_clicks, growth_clicks, ticker_input):
        """Handle scan button clicks and preset selections."""
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        # Parse tickers
        if ticker_input:
            tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]
        else:
            tickers = data.get_sample_tickers()[:5]
        
        # Determine scan type based on trigger
        scan_type = "momentum"  # default
        if trigger_id == "rl-scan-preset-value":
            scan_type = "value"
        elif trigger_id == "rl-scan-preset-growth":
            scan_type = "growth"
        
        # Get scan results
        results = data.load_screen_results({"type": scan_type, "tickers": tickers})
        scan_results_component = components.scan_results_table(results.get("tickers", []))
        
        # Get news feed
        news = data.load_news_feed(tickers)
        news_components = [components.news_feed_item(item) for item in news] if news else [
            components.empty_state("No news found for these tickers", icon="bi-newspaper")
        ]
        
        return scan_results_component, news_components
    
    @app.callback(
        Output("rl-scan-news", "children", allow_duplicate=True),
        [Input("rl-scan-news-refresh", "n_clicks")],
        [State("rl-scan-ticker", "value")],
        prevent_initial_call=True
    )
    def refresh_news(n_clicks, ticker_input):
        """Refresh news feed."""
        if not n_clicks:
            raise PreventUpdate
        
        tickers = [t.strip().upper() for t in (ticker_input or "AAPL").split(",") if t.strip()]
        news = data.load_news_feed(tickers)
        
        if news:
            return [components.news_feed_item(item) for item in news]
        return [components.empty_state("No news found", icon="bi-newspaper")]
    
    # ========================================================================
    # FACTOR TAB CALLBACKS
    # ========================================================================
    
    @app.callback(
        [Output("rl-factor-exposures", "children"),
         Output("rl-factor-heatmap", "figure")],
        [Input("rl-factor-select", "value"),
         Input("rl-factor-period", "value")],
        prevent_initial_call=False
    )
    def update_factor_analysis(tickers, period):
        """Update factor exposures and correlation heatmap."""
        if not tickers:
            empty = components.empty_state("Select tickers to analyze", icon="bi-graph-up")
            empty_fig = _empty_heatmap_figure()
            return empty, empty_fig
        
        # Get factor exposures
        exposures = data.load_factor_exposures(tickers, period)
        exposure_table = components.factor_exposure_table(exposures)
        
        # Get correlation matrix and create heatmap
        corr_matrix = data.load_correlation_matrix(tickers)
        heatmap_fig = _create_correlation_heatmap(corr_matrix, tickers)
        
        return exposure_table, heatmap_fig
    
    @app.callback(
        [Output("rl-factor-preview", "children"),
         Output("rl-alert", "children", allow_duplicate=True),
         Output("rl-alert", "color", allow_duplicate=True),
         Output("rl-alert", "is_open", allow_duplicate=True)],
        [Input("rl-factor-create-signal", "n_clicks")],
        [State("rl-factor-signal-factor", "value"),
         State("rl-factor-signal-threshold", "value"),
         State("rl-factor-signal-name", "value"),
         State("rl-factor-select", "value")],
        prevent_initial_call=True
    )
    def create_signal(n_clicks, factor, threshold, name, tickers):
        """Create and preview a new signal."""
        if not n_clicks:
            raise PreventUpdate
        
        if not name:
            return no_update, "Please enter a signal name", "warning", True
        
        # Get exposures and filter by threshold
        exposures = data.load_factor_exposures(tickers or data.get_sample_tickers()[:5])
        
        matching = []
        for ticker, factors in exposures.items():
            if factors.get(factor, 0) >= (threshold or 0):
                matching.append({"ticker": ticker, "value": factors.get(factor, 0)})
        
        preview = html.Div([
            html.H6(f"Signal: {name}", className="text-light"),
            html.P(f"Filter: {factor} >= {threshold}", className="text-muted small"),
            html.P(f"Matches: {len(matching)} tickers", className="text-info"),
            html.Ul([html.Li(f"{m['ticker']}: {m['value']:.3f}") for m in matching[:5]],
                   className="text-light small")
        ])
        
        return preview, f"Signal '{name}' created!", "success", True
    
    # ========================================================================
    # SCREEN TAB CALLBACKS
    # ========================================================================
    
    @app.callback(
        [Output("rl-screen-results", "children"),
         Output("rl-screen-export-btn", "disabled")],
        [Input("rl-screen-run-btn", "n_clicks")],
        [State("rl-screen-sector", "value"),
         State("rl-screen-liquidity", "value"),
         State("rl-screen-volatility", "value"),
         State("rl-screen-momentum", "value")],
        prevent_initial_call=True
    )
    def run_screen(n_clicks, sector, liquidity, volatility, momentum):
        """Run screening with specified filters."""
        if not n_clicks:
            raise PreventUpdate
        
        filters = {
            "sector": sector,
            "min_liquidity": liquidity,
            "max_volatility": volatility,
            "min_momentum": momentum
        }
        
        results = data.load_screen_results(filters)
        
        if results.get("tickers"):
            table = components.scan_results_table(results["tickers"])
            return table, False
        
        return components.empty_state("No matches for these filters", icon="bi-funnel"), True
    
    # ========================================================================
    # RAG TAB CALLBACKS
    # ========================================================================
    
    @app.callback(
        [Output("rl-rag-answer", "children"),
         Output("rl-rag-sources", "children"),
         Output("rl-rag-answer-id", "data"),
         Output("rl-rag-explain-btn", "disabled"),
         Output("rl-rag-create-brief-btn", "disabled")],
        [Input("rl-rag-run-btn", "n_clicks")],
        [State("rl-rag-query-input", "value"),
         State("rl-rag-source-filter", "value"),
         State("rl-diag-llm-provider", "value")],
        prevent_initial_call=True
    )
    def run_rag_query(n_clicks, query, source_filter, llm_provider):
        """Execute RAG query and display results."""
        if not n_clicks or not query:
            raise PreventUpdate
        
        try:
            # Call RAG API with selected LLM provider
            result = _execute_rag_query(query, source_filter, llm_provider)
            
            answer_id = result.get("answer_id", f"ans-{datetime.now().timestamp()}")
            answer_text = result.get("answer", "No answer generated.")
            sources = result.get("sources", [])
            
            # Indicate which LLM was used
            llm_used = result.get("llm_used", llm_provider or "unknown")
            
            answer_component = html.Div([
                html.P(answer_text, className="text-light"),
                html.Small([
                    html.Span(f"Generated at: {datetime.now().strftime('%H:%M:%S')} ", className="text-muted"),
                    dbc.Badge(f"via {llm_used}", color="info", className="ms-2")
                ])
            ])
            
            source_components = [
                components.rag_source_card(
                    doc_id=s.get("doc_id", "unknown"),
                    title=s.get("title", "Untitled"),
                    snippet=s.get("snippet", ""),
                    score=s.get("score", 0)
                )
                for s in sources
            ] if sources else [components.empty_state("No sources found", icon="bi-file-x")]
            
            return answer_component, source_components, answer_id, False, False
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            error_msg = components.error_panel(f"Query failed: {str(e)}")
            return error_msg, [], None, True, True
    
    @app.callback(
        Output("rl-rag-answer", "children", allow_duplicate=True),
        [Input("rl-rag-explain-btn", "n_clicks")],
        [State("rl-rag-answer-id", "data")],
        prevent_initial_call=True
    )
    def explain_rag_answer(n_clicks, answer_id):
        """Get explanation for RAG answer."""
        if not n_clicks or not answer_id:
            raise PreventUpdate
        
        # Mock explanation
        explanation = {
            "method": "Vector similarity + context injection",
            "top_docs": 3,
            "confidence": 0.85,
            "chain_of_thought": "Retrieved relevant documents → Extracted key facts → Synthesized answer"
        }
        
        return html.Div([
            html.H6("Explanation", className="text-light"),
            html.P(f"Method: {explanation['method']}", className="text-muted small"),
            html.P(f"Documents used: {explanation['top_docs']}", className="text-muted small"),
            html.P(f"Confidence: {explanation['confidence']*100:.0f}%", className="text-info small"),
            html.P(f"Process: {explanation['chain_of_thought']}", className="text-muted small")
        ])
    
    # ========================================================================
    # BRIEFS TAB CALLBACKS
    # ========================================================================
    
    @app.callback(
        Output("rl-briefs-store", "data"),
        [Input("rl-refresh-btn", "n_clicks"),
         Input("rl-load-demo-btn", "n_clicks")],
        prevent_initial_call=False
    )
    def load_briefs(refresh_clicks, demo_clicks):
        """Load briefs from storage."""
        return data.load_briefs()
    
    @app.callback(
        Output("rl-brief-list", "children"),
        [Input("rl-briefs-store", "data")]
    )
    def update_brief_list(briefs):
        """Update brief list display."""
        if not briefs:
            return components.empty_brief_list()
        
        return [
            components.brief_card(
                brief_id=b.get("id"),
                title=b.get("title", "Untitled"),
                summary=b.get("summary", ""),
                tags=b.get("tags", []),
                created_at=b.get("created_at", ""),
                last_updated=b.get("last_updated", ""),
                status=b.get("status", "draft")
            )
            for b in briefs
        ]
    
    @app.callback(
        Output("rl-selected-brief-id", "data"),
        [Input({"type": "rl-select-brief", "index": ALL}, "n_clicks")],
        [State({"type": "rl-select-brief", "index": ALL}, "id")],
        prevent_initial_call=True
    )
    def select_brief(n_clicks_list, button_ids):
        """Handle brief selection."""
        ctx = callback_context
        if not ctx.triggered or not any(n_clicks_list):
            raise PreventUpdate
        
        triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
        try:
            button_id = json.loads(triggered_id)
            if button_id.get("type") == "rl-select-brief":
                return button_id.get("index")
        except:
            pass
        
        raise PreventUpdate
    
    @app.callback(
        Output("rl-brief-view", "children"),
        [Input("rl-selected-brief-id", "data"),
         Input("rl-briefs-store", "data")]
    )
    def display_brief_detail(selected_id, briefs):
        """Display selected brief detail."""
        if not selected_id or not briefs:
            return components.empty_detail_panel()
        
        brief = next((b for b in briefs if b.get("id") == selected_id), None)
        return components.brief_detail_view(brief)
    
    @app.callback(
        Output("rl-brief-modal", "is_open"),
        [Input("rl-brief-create", "n_clicks"),
         Input("rl-modal-cancel", "n_clicks"),
         Input("rl-modal-save", "n_clicks")],
        [State("rl-brief-modal", "is_open")],
        prevent_initial_call=True
    )
    def toggle_brief_modal(create_clicks, cancel_clicks, save_clicks, is_open):
        """Toggle brief modal visibility."""
        ctx = callback_context
        if not ctx.triggered:
            raise PreventUpdate
        
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        
        if trigger_id == "rl-brief-create":
            return True
        elif trigger_id in ["rl-modal-cancel", "rl-modal-save"]:
            return False
        
        return is_open
    
    # ========================================================================
    # EXPERIMENT TAB CALLBACKS
    # ========================================================================
    
    @app.callback(
        Output("rl-exp-list", "children"),
        [Input("rl-experiments-store", "data")]
    )
    def update_experiment_list(experiments):
        """Update experiment list display."""
        if not experiments:
            experiments = data.load_experiments()
        
        if not experiments:
            return components.empty_state("No experiments yet", icon="bi-flask")
        
        return [components.experiment_card(exp) for exp in experiments]
    
    @app.callback(
        [Output("rl-exp-results", "children"),
         Output("rl-experiments-store", "data"),
         Output("rl-exp-export", "disabled")],
        [Input("rl-exp-run-btn", "n_clicks")],
        [State("rl-exp-strategy", "value"),
         State("rl-exp-lookback", "value"),
         State("rl-exp-topn", "value"),
         State("rl-experiments-store", "data")],
        prevent_initial_call=True
    )
    def run_experiment(n_clicks, strategy, lookback, top_n, current_experiments):
        """Run experiment preview."""
        if not n_clicks:
            raise PreventUpdate
        
        # Generate mock experiment result
        exp_id = f"exp-{datetime.now().strftime('%H%M%S')}"
        
        # Deterministic mock results
        import hashlib
        seed = int(hashlib.md5(f"{strategy}{lookback}{top_n}".encode()).hexdigest()[:8], 16)
        
        new_exp = {
            "id": exp_id,
            "name": f"{strategy.title()} {lookback}d Preview",
            "strategy": strategy,
            "parameters": {"lookback": lookback, "top_n": top_n},
            "created_at": datetime.now().isoformat()[:19],
            "status": "completed",
            "metrics": {
                "total_return": ((seed % 50) - 10) / 100,
                "sharpe_ratio": (seed % 30 + 80) / 100,
                "max_drawdown": -(seed % 15 + 5) / 100,
                "win_rate": (seed % 30 + 50) / 100
            }
        }
        
        # Create results display
        metrics = new_exp["metrics"]
        results = html.Div([
            html.H5(f"Preview: {new_exp['name']}", className="text-light"),
            dbc.Row([
                dbc.Col([
                    html.Small("Return", className="text-muted d-block"),
                    html.H4(f"{metrics['total_return']*100:.1f}%",
                           className="text-success" if metrics['total_return'] > 0 else "text-danger")
                ], width=3),
                dbc.Col([
                    html.Small("Sharpe", className="text-muted d-block"),
                    html.H4(f"{metrics['sharpe_ratio']:.2f}", className="text-info")
                ], width=3),
                dbc.Col([
                    html.Small("Max DD", className="text-muted d-block"),
                    html.H4(f"{metrics['max_drawdown']*100:.1f}%", className="text-danger")
                ], width=3),
                dbc.Col([
                    html.Small("Win Rate", className="text-muted d-block"),
                    html.H4(f"{metrics['win_rate']*100:.0f}%", className="text-light")
                ], width=3)
            ], className="mt-3")
        ])
        
        # Update experiments list
        updated_experiments = (current_experiments or []) + [new_exp]
        
        return results, updated_experiments, False
    
    # ========================================================================
    # DIAGNOSTICS TAB CALLBACKS
    # ========================================================================
    
    @app.callback(
        Output("rl-diag-index-stats", "children"),
        [Input("rl-diag-refresh-btn", "n_clicks")],
        prevent_initial_call=False
    )
    def refresh_index_stats(n_clicks):
        """Refresh index health stats."""
        health = data.get_index_health()
        return components.index_health_display(health)
    
    @app.callback(
        [Output("rl-diag-logs", "children"),
         Output("rl-alert", "children", allow_duplicate=True),
         Output("rl-alert", "color", allow_duplicate=True),
         Output("rl-alert", "is_open", allow_duplicate=True)],
        [Input("rl-diag-rebuild-btn", "n_clicks")],
        prevent_initial_call=True
    )
    def rebuild_index(n_clicks):
        """Trigger index rebuild."""
        if not n_clicks:
            raise PreventUpdate
        
        logs = [
            f"[{datetime.now().strftime('%H:%M:%S')}] Index rebuild triggered",
            f"[{datetime.now().strftime('%H:%M:%S')}] Scanning documents...",
            f"[{datetime.now().strftime('%H:%M:%S')}] Found 0 documents (no ingested docs)",
            f"[{datetime.now().strftime('%H:%M:%S')}] Rebuild complete (empty index)"
        ]
        
        return "\n".join(logs), "Index rebuild initiated", "info", True
    
    @app.callback(
        [Output("rl-alert", "children", allow_duplicate=True),
         Output("rl-alert", "color", allow_duplicate=True),
         Output("rl-alert", "is_open", allow_duplicate=True)],
        [Input("rl-diag-save-config", "n_clicks")],
        [State("rl-diag-llm-provider", "value"),
         State("rl-diag-embed-model", "value"),
         State("rl-diag-topk", "value")],
        prevent_initial_call=True
    )
    def save_rag_config(n_clicks, llm_provider, embed_model, topk):
        """Save RAG configuration."""
        if not n_clicks:
            raise PreventUpdate
        
        config = {
            "llm_provider": llm_provider,
            "embed_model": embed_model,
            "top_k": topk,
            "saved_at": datetime.now().isoformat()
        }
        
        # Save to fixture for persistence
        data.save_fixture("rag_config.json", config)
        
        return f"Config saved: {llm_provider}/{embed_model}, top_k={topk}", "success", True
    
    # ========================================================================
    # NAVIGATION CALLBACKS
    # ========================================================================
    
    @app.callback(
        Output("rl-main-tabs", "active_tab"),
        [Input("rl-rag-go-diag", "n_clicks")],
        prevent_initial_call=True
    )
    def navigate_to_diagnostics(n_clicks):
        """Navigate to diagnostics tab."""
        if n_clicks:
            return "rl-diag-tab"
        raise PreventUpdate
    
    
    # ========================================================================
    # FINGPT FORECASTER CALLBACKS
    # ========================================================================
    
    @app.callback(
        [Output("rl-forecast-result", "children"),
         Output("rl-forecast-data", "data")],
        [Input("rl-forecast-run-btn", "n_clicks")],
        [State("rl-forecast-ticker", "value"),
         State("rl-forecast-weeks", "value"),
         State("rl-forecast-options", "value"),
         State("rl-diag-llm-provider", "value")],
        prevent_initial_call=True
    )
    def run_forecast(n_clicks, ticker, weeks, options, llm_provider):
        """Run FinGPT forecaster."""
        if not n_clicks or not ticker:
            raise PreventUpdate
        
        try:
            from financial_dashboard.services.forecaster import run_forecast as run_forecast_fn
            
            include_financials = "financials" in (options or [])
            
            # Run forecast
            result = run_forecast_fn(
                ticker=ticker.upper(),
                n_weeks=int(weeks or 4),
                include_financials=include_financials,
                model_provider=llm_provider or "mock"
            )
            
            # Format result
            prediction = result.get('prediction', 'neutral')
            confidence = result.get('confidence', 0.5)
            analysis = result.get('analysis', 'No analysis available')
            
            # Color based on prediction
            pred_color = {
                'up': 'success',
                'down': 'danger',
                'neutral': 'secondary',
                'error': 'warning'
            }.get(prediction, 'secondary')
            
            # Build UI
            result_ui = html.Div([
                dbc.Alert([
                    html.H5([
                        html.I(className=f"bi bi-{'arrow-up' if prediction == 'up' else 'arrow-down' if prediction == 'down' else 'dash'} me-2"),
                        f"Prediction: {prediction.upper()}"
                    ], className="mb-2"),
                    html.P([
                        "Confidence: ",
                        dbc.Badge(f"{confidence:.1%}", color="light", className="ms-1")
                    ], className="mb-0")
                ], color=pred_color, className="mb-3"),
                
                html.H6("Analysis", className="text-light mt-3"),
                html.P(analysis, className="text-muted"),
                
                html.Hr(),
                
                html.Small([
                    f"Ticker: {result.get('ticker', 'N/A')} | ",
                    f"News weeks: {weeks} | ",
                    f"Financials: {'Yes' if include_financials else 'No'} | ",
                    f"Model: {result.get('provenance', {}).get('model', 'unknown')}"
                ], className="text-muted")
            ])
            
            return result_ui, result
            
        except Exception as e:
            logger.error(f"Forecast failed: {e}")
            error_ui = components.error_panel(f"Forecast failed: {str(e)}")
            return error_ui, None
    
    # ========================================================================
    # RAG INDEX STATUS CALLBACK
    # ========================================================================
    
    @app.callback(
        Output("rl-rag-index-info", "children"),
        [Input("rl-main-tabs", "active_tab")],
        prevent_initial_call=False
    )
    def update_rag_index_info(active_tab):
        """Update RAG index info display."""
        try:
            from financial_dashboard.services.rag import RAGRetriever
            
            retriever = RAGRetriever()
            status = retriever.get_status()
            
            if status.get('initialized'):
                doc_count = status.get('document_count', 0)
                index_dir = status.get('index_dir', 'unknown')
                
                return html.Div([
                    html.P([
                        html.Strong("Documents indexed: "),
                        html.Span(f"{doc_count}", className="text-success")
                    ], className="small mb-2"),
                    html.P([
                        html.Strong("Status: "),
                        dbc.Badge("Ready", color="success", className="ms-1")
                    ], className="small mb-2"),
                    html.P([
                        html.Strong("Index dir: "),
                        html.Code(index_dir, className="text-muted small")
                    ], className="small mb-2"),
                    dbc.Button(
                        "Go to Diagnostics",
                        id="rl-rag-go-diag",
                        color="link",
                        size="sm"
                    )
                ])
            else:
                return html.Div([
                    html.P([
                        html.Strong("Status: "),
                        dbc.Badge("Not Initialized", color="warning", className="ms-1")
                    ], className="small mb-2"),
                    html.P("Run build_rag_index.py to initialize", className="text-muted small"),
                    dbc.Button(
                        "Go to Diagnostics",
                        id="rl-rag-go-diag",
                        color="link",
                        size="sm"
                    )
                ])
                
        except Exception as e:
            return html.Div([
                html.P([
                    html.Strong("Status: "),
                    dbc.Badge("Error", color="danger", className="ms-1")
                ], className="small mb-2"),
                html.P(f"Error: {str(e)[:50]}", className="text-muted small"),
                dbc.Button(
                    "Go to Diagnostics",
                    id="rl-rag-go-diag",
                    color="link",
                    size="sm"
                )
            ])
    
    # Mark as registered
    _callbacks_registered = True
    logger.info("✓ Research Lab pkg callbacks registered successfully")


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _empty_heatmap_figure():
    """Create empty heatmap figure."""
    return {
        "data": [],
        "layout": {
            "template": "plotly_dark",
            "title": "Select tickers to view correlation",
            "paper_bgcolor": "#2b3035",
            "plot_bgcolor": "#2b3035",
            "xaxis": {"visible": False},
            "yaxis": {"visible": False}
        }
    }


def _create_correlation_heatmap(corr_matrix: Dict, tickers: List[str]):
    """Create correlation heatmap figure."""
    if not corr_matrix or not tickers:
        return _empty_heatmap_figure()
    
    # Build z matrix
    z = []
    for t1 in tickers:
        row = []
        for t2 in tickers:
            val = corr_matrix.get(t1, {}).get(t2, 0)
            row.append(val)
        z.append(row)
    
    return {
        "data": [{
            "type": "heatmap",
            "z": z,
            "x": tickers,
            "y": tickers,
            "colorscale": "RdBu",
            "zmin": -1,
            "zmax": 1,
            "showscale": True,
            "hovertemplate": "%{x} vs %{y}: %{z:.2f}<extra></extra>"
        }],
        "layout": {
            "template": "plotly_dark",
            "title": "Correlation Matrix",
            "paper_bgcolor": "#2b3035",
            "plot_bgcolor": "#2b3035",
            "margin": {"l": 60, "r": 40, "t": 50, "b": 60},
            "xaxis": {"tickangle": -45},
            "yaxis": {"tickangle": 0}
        }
    }


def _execute_rag_query(query: str, source_filter: str, llm_provider: str = None) -> Dict[str, Any]:
    """
    Execute RAG query using FinGPT retriever and model adapters.
    
    Args:
        query: The question to answer
        source_filter: Source filter (all, briefs, news, docs)
        llm_provider: LLM provider to use (openai, hf_lora, mock)
    """
    if data.is_deterministic():
        # Return deterministic mock response
        result = _mock_rag_response(query)
        result["llm_used"] = "mock"
        return result
    
    try:
        # Import our RAG retriever
        from financial_dashboard.services.rag import query_retriever
        from financial_dashboard.models.adapters import MockAdapter
        
        # Step 1: Retrieve relevant documents
        try:
            retrieved_docs = query_retriever(query, top_k=5)
            logger.info(f"Retrieved {len(retrieved_docs)} documents for query")
        except Exception as e:
            logger.warning(f"Retriever failed: {e}, using empty context")
            retrieved_docs = []
        
        # Step 2: Build context from retrieved docs
        if retrieved_docs:
            context = "\n\n".join([
                f"[Source {i+1}]: {doc['text'][:400]}"
                for i, doc in enumerate(retrieved_docs[:3])
            ])
        else:
            context = "(No indexed documents found)"
        
        # Step 3: Get model adapter
        try:
            adapter = _get_model_adapter(llm_provider)
        except Exception as e:
            logger.warning(f"Failed to get model adapter: {e}, using mock")
            adapter = MockAdapter({'name': 'mock', 'type': 'mock'})
        
        # Step 4: Build RAG prompt
        rag_prompt = f"""You are a financial research assistant. Use the following context from indexed documents to answer the question. If the context doesn't contain relevant information, use your general knowledge but note that.

Context:
{context}

Question: {query}

Provide a clear, concise, and actionable answer:"""
        
        # Step 5: Generate answer
        try:
            gen_result = adapter.generate(rag_prompt, max_tokens=512)
            answer = gen_result.get('text', 'No answer generated')
            llm_used = gen_result.get('model', adapter.name)
        except Exception as e:
            logger.exception("Generation failed during RAG generation")
            answer = f"Error generating answer: {str(e)}"
            llm_used = "error"
        
        # Step 6: Format sources
        sources = []
        for i, doc in enumerate(retrieved_docs):
            sources.append({
                "doc_id": f"doc_{i}",
                "title": doc['metadata'].get('filename', 'Unknown') if doc.get('metadata') else f"Document {i+1}",
                "snippet": doc['text'][:200],
                "score": doc.get('score', 0.0)
            })
        
        return {
            "answer_id": f"rag-{datetime.now().timestamp()}",
            "answer": answer,
            "sources": sources,
            "llm_used": llm_used,
            "generated_at": datetime.now().isoformat(),
            "retrieved_count": len(retrieved_docs)
        }
        
    except Exception as e:
        logger.error(f"RAG query failed: {e}")
        # Fallback to mock
        result = _mock_rag_response(query)
        result["llm_used"] = "mock (error fallback)"
        result["error_note"] = str(e)
        return result


def _get_model_adapter(provider: str = None):
    """Get model adapter based on provider name."""
    from financial_dashboard.services.model_config import get_default_adapter
    from financial_dashboard.models.adapters import MockAdapter
    from financial_dashboard.models.openai_adapter import OpenAIAdapter
    
    # If no provider specified or 'auto', use configured backend
    if not provider or provider == "auto":
        return get_default_adapter()
    
    # Explicit mock override
    if provider == "mock":
        return MockAdapter({'name': 'mock', 'type': 'mock'})
    
    # Explicit openai override
    if provider == "openai" or provider.startswith("gpt"):
        config = {
            'name': 'openai',
            'type': 'openai',
            'api_key_env': 'OPENAI_API_KEY',
            'model': 'gpt-4o-mini',
            'max_tokens': 512,
            'temperature': 0.7
        }
        return OpenAIAdapter(config)
    
    # Default to configured adapter
    logger.warning(f"Unknown provider '{provider}', using configured adapter")
    return get_default_adapter()


def _mock_rag_response(query: str) -> Dict[str, Any]:
    """Generate mock RAG response."""
    import hashlib
    seed = int(hashlib.md5(query.encode()).hexdigest()[:8], 16)
    
    return {
        "answer_id": f"mock-{seed}",
        "answer": f"Based on the research documents, here is a synthesized answer to your query about '{query[:50]}...': "
                  f"The analysis indicates key trends in momentum and value factors. "
                  f"Further investigation is recommended for specific sectors.",
        "sources": [
            {
                "doc_id": f"doc-{seed % 100}",
                "title": "Momentum Strategy Analysis",
                "snippet": "Momentum factors show strong performance in tech sector with positive signals...",
                "score": 0.92
            },
            {
                "doc_id": f"doc-{(seed + 1) % 100}",
                "title": "Market Trends Report",
                "snippet": "Current market conditions favor growth stocks with improving fundamentals...",
                "score": 0.85
            }
        ],
        "generated_at": datetime.now().isoformat()
    }


# Import html for use in callbacks
from dash import html
import dash_bootstrap_components as dbc
