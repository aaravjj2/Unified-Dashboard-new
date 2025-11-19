"""
Phase 8 — Trend Analyzer Module
=================================

Analyze forecast trends, moving averages, and correlation patterns from Phase 6/7 outputs.

Key Features:
- Rolling expected returns (7-day, 30-day windows)
- Correlation matrices (ticker × ticker)
- Trendline slope and signal stability indices
- JSON + Pandas DataFrame + chart-ready dict exports

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0 (Phase 8)
"""

import json
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class TrendSignal:
    """
    Trend detection signal for a single ticker.
    
    Attributes:
        ticker: Stock ticker symbol
        timestamp: Analysis timestamp
        trend_label: Bullish / Neutral / Bearish
        slope_7d: 7-day trendline slope
        slope_30d: 30-day trendline slope
        stability_index: Signal stability (0-1, higher = more stable)
        correlation_cluster: Ticker correlation group ID
        metadata: Additional metrics
    """
    ticker: str
    timestamp: str
    trend_label: str  # "Bullish" | "Neutral" | "Bearish"
    slope_7d: float
    slope_30d: float
    stability_index: float
    correlation_cluster: int
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), separators=(',', ':'))


@dataclass
class TrendAnalysisResult:
    """
    Complete trend analysis result for portfolio.
    
    Attributes:
        analysis_id: Unique analysis identifier
        timestamp: Analysis timestamp
        tickers: List of analyzed tickers
        signals: Dict of ticker → TrendSignal
        correlation_matrix: Ticker correlation matrix (JSON-safe)
        moving_avg_7d: 7-day moving averages
        moving_avg_30d: 30-day moving averages
        metadata: Additional analysis metadata
    """
    analysis_id: str
    timestamp: str
    tickers: List[str]
    signals: Dict[str, TrendSignal]
    correlation_matrix: Dict[str, Dict[str, float]]
    moving_avg_7d: Dict[str, float]
    moving_avg_30d: Dict[str, float]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            'analysis_id': self.analysis_id,
            'timestamp': self.timestamp,
            'tickers': self.tickers,
            'signals': {k: v.to_dict() for k, v in self.signals.items()},
            'correlation_matrix': self.correlation_matrix,
            'moving_avg_7d': self.moving_avg_7d,
            'moving_avg_30d': self.moving_avg_30d,
            'metadata': self.metadata
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    def to_dataframe(self) -> pd.DataFrame:
        """Convert signals to Pandas DataFrame."""
        rows = []
        for ticker, signal in self.signals.items():
            row = {
                'ticker': ticker,
                'trend_label': signal.trend_label,
                'slope_7d': signal.slope_7d,
                'slope_30d': signal.slope_30d,
                'stability_index': signal.stability_index,
                'correlation_cluster': signal.correlation_cluster
            }
            rows.append(row)
        
        return pd.DataFrame(rows)


# =============================================================================
# TREND ANALYZER
# =============================================================================

