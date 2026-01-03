"""
Pattern Recognition Engine - Phase 1: Hybrid Sentiment Engine
=============================================================
Detects common chart patterns using scipy signal processing.

Implemented Patterns:
- Double Bottom: Two lows at similar price levels with a peak between
- Bull Flag: Strong upward move followed by consolidation channel
- Double Top: Two highs at similar price levels with a trough between
- Support/Resistance: Key price levels with multiple touches

Performance:
- All detections run in O(n) time complexity
- Designed for real-time use with streaming data
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum

import numpy as np
import pandas as pd

try:
    from scipy.signal import find_peaks, argrelextrema
    from scipy.stats import linregress
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    find_peaks = None
    argrelextrema = None
    linregress = None

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES & ENUMS
# =============================================================================

class PatternType(Enum):
    """Types of chart patterns."""
    DOUBLE_BOTTOM = "Double Bottom"
    DOUBLE_TOP = "Double Top"
    BULL_FLAG = "Bull Flag"
    BEAR_FLAG = "Bear Flag"
    HEAD_SHOULDERS = "Head & Shoulders"
    INV_HEAD_SHOULDERS = "Inverse Head & Shoulders"
    ASCENDING_TRIANGLE = "Ascending Triangle"
    DESCENDING_TRIANGLE = "Descending Triangle"
    SUPPORT_LEVEL = "Support Level"
    RESISTANCE_LEVEL = "Resistance Level"
    NO_PATTERN = "No Pattern"


class PatternSignal(Enum):
    """Trading signal from pattern."""
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"


@dataclass
class PatternResult:
    """Result from pattern detection."""
    pattern: str                    # Pattern name
    pattern_type: PatternType       # Enum type
    confidence: float               # 0.0 to 1.0
    signal: PatternSignal           # Trading signal
    start_idx: int = 0              # Start index of pattern in data
    end_idx: int = 0                # End index of pattern
    key_prices: List[float] = field(default_factory=list)  # Key price points
    description: str = ""           # Human-readable description
    target_price: Optional[float] = None  # Projected target if pattern completes
    stop_loss: Optional[float] = None     # Suggested stop loss
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'pattern': self.pattern,
            'confidence': round(self.confidence, 2),
            'signal': self.signal.value,
            'start_idx': self.start_idx,
            'end_idx': self.end_idx,
            'key_prices': [round(p, 2) for p in self.key_prices],
            'description': self.description,
            'target_price': round(self.target_price, 2) if self.target_price else None,
            'stop_loss': round(self.stop_loss, 2) if self.stop_loss else None,
            'timestamp': self.timestamp.isoformat()
        }


# =============================================================================
# PATTERN DETECTOR CLASS
# =============================================================================

class PatternDetector:
    """
    Detects chart patterns in price data using signal processing.
    
    Usage:
        detector = PatternDetector()
        
        # With pandas Series
        prices = pd.Series([100, 98, 95, 97, 94, 96, 99, 102])
        patterns = detector.detect_patterns(prices)
        
        # With numpy array
        prices = np.array([100, 98, 95, 97, 94, 96, 99, 102])
        patterns = detector.detect_patterns(prices)
        
        for p in patterns:
            print(f"{p.pattern}: {p.confidence:.0%} confidence ({p.signal.value})")
    """
    
    # Default parameters for pattern detection
    DEFAULT_PARAMS = {
        'min_pattern_bars': 10,      # Minimum bars for pattern
        'max_pattern_bars': 100,     # Maximum bars for pattern
        'price_tolerance': 0.02,     # 2% tolerance for price matching
        'min_confidence': 0.6,       # Minimum confidence to report
        'peak_prominence': 0.01,     # Minimum prominence for peaks (1%)
        'peak_distance': 5,          # Minimum distance between peaks
    }
    
    def __init__(self, params: Optional[Dict] = None):
        """
        Initialize pattern detector.
        
        Args:
            params: Override default parameters
        """
        self.params = {**self.DEFAULT_PARAMS, **(params or {})}
        
        if not SCIPY_AVAILABLE:
            logger.warning("scipy not available - pattern detection will use fallback methods")
    
    def detect_patterns(self, prices: pd.Series, 
                       detect_all: bool = True) -> List[PatternResult]:
        """
        Detect all patterns in price data.
        
        Args:
            prices: Price series (pandas Series or numpy array)
            detect_all: If True, detect all patterns. If False, return first found.
            
        Returns:
            List of PatternResult objects, sorted by confidence (highest first)
        """
        # Convert to numpy array
        if isinstance(prices, pd.Series):
            price_array = prices.values.astype(float)
        else:
            price_array = np.array(prices, dtype=float)
        
        if len(price_array) < self.params['min_pattern_bars']:
            return [PatternResult(
                pattern="Insufficient Data",
                pattern_type=PatternType.NO_PATTERN,
                confidence=0.0,
                signal=PatternSignal.NEUTRAL,
                description=f"Need at least {self.params['min_pattern_bars']} bars"
            )]
        
        patterns = []
        
        # Detect each pattern type
        double_bottom = self._detect_double_bottom(price_array)
        if double_bottom and double_bottom.confidence >= self.params['min_confidence']:
            patterns.append(double_bottom)
            if not detect_all:
                return patterns
        
        double_top = self._detect_double_top(price_array)
        if double_top and double_top.confidence >= self.params['min_confidence']:
            patterns.append(double_top)
            if not detect_all:
                return patterns
        
        bull_flag = self._detect_bull_flag(price_array)
        if bull_flag and bull_flag.confidence >= self.params['min_confidence']:
            patterns.append(bull_flag)
            if not detect_all:
                return patterns
        
        bear_flag = self._detect_bear_flag(price_array)
        if bear_flag and bear_flag.confidence >= self.params['min_confidence']:
            patterns.append(bear_flag)
            if not detect_all:
                return patterns
        
        # Sort by confidence
        patterns.sort(key=lambda x: x.confidence, reverse=True)
        
        # If no patterns found, return "No Pattern"
        if not patterns:
            return [PatternResult(
                pattern="No Pattern Detected",
                pattern_type=PatternType.NO_PATTERN,
                confidence=0.0,
                signal=PatternSignal.NEUTRAL,
                description="No recognizable patterns in the data"
            )]
        
        return patterns
    
    def _detect_double_bottom(self, prices: np.ndarray) -> Optional[PatternResult]:
        """
        Detect double bottom pattern.
        
        Double bottom: Two lows at similar price levels with a peak between them.
        Signal: Bullish reversal
        """
        if not SCIPY_AVAILABLE:
            return self._detect_double_bottom_fallback(prices)
        
        try:
            # Find local minima (bottoms)
            prominence = np.std(prices) * self.params['peak_prominence'] * 10
            distance = self.params['peak_distance']
            
            # Invert prices to find minima as peaks
            inverted = -prices
            bottoms, properties = find_peaks(inverted, 
                                            prominence=prominence,
                                            distance=distance)
            
            if len(bottoms) < 2:
                return None
            
            # Check last two bottoms
            idx1, idx2 = bottoms[-2], bottoms[-1]
            price1, price2 = prices[idx1], prices[idx2]
            
            # Prices should be within tolerance
            tolerance = self.params['price_tolerance']
            avg_price = (price1 + price2) / 2
            price_diff = abs(price1 - price2) / avg_price
            
            if price_diff > tolerance:
                return None
            
            # Find peak between bottoms
            between_prices = prices[idx1:idx2+1]
            peak_idx_local = np.argmax(between_prices)
            peak_idx = idx1 + peak_idx_local
            peak_price = prices[peak_idx]
            
            # Peak should be significantly higher than bottoms
            peak_diff = (peak_price - avg_price) / avg_price
            if peak_diff < 0.02:  # At least 2% higher
                return None
            
            # Calculate confidence based on symmetry and peak height
            symmetry = 1 - price_diff / tolerance
            height_factor = min(1.0, peak_diff / 0.05)  # Max confidence at 5% height
            confidence = (symmetry * 0.5 + height_factor * 0.5)
            confidence = min(0.95, max(0.6, confidence))
            
            # Target price: measure from neckline
            target_price = peak_price + (peak_price - avg_price)
            stop_loss = avg_price * 0.98  # 2% below bottom
            
            return PatternResult(
                pattern="Double Bottom",
                pattern_type=PatternType.DOUBLE_BOTTOM,
                confidence=confidence,
                signal=PatternSignal.BULLISH,
                start_idx=int(idx1),
                end_idx=int(idx2),
                key_prices=[float(price1), float(peak_price), float(price2)],
                description=f"Double bottom at ${avg_price:.2f} with neckline at ${peak_price:.2f}",
                target_price=float(target_price),
                stop_loss=float(stop_loss)
            )
        
        except Exception as e:
            logger.debug(f"Double bottom detection error: {e}")
            return None
    
    def _detect_double_bottom_fallback(self, prices: np.ndarray) -> Optional[PatternResult]:
        """Fallback double bottom detection without scipy."""
        n = len(prices)
        if n < 20:
            return None
        
        # Simple approach: find two lowest points in last 50% of data
        half = n // 2
        recent_prices = prices[half:]
        
        # Find local minima using simple comparison
        minima_indices = []
        for i in range(2, len(recent_prices) - 2):
            if (recent_prices[i] < recent_prices[i-1] and 
                recent_prices[i] < recent_prices[i-2] and
                recent_prices[i] < recent_prices[i+1] and
                recent_prices[i] < recent_prices[i+2]):
                minima_indices.append(i + half)
        
        if len(minima_indices) < 2:
            return None
        
        # Check last two minima
        idx1, idx2 = minima_indices[-2], minima_indices[-1]
        price1, price2 = prices[idx1], prices[idx2]
        
        tolerance = self.params['price_tolerance']
        avg_price = (price1 + price2) / 2
        price_diff = abs(price1 - price2) / avg_price
        
        if price_diff > tolerance:
            return None
        
        peak_price = np.max(prices[idx1:idx2+1])
        
        confidence = 0.65  # Lower confidence for fallback method
        
        return PatternResult(
            pattern="Double Bottom",
            pattern_type=PatternType.DOUBLE_BOTTOM,
            confidence=confidence,
            signal=PatternSignal.BULLISH,
            start_idx=idx1,
            end_idx=idx2,
            key_prices=[float(price1), float(peak_price), float(price2)],
            description=f"Double bottom detected (fallback method)"
        )
    
    def _detect_double_top(self, prices: np.ndarray) -> Optional[PatternResult]:
        """
        Detect double top pattern.
        
        Double top: Two highs at similar price levels with a trough between them.
        Signal: Bearish reversal
        """
        if not SCIPY_AVAILABLE:
            return None  # Skip without scipy
        
        try:
            prominence = np.std(prices) * self.params['peak_prominence'] * 10
            distance = self.params['peak_distance']
            
            tops, properties = find_peaks(prices, 
                                         prominence=prominence,
                                         distance=distance)
            
            if len(tops) < 2:
                return None
            
            idx1, idx2 = tops[-2], tops[-1]
            price1, price2 = prices[idx1], prices[idx2]
            
            tolerance = self.params['price_tolerance']
            avg_price = (price1 + price2) / 2
            price_diff = abs(price1 - price2) / avg_price
            
            if price_diff > tolerance:
                return None
            
            # Find trough between tops
            between_prices = prices[idx1:idx2+1]
            trough_idx_local = np.argmin(between_prices)
            trough_idx = idx1 + trough_idx_local
            trough_price = prices[trough_idx]
            
            trough_diff = (avg_price - trough_price) / avg_price
            if trough_diff < 0.02:
                return None
            
            symmetry = 1 - price_diff / tolerance
            height_factor = min(1.0, trough_diff / 0.05)
            confidence = (symmetry * 0.5 + height_factor * 0.5)
            confidence = min(0.95, max(0.6, confidence))
            
            target_price = trough_price - (avg_price - trough_price)
            stop_loss = avg_price * 1.02
            
            return PatternResult(
                pattern="Double Top",
                pattern_type=PatternType.DOUBLE_TOP,
                confidence=confidence,
                signal=PatternSignal.BEARISH,
                start_idx=int(idx1),
                end_idx=int(idx2),
                key_prices=[float(price1), float(trough_price), float(price2)],
                description=f"Double top at ${avg_price:.2f} with neckline at ${trough_price:.2f}",
                target_price=float(target_price),
                stop_loss=float(stop_loss)
            )
        
        except Exception as e:
            logger.debug(f"Double top detection error: {e}")
            return None
    
    def _detect_bull_flag(self, prices: np.ndarray) -> Optional[PatternResult]:
        """
        Detect bull flag pattern.
        
        Bull flag: Strong upward move (pole) followed by slight downward 
        consolidation (flag).
        Signal: Bullish continuation
        """
        if not SCIPY_AVAILABLE or linregress is None:
            return None
        
        try:
            n = len(prices)
            if n < 20:
                return None
            
            # Look for pattern in last 60% of data
            lookback = int(n * 0.6)
            recent = prices[-lookback:]
            
            # Split into potential pole (first 40%) and flag (last 60%)
            pole_end = int(len(recent) * 0.4)
            pole = recent[:pole_end]
            flag = recent[pole_end:]
            
            if len(pole) < 5 or len(flag) < 5:
                return None
            
            # Pole should have strong upward trend
            pole_x = np.arange(len(pole))
            pole_slope, _, pole_r, _, _ = linregress(pole_x, pole)
            
            pole_return = (pole[-1] - pole[0]) / pole[0]
            if pole_return < 0.03 or pole_r < 0.7:  # At least 3% gain, R > 0.7
                return None
            
            # Flag should have slight downward or flat trend
            flag_x = np.arange(len(flag))
            flag_slope, _, flag_r, _, _ = linregress(flag_x, flag)
            
            flag_return = (flag[-1] - flag[0]) / flag[0]
            if flag_return > 0.01:  # Flag shouldn't rise more than 1%
                return None
            
            if flag_return < -0.05:  # Flag shouldn't drop more than 5%
                return None
            
            # Calculate confidence
            pole_strength = min(1.0, pole_return / 0.1)  # Max at 10% pole
            flag_quality = 1 - abs(flag_return) / 0.05   # Better if flat
            confidence = (pole_strength * 0.6 + flag_quality * 0.4)
            confidence = min(0.90, max(0.6, confidence))
            
            # Target: pole height added to breakout
            pole_height = pole[-1] - pole[0]
            breakout_level = np.max(flag)
            target_price = breakout_level + pole_height
            stop_loss = np.min(flag) * 0.98
            
            return PatternResult(
                pattern="Bull Flag",
                pattern_type=PatternType.BULL_FLAG,
                confidence=confidence,
                signal=PatternSignal.BULLISH,
                start_idx=n - lookback,
                end_idx=n - 1,
                key_prices=[float(pole[0]), float(pole[-1]), float(flag[-1])],
                description=f"Bull flag with {pole_return:.1%} pole, targeting ${target_price:.2f}",
                target_price=float(target_price),
                stop_loss=float(stop_loss)
            )
        
        except Exception as e:
            logger.debug(f"Bull flag detection error: {e}")
            return None
    
    def _detect_bear_flag(self, prices: np.ndarray) -> Optional[PatternResult]:
        """
        Detect bear flag pattern.
        
        Bear flag: Strong downward move (pole) followed by slight upward 
        consolidation (flag).
        Signal: Bearish continuation
        """
        if not SCIPY_AVAILABLE or linregress is None:
            return None
        
        try:
            n = len(prices)
            if n < 20:
                return None
            
            lookback = int(n * 0.6)
            recent = prices[-lookback:]
            
            pole_end = int(len(recent) * 0.4)
            pole = recent[:pole_end]
            flag = recent[pole_end:]
            
            if len(pole) < 5 or len(flag) < 5:
                return None
            
            # Pole should have strong downward trend
            pole_x = np.arange(len(pole))
            pole_slope, _, pole_r, _, _ = linregress(pole_x, pole)
            
            pole_return = (pole[-1] - pole[0]) / pole[0]
            if pole_return > -0.03 or pole_r < 0.7:  # At least -3% drop
                return None
            
            # Flag should have slight upward or flat trend
            flag_x = np.arange(len(flag))
            flag_slope, _, flag_r, _, _ = linregress(flag_x, flag)
            
            flag_return = (flag[-1] - flag[0]) / flag[0]
            if flag_return < -0.01:  # Flag shouldn't drop more
                return None
            
            if flag_return > 0.05:  # Flag shouldn't rise more than 5%
                return None
            
            pole_strength = min(1.0, abs(pole_return) / 0.1)
            flag_quality = 1 - abs(flag_return) / 0.05
            confidence = (pole_strength * 0.6 + flag_quality * 0.4)
            confidence = min(0.90, max(0.6, confidence))
            
            pole_height = abs(pole[-1] - pole[0])
            breakdown_level = np.min(flag)
            target_price = breakdown_level - pole_height
            stop_loss = np.max(flag) * 1.02
            
            return PatternResult(
                pattern="Bear Flag",
                pattern_type=PatternType.BEAR_FLAG,
                confidence=confidence,
                signal=PatternSignal.BEARISH,
                start_idx=n - lookback,
                end_idx=n - 1,
                key_prices=[float(pole[0]), float(pole[-1]), float(flag[-1])],
                description=f"Bear flag with {pole_return:.1%} pole, targeting ${target_price:.2f}",
                target_price=float(target_price),
                stop_loss=float(stop_loss)
            )
        
        except Exception as e:
            logger.debug(f"Bear flag detection error: {e}")
            return None
    
    def detect_support_resistance(self, prices: np.ndarray, 
                                 n_levels: int = 3) -> Dict[str, List[float]]:
        """
        Detect support and resistance levels.
        
        Args:
            prices: Price array
            n_levels: Number of levels to return for each
            
        Returns:
            Dict with 'support' and 'resistance' lists
        """
        if not SCIPY_AVAILABLE:
            # Fallback: use percentiles
            support = [float(np.percentile(prices, p)) for p in [10, 25, 40]]
            resistance = [float(np.percentile(prices, p)) for p in [60, 75, 90]]
            return {'support': support[:n_levels], 'resistance': resistance[:n_levels]}
        
        try:
            # Find peaks and troughs
            distance = max(3, len(prices) // 20)
            
            peaks, _ = find_peaks(prices, distance=distance)
            troughs, _ = find_peaks(-prices, distance=distance)
            
            # Cluster nearby levels
            resistance_levels = self._cluster_levels(prices[peaks], n_levels) if len(peaks) > 0 else []
            support_levels = self._cluster_levels(prices[troughs], n_levels) if len(troughs) > 0 else []
            
            return {
                'support': support_levels,
                'resistance': resistance_levels
            }
        
        except Exception as e:
            logger.debug(f"Support/resistance detection error: {e}")
            return {'support': [], 'resistance': []}
    
    def _cluster_levels(self, levels: np.ndarray, n_clusters: int) -> List[float]:
        """Cluster nearby price levels into key levels."""
        if len(levels) == 0:
            return []
        
        if len(levels) <= n_clusters:
            return sorted([float(l) for l in levels])
        
        # Simple clustering by binning
        sorted_levels = np.sort(levels)
        bins = np.array_split(sorted_levels, n_clusters)
        
        return [float(np.mean(b)) for b in bins if len(b) > 0]


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def detect_patterns(prices: pd.Series) -> List[PatternResult]:
    """
    Convenience function to detect patterns.
    
    Args:
        prices: Price series
        
    Returns:
        List of detected patterns
    """
    detector = PatternDetector()
    return detector.detect_patterns(prices)


def get_primary_pattern(prices: pd.Series) -> PatternResult:
    """
    Get the highest-confidence pattern.
    
    Args:
        prices: Price series
        
    Returns:
        Single PatternResult with highest confidence
    """
    detector = PatternDetector()
    patterns = detector.detect_patterns(prices)
    return patterns[0] if patterns else PatternResult(
        pattern="No Pattern",
        pattern_type=PatternType.NO_PATTERN,
        confidence=0.0,
        signal=PatternSignal.NEUTRAL
    )


# =============================================================================
# STANDALONE TESTING
# =============================================================================

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("Pattern Detector Test")
    print("=" * 60)
    
    # Create test data with patterns
    np.random.seed(42)
    
    # Double bottom pattern
    double_bottom_data = np.array([
        100, 99, 97, 95, 93, 92, 90, 91, 93, 95,  # First decline
        98, 100, 102, 100, 98, 96, 94, 92, 90, 91,  # Peak and second decline
        93, 95, 98, 101, 104, 107, 110  # Recovery
    ])
    
    # Bull flag pattern
    bull_flag_data = np.array([
        100, 102, 105, 108, 112, 115, 118, 120,  # Strong pole
        119, 118, 117, 118, 117, 116, 117, 116,  # Flag consolidation
        117, 118, 119, 120  # Breakout start
    ])
    
    detector = PatternDetector()
    
    print("\n📊 Test 1: Double Bottom Data")
    print("-" * 40)
    patterns = detector.detect_patterns(double_bottom_data)
    for p in patterns:
        print(f"  {p.pattern}: {p.confidence:.0%} confidence ({p.signal.value})")
        print(f"    {p.description}")
        if p.target_price:
            print(f"    Target: ${p.target_price:.2f}, Stop: ${p.stop_loss:.2f}")
    
    print("\n📊 Test 2: Bull Flag Data")
    print("-" * 40)
    patterns = detector.detect_patterns(bull_flag_data)
    for p in patterns:
        print(f"  {p.pattern}: {p.confidence:.0%} confidence ({p.signal.value})")
        print(f"    {p.description}")
    
    print("\n📊 Test 3: Random Data (should find no patterns)")
    print("-" * 40)
    random_data = np.random.randn(50) * 5 + 100
    patterns = detector.detect_patterns(random_data)
    for p in patterns:
        print(f"  {p.pattern}: {p.confidence:.0%} confidence")
    
    print("\n📊 Test 4: Support/Resistance")
    print("-" * 40)
    levels = detector.detect_support_resistance(double_bottom_data)
    print(f"  Support: {[f'${l:.2f}' for l in levels['support']]}")
    print(f"  Resistance: {[f'${l:.2f}' for l in levels['resistance']]}")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")

