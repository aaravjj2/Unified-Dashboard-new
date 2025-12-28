"""
AlphaSim Indicators - Technical indicator calculations.
"""
from typing import List, Optional, Union
import pandas as pd


def sma(series: Union[pd.Series, List[float]], period: int = 10) -> pd.Series:
    """
    Calculate Simple Moving Average.
    
    Args:
        series: Price series (pandas Series or list of floats)
        period: Number of periods for the moving average
    
    Returns:
        pandas Series with SMA values
    """
    if isinstance(series, list):
        series = pd.Series(series)
    
    if len(series) < period:
        return pd.Series(dtype=float)
    
    return series.rolling(window=period).mean()


def ema(series: Union[pd.Series, List[float]], period: int = 10) -> pd.Series:
    """
    Calculate Exponential Moving Average.
    
    Args:
        series: Price series
        period: Number of periods for the EMA
    
    Returns:
        pandas Series with EMA values
    """
    if isinstance(series, list):
        series = pd.Series(series)
    
    if len(series) < period:
        return pd.Series(dtype=float)
    
    return series.ewm(span=period, adjust=False).mean()


def rsi(series: Union[pd.Series, List[float]], period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index.
    
    Args:
        series: Price series
        period: RSI period (typically 14)
    
    Returns:
        pandas Series with RSI values (0-100)
    """
    if isinstance(series, list):
        series = pd.Series(series)
    
    if len(series) < period + 1:
        return pd.Series(dtype=float)
    
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi_values = 100 - (100 / (1 + rs))
    
    return rsi_values


def macd(
    series: Union[pd.Series, List[float]],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> dict:
    """
    Calculate MACD (Moving Average Convergence Divergence).
    
    Args:
        series: Price series
        fast_period: Fast EMA period (typically 12)
        slow_period: Slow EMA period (typically 26)
        signal_period: Signal line period (typically 9)
    
    Returns:
        dict with 'macd', 'signal', and 'histogram' Series
    """
    if isinstance(series, list):
        series = pd.Series(series)
    
    if len(series) < slow_period:
        return {
            "macd": pd.Series(dtype=float),
            "signal": pd.Series(dtype=float),
            "histogram": pd.Series(dtype=float)
        }
    
    fast_ema = series.ewm(span=fast_period, adjust=False).mean()
    slow_ema = series.ewm(span=slow_period, adjust=False).mean()
    
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return {
        "macd": macd_line,
        "signal": signal_line,
        "histogram": histogram
    }


def vwap(
    high: Union[pd.Series, List[float]],
    low: Union[pd.Series, List[float]],
    close: Union[pd.Series, List[float]],
    volume: Union[pd.Series, List[float]]
) -> pd.Series:
    """
    Calculate Volume Weighted Average Price.
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        volume: Volume
    
    Returns:
        pandas Series with VWAP values
    """
    if isinstance(high, list):
        high = pd.Series(high)
    if isinstance(low, list):
        low = pd.Series(low)
    if isinstance(close, list):
        close = pd.Series(close)
    if isinstance(volume, list):
        volume = pd.Series(volume)
    
    typical_price = (high + low + close) / 3
    vwap_values = (typical_price * volume).cumsum() / volume.cumsum()
    
    return vwap_values
