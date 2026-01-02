"""
AI Recommendation Engine - Phase 2: Strategy Recommendations
=============================================================
Combines Phase 1 (Hype Score/Sentiment) + Phase 2 (Forecast) signals
to generate actionable options strategy recommendations.

Decision Matrix:
- High Hype + Bullish Forecast → Aggressive bullish plays (Long Call, Debit Call Spread)
- Low Hype + High Vol → Neutral/defensive plays (Iron Condor, Credit Spread)
- Macro Bullish (GLD) → Safe haven plays
- Tech Bullish (NVDA) → Growth plays

Focus Assets: NVDA, TSLA, SPY, GLD, SLV
"""

import os
import sys
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from enum import Enum

import numpy as np
import pandas as pd

# Add parent path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import Phase 1 & Phase 2 engines
try:
    from financial_dashboard.engines.news import get_news_client, HybridNewsClient
except ImportError:
    get_news_client = None
    HybridNewsClient = None

try:
    from financial_dashboard.engines.ai.local_forecast import (
        get_forecast_engine, LocalForecastEngine, ForecastResult, 
        VolatilityForecast, TrendDirection, VolatilityRegime
    )
except ImportError:
    get_forecast_engine = None
    LocalForecastEngine = None

logger = logging.getLogger(__name__)


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class StrategyType(Enum):
    """Options strategy types."""
    # Bullish
    LONG_CALL = "Long Call"
    DEBIT_CALL_SPREAD = "Debit Call Spread"
    BULL_PUT_SPREAD = "Bull Put Spread"
    CALL_CALENDAR = "Call Calendar"
    
    # Bearish
    LONG_PUT = "Long Put"
    DEBIT_PUT_SPREAD = "Debit Put Spread"
    BEAR_CALL_SPREAD = "Bear Call Spread"
    PUT_CALENDAR = "Put Calendar"
    
    # Neutral/Income
    IRON_CONDOR = "Iron Condor"
    IRON_BUTTERFLY = "Iron Butterfly"
    STRADDLE = "Straddle"
    STRANGLE = "Strangle"
    COVERED_CALL = "Covered Call"
    CASH_SECURED_PUT = "Cash-Secured Put"
    
    # Volatility
    LONG_STRADDLE = "Long Straddle"
    LONG_STRANGLE = "Long Strangle"
    RATIO_SPREAD = "Ratio Spread"


class RiskLevel(Enum):
    """Risk classification."""
    CONSERVATIVE = "Conservative"
    MODERATE = "Moderate"
    AGGRESSIVE = "Aggressive"
    SPECULATIVE = "Speculative"


class SignalStrength(Enum):
    """Signal strength classification."""
    STRONG = "Strong"
    MODERATE = "Moderate"
    WEAK = "Weak"


@dataclass
class StrategyLeg:
    """Single leg of an options strategy."""
    action: str          # 'BUY' or 'SELL'
    option_type: str     # 'CALL' or 'PUT'
    strike: float        # Strike price
    expiry_days: int     # Days to expiration
    quantity: int = 1
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'action': self.action,
            'option_type': self.option_type,
            'strike': self.strike,
            'expiry_days': self.expiry_days,
            'quantity': self.quantity
        }


@dataclass
class StrategyRecommendation:
    """A complete strategy recommendation."""
    symbol: str
    strategy: StrategyType
    strategy_name: str
    
    # Legs
    legs: List[StrategyLeg]
    
    # Reasoning
    reason: str                    # Human-readable explanation
    signals: List[str]             # List of signals that triggered this rec
    
    # Confidence & Risk
    confidence: float              # 0-1 confidence score
    signal_strength: SignalStrength
    risk_level: RiskLevel
    
    # Trade parameters
    suggested_expiry: str          # e.g., "Weekly", "Monthly", "45 DTE"
    target_profit_pct: float       # Expected profit target %
    max_loss_pct: float           # Maximum loss %
    
    # Context
    underlying_price: float
    hype_score: float
    forecast_direction: str
    vol_regime: str
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'strategy': self.strategy.value,
            'strategy_name': self.strategy_name,
            'legs': [leg.to_dict() for leg in self.legs],
            'reason': self.reason,
            'signals': self.signals,
            'confidence': round(self.confidence, 2),
            'signal_strength': self.signal_strength.value,
            'risk_level': self.risk_level.value,
            'suggested_expiry': self.suggested_expiry,
            'target_profit_pct': round(self.target_profit_pct, 1),
            'max_loss_pct': round(self.max_loss_pct, 1),
            'underlying_price': round(self.underlying_price, 2),
            'hype_score': round(self.hype_score, 2),
            'forecast_direction': self.forecast_direction,
            'vol_regime': self.vol_regime,
            'timestamp': self.timestamp.isoformat()
        }


