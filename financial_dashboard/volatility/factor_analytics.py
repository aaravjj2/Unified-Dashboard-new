"""
Factor Analytics Engine
Calculates beta, factor loadings, and portfolio exposures.

Features:
- Beta calculation (regression on market factor)
- Multi-factor models (Fama-French style)
- Rolling factor exposures
- Portfolio factor attribution

Mathematical Foundation:
- OLS regression: r_asset = α + β * r_market + ε
- Multi-factor: r_asset = α + Σ(β_i * factor_i) + ε

Author: Phase 0.9B - Volatility Lab Full Implementation
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def calculate_returns(prices: pd.Series, method: str = 'log') -> pd.Series:
    """
    Calculate returns from price series.
    
    Args:
        prices: Price series
        method: 'log' or 'simple'
        
    Returns:
        Returns series
    """
    if method == 'log':
        return np.log(prices / prices.shift(1)).dropna()
    else:
        return (prices / prices.shift(1) - 1).dropna()


def calculate_beta(
    asset_returns: pd.Series,
    market_returns: pd.Series,
    window: Optional[int] = None
) -> float:
    """
    Calculate beta using linear regression.
    
    Beta = Cov(r_asset, r_market) / Var(r_market)
    
    Args:
        asset_returns: Asset return series
        market_returns: Market return series (e.g., SPY)
        window: Rolling window (None for full period)
        
    Returns:
        Beta coefficient
    """
    # Align series
    aligned = pd.DataFrame({
        'asset': asset_returns,
        'market': market_returns
    }).dropna()
    
    if len(aligned) < 10:
        logger.warning(f"Insufficient data for beta calculation ({len(aligned)} points)")
        return None
    
    if window:
        aligned = aligned.tail(window)
    
    # Calculate beta using covariance
    covariance = aligned['asset'].cov(aligned['market'])
    market_variance = aligned['market'].var()
    
    if market_variance == 0:
        return None
    
    beta = covariance / market_variance
    
    return beta


def calculate_alpha(
    asset_returns: pd.Series,
    market_returns: pd.Series,
    beta: float,
    risk_free_rate: float = 0.05
) -> float:
    """
    Calculate Jensen's alpha.
    
    α = r_asset - [r_f + β * (r_market - r_f)]
    
    Args:
        asset_returns: Asset return series
        market_returns: Market return series
        beta: Asset beta
        risk_free_rate: Annual risk-free rate
        
    Returns:
        Annualized alpha
    """
    # Convert annual risk-free rate to period rate
    # Assuming daily returns
    rf_period = risk_free_rate / 252
    
    # Align series
    aligned = pd.DataFrame({
        'asset': asset_returns,
        'market': market_returns
    }).dropna()
    
    # Calculate excess returns
    asset_excess = aligned['asset'].mean() - rf_period
    market_excess = aligned['market'].mean() - rf_period
    
    # Jensen's alpha
    alpha = asset_excess - beta * market_excess
    
    # Annualize
    alpha_annualized = alpha * 252
    
    return alpha_annualized


def calculate_correlation_matrix(
    returns_dict: Dict[str, pd.Series],
    method: str = 'pearson'
) -> pd.DataFrame:
    """
    Calculate correlation matrix for multiple assets.
    
    Args:
        returns_dict: Dict of {ticker: returns_series}
        method: 'pearson', 'spearman', or 'kendall'
        
    Returns:
        Correlation matrix DataFrame
    """
    # Combine into DataFrame
    returns_df = pd.DataFrame(returns_dict)
    
    # Calculate correlation
    corr_matrix = returns_df.corr(method=method)
    
    return corr_matrix


def calculate_rolling_beta(
    asset_returns: pd.Series,
    market_returns: pd.Series,
    window: int = 60
) -> pd.Series:
    """
    Calculate rolling beta over time.
    
    Args:
        asset_returns: Asset return series
        market_returns: Market return series
        window: Rolling window size (e.g., 60 days)
        
    Returns:
        Rolling beta series
    """
    # Align series
    aligned = pd.DataFrame({
        'asset': asset_returns,
        'market': market_returns
    }).dropna()
    
    if len(aligned) < window:
        logger.warning(f"Insufficient data for rolling beta (need {window}, have {len(aligned)})")
        return pd.Series()
    
    # Calculate rolling covariance and variance
    rolling_cov = aligned['asset'].rolling(window).cov(aligned['market'])
    rolling_var = aligned['market'].rolling(window).var()
    
    # Beta = Cov / Var
    rolling_beta = rolling_cov / rolling_var
    
    return rolling_beta.dropna()


def calculate_factor_loadings(
    asset_returns: pd.Series,
    factor_returns: Dict[str, pd.Series]
) -> Dict[str, float]:
    """
    Calculate multi-factor loadings using OLS regression.
    
    Model: r_asset = α + β₁*factor₁ + β₂*factor₂ + ... + ε
    
    Args:
        asset_returns: Asset return series
        factor_returns: Dict of {factor_name: returns_series}
        
    Returns:
        Dict of {factor_name: loading, 'alpha': alpha, 'r_squared': R²}
        
    Example:
        >>> factors = {
        ...     'market': spy_returns,
        ...     'size': smb_returns,  # Small Minus Big
        ...     'value': hml_returns   # High Minus Low
        ... }
        >>> loadings = calculate_factor_loadings(aapl_returns, factors)
    """
    from sklearn.linear_model import LinearRegression
    
    # Combine into DataFrame
    df = pd.DataFrame(factor_returns)
    df['asset'] = asset_returns
    df = df.dropna()
    
    if len(df) < 20:
        logger.warning(f"Insufficient data for factor regression ({len(df)} points)")
        return {}
    
    # Prepare X (factors) and y (asset)
    X = df[list(factor_returns.keys())].values
    y = df['asset'].values
    
    # Fit regression
    model = LinearRegression()
    model.fit(X, y)
    
    # Extract results
    loadings = {}
    for i, factor_name in enumerate(factor_returns.keys()):
        loadings[factor_name] = model.coef_[i]
    
    loadings['alpha'] = model.intercept_
    loadings['r_squared'] = model.score(X, y)
    
    return loadings


def calculate_sharpe_ratio(
    returns: pd.Series,
    risk_free_rate: float = 0.05,
    periods_per_year: int = 252
) -> float:
    """
    Calculate Sharpe ratio.
    
    Sharpe = (r_portfolio - r_f) / σ_portfolio
    
    Args:
        returns: Return series
        risk_free_rate: Annual risk-free rate
        periods_per_year: 252 for daily, 52 for weekly, 12 for monthly
        
    Returns:
        Annualized Sharpe ratio
    """
    rf_period = risk_free_rate / periods_per_year
    
    excess_returns = returns - rf_period
    sharpe = excess_returns.mean() / excess_returns.std()
    
    # Annualize
    sharpe_annualized = sharpe * np.sqrt(periods_per_year)
    
    return sharpe_annualized


def calculate_portfolio_factor_exposure(
    holdings: Dict[str, float],
    asset_betas: Dict[str, float]
) -> float:
    """
    Calculate portfolio's aggregate factor exposure.
    
    β_portfolio = Σ(weight_i * β_i)
    
    Args:
        holdings: Dict of {ticker: weight} (weights sum to 1.0)
        asset_betas: Dict of {ticker: beta}
        
    Returns:
        Portfolio beta
    """
    portfolio_beta = 0.0
    
    for ticker, weight in holdings.items():
        beta = asset_betas.get(ticker, 1.0)  # Default to 1.0 if unknown
        portfolio_beta += weight * beta
    
    return portfolio_beta


def calculate_tracking_error(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
    annualize: bool = True
) -> float:
    """
    Calculate tracking error (volatility of excess returns).
    
    TE = σ(r_portfolio - r_benchmark)
    
    Args:
        portfolio_returns: Portfolio return series
        benchmark_returns: Benchmark return series
        annualize: Whether to annualize result
        
    Returns:
        Tracking error
    """
    # Align series
    aligned = pd.DataFrame({
        'portfolio': portfolio_returns,
        'benchmark': benchmark_returns
    }).dropna()
    
    # Calculate excess returns
    excess_returns = aligned['portfolio'] - aligned['benchmark']
    
    # Tracking error
    te = excess_returns.std()
    
    if annualize:
        te = te * np.sqrt(252)  # Assuming daily returns
    
    return te


def calculate_information_ratio(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series
) -> float:
    """
    Calculate information ratio.
    
    IR = (r_portfolio - r_benchmark) / TE
    
    Args:
        portfolio_returns: Portfolio return series
        benchmark_returns: Benchmark return series
        
    Returns:
        Annualized information ratio
    """
    # Align series
    aligned = pd.DataFrame({
        'portfolio': portfolio_returns,
        'benchmark': benchmark_returns
    }).dropna()
    
    # Excess returns
    excess_returns = aligned['portfolio'] - aligned['benchmark']
    
    # Mean and std of excess returns
    mean_excess = excess_returns.mean() * 252  # Annualize
    std_excess = excess_returns.std() * np.sqrt(252)  # Annualize
    
    if std_excess == 0:
        return None
    
    ir = mean_excess / std_excess
    
    return ir
