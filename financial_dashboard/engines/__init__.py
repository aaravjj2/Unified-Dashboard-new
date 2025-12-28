"""
FinGPT-Style AI Engine Stack
============================
Comprehensive AI/ML stack for financial forecasting and trading signals.

Architecture Layers:
1. Data Foundation - Market data, news, order book
2. LLM Intelligence - FinGPT-style sentiment analysis
3. Price Forecasting - Qlib-style deep learning models  
4. Options Forecasting - IV surface, Greeks, Deep Hedging
5. RL Trading Signals - FinRL-Meta style PPO/A2C/DDPG
6. Signal Fusion - Combine all signals with weighted ensemble
7. Risk Management - VaR, CVaR, position sizing

Exports the main engine classes and convenience functions.
"""

# Existing options engine
from .options_forecast_engine import (
    OptionsForecastEngine,
    generate_options_forecast
)

# FinGPT-style AI engines (lazy imports to avoid heavy deps at startup)
def get_signal_fusion_engine():
    """Lazy load Signal Fusion Engine"""
    from .signal_fusion_engine import SignalFusionEngine
    return SignalFusionEngine

def get_qlib_forecaster():
    """Lazy load Qlib-style Forecaster"""
    from .qlib_forecaster import QlibStyleForecaster
    return QlibStyleForecaster

def get_fingpt_sentiment():
    """Lazy load FinGPT Sentiment Engine"""
    from .fingpt_sentiment import FinGPTSentimentEngine
    return FinGPTSentimentEngine

def get_deep_hedging():
    """Lazy load Deep Hedging Engine"""
    from .deep_hedging import DeepHedgingEngine
    return DeepHedgingEngine

def get_finrl_signals():
    """Lazy load FinRL Trading Signals"""
    from .finrl_signals import FinRLTradingSignals
    return FinRLTradingSignals

def get_neural_prophet():
    """Lazy load NeuralProphet Forecaster"""
    from .neural_prophet_forecaster import NeuralProphetForecaster
    return NeuralProphetForecaster


__all__ = [
    # Existing
    'OptionsForecastEngine',
    'generate_options_forecast',
    # New FinGPT-style engines (lazy loaders)
    'get_signal_fusion_engine',
    'get_qlib_forecaster', 
    'get_fingpt_sentiment',
    'get_deep_hedging',
    'get_finrl_signals',
    'get_neural_prophet'
]
