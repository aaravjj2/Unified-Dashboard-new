"""
ML Integration for Options Lab

Provides ML-powered predictions and recommendations:
- Price direction prediction
- IV forecast
- Optimal strike selection
- Trade recommendations
- Anomaly detection
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PricePrediction:
    """Price direction prediction result."""
    ticker: str
    direction: str  # 'bullish', 'bearish', 'neutral'
    confidence: float  # 0-1
    predicted_move: float  # Expected % move
    horizon_days: int
    factors: List[str]  # Contributing factors
    timestamp: str


@dataclass
class IVForecast:
    """IV forecast result."""
    ticker: str
    current_iv: float
    predicted_iv: float
    iv_change: float
    iv_percentile: int
    iv_rank: int
    earnings_impact: bool
    forecast_days: int
    confidence: float


@dataclass
class StrikeRecommendation:
    """Optimal strike recommendation."""
    strike: float
    option_type: str  # 'call' or 'put'
    expiration: str
    delta: float
    probability_profit: float
    risk_reward_ratio: float
    score: float
    reasoning: str


@dataclass 
class TradeRecommendation:
    """AI trade recommendation."""
    action: str  # 'buy_call', 'buy_put', 'sell_call', 'sell_put', 'spread', etc.
    symbol: str
    strike: float
    expiration: str
    confidence: float
    reasoning: str
    expected_return: float
    max_loss: float
    factors: Dict[str, Any]


@dataclass
class AnomalyAlert:
    """Unusual activity alert."""
    symbol: str
    alert_type: str  # 'volume_spike', 'iv_spike', 'large_trade', 'sweep'
    severity: str  # 'low', 'medium', 'high'
    details: str
    timestamp: str
    value: float
    threshold: float


class OptionsMLEngine:
    """
    ML Engine for options analysis and predictions.
    
    Integrates with existing ML models in the dashboard.
    """
    
    def __init__(self):
        """Initialize ML engine."""
        self.model_loaded = False
        self._price_model = None
        self._iv_model = None
        
        # Try to load existing models
        self._load_models()
    
    def _load_models(self):
        """Load ML models from model server if available."""
        try:
            # Try to import forecaster service
            from financial_dashboard.services.forecaster import get_forecaster
            self._forecaster = get_forecaster()
            self.model_loaded = True
            logger.info("✅ ML models loaded from forecaster service")
        except Exception as e:
            logger.warning(f"⚠️ ML models not available: {e}")
            self._forecaster = None
    
    def predict_price_direction(
        self, 
        ticker: str, 
        horizon_days: int = 5,
        historical_data: Optional[pd.DataFrame] = None
    ) -> PricePrediction:
        """
        Predict price direction using ML model.
        
        Args:
            ticker: Stock symbol
            horizon_days: Prediction horizon in days
            historical_data: Optional historical price data
            
        Returns:
            PricePrediction with direction and confidence
        """
        try:
            # Use forecaster if available
            if self._forecaster:
                result = self._forecaster.predict(ticker, horizon=horizon_days)
                if result:
                    direction = 'bullish' if result.get('prediction', 0) > 0 else 'bearish'
                    confidence = result.get('confidence', 0.5)
                    predicted_move = result.get('predicted_return', 0) * 100
                    
                    return PricePrediction(
                        ticker=ticker,
                        direction=direction,
                        confidence=confidence,
                        predicted_move=predicted_move,
                        horizon_days=horizon_days,
                        factors=result.get('factors', ['ML model prediction']),
                        timestamp=datetime.now().isoformat()
                    )
            
            # Fallback: Use momentum-based heuristics
            return self._heuristic_price_prediction(ticker, horizon_days, historical_data)
            
        except Exception as e:
            logger.error(f"Price prediction error: {e}")
            return PricePrediction(
                ticker=ticker,
                direction='neutral',
                confidence=0.5,
                predicted_move=0.0,
                horizon_days=horizon_days,
                factors=['Error in prediction'],
                timestamp=datetime.now().isoformat()
            )
    
    def _heuristic_price_prediction(
        self,
        ticker: str,
        horizon_days: int,
        historical_data: Optional[pd.DataFrame]
    ) -> PricePrediction:
        """Fallback heuristic-based prediction."""
        # Simple momentum-based prediction
        factors = []
        direction = 'neutral'
        confidence = 0.5
        predicted_move = 0.0
        
        if historical_data is not None and len(historical_data) >= 20:
            # Calculate momentum indicators
            close = historical_data['close'].values if 'close' in historical_data else historical_data.iloc[:, 0].values
            
            # 5-day momentum
            mom_5 = (close[-1] / close[-5] - 1) * 100 if len(close) >= 5 else 0
            
            # 20-day momentum
            mom_20 = (close[-1] / close[-20] - 1) * 100 if len(close) >= 20 else 0
            
            # RSI approximation
            gains = np.maximum(np.diff(close[-14:]), 0).mean()
            losses = np.abs(np.minimum(np.diff(close[-14:]), 0)).mean()
            rs = gains / (losses + 1e-10)
            rsi = 100 - (100 / (1 + rs))
            
            # Determine direction
            if mom_5 > 1 and mom_20 > 2:
                direction = 'bullish'
                confidence = min(0.7 + mom_5 / 20, 0.85)
                predicted_move = mom_5 * 0.3
                factors.append(f"Strong momentum: 5d={mom_5:.1f}%, 20d={mom_20:.1f}%")
            elif mom_5 < -1 and mom_20 < -2:
                direction = 'bearish'
                confidence = min(0.7 + abs(mom_5) / 20, 0.85)
                predicted_move = mom_5 * 0.3
                factors.append(f"Weak momentum: 5d={mom_5:.1f}%, 20d={mom_20:.1f}%")
            else:
                factors.append(f"Mixed signals: 5d={mom_5:.1f}%, 20d={mom_20:.1f}%")
            
            if rsi > 70:
                factors.append(f"RSI overbought: {rsi:.0f}")
            elif rsi < 30:
                factors.append(f"RSI oversold: {rsi:.0f}")
        else:
            factors.append("Insufficient historical data")
        
        return PricePrediction(
            ticker=ticker,
            direction=direction,
            confidence=confidence,
            predicted_move=predicted_move,
            horizon_days=horizon_days,
            factors=factors,
            timestamp=datetime.now().isoformat()
        )
    
    def forecast_iv(
        self,
        ticker: str,
        current_iv: float,
        historical_iv: Optional[List[float]] = None,
        days_to_earnings: Optional[int] = None,
        forecast_days: int = 5
    ) -> IVForecast:
        """
        Forecast implied volatility changes.
        
        Args:
            ticker: Stock symbol
            current_iv: Current implied volatility
            historical_iv: Historical IV values (last 252 days ideal)
            days_to_earnings: Days until next earnings (if known)
            forecast_days: Forecast horizon
            
        Returns:
            IVForecast with predicted IV and context
        """
        try:
            # Calculate IV percentile and rank
            iv_percentile = 50
            iv_rank = 50
            
            if historical_iv and len(historical_iv) >= 20:
                hist_iv = np.array(historical_iv)
                iv_percentile = int(np.percentile(hist_iv <= current_iv, 100))
                
                iv_high = np.max(hist_iv)
                iv_low = np.min(hist_iv)
                if iv_high > iv_low:
                    iv_rank = int((current_iv - iv_low) / (iv_high - iv_low) * 100)
            
            # Predict IV direction
            predicted_iv = current_iv
            earnings_impact = False
            
            # Mean reversion tendency
            if historical_iv:
                mean_iv = np.mean(historical_iv)
                # IV tends to mean-revert
                reversion_factor = 0.1 * forecast_days / 5
                predicted_iv = current_iv + (mean_iv - current_iv) * reversion_factor
            
            # Earnings impact
            if days_to_earnings is not None:
                if days_to_earnings <= forecast_days:
                    # IV typically spikes before earnings
                    if days_to_earnings > 0:
                        predicted_iv *= 1.1 + (0.2 * (1 - days_to_earnings / forecast_days))
                        earnings_impact = True
                    else:
                        # Post-earnings IV crush
                        predicted_iv *= 0.7
                        earnings_impact = True
            
            iv_change = predicted_iv - current_iv
            confidence = 0.6 if historical_iv else 0.4
            
            return IVForecast(
                ticker=ticker,
                current_iv=current_iv,
                predicted_iv=predicted_iv,
                iv_change=iv_change,
                iv_percentile=iv_percentile,
                iv_rank=iv_rank,
                earnings_impact=earnings_impact,
                forecast_days=forecast_days,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"IV forecast error: {e}")
            return IVForecast(
                ticker=ticker,
                current_iv=current_iv,
                predicted_iv=current_iv,
                iv_change=0,
                iv_percentile=50,
                iv_rank=50,
                earnings_impact=False,
                forecast_days=forecast_days,
                confidence=0.0
            )
    
    def recommend_strikes(
        self,
        ticker: str,
        spot_price: float,
        chain_data: Dict,
        strategy: str = 'long_call',
        risk_tolerance: str = 'moderate',
        target_delta: Optional[float] = None
    ) -> List[StrikeRecommendation]:
        """
        Recommend optimal strikes based on strategy and risk profile.
        
        Args:
            ticker: Stock symbol
            spot_price: Current underlying price
            chain_data: Options chain data
            strategy: 'long_call', 'long_put', 'covered_call', 'cash_secured_put'
            risk_tolerance: 'conservative', 'moderate', 'aggressive'
            target_delta: Optional specific delta target
            
        Returns:
            List of StrikeRecommendation sorted by score
        """
        recommendations = []
        
        try:
            # Get first expiration's data
            expirations = chain_data.get('expirations', [])
            chains = chain_data.get('chains', {})
            
            if not expirations or not chains:
                return recommendations
            
            # Use nearest expiration (or 30-45 DTE for optimal theta)
            target_exp = expirations[0]
            for exp in expirations:
                exp_date = datetime.strptime(exp, '%Y-%m-%d')
                dte = (exp_date - datetime.now()).days
                if 30 <= dte <= 45:
                    target_exp = exp
                    break
            
            chain = chains.get(target_exp, {})
            
            # Determine which options to analyze
            if 'call' in strategy.lower():
                options = chain.get('calls', [])
                option_type = 'call'
            else:
                options = chain.get('puts', [])
                option_type = 'put'
            
            # Set delta targets based on risk tolerance
            delta_targets = {
                'conservative': 0.30 if option_type == 'call' else -0.30,
                'moderate': 0.45 if option_type == 'call' else -0.45,
                'aggressive': 0.60 if option_type == 'call' else -0.60
            }
            
            target = target_delta or delta_targets.get(risk_tolerance, 0.45)
            
            for opt in options:
                strike = opt.get('strike', 0)
                delta = opt.get('delta', 0)
                iv = opt.get('impliedVolatility', 0)
                bid = opt.get('bid', 0)
                ask = opt.get('ask', 0)
                
                if strike == 0 or bid == 0:
                    continue
                
                # Score based on delta proximity to target
                delta_score = 1 - abs(abs(delta) - abs(target)) / abs(target) if target != 0 else 0.5
                
                # Probability of profit estimate (simplified)
                if option_type == 'call':
                    prob_profit = max(0, min(1, 1 - abs(delta)))  # OTM calls
                else:
                    prob_profit = max(0, min(1, abs(delta)))  # OTM puts
                
                # Risk/reward (max gain vs max loss for long options)
                mid_price = (bid + ask) / 2
                risk_reward = (spot_price * 0.1) / (mid_price * 100) if mid_price > 0 else 0  # Simplified
                
                # Combined score
                score = delta_score * 0.4 + prob_profit * 0.3 + min(risk_reward, 1) * 0.3
                
                # Generate reasoning
                reasoning = f"Delta {delta:.2f} "
                if abs(delta - target) < 0.05:
                    reasoning += "(matches target), "
                reasoning += f"IV {iv*100:.1f}%, "
                reasoning += f"Prob profit ~{prob_profit*100:.0f}%"
                
                recommendations.append(StrikeRecommendation(
                    strike=strike,
                    option_type=option_type,
                    expiration=target_exp,
                    delta=delta,
                    probability_profit=prob_profit,
                    risk_reward_ratio=risk_reward,
                    score=score,
                    reasoning=reasoning
                ))
            
            # Sort by score descending
            recommendations.sort(key=lambda x: x.score, reverse=True)
            return recommendations[:5]  # Top 5
            
        except Exception as e:
            logger.error(f"Strike recommendation error: {e}")
            return recommendations
    
    def generate_trade_recommendations(
        self,
        ticker: str,
        spot_price: float,
        chain_data: Dict,
        price_prediction: Optional[PricePrediction] = None,
        iv_forecast: Optional[IVForecast] = None
    ) -> List[TradeRecommendation]:
        """
        Generate AI-powered trade recommendations.
        
        Args:
            ticker: Stock symbol
            spot_price: Current price
            chain_data: Options chain data
            price_prediction: Optional price prediction
            iv_forecast: Optional IV forecast
            
        Returns:
            List of TradeRecommendation
        """
        recommendations = []
        
        try:
            # Get prediction if not provided
            if price_prediction is None:
                price_prediction = self.predict_price_direction(ticker)
            
            # Generate recommendations based on prediction
            direction = price_prediction.direction
            confidence = price_prediction.confidence
            
            # Get strike recommendations
            if direction == 'bullish' and confidence >= 0.6:
                strikes = self.recommend_strikes(
                    ticker, spot_price, chain_data, 
                    strategy='long_call', 
                    risk_tolerance='moderate' if confidence < 0.75 else 'aggressive'
                )
                
                if strikes:
                    best_strike = strikes[0]
                    recommendations.append(TradeRecommendation(
                        action='buy_call',
                        symbol=ticker,
                        strike=best_strike.strike,
                        expiration=best_strike.expiration,
                        confidence=confidence,
                        reasoning=f"Bullish outlook ({confidence*100:.0f}% confidence). {best_strike.reasoning}",
                        expected_return=price_prediction.predicted_move * 2,  # Leverage estimate
                        max_loss=100,  # Premium paid
                        factors={
                            'price_direction': direction,
                            'prediction_confidence': confidence,
                            'iv_percentile': iv_forecast.iv_percentile if iv_forecast else 50
                        }
                    ))
            
            elif direction == 'bearish' and confidence >= 0.6:
                strikes = self.recommend_strikes(
                    ticker, spot_price, chain_data,
                    strategy='long_put',
                    risk_tolerance='moderate' if confidence < 0.75 else 'aggressive'
                )
                
                if strikes:
                    best_strike = strikes[0]
                    recommendations.append(TradeRecommendation(
                        action='buy_put',
                        symbol=ticker,
                        strike=best_strike.strike,
                        expiration=best_strike.expiration,
                        confidence=confidence,
                        reasoning=f"Bearish outlook ({confidence*100:.0f}% confidence). {best_strike.reasoning}",
                        expected_return=abs(price_prediction.predicted_move) * 2,
                        max_loss=100,
                        factors={
                            'price_direction': direction,
                            'prediction_confidence': confidence,
                            'iv_percentile': iv_forecast.iv_percentile if iv_forecast else 50
                        }
                    ))
            
            # IV-based recommendations
            if iv_forecast and iv_forecast.iv_percentile < 20:
                recommendations.append(TradeRecommendation(
                    action='buy_straddle',
                    symbol=ticker,
                    strike=spot_price,  # ATM
                    expiration=chain_data.get('expirations', [''])[0],
                    confidence=0.6,
                    reasoning=f"IV at {iv_forecast.iv_percentile}th percentile - cheap options. Consider buying volatility.",
                    expected_return=50,
                    max_loss=100,
                    factors={
                        'iv_percentile': iv_forecast.iv_percentile,
                        'strategy': 'long_volatility'
                    }
                ))
            elif iv_forecast and iv_forecast.iv_percentile > 80:
                recommendations.append(TradeRecommendation(
                    action='sell_strangle',
                    symbol=ticker,
                    strike=spot_price,
                    expiration=chain_data.get('expirations', [''])[0],
                    confidence=0.6,
                    reasoning=f"IV at {iv_forecast.iv_percentile}th percentile - expensive options. Consider selling volatility.",
                    expected_return=30,
                    max_loss=200,  # Undefined risk warning
                    factors={
                        'iv_percentile': iv_forecast.iv_percentile,
                        'strategy': 'short_volatility'
                    }
                ))
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Trade recommendation error: {e}")
            return recommendations
    
    def detect_anomalies(
        self,
        ticker: str,
        chain_data: Dict,
        historical_volume: Optional[Dict] = None
    ) -> List[AnomalyAlert]:
        """
        Detect unusual options activity.
        
        Args:
            ticker: Stock symbol
            chain_data: Current options chain data
            historical_volume: Historical volume data for comparison
            
        Returns:
            List of AnomalyAlert
        """
        alerts = []
        
        try:
            chains = chain_data.get('chains', {})
            
            for exp, chain in chains.items():
                for opt_type in ['calls', 'puts']:
                    options = chain.get(opt_type, [])
                    
                    for opt in options:
                        strike = opt.get('strike', 0)
                        volume = opt.get('volume', 0)
                        oi = opt.get('openInterest', 0)
                        iv = opt.get('impliedVolatility', 0)
                        
                        # Volume spike detection
                        if oi > 0 and volume > oi * 2:
                            alerts.append(AnomalyAlert(
                                symbol=f"{ticker} {exp} {strike} {opt_type[:-1].upper()}",
                                alert_type='volume_spike',
                                severity='high' if volume > oi * 5 else 'medium',
                                details=f"Volume {volume:,} is {volume/oi:.1f}x open interest {oi:,}",
                                timestamp=datetime.now().isoformat(),
                                value=volume,
                                threshold=oi * 2
                            ))
                        
                        # IV spike (would need historical comparison)
                        if iv > 1.0:  # 100% IV is unusual for most stocks
                            alerts.append(AnomalyAlert(
                                symbol=f"{ticker} {exp} {strike} {opt_type[:-1].upper()}",
                                alert_type='iv_spike',
                                severity='high' if iv > 1.5 else 'medium',
                                details=f"IV at {iv*100:.1f}% is elevated",
                                timestamp=datetime.now().isoformat(),
                                value=iv * 100,
                                threshold=100
                            ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
            return alerts


# Singleton instance
_ml_engine: Optional[OptionsMLEngine] = None


def get_ml_engine() -> OptionsMLEngine:
    """Get or create singleton ML engine."""
    global _ml_engine
    if _ml_engine is None:
        _ml_engine = OptionsMLEngine()
    return _ml_engine
