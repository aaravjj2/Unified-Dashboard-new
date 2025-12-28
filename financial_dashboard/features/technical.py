"""
Technical Features - Feature Engineering for Technical Indicators
=================================================================
Phase 1 of ML Project Guide implementation.

Pure, unit-testable functions for computing technical features.
"""

import logging
from typing import Dict, List, Optional, Union
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


# ==============================================================================
# MOVING AVERAGES
# ==============================================================================

def compute_sma(series: pd.Series, window: int) -> pd.Series:
    """
    Compute Simple Moving Average.
    
    Args:
        series: Price series
        window: Moving average window
        
    Returns:
        SMA values
    """
    return series.rolling(window=window).mean()


def compute_ema(series: pd.Series, span: int) -> pd.Series:
    """
    Compute Exponential Moving Average.
    
    Args:
        series: Price series
        span: EMA span (alpha = 2/(span+1))
        
    Returns:
        EMA values
    """
    return series.ewm(span=span, adjust=False).mean()


def compute_wma(series: pd.Series, window: int) -> pd.Series:
    """
    Compute Weighted Moving Average.
    
    Args:
        series: Price series
        window: Window size
        
    Returns:
        WMA values
    """
    weights = pd.Series(range(1, window + 1))
    return series.rolling(window=window).apply(
        lambda x: np.dot(x, weights) / weights.sum(),
        raw=True
    )


def compute_dema(series: pd.Series, span: int) -> pd.Series:
    """Compute Double Exponential Moving Average."""
    ema1 = series.ewm(span=span, adjust=False).mean()
    ema2 = ema1.ewm(span=span, adjust=False).mean()
    return 2 * ema1 - ema2


# ==============================================================================
# MOMENTUM INDICATORS
# ==============================================================================

def compute_rsi(series: pd.Series, window: int = 14) -> pd.Series:
    """
    Compute Relative Strength Index.
    
    Args:
        series: Price series
        window: RSI period (default 14)
        
    Returns:
        RSI values (0-100)
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def compute_stoch(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3
) -> Dict[str, pd.Series]:
    """
    Compute Stochastic Oscillator.
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        k_period: %K period
        d_period: %D smoothing period
        
    Returns:
        Dict with '%K' and '%D' series
    """
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    
    pct_k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    pct_d = pct_k.rolling(window=d_period).mean()
    
    return {'%K': pct_k, '%D': pct_d}


def compute_macd(
    series: pd.Series,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9
) -> Dict[str, pd.Series]:
    """
    Compute MACD (Moving Average Convergence Divergence).
    
    Args:
        series: Price series
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line period
        
    Returns:
        Dict with 'macd', 'signal', and 'histogram'
    """
    fast_ema = series.ewm(span=fast_period, adjust=False).mean()
    slow_ema = series.ewm(span=slow_period, adjust=False).mean()
    
    macd_line = fast_ema - slow_ema
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
    histogram = macd_line - signal_line
    
    return {
        'macd': macd_line,
        'signal': signal_line,
        'histogram': histogram
    }


def compute_momentum(series: pd.Series, period: int = 10) -> pd.Series:
    """Compute Momentum."""
    return series - series.shift(period)


def compute_roc(series: pd.Series, period: int = 10) -> pd.Series:
    """Compute Rate of Change (%)."""
    return 100 * (series - series.shift(period)) / series.shift(period)


def compute_cci(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 20
) -> pd.Series:
    """
    Compute Commodity Channel Index.
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: CCI period
        
    Returns:
        CCI values
    """
    tp = (high + low + close) / 3
    tp_sma = tp.rolling(window=period).mean()
    tp_mad = tp.rolling(window=period).apply(
        lambda x: np.abs(x - x.mean()).mean(),
        raw=True
    )
    return (tp - tp_sma) / (0.015 * tp_mad)


def compute_williams_r(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """Compute Williams %R."""
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    return -100 * (highest_high - close) / (highest_high - lowest_low)


# ==============================================================================
# TREND INDICATORS
# ==============================================================================

def compute_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> Dict[str, pd.Series]:
    """
    Compute Average Directional Index.
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ADX period
        
    Returns:
        Dict with 'ADX', '+DI', and '-DI'
    """
    # True Range
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    # Directional Movement
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    plus_dm[(plus_dm < minus_dm)] = 0
    minus_dm[(minus_dm < plus_dm)] = 0
    
    # Smoothed values
    atr = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
    
    # ADX
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx = dx.ewm(span=period, adjust=False).mean()
    
    return {'ADX': adx, '+DI': plus_di, '-DI': minus_di}


def compute_aroon(
    high: pd.Series,
    low: pd.Series,
    period: int = 25
) -> Dict[str, pd.Series]:
    """
    Compute Aroon Indicator.
    
    Returns:
        Dict with 'aroon_up' and 'aroon_down'
    """
    aroon_up = 100 * high.rolling(window=period + 1).apply(
        lambda x: x.argmax(), raw=True
    ) / period
    aroon_down = 100 * low.rolling(window=period + 1).apply(
        lambda x: x.argmin(), raw=True
    ) / period
    
    return {'aroon_up': aroon_up, 'aroon_down': aroon_down}


# ==============================================================================
# VOLATILITY INDICATORS
# ==============================================================================

def compute_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Compute Average True Range.
    
    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: ATR period
        
    Returns:
        ATR values
    """
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    return tr.ewm(span=period, adjust=False).mean()


