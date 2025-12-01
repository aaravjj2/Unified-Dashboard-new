"""
Phase 8 — Risk Dashboard Module
================================

Unified risk dashboard integrating trend and volatility analytics.

Key Features:
- Portfolio Stability Index (PSI)
- Risk-return scatterplots
- Volatility band visualizations
- Unified dashboard snapshot (JSON export)
- Integration with trend_analyzer and volatility_heatmap

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0 (Phase 8)
"""

import json
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Import Phase 8 analytics modules
try:
    from phase8_analytics.trend_analyzer import TrendAnalyzer, TrendAnalysisResult
    from phase8_analytics.volatility_heatmap import VolatilityHeatmap, VolatilityMetrics
except ImportError:
    # Fallback for testing
    TrendAnalyzer = None
    TrendAnalysisResult = None
    VolatilityHeatmap = None
    VolatilityMetrics = None

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class PortfolioStabilityIndex:
    """
    Portfolio Stability Index (PSI) metrics.
    
    Attributes:
        psi_score: Overall stability score (0-100)
        volatility_score: Volatility component (0-100)
        trend_score: Trend stability component (0-100)
        correlation_score: Correlation diversity component (0-100)
        risk_level: Risk classification (Low|Medium|High)
        metadata: Additional metrics
    """
    psi_score: float
    volatility_score: float
    trend_score: float
    correlation_score: float
    risk_level: str
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), separators=(',', ':'))


@dataclass
class RiskDashboardSnapshot:
    """
    Complete risk dashboard snapshot.
    
    Attributes:
        snapshot_id: Unique snapshot identifier
        timestamp: Snapshot timestamp
        psi: Portfolio Stability Index
        trend_summary: Trend analysis summary
        volatility_summary: Volatility metrics summary
        risk_return_data: Risk-return scatterplot data
        volatility_bands: Volatility band data
        metadata: Additional snapshot metadata
    """
    snapshot_id: str
    timestamp: str
    psi: PortfolioStabilityIndex
    trend_summary: Dict[str, Any]
    volatility_summary: Dict[str, Any]
    risk_return_data: List[Dict[str, Any]]
    volatility_bands: Dict[str, List[float]]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            'snapshot_id': self.snapshot_id,
            'timestamp': self.timestamp,
            'psi': self.psi.to_dict(),
            'trend_summary': self.trend_summary,
            'volatility_summary': self.volatility_summary,
            'risk_return_data': self.risk_return_data,
            'volatility_bands': self.volatility_bands,
            'metadata': self.metadata
        }
    
    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


# =============================================================================
# RISK DASHBOARD
# =============================================================================