class TrendAnalyzer:
    """
    Analyze trends from forecast data and generate trading signals.
    
    Workflow:
    1. Load forecast data (ForecastContract JSONs or batch outputs)
    2. Compute rolling returns (7d, 30d)
    3. Calculate correlation matrix
    4. Detect trendlines and stability
    5. Classify signals (Bullish/Neutral/Bearish)
    6. Export JSON + DataFrame
    """
    
    def __init__(self, 
                 short_window: int = 7,
                 long_window: int = 30,
                 stability_threshold: float = 0.7):
        """
        Initialize trend analyzer.
        
        Args:
            short_window: Short-term window (days)
            long_window: Long-term window (days)
            stability_threshold: Minimum stability index for reliable signals
        """
        self.short_window = short_window
        self.long_window = long_window
        self.stability_threshold = stability_threshold
        
        logger.info(
            f"🔧 TrendAnalyzer initialized "
            f"(short={short_window}d, long={long_window}d, threshold={stability_threshold})"
        )
    
    def analyze_trends(self,
                       forecast_data: Dict[str, List[Dict[str, Any]]],
                       compute_correlations: bool = True) -> TrendAnalysisResult:
        """
        Analyze trends from forecast time-series data.
        
        Args:
            forecast_data: Dict of ticker → list of forecast dicts
                          Each forecast dict must have 'timestamp', 'expected_return'
            compute_correlations: Whether to compute correlation matrix
        
        Returns:
            TrendAnalysisResult with signals and metrics
        """
        logger.info(f"📊 Analyzing trends for {len(forecast_data)} tickers...")
        
        # Step 1: Compute moving averages
        moving_avg_7d = {}
        moving_avg_30d = {}
        
        for ticker, forecasts in forecast_data.items():
            returns = [f['expected_return'] for f in forecasts]
            
            if len(returns) >= self.short_window:
                moving_avg_7d[ticker] = float(np.mean(returns[-self.short_window:]))
            else:
                moving_avg_7d[ticker] = float(np.mean(returns)) if returns else 0.0
            
            if len(returns) >= self.long_window:
                moving_avg_30d[ticker] = float(np.mean(returns[-self.long_window:]))
            else:
                moving_avg_30d[ticker] = float(np.mean(returns)) if returns else 0.0
        
        # Step 2: Compute trendline slopes
        signals = {}
        for ticker, forecasts in forecast_data.items():
            signal = self._compute_trend_signal(ticker, forecasts)
            signals[ticker] = signal
        
        # Step 3: Compute correlation matrix (if requested)
        correlation_matrix = {}
        if compute_correlations:
            correlation_matrix = self._compute_correlation_matrix(forecast_data)
        
        # Step 4: Assign correlation clusters
        self._assign_correlation_clusters(signals, correlation_matrix)
        
        # Step 5: Create result
        analysis_id = hashlib.sha256(
            f"{','.join(sorted(forecast_data.keys()))}:{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]
        
        result = TrendAnalysisResult(
            analysis_id=analysis_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            tickers=list(forecast_data.keys()),
            signals=signals,
            correlation_matrix=correlation_matrix,
            moving_avg_7d=moving_avg_7d,
            moving_avg_30d=moving_avg_30d,
            metadata={
                'short_window': self.short_window,
                'long_window': self.long_window,
                'stability_threshold': self.stability_threshold,
                'tickers_analyzed': len(forecast_data)
            }
        )
        
        logger.info(
            f"✅ Trend analysis complete: {len(signals)} signals generated "
            f"(Bullish: {sum(1 for s in signals.values() if s.trend_label == 'Bullish')}, "
            f"Neutral: {sum(1 for s in signals.values() if s.trend_label == 'Neutral')}, "
            f"Bearish: {sum(1 for s in signals.values() if s.trend_label == 'Bearish')})"
        )
        
        return result
    
    def _compute_trend_signal(self, ticker: str, forecasts: List[Dict[str, Any]]) -> TrendSignal:
        """Compute trend signal for a single ticker."""
        returns = np.array([f['expected_return'] for f in forecasts])
        
        # Compute slopes
        slope_7d = self._compute_slope(returns, window=self.short_window)
        slope_30d = self._compute_slope(returns, window=self.long_window)
        
        # Compute stability index (inverse of variance / mean)
        stability_index = self._compute_stability(returns)
        
        # Classify trend
        if slope_7d > 0.01 and slope_30d > 0.005:
            trend_label = "Bullish"
        elif slope_7d < -0.01 and slope_30d < -0.005:
            trend_label = "Bearish"
        else:
            trend_label = "Neutral"
        
        return TrendSignal(
            ticker=ticker,
            timestamp=datetime.now(timezone.utc).isoformat(),
            trend_label=trend_label,
            slope_7d=float(slope_7d),
            slope_30d=float(slope_30d),
            stability_index=float(stability_index),
            correlation_cluster=0,  # Assigned later
            metadata={
                'forecast_count': len(forecasts),
                'mean_return': float(np.mean(returns)),
                'std_return': float(np.std(returns))
            }
        )
    
    def _compute_slope(self, returns: np.ndarray, window: int) -> float:
        """Compute trendline slope using linear regression."""
        if len(returns) < 2:
            return 0.0
        
        window_returns = returns[-window:] if len(returns) >= window else returns
        x = np.arange(len(window_returns))
        
        # Linear regression: y = mx + b
        if len(x) > 1:
            slope, _ = np.polyfit(x, window_returns, 1)
            return float(slope)
        else:
            return 0.0
    
    def _compute_stability(self, returns: np.ndarray) -> float:
        """Compute signal stability index (0-1)."""
        if len(returns) < 2:
            return 0.0
        
        std = np.std(returns)
        mean_abs = np.abs(np.mean(returns))
        
        # Stability = 1 / (1 + CV) where CV = std / |mean|
        if mean_abs > 1e-6:
            cv = std / mean_abs
            stability = 1.0 / (1.0 + cv)
        else:
            stability = 0.0
        
        return min(1.0, max(0.0, float(stability)))
    
    def _compute_correlation_matrix(self, 
                                   forecast_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Dict[str, float]]:
        """Compute ticker correlation matrix."""
        tickers = sorted(forecast_data.keys())
        n = len(tickers)
        
        # Build return matrix
        max_len = max(len(forecasts) for forecasts in forecast_data.values())
        return_matrix = np.zeros((n, max_len))
        
        for i, ticker in enumerate(tickers):
            returns = [f['expected_return'] for f in forecast_data[ticker]]
            return_matrix[i, :len(returns)] = returns
        
        # Compute correlation
        corr_matrix = np.corrcoef(return_matrix)
        
        # Convert to JSON-safe dict
        corr_dict = {}
        for i, ticker1 in enumerate(tickers):
            corr_dict[ticker1] = {}
            for j, ticker2 in enumerate(tickers):
                corr_dict[ticker1][ticker2] = float(corr_matrix[i, j]) if not np.isnan(corr_matrix[i, j]) else 0.0
        
        return corr_dict
    
    def _assign_correlation_clusters(self,
                                     signals: Dict[str, TrendSignal],
                                     correlation_matrix: Dict[str, Dict[str, float]]):
        """Assign correlation cluster IDs using simple threshold-based grouping."""
        if not correlation_matrix:
            return
        
        tickers = list(signals.keys())
        cluster_id = 0
        assigned = set()
        
        for ticker in tickers:
            if ticker in assigned:
                continue
            
            # Find highly correlated tickers (corr > 0.7)
            cluster = [ticker]
            for other_ticker in tickers:
                if other_ticker != ticker and other_ticker not in assigned:
                    corr = correlation_matrix.get(ticker, {}).get(other_ticker, 0.0)
                    if corr > 0.7:
                        cluster.append(other_ticker)
            
            # Assign cluster ID
            for t in cluster:
                signals[t].correlation_cluster = cluster_id
                assigned.add(t)
            
            cluster_id += 1


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_forecast_data_from_json(json_path: str) -> Dict[str, List[Dict[str, Any]]]:
    """
    Load forecast data from JSON file.
    
    Args:
        json_path: Path to JSON file with forecast data
    
    Returns:
        Dict of ticker → list of forecast dicts
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    return data


def save_trend_analysis(result: TrendAnalysisResult, output_path: str):
    """
    Save trend analysis result to JSON file.
    
    Args:
        result: TrendAnalysisResult to save
        output_path: Output file path
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(result.to_json())
    
    logger.info(f"💾 Trend analysis saved to {output_path}")


# =============================================================================
# MAIN EXECUTION (FOR TESTING)
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    
    print("=" * 80)
    print("Phase 8 — Trend Analyzer — Standalone Test")
    print("=" * 80)
    
    # Generate mock forecast data
    tickers = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL"]
    forecast_data = {}
    
    for ticker in tickers:
        forecasts = []
        base_return = np.random.uniform(-0.05, 0.15)
        
        for day in range(30):
            forecast = {
                'timestamp': (datetime.now(timezone.utc) - timedelta(days=30-day)).isoformat(),
                'expected_return': base_return + np.random.normal(0, 0.02)
            }
            forecasts.append(forecast)
        
        forecast_data[ticker] = forecasts
    
    # Analyze trends
    analyzer = TrendAnalyzer(short_window=7, long_window=30, stability_threshold=0.7)
    result = analyzer.analyze_trends(forecast_data, compute_correlations=True)
    
    # Print results
    print(f"\n📊 Analysis ID: {result.analysis_id}")
    print(f"📅 Timestamp: {result.timestamp}")
    print(f"📈 Tickers Analyzed: {len(result.tickers)}")
    
    print("\n🔍 Trend Signals:")
    df = result.to_dataframe()
    print(df.to_string(index=False))
    
    print(f"\n✅ Trend analysis complete!")
    print(f"   JSON size: {len(result.to_json())} bytes")
