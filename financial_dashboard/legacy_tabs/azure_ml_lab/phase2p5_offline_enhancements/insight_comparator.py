"""
Azure ML Lab - Multi-Ticker Comparison (Phase 2.5 Offline Enhancements)

Enables side-by-side comparison of feature importance across multiple tickers.
Helps identify portfolio-wide patterns and ticker-specific drivers.

Features:
- Side-by-side bar charts
- Correlation heatmaps
- Differential analysis (which features differ most)
- Consensus ranking (features important across all tickers)

Author: Unified Financial Dashboard Team
Version: 1.0 (Phase 2.5)
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Import visualization functions
try:
    from financial_dashboard.tabs.azure_ml_lab.phase2p5_offline_enhancements.insight_visuals import (
        create_feature_heatmap,
        PLOTLY_AVAILABLE,
        TEXT_COLOR,
        GRID_COLOR,
        BACKGROUND_COLOR,
        POSITIVE_COLOR,
        NEGATIVE_COLOR
    )
    if PLOTLY_AVAILABLE:
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots
except ImportError:
    PLOTLY_AVAILABLE = False
    logger.warning("⚠️ visualization dependencies not available")


# ============================================================================
# COMPARISON DATA STRUCTURES
# ============================================================================

def generate_comparison_dataset(
    results: List[Dict],
    tickers: List[str]
) -> pd.DataFrame:
    """
    Convert multiple explanation results into comparison-ready DataFrame.
    
    Args:
        results: List of explanation dicts (from generate_explanation_summary)
        tickers: List of ticker symbols
        
    Returns:
        DataFrame with columns [ticker, feature, importance, shap_value, rank]
    """
    rows = []
    
    for ticker, result in zip(tickers, results):
        feature_importance = result.get('feature_importance', [])
        
        for rank, feat in enumerate(feature_importance, start=1):
            rows.append({
                'ticker': ticker,
                'feature': feat['feature'],
                'importance': feat.get('abs_shap_value', 0),
                'shap_value': feat.get('shap_value', 0),
                'rank': rank
            })
    
    return pd.DataFrame(rows)


# ============================================================================
# 1. SIDE-BY-SIDE BAR CHARTS
# ============================================================================

def create_side_by_side_bars(
    results: List[Dict],
    tickers: List[str],
    top_n: int = 10
) -> Optional[go.Figure]:
    """
    Create side-by-side bar charts comparing feature importance across tickers.
    
    Args:
        results: List of explanation results
        tickers: List of ticker symbols
        top_n: Number of top features per ticker
        
    Returns:
        Plotly Figure with subplots
        
    Example:
        >>> results = [explain_aapl, explain_tsla, explain_nvda]
        >>> tickers = ['AAPL', 'TSLA', 'NVDA']
        >>> fig = create_side_by_side_bars(results, tickers, top_n=8)
        >>> fig.show()
    """
    if not PLOTLY_AVAILABLE:
        logger.error("Plotly not available")
        return None
    
    num_tickers = len(tickers)
    fig = make_subplots(
        rows=1,
        cols=num_tickers,
        subplot_titles=tickers,
        horizontal_spacing=0.1
    )
    
    for idx, (ticker, result) in enumerate(zip(tickers, results), start=1):
        feature_importance = result.get('feature_importance', [])[:top_n]
        
        features = [f['feature'] for f in feature_importance]
        importances = [f.get('abs_shap_value', 0) for f in feature_importance]
        shap_values = [f.get('shap_value', 0) for f in feature_importance]
        
        colors = [POSITIVE_COLOR if sv > 0 else NEGATIVE_COLOR for sv in shap_values]
        
        fig.add_trace(
            go.Bar(
                y=features[::-1],
                x=importances[::-1],
                orientation='h',
                marker=dict(color=colors[::-1]),
                text=[f"{imp:.3f}" for imp in importances[::-1]],
                textposition='outside',
                textfont=dict(color=TEXT_COLOR, size=9),
                showlegend=False,
                hovertemplate='<b>%{y}</b><br>Importance: %{x:.4f}<extra></extra>'
            ),
            row=1,
            col=idx
        )
        
        # Update subplot axes
        fig.update_xaxes(
            title_text="Importance" if idx == 1 else "",
            titlefont=dict(color=TEXT_COLOR, size=10),
            tickfont=dict(color=TEXT_COLOR, size=8),
            gridcolor=GRID_COLOR,
            showgrid=True,
            row=1,
            col=idx
        )
        
        fig.update_yaxes(
            tickfont=dict(color=TEXT_COLOR, size=8),
            showgrid=False,
            row=1,
            col=idx
        )
    
    fig.update_layout(
        title=dict(
            text=f"Feature Importance Comparison ({num_tickers} Tickers)",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.5,
            xanchor='center'
        ),
        plot_bgcolor=BACKGROUND_COLOR,
        paper_bgcolor=BACKGROUND_COLOR,
        height=500,
        margin=dict(l=150, r=50, t=100, b=50)
    )
    
    # Update subplot title fonts
    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(color=TEXT_COLOR, size=12)
    
    return fig


# ============================================================================
# 2. DIFFERENTIAL ANALYSIS
# ============================================================================

def compute_differential_importance(
    results: List[Dict],
    tickers: List[str],
    top_n: int = 15
) -> pd.DataFrame:
    """
    Identify features that vary most in importance across tickers.
    
    High variance = ticker-specific drivers
    Low variance = portfolio-wide drivers
    
    Args:
        results: List of explanation results
        tickers: List of ticker symbols
        top_n: Number of features to analyze
        
    Returns:
        DataFrame with [feature, mean_importance, std_importance, cv, max_ticker, min_ticker]
    """
    df = generate_comparison_dataset(results, tickers)
    
    # Aggregate by feature
    feature_stats = df.groupby('feature').agg({
        'importance': ['mean', 'std', 'min', 'max', 'count']
    }).reset_index()
    
    feature_stats.columns = ['feature', 'mean_importance', 'std_importance', 
                              'min_importance', 'max_importance', 'count']
    
    # Calculate coefficient of variation (std / mean)
    feature_stats['cv'] = feature_stats['std_importance'] / (feature_stats['mean_importance'] + 1e-8)
    
    # Find tickers with max/min importance for each feature
    max_tickers = []
    min_tickers = []
    
    for feat in feature_stats['feature']:
        feat_df = df[df['feature'] == feat]
        max_tickers.append(feat_df.loc[feat_df['importance'].idxmax(), 'ticker'])
        min_tickers.append(feat_df.loc[feat_df['importance'].idxmin(), 'ticker'])
    
    feature_stats['max_ticker'] = max_tickers
    feature_stats['min_ticker'] = min_tickers
    
    # Sort by coefficient of variation (most variable first)
    feature_stats = feature_stats.sort_values('cv', ascending=False)
    
    return feature_stats.head(top_n)


def create_differential_chart(
    results: List[Dict],
    tickers: List[str],
    top_n: int = 10
) -> Optional[go.Figure]:
    """
    Visualize differential importance as horizontal bars with variance bands.
    
    Args:
        results: Explanation results
        tickers: Ticker symbols
        top_n: Number of features to display
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        logger.error("Plotly not available")
        return None
    
    diff_df = compute_differential_importance(results, tickers, top_n)
    
    fig = go.Figure()
    
    # Mean importance bars
    fig.add_trace(go.Bar(
        y=diff_df['feature'][::-1],
        x=diff_df['mean_importance'][::-1],
        orientation='h',
        name='Mean Importance',
        marker=dict(color='#1976D2'),
        error_x=dict(
            type='data',
            array=diff_df['std_importance'][::-1],
            color=TEXT_COLOR,
            thickness=1.5
        ),
        text=[f"{m:.3f}±{s:.3f}" for m, s in 
              zip(diff_df['mean_importance'][::-1], diff_df['std_importance'][::-1])],
        textposition='outside',
        textfont=dict(color=TEXT_COLOR, size=9)
    ))
    
    fig.update_layout(
        title=dict(
            text=f"Differential Feature Importance (Variance Analysis)",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title="Mean Importance ± Std Dev",
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
        showlegend=False,
        height=400 + (top_n * 15),
        margin=dict(l=150, r=50, t=80, b=50)
    )
    
    return fig


# ============================================================================
# 3. CONSENSUS RANKING
# ============================================================================

def compute_consensus_ranking(
    results: List[Dict],
    tickers: List[str],
    method: str = 'mean_rank'
) -> pd.DataFrame:
    """
    Identify features that are consistently important across all tickers.
    
    Methods:
    - 'mean_rank': Average rank across tickers (lower = more important)
    - 'mean_importance': Average absolute importance
    - 'top3_frequency': How often feature appears in top 3
    
    Args:
        results: Explanation results
        tickers: Ticker symbols
        method: Ranking method
        
    Returns:
        DataFrame with consensus ranking
    """
    df = generate_comparison_dataset(results, tickers)
    
    if method == 'mean_rank':
        consensus = df.groupby('feature')['rank'].mean().sort_values()
        consensus_df = pd.DataFrame({
            'feature': consensus.index,
            'mean_rank': consensus.values,
            'method': 'mean_rank'
        })
    
    elif method == 'mean_importance':
        consensus = df.groupby('feature')['importance'].mean().sort_values(ascending=False)
        consensus_df = pd.DataFrame({
            'feature': consensus.index,
            'mean_importance': consensus.values,
            'method': 'mean_importance'
        })
    
    elif method == 'top3_frequency':
        top3_counts = df[df['rank'] <= 3].groupby('feature').size()
        consensus_df = pd.DataFrame({
            'feature': top3_counts.index,
            'top3_count': top3_counts.values,
            'top3_frequency': top3_counts.values / len(tickers),
            'method': 'top3_frequency'
        }).sort_values('top3_count', ascending=False)
    
    else:
        raise ValueError(f"Unknown method: {method}")
    
    # Add ticker appearances
    consensus_df['appears_in_n_tickers'] = df.groupby('feature').size().reindex(consensus_df['feature']).values
    
    return consensus_df


def create_consensus_chart(
    results: List[Dict],
    tickers: List[str],
    method: str = 'mean_rank',
    top_n: int = 10
) -> Optional[go.Figure]:
    """
    Visualize consensus ranking across portfolio.
    
    Args:
        results: Explanation results
        tickers: Ticker symbols
        method: Ranking method ('mean_rank', 'mean_importance', 'top3_frequency')
        top_n: Number of features to display
        
    Returns:
        Plotly Figure
    """
    if not PLOTLY_AVAILABLE:
        logger.error("Plotly not available")
        return None
    
    consensus_df = compute_consensus_ranking(results, tickers, method).head(top_n)
    
    fig = go.Figure()
    
    if method == 'mean_rank':
        # Lower rank = better (reverse x-axis)
        fig.add_trace(go.Bar(
            y=consensus_df['feature'][::-1],
            x=consensus_df['mean_rank'][::-1],
            orientation='h',
            marker=dict(color='#388E3C'),
            text=[f"Rank {r:.1f}" for r in consensus_df['mean_rank'][::-1]],
            textposition='outside',
            textfont=dict(color=TEXT_COLOR, size=10)
        ))
        x_title = "Average Rank (lower = more important)"
        
    elif method == 'mean_importance':
        fig.add_trace(go.Bar(
            y=consensus_df['feature'][::-1],
            x=consensus_df['mean_importance'][::-1],
            orientation='h',
            marker=dict(color='#1976D2'),
            text=[f"{imp:.3f}" for imp in consensus_df['mean_importance'][::-1]],
            textposition='outside',
            textfont=dict(color=TEXT_COLOR, size=10)
        ))
        x_title = "Average Importance"
        
    elif method == 'top3_frequency':
        fig.add_trace(go.Bar(
            y=consensus_df['feature'][::-1],
            x=consensus_df['top3_frequency'][::-1],
            orientation='h',
            marker=dict(color='#D32F2F'),
            text=[f"{freq*100:.0f}%" for freq in consensus_df['top3_frequency'][::-1]],
            textposition='outside',
            textfont=dict(color=TEXT_COLOR, size=10)
        ))
        x_title = "Top-3 Frequency (%)"
    
    fig.update_layout(
        title=dict(
            text=f"Consensus Feature Ranking ({len(tickers)} Tickers)",
            font=dict(size=16, color=TEXT_COLOR),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            title=x_title,
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
        showlegend=False,
        height=400 + (top_n * 15),
        margin=dict(l=150, r=50, t=80, b=50)
    )
    
    return fig


# ============================================================================
# 4. COMPARATIVE SUMMARY REPORT
# ============================================================================

def generate_comparison_report(
    results: List[Dict],
    tickers: List[str]
) -> Dict:
    """
    Generate comprehensive comparison report with statistics and insights.
    
    Args:
        results: Explanation results
        tickers: Ticker symbols
        
    Returns:
        Dict with summary statistics, consensus ranking, differential analysis
    """
    df = generate_comparison_dataset(results, tickers)
    
    # Consensus ranking (all 3 methods)
    consensus_mean_rank = compute_consensus_ranking(results, tickers, 'mean_rank')
    consensus_mean_imp = compute_consensus_ranking(results, tickers, 'mean_importance')
    consensus_top3 = compute_consensus_ranking(results, tickers, 'top3_frequency')
    
    # Differential analysis
    differential = compute_differential_importance(results, tickers)
    
    # Summary stats
    report = {
        'metadata': {
            'num_tickers': len(tickers),
            'tickers': tickers,
            'timestamp': datetime.now().isoformat(),
            'total_features_analyzed': len(df['feature'].unique())
        },
        'consensus_rankings': {
            'by_mean_rank': consensus_mean_rank.head(10).to_dict('records'),
            'by_mean_importance': consensus_mean_imp.head(10).to_dict('records'),
            'by_top3_frequency': consensus_top3.head(10).to_dict('records')
        },
        'differential_analysis': {
            'most_variable_features': differential.head(10).to_dict('records'),
            'portfolio_wide_drivers': differential.tail(10).to_dict('records')
        },
        'summary': {
            'top_consensus_feature': consensus_mean_rank.iloc[0]['feature'],
            'most_variable_feature': differential.iloc[0]['feature'],
            'least_variable_feature': differential.iloc[-1]['feature']
        }
    }
    
    return report


logger.info("✓ Insight Comparator module loaded (Phase 2.5 - Multi-Ticker)")