class RiskDashboard:
    """
    Unified risk dashboard controller.
    
    Integrates trend analysis and volatility heatmaps to generate
    portfolio stability metrics and risk visualizations.
    
    Workflow:
    1. Load trend and volatility data
    2. Compute Portfolio Stability Index (PSI)
    3. Generate risk-return scatterplot
    4. Create volatility bands
    5. Export unified dashboard snapshot
    """
    
    def __init__(self,
                 psi_volatility_weight: float = 0.4,
                 psi_trend_weight: float = 0.35,
                 psi_correlation_weight: float = 0.25):
        """
        Initialize risk dashboard.
        
        Args:
            psi_volatility_weight: Weight for volatility in PSI calculation
            psi_trend_weight: Weight for trend stability in PSI calculation
            psi_correlation_weight: Weight for correlation diversity in PSI calculation
        """
        self.psi_volatility_weight = psi_volatility_weight
        self.psi_trend_weight = psi_trend_weight
        self.psi_correlation_weight = psi_correlation_weight
        
        logger.info(
            f"🔧 RiskDashboard initialized "
            f"(PSI weights: vol={psi_volatility_weight}, trend={psi_trend_weight}, corr={psi_correlation_weight})"
        )
    
    def generate_dashboard_snapshot(self,
                                    trend_result: Any,  # TrendAnalysisResult
                                    volatility_metrics: Dict[str, Any]) -> RiskDashboardSnapshot:
        """
        Generate unified dashboard snapshot.
        
        Args:
            trend_result: TrendAnalysisResult from trend_analyzer
            volatility_metrics: Dict of ticker → VolatilityMetrics from volatility_heatmap
        
        Returns:
            RiskDashboardSnapshot with PSI and risk visualizations
        """
        logger.info("📊 Generating risk dashboard snapshot...")
        
        # Step 1: Compute Portfolio Stability Index
        psi = self._compute_psi(trend_result, volatility_metrics)
        
        # Step 2: Generate trend summary
        trend_summary = self._generate_trend_summary(trend_result)
        
        # Step 3: Generate volatility summary
        volatility_summary = self._generate_volatility_summary(volatility_metrics)
        
        # Step 4: Generate risk-return scatterplot data
        risk_return_data = self._generate_risk_return_data(trend_result, volatility_metrics)
        
        # Step 5: Generate volatility bands
        volatility_bands = self._generate_volatility_bands(volatility_metrics)
        
        # Step 6: Create snapshot
        snapshot_id = hashlib.sha256(
            f"{datetime.now(timezone.utc).isoformat()}:{psi.psi_score}".encode()
        ).hexdigest()[:16]
        
        snapshot = RiskDashboardSnapshot(
            snapshot_id=snapshot_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            psi=psi,
            trend_summary=trend_summary,
            volatility_summary=volatility_summary,
            risk_return_data=risk_return_data,
            volatility_bands=volatility_bands,
            metadata={
                'tickers_analyzed': len(volatility_metrics),
                'psi_weights': {
                    'volatility': self.psi_volatility_weight,
                    'trend': self.psi_trend_weight,
                    'correlation': self.psi_correlation_weight
                }
            }
        )
        
        logger.info(
            f"✅ Dashboard snapshot generated: PSI = {psi.psi_score:.1f} ({psi.risk_level})"
        )
        
        return snapshot
    
    def _compute_psi(self, trend_result: Any, volatility_metrics: Dict[str, Any]) -> PortfolioStabilityIndex:
        """Compute Portfolio Stability Index."""
        
        # Volatility component: Lower volatility = higher score
        volatilities = [
            m.annualized_volatility if hasattr(m, 'annualized_volatility') else m.get('annualized_volatility', 0.0)
            for m in volatility_metrics.values()
        ]
        avg_volatility = np.mean(volatilities) if volatilities else 0.5
        volatility_score = max(0, min(100, 100 * (1.0 - avg_volatility)))
        
        # Trend component: Higher stability index = higher score
        if hasattr(trend_result, 'signals'):
            trend_signals = trend_result.signals
            trend_stabilities = [
                s.stability_index if hasattr(s, 'stability_index') else s.get('stability_index', 0.0)
                for s in trend_signals.values()
            ]
            avg_stability = np.mean(trend_stabilities) if trend_stabilities else 0.5
        else:
            avg_stability = 0.5
        
        trend_score = max(0, min(100, 100 * avg_stability))
        
        # Correlation component: Lower avg correlation = higher diversity = higher score
        if hasattr(trend_result, 'correlation_matrix') and trend_result.correlation_matrix:
            corr_matrix = trend_result.correlation_matrix
            
            # Compute average off-diagonal correlation
            correlations = []
            tickers = list(corr_matrix.keys())
            for i, t1 in enumerate(tickers):
                for j, t2 in enumerate(tickers):
                    if i < j:  # Upper triangle only
                        correlations.append(abs(corr_matrix[t1][t2]))
            
            avg_correlation = np.mean(correlations) if correlations else 0.5
        else:
            avg_correlation = 0.5
        
        correlation_score = max(0, min(100, 100 * (1.0 - avg_correlation)))
        
        # Compute weighted PSI
        psi_score = (
            self.psi_volatility_weight * volatility_score +
            self.psi_trend_weight * trend_score +
            self.psi_correlation_weight * correlation_score
        )
        
        # Classify risk level
        if psi_score >= 70:
            risk_level = "Low"
        elif psi_score >= 40:
            risk_level = "Medium"
        else:
            risk_level = "High"
        
        return PortfolioStabilityIndex(
            psi_score=float(psi_score),
            volatility_score=float(volatility_score),
            trend_score=float(trend_score),
            correlation_score=float(correlation_score),
            risk_level=risk_level,
            metadata={
                'avg_volatility': float(avg_volatility),
                'avg_stability': float(avg_stability),
                'avg_correlation': float(avg_correlation)
            }
        )
    
    def _generate_trend_summary(self, trend_result: Any) -> Dict[str, Any]:
        """Generate trend analysis summary."""
        if hasattr(trend_result, 'signals'):
            signals = trend_result.signals
            
            bullish_count = sum(1 for s in signals.values() if getattr(s, 'trend_label', 'Neutral') == 'Bullish')
            neutral_count = sum(1 for s in signals.values() if getattr(s, 'trend_label', 'Neutral') == 'Neutral')
            bearish_count = sum(1 for s in signals.values() if getattr(s, 'trend_label', 'Neutral') == 'Bearish')
            
            return {
                'total_tickers': len(signals),
                'bullish_count': bullish_count,
                'neutral_count': neutral_count,
                'bearish_count': bearish_count,
                'bullish_pct': bullish_count / len(signals) * 100 if signals else 0
            }
        else:
            return {
                'total_tickers': 0,
                'bullish_count': 0,
                'neutral_count': 0,
                'bearish_count': 0,
                'bullish_pct': 0
            }
    
    def _generate_volatility_summary(self, volatility_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate volatility summary."""
        if not volatility_metrics:
            return {
                'total_tickers': 0,
                'avg_annualized_volatility': 0.0,
                'min_volatility': 0.0,
                'max_volatility': 0.0,
                'avg_sharpe_ratio': 0.0
            }
        
        volatilities = [
            m.annualized_volatility if hasattr(m, 'annualized_volatility') else m.get('annualized_volatility', 0.0)
            for m in volatility_metrics.values()
        ]
        
        sharpe_ratios = [
            m.sharpe_ratio if hasattr(m, 'sharpe_ratio') else m.get('sharpe_ratio', 0.0)
            for m in volatility_metrics.values()
        ]
        
        return {
            'total_tickers': len(volatility_metrics),
            'avg_annualized_volatility': float(np.mean(volatilities)),
            'min_volatility': float(np.min(volatilities)),
            'max_volatility': float(np.max(volatilities)),
            'avg_sharpe_ratio': float(np.mean(sharpe_ratios))
        }
    
    def _generate_risk_return_data(self, trend_result: Any, volatility_metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate risk-return scatterplot data."""
        data = []
        
        # Extract tickers
        if hasattr(trend_result, 'signals'):
            tickers = list(trend_result.signals.keys())
        else:
            tickers = list(volatility_metrics.keys())
        
        for ticker in tickers:
            # Get expected return from trend data
            if hasattr(trend_result, 'signals') and ticker in trend_result.signals:
                signal = trend_result.signals[ticker]
                expected_return = getattr(signal, 'metadata', {}).get('mean_return', 0.0)
            else:
                expected_return = 0.0
            
            # Get volatility
            if ticker in volatility_metrics:
                m = volatility_metrics[ticker]
                volatility = m.annualized_volatility if hasattr(m, 'annualized_volatility') else m.get('annualized_volatility', 0.0)
                sharpe = m.sharpe_ratio if hasattr(m, 'sharpe_ratio') else m.get('sharpe_ratio', 0.0)
            else:
                volatility = 0.0
                sharpe = 0.0
            
            data.append({
                'ticker': ticker,
                'expected_return': float(expected_return),
                'volatility': float(volatility),
                'sharpe_ratio': float(sharpe)
            })
        
        return data
    
    def _generate_volatility_bands(self, volatility_metrics: Dict[str, Any]) -> Dict[str, List[float]]:
        """Generate volatility bands (low/medium/high thresholds)."""
        volatilities = [
            m.annualized_volatility if hasattr(m, 'annualized_volatility') else m.get('annualized_volatility', 0.0)
            for m in volatility_metrics.values()
        ]
        
        if not volatilities:
            return {
                'low_threshold': [0.0],
                'medium_threshold': [0.0],
                'high_threshold': [0.0]
            }
        
        # Compute percentiles
        p33 = float(np.percentile(volatilities, 33))
        p67 = float(np.percentile(volatilities, 67))
        p100 = float(np.max(volatilities))
        
        return {
            'low_threshold': [0.0, p33],
            'medium_threshold': [p33, p67],
            'high_threshold': [p67, p100]
        }


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def save_dashboard_snapshot(snapshot: RiskDashboardSnapshot, output_path: str):
    """
    Save dashboard snapshot to JSON file.
    
    Args:
        snapshot: RiskDashboardSnapshot to save
        output_path: Output file path
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        f.write(snapshot.to_json())
    
    logger.info(f"💾 Dashboard snapshot saved to {output_path}")


# =============================================================================
# MAIN EXECUTION (FOR TESTING)
# =============================================================================

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
    
    print("=" * 80)
    print("Phase 8 — Risk Dashboard — Standalone Test")
    print("=" * 80)
    
    # Generate mock trend data
    class MockTrendSignal:
        def __init__(self, ticker, trend_label, stability_index, mean_return):
            self.ticker = ticker
            self.trend_label = trend_label
            self.stability_index = stability_index
            self.metadata = {'mean_return': mean_return}
    
    class MockTrendResult:
        def __init__(self):
            self.signals = {
                'AAPL': MockTrendSignal('AAPL', 'Bullish', 0.8, 0.12),
                'TSLA': MockTrendSignal('TSLA', 'Neutral', 0.6, 0.05),
                'NVDA': MockTrendSignal('NVDA', 'Bullish', 0.75, 0.15),
                'MSFT': MockTrendSignal('MSFT', 'Bullish', 0.85, 0.10),
                'GOOGL': MockTrendSignal('GOOGL', 'Bearish', 0.5, -0.03)
            }
            self.correlation_matrix = {
                'AAPL': {'AAPL': 1.0, 'TSLA': 0.3, 'NVDA': 0.5, 'MSFT': 0.7, 'GOOGL': 0.4},
                'TSLA': {'AAPL': 0.3, 'TSLA': 1.0, 'NVDA': 0.4, 'MSFT': 0.2, 'GOOGL': 0.1},
                'NVDA': {'AAPL': 0.5, 'TSLA': 0.4, 'NVDA': 1.0, 'MSFT': 0.6, 'GOOGL': 0.3},
                'MSFT': {'AAPL': 0.7, 'TSLA': 0.2, 'NVDA': 0.6, 'MSFT': 1.0, 'GOOGL': 0.5},
                'GOOGL': {'AAPL': 0.4, 'TSLA': 0.1, 'NVDA': 0.3, 'MSFT': 0.5, 'GOOGL': 1.0}
            }
    
    # Generate mock volatility data
    class MockVolatilityMetrics:
        def __init__(self, ticker, ann_vol, sharpe):
            self.ticker = ticker
            self.annualized_volatility = ann_vol
            self.sharpe_ratio = sharpe
    
    volatility_metrics = {
        'AAPL': MockVolatilityMetrics('AAPL', 0.25, 1.2),
        'TSLA': MockVolatilityMetrics('TSLA', 0.45, 0.5),
        'NVDA': MockVolatilityMetrics('NVDA', 0.35, 1.5),
        'MSFT': MockVolatilityMetrics('MSFT', 0.20, 1.0),
        'GOOGL': MockVolatilityMetrics('GOOGL', 0.30, -0.2)
    }
    
    # Generate dashboard
    dashboard = RiskDashboard(
        psi_volatility_weight=0.4,
        psi_trend_weight=0.35,
        psi_correlation_weight=0.25
    )
    
    snapshot = dashboard.generate_dashboard_snapshot(MockTrendResult(), volatility_metrics)
    
    # Print results
    print(f"\n📊 Dashboard Snapshot:")
    print(f"   ID: {snapshot.snapshot_id}")
    print(f"   Timestamp: {snapshot.timestamp}")
    print(f"\n📈 Portfolio Stability Index (PSI):")
    print(f"   Overall Score: {snapshot.psi.psi_score:.1f} ({snapshot.psi.risk_level})")
    print(f"   Volatility Score: {snapshot.psi.volatility_score:.1f}")
    print(f"   Trend Score: {snapshot.psi.trend_score:.1f}")
    print(f"   Correlation Score: {snapshot.psi.correlation_score:.1f}")
    
    print(f"\n🎯 Trend Summary:")
    print(f"   Bullish: {snapshot.trend_summary['bullish_count']} ({snapshot.trend_summary['bullish_pct']:.1f}%)")
    print(f"   Neutral: {snapshot.trend_summary['neutral_count']}")
    print(f"   Bearish: {snapshot.trend_summary['bearish_count']}")
    
    print(f"\n💥 Volatility Summary:")
    print(f"   Avg Volatility: {snapshot.volatility_summary['avg_annualized_volatility']:.2%}")
    print(f"   Avg Sharpe: {snapshot.volatility_summary['avg_sharpe_ratio']:.2f}")
    
    print(f"\n✅ Dashboard snapshot complete!")
    print(f"   JSON size: {len(snapshot.to_json())} bytes")
