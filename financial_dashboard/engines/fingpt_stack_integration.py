#!/usr/bin/env python3
"""
FinGPT Stack Integration
========================
Integration layer connecting all FinGPT-style AI engines to the dashboard.

This module provides:
- Unified API for all AI engines
- Combined forecast generation
- Signal aggregation
- Real-time prediction pipeline
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class UnifiedForecast:
    """Combined forecast from all engines"""
    ticker: str
    timestamp: datetime
    
    # Price forecast
    price_current: float
    price_forecast: np.ndarray
    price_lower: np.ndarray
    price_upper: np.ndarray
    forecast_dates: List[datetime]
    
    # Sentiment
    sentiment_score: float
    sentiment_label: str
    sentiment_confidence: float
    
    # Trading signal
    signal_action: str
    signal_confidence: float
    signal_reasoning: str
    
    # Options/Hedging (optional)
    delta_hedge: Optional[float] = None
    gamma: Optional[float] = None
    implied_vol: Optional[float] = None
    
    # Component scores
    component_scores: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    models_used: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'timestamp': self.timestamp.isoformat(),
            'price': {
                'current': self.price_current,
                'forecast': self.price_forecast.tolist() if isinstance(self.price_forecast, np.ndarray) else self.price_forecast,
                'lower': self.price_lower.tolist() if isinstance(self.price_lower, np.ndarray) else self.price_lower,
                'upper': self.price_upper.tolist() if isinstance(self.price_upper, np.ndarray) else self.price_upper,
                'dates': [d.isoformat() if isinstance(d, datetime) else str(d) for d in self.forecast_dates]
            },
            'sentiment': {
                'score': self.sentiment_score,
                'label': self.sentiment_label,
                'confidence': self.sentiment_confidence
            },
            'signal': {
                'action': self.signal_action,
                'confidence': self.signal_confidence,
                'reasoning': self.signal_reasoning
            },
            'options': {
                'delta_hedge': self.delta_hedge,
                'gamma': self.gamma,
                'implied_vol': self.implied_vol
            },
            'component_scores': self.component_scores,
            'models_used': self.models_used,
            'data_sources': self.data_sources
        }


class FinGPTStackIntegration:
    """
    Unified FinGPT-style AI stack integration.
    
    Coordinates:
    - QlibStyleForecaster - Price prediction
    - FinGPTSentimentEngine - Sentiment analysis
    - FinRLTradingSignals - RL-based signals
    - DeepHedgingEngine - Options hedging
    - NeuralProphetForecaster - Time series decomposition
    - SignalFusionEngine - Signal combination
    """
    
    def __init__(self,
                 enable_price_forecast: bool = True,
                 enable_sentiment: bool = True,
                 enable_rl_signals: bool = True,
                 enable_hedging: bool = True,
                 enable_neural_prophet: bool = True):
        """
        Args:
            enable_*: Toggle individual components
        """
        self.enable_price_forecast = enable_price_forecast
        self.enable_sentiment = enable_sentiment
        self.enable_rl_signals = enable_rl_signals
        self.enable_hedging = enable_hedging
        self.enable_neural_prophet = enable_neural_prophet
        
        self._engines = {}
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize all enabled engines"""
        if self._initialized:
            return True
            
        logger.info("Initializing FinGPT Stack Integration...")
        
        # Lazy import engines
        from financial_dashboard.engines import (
            get_signal_fusion_engine,
            get_qlib_forecaster,
            get_fingpt_sentiment,
            get_deep_hedging,
            get_finrl_signals,
            get_neural_prophet
        )
        
        try:
            # Signal Fusion (always enabled - combines all signals)
            SFE = get_signal_fusion_engine()
            self._engines['fusion'] = SFE()
            logger.info("✅ SignalFusionEngine loaded")
            
            if self.enable_price_forecast:
                QSF = get_qlib_forecaster()
                self._engines['qlib'] = QSF()
                self._engines['qlib'].initialize()
                logger.info("✅ QlibStyleForecaster loaded")
            
            if self.enable_sentiment:
                FGS = get_fingpt_sentiment()
                self._engines['sentiment'] = FGS()
                self._engines['sentiment'].initialize()
                logger.info("✅ FinGPTSentimentEngine loaded")
            
            if self.enable_rl_signals:
                FRL = get_finrl_signals()
                self._engines['finrl'] = FRL()
                self._engines['finrl'].initialize()
                logger.info("✅ FinRLTradingSignals loaded")
            
            if self.enable_hedging:
                DHE = get_deep_hedging()
                self._engines['hedging'] = DHE()
                self._engines['hedging'].initialize()
                logger.info("✅ DeepHedgingEngine loaded")
            
            if self.enable_neural_prophet:
                NP = get_neural_prophet()
                self._engines['neural_prophet'] = NP()
                self._engines['neural_prophet'].initialize()
                logger.info("✅ NeuralProphetForecaster loaded")
            
            self._initialized = True
            logger.info("🚀 FinGPT Stack fully initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize FinGPT Stack: {e}")
            return False
    
    def generate_unified_forecast(self,
                                  ticker: str,
                                  price_history: pd.DataFrame,
                                  news_headlines: List[str] = None,
                                  option_data: Dict = None,
                                  horizon: int = 5) -> UnifiedForecast:
        """
        Generate comprehensive forecast using all engines.
        
        Args:
            ticker: Stock symbol
            price_history: OHLCV DataFrame
            news_headlines: Recent news for sentiment
            option_data: Optional options chain data
            horizon: Forecast horizon in days
            
        Returns:
            UnifiedForecast combining all predictions
        """
        if not self._initialized:
            self.initialize()
        
        models_used = []
        data_sources = []
        component_scores = {}
        
        # Normalize column names
        price_history = self._normalize_columns(price_history)
        current_price = float(price_history['close'].iloc[-1])
        
        # 1. Price Forecast (Qlib-style)
        price_forecast = np.full(horizon, current_price)
        price_lower = price_forecast * 0.95
        price_upper = price_forecast * 1.05
        
        if 'qlib' in self._engines and self.enable_price_forecast:
            try:
                qlib = self._engines['qlib']
                result = qlib.forecast(
                    price_history,
                    horizon=horizon,
                    ticker=ticker
                )
                price_forecast = result.forecast_values
                price_lower = result.confidence_lower
                price_upper = result.confidence_upper
                component_scores['qlib_ic'] = result.ic_score if result.ic_score else 0
                models_used.append('Qlib-ALSTM')
                data_sources.append('price_history')
            except Exception as e:
                logger.warning(f"Qlib forecast failed: {e}")
        
        # 2. NeuralProphet Enhancement
        if 'neural_prophet' in self._engines and self.enable_neural_prophet:
            try:
                np_model = self._engines['neural_prophet']
                
                # Prepare data for NeuralProphet
                np_df = price_history.copy()
                np_df['ds'] = pd.to_datetime(price_history.index)
                np_df['y'] = np_df['close']
                
                np_model.fit(np_df[['ds', 'y']])
                np_result = np_model.predict(periods=horizon)
                
                # Blend with Qlib forecast
                price_forecast = 0.6 * price_forecast + 0.4 * np_result.yhat
                price_lower = np.minimum(price_lower, np_result.yhat_lower)
                price_upper = np.maximum(price_upper, np_result.yhat_upper)
                
                models_used.append('NeuralProphet')
            except Exception as e:
                logger.warning(f"NeuralProphet failed: {e}")
        
        # 3. Sentiment Analysis
        sentiment_score = 0.0
        sentiment_label = 'neutral'
        sentiment_confidence = 0.5
        
        if 'sentiment' in self._engines and self.enable_sentiment:
            try:
                sentiment_engine = self._engines['sentiment']
                headlines = news_headlines or [f"{ticker} stock market news"]
                
                agg_sentiment = sentiment_engine.aggregate_sentiment(
                    ticker,
                    news_texts=headlines
                )
                sentiment_score = agg_sentiment.overall_score
                sentiment_label = agg_sentiment.overall_label.name if hasattr(agg_sentiment.overall_label, 'name') else str(agg_sentiment.overall_label)
                sentiment_confidence = agg_sentiment.confidence
                
                component_scores['sentiment'] = sentiment_score
                models_used.append('FinGPT-Sentiment')
                data_sources.append('news_headlines')
            except Exception as e:
                logger.warning(f"Sentiment analysis failed: {e}")
        
        # 4. RL Trading Signal
        signal_action = 'HOLD'
        signal_confidence = 0.5
        signal_reasoning = 'Default signal'
        
        if 'finrl' in self._engines and self.enable_rl_signals:
            try:
                finrl = self._engines['finrl']
                rl_signal = finrl.generate_signal(
                    ticker=ticker,
                    price_history=price_history
                )
                
                signal_action = rl_signal.action.name
                signal_confidence = rl_signal.confidence
                signal_reasoning = f"RL ensemble ({rl_signal.algorithm}) with Q-value {rl_signal.q_value:.3f}"
                
                component_scores['rl_signal'] = rl_signal.action.value / 2  # Normalize to [-1, 1]
                models_used.append('FinRL-Ensemble')
            except Exception as e:
                logger.warning(f"RL signal failed: {e}")
        
        # 5. Options/Hedging
        delta_hedge = None
        gamma = None
        implied_vol = None
        
        if 'hedging' in self._engines and self.enable_hedging and option_data:
            try:
                hedging = self._engines['hedging']
                
                # Create option contract from data
                from financial_dashboard.engines.deep_hedging import OptionContract
                
                contract = OptionContract(
                    strike=option_data.get('strike', current_price),
                    expiry=datetime.now() + timedelta(days=option_data.get('dte', 30)),
                    option_type=option_data.get('type', 'call'),
                    underlying_price=current_price
                )
                
                greeks = hedging.bs_greeks(contract, risk_free_rate=0.05, volatility=0.3)
                
                delta_hedge = greeks.delta
                gamma = greeks.gamma
                implied_vol = option_data.get('iv', 0.3)
                
                component_scores['delta'] = greeks.delta
                models_used.append('DeepHedging')
            except Exception as e:
                logger.warning(f"Hedging failed: {e}")
        
        # 6. Signal Fusion - Combine all components
        if 'fusion' in self._engines:
            try:
                fusion = self._engines['fusion']
                
                # Create signals for fusion
                signals = []
                
                # Price momentum signal
                momentum = (current_price - price_history['close'].iloc[-5]) / price_history['close'].iloc[-5]
                price_signal = fusion.create_price_signal(ticker, momentum, current_price)
                signals.append(price_signal)
                
                # Sentiment signal
                if sentiment_score != 0:
                    sent_signal = fusion.create_sentiment_signal(
                        ticker, 
                        sentiment_score, 
                        sentiment_confidence
                    )
                    signals.append(sent_signal)
                
                # Fuse all signals
                if signals:
                    fused = fusion.fuse_signals(signals)
                    
                    if fused and fused.direction:
                        # Override signal with fused result
                        signal_action = fused.direction.name
                        signal_confidence = fused.confidence
                        signal_reasoning = f"Fused from {len(signals)} signals (agreement: {fused.signal_agreement:.0%}, expected return: {fused.expected_return:.2%})"
                        
                        component_scores['fused_agreement'] = fused.signal_agreement
                        component_scores['expected_return'] = fused.expected_return
                    
            except Exception as e:
                logger.warning(f"Signal fusion failed: {e}")
        
        # Generate forecast dates
        last_date = pd.to_datetime(price_history.index[-1])
        forecast_dates = [last_date + timedelta(days=i+1) for i in range(horizon)]
        
        return UnifiedForecast(
            ticker=ticker,
            timestamp=datetime.now(),
            price_current=current_price,
            price_forecast=np.array(price_forecast),
            price_lower=np.array(price_lower),
            price_upper=np.array(price_upper),
            forecast_dates=forecast_dates,
            sentiment_score=sentiment_score,
            sentiment_label=sentiment_label,
            sentiment_confidence=sentiment_confidence,
            signal_action=signal_action,
            signal_confidence=signal_confidence,
            signal_reasoning=signal_reasoning,
            delta_hedge=delta_hedge,
            gamma=gamma,
            implied_vol=implied_vol,
            component_scores=component_scores,
            models_used=models_used,
            data_sources=data_sources
        )
    
    def _normalize_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize column names to lowercase"""
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]
        return df
    
    def get_engine_status(self) -> Dict[str, bool]:
        """Get status of all engines"""
        return {
            'initialized': self._initialized,
            'qlib': 'qlib' in self._engines,
            'sentiment': 'sentiment' in self._engines,
            'finrl': 'finrl' in self._engines,
            'hedging': 'hedging' in self._engines,
            'neural_prophet': 'neural_prophet' in self._engines,
            'fusion': 'fusion' in self._engines
        }
    
    def quick_sentiment(self, text: str) -> Dict:
        """Quick sentiment analysis for a single text"""
        if not self._initialized:
            self.initialize()
            
        if 'sentiment' not in self._engines:
            return {'score': 0, 'label': 'neutral', 'confidence': 0}
            
        try:
            result = self._engines['sentiment'].analyze_text(text)
            return {
                'score': result.score,
                'label': result.label.name if hasattr(result.label, 'name') else str(result.label),
                'confidence': result.confidence
            }
        except Exception as e:
            logger.warning(f"Quick sentiment failed: {e}")
            return {'score': 0, 'label': 'neutral', 'confidence': 0}
    
    def quick_forecast(self, 
                       ticker: str,
                       price_history: pd.DataFrame,
                       horizon: int = 5) -> Dict:
        """Quick price forecast without full analysis"""
        if not self._initialized:
            self.initialize()
        
        price_history = self._normalize_columns(price_history)
        current_price = float(price_history['close'].iloc[-1])
        
        if 'qlib' in self._engines:
            try:
                result = self._engines['qlib'].forecast(price_history, horizon=horizon, ticker=ticker)
                # Determine direction
                direction = 'bullish' if result.forecast_values[-1] > current_price else 'bearish'
                if abs(result.forecast_values[-1] - current_price) / current_price < 0.01:
                    direction = 'neutral'
                    
                return {
                    'current': current_price,
                    'forecast': result.forecast_values.tolist(),
                    'lower': result.confidence_lower.tolist(),
                    'upper': result.confidence_upper.tolist(),
                    'direction': direction
                }
            except Exception as e:
                logger.warning(f"Quick forecast failed: {e}")
        
        # Simple fallback
        volatility = price_history['close'].pct_change().std()
        forecast = [current_price * (1 + volatility * i * 0.1) for i in range(horizon)]
        
        return {
            'current': current_price,
            'forecast': forecast,
            'lower': [p * 0.95 for p in forecast],
            'upper': [p * 1.05 for p in forecast],
            'direction': 'neutral'
        }


# Singleton instance
_stack_instance = None

def get_fingpt_stack() -> FinGPTStackIntegration:
    """Get or create FinGPT stack singleton"""
    global _stack_instance
    if _stack_instance is None:
        _stack_instance = FinGPTStackIntegration()
    return _stack_instance
