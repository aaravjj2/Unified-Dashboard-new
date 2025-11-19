"""
Azure ML Lab - Model Insights Callbacks (Phase 2 Local Integration)

This module wires the Model Insight Explorer UI to the explainability engine.
Handles user interactions (button clicks) and renders SHAP-like explanations.

Phase 2 Scope: LOCAL CALLBACKS ONLY (uses MockSHAPEngine)
Phase 3: Will integrate with real Azure ML SHAP endpoints

Author: Unified Financial Dashboard Team
Version: 1.0 (Phase 2)
"""

import logging
import traceback
from dash import Input, Output, State, html, dcc, no_update
from dash.exceptions import PreventUpdate
import dash_bootstrap_components as dbc

# Import the Phase 2 caching-enabled wrapper
from financial_dashboard.tabs.azure_ml_lab.explainability_engine import (
    generate_explanation_summary,
    get_cache_stats
)

logger = logging.getLogger(__name__)


# ============================================================================
# CALLBACK REGISTRATION
# ============================================================================

def register_insight_callbacks(app):
    """
    Register all Model Insight Explorer callbacks.
    
    This function should be called during app initialization to wire up
    the UI components with the explainability engine.
    
    Args:
        app: Dash app instance
    """
    
    @app.callback(
        Output('insight-results-container', 'children'),
        Input('insight-generate-btn', 'n_clicks'),
        State('insight-ticker-selector', 'value'),
        State('insight-top-n-slider', 'value'),
        prevent_initial_call=True
    )
    def generate_insight_explanation(n_clicks, ticker, top_n):
        """
        Generate and render SHAP-like explanation when user clicks Generate button.
        
        Workflow:
        1. Validate inputs (ticker selected, valid top_n)
        2. Call generate_explanation_summary() with caching
        3. Render Plotly chart + textual rationale
        4. Display cache stats + success banner
        5. Handle errors gracefully with error boundary
        
        Args:
            n_clicks: Button click count (triggers callback)
            ticker: Selected stock symbol from dropdown
            top_n: Number of top features to explain (from slider)
            
        Returns:
            Dash component tree for results container
        """
        
        # ===== INPUT VALIDATION =====
        if not ticker:
            return _render_error_alert(
                "⚠️ No Ticker Selected",
                "Please select a stock symbol from the dropdown above."
            )
        
        if not top_n or not isinstance(top_n, int) or top_n < 1:
            return _render_error_alert(
                "⚠️ Invalid Top N Value",
                f"Top N must be a positive integer. Received: {top_n}"
            )
        
        # ===== EXPLANATION GENERATION =====
        try:
            logger.info(f"🔄 Generating explanation for {ticker} (top {top_n} features)")
            
            # Mock prediction value (in real Phase 3, this would come from live model)
            prediction_value = 0.08  # 8% predicted return
            prediction_target = 'return'
            
            # Call Phase 2 cached wrapper
            result = generate_explanation_summary(
                ticker=ticker,
                prediction_value=prediction_value,
                prediction_target=prediction_target,
                top_n_features=top_n,
                use_cache=True
            )
            
            # Check for errors in result
            if 'error' in result:
                return _render_error_alert(
                    "❌ Explanation Failed",
                    result['error']
                )
            
            # ===== RENDER SUCCESS RESPONSE =====
            return _render_explanation_success(result)
            
        except Exception as e:
            logger.exception(f"Exception in generate_insight_explanation: {e}")
            return _render_error_alert(
                "❌ Unexpected Error",
                f"Failed to generate explanation: {str(e)}\n\n{traceback.format_exc()}"
            )


# ============================================================================
# RENDERING HELPERS
# ============================================================================

def _render_error_alert(title: str, message: str):
    """
    Render error alert with red styling.
    
    Args:
        title: Error title (e.g., "⚠️ No Ticker Selected")
        message: Detailed error message
        
    Returns:
        dbc.Alert component
    """
    return dbc.Alert(
        [
            html.H5(title, className="alert-heading", style={'color': '#000000'}),
            html.P(message, style={'color': '#000000', 'white-space': 'pre-wrap'})
        ],
        color="danger",
        dismissable=True
    )


