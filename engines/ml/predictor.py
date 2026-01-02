"""
ML Predictor Module - Phase 2 Forecast Engine

Implements:
- PricePredictor: LSTM-based price direction prediction (deterministic stub)
- VolPredictor: XGBoost-based volatility forecast (deterministic stub)

Environment Variables:
- ML_DETERMINISTIC=1: Uses fixed seed for reproducible results
- AZURE_ENABLED=false: Disables Azure ML integration

Author: Agent-ML Phase 2
"""

import os
import logging
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

import numpy as np

logger = logging.getLogger(__name__)

# Environment configuration
ML_DETERMINISTIC = os.environ.get('ML_DETERMINISTIC', '1') == '1'
AZURE_ENABLED = os.environ.get('AZURE_ENABLED', 'false').lower() == 'true'

# Fixed seed for deterministic mode
DETERMINISTIC_SEED = 42


class RegimeType(Enum):
    """Market regime classification."""
    BULL = "BULL"
    BEAR = "BEAR"
    CRAB = "CRAB"  # Sideways/range-bound


class SignalDirection(Enum):
    """Price direction signal."""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass
class PricePrediction:
    """Price prediction result."""
    ticker: str
    direction: SignalDirection
    confidence: float  # 0-100
    target_price: float
    current_price: float
    change_pct: float
    horizon_days: int
    regime: RegimeType
    signal_strength: float  # 0-100 for gauge
    price_path: List[float]  # Predicted price path
    timestamps: List[str]
    last_updated: str
    model_version: str = "lstm_stub_v1"


@dataclass
class VolatilityPrediction:
    """Volatility prediction result."""
    ticker: str
    current_iv: float  # Current implied volatility
    forecast_iv: float  # Forecasted IV
    iv_change_pct: float
    iv_rank: float  # 0-100 percentile
    vol_regime: str  # "HIGH", "NORMAL", "LOW"
    confidence: float  # 0-100
    horizon_days: int
    last_updated: str
    model_version: str = "xgb_stub_v1"


