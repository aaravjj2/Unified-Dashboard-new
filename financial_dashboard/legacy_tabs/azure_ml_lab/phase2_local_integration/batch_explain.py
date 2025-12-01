"""
Azure ML Lab - Batch Explainability (Phase 2 Local Integration)

Generates explanations for multiple tickers (portfolio-wide analysis).
Saves aggregated reports to JSON files for later review.

Use Cases:
- Explain predictions for all stocks in a portfolio
- Nightly batch processing of model outputs
- Comparative analysis across multiple tickers

Phase 2 Scope: LOCAL BATCH ONLY (uses MockSHAPEngine)
Phase 3: Will integrate with Azure ML SHAP batch endpoints

Author: Unified Financial Dashboard Team
Version: 1.0 (Phase 2)
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

from financial_dashboard.tabs.azure_ml_lab.phase2_local_integration.mode_router import (
    route_explanation_request,
    get_mode_info
)

logger = logging.getLogger(__name__)


# ============================================================================
# BATCH PROCESSING
# ============================================================================

def generate_batch_explanations(
    tickers: List[str],
    prediction_values: Optional[List[float]] = None,
    prediction_target: str = 'return',
    top_n_features: int = 10,
    output_dir: Optional[Path] = None,
    use_cache: bool = True
) -> Dict:
    """
    Generate explanations for multiple tickers in batch.
    
    This is useful for:
    - Portfolio-wide explainability analysis
    - Nightly batch processing of model predictions
    - Comparative feature importance across stocks
    
    Args:
        tickers: List of stock symbols (e.g., ['AAPL', 'TSLA', 'NVDA'])
        prediction_values: Predicted values for each ticker (optional, uses 8% default)
        prediction_target: What's being predicted ('return', 'volatility', 'sharpe')
        top_n_features: Number of top features to explain per ticker
        output_dir: Where to save JSON report (default: outputs/phase2_reports/)
        use_cache: Whether to use LRU cache (mock mode only)
        
    Returns:
        Batch report dictionary with:
        - summary: total_tickers, successful, failed, elapsed_time_seconds
        - results: List of explanation dicts (one per ticker)
        - errors: List of error dicts for failed tickers
        - metadata: mode, timestamp, output_file
        - aggregated_stats: Average cache hit rate, total features analyzed
        
    Example:
        >>> tickers = ['AAPL', 'TSLA', 'NVDA', 'GOOGL']
        >>> report = generate_batch_explanations(tickers, top_n_features=10)
        >>> print(f"Processed {report['summary']['successful']}/{report['summary']['total_tickers']} tickers")
        >>> print(f"Report saved to: {report['metadata']['output_file']}")
    """
    
    logger.info(f"🔄 Starting batch explanation for {len(tickers)} tickers")
    start_time = datetime.now()
    
    # Default prediction values if not provided
    if prediction_values is None:
        prediction_values = [0.08] * len(tickers)  # 8% default return
    
    # Validate input lengths match
    if len(prediction_values) != len(tickers):
        raise ValueError(
            f"Mismatch: {len(tickers)} tickers but {len(prediction_values)} prediction values"
        )
    
    # Initialize results containers
    results = []
    errors = []
    cache_hits = 0
    cache_misses = 0
    
    # Process each ticker
    for i, ticker in enumerate(tickers):
        pred_value = prediction_values[i]
        
        try:
            logger.info(f"  [{i+1}/{len(tickers)}] Processing {ticker}...")
            
            explanation = route_explanation_request(
                ticker=ticker,
                prediction_value=pred_value,
                prediction_target=prediction_target,
                top_n_features=top_n_features,
                use_cache=use_cache
            )
            
            # Check if explanation succeeded
            if 'error' in explanation:
                errors.append({
                    'ticker': ticker,
                    'error': explanation['error'],
                    'message': explanation.get('message', 'Unknown error')
                })
                logger.warning(f"  ⚠️ {ticker} failed: {explanation['error']}")
            else:
                results.append(explanation)
                
                # Track cache stats
                metadata = explanation.get('metadata', {})
                if metadata.get('cache_hit'):
                    cache_hits += 1
                else:
                    cache_misses += 1
                
                logger.info(f"  ✅ {ticker} completed ({metadata.get('generation_time_ms', 0):.1f}ms)")
                
        except Exception as e:
            logger.exception(f"  ❌ Exception for {ticker}: {e}")
            errors.append({
                'ticker': ticker,
                'error': 'Exception',
                'message': str(e)
            })
    
    # Calculate summary stats
    elapsed_seconds = (datetime.now() - start_time).total_seconds()
    total_tickers = len(tickers)
    successful = len(results)
    failed = len(errors)
    
    # Aggregated stats
    total_features_analyzed = successful * top_n_features
    avg_cache_hit_rate = (cache_hits / (cache_hits + cache_misses) * 100) if (cache_hits + cache_misses) > 0 else 0.0
    
    # Build report
    report = {
        'summary': {
            'total_tickers': total_tickers,
            'successful': successful,
            'failed': failed,
            'success_rate_percent': round((successful / total_tickers * 100) if total_tickers > 0 else 0, 1),
            'elapsed_time_seconds': round(elapsed_seconds, 2),
            'avg_time_per_ticker_ms': round((elapsed_seconds / total_tickers * 1000) if total_tickers > 0 else 0, 1)
        },
        'results': results,
        'errors': errors,
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'prediction_target': prediction_target,
            'top_n_features': top_n_features,
            'use_cache': use_cache,
            'mode_info': get_mode_info()
        },
        'aggregated_stats': {
            'total_features_analyzed': total_features_analyzed,
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'avg_cache_hit_rate_percent': round(avg_cache_hit_rate, 1)
        }
    }
    
    # Save to file
    if output_dir is None:
        output_dir = Path('outputs/phase2_reports')
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"batch_explanations_{timestamp}.json"
    output_file = output_dir / filename
    
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2, default=str)  # default=str handles datetime serialization
    
    report['metadata']['output_file'] = str(output_file)
    logger.info(f"✅ Batch complete: {successful}/{total_tickers} successful, saved to {output_file}")
    
    return report


def generate_portfolio_comparison(
    tickers: List[str],
    output_dir: Optional[Path] = None
) -> Dict:
    """
    Generate comparative feature importance analysis for a portfolio.
    
    This creates a special batch report that highlights:
    - Which features are consistently important across stocks
    - Which stocks have unusual feature importance patterns
    - Aggregate feature importance rankings
    
    Args:
        tickers: List of stock symbols to compare
        output_dir: Where to save comparison report
        
    Returns:
        Comparison report with:
        - batch_report: Full batch explanation results
        - feature_rankings: Aggregated feature importance across all stocks
        - outliers: Stocks with unusual patterns
        - metadata: Comparison method, timestamp
        
    Example:
        >>> tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN']
        >>> comparison = generate_portfolio_comparison(tickers)
        >>> print(comparison['feature_rankings'][:5])  # Top 5 most important features
    """
    
    logger.info(f"📊 Generating portfolio comparison for {len(tickers)} tickers")
    
    # Generate batch explanations
    batch_report = generate_batch_explanations(
        tickers=tickers,
        top_n_features=15,  # More features for comparison analysis
        output_dir=output_dir,
        use_cache=True
    )
    
    # Aggregate feature importance across all stocks
    feature_importance_agg = {}
    
    for result in batch_report['results']:
        for feat in result.get('feature_importance', []):
            feature_name = feat['feature']
            # Use abs_shap_value as the importance metric
            importance = feat.get('abs_shap_value', feat.get('contribution_pct', 0.0))
            
            if feature_name not in feature_importance_agg:
                feature_importance_agg[feature_name] = {
                    'total_importance': 0.0,
                    'count': 0,
                    'avg_importance': 0.0
                }
            
            feature_importance_agg[feature_name]['total_importance'] += importance
            feature_importance_agg[feature_name]['count'] += 1
    
    # Calculate averages and rank
    for feat_name, stats in feature_importance_agg.items():
        stats['avg_importance'] = stats['total_importance'] / stats['count']
    
    # Sort by average importance
    feature_rankings = sorted(
        [
            {'feature': name, **stats}
            for name, stats in feature_importance_agg.items()
        ],
        key=lambda x: x['avg_importance'],
        reverse=True
    )
    
    # Build comparison report
    comparison_report = {
        'batch_report': batch_report,
        'feature_rankings': feature_rankings,
        'metadata': {
            'comparison_method': 'Average feature importance across portfolio',
            'num_stocks': len(tickers),
            'timestamp': datetime.now().isoformat()
        }
    }
    
    # Save comparison report
    if output_dir is None:
        output_dir = Path('outputs/phase2_reports')
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"portfolio_comparison_{timestamp}.json"
    output_file = output_dir / filename
    
    with open(output_file, 'w') as f:
        json.dump(comparison_report, f, indent=2, default=str)
    
    comparison_report['metadata']['output_file'] = str(output_file)
    logger.info(f"✅ Portfolio comparison saved to {output_file}")
    
    return comparison_report


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def load_batch_report(report_path: Path) -> Dict:
    """
    Load a previously saved batch report from JSON file.
    
    Args:
        report_path: Path to batch_explanations_*.json file
        
    Returns:
        Batch report dictionary
    """
    with open(report_path, 'r') as f:
        return json.load(f)


def summarize_batch_report(report: Dict) -> str:
    """
    Generate a human-readable summary of a batch report.
    
    Args:
        report: Batch report dictionary
        
    Returns:
        Markdown-formatted summary string
    """
    summary = report['summary']
    agg_stats = report['aggregated_stats']
    
    md = f"""
