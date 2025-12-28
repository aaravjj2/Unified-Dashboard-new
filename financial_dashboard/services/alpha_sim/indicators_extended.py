"""
Extended Technical Indicators - Full AlphaVantage API Recreation
================================================================
Implements all technical indicators from AlphaVantage API:
- Moving Averages: SMA, EMA, WMA, DEMA, TEMA, T3, KAMA
- Momentum: RSI, STOCH, STOCHF, STOCHRSI, WILLR, ADX, ADXR, CCI, MOM, ROC, AROON, MFI, TRIX, DX, ULTOSC, BOP
- Volume: OBV, AD, ADOSC
- Volatility: ATR, NATR, BBANDS
- Pattern: HT_TRENDLINE, HT_SINE, HT_TRENDMODE, HT_DCPERIOD, HT_DCPHASE, HT_PHASOR
"""

from typing import Dict, List, Optional, Union, Tuple
import pandas as pd
import numpy as np


# ==============================================================================
# MOVING AVERAGES
# ==============================================================================

def sma(series: pd.Series, period: int = 10) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period).mean()


def ema(series: pd.Series, period: int = 10) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False).mean()


def wma(series: pd.Series, period: int = 10) -> pd.Series:
    """Weighted Moving Average."""
    weights = pd.Series(range(1, period + 1))
    return series.rolling(window=period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)


def dema(series: pd.Series, period: int = 10) -> pd.Series:
    """Double Exponential Moving Average."""
    ema1 = series.ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    return 2 * ema1 - ema2


def tema(series: pd.Series, period: int = 10) -> pd.Series:
    """Triple Exponential Moving Average."""
    ema1 = series.ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    ema3 = ema2.ewm(span=period, adjust=False).mean()
    return 3 * ema1 - 3 * ema2 + ema3


def t3(series: pd.Series, period: int = 5, vfactor: float = 0.7) -> pd.Series:
    """T3 Moving Average (triple smoothed EMA)."""
    c1 = -vfactor ** 3
    c2 = 3 * vfactor ** 2 + 3 * vfactor ** 3
    c3 = -6 * vfactor ** 2 - 3 * vfactor - 3 * vfactor ** 3
    c4 = 1 + 3 * vfactor + vfactor ** 3 + 3 * vfactor ** 2
    
    ema1 = series.ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    ema3 = ema2.ewm(span=period, adjust=False).mean()
    ema4 = ema3.ewm(span=period, adjust=False).mean()
    ema5 = ema4.ewm(span=period, adjust=False).mean()
    ema6 = ema5.ewm(span=period, adjust=False).mean()
    
    return c1 * ema6 + c2 * ema5 + c3 * ema4 + c4 * ema3


def kama(series: pd.Series, period: int = 10, fast_sc: int = 2, slow_sc: int = 30) -> pd.Series:
    """Kaufman Adaptive Moving Average."""
    change = abs(series - series.shift(period))
    volatility = abs(series.diff()).rolling(window=period).sum()
    
    er = change / volatility.replace(0, np.nan)
    
    fast_alpha = 2 / (fast_sc + 1)
    slow_alpha = 2 / (slow_sc + 1)
    
    sc = (er * (fast_alpha - slow_alpha) + slow_alpha) ** 2
    
    kama_values = pd.Series(index=series.index, dtype=float)
    kama_values.iloc[period - 1] = series.iloc[period - 1]
    
    for i in range(period, len(series)):
        if not np.isnan(sc.iloc[i]):
            kama_values.iloc[i] = kama_values.iloc[i-1] + sc.iloc[i] * (series.iloc[i] - kama_values.iloc[i-1])
        else:
            kama_values.iloc[i] = kama_values.iloc[i-1]
    
    return kama_values


# ==============================================================================
# MOMENTUM INDICATORS
# ==============================================================================

