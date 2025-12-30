"""
Regime Detection Engine - Phase 5 Market Intelligence
======================================================

Implements market regime detection using two methods:
- Statistical: Gaussian HMM (Hidden Markov Model) for 3-state regime detection
- Clustering: K-Means on rolling volatility & returns

Output: DataFrame with 'regime' column (0=Bear, 1=Sideways, 2=Bull)

Author: Agent-P5
Date: 2025-12-29
"""

import os
import logging
import numpy as np
import pandas as pd
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Set deterministic mode for reproducibility
if os.getenv('PHASE5_DETERMINISTIC', '0') == '1':
    np.random.seed(42)
    logger.info("✅ Phase 5 deterministic mode enabled for Regime Engine")

# Import dependencies with graceful fallback
try:
    from hmmlearn.hmm import GaussianHMM
    HMM_AVAILABLE = True
except ImportError:
    HMM_AVAILABLE = False
    logger.warning("hmmlearn not available - HMM regime detection disabled")

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available - K-Means clustering disabled")


# Regime labels and colors
REGIME_LABELS = {
    0: 'Bear',
    1: 'Sideways',
    2: 'Bull'
}

REGIME_COLORS = {
    0: 'rgba(220, 53, 69, 0.3)',   # Red - Bear
    1: 'rgba(108, 117, 125, 0.3)', # Gray - Sideways
    2: 'rgba(40, 167, 69, 0.3)'    # Green - Bull
}

REGIME_SOLID_COLORS = {
    0: '#dc3545',  # Red - Bear
    1: '#6c757d',  # Gray - Sideways
    2: '#28a745'   # Green - Bull
}


