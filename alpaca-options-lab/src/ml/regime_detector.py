"""
Market Regime Detector - Hidden Markov Model Based

Detects market regimes using Hidden Markov Models:
- Low Volatility (VIX <15, trending up)
- High Volatility (VIX >30, choppy)
- Trending (strong directional moves)
- Mean-Reverting (oscillating around mean)
- Crisis (VIX >50, extreme moves)

Usage:
    from src.ml.regime_detector import MarketRegimeDetector
    
    detector = MarketRegimeDetector(n_regimes=5)
    detector.fit(historical_data)
    
    current_regime = detector.predict_current_regime(recent_data)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Try to import optional dependencies
try:
    from hmmlearn import hmm
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    hmm = None

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    pd = None


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class MarketRegime(Enum):
    """Market regime types"""
    LOW_VOLATILITY = auto()
    HIGH_VOLATILITY = auto()
    TRENDING = auto()
    MEAN_REVERTING = auto()
    CRISIS = auto()
    UNKNOWN = auto()


@dataclass
class RegimeInfo:
    """Information about detected regime"""
    regime: MarketRegime
    probability: float
    duration_days: int
    regime_probabilities: Dict[str, float]
    features: Dict[str, float]


@dataclass
class RegimeTransition:
    """Record of regime transition"""
    timestamp: datetime
    from_regime: MarketRegime
    to_regime: MarketRegime
    probability: float


# =============================================================================
# MARKET REGIME DETECTOR
# =============================================================================

class MarketRegimeDetector:
    """
    Detect market regimes using Hidden Markov Model.
    
    Regimes:
    1. Low Volatility (VIX <15, trending up)
    2. High Volatility (VIX >30, choppy)
    3. Trending (strong directional moves)
    4. Mean-Reverting (oscillating around mean)
    5. Crisis (VIX >50, extreme moves)
    
    Features used:
    - Returns (1d, 5d, 20d)
    - Volatility (realized and implied)
    - VIX level and change
    - Trend strength
    
    Attributes:
        n_regimes: Number of regimes to detect
        model: Trained HMM model
        fitted: Whether model has been trained
    """
    
    REGIME_NAMES = [
        "Low_Volatility",
        "High_Volatility",
        "Trending",
        "Mean_Reverting",
        "Crisis",
    ]
    
    def __init__(
        self,
        n_regimes: int = 5,
        covariance_type: str = "full",
        n_iter: int = 1000,
        random_state: int = 42,
    ):
        """
        Initialize regime detector.
        
        Args:
            n_regimes: Number of regimes (max 5)
            covariance_type: HMM covariance type
            n_iter: Training iterations
            random_state: Random seed
        """
        if not HMM_AVAILABLE:
            raise ImportError("hmmlearn is required for regime detection")
        
        self.n_regimes = min(n_regimes, 5)
        self.covariance_type = covariance_type
        self.n_iter = n_iter
        self.random_state = random_state
        
        self.model = hmm.GaussianHMM(
            n_components=self.n_regimes,
            covariance_type=covariance_type,
            n_iter=n_iter,
            random_state=random_state,
        )
        
        self.fitted = False
        self.feature_means: Optional[np.ndarray] = None
        self.feature_stds: Optional[np.ndarray] = None
        self.regime_mapping: Dict[int, MarketRegime] = {}
        self.transition_history: List[RegimeTransition] = []
        
        logger.info(
            "regime_detector_initialized",
            n_regimes=n_regimes,
            covariance_type=covariance_type,
        )
    
    def prepare_features(self, price_data: Dict[str, np.ndarray]) -> np.ndarray:
        """
        Prepare features for regime detection.
        
        Args:
            price_data: Dictionary with keys:
                - 'close': Closing prices
                - 'high': High prices (optional)
                - 'low': Low prices (optional)
                - 'vix': VIX levels
                
        Returns:
            Feature array of shape (n_samples, n_features)
        """
        close = np.array(price_data['close'])
        vix = np.array(price_data.get('vix', np.full_like(close, 20)))
        
        n = len(close)
        features = []
        
        # Returns at multiple horizons
        returns_1d = np.zeros(n)
        returns_1d[1:] = np.diff(close) / close[:-1]
        features.append(returns_1d)
        
        returns_5d = np.zeros(n)
        returns_5d[5:] = (close[5:] - close[:-5]) / close[:-5]
        features.append(returns_5d)
        
        returns_20d = np.zeros(n)
        returns_20d[20:] = (close[20:] - close[:-20]) / close[:-20]
        features.append(returns_20d)
        
        # Realized volatility (20-day)
        volatility_20d = np.zeros(n)
        for i in range(20, n):
            volatility_20d[i] = np.std(returns_1d[i-20:i]) * np.sqrt(252)
        features.append(volatility_20d)
        
        # VIX level
        features.append(vix)
        
        # VIX change
        vix_change = np.zeros(n)
        vix_change[1:] = np.diff(vix) / vix[:-1]
        features.append(vix_change)
        
        # Trend strength (20d return / 20d volatility)
        trend_strength = np.zeros(n)
        mask = volatility_20d > 0
        trend_strength[mask] = returns_20d[mask] / volatility_20d[mask]
        features.append(trend_strength)
        
        # Stack features
        feature_array = np.column_stack(features)
        
        # Handle NaN/Inf
        feature_array = np.nan_to_num(feature_array, nan=0, posinf=0, neginf=0)
        
        return feature_array
    
    def fit(self, price_data: Dict[str, np.ndarray]) -> None:
        """
        Train HMM on historical data.
        
        Args:
            price_data: Historical price data
        """
        features = self.prepare_features(price_data)
        
        # Normalize features
        self.feature_means = np.mean(features, axis=0)
        self.feature_stds = np.std(features, axis=0) + 1e-6
        features_normalized = (features - self.feature_means) / self.feature_stds
        
        # Fit HMM
        self.model.fit(features_normalized)
        self.fitted = True
        
        # Map HMM states to regime names based on characteristics
        self._map_regimes_to_states(features, features_normalized)
        
        logger.info(
            "regime_detector_trained",
            n_regimes=self.n_regimes,
            n_samples=len(features),
        )
    
    def _map_regimes_to_states(
        self,
        features: np.ndarray,
        features_normalized: np.ndarray,
    ) -> None:
        """Map HMM states to meaningful regime names"""
        # Get state sequence
        states = self.model.predict(features_normalized)
        
        # Calculate state characteristics
        state_chars = {}
        for state_idx in range(self.n_regimes):
            mask = states == state_idx
            if not np.any(mask):
                continue
            
            state_features = features[mask]
            
            # Average VIX and volatility for this state
            avg_vix = np.mean(state_features[:, 4])  # VIX column
            avg_vol = np.mean(state_features[:, 3])  # Volatility column
            avg_trend = np.mean(np.abs(state_features[:, 6]))  # Trend strength
            
            state_chars[state_idx] = {
                'avg_vix': avg_vix,
                'avg_vol': avg_vol,
                'avg_trend': avg_trend,
            }
        
        # Assign regimes based on characteristics
        self.regime_mapping = {}
        assigned = set()
        
        for state_idx, chars in sorted(
            state_chars.items(),
            key=lambda x: x[1]['avg_vix'],
            reverse=True,
        ):
            if chars['avg_vix'] > 50 and MarketRegime.CRISIS not in assigned:
                self.regime_mapping[state_idx] = MarketRegime.CRISIS
                assigned.add(MarketRegime.CRISIS)
            elif chars['avg_vix'] > 30 and MarketRegime.HIGH_VOLATILITY not in assigned:
                self.regime_mapping[state_idx] = MarketRegime.HIGH_VOLATILITY
                assigned.add(MarketRegime.HIGH_VOLATILITY)
            elif chars['avg_trend'] > 0.5 and MarketRegime.TRENDING not in assigned:
                self.regime_mapping[state_idx] = MarketRegime.TRENDING
                assigned.add(MarketRegime.TRENDING)
            elif chars['avg_vix'] < 15 and MarketRegime.LOW_VOLATILITY not in assigned:
                self.regime_mapping[state_idx] = MarketRegime.LOW_VOLATILITY
                assigned.add(MarketRegime.LOW_VOLATILITY)
            else:
                if MarketRegime.MEAN_REVERTING not in assigned:
                    self.regime_mapping[state_idx] = MarketRegime.MEAN_REVERTING
                    assigned.add(MarketRegime.MEAN_REVERTING)
                else:
                    self.regime_mapping[state_idx] = MarketRegime.UNKNOWN
        
        logger.debug("regime_mapping_complete", mapping=str(self.regime_mapping))
    
    def predict_current_regime(
        self,
        price_data: Dict[str, np.ndarray],
    ) -> MarketRegime:
        """
        Predict current market regime.
        
        Args:
            price_data: Recent price data
            
        Returns:
            Current MarketRegime
        """
        if not self.fitted:
            raise ValueError("Model not fitted - call fit() first")
        
        features = self.prepare_features(price_data)
        features_normalized = (features - self.feature_means) / self.feature_stds
        
        # Get state sequence
        states = self.model.predict(features_normalized)
        current_state = states[-1]
        
        # Map to regime
        regime = self.regime_mapping.get(current_state, MarketRegime.UNKNOWN)
        
        logger.debug(
            "regime_predicted",
            state=current_state,
            regime=regime.name,
        )
        
        return regime
    
    def get_regime_probabilities(
        self,
        price_data: Dict[str, np.ndarray],
    ) -> Dict[str, float]:
        """
        Get probability distribution over regimes.
        
        Args:
            price_data: Recent price data
            
        Returns:
            Dictionary mapping regime names to probabilities
        """
        if not self.fitted:
            raise ValueError("Model not fitted - call fit() first")
        
        features = self.prepare_features(price_data)
        features_normalized = (features - self.feature_means) / self.feature_stds
        
        # Get posterior probabilities
        _, posteriors = self.model.score_samples(features_normalized)
        current_probs = posteriors[-1]
        
        # Map to regime names
        result = {}
        for state_idx, prob in enumerate(current_probs):
            regime = self.regime_mapping.get(state_idx, MarketRegime.UNKNOWN)
            result[regime.name] = float(prob)
        
        return result
    
    def get_regime_info(
        self,
        price_data: Dict[str, np.ndarray],
    ) -> RegimeInfo:
        """
        Get detailed regime information.
        
        Args:
            price_data: Recent price data
            
        Returns:
            RegimeInfo with regime details
        """
        regime = self.predict_current_regime(price_data)
        probabilities = self.get_regime_probabilities(price_data)
        
        # Calculate duration (how long in current regime)
        features = self.prepare_features(price_data)
        features_normalized = (features - self.feature_means) / self.feature_stds
        states = self.model.predict(features_normalized)
        
        current_state = states[-1]
        duration = 1
        for i in range(len(states) - 2, -1, -1):
            if states[i] == current_state:
                duration += 1
            else:
                break
        
        # Current features
        current_features = features[-1]
        feature_dict = {
            'return_1d': float(current_features[0]),
            'return_5d': float(current_features[1]),
            'return_20d': float(current_features[2]),
            'volatility_20d': float(current_features[3]),
            'vix': float(current_features[4]),
            'vix_change': float(current_features[5]),
            'trend_strength': float(current_features[6]),
        }
        
        return RegimeInfo(
            regime=regime,
            probability=probabilities.get(regime.name, 0),
            duration_days=duration,
            regime_probabilities=probabilities,
            features=feature_dict,
        )
    
    def detect_regime_change(
        self,
        price_data: Dict[str, np.ndarray],
        lookback_days: int = 5,
    ) -> Optional[RegimeTransition]:
        """
        Detect if regime has changed recently.
        
        Args:
            price_data: Recent price data
            lookback_days: Days to look back for change
            
        Returns:
            RegimeTransition if change detected, None otherwise
        """
        if not self.fitted:
            return None
        
        features = self.prepare_features(price_data)
        features_normalized = (features - self.feature_means) / self.feature_stds
        
        if len(features_normalized) < lookback_days + 1:
            return None
        
        states = self.model.predict(features_normalized)
        
        # Check for transition in lookback period
        current_state = states[-1]
        for i in range(2, min(lookback_days + 1, len(states))):
            prev_state = states[-i]
            if prev_state != current_state:
                from_regime = self.regime_mapping.get(prev_state, MarketRegime.UNKNOWN)
                to_regime = self.regime_mapping.get(current_state, MarketRegime.UNKNOWN)
                
                _, posteriors = self.model.score_samples(features_normalized)
                prob = posteriors[-1][current_state]
                
                transition = RegimeTransition(
                    timestamp=datetime.now(),
                    from_regime=from_regime,
                    to_regime=to_regime,
                    probability=float(prob),
                )
                
                logger.info(
                    "regime_change_detected",
                    from_regime=from_regime.name,
                    to_regime=to_regime.name,
                    days_ago=i - 1,
                )
                
                return transition
        
        return None


# =============================================================================
# REGIME-ADAPTIVE STRATEGY SELECTOR
# =============================================================================

class RegimeAdaptiveStrategySelector:
    """
    Select optimal strategies based on market regime.
    
    Strategy mapping:
    - Low Volatility: Iron Condor (sell premium)
    - High Volatility: Calendar Spread (exploit vol term structure)
    - Trending: Directional butterflies
    - Mean-Reverting: Straddles/Strangles
    - Crisis: Cash / protective puts only
    
    Attributes:
        regime_detector: MarketRegimeDetector instance
        strategy_map: Mapping from regime to strategies
    """
    
    DEFAULT_STRATEGY_MAP = {
        MarketRegime.LOW_VOLATILITY: [
            "iron_condor_0dte",
            "covered_call_wheel",
            "cash_secured_put",
        ],
        MarketRegime.HIGH_VOLATILITY: [
            "calendar_spread",
            "diagonal_spread",
            "jade_lizard",
        ],
        MarketRegime.TRENDING: [
            "directional_butterfly",
            "bull_put_spread",
            "bear_call_spread",
        ],
        MarketRegime.MEAN_REVERTING: [
            "straddle",
            "strangle",
            "iron_butterfly",
        ],
        MarketRegime.CRISIS: [
            "protective_put",
            "cash",
        ],
        MarketRegime.UNKNOWN: [
            "iron_condor_0dte",
        ],
    }
    
    def __init__(
        self,
        regime_detector: MarketRegimeDetector,
        strategy_map: Optional[Dict[MarketRegime, List[str]]] = None,
    ):
        """
        Initialize strategy selector.
        
        Args:
            regime_detector: Trained regime detector
            strategy_map: Custom regime-to-strategy mapping
        """
        self.regime_detector = regime_detector
        self.strategy_map = strategy_map or self.DEFAULT_STRATEGY_MAP
        
        logger.info(
            "regime_adaptive_selector_initialized",
            n_regimes=len(self.strategy_map),
        )
    
    def select_strategies(
        self,
        price_data: Dict[str, np.ndarray],
    ) -> List[str]:
        """
        Select active strategies based on current regime.
        
        Args:
            price_data: Recent price data
            
        Returns:
            List of recommended strategy names
        """
        current_regime = self.regime_detector.predict_current_regime(price_data)
        strategies = self.strategy_map.get(current_regime, ["iron_condor_0dte"])
        
        logger.info(
            "strategies_selected_for_regime",
            regime=current_regime.name,
            strategies=strategies,
        )
        
        return strategies
    
    def get_strategy_allocation(
        self,
        price_data: Dict[str, np.ndarray],
    ) -> Dict[str, float]:
        """
        Get strategy allocation weights based on regime probabilities.
        
        Args:
            price_data: Recent price data
            
        Returns:
            Dictionary mapping strategy names to weights (0-1)
        """
        regime_probs = self.regime_detector.get_regime_probabilities(price_data)
        
        allocation: Dict[str, float] = {}
        
        for regime_name, prob in regime_probs.items():
            try:
                regime = MarketRegime[regime_name]
            except KeyError:
                continue
            
            strategies = self.strategy_map.get(regime, [])
            
            if strategies:
                weight_per_strategy = prob / len(strategies)
                for strategy in strategies:
                    allocation[strategy] = allocation.get(strategy, 0) + weight_per_strategy
        
        # Normalize
        total = sum(allocation.values())
        if total > 0:
            allocation = {k: v / total for k, v in allocation.items()}
        
        return allocation
    
    def should_trade(
        self,
        price_data: Dict[str, np.ndarray],
        confidence_threshold: float = 0.6,
    ) -> Tuple[bool, str]:
        """
        Determine if trading is recommended in current regime.
        
        Args:
            price_data: Recent price data
            confidence_threshold: Minimum regime probability
            
        Returns:
            (should_trade, reason)
        """
        regime_info = self.regime_detector.get_regime_info(price_data)
        
        # Don't trade during crisis
        if regime_info.regime == MarketRegime.CRISIS:
            return False, "Crisis regime detected - recommend staying in cash"
        
        # Don't trade with low confidence
        if regime_info.probability < confidence_threshold:
            return False, f"Regime confidence too low: {regime_info.probability:.1%}"
        
        # Don't trade during regime transitions
        transition = self.regime_detector.detect_regime_change(price_data)
        if transition and regime_info.duration_days < 2:
            return False, f"Recent regime change to {regime_info.regime.name} - wait for confirmation"
        
        return True, f"Trading recommended in {regime_info.regime.name} regime"
    
    def get_regime_summary(
        self,
        price_data: Dict[str, np.ndarray],
    ) -> Dict[str, Any]:
        """
        Get comprehensive regime analysis summary.
        
        Returns:
            Dictionary with regime information
        """
        regime_info = self.regime_detector.get_regime_info(price_data)
        should_trade, trade_reason = self.should_trade(price_data)
        strategies = self.select_strategies(price_data)
        allocation = self.get_strategy_allocation(price_data)
        
        return {
            'current_regime': regime_info.regime.name,
            'regime_probability': regime_info.probability,
            'duration_days': regime_info.duration_days,
            'all_probabilities': regime_info.regime_probabilities,
            'features': regime_info.features,
            'should_trade': should_trade,
            'trade_reason': trade_reason,
            'recommended_strategies': strategies,
            'strategy_allocation': allocation,
        }
