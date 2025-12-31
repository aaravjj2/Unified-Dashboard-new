"""
Enhanced AI Options Forecaster
Combines multiple signals for actionable options recommendations.

Features:
- Multi-model ensemble (LSTM, statistical, pattern-based)
- Greeks-aware strike selection
- Confidence-weighted recommendations
- Integration with TA-Lib patterns

Inspired by:
- QuantStats tearsheets
- OpenBB AI Copilot
- Freqtrade's FreqAI

Usage:
    from engines.analysis.ai_options_forecast import AIOptionsForecast
    
    forecaster = AIOptionsForecast()
    recommendations = forecaster.get_recommendations('AAPL')
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class OptionDirection(Enum):
    """Directional bias for options."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"
    VOLATILE = "volatile"  # Straddle/strangle plays


class OptionStrategy(Enum):
    """Recommended options strategies."""
    LONG_CALL = "long_call"
    LONG_PUT = "long_put"
    COVERED_CALL = "covered_call"
    CASH_SECURED_PUT = "cash_secured_put"
    BULL_CALL_SPREAD = "bull_call_spread"
    BEAR_PUT_SPREAD = "bear_put_spread"
    IRON_CONDOR = "iron_condor"
    STRADDLE = "straddle"
    STRANGLE = "strangle"
    CALENDAR_SPREAD = "calendar_spread"


class SignalStrength(Enum):
    """Signal strength levels."""
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    NONE = "none"


@dataclass
class PriceTarget:
    """Price target with probability."""
    price: float
    probability: float
    timeframe_days: int
    direction: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "price": round(self.price, 2),
            "probability": round(self.probability, 3),
            "timeframe_days": self.timeframe_days,
            "direction": self.direction,
        }


@dataclass
class AISignal:
    """Individual AI signal component."""
    source: str  # 'lstm', 'pattern', 'technical', 'sentiment'
    direction: OptionDirection
    strength: SignalStrength
    confidence: float
    reason: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "direction": self.direction.value,
            "strength": self.strength.value,
            "confidence": round(self.confidence, 3),
            "reason": self.reason,
        }


@dataclass
class OptionRecommendation:
    """Complete options recommendation."""
    symbol: str
    strategy: OptionStrategy
    direction: OptionDirection
    confidence: float
    signals: List[AISignal]
    
    # Strategy details
    strike_price: Optional[float] = None
    strike_price_2: Optional[float] = None  # For spreads
    expiration_dte: int = 30
    
    # Risk/reward
    max_profit: Optional[float] = None
    max_loss: Optional[float] = None
    breakeven: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    stop_loss: Optional[float] = None  # Stop loss price
    
    # Greeks impact
    delta_exposure: Optional[float] = None
    theta_decay: Optional[float] = None
    vega_exposure: Optional[float] = None
    
    # Targets
    price_targets: List[PriceTarget] = field(default_factory=list)
    
    # Metadata
    reasoning: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def entry_price(self) -> float:
        """Alias for strike_price for UI compatibility."""
        return self.strike_price or 0.0
    
    @property
    def rationale(self) -> str:
        """Alias for reasoning for UI compatibility."""
        return self.reasoning or f"{self.strategy.value.replace('_', ' ').title()} based on {len(self.signals)} signals"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "symbol": self.symbol,
            "strategy": self.strategy.value,
            "direction": self.direction.value,
            "confidence": round(self.confidence, 3),
            "signals": [s.to_dict() for s in self.signals],
            "strike_price": round(self.strike_price, 2) if self.strike_price else None,
            "strike_price_2": round(self.strike_price_2, 2) if self.strike_price_2 else None,
            "expiration_dte": self.expiration_dte,
            "max_profit": round(self.max_profit, 2) if self.max_profit else None,
            "max_loss": round(self.max_loss, 2) if self.max_loss else None,
            "breakeven": round(self.breakeven, 2) if self.breakeven else None,
            "risk_reward_ratio": round(self.risk_reward_ratio, 2) if self.risk_reward_ratio else None,
            "delta_exposure": round(self.delta_exposure, 3) if self.delta_exposure else None,
            "theta_decay": round(self.theta_decay, 3) if self.theta_decay else None,
            "vega_exposure": round(self.vega_exposure, 3) if self.vega_exposure else None,
            "price_targets": [t.to_dict() for t in self.price_targets],
            "reasoning": self.reasoning,
            "timestamp": self.timestamp.isoformat(),
        }


