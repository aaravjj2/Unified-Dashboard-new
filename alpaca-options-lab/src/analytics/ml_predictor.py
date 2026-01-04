"""
Alpaca Options Lab - ML Predictors

Machine learning models for options trading:
- Volatility prediction (IV forecasting)
- Direction prediction (price movement)
- Regime detection
- Feature engineering
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, date, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class PredictionHorizon(Enum):
    """Prediction time horizon."""
    INTRADAY = "intraday"  # Same day
    DAILY = "daily"        # Next day
    WEEKLY = "weekly"      # 5 trading days
    MONTHLY = "monthly"    # 21 trading days


@dataclass
class Prediction:
    """ML model prediction."""
    model_name: str
    target: str
    horizon: PredictionHorizon
    
    # Prediction
    value: float
    confidence: float  # 0-1
    
    # Probability distribution (if available)
    probabilities: Dict[str, float] = field(default_factory=dict)
    
    # Metadata
    features_used: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class FeatureSet:
    """Feature set for ML models."""
    timestamp: datetime
    symbol: str
    
    # Price features
    price: float
    returns_1d: float = 0.0
    returns_5d: float = 0.0
    returns_20d: float = 0.0
    
    # Volatility features
    realized_vol_5d: float = 0.0
    realized_vol_20d: float = 0.0
    iv_atm: float = 0.0
    iv_percentile: float = 0.0  # IV rank
    
    # Term structure
    iv_slope: float = 0.0
    vix: float = 0.0
    vix_term_structure: float = 0.0
    
    # Technical
    rsi_14: float = 0.0
    macd: float = 0.0
    bollinger_position: float = 0.0
    
    # Volume/flow
    volume_ratio: float = 0.0
    put_call_ratio: float = 0.0
    
    def to_array(self) -> np.ndarray:
        """Convert to numpy array for model input."""
        return np.array([
            self.price,
            self.returns_1d,
            self.returns_5d,
            self.returns_20d,
            self.realized_vol_5d,
            self.realized_vol_20d,
            self.iv_atm,
            self.iv_percentile,
            self.iv_slope,
            self.vix,
            self.vix_term_structure,
            self.rsi_14,
            self.macd,
            self.bollinger_position,
            self.volume_ratio,
            self.put_call_ratio,
        ])
    
    @staticmethod
    def feature_names() -> List[str]:
        """Get feature names in order."""
        return [
            "price", "returns_1d", "returns_5d", "returns_20d",
            "realized_vol_5d", "realized_vol_20d", "iv_atm", "iv_percentile",
            "iv_slope", "vix", "vix_term_structure",
            "rsi_14", "macd", "bollinger_position",
            "volume_ratio", "put_call_ratio",
        ]


class FeatureEngine:
    """
    Feature engineering for ML models.
    
    Calculates technical indicators and features from raw market data.
    """
    
    def __init__(self):
        # Historical data for calculations
        self._price_history: Dict[str, List[Tuple[datetime, float]]] = {}
        self._volume_history: Dict[str, List[Tuple[datetime, float]]] = {}
        self._iv_history: Dict[str, List[Tuple[datetime, float]]] = {}
    
    def add_price(self, symbol: str, timestamp: datetime, price: float) -> None:
        """Add price observation."""
        if symbol not in self._price_history:
            self._price_history[symbol] = []
        self._price_history[symbol].append((timestamp, price))
        
        # Keep last 252 days (1 year)
        if len(self._price_history[symbol]) > 252:
            self._price_history[symbol] = self._price_history[symbol][-252:]
    
    def add_volume(self, symbol: str, timestamp: datetime, volume: float) -> None:
        """Add volume observation."""
        if symbol not in self._volume_history:
            self._volume_history[symbol] = []
        self._volume_history[symbol].append((timestamp, volume))
        
        if len(self._volume_history[symbol]) > 60:
            self._volume_history[symbol] = self._volume_history[symbol][-60:]
    
    def add_iv(self, symbol: str, timestamp: datetime, iv: float) -> None:
        """Add IV observation."""
        if symbol not in self._iv_history:
            self._iv_history[symbol] = []
        self._iv_history[symbol].append((timestamp, iv))
        
        if len(self._iv_history[symbol]) > 252:
            self._iv_history[symbol] = self._iv_history[symbol][-252:]
    
    def calculate_features(
        self,
        symbol: str,
        current_price: float,
        current_iv: float = 0.0,
        vix: float = 0.0,
    ) -> FeatureSet:
        """
        Calculate feature set for a symbol.
        
        Returns:
            FeatureSet with all computed features
        """
        timestamp = datetime.now(timezone.utc)
        
        # Get price history
        prices = [p for _, p in self._price_history.get(symbol, [])]
        
        # Returns
        returns_1d = self._calculate_return(prices, 1)
        returns_5d = self._calculate_return(prices, 5)
        returns_20d = self._calculate_return(prices, 20)
        
        # Realized volatility
        rv_5d = self._realized_vol(prices, 5)
        rv_20d = self._realized_vol(prices, 20)
        
        # IV rank (percentile over 252 days)
        ivs = [iv for _, iv in self._iv_history.get(symbol, [])]
        iv_percentile = self._percentile_rank(ivs, current_iv) if ivs else 0.5
        
        # Technical indicators
        rsi = self._calculate_rsi(prices, 14)
        macd = self._calculate_macd(prices)
        bb_pos = self._bollinger_position(prices, current_price)
        
        # Volume ratio
        volumes = [v for _, v in self._volume_history.get(symbol, [])]
        vol_ratio = self._volume_ratio(volumes) if volumes else 1.0
        
        return FeatureSet(
            timestamp=timestamp,
            symbol=symbol,
            price=current_price,
            returns_1d=returns_1d,
            returns_5d=returns_5d,
            returns_20d=returns_20d,
            realized_vol_5d=rv_5d,
            realized_vol_20d=rv_20d,
            iv_atm=current_iv,
            iv_percentile=iv_percentile,
            iv_slope=0.0,  # Requires term structure data
            vix=vix,
            vix_term_structure=0.0,
            rsi_14=rsi,
            macd=macd,
            bollinger_position=bb_pos,
            volume_ratio=vol_ratio,
            put_call_ratio=1.0,  # Requires options flow data
        )
    
    def _calculate_return(self, prices: List[float], days: int) -> float:
        """Calculate return over N days."""
        if len(prices) < days + 1:
            return 0.0
        return (prices[-1] / prices[-days - 1]) - 1
    
    def _realized_vol(self, prices: List[float], days: int) -> float:
        """Calculate realized volatility."""
        if len(prices) < days + 1:
            return 0.0
        
        returns = np.diff(np.log(prices[-days - 1:]))
        return float(np.std(returns) * np.sqrt(252))
    
    def _percentile_rank(self, values: List[float], current: float) -> float:
        """Calculate percentile rank of current value."""
        if not values:
            return 0.5
        below = sum(1 for v in values if v < current)
        return below / len(values)
    
    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate RSI."""
        if len(prices) < period + 1:
            return 50.0
        
        deltas = np.diff(prices[-period - 1:])
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains)
        avg_loss = np.mean(losses)
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
    
    def _calculate_macd(self, prices: List[float]) -> float:
        """Calculate MACD."""
        if len(prices) < 26:
            return 0.0
        
        prices_arr = np.array(prices)
        ema12 = self._ema(prices_arr, 12)
        ema26 = self._ema(prices_arr, 26)
        
        return ema12 - ema26
    
    def _ema(self, data: np.ndarray, period: int) -> float:
        """Calculate EMA."""
        if len(data) < period:
            return float(np.mean(data))
        
        alpha = 2 / (period + 1)
        ema = data[-period]
        
        for price in data[-period + 1:]:
            ema = alpha * price + (1 - alpha) * ema
        
        return float(ema)
    
    def _bollinger_position(
        self,
        prices: List[float],
        current: float,
        period: int = 20,
    ) -> float:
        """
        Calculate position within Bollinger Bands.
        
        Returns: -1 (below lower) to +1 (above upper), 0 at mean
        """
        if len(prices) < period:
            return 0.0
        
        recent = prices[-period:]
        mean = np.mean(recent)
        std = np.std(recent)
        
        if std == 0:
            return 0.0
        
        # Position in terms of standard deviations from mean
        z_score = (current - mean) / std
        
        # Normalize to -1 to 1 (clipping at 2 std)
        return max(-1, min(1, z_score / 2))
    
    def _volume_ratio(self, volumes: List[float]) -> float:
        """Calculate volume ratio (current vs 20-day average)."""
        if len(volumes) < 2:
            return 1.0
        
        avg_volume = np.mean(volumes[:-1]) if len(volumes) > 1 else volumes[0]
        if avg_volume == 0:
            return 1.0
        
        return volumes[-1] / avg_volume


