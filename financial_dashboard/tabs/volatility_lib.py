"""
Volatility Computation Library

Pure functions for calculating various volatility metrics:
- Log returns
- Rolling volatility
- Realized volatility  
- Annualized volatility

All functions are designed to work with pandas Series/DataFrames and handle edge cases.
"""

import numpy as np
import pandas as pd
from typing import Union, Optional


def compute_log_returns(prices: pd.Series) -> pd.Series:
    """
    Compute log returns from price series.
    
    Args:
        prices: pandas Series of prices
        
    Returns:
        pandas Series of log returns (length = len(prices) - 1)
        
    Formula:
        r_t = ln(P_t / P_{t-1})
    """
    if len(prices) == 0:
        return pd.Series([], dtype=float)
    
    if len(prices) == 1:
        return pd.Series([], dtype=float, index=prices.index[:0])
    
    # Calculate log returns: ln(P_t / P_{t-1})
    returns = np.log(prices).diff().dropna()
    
    return returns


def rolling_volatility(
    returns: pd.Series,
    window: int,
    annualize: bool = False,
    periods_per_year: int = 252
) -> pd.Series:
    """
    Calculate rolling volatility of returns.
    
    Args:
        returns: pandas Series of returns
        window: rolling window size
        annualize: whether to annualize the volatility
        periods_per_year: number of periods per year (252 for daily, ~1638 for hourly)
        
    Returns:
        pandas Series of rolling volatility
        
    Notes:
        - First (window-1) values will be NaN
        - Uses sample std (ddof=1)
        - If annualize=True, multiplies by sqrt(periods_per_year)
    """
    if len(returns) == 0:
        return pd.Series([], dtype=float)
    
    # Calculate rolling standard deviation
    vol = returns.rolling(window=window, min_periods=window).std(ddof=1)
    
    if annualize:
        vol = vol * np.sqrt(periods_per_year)
    
    return vol


def realized_vol(
    returns: pd.Series,
    start: Optional[str] = None,
    end: Optional[str] = None,
    annualize: bool = False,
    periods_per_year: int = 252
) -> float:
    """
    Calculate realized volatility over a period.
    
    Args:
        returns: pandas Series of returns
        start: start date (ISO string) - optional
        end: end date (ISO string) - optional
        annualize: whether to annualize the volatility
        periods_per_year: number of periods per year
        
    Returns:
        float: realized volatility
        
    Notes:
        - If start/end not provided, uses full series
        - Returns NaN for empty or single-value series
    """
    if len(returns) == 0:
        return np.nan
    
    # Subset to date range if provided
    if start is not None or end is not None:
        returns = returns.loc[start:end]
    
    if len(returns) <= 1:
        return np.nan
    
    # Calculate standard deviation
    vol = returns.std(ddof=1)
    
    if annualize:
        vol = vol * np.sqrt(periods_per_year)
    
    return vol


def annualized_vol(
    vol: Union[float, pd.Series],
    periods_per_year: int = 252
) -> Union[float, pd.Series]:
    """
    Convert volatility to annualized volatility.
    
    Args:
        vol: volatility value or Series
        periods_per_year: number of periods per year
        
    Returns:
        Annualized volatility (same type as input)
        
    Formula:
        annual_vol = vol * sqrt(periods_per_year)
    """
    return vol * np.sqrt(periods_per_year)


def compute_volatility_metrics(
    prices: pd.Series,
    window: int = 20,
    annualize: bool = True,
    periods_per_year: int = 252
) -> pd.DataFrame:
    """
    Compute comprehensive volatility metrics from price series.
    
    Args:
        prices: pandas Series of prices with datetime index
        window: rolling window for rolling volatility
        annualize: whether to annualize volatilities
        periods_per_year: number of periods per year
        
    Returns:
        DataFrame with columns:
            - price: original prices
            - return: log returns
            - rolling_vol: rolling volatility
            - realized_vol: realized vol over full period (scalar broadcast)
    """
    # Compute returns
    returns = compute_log_returns(prices)
    
    # Compute rolling volatility
    roll_vol = rolling_volatility(
        returns,
        window=window,
        annualize=annualize,
        periods_per_year=periods_per_year
    )
    
    # Compute realized volatility (scalar)
    real_vol = realized_vol(
        returns,
        annualize=annualize,
        periods_per_year=periods_per_year
    )
    
    # Build DataFrame aligned to returns index
    df = pd.DataFrame({
        'price': prices.iloc[1:],  # Align with returns (skip first)
        'return': returns,
        'rolling_vol': roll_vol,
        'realized_vol': real_vol  # Broadcast scalar
    })
    
    return df