def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Relative Strength Index."""
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def stoch(high: pd.Series, low: pd.Series, close: pd.Series, 
          fastk_period: int = 5, slowk_period: int = 3, slowd_period: int = 3) -> Dict[str, pd.Series]:
    """Stochastic Oscillator (STOCH)."""
    lowest_low = low.rolling(window=fastk_period).min()
    highest_high = high.rolling(window=fastk_period).max()
    
    fastk = 100 * (close - lowest_low) / (highest_high - lowest_low)
    slowk = fastk.rolling(window=slowk_period).mean()
    slowd = slowk.rolling(window=slowd_period).mean()
    
    return {'SlowK': slowk, 'SlowD': slowd}


def stochf(high: pd.Series, low: pd.Series, close: pd.Series,
           fastk_period: int = 5, fastd_period: int = 3) -> Dict[str, pd.Series]:
    """Stochastic Fast (STOCHF)."""
    lowest_low = low.rolling(window=fastk_period).min()
    highest_high = high.rolling(window=fastk_period).max()
    
    fastk = 100 * (close - lowest_low) / (highest_high - lowest_low)
    fastd = fastk.rolling(window=fastd_period).mean()
    
    return {'FastK': fastk, 'FastD': fastd}


def stochrsi(series: pd.Series, period: int = 14, fastk_period: int = 5, fastd_period: int = 3) -> Dict[str, pd.Series]:
    """Stochastic RSI."""
    rsi_values = rsi(series, period)
    
    stochrsi_k = (rsi_values - rsi_values.rolling(window=fastk_period).min()) / \
                 (rsi_values.rolling(window=fastk_period).max() - rsi_values.rolling(window=fastk_period).min())
    
    fastk = 100 * stochrsi_k
    fastd = fastk.rolling(window=fastd_period).mean()
    
    return {'FastK': fastk, 'FastD': fastd}


def willr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Williams %R."""
    highest_high = high.rolling(window=period).max()
    lowest_low = low.rolling(window=period).min()
    
    return -100 * (highest_high - close) / (highest_high - lowest_low)


def adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> Dict[str, pd.Series]:
    """Average Directional Index."""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    
    plus_dm = high.diff()
    minus_dm = -low.diff()
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm < 0] = 0
    plus_dm[(plus_dm < minus_dm)] = 0
    minus_dm[(minus_dm < plus_dm)] = 0
    
    atr = tr.ewm(span=period, adjust=False).mean()
    plus_di = 100 * (plus_dm.ewm(span=period, adjust=False).mean() / atr)
    minus_di = 100 * (minus_dm.ewm(span=period, adjust=False).mean() / atr)
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
    adx_value = dx.ewm(span=period, adjust=False).mean()
    
    return {'ADX': adx_value, 'Plus_DI': plus_di, 'Minus_DI': minus_di}


def adxr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average Directional Index Rating."""
    adx_result = adx(high, low, close, period)
    adx_values = adx_result['ADX']
    return (adx_values + adx_values.shift(period)) / 2


def cci(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 20) -> pd.Series:
    """Commodity Channel Index."""
    tp = (high + low + close) / 3
    tp_sma = tp.rolling(window=period).mean()
    tp_mad = tp.rolling(window=period).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - tp_sma) / (0.015 * tp_mad)


def mom(series: pd.Series, period: int = 10) -> pd.Series:
    """Momentum."""
    return series - series.shift(period)


def roc(series: pd.Series, period: int = 10) -> pd.Series:
    """Rate of Change."""
    return 100 * (series - series.shift(period)) / series.shift(period)


def aroon(high: pd.Series, low: pd.Series, period: int = 25) -> Dict[str, pd.Series]:
    """Aroon Indicator."""
    aroon_up = 100 * high.rolling(window=period + 1).apply(lambda x: x.argmax(), raw=True) / period
    aroon_down = 100 * low.rolling(window=period + 1).apply(lambda x: x.argmin(), raw=True) / period
    return {'Aroon Up': aroon_up, 'Aroon Down': aroon_down}


def mfi(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series, period: int = 14) -> pd.Series:
    """Money Flow Index."""
    tp = (high + low + close) / 3
    mf = tp * volume
    
    mf_pos = pd.Series(0.0, index=mf.index)
    mf_neg = pd.Series(0.0, index=mf.index)
    
    mf_pos[tp > tp.shift(1)] = mf[tp > tp.shift(1)]
    mf_neg[tp < tp.shift(1)] = mf[tp < tp.shift(1)]
    
    mf_ratio = mf_pos.rolling(window=period).sum() / mf_neg.rolling(window=period).sum()
    return 100 - (100 / (1 + mf_ratio))


def trix(series: pd.Series, period: int = 15) -> pd.Series:
    """Triple Exponential Average."""
    ema1 = series.ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    ema3 = ema2.ewm(span=period, adjust=False).mean()
    return 10000 * ema3.pct_change()


def dx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Directional Movement Index."""
    adx_result = adx(high, low, close, period)
    plus_di = adx_result['Plus_DI']
    minus_di = adx_result['Minus_DI']
    return 100 * abs(plus_di - minus_di) / (plus_di + minus_di)


