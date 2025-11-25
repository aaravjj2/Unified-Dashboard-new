"""Risk Metrics Computer

Computes comprehensive portfolio risk metrics including:
- Daily returns and volatility (annualized)
- Sharpe ratio and Sortino ratio
- Beta vs benchmark
- Value at Risk (VaR) at 95% confidence
- Maximum drawdown
- Tracking error

All computations are fully offline using pandas/numpy.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import Dict, Optional


def compute_returns(prices: pd.Series) -> pd.Series:
    """Compute daily percentage returns from price series."""
    return prices.pct_change().dropna()


def compute_volatility(returns: pd.Series, annualize: bool = True) -> float:
    """Compute volatility (standard deviation of returns).
    
    Args:
        returns: Series of daily returns
        annualize: If True, multiply by sqrt(252) for annual volatility
    
    Returns:
        Volatility as a float
    """
    vol = returns.std()
    if annualize:
        vol *= np.sqrt(252)
    return float(vol)


def compute_sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """Compute annualized Sharpe ratio.
    
    Args:
        returns: Series of daily returns
        risk_free_rate: Annual risk-free rate (default 2%)
    
    Returns:
        Sharpe ratio
    """
    excess_returns = returns - (risk_free_rate / 252)
    if excess_returns.std() == 0:
        return 0.0
    sharpe = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)
    return float(sharpe)


def compute_sortino_ratio(returns: pd.Series, risk_free_rate: float = 0.02) -> float:
    """Compute annualized Sortino ratio (downside deviation).
    
    Args:
        returns: Series of daily returns
        risk_free_rate: Annual risk-free rate
    
    Returns:
        Sortino ratio
    """
    excess_returns = returns - (risk_free_rate / 252)
    downside_returns = excess_returns[excess_returns < 0]
    
    if len(downside_returns) == 0 or downside_returns.std() == 0:
        return 0.0
    
    sortino = (excess_returns.mean() / downside_returns.std()) * np.sqrt(252)
    return float(sortino)


def compute_beta(portfolio_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """Compute beta vs benchmark.
    
    Args:
        portfolio_returns: Portfolio daily returns
        benchmark_returns: Benchmark daily returns
    
    Returns:
        Beta coefficient
    """
    # Align series
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2:
        return 1.0
    
    covariance = aligned.iloc[:, 0].cov(aligned.iloc[:, 1])
    benchmark_var = aligned.iloc[:, 1].var()
    
    if benchmark_var == 0:
        return 1.0
    
    beta = covariance / benchmark_var
    return float(beta)


def compute_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """Compute Value at Risk at given confidence level.
    
    Args:
        returns: Series of daily returns
        confidence: Confidence level (default 95%)
    
    Returns:
        VaR as positive number (loss magnitude)
    """
    var = np.percentile(returns, (1 - confidence) * 100)
    return float(abs(var))


def compute_max_drawdown(prices: pd.Series) -> float:
    """Compute maximum drawdown from peak.
    
    Args:
        prices: Price series
    
    Returns:
        Maximum drawdown as positive decimal (e.g., 0.15 for 15% drawdown)
    """
    cummax = prices.cummax()
    drawdown = (prices - cummax) / cummax
    max_dd = abs(drawdown.min())
    return float(max_dd)


def compute_tracking_error(portfolio_returns: pd.Series, benchmark_returns: pd.Series, 
                          annualize: bool = True) -> float:
    """Compute tracking error (volatility of excess returns).
    
    Args:
        portfolio_returns: Portfolio daily returns
        benchmark_returns: Benchmark daily returns
        annualize: If True, annualize the tracking error
    
    Returns:
        Tracking error
    """
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2:
        return 0.0
    
    excess = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    te = excess.std()
    
    if annualize:
        te *= np.sqrt(252)
    
    return float(te)


def compute_risk_metrics(df_portfolio: pd.DataFrame, 
                        df_benchmark: Optional[pd.DataFrame] = None,
                        price_col: str = 'close',
                        risk_free_rate: float = 0.02) -> Dict:
    """Compute comprehensive risk metrics for portfolio.
    
    Args:
        df_portfolio: DataFrame with portfolio price history (must have date index and price column)
        df_benchmark: Optional DataFrame with benchmark price history
        price_col: Name of price column (default 'close')
        risk_free_rate: Annual risk-free rate for Sharpe/Sortino
    
    Returns:
        Dictionary with all risk metrics
    """
    # Ensure date index
    if not isinstance(df_portfolio.index, pd.DatetimeIndex):
        if 'date' in df_portfolio.columns:
            df_portfolio = df_portfolio.set_index('date')
        else:
            raise ValueError("Portfolio DataFrame must have date index or 'date' column")
    
    # Extract price series
    if price_col not in df_portfolio.columns:
        raise ValueError(f"Column '{price_col}' not found in portfolio DataFrame")
    
    prices = df_portfolio[price_col]
    returns = compute_returns(prices)
    
    # Basic metrics
    metrics = {
        "total_return": float((prices.iloc[-1] / prices.iloc[0]) - 1) if len(prices) > 0 else 0.0,
        "annualized_return": float(((prices.iloc[-1] / prices.iloc[0]) ** (252 / len(prices)) - 1)) if len(prices) > 1 else 0.0,
        "volatility": compute_volatility(returns, annualize=True),
        "sharpe_ratio": compute_sharpe_ratio(returns, risk_free_rate),
        "sortino_ratio": compute_sortino_ratio(returns, risk_free_rate),
        "var_95": compute_var(returns, confidence=0.95),
        "max_drawdown": compute_max_drawdown(prices),
    }
    
    # Benchmark-relative metrics
    if df_benchmark is not None:
        if not isinstance(df_benchmark.index, pd.DatetimeIndex):
            if 'date' in df_benchmark.columns:
                df_benchmark = df_benchmark.set_index('date')
        
        if price_col in df_benchmark.columns:
            benchmark_prices = df_benchmark[price_col]
            benchmark_returns = compute_returns(benchmark_prices)
            
            metrics["beta"] = compute_beta(returns, benchmark_returns)
            metrics["tracking_error"] = compute_tracking_error(returns, benchmark_returns)
            
            # Information ratio (excess return / tracking error)
            excess_return = metrics["annualized_return"] - float(((benchmark_prices.iloc[-1] / benchmark_prices.iloc[0]) ** (252 / len(benchmark_prices)) - 1))
            metrics["information_ratio"] = excess_return / metrics["tracking_error"] if metrics["tracking_error"] > 0 else 0.0
        else:
            metrics["beta"] = 1.0
            metrics["tracking_error"] = 0.0
            metrics["information_ratio"] = 0.0
    else:
        metrics["beta"] = None
        metrics["tracking_error"] = None
        metrics["information_ratio"] = None
    
    return metrics


if __name__ == '__main__':
    # Quick test with synthetic data
    dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
    prices = pd.Series(100 * (1 + np.random.randn(len(dates)).cumsum() * 0.01), index=dates)
    df_test = pd.DataFrame({'close': prices})
    
    metrics = compute_risk_metrics(df_test)
    print("Sample risk metrics:")
    for k, v in metrics.items():
        print(f"  {k}: {v}")
