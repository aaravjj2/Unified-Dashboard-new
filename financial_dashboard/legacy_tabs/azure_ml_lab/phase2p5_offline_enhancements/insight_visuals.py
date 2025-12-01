"""
Azure ML Lab - Advanced Insight Visualizations (Phase 2.5 Offline Enhancements)

Implements rich, interactive Plotly visualizations for SHAP-like feature importance.
Provides multiple chart types optimized for different analytical perspectives.

Chart Types:
- Bar Chart: Classic feature importance ranking
- Waterfall Chart: Cumulative contribution breakdown
- Heatmap: Feature correlation and clustering
- Beeswarm Plot: Feature value distributions
- Force Plot: Single prediction breakdown

All charts enforce black text (#000000) for accessibility.

Author: Unified Financial Dashboard Team
Version: 1.0 (Phase 2.5)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Check for Plotly availability
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("⚠️ Plotly not available - visualizations will be limited")


# ============================================================================
# COLOR SCHEMES (Accessibility-First)
# ============================================================================

# Black text enforced throughout
TEXT_COLOR = '#000000'
GRID_COLOR = '#E0E0E0'
BACKGROUND_COLOR = '#FFFFFF'

# Feature importance color scales (colorblind-friendly)
IMPORTANCE_COLOR_SCALE = [
    '#4575B4',  # Blue (low importance)
    '#74ADD1',
    '#ABD9E9',
    '#E0F3F8',
    '#FEE090',
    '#FDAE61',
    '#F46D43',
    '#D73027'   # Red (high importance)
]

# Direction colors (positive/negative contribution)
POSITIVE_COLOR = '#2E7D32'  # Dark green
NEGATIVE_COLOR = '#C62828'  # Dark red
NEUTRAL_COLOR = '#757575'   # Gray


# ============================================================================
# 1. BAR CHART - Classic Feature Importance
# ============================================================================

def create_feature_importance_bar(
    feature_importance: List[Dict],
    ticker: str,
    title: Optional[str] = None,
    top_n: int = 10
) -> go.Figure:
    """
    Create interactive bar chart for feature importance.
    
    Args:
        feature_importance: List of dicts with keys [feature, abs_shap_value, shap_value]
        ticker: Stock ticker symbol
        title: Chart title (default: "Feature Importance for {ticker}")
        top_n: Number of top features to display
        
    Returns:
        Plotly Figure object
        
    Example:
        >>> fig = create_feature_importance_bar(importance_data, 'AAPL', top_n=10)
        >>> fig.show()
    """
    if not PLOTLY_AVAILABLE:
        logger.error("Plotly not available")
        return None
    
    # Extract top N features
    top_features = feature_importance[:top_n]
    
    # Prepare data
    features = [f['feature'] for f in top_features]
    importances = [f.get('abs_shap_value', f.get('contribution_pct', 0)) for f in top_features]
    shap_values = [f.get('shap_value', 0) for f in top_features]
    
    # Assign colors based on direction
    colors = [POSITIVE_COLOR if sv > 0 else NEGATIVE_COLOR for sv in shap_values]
    
    # Create figure
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=features[::-1],  # Reverse for top-to-bottom
        x=importances[::-1],
        orientation='h',
        marker=dict(
            color=colors[::-1],
            line=dict(color=TEXT_COLOR, width=0.5)
        ),
        text=[f"{imp:.4f}" for imp in importances[::-1]],
        textposition='outside',
        textfont=dict(color=TEXT_COLOR, size=11),
        hovertemplate=(
            '<b>%{y}</b><br>' +
            'Importance: %{x:.4f}<br>' +
            '<extra></extra>'
        )
    ))
    
    # Layout
    fig.update_layout(
        title=dict(
            text=title or f"Feature Importance for {ticker}",
            font=dict(size=16, color=TEXT_COLOR, family='Arial, sans-serif'),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title="Absolute SHAP Value",
            titlefont=dict(color=TEXT_COLOR, size=12),
            tickfont=dict(color=TEXT_COLOR, size=10),
            gridcolor=GRID_COLOR,
            showgrid=True
        ),
        yaxis=dict(
            title="",
            tickfont=dict(color=TEXT_COLOR, size=10),
            showgrid=False
        ),
        plot_bgcolor=BACKGROUND_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        margin=dict(l=150, r=50, t=80, b=50),
        height=400 + (top_n * 15),  # Dynamic height
        showlegend=False
    )
    
    return fig


# ============================================================================
# 2. WATERFALL CHART - Cumulative Contribution
# ============================================================================

def create_waterfall_chart(
    feature_importance: List[Dict],
    ticker: str,
    baseline_value: float = 0.0,
    prediction_value: float = 0.08,
    top_n: int = 10
) -> go.Figure:
    """
    Create waterfall chart showing cumulative feature contributions.
    
    Shows how features incrementally build up from baseline to final prediction.
    
    Args:
        feature_importance: List of dicts with feature importance
        ticker: Stock ticker
        baseline_value: Model baseline (e.g., average prediction)
        prediction_value: Final prediction value
        top_n: Number of features to display
        
    Returns:
        Plotly Figure object
        
    Example:
        >>> fig = create_waterfall_chart(importance_data, 'AAPL', 0.0, 0.08)
        >>> fig.show()
    """
    if not PLOTLY_AVAILABLE:
        logger.error("Plotly not available")
        return None
    
    # Extract top N features
    top_features = feature_importance[:top_n]
    
    # Prepare data
    feature_names = ['Baseline'] + [f['feature'] for f in top_features] + ['Final Prediction']
    shap_values = [baseline_value] + [f.get('shap_value', 0) for f in top_features] + [0]
    
    # Calculate cumulative values for positioning
    cumulative = [baseline_value]
    for sv in shap_values[1:-1]:
        cumulative.append(cumulative[-1] + sv)
    cumulative.append(prediction_value)
    
    # Prepare measure types
    measures = ['absolute'] + ['relative'] * len(top_features) + ['total']
    
    # Colors
    colors = [NEUTRAL_COLOR]
    for sv in shap_values[1:-1]:
        colors.append(POSITIVE_COLOR if sv > 0 else NEGATIVE_COLOR)
    colors.append(NEUTRAL_COLOR)
    
    # Create waterfall
    fig = go.Figure(go.Waterfall(
        name="Feature Contributions",
        orientation="v",
        measure=measures,
        x=feature_names,
        y=shap_values,
        text=[f"{val:+.4f}" if val != 0 else f"{val:.4f}" for val in shap_values],
        textposition="outside",
        textfont=dict(color=TEXT_COLOR, size=10),
        connector={"line": {"color": GRID_COLOR, "width": 1}},
        increasing={"marker": {"color": POSITIVE_COLOR}},
        decreasing={"marker": {"color": NEGATIVE_COLOR}},
        totals={"marker": {"color": NEUTRAL_COLOR}}
    ))
    
    fig.update_layout(
        title=dict(
            text=f"Waterfall Analysis: {ticker} Prediction Breakdown",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title="Features",
            titlefont=dict(color=TEXT_COLOR),
            tickfont=dict(color=TEXT_COLOR, size=9),
            tickangle=-45
        ),
        yaxis=dict(
            title="Cumulative Contribution",
            titlefont=dict(color=TEXT_COLOR),
            tickfont=dict(color=TEXT_COLOR),
            gridcolor=GRID_COLOR,
            showgrid=True
        ),
        plot_bgcolor=BACKGROUND_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        margin=dict(l=60, r=40, t=80, b=120),
        height=500,
        showlegend=False
    )
    
    return fig


# ============================================================================
# 3. HEATMAP - Feature Correlation Matrix
# ============================================================================

def create_feature_heatmap(
    feature_importance_list: List[Dict[str, List[Dict]]],
    tickers: List[str],
    top_n: int = 15
) -> go.Figure:
    """
    Create heatmap showing feature importance across multiple tickers.
    
    Useful for identifying which features are consistently important
    across a portfolio.
    
    Args:
        feature_importance_list: List of feature importance results (one per ticker)
        tickers: List of ticker symbols
        top_n: Number of top features to include
        
    Returns:
        Plotly Figure object
        
    Example:
        >>> results = [result_aapl, result_tsla, result_nvda]
        >>> tickers = ['AAPL', 'TSLA', 'NVDA']
        >>> fig = create_feature_heatmap(results, tickers, top_n=10)
        >>> fig.show()
    """
    if not PLOTLY_AVAILABLE:
        logger.error("Plotly not available")
        return None
    
    # Collect all unique features
    all_features = set()
    for result in feature_importance_list:
        for feat in result.get('feature_importance', [])[:top_n]:
            all_features.add(feat['feature'])
    
    # Build matrix
    features_list = sorted(all_features)
    importance_matrix = []
    
    for ticker_result in feature_importance_list:
        ticker_importances = {}
        for feat in ticker_result.get('feature_importance', []):
            ticker_importances[feat['feature']] = feat.get('abs_shap_value', 0)
        
        row = [ticker_importances.get(f, 0) for f in features_list]
        importance_matrix.append(row)
    
    # Transpose for better visualization (features as rows)
    importance_matrix = np.array(importance_matrix).T
    
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=importance_matrix,
        x=tickers,
        y=features_list,
        colorscale=IMPORTANCE_COLOR_SCALE,
        text=importance_matrix,
        texttemplate='%{text:.3f}',
        textfont=dict(color=TEXT_COLOR, size=9),
        hovertemplate=(
            '<b>%{y}</b><br>' +
            '<b>%{x}</b><br>' +
            'Importance: %{z:.4f}<br>' +
            '<extra></extra>'
        ),
        colorbar=dict(
            title="Importance",
            titlefont=dict(color=TEXT_COLOR),
            tickfont=dict(color=TEXT_COLOR)
        )
    ))
    
    fig.update_layout(
        title=dict(
            text=f"Feature Importance Heatmap ({len(tickers)} Tickers)",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title="Tickers",
            titlefont=dict(color=TEXT_COLOR),
            tickfont=dict(color=TEXT_COLOR, size=11),
            side='top'
        ),
        yaxis=dict(
            title="Features",
            titlefont=dict(color=TEXT_COLOR),
            tickfont=dict(color=TEXT_COLOR, size=9)
        ),
        plot_bgcolor=BACKGROUND_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        margin=dict(l=180, r=100, t=100, b=50),
        height=400 + (len(features_list) * 20)
    )
    
    return fig


# ============================================================================
# 4. BEESWARM PLOT - Feature Value Distribution
# ============================================================================

def create_beeswarm_plot(
    feature_importance: List[Dict],
    ticker: str,
    top_n: int = 10
) -> go.Figure:
    """
    Create beeswarm-style plot showing feature value distributions.
    
    Each dot represents a feature, positioned by importance and colored by direction.
    
    Args:
        feature_importance: List of feature importance dicts
        ticker: Stock ticker
        top_n: Number of features to display
        
    Returns:
        Plotly Figure object
    """
    if not PLOTLY_AVAILABLE:
        logger.error("Plotly not available")
        return None
    
    top_features = feature_importance[:top_n]
    
    # Separate positive and negative contributions
    positive_features = [f for f in top_features if f.get('shap_value', 0) > 0]
    negative_features = [f for f in top_features if f.get('shap_value', 0) < 0]
    
    fig = go.Figure()
    
    # Positive contributions
    if positive_features:
        fig.add_trace(go.Scatter(
            x=[f.get('abs_shap_value', 0) for f in positive_features],
            y=[f['feature'] for f in positive_features],
            mode='markers',
            name='Positive',
            marker=dict(
                size=12,
                color=POSITIVE_COLOR,
                line=dict(color=TEXT_COLOR, width=1),
                symbol='circle'
            ),
            text=[f"SHAP: +{f.get('shap_value', 0):.4f}" for f in positive_features],
            hovertemplate='<b>%{y}</b><br>%{text}<extra></extra>'
        ))
    
    # Negative contributions
    if negative_features:
        fig.add_trace(go.Scatter(
            x=[f.get('abs_shap_value', 0) for f in negative_features],
            y=[f['feature'] for f in negative_features],
            mode='markers',
            name='Negative',
            marker=dict(
                size=12,
                color=NEGATIVE_COLOR,
                line=dict(color=TEXT_COLOR, width=1),
                symbol='circle'
            ),
            text=[f"SHAP: {f.get('shap_value', 0):.4f}" for f in negative_features],
            hovertemplate='<b>%{y}</b><br>%{text}<extra></extra>'
        ))
    
    fig.update_layout(
        title=dict(
            text=f"Feature Distribution: {ticker}",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title="Absolute SHAP Value",
            titlefont=dict(color=TEXT_COLOR),
            tickfont=dict(color=TEXT_COLOR),
            gridcolor=GRID_COLOR,
            showgrid=True
        ),
        yaxis=dict(
            title="",
            tickfont=dict(color=TEXT_COLOR, size=10),
            showgrid=False
        ),
        plot_bgcolor=BACKGROUND_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        legend=dict(
            font=dict(color=TEXT_COLOR, size=11),
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor=TEXT_COLOR,
            borderwidth=1
        ),
        margin=dict(l=150, r=50, t=80, b=50),
        height=400
    )
    
    return fig


# ============================================================================
# 5. FORCE PLOT - Single Prediction Breakdown
# ============================================================================

def create_force_plot(
    feature_importance: List[Dict],
    ticker: str,
    baseline_value: float = 0.0,
    prediction_value: float = 0.08,
    top_n: int = 10
) -> go.Figure:
    """
    Create force plot (horizontal stacked bar) showing push/pull of features.
    
    Visualizes which features push the prediction higher (positive) or
    lower (negative) from the baseline.
    
    Args:
        feature_importance: Feature importance data
        ticker: Stock ticker
        baseline_value: Model baseline
        prediction_value: Final prediction
        top_n: Number of features to show
        
    Returns:
        Plotly Figure object
    """
    if not PLOTLY_AVAILABLE:
        logger.error("Plotly not available")
        return None
    
    top_features = feature_importance[:top_n]
    
    # Separate positive and negative
    positive = [f for f in top_features if f.get('shap_value', 0) > 0]
    negative = [f for f in top_features if f.get('shap_value', 0) < 0]
    
    fig = go.Figure()
    
    # Baseline marker
    fig.add_trace(go.Scatter(
        x=[baseline_value],
        y=[0.5],
        mode='markers+text',
        name='Baseline',
        marker=dict(size=15, color=NEUTRAL_COLOR, symbol='diamond'),
        text=[f"Baseline: {baseline_value:.4f}"],
        textposition='top center',
        textfont=dict(color=TEXT_COLOR, size=10),
        showlegend=False
    ))
    
    # Positive features (pushing right)
    if positive:
        pos_start = baseline_value
        for f in positive:
            shap = f.get('shap_value', 0)
            fig.add_trace(go.Scatter(
                x=[pos_start, pos_start + shap],
                y=[0.5, 0.5],
                mode='lines+text',
                name=f['feature'],
                line=dict(color=POSITIVE_COLOR, width=8),
                text=['', f['feature'][:10]],
                textposition='top center',
                textfont=dict(color=TEXT_COLOR, size=9),
                hovertemplate=f"<b>{f['feature']}</b><br>+{shap:.4f}<extra></extra>"
            ))
            pos_start += shap
    
    # Negative features (pushing left)
    if negative:
        neg_start = baseline_value
        for f in negative:
            shap = f.get('shap_value', 0)
            fig.add_trace(go.Scatter(
                x=[neg_start, neg_start + shap],
                y=[0.5, 0.5],
                mode='lines+text',
                name=f['feature'],
                line=dict(color=NEGATIVE_COLOR, width=8),
                text=['', f['feature'][:10]],
                textposition='bottom center',
                textfont=dict(color=TEXT_COLOR, size=9),
                hovertemplate=f"<b>{f['feature']}</b><br>{shap:.4f}<extra></extra>"
            ))
            neg_start += shap
    
    # Final prediction marker
    fig.add_trace(go.Scatter(
        x=[prediction_value],
        y=[0.5],
        mode='markers+text',
        name='Prediction',
        marker=dict(size=15, color='#1976D2', symbol='star'),
        text=[f"Prediction: {prediction_value:.4f}"],
        textposition='bottom center',
        textfont=dict(color=TEXT_COLOR, size=10),
        showlegend=False
    ))
    
    fig.update_layout(
        title=dict(
            text=f"Force Plot: {ticker} Prediction Drivers",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title="Prediction Value",
            titlefont=dict(color=TEXT_COLOR),
            tickfont=dict(color=TEXT_COLOR),
            gridcolor=GRID_COLOR,
            showgrid=True,
            zeroline=True,
            zerolinecolor=TEXT_COLOR,
            zerolinewidth=2
        ),
        yaxis=dict(
            visible=False,
            range=[0, 1]
        ),
        plot_bgcolor=BACKGROUND_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        showlegend=False,
        margin=dict(l=50, r=50, t=80, b=80),
        height=300
    )
    
    return fig


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def get_available_chart_types() -> List[str]:
    """Return list of available chart types."""
    return [
        'bar',
        'waterfall',
        'heatmap',
        'beeswarm',
        'force'
    ]


def create_chart_by_type(
    chart_type: str,
    feature_importance: List[Dict],
    ticker: str,
    **kwargs
) -> Optional[go.Figure]:
    """
    Factory function to create charts by type.
    
    Args:
        chart_type: One of ['bar', 'waterfall', 'heatmap', 'beeswarm', 'force']
        feature_importance: Feature importance data
        ticker: Stock ticker
        **kwargs: Additional chart-specific arguments
        
    Returns:
        Plotly Figure or None
    """
    chart_map = {
        'bar': create_feature_importance_bar,
        'waterfall': create_waterfall_chart,
        'beeswarm': create_beeswarm_plot,
        'force': create_force_plot
    }
    
    if chart_type not in chart_map:
        logger.error(f"Unknown chart type: {chart_type}")
        return None
    
    try:
        return chart_map[chart_type](feature_importance, ticker, **kwargs)
    except Exception as e:
        logger.exception(f"Failed to create {chart_type} chart: {e}")
        return None


logger.info("✓ Insight Visuals module loaded (Phase 2.5 - Advanced Charts)")


# ============================================================================
# PHASE 3 EXTENSIONS: Portfolio Analytics Visualizations
# ============================================================================

def create_risk_radar(risk_metrics: Dict, benchmark_metrics: Optional[Dict] = None) -> go.Figure:
    """Create radar chart comparing risk metrics.
    
    Args:
        risk_metrics: Portfolio risk metrics
        benchmark_metrics: Optional benchmark metrics for comparison
    
    Returns:
        Plotly radar chart
    """
    if not PLOTLY_AVAILABLE:
        return None
    
    # Normalize metrics to 0-1 scale for radar display
    metrics_config = {
        'sharpe_ratio': {'scale': 3.0, 'label': 'Sharpe Ratio'},
        'sortino_ratio': {'scale': 3.0, 'label': 'Sortino Ratio'},
        'information_ratio': {'scale': 2.0, 'label': 'Info Ratio'},
        'volatility': {'scale': 0.3, 'label': 'Volatility', 'invert': True},
        'max_drawdown': {'scale': 0.3, 'label': 'Max Drawdown', 'invert': True}
    }
    
    categories = []
    portfolio_values = []
    
    for key, config in metrics_config.items():
        if key in risk_metrics and risk_metrics[key] is not None:
            categories.append(config['label'])
            val = abs(float(risk_metrics[key])) / config['scale']
            if config.get('invert'):
                val = 1 - min(val, 1)
            portfolio_values.append(min(val, 1))
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatterpolar(
        r=portfolio_values,
        theta=categories,
        fill='toself',
        name='Portfolio',
        line=dict(color='#2E7D32', width=2),
        fillcolor='rgba(46, 125, 50, 0.3)'
    ))
    
    if benchmark_metrics:
        benchmark_values = []
        for key, config in metrics_config.items():
            if key in benchmark_metrics and benchmark_metrics[key] is not None:
                val = abs(float(benchmark_metrics[key])) / config['scale']
                if config.get('invert'):
                    val = 1 - min(val, 1)
                benchmark_values.append(min(val, 1))
        
        fig.add_trace(go.Scatterpolar(
            r=benchmark_values,
            theta=categories,
            fill='toself',
            name='Benchmark',
            line=dict(color='#1565C0', width=2),
            fillcolor='rgba(21, 101, 192, 0.2)'
        ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], showticklabels=False),
            angularaxis=dict(color=TEXT_COLOR)
        ),
        showlegend=True,
        title=dict(text='Risk Profile Comparison', font=dict(color=TEXT_COLOR, size=16)),
        font=dict(color=TEXT_COLOR, size=12),
        paper_bgcolor=BACKGROUND_COLOR,
        plot_bgcolor=BACKGROUND_COLOR,
        height=500
    )
    
    return fig


def create_attribution_waterfall(sector_data: List[Dict]) -> go.Figure:
    """Create waterfall chart showing sector contribution to returns.
    
    Args:
        sector_data: List of dicts with keys [sector, contribution]
    
    Returns:
        Plotly waterfall chart
    """
    if not PLOTLY_AVAILABLE:
        return None
    
    # Sort by contribution
    sorted_sectors = sorted(sector_data, key=lambda x: x.get('contribution', 0), reverse=True)
    
    sectors = [s['sector'] for s in sorted_sectors]
    contributions = [s.get('contribution', 0) * 100 for s in sorted_sectors]
    
    # Determine colors based on positive/negative
    colors = [POSITIVE_COLOR if c >= 0 else NEGATIVE_COLOR for c in contributions]
    
    fig = go.Figure(go.Waterfall(
        x=sectors,
        y=contributions,
        measure=['relative'] * len(sectors),
        text=[f"{c:+.2f}%" for c in contributions],
        textposition='outside',
        connector={'line': {'color': GRID_COLOR}},
        increasing={'marker': {'color': POSITIVE_COLOR}},
        decreasing={'marker': {'color': NEGATIVE_COLOR}},
        totals={'marker': {'color': NEUTRAL_COLOR}}
    ))
    
    fig.update_layout(
        title=dict(text='Sector Attribution (% Contribution)', font=dict(color=TEXT_COLOR, size=16)),
        xaxis=dict(title='Sector', color=TEXT_COLOR, gridcolor=GRID_COLOR),
        yaxis=dict(title='Contribution (%)', color=TEXT_COLOR, gridcolor=GRID_COLOR),
        font=dict(color=TEXT_COLOR, size=12),
        paper_bgcolor=BACKGROUND_COLOR,
        plot_bgcolor=BACKGROUND_COLOR,
        height=500,
        showlegend=False
    )
    
    return fig


def create_sector_heatmap(sector_data: List[Dict]) -> go.Figure:
    """Create heatmap showing sector allocation vs. performance.
    
    Args:
        sector_data: List of dicts with keys [sector, allocation_pct, avg_return]
    
    Returns:
        Plotly heatmap
    """
    if not PLOTLY_AVAILABLE:
        return None
    
    sectors = [s['sector'] for s in sector_data]
    allocations = [s.get('allocation_pct', 0) for s in sector_data]
    returns = [s.get('avg_return', 0) * 100 if 'avg_return' in s else 0 for s in sector_data]
    
    # Create 2x matrix for heatmap display
    z_data = [allocations, returns]
    y_labels = ['Allocation %', 'Return %']
    
    fig = go.Figure(go.Heatmap(
        z=z_data,
        x=sectors,
        y=y_labels,
        colorscale='RdYlGn',
        text=[[f"{v:.1f}" for v in row] for row in z_data],
        texttemplate='%{text}',
        textfont=dict(color=TEXT_COLOR, size=11),
        colorbar=dict(title='Value', tickfont=dict(color=TEXT_COLOR))
    ))
    
    fig.update_layout(
        title=dict(text='Sector Allocation & Performance', font=dict(color=TEXT_COLOR, size=16)),
        xaxis=dict(title='Sector', color=TEXT_COLOR, side='bottom'),
        yaxis=dict(color=TEXT_COLOR),
        font=dict(color=TEXT_COLOR, size=12),
        paper_bgcolor=BACKGROUND_COLOR,
        height=400
    )
    
    return fig


def render_portfolio_analytics(analytics_report: Dict) -> Dict[str, go.Figure]:
    """Render complete set of portfolio analytics visualizations.
    
    Args:
        analytics_report: Complete analytics report from PortfolioAnalyticsEngine
    
    Returns:
        Dictionary of figure name -> Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        return {}
    
    figures = {}
    
    # Risk radar
    risk_metrics = analytics_report.get('risk_metrics', {})
    benchmark = analytics_report.get('benchmark_comparison', {})
    
    if risk_metrics:
        benchmark_risk = None
        if 'benchmark' in benchmark and 'error' not in benchmark:
            # Extract benchmark metrics if available
            benchmark_risk = {
                'sharpe_ratio': 0.5,  # Placeholder
                'volatility': 0.15
            }
        
        figures['risk_radar'] = create_risk_radar(risk_metrics, benchmark_risk)
    
    # Sector visualizations
    sector_analysis = analytics_report.get('sector_analysis', {})
    sectors = sector_analysis.get('sectors', [])
    
    if sectors:
        # Attribution waterfall (if contribution data available)
        if any('contribution' in s for s in sectors):
            figures['attribution_waterfall'] = create_attribution_waterfall(sectors)
        
        # Sector heatmap
        figures['sector_heatmap'] = create_sector_heatmap(sectors)
    
    return figures