class RegimeDetector:
    """
    Market Regime Detection using HMM and K-Means clustering.
    
    Detects three market regimes:
    - Bear (0): Negative returns, high volatility
    - Sideways (1): Low returns, low volatility
    - Bull (2): Positive returns, moderate volatility
    """
    
    def __init__(
        self,
        method: str = 'hmm',
        n_regimes: int = 3,
        lookback_volatility: int = 20,
        lookback_returns: int = 5
    ):
        """
        Initialize RegimeDetector.
        
        Args:
            method: Detection method ('hmm' or 'kmeans')
            n_regimes: Number of regimes to detect
            lookback_volatility: Window for rolling volatility
            lookback_returns: Window for rolling returns
        """
        self.method = method.lower()
        self.n_regimes = n_regimes
        self.lookback_volatility = lookback_volatility
        self.lookback_returns = lookback_returns
        
        # Model storage
        self.model = None
        self.scaler = None
        self._fitted = False
        
        # Validate dependencies
        if self.method == 'hmm' and not HMM_AVAILABLE:
            logger.warning("HMM not available, falling back to kmeans")
            self.method = 'kmeans'
        
        if self.method == 'kmeans' and not SKLEARN_AVAILABLE:
            raise ImportError("scikit-learn required for K-Means clustering")
    
    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for regime detection.
        
        Args:
            df: DataFrame with 'Close' column
            
        Returns:
            DataFrame with features
        """
        features = pd.DataFrame(index=df.index)
        
        # Daily returns
        features['returns'] = df['Close'].pct_change()
        
        # Rolling volatility (annualized)
        features['volatility'] = features['returns'].rolling(
            window=self.lookback_volatility
        ).std() * np.sqrt(252)
        
        # Rolling returns (cumulative)
        features['rolling_returns'] = features['returns'].rolling(
            window=self.lookback_returns
        ).sum()
        
        # Momentum indicator
        features['momentum'] = df['Close'].pct_change(periods=self.lookback_returns)
        
        # Volume change if available
        if 'Volume' in df.columns:
            features['volume_change'] = df['Volume'].pct_change()
        
        # Drop NaN rows
        features = features.dropna()
        
        return features
    
    def _order_regimes(self, regimes: np.ndarray, features: pd.DataFrame) -> np.ndarray:
        """
        Reorder regimes so that:
        - 0 = Bear (lowest average returns)
        - 1 = Sideways (middle)
        - 2 = Bull (highest average returns)
        """
        regime_returns = {}
        for r in range(self.n_regimes):
            mask = regimes == r
            if mask.sum() > 0:
                regime_returns[r] = features.loc[mask, 'returns'].mean()
            else:
                regime_returns[r] = 0
        
        # Sort by returns
        sorted_regimes = sorted(regime_returns.keys(), key=lambda x: regime_returns[x])
        
        # Create mapping
        mapping = {old: new for new, old in enumerate(sorted_regimes)}
        
        # Apply mapping
        ordered = np.array([mapping[r] for r in regimes])
        
        return ordered
    
    def fit_predict(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Fit model and predict regimes.
        
        Args:
            df: DataFrame with 'Close' column (and optionally 'Volume')
            
        Returns:
            Original DataFrame with 'regime' column added
        """
        if 'Close' not in df.columns:
            raise ValueError("DataFrame must have 'Close' column")
        
        # Prepare features
        features = self._prepare_features(df)
        
        if len(features) < 30:
            logger.warning("Insufficient data for regime detection")
            result = df.copy()
            result['regime'] = 1  # Default to sideways
            return result
        
        # Select feature columns for model
        feature_cols = ['returns', 'volatility', 'rolling_returns']
        if 'volume_change' in features.columns:
            feature_cols.append('volume_change')
        
        X = features[feature_cols].values
        
        # Scale features
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)
        
        # Detect regimes based on method
        if self.method == 'hmm':
            regimes = self._fit_hmm(X_scaled)
        else:
            regimes = self._fit_kmeans(X_scaled)
        
        # Reorder regimes by returns
        ordered_regimes = self._order_regimes(regimes, features)
        
        # Create result DataFrame
        result = df.copy()
        result['regime'] = np.nan
        result.loc[features.index, 'regime'] = ordered_regimes
        
        # Forward fill first NaN values
        result['regime'] = result['regime'].ffill().fillna(1)
        result['regime'] = result['regime'].astype(int)
        
        self._fitted = True
        logger.info(f"Regime detection complete using {self.method.upper()}")
        
        return result
    
    def _fit_hmm(self, X: np.ndarray) -> np.ndarray:
        """Fit Gaussian HMM and predict regimes."""
        self.model = GaussianHMM(
            n_components=self.n_regimes,
            covariance_type='full',
            n_iter=100,
            random_state=42 if os.getenv('PHASE5_DETERMINISTIC', '0') == '1' else None
        )
        
        self.model.fit(X)
        regimes = self.model.predict(X)
        
        logger.info(f"HMM converged: {self.model.monitor_.converged}")
        
        return regimes
    
    def _fit_kmeans(self, X: np.ndarray) -> np.ndarray:
        """Fit K-Means clustering and predict regimes."""
        self.model = KMeans(
            n_clusters=self.n_regimes,
            random_state=42 if os.getenv('PHASE5_DETERMINISTIC', '0') == '1' else None,
            n_init=10
        )
        
        regimes = self.model.fit_predict(X)
        
        logger.info(f"K-Means inertia: {self.model.inertia_:.4f}")
        
        return regimes
    
    def get_regime_stats(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get statistics for each regime.
        
        Args:
            df: DataFrame with 'regime' and 'Close' columns
            
        Returns:
            Dict with regime statistics
        """
        if 'regime' not in df.columns:
            return {}
        
        stats = {}
        returns = df['Close'].pct_change()
        
        for regime in range(self.n_regimes):
            mask = df['regime'] == regime
            regime_returns = returns[mask]
            
            stats[REGIME_LABELS[regime]] = {
                'count': int(mask.sum()),
                'pct_time': float(mask.sum() / len(df) * 100),
                'avg_return': float(regime_returns.mean() * 100) if len(regime_returns) > 0 else 0,
                'volatility': float(regime_returns.std() * np.sqrt(252) * 100) if len(regime_returns) > 0 else 0,
                'color': REGIME_SOLID_COLORS[regime]
            }
        
        return stats
    
    def get_current_regime(self, df: pd.DataFrame) -> Tuple[int, str, str]:
        """
        Get the current (latest) regime.
        
        Returns:
            Tuple of (regime_id, regime_label, regime_color)
        """
        if 'regime' not in df.columns or len(df) == 0:
            return 1, 'Sideways', REGIME_SOLID_COLORS[1]
        
        current = int(df['regime'].iloc[-1])
        return current, REGIME_LABELS[current], REGIME_SOLID_COLORS[current]


def detect_regimes(
    ticker: str,
    method: str = 'hmm',
    lookback_days: int = 365
) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """
    Convenience function to detect regimes for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        method: 'hmm' or 'kmeans'
        lookback_days: Historical data lookback
        
    Returns:
        Tuple of (DataFrame with regimes, statistics dict)
    """
    try:
        # Fetch data
        import yfinance as yf
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days + 30)
        
        ticker_obj = yf.Ticker(ticker)
        df = ticker_obj.history(start=start_date, end=end_date)
        
        if df.empty:
            logger.error(f"No data for {ticker}")
            return None, {}
        
        # Detect regimes
        detector = RegimeDetector(method=method)
        result = detector.fit_predict(df)
        
        # Get stats
        stats = detector.get_regime_stats(result)
        current_regime = detector.get_current_regime(result)
        
        stats['current'] = {
            'regime_id': current_regime[0],
            'label': current_regime[1],
            'color': current_regime[2]
        }
        stats['ticker'] = ticker
        stats['method'] = method
        
        return result, stats
        
    except Exception as e:
        logger.error(f"Regime detection error: {e}")
        return None, {'error': str(e)}


def is_regime_detection_available() -> bool:
    """Check if regime detection is available."""
    return HMM_AVAILABLE or SKLEARN_AVAILABLE


# Export
__all__ = [
    'RegimeDetector',
    'detect_regimes',
    'is_regime_detection_available',
    'REGIME_LABELS',
    'REGIME_COLORS',
    'REGIME_SOLID_COLORS'
]
