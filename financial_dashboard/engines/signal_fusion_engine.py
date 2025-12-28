#!/usr/bin/env python3
"""
Signal Fusion Engine
====================
Combines multiple signal sources into unified trading signals.

Inspired by FinGPT/FinRL architectures, this engine fuses:
- Price forecasts (Qlib-style models)
- Sentiment signals (FinBERT/FinGPT)
- Technical indicators
- Options flow signals
- RL-based signals

Uses weighted ensemble with dynamic confidence adjustment.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Types of trading signals"""
    PRICE_FORECAST = "price_forecast"
    SENTIMENT = "sentiment"
    TECHNICAL = "technical"
    OPTIONS_FLOW = "options_flow"
    RL_SIGNAL = "rl_signal"
    VOLATILITY = "volatility"


class SignalDirection(Enum):
    """Signal direction"""
    STRONG_BUY = 2
    BUY = 1
    NEUTRAL = 0
    SELL = -1
    STRONG_SELL = -2


@dataclass
class Signal:
    """Individual trading signal"""
    signal_type: SignalType
    ticker: str
    direction: SignalDirection
    confidence: float  # 0-1
    magnitude: float  # Expected move magnitude
    horizon_days: int
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'signal_type': self.signal_type.value,
            'ticker': self.ticker,
            'direction': self.direction.value,
            'direction_name': self.direction.name,
            'confidence': self.confidence,
            'magnitude': self.magnitude,
            'horizon_days': self.horizon_days,
            'timestamp': self.timestamp.isoformat(),
            'metadata': self.metadata
        }


@dataclass
class FusedSignal:
    """Combined signal from multiple sources"""
    ticker: str
    direction: SignalDirection
    confidence: float
    expected_return: float
    risk_adjusted_return: float
    horizon_days: int
    contributing_signals: List[Signal]
    signal_agreement: float  # 0-1, how much signals agree
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            'ticker': self.ticker,
            'direction': self.direction.value,
            'direction_name': self.direction.name,
            'confidence': self.confidence,
            'expected_return': self.expected_return,
            'risk_adjusted_return': self.risk_adjusted_return,
            'horizon_days': self.horizon_days,
            'signal_agreement': self.signal_agreement,
            'num_signals': len(self.contributing_signals),
            'signals': [s.to_dict() for s in self.contributing_signals],
            'timestamp': self.timestamp.isoformat()
        }