# =============================================================================
# AI RECOMMENDER ENGINE
# =============================================================================

class AIRecommender:
    """
    AI-powered strategy recommendation engine.
    
    Combines multiple signals:
    1. Retail Hype Score (Phase 1) - sentiment gauge
    2. Price Forecast (Phase 2) - EMA/regression direction
    3. Volatility Regime (Phase 2) - HV percentile classification
    4. News Sentiment (Phase 2) - headline analysis
    
    Decision Rules:
    - High Hype (>70) + Bullish Forecast → Aggressive bullish
    - Low Hype (<30) + High Vol → Neutral income strategies
    - Macro Bullish (GLD/SLV) → Safe haven plays
    - High Vol Regime → Premium selling strategies
    - Low Vol Regime → Premium buying strategies
    
    Usage:
        recommender = AIRecommender()
        recs = recommender.generate_recommendations('NVDA', price_history_df)
        for rec in recs:
            print(f"{rec.strategy_name}: {rec.reason}")
    """
    
    # Hype thresholds
    HIGH_HYPE = 70
    LOW_HYPE = 30
    
    # Focus asset classifications
    TECH_ASSETS = {'NVDA', 'TSLA', 'AMD', 'AAPL', 'MSFT', 'META', 'GOOGL', 'AMZN'}
    MACRO_ASSETS = {'SPY', 'QQQ', 'IWM', 'DIA'}
    SAFE_HAVEN = {'GLD', 'SLV', 'TLT'}
    
    def __init__(self, news_client: Optional[HybridNewsClient] = None,
                 forecast_engine: Optional[LocalForecastEngine] = None):
        """Initialize the recommender with optional engines."""
        self.news_client = news_client or (get_news_client() if get_news_client else None)
        self.forecast_engine = forecast_engine or (get_forecast_engine() if get_forecast_engine else None)
        
        logger.info("🤖 AIRecommender initialized (Phase 2)")
    
    def generate_recommendations(self, symbol: str, 
                                 history_df: Optional[pd.DataFrame] = None,
                                 current_iv: Optional[float] = None,
                                 max_recommendations: int = 3) -> List[StrategyRecommendation]:
        """
        Generate strategy recommendations for a symbol.
        
        Args:
            symbol: Ticker symbol
            history_df: Price history DataFrame (optional, will fetch if not provided)
            current_iv: Current implied volatility (optional)
            max_recommendations: Maximum number of recommendations
            
        Returns:
            List of StrategyRecommendation objects, sorted by confidence
        """
        symbol = symbol.upper().strip()
        
        # Gather all signals
        signals = self._gather_signals(symbol, history_df, current_iv)
        
        # Generate recommendations based on signals
        recommendations = self._generate_from_signals(symbol, signals)
        
        # Sort by confidence and limit
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        return recommendations[:max_recommendations]
    
    def generate_multi_symbol_recommendations(self, 
                                             symbols: List[str],
                                             history_data: Optional[Dict[str, pd.DataFrame]] = None,
                                             max_per_symbol: int = 2) -> Dict[str, List[StrategyRecommendation]]:
        """Generate recommendations for multiple symbols."""
        results = {}
        for symbol in symbols:
            df = history_data.get(symbol) if history_data else None
            results[symbol] = self.generate_recommendations(symbol, df, max_recommendations=max_per_symbol)
        return results
    
    def _gather_signals(self, symbol: str, 
                       history_df: Optional[pd.DataFrame],
                       current_iv: Optional[float]) -> Dict[str, Any]:
        """Gather all signals for decision making."""
        signals = {
            'symbol': symbol,
            'asset_class': self._classify_asset(symbol),
            'hype_score': 50.0,  # Default neutral
            'hype_label': 'Neutral',
            'news_sentiment': 'Neutral',
            'news_positive_pct': 50.0,
            'forecast_direction': 'Neutral',
            'forecast_confidence': 0.5,
            'momentum': 0.0,
            'vol_regime': 'Normal',
            'vol_percentile': 50.0,
            'current_hv': 0.25,
            'current_iv': current_iv or 0.25,
            'iv_premium': 0.0,
            'underlying_price': 100.0
        }
        
        # Get hype score from news client
        if self.news_client:
            try:
                hype_data = self.news_client.get_hype_score(symbol)
                signals['hype_score'] = hype_data.get('hype_score', 0.5) * 100
                signals['hype_label'] = hype_data.get('sentiment_label', 'Neutral')
                
                # Get news sentiment breakdown
                sentiment_summary = self.news_client.get_sentiment_summary(symbol)
                signals['news_positive_pct'] = sentiment_summary.get('positive_pct', 50)
                signals['news_sentiment'] = sentiment_summary.get('overall_sentiment', 'Neutral')
            except Exception as e:
                logger.warning(f"Failed to get hype data for {symbol}: {e}")
        
        # Get forecast from forecast engine
        if self.forecast_engine and history_df is not None and len(history_df) > 0:
            try:
                forecast = self.forecast_engine.generate_forecast(symbol, history_df)
                signals['forecast_direction'] = forecast.direction.value
                signals['forecast_confidence'] = forecast.confidence
                signals['momentum'] = forecast.momentum_score
                signals['underlying_price'] = forecast.current_price
                
                vol_forecast = self.forecast_engine.forecast_volatility(symbol, history_df, current_iv)
                signals['vol_regime'] = vol_forecast.regime.value
                signals['vol_percentile'] = vol_forecast.percentile
                signals['current_hv'] = vol_forecast.current_hv
                if vol_forecast.iv_premium:
                    signals['iv_premium'] = vol_forecast.iv_premium
            except Exception as e:
                logger.warning(f"Failed to get forecast for {symbol}: {e}")
        
        return signals
    
    def _generate_from_signals(self, symbol: str, 
                              signals: Dict[str, Any]) -> List[StrategyRecommendation]:
        """Generate recommendations based on gathered signals."""
        recommendations = []
        
        hype = signals['hype_score']
        vol_regime = signals['vol_regime']
        forecast_dir = signals['forecast_direction']
        asset_class = signals['asset_class']
        price = signals['underlying_price']
        
        # =====================================================================
        # RULE 1: High Hype + Bullish Forecast → Aggressive bullish plays
        # =====================================================================
        if hype > self.HIGH_HYPE and 'Bullish' in forecast_dir:
            # Debit Call Spread (defined risk)
            recommendations.append(self._create_recommendation(
                symbol=symbol,
                strategy=StrategyType.DEBIT_CALL_SPREAD,
                signals=signals,
                reason=f"High retail hype ({hype:.0f}) + {forecast_dir} forecast signals strong upside momentum",
                signal_list=['High Hype', 'Bullish Forecast', f'{asset_class} Momentum'],
                confidence=min(0.85, signals['forecast_confidence'] + 0.1),
                risk_level=RiskLevel.MODERATE,
                expiry="Monthly (30-45 DTE)",
                target_pct=50.0,
                max_loss_pct=100.0  # Max loss is debit paid
            ))
            
            # Long Call (higher risk, higher reward)
            if 'Strongly' in forecast_dir:
                recommendations.append(self._create_recommendation(
                    symbol=symbol,
                    strategy=StrategyType.LONG_CALL,
                    signals=signals,
                    reason=f"Strongly bullish conditions: {hype:.0f} hype + {forecast_dir} with {signals['momentum']:.1f} momentum",
                    signal_list=['High Hype', 'Strong Momentum', 'Bullish Forecast'],
                    confidence=min(0.8, signals['forecast_confidence']),
                    risk_level=RiskLevel.AGGRESSIVE,
                    expiry="Weekly (7-14 DTE)",
                    target_pct=100.0,
                    max_loss_pct=100.0
                ))
        
        # =====================================================================
        # RULE 2: Low Hype + High Vol → Neutral income plays
        # =====================================================================
        if hype < self.LOW_HYPE and vol_regime in ('High', 'Extreme'):
            # Iron Condor (premium collection)
            recommendations.append(self._create_recommendation(
                symbol=symbol,
                strategy=StrategyType.IRON_CONDOR,
                signals=signals,
                reason=f"Low hype ({hype:.0f}) + {vol_regime} volatility = premium selling opportunity",
                signal_list=['Low Hype', 'High IV', 'Neutral Outlook'],
                confidence=0.75,
                risk_level=RiskLevel.MODERATE,
                expiry="Monthly (30-45 DTE)",
                target_pct=30.0,
                max_loss_pct=70.0
            ))
        
        # =====================================================================
        # RULE 3: Bearish Signals → Defensive plays
        # =====================================================================
        if 'Bearish' in forecast_dir and signals['momentum'] < -0.3:
            # Bear Call Spread (credit)
            recommendations.append(self._create_recommendation(
                symbol=symbol,
                strategy=StrategyType.BEAR_CALL_SPREAD,
                signals=signals,
                reason=f"Bearish forecast ({forecast_dir}) with negative momentum ({signals['momentum']:.2f})",
                signal_list=['Bearish Forecast', 'Negative Momentum'],
                confidence=min(0.7, signals['forecast_confidence']),
                risk_level=RiskLevel.MODERATE,
                expiry="Monthly (30-45 DTE)",
                target_pct=35.0,
                max_loss_pct=65.0
            ))
            
            # Long Put (if strongly bearish)
            if 'Strongly' in forecast_dir:
                recommendations.append(self._create_recommendation(
                    symbol=symbol,
                    strategy=StrategyType.LONG_PUT,
                    signals=signals,
                    reason=f"Strongly bearish conditions warrant put protection",
                    signal_list=['Strong Bearish', 'High Conviction'],
                    confidence=min(0.75, signals['forecast_confidence']),
                    risk_level=RiskLevel.AGGRESSIVE,
                    expiry="Weekly (7-14 DTE)",
                    target_pct=80.0,
                    max_loss_pct=100.0
                ))
        
        # =====================================================================
        # RULE 4: Safe Haven (GLD/SLV) Bullish → Safe haven plays
        # =====================================================================
        if asset_class == 'SAFE_HAVEN' and signals['hype_label'] == 'Bullish':
            recommendations.append(self._create_recommendation(
                symbol=symbol,
                strategy=StrategyType.BULL_PUT_SPREAD,
                signals=signals,
                reason=f"Safe haven asset showing bullish sentiment - collect premium on downside",
                signal_list=['Safe Haven', 'Bullish Sentiment', 'Risk-Off Environment'],
                confidence=0.7,
                risk_level=RiskLevel.CONSERVATIVE,
                expiry="Monthly (45-60 DTE)",
                target_pct=25.0,
                max_loss_pct=75.0
            ))
        
        # =====================================================================
        # RULE 5: High IV Premium → Premium selling
        # =====================================================================
        if signals['iv_premium'] > 0.05:  # IV 5% above HV
            recommendations.append(self._create_recommendation(
                symbol=symbol,
                strategy=StrategyType.IRON_CONDOR,
                signals=signals,
                reason=f"IV premium ({signals['iv_premium']*100:.1f}%) suggests overpriced options - sell premium",
                signal_list=['High IV Premium', 'Premium Selling Opportunity'],
                confidence=0.7,
                risk_level=RiskLevel.MODERATE,
                expiry="Monthly (30-45 DTE)",
                target_pct=30.0,
                max_loss_pct=70.0
            ))
        
        # =====================================================================
        # RULE 6: Low Vol Regime → Long volatility plays
        # =====================================================================
        if vol_regime == 'Low' and signals['vol_percentile'] < 20:
            recommendations.append(self._create_recommendation(
                symbol=symbol,
                strategy=StrategyType.LONG_STRADDLE,
                signals=signals,
                reason=f"Volatility at {signals['vol_percentile']:.0f}th percentile - expect mean reversion",
                signal_list=['Low Volatility', 'Vol Expansion Expected'],
                confidence=0.65,
                risk_level=RiskLevel.AGGRESSIVE,
                expiry="Monthly (30-45 DTE)",
                target_pct=50.0,
                max_loss_pct=100.0
            ))
        
        # =====================================================================
        # RULE 7: Neutral forecast + Normal vol → Calendar spreads
        # =====================================================================
        if forecast_dir == 'Neutral' and vol_regime == 'Normal':
            recommendations.append(self._create_recommendation(
                symbol=symbol,
                strategy=StrategyType.CALL_CALENDAR,
                signals=signals,
                reason=f"Neutral outlook with normal volatility - calendar spread for theta decay",
                signal_list=['Neutral Forecast', 'Normal Volatility', 'Time Decay Play'],
                confidence=0.6,
                risk_level=RiskLevel.CONSERVATIVE,
                expiry="Calendar (7 DTE front / 45 DTE back)",
                target_pct=20.0,
                max_loss_pct=50.0
            ))
        
        # =====================================================================
        # DEFAULT: Cash-Secured Put for high-quality assets
        # =====================================================================
        if asset_class == 'TECH' and len(recommendations) < 2:
            recommendations.append(self._create_recommendation(
                symbol=symbol,
                strategy=StrategyType.CASH_SECURED_PUT,
                signals=signals,
                reason=f"Collect premium while waiting to own {symbol} at lower price",
                signal_list=['Tech Asset', 'Premium Collection', 'Buy-the-Dip Setup'],
                confidence=0.6,
                risk_level=RiskLevel.CONSERVATIVE,
                expiry="Monthly (30-45 DTE)",
                target_pct=15.0,
                max_loss_pct=100.0  # Assigned stock
            ))
        
        return recommendations
    
    def _create_recommendation(self, symbol: str, strategy: StrategyType,
                              signals: Dict[str, Any], reason: str,
                              signal_list: List[str], confidence: float,
                              risk_level: RiskLevel, expiry: str,
                              target_pct: float, max_loss_pct: float) -> StrategyRecommendation:
        """Create a strategy recommendation with legs."""
        price = signals['underlying_price']
        
        # Generate legs based on strategy type
        legs = self._generate_legs(strategy, price)
        
        # Determine signal strength
        if confidence >= 0.75:
            signal_strength = SignalStrength.STRONG
        elif confidence >= 0.6:
            signal_strength = SignalStrength.MODERATE
        else:
            signal_strength = SignalStrength.WEAK
        
        return StrategyRecommendation(
            symbol=symbol,
            strategy=strategy,
            strategy_name=strategy.value,
            legs=legs,
            reason=reason,
            signals=signal_list,
            confidence=confidence,
            signal_strength=signal_strength,
            risk_level=risk_level,
            suggested_expiry=expiry,
            target_profit_pct=target_pct,
            max_loss_pct=max_loss_pct,
            underlying_price=price,
            hype_score=signals['hype_score'],
            forecast_direction=signals['forecast_direction'],
            vol_regime=signals['vol_regime']
        )
    
    def _generate_legs(self, strategy: StrategyType, price: float) -> List[StrategyLeg]:
        """Generate option legs for a strategy."""
        # Round to nearest strike interval
        atm_strike = round(price / 5) * 5
        otm_call = atm_strike + 5
        otm_put = atm_strike - 5
        
        legs = []
        
        if strategy == StrategyType.LONG_CALL:
            legs = [StrategyLeg('BUY', 'CALL', atm_strike, 30)]
        
        elif strategy == StrategyType.LONG_PUT:
            legs = [StrategyLeg('BUY', 'PUT', atm_strike, 30)]
        
        elif strategy == StrategyType.DEBIT_CALL_SPREAD:
            legs = [
                StrategyLeg('BUY', 'CALL', atm_strike, 30),
                StrategyLeg('SELL', 'CALL', otm_call + 5, 30)
            ]
        
        elif strategy == StrategyType.DEBIT_PUT_SPREAD:
            legs = [
                StrategyLeg('BUY', 'PUT', atm_strike, 30),
                StrategyLeg('SELL', 'PUT', otm_put - 5, 30)
            ]
        
        elif strategy == StrategyType.BULL_PUT_SPREAD:
            legs = [
                StrategyLeg('SELL', 'PUT', otm_put, 45),
                StrategyLeg('BUY', 'PUT', otm_put - 5, 45)
            ]
        
        elif strategy == StrategyType.BEAR_CALL_SPREAD:
            legs = [
                StrategyLeg('SELL', 'CALL', otm_call, 45),
                StrategyLeg('BUY', 'CALL', otm_call + 5, 45)
            ]
        
        elif strategy == StrategyType.IRON_CONDOR:
            legs = [
                StrategyLeg('BUY', 'PUT', otm_put - 10, 45),
                StrategyLeg('SELL', 'PUT', otm_put - 5, 45),
                StrategyLeg('SELL', 'CALL', otm_call + 5, 45),
                StrategyLeg('BUY', 'CALL', otm_call + 10, 45)
            ]
        
        elif strategy == StrategyType.LONG_STRADDLE:
            legs = [
                StrategyLeg('BUY', 'CALL', atm_strike, 30),
                StrategyLeg('BUY', 'PUT', atm_strike, 30)
            ]
        
        elif strategy == StrategyType.LONG_STRANGLE:
            legs = [
                StrategyLeg('BUY', 'CALL', otm_call, 30),
                StrategyLeg('BUY', 'PUT', otm_put, 30)
            ]
        
        elif strategy == StrategyType.CALL_CALENDAR:
            legs = [
                StrategyLeg('SELL', 'CALL', atm_strike, 7),
                StrategyLeg('BUY', 'CALL', atm_strike, 45)
            ]
        
        elif strategy == StrategyType.CASH_SECURED_PUT:
            legs = [StrategyLeg('SELL', 'PUT', otm_put, 45)]
        
        elif strategy == StrategyType.COVERED_CALL:
            legs = [StrategyLeg('SELL', 'CALL', otm_call, 30)]
        
        return legs
    
    def _classify_asset(self, symbol: str) -> str:
        """Classify asset type."""
        symbol = symbol.upper()
        if symbol in self.TECH_ASSETS:
            return 'TECH'
        elif symbol in self.MACRO_ASSETS:
            return 'MACRO'
        elif symbol in self.SAFE_HAVEN:
            return 'SAFE_HAVEN'
        else:
            return 'OTHER'


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

