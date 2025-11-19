"""
utils/attribution.py

Attribution analysis for trading picks - decompose realized returns into:
- Beta contribution (market risk)
- Alpha residual (stock-specific performance)
- Factor contributions (grouped SHAP values)

Key functions:
- estimate_beta: Estimate stock's beta vs benchmark using rolling regression
- aggregate_shap_by_factor: Group SHAP values by factor categories
- compute_alpha_beta_decomposition: Full attribution pipeline for a pick
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import logging
from scipy import stats
from sklearn.linear_model import LinearRegression, HuberRegressor

logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

# Beta estimation parameters
DEFAULT_BETA_WINDOW = 126  # ~6 months of trading days
MIN_OBSERVATIONS_BETA = 20  # Minimum data points for beta estimation
ROBUST_REGRESSION_THRESHOLD = 0.8  # Use robust regression if R² < this

# Factor mapping - categorize features into broader factors
FACTOR_MAP = {
    # Momentum factors
    'momentum': [
        'ret_1m', 'ret_3m', 'ret_6m', 'ret_12m',
        'mom_', 'rsi_', 'macd_',
        'price_vs_ma', 'ma50_slope', 'ma200_slope',
    ],
    
    # Sentiment factors
    'sentiment': [
        'sentiment_', 'finbert_', 'news_',
        'headline_', 'social_',
    ],
    
    # Value factors
    'value': [
        'pe_', 'pb_', 'ps_', 'pcf_',
        'ev_ebitda', 'peg_', 'yield_',
        'valuation_', 'earnings_yield',
    ],
    
    # Size/Liquidity factors
    'size': [
        'market_cap', 'log_mcap', 'size_',
        'adv_', 'volume_', 'turnover_',
        'liquidity_', 'spread_',
    ],
    
    # Quality factors
    'quality': [
        'roa_', 'roe_', 'roic_',
        'margin_', 'fcf_', 'debt_',
        'quality_', 'profitability_',
    ],
    
    # Volatility factors
    'volatility': [
        'vol_', 'std_', 'atr_',
        'realized_vol', 'iv_', 'vix_',
        'beta_', 'idio_vol',
    ],
    
    # Growth factors
    'growth': [
        'revenue_growth', 'earnings_growth', 'eps_growth',
        'growth_', 'yoy_', 'qoq_',
    ],
    
    # Macro factors
    'macro': [
        'spy_', 'market_', 'sector_',
        'rates_', 'treasury_', 'credit_',
        'gdp_', 'inflation_', 'unemployment_',
    ],
}


# ============================================================================
# Beta Estimation
# ============================================================================

def estimate_beta(
    returns_df: pd.DataFrame,
    ticker: str,
    benchmark: str = 'SPY',
    window: int = DEFAULT_BETA_WINDOW,
    use_robust: Optional[bool] = None,
) -> Tuple[float, float, Dict[str, Any]]:
    """
    Estimate stock's beta vs benchmark using rolling regression.
    
    Args:
        returns_df: DataFrame with columns [date, ticker, returns, SPY_returns]
                   or multi-column format with ticker and benchmark returns
        ticker: Ticker symbol to estimate beta for
        benchmark: Benchmark ticker (default 'SPY')
        window: Lookback window in days for regression
        use_robust: Force robust regression. If None, auto-decide based on R²
    
    Returns:
        Tuple of (beta, alpha, metadata_dict)
        - beta: Estimated market beta
        - alpha: Regression intercept (annualized alpha)
        - metadata: Dict with r_squared, n_obs, method, stderr_beta
    
    Raises:
        ValueError: If insufficient data for estimation
    """
    try:
        # Extract returns for ticker and benchmark
        if 'ticker' in returns_df.columns:
            ticker_returns = returns_df[returns_df['ticker'] == ticker]['returns'].values
            bench_returns = returns_df[returns_df['ticker'] == benchmark]['returns'].values
        else:
            # Assume columns are ticker names
            ticker_returns = returns_df[ticker].values if ticker in returns_df.columns else None
            bench_returns = returns_df[benchmark].values if benchmark in returns_df.columns else None
        
        if ticker_returns is None or bench_returns is None:
            raise ValueError(f"Could not find returns for {ticker} or {benchmark}")
        
        # Align lengths and remove NaN
        min_len = min(len(ticker_returns), len(bench_returns))
        ticker_returns = ticker_returns[-min_len:]
        bench_returns = bench_returns[-min_len:]
        
        # Create mask for valid observations
        valid_mask = ~(np.isnan(ticker_returns) | np.isnan(bench_returns))
        ticker_returns = ticker_returns[valid_mask]
        bench_returns = bench_returns[valid_mask]
        
        # Apply window
        if len(ticker_returns) > window:
            ticker_returns = ticker_returns[-window:]
            bench_returns = bench_returns[-window:]
        
        n_obs = len(ticker_returns)
        
        if n_obs < MIN_OBSERVATIONS_BETA:
            raise ValueError(
                f"Insufficient data: {n_obs} observations < {MIN_OBSERVATIONS_BETA} minimum"
            )
        
        # Reshape for sklearn
        X = bench_returns.reshape(-1, 1)
        y = ticker_returns
        
        # Fit OLS regression first
        ols_model = LinearRegression()
        ols_model.fit(X, y)
        beta_ols = ols_model.coef_[0]
        alpha_ols = ols_model.intercept_
        
        # Calculate R²
        y_pred = ols_model.predict(X)
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - np.mean(y)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        # Decide whether to use robust regression
        if use_robust is None:
            use_robust = r_squared < ROBUST_REGRESSION_THRESHOLD
        
        if use_robust:
            # Use Huber regression for robustness to outliers
            robust_model = HuberRegressor(epsilon=1.35, max_iter=200)
            robust_model.fit(X, y)
            beta = robust_model.coef_[0]
            alpha = robust_model.intercept_
            method = 'huber_robust'
            logger.info(
                f"Used robust regression for {ticker}: OLS R²={r_squared:.3f}, "
                f"beta_ols={beta_ols:.3f}, beta_robust={beta:.3f}"
            )
        else:
            beta = beta_ols
            alpha = alpha_ols
            method = 'ols'
        
        # Calculate standard error of beta
        residuals = y - (alpha + beta * bench_returns)
        mse = np.sum(residuals ** 2) / (n_obs - 2)
        var_x = np.sum((bench_returns - np.mean(bench_returns)) ** 2)
        stderr_beta = np.sqrt(mse / var_x) if var_x > 0 else np.nan
        
        # Annualize alpha (assuming daily returns)
        alpha_annual = alpha * 252
        
        metadata = {
            'r_squared': float(r_squared),
            'n_obs': int(n_obs),
            'method': method,
            'stderr_beta': float(stderr_beta),
            'alpha_daily': float(alpha),
            'alpha_annual': float(alpha_annual),
            'beta_ols': float(beta_ols) if use_robust else float(beta),
        }
        
        return float(beta), float(alpha_annual), metadata
        
    except Exception as e:
        logger.error(f"Beta estimation failed for {ticker}: {e}")
        # Return neutral beta with error metadata
        return 1.0, 0.0, {
            'r_squared': 0.0,
            'n_obs': 0,
            'method': 'fallback',
            'error': str(e),
        }


# ============================================================================
# SHAP Aggregation by Factor
# ============================================================================

def aggregate_shap_by_factor(
    shap_values: Dict[str, float],
    feature_names: Optional[List[str]] = None,
    factor_map: Optional[Dict[str, List[str]]] = None,
    include_other: bool = True,
) -> Dict[str, float]:
    """
    Aggregate SHAP values by factor categories.
    
    Args:
        shap_values: Dict mapping feature names to SHAP values
                    OR array of SHAP values (requires feature_names)
        feature_names: List of feature names (if shap_values is array)
        factor_map: Custom factor mapping (default uses FACTOR_MAP)
        include_other: Include 'other' category for unmapped features
    
    Returns:
        Dict mapping factor names to aggregated SHAP contributions
        Keys: factor names + 'other' (if include_other=True)
    
    Example:
        >>> shap_dict = {'ret_1m': 0.05, 'sentiment_mean': 0.03, 'pe_ratio': -0.02}
        >>> factors = aggregate_shap_by_factor(shap_dict)
        >>> print(factors)
        {'momentum': 0.05, 'sentiment': 0.03, 'value': -0.02}
    """
    # Handle array input
    if isinstance(shap_values, (list, np.ndarray)):
        if feature_names is None:
            raise ValueError("feature_names required when shap_values is array")
        shap_values = dict(zip(feature_names, shap_values))
    
    # Use default factor map if not provided
    if factor_map is None:
        factor_map = FACTOR_MAP
    
    # Initialize factor contributions
    factor_contribs = {factor: 0.0 for factor in factor_map.keys()}
    if include_other:
        factor_contribs['other'] = 0.0
    
    # Aggregate SHAP values by factor
    for feature, shap_val in shap_values.items():
        if pd.isna(shap_val) or not isinstance(shap_val, (int, float)):
            continue
            
        # Find which factor this feature belongs to
        assigned = False
        for factor, patterns in factor_map.items():
            for pattern in patterns:
                if pattern in feature.lower():
                    factor_contribs[factor] += shap_val
                    assigned = True
                    break
            if assigned:
                break
        
        # Add to 'other' if not assigned
        if not assigned and include_other:
            factor_contribs['other'] += shap_val
    
    # Remove factors with zero contribution (optional, cleaner output)
    factor_contribs = {k: v for k, v in factor_contribs.items() if abs(v) > 1e-8}
    
    return factor_contribs


# ============================================================================
# Full Attribution Pipeline
# ============================================================================

def compute_alpha_beta_decomposition(
    ticker: str,
    realized_return: float,
    benchmark_return: float,
    returns_history_df: pd.DataFrame,
    shap_values: Optional[Dict[str, float]] = None,
    benchmark: str = 'SPY',
) -> Dict[str, Any]:
    """
    Complete attribution decomposition for a single pick.
    
    Attribution equation:
        realized_return = beta * benchmark_return + alpha_residual
    
    Args:
        ticker: Ticker symbol
        realized_return: Actual return over horizon (e.g., 1 week or 1 month)
        benchmark_return: Benchmark return over same horizon
        returns_history_df: Historical returns for beta estimation
        shap_values: Optional dict of SHAP values for factor attribution
        benchmark: Benchmark ticker (default 'SPY')
    
    Returns:
        Dict with keys:
        - ticker: str
        - realized_return: float
        - beta: float
        - beta_contrib: float (= beta * benchmark_return)
        - alpha: float (= realized_return - beta_contrib)
        - benchmark_return: float
        - factor_attribution: Dict[str, float] (if shap_values provided)
        - beta_metadata: Dict (r_squared, n_obs, method, etc.)
    """
    # Estimate beta
    beta, alpha_intercept, beta_metadata = estimate_beta(
        returns_history_df,
        ticker=ticker,
        benchmark=benchmark,
    )
    
    # Decompose return
    beta_contrib = beta * benchmark_return
    alpha_residual = realized_return - beta_contrib
    
    result = {
        'ticker': ticker,
        'realized_return': round(realized_return, 4),
        'beta': round(beta, 3),
        'beta_contrib': round(beta_contrib, 4),
        'alpha': round(alpha_residual, 4),
        'benchmark_return': round(benchmark_return, 4),
        'beta_metadata': beta_metadata,
    }
    
    # Add factor attribution if SHAP values provided
    if shap_values:
        factor_contribs = aggregate_shap_by_factor(shap_values)
        result['factor_attribution'] = {
            k: round(v, 4) for k, v in factor_contribs.items()
        }
        
        # Add top factors
        top_factors = sorted(
            factor_contribs.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:3]
        result['top_factors'] = [
            {'factor': f, 'contribution': round(c, 4)}
            for f, c in top_factors
        ]
    
    return result


# ============================================================================
# Batch Processing Helpers
# ============================================================================

def compute_portfolio_attribution(
    picks_df: pd.DataFrame,
    returns_history_df: pd.DataFrame,
    shap_dict: Optional[Dict[str, Dict[str, float]]] = None,
    benchmark: str = 'SPY',
) -> pd.DataFrame:
    """
    Compute attribution for entire portfolio of picks.
    
    Args:
        picks_df: DataFrame with columns [ticker, realized_return, benchmark_return]
        returns_history_df: Historical returns for beta estimation
        shap_dict: Optional dict mapping ticker -> SHAP values dict
        benchmark: Benchmark ticker
    
    Returns:
        DataFrame with attribution results for each pick
        Columns: ticker, realized_return, beta, beta_contrib, alpha, ...
    """
    results = []
    
    for _, row in picks_df.iterrows():
        ticker = row['ticker']
        shap_values = shap_dict.get(ticker) if shap_dict else None
        
        attribution = compute_alpha_beta_decomposition(
            ticker=ticker,
            realized_return=row['realized_return'],
            benchmark_return=row['benchmark_return'],
            returns_history_df=returns_history_df,
            shap_values=shap_values,
            benchmark=benchmark,
        )
        
        results.append(attribution)
    
    return pd.DataFrame(results)


def aggregate_portfolio_metrics(attribution_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Aggregate attribution metrics across entire portfolio.
    
    Args:
        attribution_df: DataFrame from compute_portfolio_attribution
    
    Returns:
        Dict with portfolio-level metrics:
        - total_return: Sum of realized returns
        - total_beta_contrib: Sum of beta contributions
        - total_alpha: Sum of alpha residuals
        - avg_beta: Average beta across picks
        - factor_contributions: Aggregated factor contributions
    """
    metrics = {
        'n_picks': len(attribution_df),
        'total_return': attribution_df['realized_return'].sum(),
        'total_beta_contrib': attribution_df['beta_contrib'].sum(),
        'total_alpha': attribution_df['alpha'].sum(),
        'avg_beta': attribution_df['beta'].mean(),
        'median_beta': attribution_df['beta'].median(),
    }
    
    # Aggregate factor contributions if available
    if 'factor_attribution' in attribution_df.columns:
        all_factors = {}
        for factor_dict in attribution_df['factor_attribution'].dropna():
            for factor, contrib in factor_dict.items():
                all_factors[factor] = all_factors.get(factor, 0.0) + contrib
        
        metrics['factor_contributions'] = {
            k: round(v, 4) for k, v in all_factors.items()
        }
        
        # Top factors at portfolio level
        top_factors = sorted(
            all_factors.items(),
            key=lambda x: abs(x[1]),
            reverse=True
        )[:5]
        metrics['top_factors'] = [
            {'factor': f, 'contribution': round(c, 4)}
            for f, c in top_factors
        ]
    
    return metrics