class BasePredictor(ABC):
    """Base class for ML predictors."""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._is_trained = False
    
    @abstractmethod
    def train(self, features: List[FeatureSet], targets: List[float]) -> None:
        """Train the model."""
        pass
    
    @abstractmethod
    def predict(self, features: FeatureSet) -> Prediction:
        """Make a prediction."""
        pass
    
    @property
    def is_trained(self) -> bool:
        return self._is_trained


class VolatilityPredictor(BasePredictor):
    """
    Predicts future implied volatility.
    
    Uses historical features to forecast IV changes.
    """
    
    def __init__(
        self,
        horizon: PredictionHorizon = PredictionHorizon.DAILY,
    ):
        super().__init__("volatility_predictor")
        self.horizon = horizon
        
        # Simple model: weighted mean reversion
        self._mean_iv: Dict[str, float] = {}
        self._iv_speed: float = 0.1  # Mean reversion speed
        
        # For more sophisticated models, would use sklearn/torch
        self._model = None
    
    def train(
        self,
        features: List[FeatureSet],
        targets: List[float],  # Future IV values
    ) -> None:
        """
        Train volatility prediction model.
        
        Simple implementation: estimate mean IV and reversion speed.
        """
        if not features:
            return
        
        # Group by symbol
        symbol_data: Dict[str, List[Tuple[float, float]]] = {}
        for f, t in zip(features, targets):
            if f.symbol not in symbol_data:
                symbol_data[f.symbol] = []
            symbol_data[f.symbol].append((f.iv_atm, t))
        
        # Calculate mean IV per symbol
        for symbol, data in symbol_data.items():
            ivs = [iv for iv, _ in data]
            self._mean_iv[symbol] = np.mean(ivs)
        
        # Estimate reversion speed from IV changes
        all_changes = []
        for data in symbol_data.values():
            for i in range(len(data) - 1):
                current_iv, next_iv = data[i][0], data[i + 1][0]
                if current_iv > 0:
                    change = (next_iv - current_iv) / current_iv
                    all_changes.append(change)
        
        if all_changes:
            self._iv_speed = min(0.5, abs(np.mean(all_changes)))
        
        self._is_trained = True
        logger.info(f"Volatility predictor trained on {len(features)} samples")
    
    def predict(self, features: FeatureSet) -> Prediction:
        """
        Predict future IV.
        
        Uses mean reversion model with IV percentile adjustment.
        """
        current_iv = features.iv_atm
        mean_iv = self._mean_iv.get(features.symbol, current_iv)
        
        # Mean reversion prediction
        # IV tends to revert to mean, faster when at extremes
        percentile_factor = 1 + abs(features.iv_percentile - 0.5)
        
        predicted_change = self._iv_speed * percentile_factor * (mean_iv - current_iv)
        predicted_iv = current_iv + predicted_change
        
        # Confidence based on IV percentile (more confident at extremes)
        confidence = 0.5 + 0.4 * abs(features.iv_percentile - 0.5)
        
        return Prediction(
            model_name=self.model_name,
            target="implied_volatility",
            horizon=self.horizon,
            value=predicted_iv,
            confidence=confidence,
            probabilities={
                "iv_up": 0.5 + 0.5 * np.sign(predicted_change) * confidence,
                "iv_down": 0.5 - 0.5 * np.sign(predicted_change) * confidence,
            },
            features_used=["iv_atm", "iv_percentile", "mean_iv"],
        )