_recommender_instance: Optional[AIRecommender] = None


def get_ai_recommender() -> AIRecommender:
    """Get singleton recommender instance."""
    global _recommender_instance
    if _recommender_instance is None:
        _recommender_instance = AIRecommender()
    return _recommender_instance


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("AI Recommender Test")
    print("=" * 60)
    
    # Generate mock price history
    np.random.seed(42)
    n_days = 60
    
    # Simulate bullish NVDA
    base_price = 140.0
    returns = np.random.randn(n_days) * 0.02 + 0.002  # Upward bias
    nvda_prices = base_price * np.cumprod(1 + returns)
    
    nvda_df = pd.DataFrame({
        'Close': nvda_prices,
        'High': nvda_prices * 1.01,
        'Low': nvda_prices * 0.99,
        'Volume': np.random.randint(10000000, 50000000, n_days)
    })
    
    # Simulate bearish TSLA
    base_price = 250.0
    returns = np.random.randn(n_days) * 0.03 - 0.001  # Downward bias
    tsla_prices = base_price * np.cumprod(1 + returns)
    
    tsla_df = pd.DataFrame({
        'Close': tsla_prices,
        'High': tsla_prices * 1.02,
        'Low': tsla_prices * 0.98,
        'Volume': np.random.randint(20000000, 100000000, n_days)
    })
    
    recommender = AIRecommender()
    
    # Test NVDA recommendations
    print("\n📈 NVDA Recommendations")
    print("-" * 40)
    nvda_recs = recommender.generate_recommendations('NVDA', nvda_df)
    for rec in nvda_recs:
        print(f"  🎯 {rec.strategy_name}")
        print(f"     Confidence: {rec.confidence:.0%} ({rec.signal_strength.value})")
        print(f"     Risk: {rec.risk_level.value}")
        print(f"     Reason: {rec.reason[:80]}...")
        print(f"     Signals: {', '.join(rec.signals)}")
        print(f"     Legs: {len(rec.legs)}")
        print()
    
    # Test TSLA recommendations
    print("\n📉 TSLA Recommendations")
    print("-" * 40)
    tsla_recs = recommender.generate_recommendations('TSLA', tsla_df)
    for rec in tsla_recs:
        print(f"  🎯 {rec.strategy_name}")
        print(f"     Confidence: {rec.confidence:.0%}")
        print(f"     Reason: {rec.reason[:80]}...")
        print()
    
    print("=" * 60)
    print("✅ All tests completed!")