def compute_bbands(
    series: pd.Series,
    period: int = 20,
    num_std: float = 2.0
) -> Dict[str, pd.Series]:
    """
    Compute Bollinger Bands.
    
    Args:
        series: Price series
        period: Moving average period
        num_std: Number of standard deviations
        
    Returns:
        Dict with 'upper', 'middle', and 'lower' bands
    """
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    
    return {
        'upper': middle + (num_std * std),
        'middle': middle,
        'lower': middle - (num_std * std)
    }


def compute_keltner(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    ema_period: int = 20,
    atr_period: int = 10,
    multiplier: float = 2.0
) -> Dict[str, pd.Series]:
    """Compute Keltner Channels."""
    middle = close.ewm(span=ema_period, adjust=False).mean()
    atr = compute_atr(high, low, close, atr_period)
    
    return {
        'upper': middle + (multiplier * atr),
        'middle': middle,
        'lower': middle - (multiplier * atr)
    }


def compute_natr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """Compute Normalized ATR (as percentage)."""
    return 100 * compute_atr(high, low, close, period) / close


# ==============================================================================
# VOLUME INDICATORS
# ==============================================================================

def compute_obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """
    Compute On Balance Volume.
    
    Args:
        close: Close prices
        volume: Volume
        
    Returns:
        OBV values
    """
    direction = np.where(close > close.shift(1), 1,
                         np.where(close < close.shift(1), -1, 0))
    return (volume * direction).cumsum()


def compute_vwap(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series
) -> pd.Series:
    """Compute Volume Weighted Average Price."""
    tp = (high + low + close) / 3
    return (tp * volume).cumsum() / volume.cumsum()


def compute_mfi(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series,
    period: int = 14
) -> pd.Series:
    """Compute Money Flow Index."""
    tp = (high + low + close) / 3
    mf = tp * volume
    
    mf_pos = pd.Series(0.0, index=mf.index)
    mf_neg = pd.Series(0.0, index=mf.index)
    
    mf_pos[tp > tp.shift(1)] = mf[tp > tp.shift(1)]
    mf_neg[tp < tp.shift(1)] = mf[tp < tp.shift(1)]
    
    mf_ratio = mf_pos.rolling(window=period).sum() / mf_neg.rolling(window=period).sum()
    return 100 - (100 / (1 + mf_ratio))


def compute_ad_line(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    volume: pd.Series
) -> pd.Series:
    """Compute Accumulation/Distribution Line."""
    clv = ((close - low) - (high - close)) / (high - low)
    clv = clv.fillna(0)
    return (clv * volume).cumsum()


