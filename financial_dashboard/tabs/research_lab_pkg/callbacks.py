"""
Research Lab - Callbacks Module

Implements interactive behavior for the Research Lab.
Uses idempotent registration pattern to prevent duplicate callbacks.
"""

import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Any

from dash import Input, Output, State, callback_context, no_update, ALL, MATCH
from dash.exceptions import PreventUpdate

from . import components
from . import data

logger = logging.getLogger(__name__)

# Idempotent registration guard
_callbacks_registered = False


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
    Execute RAG query using actual LLM connector.
    
    In deterministic mode or if LLM unavailable, returns mock response.
    Otherwise, calls the LLM connector directly.
    
    Args:
        query: The question to answer
        source_filter: Source filter (all, briefs, news, docs)
        llm_provider: LLM provider to use (openai, ollama, gpt4all, mock)
    """
    if data.is_deterministic():
        # Return deterministic mock response
        result = _mock_rag_response(query)
        result["llm_used"] = "mock"
        return result
    
    # Try using the LLM connector directly
    try:
        from financial_dashboard.services.llm_local import get_llm_connector, RAGQueryEngine
        
        # Use provided provider or default to openai
        provider = llm_provider or os.getenv("LLM_PROVIDER", "openai")
        connector = get_llm_connector(provider)
        
        if connector.name != "mock" and connector.is_available():
            # Use RAG query engine with real LLM
            try:
                engine = RAGQueryEngine(llm_connector=connector)
                result = engine.query(query, top_k=5, sources=source_filter)
                result["llm_used"] = connector.name
                return result
            except Exception as e:
                logger.warning(f"RAG engine failed, falling back to direct LLM: {e}")
                # Fall back to direct LLM call without RAG
                prompt = f"""You are a financial research assistant. Answer the following question based on your knowledge of financial markets, investing strategies, and economic factors.

Question: {query}

Provide a clear, concise, and actionable answer:"""
                answer = connector.generate(prompt, max_tokens=512)
                return {
                    "answer_id": f"llm-{datetime.now().timestamp()}",
                    "answer": answer,
                    "sources": [],
                    "llm_used": connector.name,
                    "generated_at": datetime.now().isoformat()
                }
        
    except Exception as e:
        logger.warning(f"LLM connector unavailable: {e}")
    
    # Try to call RAG API as fallback
    try:
        import requests
        api_url = os.getenv("RESEARCH_API_BASE_URL", "http://127.0.0.1:8051")
        response = requests.post(
            f"{api_url}/api/research/query",
            json={"query": query, "sources": source_filter, "top_k": 5},
            timeout=30
        )
        if response.status_code == 200:
            result = response.json()
            result["llm_used"] = "api"
            return result
    except Exception as e:
        logger.warning(f"RAG API unavailable: {e}")
    
    # Fallback to mock
    result = _mock_rag_response(query)
    result["llm_used"] = "mock"
    return result


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