def _render_explanation_success(result: dict):
    """
    Render successful explanation with Plotly chart + rationale.
    
    Args:
        result: Dictionary from generate_explanation_summary() containing:
            - ticker, prediction_value, prediction_target
            - feature_importance: List of {feature, importance, direction}
            - textual_rationale: Markdown explanation
            - plotly_chart: Plotly Figure (optional)
            - metadata: cache_hit, generation_time_ms, cache_stats
            
    Returns:
        html.Div with success banner, chart, rationale, and cache stats
    """
    ticker = result.get('ticker', 'UNKNOWN')
    pred_value = result.get('prediction_value', 0.0)
    pred_target = result.get('prediction_target', 'return')
    rationale = result.get('textual_rationale', '_No rationale available_')
    plotly_chart = result.get('plotly_chart')
    metadata = result.get('metadata', {})
    
    # Extract cache stats
    cache_hit = metadata.get('cache_hit', False)
    gen_time_ms = metadata.get('generation_time_ms', 0.0)
    cache_stats = metadata.get('cache_stats', {})
    
    # Build cache stats badge
    cache_badge_text = (
        f"🎯 Cache HIT ({gen_time_ms:.1f}ms)" if cache_hit 
        else f"⏱️ Cache MISS ({gen_time_ms:.1f}ms)"
    )
    cache_badge_color = "success" if cache_hit else "warning"
    
    # Build overall cache stats text
    total_calls = cache_stats.get('total_calls', 0)
    hits = cache_stats.get('hits', 0)
    hit_rate = (hits / total_calls * 100) if total_calls > 0 else 0.0
    overall_cache_text = (
        f"Session Cache: {hits}/{total_calls} hits ({hit_rate:.1f}% hit rate)"
    )
    
    # Build components
    components = []
    
    # 1. Success banner with cache badge
    components.append(
        dbc.Alert(
            [
                html.Div([
                    html.H5(
                        f"✅ Explanation Generated for {ticker}",
                        className="alert-heading",
                        style={'color': '#000000', 'display': 'inline-block', 'margin-right': '10px'}
                    ),
                    dbc.Badge(
                        cache_badge_text,
                        color=cache_badge_color,
                        className="ms-2",
                        style={'color': '#000000'}
                    )
                ], style={'margin-bottom': '10px'}),
                html.P(
                    f"Prediction: {pred_value:.2%} {pred_target}",
                    style={'color': '#000000', 'margin-bottom': '5px'}
                ),
                html.Small(
                    overall_cache_text,
                    style={'color': '#000000', 'font-style': 'italic'}
                )
            ],
            color="success",
            dismissable=True
        )
    )
    
    # 2. Plotly chart (if available)
    if plotly_chart:
        components.append(
            dbc.Card(
                dbc.CardBody([
                    html.H5("📊 Feature Importance Chart", style={'color': '#000000'}),
                    dcc.Graph(
                        figure=plotly_chart,
                        config={'displayModeBar': False},
                        style={'height': '400px'}
                    )
                ]),
                className="mb-3"
            )
        )
    else:
        components.append(
            dbc.Alert(
                "⚠️ Chart unavailable (Plotly not installed or error occurred)",
                color="warning",
                className="mb-3"
            )
        )
    
    # 3. Textual rationale
    components.append(
        dbc.Card(
            dbc.CardBody([
                html.H5("💬 Explanation Rationale", style={'color': '#000000'}),
                dcc.Markdown(
                    rationale,
                    style={'color': '#000000', 'line-height': '1.6'}
                )
            ]),
            className="mb-3"
        )
    )
    
    # 4. Feature importance table (optional detail)
    feature_importance = result.get('feature_importance', [])
    if feature_importance:
        table_rows = []
        for feat in feature_importance[:10]:  # Show top 10
            # Handle both 'importance' and 'abs_shap_value' field names
            importance_val = feat.get('abs_shap_value', feat.get('contribution_pct', 0.0))
            shap_value = feat.get('shap_value', 0.0)
            
            table_rows.append(
                html.Tr([
                    html.Td(feat['feature'], style={'color': '#000000'}),
                    html.Td(f"{importance_val:.4f}", style={'color': '#000000'}),
                    html.Td(
                        "🔴 Negative" if shap_value < 0 else "🟢 Positive",
                        style={'color': '#000000'}
                    )
                ])
            )
        
        components.append(
            dbc.Card(
                dbc.CardBody([
                    html.H5("📋 Feature Importance Details", style={'color': '#000000'}),
                    html.Table([
                        html.Thead(
                            html.Tr([
                                html.Th("Feature", style={'color': '#000000'}),
                                html.Th("Importance", style={'color': '#000000'}),
                                html.Th("Direction", style={'color': '#000000'})
                            ])
                        ),
                        html.Tbody(table_rows)
                    ], className="table table-striped table-hover")
                ]),
                className="mb-3"
            )
        )
    
    return html.Div(components)


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

logger.info("✓ Model Insights callbacks loaded (Phase 2 - Local Mode)")