# ==============================================================================
# CROSS-SECTIONAL FEATURES
# ==============================================================================

def compute_zscore(series: pd.Series, window: int = 20) -> pd.Series:
    """Compute rolling Z-score."""
    mean = series.rolling(window=window).mean()
    std = series.rolling(window=window).std()
    return (series - mean) / std


def compute_percentile_rank(series: pd.Series, window: int = 20) -> pd.Series:
    """Compute rolling percentile rank."""
    return series.rolling(window=window).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1],
        raw=True
    )


def compute_relative_strength(
    series: pd.Series,
    benchmark: pd.Series,
    window: int = 20
) -> pd.Series:
    """Compute relative strength vs benchmark."""
    return (series / benchmark).pct_change(window)


# ==============================================================================
# FEATURE PIPELINE
# ==============================================================================

def compute_all_technical_features(
    df: pd.DataFrame,
    config: Optional[Dict] = None
) -> pd.DataFrame:
    """
    Compute all technical features for a DataFrame.
    
    Args:
        df: DataFrame with OHLCV columns (Open, High, Low, Close, Volume)
        config: Optional configuration dict for feature parameters
        
    Returns:
        DataFrame with all technical features
    """
    config = config or {}
    
    # Ensure required columns exist
    required = ['Open', 'High', 'Low', 'Close', 'Volume']
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    features = pd.DataFrame(index=df.index)
    
    # Price data
    close = df['Close']
    high = df['High']
    low = df['Low']
    volume = df['Volume']
    
    # Moving Averages
    for window in config.get('sma_windows', [5, 10, 20, 50, 200]):
        features[f'sma_{window}'] = compute_sma(close, window)
    
    for span in config.get('ema_spans', [5, 10, 20, 50]):
        features[f'ema_{span}'] = compute_ema(close, span)
    
    # Momentum
    for window in config.get('rsi_windows', [14]):
        features[f'rsi_{window}'] = compute_rsi(close, window)
    
    # MACD
    macd = compute_macd(close)
    features['macd'] = macd['macd']
    features['macd_signal'] = macd['signal']
    features['macd_hist'] = macd['histogram']
    
    # Stochastic
    stoch = compute_stoch(high, low, close)
    features['stoch_k'] = stoch['%K']
    features['stoch_d'] = stoch['%D']
    
    # Trend
    adx = compute_adx(high, low, close)
    features['adx'] = adx['ADX']
    features['plus_di'] = adx['+DI']
    features['minus_di'] = adx['-DI']
    
    aroon = compute_aroon(high, low)
    features['aroon_up'] = aroon['aroon_up']
    features['aroon_down'] = aroon['aroon_down']
    
    # Volatility
    for period in config.get('atr_periods', [14]):
        features[f'atr_{period}'] = compute_atr(high, low, close, period)
        features[f'natr_{period}'] = compute_natr(high, low, close, period)
    
    bbands = compute_bbands(close)
    features['bb_upper'] = bbands['upper']
    features['bb_middle'] = bbands['middle']
    features['bb_lower'] = bbands['lower']
    features['bb_width'] = (bbands['upper'] - bbands['lower']) / bbands['middle']
    
    # Volume
    features['obv'] = compute_obv(close, volume)
    features['vwap'] = compute_vwap(high, low, close, volume)
    features['mfi'] = compute_mfi(high, low, close, volume)
    features['ad_line'] = compute_ad_line(high, low, close, volume)
    
    # Returns
    for period in config.get('return_periods', [1, 5, 10, 20]):
        features[f'return_{period}d'] = close.pct_change(period)
        features[f'log_return_{period}d'] = np.log(close / close.shift(period))
    
    # Z-scores
    features['close_zscore'] = compute_zscore(close)
    features['volume_zscore'] = compute_zscore(volume)
    
    # Price relative to MAs
    for window in [20, 50, 200]:
        if f'sma_{window}' in features.columns:
            features[f'close_to_sma_{window}'] = close / features[f'sma_{window}']
    
    return features