class DirectionPredictor(BasePredictor):
    """
    Predicts price direction.
    
    Binary classification: up or down.
    """
    
    def __init__(
        self,
        horizon: PredictionHorizon = PredictionHorizon.DAILY,
    ):
        super().__init__("direction_predictor")
        self.horizon = horizon
        
        # Feature weights (simple linear model)
        self._weights: np.ndarray = np.zeros(16)
        self._bias: float = 0.0
    
    def train(
        self,
        features: List[FeatureSet],
        targets: List[float],  # +1 for up, -1 for down
    ) -> None:
        """
        Train direction prediction model.
        
        Simple implementation: learn feature weights via gradient descent.
        """
        if len(features) < 10:
            self._is_trained = True
            return
        
        X = np.array([f.to_array() for f in features])
        y = np.array(targets)
        
        # Normalize features
        X_mean = np.mean(X, axis=0)
        X_std = np.std(X, axis=0) + 1e-8
        X_norm = (X - X_mean) / X_std
        
        # Simple gradient descent
        lr = 0.01
        n_iterations = 100
        
        weights = np.zeros(X_norm.shape[1])
        bias = 0.0
        
        for _ in range(n_iterations):
            # Forward pass
            logits = X_norm @ weights + bias
            preds = np.tanh(logits)
            
            # Backward pass
            errors = preds - y
            grad_w = X_norm.T @ errors / len(y)
            grad_b = np.mean(errors)
            
            # Update
            weights -= lr * grad_w
            bias -= lr * grad_b
        
        self._weights = weights
        self._bias = bias
        self._feature_mean = X_mean
        self._feature_std = X_std
        
        self._is_trained = True
        logger.info(f"Direction predictor trained on {len(features)} samples")
    
    def predict(self, features: FeatureSet) -> Prediction:
        """
        Predict price direction.
        
        Returns probability of up move.
        """
        if not self._is_trained:
            return Prediction(
                model_name=self.model_name,
                target="direction",
                horizon=self.horizon,
                value=0.5,
                confidence=0.0,
                probabilities={"up": 0.5, "down": 0.5},
            )
        
        X = features.to_array()
        
        # Normalize
        if hasattr(self, '_feature_mean'):
            X_norm = (X - self._feature_mean) / self._feature_std
        else:
            X_norm = X
        
        # Predict
        logit = np.dot(X_norm, self._weights) + self._bias
        prob_up = (np.tanh(logit) + 1) / 2  # Map to [0, 1]
        
        # Confidence = distance from 0.5
        confidence = abs(prob_up - 0.5) * 2
        
        return Prediction(
            model_name=self.model_name,
            target="direction",
            horizon=self.horizon,
            value=1 if prob_up > 0.5 else -1,
            confidence=confidence,
            probabilities={
                "up": float(prob_up),
                "down": float(1 - prob_up),
            },
            features_used=FeatureSet.feature_names(),
        )