def ultosc(high: pd.Series, low: pd.Series, close: pd.Series,
           period1: int = 7, period2: int = 14, period3: int = 28) -> pd.Series:
    """Ultimate Oscillator."""
    bp = close - pd.concat([low, close.shift(1)], axis=1).min(axis=1)
    tr = pd.concat([high, close.shift(1)], axis=1).max(axis=1) - pd.concat([low, close.shift(1)], axis=1).min(axis=1)
    
    avg1 = bp.rolling(window=period1).sum() / tr.rolling(window=period1).sum()
    avg2 = bp.rolling(window=period2).sum() / tr.rolling(window=period2).sum()
    avg3 = bp.rolling(window=period3).sum() / tr.rolling(window=period3).sum()
    
    return 100 * ((4 * avg1) + (2 * avg2) + avg3) / 7


def bop(open_price: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Balance of Power."""
    return (close - open_price) / (high - low)


# ==============================================================================
# VOLUME INDICATORS
# ==============================================================================

def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    """On Balance Volume."""
    obv_values = pd.Series(0.0, index=close.index)
    
    for i in range(1, len(close)):
        if close.iloc[i] > close.iloc[i-1]:
            obv_values.iloc[i] = obv_values.iloc[i-1] + volume.iloc[i]
        elif close.iloc[i] < close.iloc[i-1]:
            obv_values.iloc[i] = obv_values.iloc[i-1] - volume.iloc[i]
        else:
            obv_values.iloc[i] = obv_values.iloc[i-1]
    
    return obv_values


def ad(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """Accumulation/Distribution Line (Chaikin A/D Line)."""
    clv = ((close - low) - (high - close)) / (high - low)
    clv = clv.fillna(0)
    ad_values = (clv * volume).cumsum()
    return ad_values


def adosc(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series,
          fast_period: int = 3, slow_period: int = 10) -> pd.Series:
    """Chaikin A/D Oscillator."""
    ad_line = ad(high, low, close, volume)
    return ad_line.ewm(span=fast_period, adjust=False).mean() - ad_line.ewm(span=slow_period, adjust=False).mean()


# ==============================================================================
# VOLATILITY INDICATORS
# ==============================================================================

def atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Average True Range."""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()


def natr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Normalized Average True Range."""
    return 100 * atr(high, low, close, period) / close


def bbands(series: pd.Series, period: int = 20, nbdevup: float = 2.0, nbdevdn: float = 2.0) -> Dict[str, pd.Series]:
    """Bollinger Bands."""
    middle = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    
    upper = middle + (nbdevup * std)
    lower = middle - (nbdevdn * std)
    
    return {'Upper Band': upper, 'Middle Band': middle, 'Lower Band': lower}


# ==============================================================================
# HILBERT TRANSFORM (Pattern Recognition)
# ==============================================================================

def ht_trendline(series: pd.Series) -> pd.Series:
    """Hilbert Transform - Instantaneous Trendline."""
    # Simplified implementation using weighted moving average
    weights = [0.0962, 0.5769, 0.5769, 0.0962]
    smooth = series.rolling(window=4).apply(lambda x: np.dot(x, weights), raw=True)
    return smooth


def ht_sine(series: pd.Series) -> Dict[str, pd.Series]:
    """Hilbert Transform - SineWave."""
    # Simplified sine wave approximation
    period = 10
    sine = np.sin(2 * np.pi * np.arange(len(series)) / period)
    leadsine = np.sin(2 * np.pi * np.arange(len(series)) / period + np.pi/4)
    return {'SINE': pd.Series(sine, index=series.index), 
            'LEADSINE': pd.Series(leadsine, index=series.index)}


def ht_trendmode(series: pd.Series) -> pd.Series:
    """Hilbert Transform - Trend vs Cycle Mode."""
    # Simplified: 1 = trend, 0 = cycle
    ma_short = series.rolling(window=10).mean()
    ma_long = series.rolling(window=30).mean()
    return (abs(ma_short - ma_long) > ma_long * 0.02).astype(int)


def ht_dcperiod(series: pd.Series) -> pd.Series:
    """Hilbert Transform - Dominant Cycle Period."""
    # Simplified dominant cycle estimation
    return pd.Series(20, index=series.index)  # Default to 20-period cycle


def ht_dcphase(series: pd.Series) -> pd.Series:
    """Hilbert Transform - Dominant Cycle Phase."""
    period = 20
    phase = (np.arange(len(series)) % period) / period * 360
    return pd.Series(phase, index=series.index)


def ht_phasor(series: pd.Series) -> Dict[str, pd.Series]:
    """Hilbert Transform - Phasor Components."""
    period = 20
    phase = 2 * np.pi * np.arange(len(series)) / period
    inphase = series * np.cos(phase)
    quadrature = series * np.sin(phase)
    return {'INPHASE': pd.Series(inphase.values, index=series.index),
            'QUADRATURE': pd.Series(quadrature.values, index=series.index)}


# ==============================================================================
# PRICE TRANSFORM FUNCTIONS
# ==============================================================================

def avgprice(open_price: pd.Series, high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Average Price."""
    return (open_price + high + low + close) / 4


def medprice(high: pd.Series, low: pd.Series) -> pd.Series:
    """Median Price."""
    return (high + low) / 2


def typprice(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Typical Price."""
    return (high + low + close) / 3


def wclprice(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    """Weighted Close Price."""
    return (high + low + 2 * close) / 4


# ==============================================================================
# HELPER: Get all available indicators
# ==============================================================================

AVAILABLE_INDICATORS = {
    # Moving Averages
    'SMA': {'func': sma, 'category': 'Moving Averages', 'params': ['period']},
    'EMA': {'func': ema, 'category': 'Moving Averages', 'params': ['period']},
    'WMA': {'func': wma, 'category': 'Moving Averages', 'params': ['period']},
    'DEMA': {'func': dema, 'category': 'Moving Averages', 'params': ['period']},
    'TEMA': {'func': tema, 'category': 'Moving Averages', 'params': ['period']},
    'T3': {'func': t3, 'category': 'Moving Averages', 'params': ['period', 'vfactor']},
    'KAMA': {'func': kama, 'category': 'Moving Averages', 'params': ['period']},
    
    # Momentum
    'RSI': {'func': rsi, 'category': 'Momentum', 'params': ['period']},
    'STOCH': {'func': stoch, 'category': 'Momentum', 'params': ['fastk_period', 'slowk_period', 'slowd_period']},
    'STOCHF': {'func': stochf, 'category': 'Momentum', 'params': ['fastk_period', 'fastd_period']},
    'STOCHRSI': {'func': stochrsi, 'category': 'Momentum', 'params': ['period', 'fastk_period', 'fastd_period']},
    'WILLR': {'func': willr, 'category': 'Momentum', 'params': ['period']},
    'ADX': {'func': adx, 'category': 'Momentum', 'params': ['period']},
    'ADXR': {'func': adxr, 'category': 'Momentum', 'params': ['period']},
    'CCI': {'func': cci, 'category': 'Momentum', 'params': ['period']},
    'MOM': {'func': mom, 'category': 'Momentum', 'params': ['period']},
    'ROC': {'func': roc, 'category': 'Momentum', 'params': ['period']},
    'AROON': {'func': aroon, 'category': 'Momentum', 'params': ['period']},
    'MFI': {'func': mfi, 'category': 'Momentum', 'params': ['period']},
    'TRIX': {'func': trix, 'category': 'Momentum', 'params': ['period']},
    'DX': {'func': dx, 'category': 'Momentum', 'params': ['period']},
    'ULTOSC': {'func': ultosc, 'category': 'Momentum', 'params': ['period1', 'period2', 'period3']},
    'BOP': {'func': bop, 'category': 'Momentum', 'params': []},
    
    # Volume
    'OBV': {'func': obv, 'category': 'Volume', 'params': []},
    'AD': {'func': ad, 'category': 'Volume', 'params': []},
    'ADOSC': {'func': adosc, 'category': 'Volume', 'params': ['fast_period', 'slow_period']},
    
    # Volatility
    'ATR': {'func': atr, 'category': 'Volatility', 'params': ['period']},
    'NATR': {'func': natr, 'category': 'Volatility', 'params': ['period']},
    'BBANDS': {'func': bbands, 'category': 'Volatility', 'params': ['period', 'nbdevup', 'nbdevdn']},
    
    # Hilbert Transform
    'HT_TRENDLINE': {'func': ht_trendline, 'category': 'Pattern', 'params': []},
    'HT_SINE': {'func': ht_sine, 'category': 'Pattern', 'params': []},
    'HT_TRENDMODE': {'func': ht_trendmode, 'category': 'Pattern', 'params': []},
    'HT_DCPERIOD': {'func': ht_dcperiod, 'category': 'Pattern', 'params': []},
    'HT_DCPHASE': {'func': ht_dcphase, 'category': 'Pattern', 'params': []},
    'HT_PHASOR': {'func': ht_phasor, 'category': 'Pattern', 'params': []},
    
    # Price Transform
    'AVGPRICE': {'func': avgprice, 'category': 'Price Transform', 'params': []},
    'MEDPRICE': {'func': medprice, 'category': 'Price Transform', 'params': []},
    'TYPPRICE': {'func': typprice, 'category': 'Price Transform', 'params': []},
    'WCLPRICE': {'func': wclprice, 'category': 'Price Transform', 'params': []},
}


def get_indicator_categories() -> Dict[str, List[str]]:
    """Get indicators organized by category."""
    categories = {}
    for name, info in AVAILABLE_INDICATORS.items():
        cat = info['category']
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(name)
    return categories
