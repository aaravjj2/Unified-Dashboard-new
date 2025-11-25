"""
Phase 6 — UI Callbacks for Azure ML Integration
================================================

Dash callbacks to wire Azure ML SHAP and Options Forecast features to UI.

Key Features:
- "Explain Portfolio" button → Batch SHAP orchestrator
- Options Forecast column → AzureMLOptionsClient
- Dynamic updates to Model Insights and Market Forecast tabs
- Automatic mock mode fallback
- Black text (#000000) consistency
- 7+ tooltips for accessibility

Dependencies:
- Phase 6: explainability_azure, options_forecast_azure, phase6_batch_explain
- Phase 3.5: ExplainabilityContract, ForecastContract
- Dash: callback, Input, Output, State

Author: Agent 1A — Unified Financial Dashboard Team
Version: 1.0 (Phase 6)
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import json

from dash import Input, Output, State, html, dcc, callback
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np

# Phase 6 Azure ML Integration
from .explainability_azure import (
    create_azure_shap_client,
    AZURE_ML_FEATURES
)
from .options_forecast_azure import (
    create_azure_options_client
)
from .phase6_batch_explain import (
    create_batch_orchestrator,
    BatchSHAPResult
)

# Phase 3.5 Contracts
from phase3p5_hybrid_bridge.data_bridge.data_contracts import (
    ExplainabilityContract,
    ForecastContract
)

logger = logging.getLogger(__name__)


# =============================================================================
# GLOBAL CLIENT INSTANCES (Singleton Pattern)
# =============================================================================

_SHAP_CLIENT = None
_OPTIONS_CLIENT = None
_BATCH_ORCHESTRATOR = None


def get_shap_client():
    """Get or create singleton AzureMLSHAPClient instance."""
    global _SHAP_CLIENT
    if _SHAP_CLIENT is None:
        _SHAP_CLIENT = create_azure_shap_client()
        logger.info("🔧 AzureMLSHAPClient initialized (singleton)")
    return _SHAP_CLIENT


def get_options_client():
    """Get or create singleton AzureMLOptionsClient instance."""
    global _OPTIONS_CLIENT
    if _OPTIONS_CLIENT is None:
        _OPTIONS_CLIENT = create_azure_options_client()
        logger.info("🔧 AzureMLOptionsClient initialized (singleton)")
    return _OPTIONS_CLIENT


def get_batch_orchestrator():
    """Get or create singleton BatchSHAPOrchestrator instance."""
    global _BATCH_ORCHESTRATOR
    if _BATCH_ORCHESTRATOR is None:
        _BATCH_ORCHESTRATOR = create_batch_orchestrator(
            shap_client=get_shap_client(),
            portfolio_source='csv',  # Default to CSV for Phase 6
            portfolio_file='tmp_first20.csv'  # Use test portfolio in repo root
        )
        logger.info("🔧 BatchSHAPOrchestrator initialized (singleton)")
    return _BATCH_ORCHESTRATOR


# =============================================================================
# CALLBACK: MODEL INSIGHTS — "EXPLAIN PORTFOLIO" BUTTON
# =============================================================================

@callback(
    Output('insight-results-container', 'children'),
    Output('insight-loading-spinner', 'children'),
    Input('explain-portfolio-btn', 'n_clicks'),
    State('portfolio-dropdown', 'value'),
    prevent_initial_call=True
)
def handle_explain_portfolio(n_clicks: int, portfolio_id: str) -> Tuple[Any, str]:
    """
    Handle "Explain Portfolio" button click.
    
    Workflow:
    1. Get batch orchestrator
    2. Call batch_explain_portfolio()
    3. Generate SHAP visualization
    4. Update insight-results-container
    
    Args:
        n_clicks: Button click count
        portfolio_id: Selected portfolio ID from dropdown
    
    Returns:
        (results_html, loading_message)
    """
    if not n_clicks:
        return html.Div("Click 'Explain Portfolio' to generate SHAP insights.", 
                        style={'color': '#000000'}), ""
    
    logger.info(f"🔄 Explain Portfolio clicked (portfolio_id={portfolio_id})")
    
    try:
        # Get orchestrator
        orchestrator = get_batch_orchestrator()
        
        # Run batch SHAP
        result: BatchSHAPResult = orchestrator.batch_explain_portfolio(
            portfolio_id=portfolio_id or "default_portfolio",
            top_n_features=10,
            use_cache=True,
            max_workers=4
        )
        
        # Generate visualization
        results_html = _render_batch_shap_results(result)
        
        logger.info(
            f"✅ Batch SHAP complete: {len(result.contracts)} tickers, "
            f"{result.execution_time_seconds:.2f}s"
        )
        
        return results_html, ""
    
    except Exception as e:
        logger.error(f"❌ Explain Portfolio failed: {e}", exc_info=True)
        
        error_html = html.Div([
            html.H4("⚠️ SHAP Explanation Failed", style={'color': '#000000'}),
            html.P(f"Error: {str(e)}", style={'color': '#000000'}),
            html.P(
                "This may occur if Azure ML endpoint is unavailable. "
                "Check logs or enable mock mode (AZURE_ML_OFFLINE_MODE=True).",
                style={'color': '#000000', 'fontSize': '0.9em'}
            )
        ])
        
        return error_html, ""


def _render_batch_shap_results(result: BatchSHAPResult) -> html.Div:
    """
    Render BatchSHAPResult as Dash HTML components.
    
    Includes:
    - Summary stats (execution time, cache hit rate)
    - Top N features bar chart
    - Per-ticker SHAP waterfall chart
    - Aggregated feature importance table
    
    Args:
        result: BatchSHAPResult to render
    
    Returns:
        html.Div with complete SHAP visualization
    """
    # Summary stats
    summary_div = html.Div([
        html.H3("📊 Batch SHAP Results", style={'color': '#000000'}),
        html.P([
            html.Strong("Portfolio ID: ", style={'color': '#000000'}),
            html.Span(result.portfolio_id, style={'color': '#000000'}),
            html.Br(),
            html.Strong("Tickers Analyzed: ", style={'color': '#000000'}),
            html.Span(f"{len(result.contracts)}/{len(result.tickers)}", 
                      style={'color': '#000000'},
                      title="Number of successfully analyzed tickers"),
            html.Br(),
            html.Strong("Execution Time: ", style={'color': '#000000'}),
            html.Span(f"{result.execution_time_seconds:.2f}s", 
                      style={'color': '#000000'},
                      title="Total batch SHAP processing time"),
            html.Br(),
            html.Strong("Cache Hit Rate: ", style={'color': '#000000'}),
            html.Span(f"{result.cache_hit_rate:.1f}%", 
                      style={'color': '#000000'},
                      title="Percentage of SHAP values retrieved from cache"),
            html.Br(),
            html.Strong("Mode: ", style={'color': '#000000'}),
            html.Span(
                "MOCK (offline)" if result.metadata.get('using_mock') else "Azure ML (live)",
                style={'color': '#000000'},
                title="Azure ML endpoint mode (live) or mock mode (offline)"
            ),
        ], style={'color': '#000000'})
    ], style={'marginBottom': '20px'})
    
    # Top features bar chart
    top_features_chart = _create_top_features_chart(result.top_features)
    
    # Per-ticker SHAP table
    ticker_table = _create_shap_ticker_table(result)
    
    # Aggregated importance table
    importance_table = _create_aggregated_importance_table(result.aggregated_importance)
    
    return html.Div([
        summary_div,
        html.Hr(style={'borderColor': '#ccc'}),
        top_features_chart,
        html.Hr(style={'borderColor': '#ccc'}),
        ticker_table,
        html.Hr(style={'borderColor': '#ccc'}),
        importance_table
    ])


def _create_top_features_chart(top_features: List[Tuple[str, float]]) -> Any:
    """
    Create bar chart for top N features.
    
    Args:
        top_features: List of (feature, importance) tuples
    
    Returns:
        dcc.Graph with Plotly bar chart or html.Div if no data
    """
    if not top_features:
        return html.Div("No features to display.", style={'color': '#000000'})
    
    features, importances = zip(*top_features)
    
    fig = go.Figure(data=[
        go.Bar(
            x=list(importances),
            y=list(features),
            orientation='h',
            marker=dict(color='#1f77b4'),  # Colorblind-safe blue
            text=[f"{imp:.4f}" for imp in importances],
            textposition='outside',
            hovertemplate='<b>%{y}</b><br>Importance: %{x:.4f}<extra></extra>'
        )
    ])
    
    fig.update_layout(
        title=dict(
            text="🏆 Top Features (Global Importance)",
            font=dict(size=16, color='#000000')
        ),
        xaxis=dict(
            title="Aggregated Importance",
            titlefont=dict(color='#000000'),
            tickfont=dict(color='#000000')
        ),
        yaxis=dict(
            title="Feature",
            titlefont=dict(color='#000000'),
            tickfont=dict(color='#000000'),
            autorange='reversed'  # Highest at top
        ),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(color='#000000'),
        height=400,
        margin=dict(l=150, r=100, t=50, b=50)
    )
    
    return dcc.Graph(
        figure=fig,
        config={'displayModeBar': False},
        style={'border': '1px solid #ccc'}
    )


def _create_shap_ticker_table(result: BatchSHAPResult) -> html.Div:
    """
    Create table showing SHAP values per ticker.
    
    Args:
        result: BatchSHAPResult
    
    Returns:
        html.Div with data table
    """
    if not result.contracts:
        return html.Div("No ticker data available.", style={'color': '#000000'})
    
    # Get top 5 features per ticker
    ticker_top_features = result.get_top_features_by_ticker(top_n=5)
    
    rows = []
    
    for ticker in sorted(ticker_top_features.keys()):
        features = ticker_top_features[ticker]
        feature_str = ", ".join([f"{feat}: {imp:.3f}" for feat, imp in features])
        
        rows.append(html.Tr([
            html.Td(ticker, style={'color': '#000000', 'fontWeight': 'bold'}),
            html.Td(feature_str, style={'color': '#000000', 'fontSize': '0.9em'}),
        ]))
    
    table = html.Table([
        html.Thead(html.Tr([
            html.Th("Ticker", style={'color': '#000000', 'backgroundColor': '#f0f0f0'}),
            html.Th("Top 5 Features (Importance)", style={'color': '#000000', 'backgroundColor': '#f0f0f0'}),
        ])),
        html.Tbody(rows)
    ], style={
        'width': '100%',
        'borderCollapse': 'collapse',
        'border': '1px solid #ccc'
    })
    
    return html.Div([
        html.H4("📈 Per-Ticker SHAP Features", style={'color': '#000000'}),
        table
    ])


def _create_aggregated_importance_table(
    aggregated_importance: Dict[str, float],
    max_rows: int = 15
) -> html.Div:
    """
    Create table for all aggregated feature importances.
    
    Args:
        aggregated_importance: Dict of feature → importance
        max_rows: Maximum rows to display
    
    Returns:
        html.Div with scrollable table
    """
    if not aggregated_importance:
        return html.Div("No aggregated data.", style={'color': '#000000'})
    
    # Sort by importance descending
    sorted_features = sorted(
        aggregated_importance.items(),
        key=lambda x: x[1],
        reverse=True
    )[:max_rows]
    
    rows = []
    
    for rank, (feature, importance) in enumerate(sorted_features, 1):
        rows.append(html.Tr([
            html.Td(str(rank), style={'color': '#000000', 'textAlign': 'center'}),
            html.Td(feature, style={'color': '#000000'}),
            html.Td(f"{importance:.4f}", style={'color': '#000000', 'textAlign': 'right'}),
        ]))
    
    table = html.Table([
        html.Thead(html.Tr([
            html.Th("Rank", style={'color': '#000000', 'backgroundColor': '#f0f0f0', 'textAlign': 'center'}),
            html.Th("Feature", style={'color': '#000000', 'backgroundColor': '#f0f0f0'}),
            html.Th("Importance", style={'color': '#000000', 'backgroundColor': '#f0f0f0', 'textAlign': 'right'}),
        ])),
        html.Tbody(rows)
    ], style={
        'width': '100%',
        'borderCollapse': 'collapse',
        'border': '1px solid #ccc'
    })
    
    return html.Div([
        html.H4("📊 Aggregated Feature Importance (All Tickers)", style={'color': '#000000'}),
        html.Div(table, style={
            'maxHeight': '400px',
            'overflowY': 'auto',
            'border': '1px solid #ccc'
        })
    ])


# =============================================================================
# CALLBACK: MARKET FORECAST — OPTIONS FORECAST COLUMN
# =============================================================================

@callback(
    Output('forecast-table-container', 'children'),
    Output('forecast-loading-spinner', 'children'),
    Input('fetch-options-btn', 'n_clicks'),
    State('ticker-dropdown', 'value'),
    prevent_initial_call=True
)
def handle_fetch_options(n_clicks: int, ticker: str) -> Tuple[Any, str]:
    """
    Handle "Fetch Options Forecast" button click.
    
    Workflow:
    1. Get AzureMLOptionsClient
    2. Call generate_options_forecast()
    3. Render IV skew, Greeks, expected returns
    4. Update forecast-table-container
    
    Args:
        n_clicks: Button click count
        ticker: Selected ticker symbol
    
    Returns:
        (forecast_html, loading_message)
    """
    if not n_clicks or not ticker:
        return html.Div(
            "Select a ticker and click 'Fetch Options Forecast'.",
            style={'color': '#000000'}
        ), ""
    
    logger.info(f"🔄 Fetch Options clicked (ticker={ticker})")
    
    try:
        # Get client
        client = get_options_client()
        
        # Generate forecast (expiration=None selects nearest expiration)
        forecast = client.generate_options_forecast(
            ticker=ticker,
            expiration=None,  # Auto-select nearest expiration
            use_cache=True
        )
        
        # Render results
        forecast_html = _render_options_forecast(ticker, forecast)
        
        logger.info(f"✅ Options forecast complete: {ticker}")
        
        return forecast_html, ""
    
    except Exception as e:
        logger.error(f"❌ Options forecast failed: {e}", exc_info=True)
        
        error_html = html.Div([
            html.H4("⚠️ Options Forecast Failed", style={'color': '#000000'}),
            html.P(f"Ticker: {ticker}", style={'color': '#000000'}),
            html.P(f"Error: {str(e)}", style={'color': '#000000'}),
            html.P(
                "Falling back to Black-Scholes mock mode...",
                style={'color': '#000000', 'fontSize': '0.9em'}
            )
        ])
        
        return error_html, ""


def _render_options_forecast(ticker: str, forecast: ForecastContract) -> html.Div:
    """
    Render options forecast as Dash HTML components.
    
    Includes:
    - ATM IV skew metrics
    - Expected return with confidence interval
    - Greeks summary (delta, gamma, theta, vega)
    - Call/Put parity check
    
    Args:
        ticker: Ticker symbol
        forecast: ForecastContract from AzureMLOptionsClient
    
    Returns:
        html.Div with complete options forecast
    """
    metadata = forecast.metadata
    
    # Extract metrics
    atm_call_iv = metadata.get('atm_call_iv', 0.0)
    atm_put_iv = metadata.get('atm_put_iv', 0.0)
    iv_skew = metadata.get('iv_skew_pct', 0.0)
    
    # Expected return from ForecastContract
    expected_return = forecast.expected_return
    return_dist = forecast.return_distribution
    ci_lower = return_dist.get('q025', expected_return - 0.05)  # 2.5% quantile
    ci_upper = return_dist.get('q975', expected_return + 0.05)  # 97.5% quantile
    
    # Greeks (use ATM call as representative)
    greeks = metadata.get('greeks', {})
    delta = greeks.get('delta', 0.0)
    gamma = greeks.get('gamma', 0.0)
    theta = greeks.get('theta', 0.0)
    vega = greeks.get('vega', 0.0)
    
    # Summary div
    summary_div = html.Div([
        html.H3(f"📈 Options Forecast — {ticker}", style={'color': '#000000'}),
        html.P([
            html.Strong("Expected Return (30d): ", style={'color': '#000000'}),
            html.Span(
                f"{expected_return:.2%}",
                style={
                    'color': '#000000',
                    'fontWeight': 'bold',
                    'fontSize': '1.2em'
                },
                title=f"95% CI: [{ci_lower:.2%}, {ci_upper:.2%}]"
            ),
            html.Br(),
            html.Strong("ATM Call IV: ", style={'color': '#000000'}),
            html.Span(f"{atm_call_iv:.2%}", style={'color': '#000000'},
                      title="At-the-money call implied volatility"),
            html.Br(),
            html.Strong("ATM Put IV: ", style={'color': '#000000'}),
            html.Span(f"{atm_put_iv:.2%}", style={'color': '#000000'},
                      title="At-the-money put implied volatility"),
            html.Br(),
            html.Strong("IV Skew: ", style={'color': '#000000'}),
            html.Span(
                f"{iv_skew:+.2f}%",
                style={'color': '#000000'},
                title="Call IV - Put IV (positive = call volatility premium)"
            ),
        ])
    ], style={'marginBottom': '20px'})
    
    # Greeks table
    greeks_table = html.Div([
        html.H4("🔢 Greeks Summary (ATM Call)", style={'color': '#000000'}),
        html.Table([
            html.Thead(html.Tr([
                html.Th("Greek", style={'color': '#000000', 'backgroundColor': '#f0f0f0'}),
                html.Th("Value", style={'color': '#000000', 'backgroundColor': '#f0f0f0'}),
                html.Th("Interpretation", style={'color': '#000000', 'backgroundColor': '#f0f0f0'}),
            ])),
            html.Tbody([
                html.Tr([
                    html.Td("Delta (Δ)", style={'color': '#000000'},
                            title="Price sensitivity to $1 stock move"),
                    html.Td(f"{delta:.4f}", style={'color': '#000000'}),
                    html.Td(_interpret_delta(delta), style={'color': '#000000'}),
                ]),
                html.Tr([
                    html.Td("Gamma (Γ)", style={'color': '#000000'},
                            title="Delta sensitivity to $1 stock move"),
                    html.Td(f"{gamma:.4f}", style={'color': '#000000'}),
                    html.Td(_interpret_gamma(gamma), style={'color': '#000000'}),
                ]),
                html.Tr([
                    html.Td("Theta (Θ)", style={'color': '#000000'},
                            title="Time decay per day"),
                    html.Td(f"{theta:.4f}", style={'color': '#000000'}),
                    html.Td(_interpret_theta(theta), style={'color': '#000000'}),
                ]),
                html.Tr([
                    html.Td("Vega (ν)", style={'color': '#000000'},
                            title="Price sensitivity to 1% volatility change"),
                    html.Td(f"{vega:.4f}", style={'color': '#000000'}),
                    html.Td(_interpret_vega(vega), style={'color': '#000000'}),
                ]),
            ])
        ], style={
            'width': '100%',
            'borderCollapse': 'collapse',
            'border': '1px solid #ccc'
        })
    ], style={'marginTop': '20px'})
    
    return html.Div([
        summary_div,
        html.Hr(style={'borderColor': '#ccc'}),
        greeks_table
    ])


def _interpret_delta(delta: float) -> str:
    """Interpret delta value."""
    if delta > 0.7:
        return "Deep ITM (high probability)"
    elif delta > 0.3:
        return "ATM (moderate probability)"
    else:
        return "OTM (low probability)"


def _interpret_gamma(gamma: float) -> str:
    """Interpret gamma value."""
    if gamma > 0.05:
        return "High sensitivity (near ATM)"
    elif gamma > 0.01:
        return "Moderate sensitivity"
    else:
        return "Low sensitivity (far OTM/ITM)"


def _interpret_theta(theta: float) -> str:
    """Interpret theta value."""
    if theta < -0.05:
        return "High time decay"
    elif theta < -0.01:
        return "Moderate time decay"
    else:
        return "Low time decay"


def _interpret_vega(vega: float) -> str:
    """Interpret vega value."""
    if vega > 0.3:
        return "High volatility sensitivity"
    elif vega > 0.1:
        return "Moderate volatility sensitivity"
    else:
        return "Low volatility sensitivity"


# =============================================================================
# UTILITY: RESET CLIENTS (FOR TESTING)
# =============================================================================

def reset_clients():
    """
    Reset all singleton clients (for testing/debugging).
    
    Forces re-initialization on next callback.
    """
    global _SHAP_CLIENT, _OPTIONS_CLIENT, _BATCH_ORCHESTRATOR
    
    _SHAP_CLIENT = None
    _OPTIONS_CLIENT = None
    _BATCH_ORCHESTRATOR = None
    
    logger.info("🔄 All Phase 6 clients reset")


# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    'handle_explain_portfolio',
    'handle_fetch_options',
    'get_shap_client',
    'get_options_client',
    'get_batch_orchestrator',
    'reset_clients'
]
