"""
Pattern Detection Engine
Phase 15 - Agent-UX

Implements technical chart pattern recognition using scipy signal processing.
Detects: Double Bottom, Head & Shoulders, Bull Flag, and more.

Usage:
    from engines.analysis.patterns import PatternDetector
    
    detector = PatternDetector()
    patterns = detector.detect_all(prices)
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Tuple
from enum import Enum
from scipy.signal import find_peaks, argrelextrema
from scipy.stats import linregress

logger = logging.getLogger(__name__)


class PatternType(Enum):
    """Pattern classification types."""
    DOUBLE_BOTTOM = "double_bottom"
    DOUBLE_TOP = "double_top"
    HEAD_SHOULDERS = "head_shoulders"
    INVERSE_HEAD_SHOULDERS = "inverse_head_shoulders"
    BULL_FLAG = "bull_flag"
    BEAR_FLAG = "bear_flag"
    ASCENDING_TRIANGLE = "ascending_triangle"
    DESCENDING_TRIANGLE = "descending_triangle"
    WEDGE_UP = "wedge_up"
    WEDGE_DOWN = "wedge_down"


class PatternSignal(Enum):
    """Pattern directional signal."""
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class DetectedPattern:
    """Represents a detected chart pattern."""
    pattern_type: PatternType
    signal: PatternSignal
    confidence: float  # 0.0 to 1.0
    start_idx: int
    end_idx: int
    key_points: List[Tuple[int, float]]  # (index, price) pairs
    description: str
    target_price: Optional[float] = None
    stop_loss: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "pattern_type": self.pattern_type.value,
            "signal": self.signal.value,
            "confidence": round(self.confidence, 3),
            "start_idx": self.start_idx,
            "end_idx": self.end_idx,
            "key_points": self.key_points,
            "description": self.description,
            "target_price": round(self.target_price, 2) if self.target_price else None,
            "stop_loss": round(self.stop_loss, 2) if self.stop_loss else None,
        }


class PatternDetector:
    """
    Technical chart pattern detector using scipy signal processing.
    
    Detects common reversal and continuation patterns in price data.
    
    Args:
        tolerance: Price tolerance for pattern matching (default 1% = 0.01)
        min_pattern_bars: Minimum bars for pattern formation
        peak_prominence: Prominence threshold for peak detection
    """
    
    def __init__(
        self,
        tolerance: float = 0.01,
        min_pattern_bars: int = 10,
        peak_prominence: float = 0.5,
    ):
        self.tolerance = tolerance
        self.min_pattern_bars = min_pattern_bars
        self.peak_prominence = peak_prominence
        logger.info(f"PatternDetector initialized: tolerance={tolerance}, min_bars={min_pattern_bars}")
    
    def _validate_prices(self, prices: np.ndarray) -> np.ndarray:
        """Validate and convert price data to numpy array."""
        if prices is None or len(prices) < self.min_pattern_bars:
            raise ValueError(f"Need at least {self.min_pattern_bars} price points")
        
        prices = np.asarray(prices, dtype=np.float64)
        
        # Remove NaN/Inf
        mask = np.isfinite(prices)
        if not mask.all():
            logger.warning(f"Removed {(~mask).sum()} invalid price points")
            prices = prices[mask]
        
        return prices
    
    def _find_local_extrema(
        self, prices: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find local minima and maxima in price data.
        
        Returns:
            Tuple of (maxima_indices, minima_indices)
        """
        # Use scipy for robust extrema detection
        order = max(3, len(prices) // 20)  # Adaptive window
        
        # Find peaks (local maxima)
        maxima_idx, _ = find_peaks(prices, prominence=self.peak_prominence, distance=order)
        
        # Find troughs (local minima) by inverting
        minima_idx, _ = find_peaks(-prices, prominence=self.peak_prominence, distance=order)
        
        # Fallback to argrelextrema if find_peaks returns empty
        if len(maxima_idx) == 0:
            maxima_idx = argrelextrema(prices, np.greater, order=order)[0]
        if len(minima_idx) == 0:
            minima_idx = argrelextrema(prices, np.less, order=order)[0]
        
        return maxima_idx, minima_idx
    
    def _prices_within_tolerance(
        self, p1: float, p2: float, tolerance: Optional[float] = None
    ) -> bool:
        """Check if two prices are within tolerance of each other."""
        tol = tolerance or self.tolerance
        return abs(p1 - p2) / max(p1, p2, 1e-10) <= tol
    
    def detect_double_bottom(
        self, prices: np.ndarray
    ) -> Optional[DetectedPattern]:
        """
        Detect Double Bottom pattern (Bullish reversal).
        
        Criteria:
        - Two minima within tolerance (typically 1-3%)
        - Peak between them (the "neckline")
        - Second bottom doesn't make new low
        
        Args:
            prices: Array of price data (OHLC close or typical price)
            
        Returns:
            DetectedPattern if found, None otherwise
        """
        try:
            prices = self._validate_prices(prices)
            maxima_idx, minima_idx = self._find_local_extrema(prices)
            
            if len(minima_idx) < 2 or len(maxima_idx) < 1:
                return None
            
            # Look for two consecutive minima with similar prices
            for i in range(len(minima_idx) - 1):
                bottom1_idx = minima_idx[i]
                bottom2_idx = minima_idx[i + 1]
                
                bottom1_price = prices[bottom1_idx]
                bottom2_price = prices[bottom2_idx]
                
                # Check if bottoms are within tolerance
                if not self._prices_within_tolerance(bottom1_price, bottom2_price, self.tolerance * 2):
                    continue
                
                # Find peak between the two bottoms
                peaks_between = maxima_idx[
                    (maxima_idx > bottom1_idx) & (maxima_idx < bottom2_idx)
                ]
                
                if len(peaks_between) == 0:
                    continue
                
                neckline_idx = peaks_between[np.argmax(prices[peaks_between])]
                neckline_price = prices[neckline_idx]
                
                # Validate pattern shape: neckline should be significantly above bottoms
                bottom_avg = (bottom1_price + bottom2_price) / 2
                height = neckline_price - bottom_avg
                
                if height / bottom_avg < 0.02:  # At least 2% height
                    continue
                
                # Calculate confidence based on symmetry and height
                symmetry = 1 - abs(bottom1_price - bottom2_price) / bottom_avg
                pattern_height = height / bottom_avg
                confidence = min(0.95, (symmetry * 0.5 + pattern_height * 2))
                
                # Target price = neckline + pattern height
                target_price = neckline_price + height
                stop_loss = min(bottom1_price, bottom2_price) * 0.99
                
                return DetectedPattern(
                    pattern_type=PatternType.DOUBLE_BOTTOM,
                    signal=PatternSignal.BULLISH,
                    confidence=confidence,
                    start_idx=int(bottom1_idx),
                    end_idx=int(bottom2_idx),
                    key_points=[
                        (int(bottom1_idx), float(bottom1_price)),
                        (int(neckline_idx), float(neckline_price)),
                        (int(bottom2_idx), float(bottom2_price)),
                    ],
                    description=f"Double Bottom: Two lows at ~${bottom_avg:.2f}, neckline at ${neckline_price:.2f}",
                    target_price=float(target_price),
                    stop_loss=float(stop_loss),
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting double bottom: {e}")
            return None
    
    def detect_double_top(
        self, prices: np.ndarray
    ) -> Optional[DetectedPattern]:
        """
        Detect Double Top pattern (Bearish reversal).
        
        Mirror of Double Bottom - two peaks with similar prices.
        """
        try:
            prices = self._validate_prices(prices)
            maxima_idx, minima_idx = self._find_local_extrema(prices)
            
            if len(maxima_idx) < 2 or len(minima_idx) < 1:
                return None
            
            for i in range(len(maxima_idx) - 1):
                top1_idx = maxima_idx[i]
                top2_idx = maxima_idx[i + 1]
                
                top1_price = prices[top1_idx]
                top2_price = prices[top2_idx]
                
                if not self._prices_within_tolerance(top1_price, top2_price, self.tolerance * 2):
                    continue
                
                # Find trough between tops
                troughs_between = minima_idx[
                    (minima_idx > top1_idx) & (minima_idx < top2_idx)
                ]
                
                if len(troughs_between) == 0:
                    continue
                
                neckline_idx = troughs_between[np.argmin(prices[troughs_between])]
                neckline_price = prices[neckline_idx]
                
                top_avg = (top1_price + top2_price) / 2
                height = top_avg - neckline_price
                
                if height / top_avg < 0.02:
                    continue
                
                symmetry = 1 - abs(top1_price - top2_price) / top_avg
                confidence = min(0.95, (symmetry * 0.5 + (height / top_avg) * 2))
                
                target_price = neckline_price - height
                stop_loss = max(top1_price, top2_price) * 1.01
                
                return DetectedPattern(
                    pattern_type=PatternType.DOUBLE_TOP,
                    signal=PatternSignal.BEARISH,
                    confidence=confidence,
                    start_idx=int(top1_idx),
                    end_idx=int(top2_idx),
                    key_points=[
                        (int(top1_idx), float(top1_price)),
                        (int(neckline_idx), float(neckline_price)),
                        (int(top2_idx), float(top2_price)),
                    ],
                    description=f"Double Top: Two highs at ~${top_avg:.2f}, neckline at ${neckline_price:.2f}",
                    target_price=float(target_price),
                    stop_loss=float(stop_loss),
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting double top: {e}")
            return None
    
    def detect_head_shoulders(
        self, prices: np.ndarray
    ) -> Optional[DetectedPattern]:
        """
        Detect Head and Shoulders pattern (Bearish reversal).
        
        Criteria:
        - Three peaks: Left Shoulder, Head (highest), Right Shoulder
        - Shoulders at similar heights
        - Head significantly higher than shoulders
        """
        try:
            prices = self._validate_prices(prices)
            maxima_idx, minima_idx = self._find_local_extrema(prices)
            
            if len(maxima_idx) < 3:
                return None
            
            # Look for three consecutive peaks
            for i in range(len(maxima_idx) - 2):
                ls_idx = maxima_idx[i]      # Left Shoulder
                head_idx = maxima_idx[i + 1]  # Head
                rs_idx = maxima_idx[i + 2]   # Right Shoulder
                
                ls_price = prices[ls_idx]
                head_price = prices[head_idx]
                rs_price = prices[rs_idx]
                
                # Head must be highest
                if head_price <= ls_price or head_price <= rs_price:
                    continue
                
                # Shoulders should be at similar levels
                if not self._prices_within_tolerance(ls_price, rs_price, self.tolerance * 3):
                    continue
                
                # Head should be significantly higher (at least 2% above shoulders)
                shoulder_avg = (ls_price + rs_price) / 2
                head_prominence = (head_price - shoulder_avg) / shoulder_avg
                
                if head_prominence < 0.02:
                    continue
                
                # Find neckline (troughs between shoulders)
                troughs_ls_head = minima_idx[(minima_idx > ls_idx) & (minima_idx < head_idx)]
                troughs_head_rs = minima_idx[(minima_idx > head_idx) & (minima_idx < rs_idx)]
                
                if len(troughs_ls_head) == 0 or len(troughs_head_rs) == 0:
                    continue
                
                nl1_idx = troughs_ls_head[np.argmin(prices[troughs_ls_head])]
                nl2_idx = troughs_head_rs[np.argmin(prices[troughs_head_rs])]
                neckline = (prices[nl1_idx] + prices[nl2_idx]) / 2
                
                # Pattern height for target
                pattern_height = head_price - neckline
                target_price = neckline - pattern_height
                stop_loss = head_price * 1.01
                
                confidence = min(0.95, 0.5 + head_prominence * 2)
                
                return DetectedPattern(
                    pattern_type=PatternType.HEAD_SHOULDERS,
                    signal=PatternSignal.BEARISH,
                    confidence=confidence,
                    start_idx=int(ls_idx),
                    end_idx=int(rs_idx),
                    key_points=[
                        (int(ls_idx), float(ls_price)),
                        (int(head_idx), float(head_price)),
                        (int(rs_idx), float(rs_price)),
                        (int(nl1_idx), float(prices[nl1_idx])),
                        (int(nl2_idx), float(prices[nl2_idx])),
                    ],
                    description=f"Head & Shoulders: Head at ${head_price:.2f}, neckline at ${neckline:.2f}",
                    target_price=float(target_price),
                    stop_loss=float(stop_loss),
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting head & shoulders: {e}")
            return None
    
    def detect_inverse_head_shoulders(
        self, prices: np.ndarray
    ) -> Optional[DetectedPattern]:
        """
        Detect Inverse Head and Shoulders pattern (Bullish reversal).
        
        Mirror of Head & Shoulders - three troughs with middle being lowest.
        """
        try:
            prices = self._validate_prices(prices)
            maxima_idx, minima_idx = self._find_local_extrema(prices)
            
            if len(minima_idx) < 3:
                return None
            
            for i in range(len(minima_idx) - 2):
                ls_idx = minima_idx[i]
                head_idx = minima_idx[i + 1]
                rs_idx = minima_idx[i + 2]
                
                ls_price = prices[ls_idx]
                head_price = prices[head_idx]
                rs_price = prices[rs_idx]
                
                # Head must be lowest
                if head_price >= ls_price or head_price >= rs_price:
                    continue
                
                # Shoulders at similar levels
                if not self._prices_within_tolerance(ls_price, rs_price, self.tolerance * 3):
                    continue
                
                shoulder_avg = (ls_price + rs_price) / 2
                head_depth = (shoulder_avg - head_price) / shoulder_avg
                
                if head_depth < 0.02:
                    continue
                
                # Find neckline (peaks between troughs)
                peaks_ls_head = maxima_idx[(maxima_idx > ls_idx) & (maxima_idx < head_idx)]
                peaks_head_rs = maxima_idx[(maxima_idx > head_idx) & (maxima_idx < rs_idx)]
                
                if len(peaks_ls_head) == 0 or len(peaks_head_rs) == 0:
                    continue
                
                nl1_idx = peaks_ls_head[np.argmax(prices[peaks_ls_head])]
                nl2_idx = peaks_head_rs[np.argmax(prices[peaks_head_rs])]
                neckline = (prices[nl1_idx] + prices[nl2_idx]) / 2
                
                pattern_height = neckline - head_price
                target_price = neckline + pattern_height
                stop_loss = head_price * 0.99
                
                confidence = min(0.95, 0.5 + head_depth * 2)
                
                return DetectedPattern(
                    pattern_type=PatternType.INVERSE_HEAD_SHOULDERS,
                    signal=PatternSignal.BULLISH,
                    confidence=confidence,
                    start_idx=int(ls_idx),
                    end_idx=int(rs_idx),
                    key_points=[
                        (int(ls_idx), float(ls_price)),
                        (int(head_idx), float(head_price)),
                        (int(rs_idx), float(rs_price)),
                    ],
                    description=f"Inverse H&S: Head at ${head_price:.2f}, neckline at ${neckline:.2f}",
                    target_price=float(target_price),
                    stop_loss=float(stop_loss),
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error detecting inverse H&S: {e}")
            return None
    
    def detect_bull_flag(
        self, prices: np.ndarray
    ) -> Optional[DetectedPattern]:
        """
        Detect Bull Flag pattern (Bullish continuation).
        
        Criteria:
        - Strong upward move (flagpole)
        - Consolidation with slight downward slope (flag)
        - Flag range is tight relative to pole
        """
        try:
            prices = self._validate_prices(prices)
            
            if len(prices) < 20:
                return None
            
            # Find the strongest upward move in recent history
            lookback = min(50, len(prices) - 10)
            
            best_pole_end = None
            best_pole_start = None
            best_gain = 0
            
            for i in range(10, lookback):
                # Look for sharp moves
                window = prices[-lookback:-lookback+i]
                if len(window) < 5:
                    continue
                
                gain = (window[-1] - window[0]) / window[0]
                if gain > best_gain and gain > 0.05:  # At least 5% move
                    best_gain = gain
                    best_pole_start = len(prices) - lookback
                    best_pole_end = len(prices) - lookback + i
            
            if best_pole_end is None:
                return None
            
            # Check for consolidation (flag) after pole
            flag_prices = prices[best_pole_end:]
            if len(flag_prices) < 5:
                return None
            
            # Flag should have slight downward or flat slope
            x = np.arange(len(flag_prices))
            slope, intercept, r_value, _, _ = linregress(x, flag_prices)
            
            # Normalize slope
            flag_height = np.max(flag_prices) - np.min(flag_prices)
            pole_height = prices[best_pole_end] - prices[best_pole_start]
            
            # Flag should be tight (less than 50% of pole height)
            if flag_height > pole_height * 0.5:
                return None
            
            # Slope should be slightly negative or flat
            slope_pct = slope / np.mean(flag_prices)
            if slope_pct > 0.01:  # Reject if strongly upward
                return None
            
            flag_start_idx = best_pole_end
            flag_end_idx = len(prices) - 1
            
            target_price = prices[flag_end_idx] + pole_height
            stop_loss = np.min(flag_prices) * 0.99
            
            confidence = min(0.90, 0.4 + best_gain * 2 + abs(r_value) * 0.3)
            
            return DetectedPattern(
                pattern_type=PatternType.BULL_FLAG,
                signal=PatternSignal.BULLISH,
                confidence=confidence,
                start_idx=int(best_pole_start),
                end_idx=int(flag_end_idx),
                key_points=[
                    (int(best_pole_start), float(prices[best_pole_start])),
                    (int(best_pole_end), float(prices[best_pole_end])),
                    (int(flag_end_idx), float(prices[flag_end_idx])),
                ],
                description=f"Bull Flag: {best_gain*100:.1f}% pole, consolidating in flag",
                target_price=float(target_price),
                stop_loss=float(stop_loss),
            )
            
        except Exception as e:
            logger.error(f"Error detecting bull flag: {e}")
            return None
    
    def detect_bear_flag(
        self, prices: np.ndarray
    ) -> Optional[DetectedPattern]:
        """
        Detect Bear Flag pattern (Bearish continuation).
        
        Mirror of Bull Flag - downward pole with upward-sloping flag.
        """
        try:
            prices = self._validate_prices(prices)
            
            if len(prices) < 20:
                return None
            
            lookback = min(50, len(prices) - 10)
            
            best_pole_end = None
            best_pole_start = None
            best_loss = 0
            
            for i in range(10, lookback):
                window = prices[-lookback:-lookback+i]
                if len(window) < 5:
                    continue
                
                loss = (window[0] - window[-1]) / window[0]  # Negative move
                if loss > best_loss and loss > 0.05:
                    best_loss = loss
                    best_pole_start = len(prices) - lookback
                    best_pole_end = len(prices) - lookback + i
            
            if best_pole_end is None:
                return None
            
            flag_prices = prices[best_pole_end:]
            if len(flag_prices) < 5:
                return None
            
            x = np.arange(len(flag_prices))
            slope, _, r_value, _, _ = linregress(x, flag_prices)
            
            flag_height = np.max(flag_prices) - np.min(flag_prices)
            pole_height = prices[best_pole_start] - prices[best_pole_end]
            
            if flag_height > pole_height * 0.5:
                return None
            
            slope_pct = slope / np.mean(flag_prices)
            if slope_pct < -0.01:  # Reject if strongly downward
                return None
            
            flag_end_idx = len(prices) - 1
            target_price = prices[flag_end_idx] - pole_height
            stop_loss = np.max(flag_prices) * 1.01
            
            confidence = min(0.90, 0.4 + best_loss * 2 + abs(r_value) * 0.3)
            
            return DetectedPattern(
                pattern_type=PatternType.BEAR_FLAG,
                signal=PatternSignal.BEARISH,
                confidence=confidence,
                start_idx=int(best_pole_start),
                end_idx=int(flag_end_idx),
                key_points=[
                    (int(best_pole_start), float(prices[best_pole_start])),
                    (int(best_pole_end), float(prices[best_pole_end])),
                    (int(flag_end_idx), float(prices[flag_end_idx])),
                ],
                description=f"Bear Flag: {best_loss*100:.1f}% drop, consolidating in flag",
                target_price=float(max(0, target_price)),
                stop_loss=float(stop_loss),
            )
            
        except Exception as e:
            logger.error(f"Error detecting bear flag: {e}")
            return None
    
    def detect_all(
        self, prices: np.ndarray
    ) -> List[DetectedPattern]:
        """
        Run all pattern detectors on price data.
        
        Args:
            prices: Array of price data
            
        Returns:
            List of detected patterns, sorted by confidence
        """
        patterns = []
        
        detectors = [
            self.detect_double_bottom,
            self.detect_double_top,
            self.detect_head_shoulders,
            self.detect_inverse_head_shoulders,
            self.detect_bull_flag,
            self.detect_bear_flag,
        ]
        
        for detector in detectors:
            try:
                result = detector(prices)
                if result is not None:
                    patterns.append(result)
            except Exception as e:
                logger.error(f"Error in {detector.__name__}: {e}")
        
        # Sort by confidence descending
        patterns.sort(key=lambda p: p.confidence, reverse=True)
        
        return patterns


def generate_mock_pattern_data(
    pattern_type: str = "double_bottom",
    length: int = 100,
    base_price: float = 100.0,
) -> np.ndarray:
    """
    Generate mock price data containing a specific pattern for testing.
    
    Args:
        pattern_type: Type of pattern to generate
        length: Number of price points
        base_price: Starting price
        
    Returns:
        numpy array of prices containing the pattern
    """
    np.random.seed(42)  # For reproducibility in tests
    
    prices = np.zeros(length)
    
    if pattern_type == "double_bottom":
        # Create W-shaped pattern
        for i in range(length):
            if i < length * 0.2:
                # Initial decline
                prices[i] = base_price - (base_price * 0.1 * i / (length * 0.2))
            elif i < length * 0.35:
                # First bottom
                t = (i - length * 0.2) / (length * 0.15)
                prices[i] = base_price * 0.9 + (base_price * 0.05) * np.sin(t * np.pi)
            elif i < length * 0.5:
                # Rise to neckline
                t = (i - length * 0.35) / (length * 0.15)
                prices[i] = base_price * 0.9 + (base_price * 0.08) * t
            elif i < length * 0.65:
                # Second bottom
                t = (i - length * 0.5) / (length * 0.15)
                prices[i] = base_price * 0.98 - (base_price * 0.08) * np.sin(t * np.pi)
            else:
                # Breakout
                t = (i - length * 0.65) / (length * 0.35)
                prices[i] = base_price * 0.9 + (base_price * 0.15) * t
        
        # Add noise
        prices += np.random.normal(0, base_price * 0.005, length)
    
    elif pattern_type == "head_shoulders":
        # Create M-shaped pattern with higher middle peak
        for i in range(length):
            if i < length * 0.15:
                prices[i] = base_price + (base_price * 0.08) * (i / (length * 0.15))
            elif i < length * 0.25:
                t = (i - length * 0.15) / (length * 0.1)
                prices[i] = base_price * 1.08 - (base_price * 0.05) * t
            elif i < length * 0.4:
                t = (i - length * 0.25) / (length * 0.15)
                prices[i] = base_price * 1.03 + (base_price * 0.12) * np.sin(t * np.pi)
            elif i < length * 0.55:
                t = (i - length * 0.4) / (length * 0.15)
                prices[i] = base_price * 1.03 + (base_price * 0.12) * np.sin(np.pi - t * np.pi)
            elif i < length * 0.7:
                t = (i - length * 0.55) / (length * 0.15)
                prices[i] = base_price * 1.03 + (base_price * 0.05) * t
            elif i < length * 0.85:
                t = (i - length * 0.7) / (length * 0.15)
                prices[i] = base_price * 1.08 - (base_price * 0.05) * t
            else:
                t = (i - length * 0.85) / (length * 0.15)
                prices[i] = base_price * 1.03 - (base_price * 0.1) * t
        
        prices += np.random.normal(0, base_price * 0.003, length)
    
    elif pattern_type == "bull_flag":
        # Strong up move then consolidation
        for i in range(length):
            if i < length * 0.4:
                # Flagpole (strong up)
                prices[i] = base_price + (base_price * 0.15) * (i / (length * 0.4))
            else:
                # Flag (slight down consolidation)
                t = (i - length * 0.4) / (length * 0.6)
                prices[i] = base_price * 1.15 - (base_price * 0.03) * t + \
                           (base_price * 0.02) * np.sin(t * np.pi * 4)
        
        prices += np.random.normal(0, base_price * 0.003, length)
    
    else:
        # Default: random walk
        prices[0] = base_price
        for i in range(1, length):
            prices[i] = prices[i-1] * (1 + np.random.normal(0, 0.01))
    
    return prices


# Module-level convenience functions
def detect_patterns(prices: np.ndarray, **kwargs) -> List[DetectedPattern]:
    """
    Convenience function to detect all patterns.
    
    Args:
        prices: Array of price data
        **kwargs: Arguments passed to PatternDetector
        
    Returns:
        List of detected patterns
    """
    detector = PatternDetector(**kwargs)
    return detector.detect_all(prices)


if __name__ == "__main__":
    # Quick test
    logging.basicConfig(level=logging.INFO)
    
    print("Testing PatternDetector...")
    
    # Test double bottom
    db_prices = generate_mock_pattern_data("double_bottom", 100, 100.0)
    detector = PatternDetector()
    db_result = detector.detect_double_bottom(db_prices)
    
    if db_result:
        print(f"✅ Double Bottom: {db_result.description}")
        print(f"   Confidence: {db_result.confidence:.2%}")
        print(f"   Target: ${db_result.target_price:.2f}")
    else:
        print("❌ Double Bottom not detected")
    
    # Test head & shoulders
    hs_prices = generate_mock_pattern_data("head_shoulders", 100, 100.0)
    hs_result = detector.detect_head_shoulders(hs_prices)
    
    if hs_result:
        print(f"✅ Head & Shoulders: {hs_result.description}")
        print(f"   Confidence: {hs_result.confidence:.2%}")
    else:
        print("❌ Head & Shoulders not detected")
    
    # Test bull flag
    bf_prices = generate_mock_pattern_data("bull_flag", 100, 100.0)
    bf_result = detector.detect_bull_flag(bf_prices)
    
    if bf_result:
        print(f"✅ Bull Flag: {bf_result.description}")
        print(f"   Confidence: {bf_result.confidence:.2%}")
    else:
        print("❌ Bull Flag not detected")
    
    print("\nAll pattern tests complete!")
