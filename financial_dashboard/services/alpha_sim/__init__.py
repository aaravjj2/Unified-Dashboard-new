# AlphaSim - Internal Alpha Vantage-compatible API service
"""
AlphaSim provides an internal API that mimics Alpha Vantage endpoints.
It uses internal data sources (PriceClient, yfinance) and FinBERT for sentiment.

Components:
- AlphaSimEngine: Core time series and indicator calculations
- AlphaSimConsole: Full AlphaVantage-compatible API interface
- indicators: Basic indicators (SMA, EMA, RSI, MACD, VWAP)
- indicators_extended: Full AlphaVantage indicator suite (40+ indicators)
"""

__version__ = "0.2.0"

# Core engine
try:
    from .engine import AlphaSimEngine
except ImportError:
    AlphaSimEngine = None

# AlphaVantage-compatible console
try:
    from .console import AlphaSimConsole, API_FUNCTIONS
except ImportError:
    AlphaSimConsole = None
    API_FUNCTIONS = {}

# Basic indicators
try:
    from .indicators import sma, ema, rsi, macd, vwap
except ImportError:
    pass

# Extended indicators
try:
    from .indicators_extended import (
        wma, dema, tema, t3, kama, trima, mama,
        stoch, stochf, stochrsi, willr, adx, adxr, apo, ppo, mom, bop, cci,
        cmo, roc, rocr, aroon, aroonosc, mfi, trix, ultosc, dx,
        minus_di, plus_di, minus_dm, plus_dm,
        obv, ad, adosc,
        atr, natr, trange, bbands,
        ht_trendline, ht_sine, ht_trendmode, ht_dcperiod, ht_dcphase, ht_phasor,
        typprice, wclprice, medprice
    )
except ImportError:
    pass

__all__ = [
    'AlphaSimEngine',
    'AlphaSimConsole',
    'API_FUNCTIONS',
    'sma', 'ema', 'rsi', 'macd', 'vwap',
]
