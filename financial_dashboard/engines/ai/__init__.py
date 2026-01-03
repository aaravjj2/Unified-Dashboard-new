"""
AI Engines Package - Phase 2: Local AI & Strategy Integration
=============================================================

Provides local AI capabilities without external API dependencies:
- LocalForecastEngine: Price & volatility forecasting using EMA, Linear Regression
- AIRecommender: Strategy recommendations based on hype + forecast signals

No external AI cloud services required - runs entirely on localhost.

Usage:
    from financial_dashboard.engines.ai import (
        get_forecast_engine,
        get_ai_recommender,
        ForecastResult,
        StrategyRecommendation
    )
    
    # Get price/vol forecast
    engine = get_forecast_engine()
    forecast = engine.generate_forecast('NVDA', history_df)
    
    # Get strategy recommendations
    recommender = get_ai_recommender()
    recs = recommender.generate_recommendations('NVDA', history_df)
"""

from .local_forecast import (
    LocalForecastEngine, 
    ForecastResult, 
    VolatilityForecast,
    TrendDirection,
    VolatilityRegime,
    get_forecast_engine
)

from .recommender import (
    AIRecommender, 
    StrategyRecommendation,
    StrategyLeg,
    StrategyType,
    RiskLevel,
    SignalStrength,
    get_ai_recommender
)

__all__ = [
    # Forecast Engine
    'LocalForecastEngine',
    'ForecastResult',
    'VolatilityForecast',
    'TrendDirection',
    'VolatilityRegime',
    'get_forecast_engine',
    # Recommender
    'AIRecommender',
    'StrategyRecommendation',
    'StrategyLeg',
    'StrategyType',
    'RiskLevel',
    'SignalStrength',
    'get_ai_recommender'
]

