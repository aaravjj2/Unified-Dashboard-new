"""
Phase 8 — Data Integrity Tests
===============================

Validate data integrity across Phase 8 analytics modules.

Test Coverage:
- Trend analyzer: Input/output schema compliance
- Volatility heatmap: Metric calculation accuracy
- Risk dashboard: PSI computation correctness
- Cache telemetry: Hit/miss tracking accuracy
"""

import pytest
import json
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Import Phase 8 modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phase8_analytics.trend_analyzer import (
    TrendAnalyzer,
    TrendSignal,
    TrendAnalysisResult
)

from phase8_analytics.volatility_heatmap import (
    VolatilityHeatmap,
    VolatilityMetrics,
    HeatmapData
)

from phase8_analytics.risk_dashboard import (
    RiskDashboard,
    PortfolioStabilityIndex,
    RiskDashboardSnapshot
)

from phase8_analytics.cache_telemetry import (
    CacheTelemetryCollector,
    CacheTelemetryReport
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_forecast_data():
    """Generate sample forecast data for trend analysis."""
    tickers = ["AAPL", "TSLA", "NVDA"]
    forecast_data = {}
    
    for ticker in tickers:
        forecasts = []
        base_return = 0.10
        
        for day in range(30):
            forecast = {
                'timestamp': (datetime.now(timezone.utc) - timedelta(days=30-day)).isoformat(),
                'expected_return': base_return + np.random.normal(0, 0.02)
            }
            forecasts.append(forecast)
        
        forecast_data[ticker] = forecasts
    
    return forecast_data


@pytest.fixture
def sample_price_data():
    """Generate sample price data for volatility analysis."""
    tickers = ["AAPL", "TSLA", "NVDA"]
    price_data = {}
    
    for ticker in tickers:
        # Generate 30 days of returns
        returns = list(np.random.normal(0.001, 0.02, 30))
        price_data[ticker] = returns
    
    return price_data


@pytest.fixture
def sample_options_data():
    """Generate sample options data."""
    return {
        "AAPL": {
            'implied_volatility': 0.25,
            'delta': 0.5,
            'gamma': 0.05
        },
        "TSLA": {
            'implied_volatility': 0.45,
            'delta': 0.6,
            'gamma': 0.08
        },
        "NVDA": {
            'implied_volatility': 0.35,
            'delta': 0.55,
            'gamma': 0.06
        }
    }


# =============================================================================
# TEST: TREND ANALYZER DATA INTEGRITY
# =============================================================================

class TestTrendAnalyzerDataIntegrity:
    """Test trend analyzer data integrity and schema compliance."""
    
    def test_trend_analysis_result_schema(self, sample_forecast_data):
        """Test that TrendAnalysisResult follows expected schema."""
        analyzer = TrendAnalyzer(short_window=7, long_window=30)
        result = analyzer.analyze_trends(sample_forecast_data, compute_correlations=True)
        
        # Check result schema
        assert hasattr(result, 'analysis_id')
        assert hasattr(result, 'timestamp')
        assert hasattr(result, 'tickers')
        assert hasattr(result, 'signals')
        assert hasattr(result, 'correlation_matrix')
        assert hasattr(result, 'moving_avg_7d')
        assert hasattr(result, 'moving_avg_30d')
        assert hasattr(result, 'metadata')
        
        # Check analysis_id format (16-char hex)
        assert len(result.analysis_id) == 16
        assert all(c in '0123456789abcdef' for c in result.analysis_id)
        
        # Check tickers match input
        assert set(result.tickers) == set(sample_forecast_data.keys())
        
        # Check signals exist for all tickers
        assert len(result.signals) == len(sample_forecast_data)
        for ticker in sample_forecast_data.keys():
            assert ticker in result.signals
    
    def test_trend_signal_schema(self, sample_forecast_data):
        """Test that TrendSignal follows expected schema."""
        analyzer = TrendAnalyzer(short_window=7, long_window=30)
        result = analyzer.analyze_trends(sample_forecast_data)
        
        for ticker, signal in result.signals.items():
            # Check signal attributes
            assert hasattr(signal, 'ticker')
            assert hasattr(signal, 'timestamp')
            assert hasattr(signal, 'trend_label')
            assert hasattr(signal, 'slope_7d')
            assert hasattr(signal, 'slope_30d')
            assert hasattr(signal, 'stability_index')
            assert hasattr(signal, 'correlation_cluster')
            assert hasattr(signal, 'metadata')
            
            # Check trend_label values
            assert signal.trend_label in ['Bullish', 'Neutral', 'Bearish']
            
            # Check stability_index range (0-1)
            assert 0.0 <= signal.stability_index <= 1.0
            
            # Check metadata
            assert 'forecast_count' in signal.metadata
            assert 'mean_return' in signal.metadata
            assert 'std_return' in signal.metadata
    
    def test_trend_analysis_json_serialization(self, sample_forecast_data):
        """Test that TrendAnalysisResult can be serialized to JSON."""
        analyzer = TrendAnalyzer()
        result = analyzer.analyze_trends(sample_forecast_data)
        
        # Serialize to JSON
        json_str = result.to_json()
        
        # Deserialize and check
        data = json.loads(json_str)
        
        assert 'analysis_id' in data
        assert 'tickers' in data
        assert 'signals' in data
        assert isinstance(data['signals'], dict)
        
        # Check that all values are JSON-serializable (no numpy types)
        for ticker, signal_dict in data['signals'].items():
            assert isinstance(signal_dict['slope_7d'], (int, float))
            assert isinstance(signal_dict['slope_30d'], (int, float))
            assert isinstance(signal_dict['stability_index'], (int, float))
    
    def test_moving_averages_calculation(self, sample_forecast_data):
        """Test that moving averages are calculated correctly."""
        analyzer = TrendAnalyzer(short_window=7, long_window=30)
        result = analyzer.analyze_trends(sample_forecast_data)
        
        for ticker in sample_forecast_data.keys():
            returns = [f['expected_return'] for f in sample_forecast_data[ticker]]
            
            # Expected 7-day average
            expected_7d = np.mean(returns[-7:])
            
            # Check computed value (with tolerance)
            assert abs(result.moving_avg_7d[ticker] - expected_7d) < 1e-6


# =============================================================================
# TEST: VOLATILITY HEATMAP DATA INTEGRITY
# =============================================================================

class TestVolatilityHeatmapDataIntegrity:
    """Test volatility heatmap data integrity and calculations."""
    
    def test_volatility_metrics_schema(self, sample_price_data, sample_options_data):
        """Test that VolatilityMetrics follows expected schema."""
        heatmap_gen = VolatilityHeatmap(risk_free_rate=0.04, trading_days=252)
        metrics = heatmap_gen.analyze_volatility(sample_price_data, sample_options_data)
        
        for ticker, m in metrics.items():
            # Check attributes
            assert hasattr(m, 'ticker')
            assert hasattr(m, 'timestamp')
            assert hasattr(m, 'annualized_volatility')
            assert hasattr(m, 'implied_volatility')
            assert hasattr(m, 'delta_cluster')
            assert hasattr(m, 'gamma_cluster')
            assert hasattr(m, 'sharpe_ratio')
            assert hasattr(m, 'metadata')
            
            # Check cluster range (0-4)
            assert 0 <= m.delta_cluster <= 4
            assert 0 <= m.gamma_cluster <= 4
            
            # Check implied volatility matches input
            if m.implied_volatility is not None:
                assert abs(m.implied_volatility - sample_options_data[ticker]['implied_volatility']) < 1e-6
    
    def test_annualized_volatility_calculation(self, sample_price_data):
        """Test that annualized volatility is calculated correctly."""
        heatmap_gen = VolatilityHeatmap(risk_free_rate=0.04, trading_days=252)
        metrics = heatmap_gen.analyze_volatility(sample_price_data)
        
        for ticker, m in metrics.items():
            returns = sample_price_data[ticker]
            
            # Expected annualized volatility
            daily_vol = np.std(returns)
            expected_ann_vol = daily_vol * np.sqrt(252)
            
            # Check computed value (with tolerance)
            assert abs(m.annualized_volatility - expected_ann_vol) < 1e-6
    
    def test_heatmap_data_schema(self, sample_price_data, sample_options_data):
        """Test that HeatmapData follows expected schema."""
        heatmap_gen = VolatilityHeatmap()
        metrics = heatmap_gen.analyze_volatility(sample_price_data, sample_options_data)
        
        heatmap_data = heatmap_gen.generate_heatmap(metrics, heatmap_type="volatility")
        
        # Check attributes
        assert hasattr(heatmap_data, 'heatmap_id')
        assert hasattr(heatmap_data, 'timestamp')
        assert hasattr(heatmap_data, 'heatmap_type')
        assert hasattr(heatmap_data, 'tickers')
        assert hasattr(heatmap_data, 'metrics')
        assert hasattr(heatmap_data, 'values')
        assert hasattr(heatmap_data, 'color_scale')
        assert hasattr(heatmap_data, 'metadata')
        
        # Check heatmap_type
        assert heatmap_data.heatmap_type == "volatility"
        
        # Check values shape (tickers × metrics)
        assert len(heatmap_data.values) == len(heatmap_data.tickers)
        assert len(heatmap_data.values[0]) == len(heatmap_data.metrics)
        
        # Check color_scale
        assert 'min' in heatmap_data.color_scale
        assert 'max' in heatmap_data.color_scale
        assert 'colors' in heatmap_data.color_scale


# =============================================================================
# TEST: RISK DASHBOARD DATA INTEGRITY
# =============================================================================

class TestRiskDashboardDataIntegrity:
    """Test risk dashboard data integrity and PSI calculations."""
    
    def test_psi_calculation(self, sample_forecast_data, sample_price_data, sample_options_data):
        """Test that PSI is calculated correctly."""
        # Generate trend result
        trend_analyzer = TrendAnalyzer()
        trend_result = trend_analyzer.analyze_trends(sample_forecast_data, compute_correlations=True)
        
        # Generate volatility metrics
        volatility_gen = VolatilityHeatmap()
        volatility_metrics = volatility_gen.analyze_volatility(sample_price_data, sample_options_data)
        
        # Generate dashboard
        dashboard = RiskDashboard(
            psi_volatility_weight=0.4,
            psi_trend_weight=0.35,
            psi_correlation_weight=0.25
        )
        
        snapshot = dashboard.generate_dashboard_snapshot(trend_result, volatility_metrics)
        
        # Check PSI schema
        psi = snapshot.psi
        assert hasattr(psi, 'psi_score')
        assert hasattr(psi, 'volatility_score')
        assert hasattr(psi, 'trend_score')
        assert hasattr(psi, 'correlation_score')
        assert hasattr(psi, 'risk_level')
        
        # Check PSI score range (0-100)
        assert 0.0 <= psi.psi_score <= 100.0
        assert 0.0 <= psi.volatility_score <= 100.0
        assert 0.0 <= psi.trend_score <= 100.0
        assert 0.0 <= psi.correlation_score <= 100.0
        
        # Check risk_level
        assert psi.risk_level in ['Low', 'Medium', 'High']
        
        # Verify weighted sum
        expected_psi = (
            0.4 * psi.volatility_score +
            0.35 * psi.trend_score +
            0.25 * psi.correlation_score
        )
        assert abs(psi.psi_score - expected_psi) < 1e-6
    
    def test_dashboard_snapshot_schema(self, sample_forecast_data, sample_price_data, sample_options_data):
        """Test that RiskDashboardSnapshot follows expected schema."""
        # Generate inputs
        trend_analyzer = TrendAnalyzer()
        trend_result = trend_analyzer.analyze_trends(sample_forecast_data)
        
        volatility_gen = VolatilityHeatmap()
        volatility_metrics = volatility_gen.analyze_volatility(sample_price_data, sample_options_data)
        
        # Generate snapshot
        dashboard = RiskDashboard()
        snapshot = dashboard.generate_dashboard_snapshot(trend_result, volatility_metrics)
        
        # Check schema
        assert hasattr(snapshot, 'snapshot_id')
        assert hasattr(snapshot, 'timestamp')
        assert hasattr(snapshot, 'psi')
        assert hasattr(snapshot, 'trend_summary')
        assert hasattr(snapshot, 'volatility_summary')
        assert hasattr(snapshot, 'risk_return_data')
        assert hasattr(snapshot, 'volatility_bands')
        assert hasattr(snapshot, 'metadata')
        
        # Check trend_summary
        assert 'bullish_count' in snapshot.trend_summary
        assert 'neutral_count' in snapshot.trend_summary
        assert 'bearish_count' in snapshot.trend_summary
        
        # Check volatility_summary
        assert 'avg_annualized_volatility' in snapshot.volatility_summary
        assert 'avg_sharpe_ratio' in snapshot.volatility_summary


# =============================================================================
# TEST: CACHE TELEMETRY DATA INTEGRITY
# =============================================================================

class TestCacheTelemetryDataIntegrity:
    """Test cache telemetry data integrity and tracking accuracy."""
    
    def test_hit_miss_tracking(self):
        """Test that hit/miss tracking is accurate."""
        collector = CacheTelemetryCollector()
        
        # Record 10 hits, 5 misses
        for i in range(10):
            collector.record_cache_request(f"key_{i}", is_hit=True, cache_level="L1", latency_ms=0.1)
        
        for i in range(5):
            collector.record_cache_request(f"key_{i+10}", is_hit=False, cache_level="MISS", latency_ms=100.0)
        
        # Generate report
        report = collector.generate_report()
        
        # Check hit/miss counts
        assert report.hit_metrics.total_requests == 15
        assert report.hit_metrics.hits == 10
        assert report.hit_metrics.misses == 5
        assert abs(report.hit_metrics.hit_rate - 10/15) < 1e-6
    
    def test_cache_level_breakdown(self):
        """Test that cache level breakdown is accurate."""
        collector = CacheTelemetryCollector()
        
        # Record hits at different cache levels
        collector.record_cache_request("key_1", is_hit=True, cache_level="L1", latency_ms=0.1)
        collector.record_cache_request("key_2", is_hit=True, cache_level="L1", latency_ms=0.1)
        collector.record_cache_request("key_3", is_hit=True, cache_level="L2", latency_ms=20.0)
        collector.record_cache_request("key_4", is_hit=True, cache_level="L3", latency_ms=80.0)
        
        # Generate report
        report = collector.generate_report()
        
        # Check cache level breakdown
        assert report.hit_metrics.l1_hits == 2
        assert report.hit_metrics.l2_hits == 1
        assert report.hit_metrics.l3_hits == 1
    
    def test_latency_metrics(self):
        """Test that latency metrics are calculated correctly."""
        collector = CacheTelemetryCollector()
        
        # Record latencies: [10, 20, 30, 40, 50]
        latencies = [10.0, 20.0, 30.0, 40.0, 50.0]
        
        for i, latency in enumerate(latencies):
            collector.record_cache_request(f"key_{i}", is_hit=True, cache_level="L1", latency_ms=latency)
        
        # Generate report
        report = collector.generate_report()
        
        # Check latency metrics
        assert report.latency_metrics.mean == 30.0
        assert report.latency_metrics.min == 10.0
        assert report.latency_metrics.max == 50.0
        assert report.latency_metrics.p50 == 30.0
    
    def test_determinism_validation(self):
        """Test that determinism validation works correctly."""
        collector = CacheTelemetryCollector(determinism_threshold=1e-6)
        
        # Record 3 runs for deterministic key
        for _ in range(3):
            collector.record_determinism_run("deterministic_key", {'value': 100, 'timestamp': '2025-01-01T00:00:00Z'})
        
        # Record 3 runs for non-deterministic key
        for i in range(3):
            collector.record_determinism_run("non_deterministic_key", {'value': 100 + i, 'timestamp': '2025-01-01T00:00:00Z'})
        
        # Generate report
        report = collector.generate_report()
        
        # Check determinism records
        assert len(report.determinism_records) == 2
        
        # Find deterministic and non-deterministic records
        deterministic_record = next(r for r in report.determinism_records if r.cache_key == "deterministic_key")
        non_deterministic_record = next(r for r in report.determinism_records if r.cache_key == "non_deterministic_key")
        
        # Check deterministic record
        assert deterministic_record.is_deterministic == True
        assert deterministic_record.variance == 0.0
        
        # Check non-deterministic record
        assert non_deterministic_record.is_deterministic == False
        assert non_deterministic_record.variance > 0.0


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