# Batch Explainability Report

## Summary
- **Total Tickers:** {summary['total_tickers']}
- **Successful:** {summary['successful']} ({summary['success_rate_percent']}%)
- **Failed:** {summary['failed']}
- **Total Time:** {summary['elapsed_time_seconds']}s
- **Avg Time per Ticker:** {summary['avg_time_per_ticker_ms']}ms

## Performance
- **Total Features Analyzed:** {agg_stats['total_features_analyzed']}
- **Cache Hits:** {agg_stats['cache_hits']}
- **Cache Misses:** {agg_stats['cache_misses']}
- **Cache Hit Rate:** {agg_stats['avg_cache_hit_rate_percent']}%

## Results
"""
    
    if report['results']:
        md += "\n### Successful Explanations\n"
        for result in report['results'][:10]:  # Show first 10
            ticker = result['ticker']
            top_feat = result['feature_importance'][0]['feature'] if result.get('feature_importance') else 'N/A'
            md += f"- **{ticker}**: Top feature = {top_feat}\n"
    
    if report['errors']:
        md += "\n### Errors\n"
        for error in report['errors']:
            md += f"- **{error['ticker']}**: {error['error']}\n"
    
    return md


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

logger.info("✓ Batch Explainability module loaded (Phase 2 - Local Mode)")