class SignalFusionEngine:
    """
    Combines multiple signal sources into unified trading signals.
    
    Uses weighted ensemble with dynamic weight adjustment based on:
    - Historical accuracy of each signal type
    - Market regime detection
    - Signal agreement/disagreement
    
    Architecture inspired by FinGPT signal layer.
    """
    
    # Default weights for each signal type
    DEFAULT_WEIGHTS = {
        SignalType.PRICE_FORECAST: 0.30,
        SignalType.SENTIMENT: 0.25,
        SignalType.TECHNICAL: 0.15,
        SignalType.OPTIONS_FLOW: 0.15,
        SignalType.RL_SIGNAL: 0.10,
        SignalType.VOLATILITY: 0.05
    }
    
    def __init__(self, 
                 weights: Dict[SignalType, float] = None,
                 min_confidence: float = 0.3,
                 min_signals: int = 2,
                 agreement_threshold: float = 0.6):
        """
        Args:
            weights: Signal type weights (must sum to 1)
            min_confidence: Minimum confidence to generate signal
            min_signals: Minimum number of signals required
            agreement_threshold: Minimum agreement ratio for high confidence
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.min_confidence = min_confidence
        self.min_signals = min_signals
        self.agreement_threshold = agreement_threshold
        
        # Historical performance tracking
        self._signal_history: Dict[SignalType, List[Dict]] = {
            st: [] for st in SignalType
        }
        self._accuracy_cache: Dict[SignalType, float] = {}
        
    def add_signal(self, signal: Signal) -> None:
        """Add a signal to the fusion engine"""
        if signal.signal_type not in self._signal_history:
            self._signal_history[signal.signal_type] = []
        self._signal_history[signal.signal_type].append(signal.to_dict())
        
    def fuse_signals(self, signals: List[Signal]) -> Optional[FusedSignal]:
        """
        Fuse multiple signals into a single trading decision.
        
        Algorithm:
        1. Group signals by direction
        2. Compute weighted confidence
        3. Calculate signal agreement
        4. Adjust for market regime
        5. Generate final signal
        
        Returns:
            FusedSignal if conditions met, None otherwise
        """
        if len(signals) < self.min_signals:
            logger.debug(f"Insufficient signals ({len(signals)} < {self.min_signals})")
            return None
            
        ticker = signals[0].ticker
        if not all(s.ticker == ticker for s in signals):
            logger.warning("Mixed tickers in signal fusion")
            
        # Compute weighted direction
        weighted_direction = 0.0
        total_weight = 0.0
        confidence_sum = 0.0
        
        for signal in signals:
            weight = self.weights.get(signal.signal_type, 0.1)
            weighted_direction += signal.direction.value * weight * signal.confidence
            total_weight += weight
            confidence_sum += signal.confidence * weight
            
        if total_weight == 0:
            return None
            
        # Normalize
        avg_direction = weighted_direction / total_weight
        avg_confidence = confidence_sum / total_weight
        
        # Calculate signal agreement
        directions = [s.direction.value for s in signals]
        agreement = self._calculate_agreement(directions)
        
        # Adjust confidence based on agreement
        adjusted_confidence = avg_confidence * (0.5 + 0.5 * agreement)
        
        if adjusted_confidence < self.min_confidence:
            logger.debug(f"Low confidence ({adjusted_confidence:.2f} < {self.min_confidence})")
            return None
            
        # Determine final direction
        final_direction = self._map_to_direction(avg_direction)
        
        # Calculate expected return
        expected_return = self._calculate_expected_return(signals)
        
        # Risk-adjusted return (simplified Sharpe-like ratio)
        volatility = self._estimate_volatility(signals)
        risk_adjusted = expected_return / max(volatility, 0.01)
        
        # Average horizon
        avg_horizon = int(np.mean([s.horizon_days for s in signals]))
        
        return FusedSignal(
            ticker=ticker,
            direction=final_direction,
            confidence=adjusted_confidence,
            expected_return=expected_return,
            risk_adjusted_return=risk_adjusted,
            horizon_days=avg_horizon,
            contributing_signals=signals,
            signal_agreement=agreement
        )
    
    def _calculate_agreement(self, directions: List[int]) -> float:
        """Calculate how much signals agree (0-1)"""
        if len(directions) <= 1:
            return 1.0
            
        # Count positive, negative, neutral
        pos = sum(1 for d in directions if d > 0)
        neg = sum(1 for d in directions if d < 0)
        total = len(directions)
        
        # Agreement is max of positive or negative ratio
        return max(pos, neg) / total
    
    def _map_to_direction(self, avg_direction: float) -> SignalDirection:
        """Map average direction to SignalDirection enum"""
        if avg_direction >= 1.5:
            return SignalDirection.STRONG_BUY
        elif avg_direction >= 0.5:
            return SignalDirection.BUY
        elif avg_direction <= -1.5:
            return SignalDirection.STRONG_SELL
        elif avg_direction <= -0.5:
            return SignalDirection.SELL
        else:
            return SignalDirection.NEUTRAL
    
    def _calculate_expected_return(self, signals: List[Signal]) -> float:
        """Calculate expected return from signals"""
        if not signals:
            return 0.0
            
        weighted_return = 0.0
        total_weight = 0.0
        
        for signal in signals:
            weight = self.weights.get(signal.signal_type, 0.1) * signal.confidence
            # Magnitude represents expected move
            expected = signal.magnitude * signal.direction.value / 2  # Normalize direction
            weighted_return += expected * weight
            total_weight += weight
            
        return weighted_return / max(total_weight, 0.01)
    
    def _estimate_volatility(self, signals: List[Signal]) -> float:
        """Estimate volatility from signal metadata"""
        vols = []
        for signal in signals:
            if 'volatility' in signal.metadata:
                vols.append(signal.metadata['volatility'])
            elif 'iv' in signal.metadata:
                vols.append(signal.metadata['iv'])
                
        if vols:
            return np.mean(vols)
        return 0.20  # Default 20% volatility
    
    def create_price_signal(self,
                           ticker: str,
                           forecast_pct: float,
                           confidence: float,
                           horizon: int = 30,
                           model_name: str = None) -> Signal:
        """Create signal from price forecast"""
        if forecast_pct >= 0.10:
            direction = SignalDirection.STRONG_BUY
        elif forecast_pct >= 0.03:
            direction = SignalDirection.BUY
        elif forecast_pct <= -0.10:
            direction = SignalDirection.STRONG_SELL
        elif forecast_pct <= -0.03:
            direction = SignalDirection.SELL
        else:
            direction = SignalDirection.NEUTRAL
            
        return Signal(
            signal_type=SignalType.PRICE_FORECAST,
            ticker=ticker,
            direction=direction,
            confidence=confidence,
            magnitude=abs(forecast_pct),
            horizon_days=horizon,
            metadata={'forecast_pct': forecast_pct, 'model': model_name}
        )
    
    def create_sentiment_signal(self,
                               ticker: str,
                               sentiment_score: float,  # -1 to 1
                               confidence: float,
                               num_articles: int = 0,
                               horizon: int = 7) -> Signal:
        """Create signal from sentiment analysis"""
        if sentiment_score >= 0.6:
            direction = SignalDirection.STRONG_BUY
        elif sentiment_score >= 0.2:
            direction = SignalDirection.BUY
        elif sentiment_score <= -0.6:
            direction = SignalDirection.STRONG_SELL
        elif sentiment_score <= -0.2:
            direction = SignalDirection.SELL
        else:
            direction = SignalDirection.NEUTRAL
            
        # Magnitude from sentiment intensity
        magnitude = abs(sentiment_score) * 0.05  # Scale to reasonable return
        
        return Signal(
            signal_type=SignalType.SENTIMENT,
            ticker=ticker,
            direction=direction,
            confidence=confidence,
            magnitude=magnitude,
            horizon_days=horizon,
            metadata={'sentiment_score': sentiment_score, 'num_articles': num_articles}
        )
    
    def create_options_flow_signal(self,
                                   ticker: str,
                                   put_call_ratio: float,
                                   unusual_activity: bool,
                                   iv_percentile: float,
                                   confidence: float,
                                   horizon: int = 14) -> Signal:
        """Create signal from options flow analysis"""
        # Low put/call = bullish, High = bearish
        if put_call_ratio < 0.5 and unusual_activity:
            direction = SignalDirection.STRONG_BUY
        elif put_call_ratio < 0.7:
            direction = SignalDirection.BUY
        elif put_call_ratio > 1.5 and unusual_activity:
            direction = SignalDirection.STRONG_SELL
        elif put_call_ratio > 1.0:
            direction = SignalDirection.SELL
        else:
            direction = SignalDirection.NEUTRAL
            
        # Magnitude from IV percentile (high IV = larger expected move)
        magnitude = 0.02 + iv_percentile * 0.08
        
        return Signal(
            signal_type=SignalType.OPTIONS_FLOW,
            ticker=ticker,
            direction=direction,
            confidence=confidence,
            magnitude=magnitude,
            horizon_days=horizon,
            metadata={
                'put_call_ratio': put_call_ratio,
                'unusual_activity': unusual_activity,
                'iv_percentile': iv_percentile
            }
        )
    
    def create_rl_signal(self,
                        ticker: str,
                        action: int,  # -2 to 2
                        q_value: float,
                        confidence: float,
                        horizon: int = 5,
                        algorithm: str = 'PPO') -> Signal:
        """Create signal from RL agent"""
        direction_map = {
            -2: SignalDirection.STRONG_SELL,
            -1: SignalDirection.SELL,
            0: SignalDirection.NEUTRAL,
            1: SignalDirection.BUY,
            2: SignalDirection.STRONG_BUY
        }
        
        return Signal(
            signal_type=SignalType.RL_SIGNAL,
            ticker=ticker,
            direction=direction_map.get(action, SignalDirection.NEUTRAL),
            confidence=confidence,
            magnitude=abs(q_value) * 0.03,  # Scale Q-value to return
            horizon_days=horizon,
            metadata={'action': action, 'q_value': q_value, 'algorithm': algorithm}
        )
    
    def generate_composite_signal(self,
                                  ticker: str,
                                  price_forecast: Dict = None,
                                  sentiment: Dict = None,
                                  options_flow: Dict = None,
                                  rl_signal: Dict = None) -> Optional[FusedSignal]:
        """
        Generate composite signal from all available data sources.
        
        This is the main entry point for the Signal Fusion Engine.
        
        Args:
            ticker: Stock symbol
            price_forecast: Dict with 'forecast_pct', 'confidence', 'horizon'
            sentiment: Dict with 'score', 'confidence', 'num_articles'
            options_flow: Dict with 'put_call_ratio', 'unusual_activity', 'iv_percentile'
            rl_signal: Dict with 'action', 'q_value', 'confidence'
            
        Returns:
            FusedSignal or None if insufficient data/confidence
        """
        signals = []
        
        if price_forecast:
            signals.append(self.create_price_signal(
                ticker=ticker,
                forecast_pct=price_forecast.get('forecast_pct', 0),
                confidence=price_forecast.get('confidence', 0.5),
                horizon=price_forecast.get('horizon', 30),
                model_name=price_forecast.get('model')
            ))
            
        if sentiment:
            signals.append(self.create_sentiment_signal(
                ticker=ticker,
                sentiment_score=sentiment.get('score', 0),
                confidence=sentiment.get('confidence', 0.5),
                num_articles=sentiment.get('num_articles', 0),
                horizon=sentiment.get('horizon', 7)
            ))
            
        if options_flow:
            signals.append(self.create_options_flow_signal(
                ticker=ticker,
                put_call_ratio=options_flow.get('put_call_ratio', 0.8),
                unusual_activity=options_flow.get('unusual_activity', False),
                iv_percentile=options_flow.get('iv_percentile', 0.5),
                confidence=options_flow.get('confidence', 0.5),
                horizon=options_flow.get('horizon', 14)
            ))
            
        if rl_signal:
            signals.append(self.create_rl_signal(
                ticker=ticker,
                action=rl_signal.get('action', 0),
                q_value=rl_signal.get('q_value', 0),
                confidence=rl_signal.get('confidence', 0.5),
                horizon=rl_signal.get('horizon', 5),
                algorithm=rl_signal.get('algorithm', 'PPO')
            ))
            
        if not signals:
            return None
            
        return self.fuse_signals(signals)
    
    def get_signal_summary(self, ticker: str) -> Dict:
        """Get summary of recent signals for a ticker"""
        # This would query historical signals in a production system
        return {
            'ticker': ticker,
            'signal_types_available': list(self.weights.keys()),
            'min_confidence': self.min_confidence,
            'min_signals': self.min_signals,
            'weights': {k.value: v for k, v in self.weights.items()}
        }