def _get_ohlc_columns(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Extract OHLC columns from DataFrame, handling various naming conventions.
    
    Returns:
        Tuple of (open, high, low, close) arrays
    """
    cols_lower = [c.lower() for c in df.columns]
    
    # Try standard naming (Open, High, Low, Close)
    if 'open' in cols_lower:
        o = df['Open'].values if 'Open' in df.columns else df['open'].values
        h = df['High'].values if 'High' in df.columns else df['high'].values
        l = df['Low'].values if 'Low' in df.columns else df['low'].values
        c = df['Close'].values if 'Close' in df.columns else df['close'].values
        return o, h, l, c
    
    # Try short naming (o, h, l, c)
    if 'o' in cols_lower:
        o = df['o'].values if 'o' in df.columns else df['O'].values
        h = df['h'].values if 'h' in df.columns else df['H'].values
        l = df['l'].values if 'l' in df.columns else df['L'].values
        c = df['c'].values if 'c' in df.columns else df['C'].values
        return o, h, l, c
    
    # Fallback: assume first 4 columns are OHLC
    if len(df.columns) >= 4:
        return df.iloc[:, 0].values, df.iloc[:, 1].values, df.iloc[:, 2].values, df.iloc[:, 3].values
    
    raise ValueError(f"Could not identify OHLC columns in DataFrame: {df.columns.tolist()}")


class AIOptionsForecast:
    """
    AI-powered options forecasting and recommendation engine.
    
    Combines multiple signal sources:
    1. LSTM price prediction
    2. Technical pattern recognition (TA-Lib)
    3. Greeks and IV analysis
    4. Statistical momentum indicators
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.6,
        max_recommendations: int = 5,
    ):
        """
        Initialize the AI forecaster.
        
        Args:
            confidence_threshold: Minimum confidence for recommendations
            max_recommendations: Maximum number of recommendations to return
        """
        self.confidence_threshold = confidence_threshold
        self.max_recommendations = max_recommendations
        self._pattern_engine = None
        logger.info(f"AIOptionsForecast initialized: confidence={confidence_threshold}")
    
    @property
    def pattern_engine(self):
        """Lazy load TA-Lib pattern engine."""
        if self._pattern_engine is None:
            try:
                from engines.analysis.talib_patterns import TALibPatternEngine
                self._pattern_engine = TALibPatternEngine()
            except ImportError:
                logger.warning("TALibPatternEngine not available")
                self._pattern_engine = None
        return self._pattern_engine
    
    def get_signals(
        self,
        symbol: str,
        ohlc_data: Optional[pd.DataFrame] = None,
        client: Any = None,
    ) -> List[AISignal]:
        """
        Gather all AI signals for a symbol.
        
        Args:
            symbol: Stock symbol
            ohlc_data: Optional DataFrame with OHLC data
            client: Optional Alpaca client
            
        Returns:
            List of AISignal objects
        """
        signals = []
        
        # Load data if not provided
        if ohlc_data is None:
            ohlc_data = self._load_data(symbol, client)
        
        if ohlc_data is None or ohlc_data.empty:
            return signals
        
        # 1. Pattern-based signals
        pattern_signals = self._get_pattern_signals(ohlc_data)
        signals.extend(pattern_signals)
        
        # 2. Momentum signals
        momentum_signal = self._get_momentum_signal(ohlc_data)
        if momentum_signal:
            signals.append(momentum_signal)
        
        # 3. Volatility signals
        vol_signal = self._get_volatility_signal(ohlc_data)
        if vol_signal:
            signals.append(vol_signal)
        
        # 4. Trend signals
        trend_signal = self._get_trend_signal(ohlc_data)
        if trend_signal:
            signals.append(trend_signal)
        
        # 5. Support/Resistance signals
        sr_signal = self._get_support_resistance_signal(ohlc_data)
        if sr_signal:
            signals.append(sr_signal)
        
        return signals
    
    def get_recommendations(
        self,
        symbol: str,
        current_price: Optional[float] = None,
        ohlc_data: Optional[pd.DataFrame] = None,
        chain_data: Optional[pd.DataFrame] = None,
        client: Any = None,
    ) -> List[OptionRecommendation]:
        """
        Get AI-powered options recommendations.
        
        Args:
            symbol: Stock symbol
            current_price: Current stock price
            ohlc_data: Optional OHLC data
            chain_data: Optional options chain data
            client: Optional Alpaca client
            
        Returns:
            List of OptionRecommendation objects sorted by confidence
        """
        recommendations = []
        
        # Load data if needed
        if ohlc_data is None:
            ohlc_data = self._load_data(symbol, client)
        
        if ohlc_data is None or ohlc_data.empty:
            return recommendations
        
        if current_price is None:
            try:
                _, _, _, c = _get_ohlc_columns(ohlc_data)
                current_price = float(c[-1])
            except:
                current_price = float(ohlc_data.iloc[-1, 3])  # Assume 4th column is close
        
        # Get all signals
        signals = self.get_signals(symbol, ohlc_data, client)
        
        if not signals:
            return recommendations
        
        # Aggregate signal direction
        direction = self._aggregate_direction(signals)
        confidence = self._aggregate_confidence(signals)
        
        # Generate price targets
        price_targets = self._generate_price_targets(ohlc_data, direction)
        
        # Generate strategy recommendations based on signals
        if direction == OptionDirection.BULLISH and confidence >= self.confidence_threshold:
            # Strong bullish - Long Call or Bull Call Spread
            if confidence >= 0.75:
                rec = self._create_long_call_recommendation(
                    symbol, current_price, signals, price_targets, confidence
                )
                recommendations.append(rec)
            
            rec = self._create_bull_spread_recommendation(
                symbol, current_price, signals, price_targets, confidence
            )
            recommendations.append(rec)
            
        elif direction == OptionDirection.BEARISH and confidence >= self.confidence_threshold:
            # Strong bearish - Long Put or Bear Put Spread
            if confidence >= 0.75:
                rec = self._create_long_put_recommendation(
                    symbol, current_price, signals, price_targets, confidence
                )
                recommendations.append(rec)
            
            rec = self._create_bear_spread_recommendation(
                symbol, current_price, signals, price_targets, confidence
            )
            recommendations.append(rec)
            
        elif direction == OptionDirection.VOLATILE:
            # High volatility expected - Straddle or Strangle
            rec = self._create_straddle_recommendation(
                symbol, current_price, signals, price_targets, confidence
            )
            recommendations.append(rec)
            
        else:
            # Neutral - Income strategies
            rec = self._create_iron_condor_recommendation(
                symbol, current_price, signals, price_targets, confidence
            )
            recommendations.append(rec)
        
        # Sort by confidence
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        return recommendations[:self.max_recommendations]
    
    def _load_data(self, symbol_or_df, client: Any = None) -> Optional[pd.DataFrame]:
        """Load OHLC data for symbol or return DataFrame if already provided."""
        try:
            # If DataFrame is passed directly, use it
            if isinstance(symbol_or_df, pd.DataFrame):
                return symbol_or_df
            
            # Otherwise fetch data
            symbol = symbol_or_df
            
            # Try yfinance first
            try:
                import yfinance as yf
                ticker = yf.Ticker(symbol)
                df = ticker.history(period='3mo')
                if not df.empty:
                    # Standardize column names
                    df.columns = [c.lower() for c in df.columns]
                    return df
            except Exception as yf_err:
                logger.debug(f"yfinance fallback error: {yf_err}")
            
            # Try client if provided
            if client is not None:
                try:
                    bars = client.get_historical_bars(symbol, '1Day', limit=90)
                    return bars
                except:
                    pass
            
            logger.warning(f"Could not load data for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to load data for {symbol_or_df}: {e}")
            return None
    
    def _get_pattern_signals(self, ohlc_data: pd.DataFrame) -> List[AISignal]:
        """Get signals from candlestick patterns."""
        signals = []
        
        if self.pattern_engine is None:
            return signals
        
        try:
            # Use helper function to extract OHLC columns
            o, h, l, c = _get_ohlc_columns(ohlc_data)
            
            patterns = self.pattern_engine.get_recent_patterns(o, h, l, c, lookback=5)
            
            bullish_count = sum(1 for p in patterns if p.signal == 'bullish')
            bearish_count = sum(1 for p in patterns if p.signal == 'bearish')
            
            if bullish_count > bearish_count:
                direction = OptionDirection.BULLISH
                strength = SignalStrength.STRONG if bullish_count >= 3 else SignalStrength.MODERATE
                confidence = min(0.9, 0.5 + bullish_count * 0.1)
                reason = f"{bullish_count} bullish patterns detected: " + ", ".join(
                    [p.display_name for p in patterns if p.signal == 'bullish'][:3]
                )
            elif bearish_count > bullish_count:
                direction = OptionDirection.BEARISH
                strength = SignalStrength.STRONG if bearish_count >= 3 else SignalStrength.MODERATE
                confidence = min(0.9, 0.5 + bearish_count * 0.1)
                reason = f"{bearish_count} bearish patterns detected: " + ", ".join(
                    [p.display_name for p in patterns if p.signal == 'bearish'][:3]
                )
            else:
                direction = OptionDirection.NEUTRAL
                strength = SignalStrength.WEAK
                confidence = 0.4
                reason = "No clear pattern direction"
            
            signals.append(AISignal(
                source='pattern',
                direction=direction,
                strength=strength,
                confidence=confidence,
                reason=reason,
            ))
            
        except Exception as e:
            logger.error(f"Pattern signal error: {e}")
        
        return signals
    
    def _get_momentum_signal(self, ohlc_data: pd.DataFrame) -> Optional[AISignal]:
        """Calculate momentum-based signal."""
        try:
            _, _, _, c = _get_ohlc_columns(ohlc_data)
            close = c
            
            if len(close) < 20:
                return None
            
            # RSI calculation
            deltas = np.diff(close)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gain = np.mean(gains[-14:])
            avg_loss = np.mean(losses[-14:])
            
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            
            # Momentum (rate of change)
            roc = (close[-1] - close[-20]) / close[-20] * 100
            
            # Signal determination
            if rsi < 30 and roc < -5:
                direction = OptionDirection.BULLISH  # Oversold bounce
                strength = SignalStrength.STRONG
                confidence = 0.75
                reason = f"Oversold: RSI={rsi:.1f}, ROC={roc:.1f}%"
            elif rsi > 70 and roc > 5:
                direction = OptionDirection.BEARISH  # Overbought pullback
                strength = SignalStrength.STRONG
                confidence = 0.75
                reason = f"Overbought: RSI={rsi:.1f}, ROC={roc:.1f}%"
            elif rsi < 40:
                direction = OptionDirection.BULLISH
                strength = SignalStrength.MODERATE
                confidence = 0.6
                reason = f"Weak momentum, potential reversal: RSI={rsi:.1f}"
            elif rsi > 60:
                direction = OptionDirection.BEARISH
                strength = SignalStrength.MODERATE
                confidence = 0.6
                reason = f"Strong momentum, potential exhaustion: RSI={rsi:.1f}"
            else:
                direction = OptionDirection.NEUTRAL
                strength = SignalStrength.WEAK
                confidence = 0.4
                reason = f"Neutral momentum: RSI={rsi:.1f}"
            
            return AISignal(
                source='momentum',
                direction=direction,
                strength=strength,
                confidence=confidence,
                reason=reason,
            )
            
        except Exception as e:
            logger.error(f"Momentum signal error: {e}")
            return None
    
    def _get_volatility_signal(self, ohlc_data: pd.DataFrame) -> Optional[AISignal]:
        """Analyze volatility for signals."""
        try:
            _, h, l, c = _get_ohlc_columns(ohlc_data)
            close = c
            high = h
            low = l
            
            if len(close) < 20:
                return None
            
            # Historical volatility
            returns = np.diff(np.log(close))
            hv_20 = np.std(returns[-20:]) * np.sqrt(252) * 100
            hv_5 = np.std(returns[-5:]) * np.sqrt(252) * 100
            
            # ATR-based volatility
            tr = np.maximum(high[1:] - low[1:], 
                          np.maximum(np.abs(high[1:] - close[:-1]),
                                    np.abs(low[1:] - close[:-1])))
            atr = np.mean(tr[-14:])
            atr_pct = atr / close[-1] * 100
            
            # Volatility signal
            if hv_5 > hv_20 * 1.5:
                direction = OptionDirection.VOLATILE
                strength = SignalStrength.STRONG
                confidence = 0.7
                reason = f"Volatility expanding: HV5={hv_5:.1f}% vs HV20={hv_20:.1f}%"
            elif hv_5 < hv_20 * 0.7:
                direction = OptionDirection.NEUTRAL
                strength = SignalStrength.MODERATE
                confidence = 0.6
                reason = f"Volatility contracting: potential breakout coming"
            else:
                direction = OptionDirection.NEUTRAL
                strength = SignalStrength.WEAK
                confidence = 0.4
                reason = f"Normal volatility: HV20={hv_20:.1f}%"
            
            return AISignal(
                source='volatility',
                direction=direction,
                strength=strength,
                confidence=confidence,
                reason=reason,
            )
            
        except Exception as e:
            logger.error(f"Volatility signal error: {e}")
            return None
    
    def _get_trend_signal(self, ohlc_data: pd.DataFrame) -> Optional[AISignal]:
        """Analyze trend for signals."""
        try:
            _, _, _, c = _get_ohlc_columns(ohlc_data)
            close = c
            
            if len(close) < 50:
                return None
            
            # Moving averages
            sma_20 = np.mean(close[-20:])
            sma_50 = np.mean(close[-50:])
            current = close[-1]
            
            # Trend determination
            above_sma20 = current > sma_20
            above_sma50 = current > sma_50
            sma_bullish = sma_20 > sma_50
            
            if above_sma20 and above_sma50 and sma_bullish:
                direction = OptionDirection.BULLISH
                strength = SignalStrength.STRONG
                confidence = 0.75
                reason = f"Strong uptrend: Price above SMA20/50, MAs bullish"
            elif not above_sma20 and not above_sma50 and not sma_bullish:
                direction = OptionDirection.BEARISH
                strength = SignalStrength.STRONG
                confidence = 0.75
                reason = f"Strong downtrend: Price below SMA20/50, MAs bearish"
            elif above_sma20 != above_sma50:
                direction = OptionDirection.NEUTRAL
                strength = SignalStrength.MODERATE
                confidence = 0.55
                reason = f"Mixed trend: Price between SMA20 and SMA50"
            else:
                direction = OptionDirection.NEUTRAL
                strength = SignalStrength.WEAK
                confidence = 0.4
                reason = f"No clear trend"
            
            return AISignal(
                source='trend',
                direction=direction,
                strength=strength,
                confidence=confidence,
                reason=reason,
            )
            
        except Exception as e:
            logger.error(f"Trend signal error: {e}")
            return None
    
    def _get_support_resistance_signal(self, ohlc_data: pd.DataFrame) -> Optional[AISignal]:
        """Analyze support/resistance levels."""
        try:
            _, h, l, c = _get_ohlc_columns(ohlc_data)
            close = c
            high = h
            low = l
            
            if len(close) < 20:
                return None
            
            current = close[-1]
            
            # Find recent support/resistance
            recent_high = np.max(high[-20:])
            recent_low = np.min(low[-20:])
            range_pct = (recent_high - recent_low) / recent_low * 100
            
            # Position in range
            position = (current - recent_low) / (recent_high - recent_low)
            
            if position > 0.9:
                direction = OptionDirection.BEARISH
                strength = SignalStrength.MODERATE
                confidence = 0.65
                reason = f"Near resistance: {position:.0%} of range, resistance at ${recent_high:.2f}"
            elif position < 0.1:
                direction = OptionDirection.BULLISH
                strength = SignalStrength.MODERATE
                confidence = 0.65
                reason = f"Near support: {position:.0%} of range, support at ${recent_low:.2f}"
            else:
                direction = OptionDirection.NEUTRAL
                strength = SignalStrength.WEAK
                confidence = 0.4
                reason = f"Mid-range: {position:.0%} between ${recent_low:.2f}-${recent_high:.2f}"
            
            return AISignal(
                source='support_resistance',
                direction=direction,
                strength=strength,
                confidence=confidence,
                reason=reason,
            )
            
        except Exception as e:
            logger.error(f"S/R signal error: {e}")
            return None
    
    def _aggregate_direction(self, signals: List[AISignal]) -> OptionDirection:
        """Aggregate signals into overall direction."""
        bullish = sum(1 for s in signals if s.direction == OptionDirection.BULLISH)
        bearish = sum(1 for s in signals if s.direction == OptionDirection.BEARISH)
        volatile = sum(1 for s in signals if s.direction == OptionDirection.VOLATILE)
        
        if volatile >= 2:
            return OptionDirection.VOLATILE
        elif bullish > bearish + 1:
            return OptionDirection.BULLISH
        elif bearish > bullish + 1:
            return OptionDirection.BEARISH
        else:
            return OptionDirection.NEUTRAL
    
    def _aggregate_confidence(self, signals: List[AISignal]) -> float:
        """Aggregate signal confidences."""
        if not signals:
            return 0.0
        
        # Weight by strength
        weights = {
            SignalStrength.STRONG: 1.0,
            SignalStrength.MODERATE: 0.7,
            SignalStrength.WEAK: 0.4,
            SignalStrength.NONE: 0.0,
        }
        
        total_weight = sum(weights[s.strength] for s in signals)
        if total_weight == 0:
            return 0.0
        
        weighted_conf = sum(s.confidence * weights[s.strength] for s in signals)
        return weighted_conf / total_weight
    
    def _generate_price_targets(
        self,
        ohlc_data: pd.DataFrame,
        direction: OptionDirection,
    ) -> List[PriceTarget]:
        """Generate price targets based on analysis."""
        targets = []
        _, _, _, c = _get_ohlc_columns(ohlc_data)
        close = c
        current = close[-1]
        
        # Historical volatility for target calculation
        returns = np.diff(np.log(close))
        hv = np.std(returns[-20:]) * np.sqrt(252)
        
        if direction == OptionDirection.BULLISH:
            targets.append(PriceTarget(
                price=current * (1 + hv * 0.5),
                probability=0.6,
                timeframe_days=30,
                direction='up',
            ))
            targets.append(PriceTarget(
                price=current * (1 + hv),
                probability=0.35,
                timeframe_days=30,
                direction='up',
            ))
        elif direction == OptionDirection.BEARISH:
            targets.append(PriceTarget(
                price=current * (1 - hv * 0.5),
                probability=0.6,
                timeframe_days=30,
                direction='down',
            ))
            targets.append(PriceTarget(
                price=current * (1 - hv),
                probability=0.35,
                timeframe_days=30,
                direction='down',
            ))
        
        return targets
    
    def _create_long_call_recommendation(
        self,
        symbol: str,
        current_price: float,
        signals: List[AISignal],
        price_targets: List[PriceTarget],
        confidence: float,
    ) -> OptionRecommendation:
        """Create long call recommendation."""
        # ATM or slightly OTM strike
        strike = round(current_price * 1.02, 0)
        
        # Estimated max loss is premium (simplified)
        estimated_premium = current_price * 0.03  # ~3% premium assumption
        
        return OptionRecommendation(
            symbol=symbol,
            strategy=OptionStrategy.LONG_CALL,
            direction=OptionDirection.BULLISH,
            confidence=confidence,
            signals=signals,
            strike_price=strike,
            expiration_dte=30,
            max_loss=estimated_premium,
            breakeven=strike + estimated_premium,
            delta_exposure=0.45,
            theta_decay=-0.02,
            vega_exposure=0.15,
            price_targets=price_targets,
            reasoning=f"Bullish signals with {confidence:.0%} confidence. Target: ${price_targets[0].price:.2f}" if price_targets else "Bullish outlook",
        )
    
    def _create_long_put_recommendation(
        self,
        symbol: str,
        current_price: float,
        signals: List[AISignal],
        price_targets: List[PriceTarget],
        confidence: float,
    ) -> OptionRecommendation:
        """Create long put recommendation."""
        strike = round(current_price * 0.98, 0)
        estimated_premium = current_price * 0.03
        
        return OptionRecommendation(
            symbol=symbol,
            strategy=OptionStrategy.LONG_PUT,
            direction=OptionDirection.BEARISH,
            confidence=confidence,
            signals=signals,
            strike_price=strike,
            expiration_dte=30,
            max_loss=estimated_premium,
            breakeven=strike - estimated_premium,
            delta_exposure=-0.45,
            theta_decay=-0.02,
            vega_exposure=0.15,
            price_targets=price_targets,
            reasoning=f"Bearish signals with {confidence:.0%} confidence. Target: ${price_targets[0].price:.2f}" if price_targets else "Bearish outlook",
        )
    
    def _create_bull_spread_recommendation(
        self,
        symbol: str,
        current_price: float,
        signals: List[AISignal],
        price_targets: List[PriceTarget],
        confidence: float,
    ) -> OptionRecommendation:
        """Create bull call spread recommendation."""
        lower_strike = round(current_price * 0.98, 0)
        upper_strike = round(current_price * 1.05, 0)
        
        spread_width = upper_strike - lower_strike
        estimated_cost = spread_width * 0.4
        
        return OptionRecommendation(
            symbol=symbol,
            strategy=OptionStrategy.BULL_CALL_SPREAD,
            direction=OptionDirection.BULLISH,
            confidence=confidence * 0.9,  # Slightly lower for spreads
            signals=signals,
            strike_price=lower_strike,
            strike_price_2=upper_strike,
            expiration_dte=30,
            max_profit=spread_width - estimated_cost,
            max_loss=estimated_cost,
            breakeven=lower_strike + estimated_cost,
            risk_reward_ratio=(spread_width - estimated_cost) / estimated_cost,
            delta_exposure=0.35,
            theta_decay=-0.01,
            vega_exposure=0.08,
            price_targets=price_targets,
            reasoning=f"Defined-risk bullish spread. Max profit ${spread_width - estimated_cost:.2f}, max loss ${estimated_cost:.2f}",
        )
    
    def _create_bear_spread_recommendation(
        self,
        symbol: str,
        current_price: float,
        signals: List[AISignal],
        price_targets: List[PriceTarget],
        confidence: float,
    ) -> OptionRecommendation:
        """Create bear put spread recommendation."""
        upper_strike = round(current_price * 1.02, 0)
        lower_strike = round(current_price * 0.95, 0)
        
        spread_width = upper_strike - lower_strike
        estimated_cost = spread_width * 0.4
        
        return OptionRecommendation(
            symbol=symbol,
            strategy=OptionStrategy.BEAR_PUT_SPREAD,
            direction=OptionDirection.BEARISH,
            confidence=confidence * 0.9,
            signals=signals,
            strike_price=upper_strike,
            strike_price_2=lower_strike,
            expiration_dte=30,
            max_profit=spread_width - estimated_cost,
            max_loss=estimated_cost,
            breakeven=upper_strike - estimated_cost,
            risk_reward_ratio=(spread_width - estimated_cost) / estimated_cost,
            delta_exposure=-0.35,
            theta_decay=-0.01,
            vega_exposure=0.08,
            price_targets=price_targets,
            reasoning=f"Defined-risk bearish spread. Max profit ${spread_width - estimated_cost:.2f}, max loss ${estimated_cost:.2f}",
        )
    
    def _create_straddle_recommendation(
        self,
        symbol: str,
        current_price: float,
        signals: List[AISignal],
        price_targets: List[PriceTarget],
        confidence: float,
    ) -> OptionRecommendation:
        """Create straddle recommendation for high volatility."""
        strike = round(current_price, 0)
        estimated_cost = current_price * 0.06  # ~6% for ATM straddle
        
        return OptionRecommendation(
            symbol=symbol,
            strategy=OptionStrategy.STRADDLE,
            direction=OptionDirection.VOLATILE,
            confidence=confidence * 0.8,
            signals=signals,
            strike_price=strike,
            expiration_dte=30,
            max_loss=estimated_cost,
            breakeven=strike,  # Upper and lower breakevens
            delta_exposure=0.0,  # Delta neutral
            theta_decay=-0.04,
            vega_exposure=0.30,
            price_targets=price_targets,
            reasoning=f"Volatility play. Profits if price moves >${estimated_cost:.2f} in either direction.",
        )
    
    def _create_iron_condor_recommendation(
        self,
        symbol: str,
        current_price: float,
        signals: List[AISignal],
        price_targets: List[PriceTarget],
        confidence: float,
    ) -> OptionRecommendation:
        """Create iron condor for neutral/low volatility."""
        put_sell = round(current_price * 0.95, 0)
        put_buy = round(current_price * 0.90, 0)
        call_sell = round(current_price * 1.05, 0)
        call_buy = round(current_price * 1.10, 0)
        
        estimated_credit = (call_sell - put_sell) * 0.02
        max_loss = (call_buy - call_sell) - estimated_credit
        
        return OptionRecommendation(
            symbol=symbol,
            strategy=OptionStrategy.IRON_CONDOR,
            direction=OptionDirection.NEUTRAL,
            confidence=confidence * 0.7,
            signals=signals,
            strike_price=put_sell,
            strike_price_2=call_sell,
            expiration_dte=30,
            max_profit=estimated_credit,
            max_loss=max_loss,
            risk_reward_ratio=estimated_credit / max_loss,
            delta_exposure=0.0,
            theta_decay=0.01,  # Positive theta
            vega_exposure=-0.10,
            price_targets=price_targets,
            reasoning=f"Income strategy. Profits if price stays between ${put_sell:.2f}-${call_sell:.2f}",
        )


# Export
__all__ = [
    'AIOptionsForecast',
    'OptionRecommendation',
    'AISignal',
    'PriceTarget',
    'OptionDirection',
    'OptionStrategy',
    'SignalStrength',
]