class PricePredictor:
    """
    LSTM-based Price Predictor (Stub Implementation).
    
    In production, this would use a trained LSTM model.
    For Phase 2, uses deterministic signals based on ticker hash.
    """
    
    def __init__(self, deterministic: bool = ML_DETERMINISTIC):
        self.deterministic = deterministic
        self.model_version = "lstm_stub_v1"
        
        if self.deterministic:
            np.random.seed(DETERMINISTIC_SEED)
            logger.info("PricePredictor initialized in DETERMINISTIC mode")
        else:
            logger.info("PricePredictor initialized in RANDOM mode")
    
    def _get_deterministic_seed(self, ticker: str) -> int:
        """Generate deterministic seed from ticker."""
        hash_val = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
        return hash_val % 10000
    
    def _generate_regime(self, ticker: str, seed: int) -> RegimeType:
        """Generate market regime based on seed."""
        np.random.seed(seed)
        regime_val = np.random.random()
        
        if regime_val < 0.35:
            return RegimeType.BULL
        elif regime_val < 0.65:
            return RegimeType.CRAB
        else:
            return RegimeType.BEAR
    
    def _generate_direction(self, regime: RegimeType, seed: int) -> Tuple[SignalDirection, float]:
        """Generate direction signal based on regime."""
        np.random.seed(seed + 1)
        
        if regime == RegimeType.BULL:
            # Higher probability of bullish signal
            direction = SignalDirection.BULLISH if np.random.random() < 0.75 else SignalDirection.NEUTRAL
            confidence = 60 + np.random.random() * 25  # 60-85%
        elif regime == RegimeType.BEAR:
            # Higher probability of bearish signal
            direction = SignalDirection.BEARISH if np.random.random() < 0.75 else SignalDirection.NEUTRAL
            confidence = 55 + np.random.random() * 30  # 55-85%
        else:  # CRAB
            # Neutral/mixed signals
            rand = np.random.random()
            if rand < 0.33:
                direction = SignalDirection.BULLISH
            elif rand < 0.66:
                direction = SignalDirection.BEARISH
            else:
                direction = SignalDirection.NEUTRAL
            confidence = 40 + np.random.random() * 25  # 40-65%
        
        return direction, round(confidence, 1)
    
    def _generate_price_path(
        self, 
        current_price: float, 
        direction: SignalDirection, 
        horizon_days: int,
        seed: int
    ) -> Tuple[List[float], float]:
        """Generate predicted price path."""
        np.random.seed(seed + 2)
        
        # Base drift based on direction
        if direction == SignalDirection.BULLISH:
            daily_drift = 0.002 + np.random.random() * 0.003  # 0.2-0.5% daily
        elif direction == SignalDirection.BEARISH:
            daily_drift = -0.002 - np.random.random() * 0.003  # -0.2 to -0.5% daily
        else:
            daily_drift = (np.random.random() - 0.5) * 0.002  # +/-0.1% daily
        
        # Daily volatility (typical for stocks)
        daily_vol = 0.015 + np.random.random() * 0.01  # 1.5-2.5% daily vol
        
        # Generate price path
        prices = [current_price]
        for _ in range(horizon_days):
            shock = np.random.normal(daily_drift, daily_vol)
            new_price = prices[-1] * (1 + shock)
            prices.append(round(new_price, 2))
        
        target_price = prices[-1]
        return prices, target_price
    
    def predict(
        self, 
        ticker: str, 
        current_price: float, 
        horizon_days: int = 7,
        historical_prices: Optional[List[float]] = None
    ) -> PricePrediction:
        """
        Generate price prediction for ticker.
        
        Args:
            ticker: Stock ticker symbol
            current_price: Current stock price
            horizon_days: Prediction horizon in days
            historical_prices: Optional historical price data
            
        Returns:
            PricePrediction dataclass with prediction results
        """
        # Get deterministic seed
        seed = self._get_deterministic_seed(ticker) if self.deterministic else np.random.randint(0, 10000)
        
        # Generate predictions
        regime = self._generate_regime(ticker, seed)
        direction, confidence = self._generate_direction(regime, seed)
        price_path, target_price = self._generate_price_path(
            current_price, direction, horizon_days, seed
        )
        
        # Calculate change percentage
        change_pct = ((target_price - current_price) / current_price) * 100
        
        # Signal strength for gauge (0-100)
        signal_strength = confidence * (abs(change_pct) / 5)  # Scale by expected move
        signal_strength = min(100, max(0, signal_strength))
        
        # Generate timestamps
        now = datetime.now()
        timestamps = [(now + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(horizon_days + 1)]
        
        return PricePrediction(
            ticker=ticker,
            direction=direction,
            confidence=confidence,
            target_price=round(target_price, 2),
            current_price=current_price,
            change_pct=round(change_pct, 2),
            horizon_days=horizon_days,
            regime=regime,
            signal_strength=round(signal_strength, 1),
            price_path=price_path,
            timestamps=timestamps,
            last_updated=now.strftime('%Y-%m-%d %H:%M:%S'),
            model_version=self.model_version
        )
    
    def to_dict(self, prediction: PricePrediction) -> Dict[str, Any]:
        """Convert prediction to dictionary."""
        return {
            'ticker': prediction.ticker,
            'direction': prediction.direction.value,
            'confidence': prediction.confidence,
            'target_price': prediction.target_price,
            'current_price': prediction.current_price,
            'change_pct': prediction.change_pct,
            'horizon_days': prediction.horizon_days,
            'regime': prediction.regime.value,
            'signal_strength': prediction.signal_strength,
            'price_path': prediction.price_path,
            'timestamps': prediction.timestamps,
            'last_updated': prediction.last_updated,
            'model_version': prediction.model_version
        }


class VolPredictor:
    """
    XGBoost-based Volatility Predictor (Stub Implementation).
    
    In production, this would use a trained XGBoost model.
    For Phase 2, uses deterministic signals based on ticker hash.
    """
    
    def __init__(self, deterministic: bool = ML_DETERMINISTIC):
        self.deterministic = deterministic
        self.model_version = "xgb_stub_v1"
        
        if self.deterministic:
            np.random.seed(DETERMINISTIC_SEED)
            logger.info("VolPredictor initialized in DETERMINISTIC mode")
        else:
            logger.info("VolPredictor initialized in RANDOM mode")
    
    def _get_deterministic_seed(self, ticker: str) -> int:
        """Generate deterministic seed from ticker."""
        hash_val = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
        return (hash_val + 1000) % 10000  # Different from price predictor
    
    def predict(
        self, 
        ticker: str,
        current_iv: Optional[float] = None,
        horizon_days: int = 7,
        historical_iv: Optional[List[float]] = None
    ) -> VolatilityPrediction:
        """
        Generate volatility prediction for ticker.
        
        Args:
            ticker: Stock ticker symbol
            current_iv: Current implied volatility (0-1 scale)
            horizon_days: Prediction horizon in days
            historical_iv: Optional historical IV data
            
        Returns:
            VolatilityPrediction dataclass with prediction results
        """
        seed = self._get_deterministic_seed(ticker) if self.deterministic else np.random.randint(0, 10000)
        np.random.seed(seed)
        
        # Default current IV if not provided
        if current_iv is None:
            current_iv = 0.20 + np.random.random() * 0.30  # 20-50% IV
        
        # Generate IV forecast
        iv_change = (np.random.random() - 0.5) * 0.1  # +/- 5% IV change
        forecast_iv = current_iv + iv_change
        forecast_iv = max(0.05, min(1.5, forecast_iv))  # Clamp to reasonable range
        
        iv_change_pct = ((forecast_iv - current_iv) / current_iv) * 100
        
        # IV Rank (percentile)
        np.random.seed(seed + 1)
        iv_rank = np.random.random() * 100  # 0-100 percentile
        
        # Vol regime classification
        if iv_rank > 70:
            vol_regime = "HIGH"
        elif iv_rank < 30:
            vol_regime = "LOW"
        else:
            vol_regime = "NORMAL"
        
        # Confidence based on IV rank (higher at extremes)
        confidence = 50 + abs(iv_rank - 50) * 0.8  # 50-90% confidence
        
        return VolatilityPrediction(
            ticker=ticker,
            current_iv=round(current_iv * 100, 1),  # Convert to percentage
            forecast_iv=round(forecast_iv * 100, 1),
            iv_change_pct=round(iv_change_pct, 1),
            iv_rank=round(iv_rank, 1),
            vol_regime=vol_regime,
            confidence=round(confidence, 1),
            horizon_days=horizon_days,
            last_updated=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            model_version=self.model_version
        )
    
    def to_dict(self, prediction: VolatilityPrediction) -> Dict[str, Any]:
        """Convert prediction to dictionary."""
        return {
            'ticker': prediction.ticker,
            'current_iv': prediction.current_iv,
            'forecast_iv': prediction.forecast_iv,
            'iv_change_pct': prediction.iv_change_pct,
            'iv_rank': prediction.iv_rank,
            'vol_regime': prediction.vol_regime,
            'confidence': prediction.confidence,
            'horizon_days': prediction.horizon_days,
            'last_updated': prediction.last_updated,
            'model_version': prediction.model_version
        }


class SmartHintGenerator:
    """
    Generates trading hints by combining price and volatility predictions.
    
    Logic: 
    - If Forecast=Bearish AND Vol=High -> Suggest "Call Credit Spread"
    - If Forecast=Bullish AND Vol=High -> Suggest "Put Credit Spread"
    - If Forecast=Neutral AND Vol=High -> Suggest "Iron Condor"
    - If Forecast=Bullish AND Vol=Low -> Suggest "Long Call"
    - If Forecast=Bearish AND Vol=Low -> Suggest "Long Put"
    """
    
    STRATEGY_MAP = {
        (SignalDirection.BEARISH, "HIGH"): {
            "strategy": "Call Credit Spread",
            "description": "Bearish outlook + High IV = Sell call spreads to collect premium",
            "icon": "📉",
            "color": "#f44336"
        },
        (SignalDirection.BULLISH, "HIGH"): {
            "strategy": "Put Credit Spread",
            "description": "Bullish outlook + High IV = Sell put spreads to collect premium",
            "icon": "📈",
            "color": "#4caf50"
        },
        (SignalDirection.NEUTRAL, "HIGH"): {
            "strategy": "Iron Condor",
            "description": "Neutral outlook + High IV = Sell both sides to capture theta decay",
            "icon": "⚖️",
            "color": "#ff9800"
        },
        (SignalDirection.BULLISH, "LOW"): {
            "strategy": "Long Call",
            "description": "Bullish outlook + Low IV = Buy calls cheaply for upside exposure",
            "icon": "🚀",
            "color": "#4caf50"
        },
        (SignalDirection.BEARISH, "LOW"): {
            "strategy": "Long Put",
            "description": "Bearish outlook + Low IV = Buy puts cheaply for downside protection",
            "icon": "🔻",
            "color": "#f44336"
        },
        (SignalDirection.NEUTRAL, "LOW"): {
            "strategy": "Long Straddle",
            "description": "Neutral but expecting movement + Low IV = Buy both sides cheaply",
            "icon": "↔️",
            "color": "#2196f3"
        },
        (SignalDirection.BULLISH, "NORMAL"): {
            "strategy": "Bull Call Spread",
            "description": "Bullish outlook + Normal IV = Defined risk bullish play",
            "icon": "📈",
            "color": "#4caf50"
        },
        (SignalDirection.BEARISH, "NORMAL"): {
            "strategy": "Bear Put Spread",
            "description": "Bearish outlook + Normal IV = Defined risk bearish play",
            "icon": "📉",
            "color": "#f44336"
        },
        (SignalDirection.NEUTRAL, "NORMAL"): {
            "strategy": "Iron Butterfly",
            "description": "Neutral outlook + Normal IV = ATM premium collection",
            "icon": "🦋",
            "color": "#9c27b0"
        }
    }
    
    def generate_hint(
        self, 
        price_pred: PricePrediction, 
        vol_pred: VolatilityPrediction
    ) -> Dict[str, Any]:
        """
        Generate smart trading hint based on combined predictions.
        
        Args:
            price_pred: Price prediction result
            vol_pred: Volatility prediction result
            
        Returns:
            Dictionary with strategy recommendation
        """
        key = (price_pred.direction, vol_pred.vol_regime)
        
        strategy_info = self.STRATEGY_MAP.get(key, {
            "strategy": "Wait for Better Setup",
            "description": "Current conditions don't favor a clear strategy",
            "icon": "⏳",
            "color": "#6b7280"
        })
        
        # Calculate overall confidence
        overall_confidence = (price_pred.confidence + vol_pred.confidence) / 2
        
        return {
            "ticker": price_pred.ticker,
            "recommended_strategy": strategy_info["strategy"],
            "description": strategy_info["description"],
            "icon": strategy_info["icon"],
            "color": strategy_info["color"],
            "price_direction": price_pred.direction.value,
            "vol_regime": vol_pred.vol_regime,
            "confidence": round(overall_confidence, 1),
            "market_regime": price_pred.regime.value,
            "last_updated": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }


# Singleton instances
_price_predictor: Optional[PricePredictor] = None
_vol_predictor: Optional[VolPredictor] = None
_hint_generator: Optional[SmartHintGenerator] = None


def get_price_predictor() -> PricePredictor:
    """Get singleton PricePredictor instance."""
    global _price_predictor
    if _price_predictor is None:
        _price_predictor = PricePredictor()
    return _price_predictor


def get_vol_predictor() -> VolPredictor:
    """Get singleton VolPredictor instance."""
    global _vol_predictor
    if _vol_predictor is None:
        _vol_predictor = VolPredictor()
    return _vol_predictor


def get_hint_generator() -> SmartHintGenerator:
    """Get singleton SmartHintGenerator instance."""
    global _hint_generator
    if _hint_generator is None:
        _hint_generator = SmartHintGenerator()
    return _hint_generator
