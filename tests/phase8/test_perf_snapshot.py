"""
Phase 8 — Performance Tests
============================

Validate performance benchmarks for Phase 8 analytics modules.

Performance SLAs:
- Trend analysis: <150ms per portfolio
- Volatility heatmap generation: <150ms per heatmap
- Risk dashboard snapshot: <150ms per snapshot
- Cache telemetry report: <50ms per report

Test Coverage:
- Single-ticker performance
- Portfolio-scale performance (10 tickers)
- Large-scale performance (100 tickers)
"""

import pytest
import time
import numpy as np
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Import Phase 8 modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from phase8_analytics.trend_analyzer import TrendAnalyzer
from phase8_analytics.volatility_heatmap import VolatilityHeatmap
from phase8_analytics.risk_dashboard import RiskDashboard
from phase8_analytics.cache_telemetry import CacheTelemetryCollector


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def small_forecast_data():
    """Generate small forecast data (3 tickers, 30 days)."""
    return generate_forecast_data(n_tickers=3, n_days=30)


@pytest.fixture
def medium_forecast_data():
    """Generate medium forecast data (10 tickers, 30 days)."""
    return generate_forecast_data(n_tickers=10, n_days=30)


@pytest.fixture
def large_forecast_data():
    """Generate large forecast data (100 tickers, 30 days)."""
    return generate_forecast_data(n_tickers=100, n_days=30)


def generate_forecast_data(n_tickers: int, n_days: int):
    """Helper to generate forecast data."""
    forecast_data = {}
    
    for i in range(n_tickers):
        ticker = f"TICKER_{i}"
        forecasts = []
        base_return = np.random.uniform(-0.05, 0.15)
        
        for day in range(n_days):
            forecast = {
                'timestamp': (datetime.now(timezone.utc) - timedelta(days=n_days-day)).isoformat(),
                'expected_return': base_return + np.random.normal(0, 0.02)
            }
            forecasts.append(forecast)
        
        forecast_data[ticker] = forecasts
    
    return forecast_data


def generate_price_data(n_tickers: int, n_days: int = 30):
    """Helper to generate price data."""
    price_data = {}
    
    for i in range(n_tickers):
        ticker = f"TICKER_{i}"
        returns = list(np.random.normal(0.001, 0.02, n_days))
        price_data[ticker] = returns
    
    return price_data


def generate_options_data(n_tickers: int):
    """Helper to generate options data."""
    options_data = {}
    
    for i in range(n_tickers):
        ticker = f"TICKER_{i}"
        options_data[ticker] = {
            'implied_volatility': float(np.random.uniform(0.2, 0.8)),
            'delta': float(np.random.uniform(0.3, 0.7)),
            'gamma': float(np.random.uniform(0.01, 0.1))
        }
    
    return options_data


# =============================================================================
# TEST: TREND ANALYZER PERFORMANCE
# =============================================================================

class TestTrendAnalyzerPerformance:
    """Test trend analyzer performance benchmarks."""
    
    def test_small_portfolio_performance(self, small_forecast_data):
        """Test trend analysis for small portfolio (3 tickers)."""
        analyzer = TrendAnalyzer()
        
        start_time = time.perf_counter()
        result = analyzer.analyze_trends(small_forecast_data, compute_correlations=True)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        print(f"\n⏱️  Small portfolio (3 tickers): {elapsed_ms:.2f}ms")
        
        # Check performance SLA: <150ms
        assert elapsed_ms < 150.0, f"Trend analysis took {elapsed_ms:.2f}ms (expected <150ms)"
    
    def test_medium_portfolio_performance(self, medium_forecast_data):
        """Test trend analysis for medium portfolio (10 tickers)."""
        analyzer = TrendAnalyzer()
        
        start_time = time.perf_counter()
        result = analyzer.analyze_trends(medium_forecast_data, compute_correlations=True)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        print(f"\n⏱️  Medium portfolio (10 tickers): {elapsed_ms:.2f}ms")
        
        # Check performance SLA: <150ms
        assert elapsed_ms < 150.0, f"Trend analysis took {elapsed_ms:.2f}ms (expected <150ms)"
    
    @pytest.mark.slow
    def test_large_portfolio_performance(self, large_forecast_data):
        """Test trend analysis for large portfolio (100 tickers)."""
        analyzer = TrendAnalyzer()
        
        start_time = time.perf_counter()
        result = analyzer.analyze_trends(large_forecast_data, compute_correlations=True)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        print(f"\n⏱️  Large portfolio (100 tickers): {elapsed_ms:.2f}ms")
        
        # Relaxed SLA for large portfolios: <500ms
        assert elapsed_ms < 500.0, f"Trend analysis took {elapsed_ms:.2f}ms (expected <500ms)"


# =============================================================================
# TEST: VOLATILITY HEATMAP PERFORMANCE
# =============================================================================

class TestVolatilityHeatmapPerformance:
    """Test volatility heatmap performance benchmarks."""
    
    def test_small_heatmap_generation(self):
        """Test heatmap generation for small portfolio (3 tickers)."""
        price_data = generate_price_data(n_tickers=3)
        options_data = generate_options_data(n_tickers=3)
        
        heatmap_gen = VolatilityHeatmap()
        
        # Analyze volatility
        start_time = time.perf_counter()
        metrics = heatmap_gen.analyze_volatility(price_data, options_data)
        elapsed_analysis_ms = (time.perf_counter() - start_time) * 1000
        
        # Generate heatmap
        start_time = time.perf_counter()
        heatmap_data = heatmap_gen.generate_heatmap(metrics, heatmap_type="volatility")
        elapsed_heatmap_ms = (time.perf_counter() - start_time) * 1000
        
        total_ms = elapsed_analysis_ms + elapsed_heatmap_ms
        
        print(f"\n⏱️  Small heatmap (3 tickers): {total_ms:.2f}ms (analysis: {elapsed_analysis_ms:.2f}ms, heatmap: {elapsed_heatmap_ms:.2f}ms)")
        
        # Check performance SLA: <150ms total
        assert total_ms < 150.0, f"Heatmap generation took {total_ms:.2f}ms (expected <150ms)"
    
    def test_medium_heatmap_generation(self):
        """Test heatmap generation for medium portfolio (10 tickers)."""
        price_data = generate_price_data(n_tickers=10)
        options_data = generate_options_data(n_tickers=10)
        
        heatmap_gen = VolatilityHeatmap()
        
        # Analyze volatility
        start_time = time.perf_counter()
        metrics = heatmap_gen.analyze_volatility(price_data, options_data)
        elapsed_analysis_ms = (time.perf_counter() - start_time) * 1000
        
        # Generate heatmap
        start_time = time.perf_counter()
        heatmap_data = heatmap_gen.generate_heatmap(metrics, heatmap_type="volatility")
        elapsed_heatmap_ms = (time.perf_counter() - start_time) * 1000
        
        total_ms = elapsed_analysis_ms + elapsed_heatmap_ms
        
        print(f"\n⏱️  Medium heatmap (10 tickers): {total_ms:.2f}ms (analysis: {elapsed_analysis_ms:.2f}ms, heatmap: {elapsed_heatmap_ms:.2f}ms)")
        
        # Check performance SLA: <150ms total
        assert total_ms < 150.0, f"Heatmap generation took {total_ms:.2f}ms (expected <150ms)"
    
    @pytest.mark.slow
    def test_large_heatmap_generation(self):
        """Test heatmap generation for large portfolio (100 tickers)."""
        price_data = generate_price_data(n_tickers=100)
        options_data = generate_options_data(n_tickers=100)
        
        heatmap_gen = VolatilityHeatmap()
        
        # Analyze volatility
        start_time = time.perf_counter()
        metrics = heatmap_gen.analyze_volatility(price_data, options_data)
        elapsed_analysis_ms = (time.perf_counter() - start_time) * 1000
        
        # Generate heatmap
        start_time = time.perf_counter()
        heatmap_data = heatmap_gen.generate_heatmap(metrics, heatmap_type="volatility")
        elapsed_heatmap_ms = (time.perf_counter() - start_time) * 1000
        
        total_ms = elapsed_analysis_ms + elapsed_heatmap_ms
        
        print(f"\n⏱️  Large heatmap (100 tickers): {total_ms:.2f}ms (analysis: {elapsed_analysis_ms:.2f}ms, heatmap: {elapsed_heatmap_ms:.2f}ms)")
        
        # Relaxed SLA for large portfolios: <500ms
        assert total_ms < 500.0, f"Heatmap generation took {total_ms:.2f}ms (expected <500ms)"


# =============================================================================
# TEST: RISK DASHBOARD PERFORMANCE
# =============================================================================

class TestRiskDashboardPerformance:
    """Test risk dashboard performance benchmarks."""
    
    def test_small_dashboard_snapshot(self):
        """Test dashboard snapshot for small portfolio (3 tickers)."""
        # Generate inputs
        forecast_data = generate_forecast_data(n_tickers=3, n_days=30)
        price_data = generate_price_data(n_tickers=3)
        options_data = generate_options_data(n_tickers=3)
        
        # Analyze trend and volatility
        trend_analyzer = TrendAnalyzer()
        trend_result = trend_analyzer.analyze_trends(forecast_data, compute_correlations=True)
        
        volatility_gen = VolatilityHeatmap()
        volatility_metrics = volatility_gen.analyze_volatility(price_data, options_data)
        
        # Generate dashboard snapshot
        dashboard = RiskDashboard()
        
        start_time = time.perf_counter()
        snapshot = dashboard.generate_dashboard_snapshot(trend_result, volatility_metrics)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        print(f"\n⏱️  Small dashboard (3 tickers): {elapsed_ms:.2f}ms")
        
        # Check performance SLA: <150ms
        assert elapsed_ms < 150.0, f"Dashboard snapshot took {elapsed_ms:.2f}ms (expected <150ms)"
    
    def test_medium_dashboard_snapshot(self):
        """Test dashboard snapshot for medium portfolio (10 tickers)."""
        # Generate inputs
        forecast_data = generate_forecast_data(n_tickers=10, n_days=30)
        price_data = generate_price_data(n_tickers=10)
        options_data = generate_options_data(n_tickers=10)
        
        # Analyze trend and volatility
        trend_analyzer = TrendAnalyzer()
        trend_result = trend_analyzer.analyze_trends(forecast_data, compute_correlations=True)
        
        volatility_gen = VolatilityHeatmap()
        volatility_metrics = volatility_gen.analyze_volatility(price_data, options_data)
        
        # Generate dashboard snapshot
        dashboard = RiskDashboard()
        
        start_time = time.perf_counter()
        snapshot = dashboard.generate_dashboard_snapshot(trend_result, volatility_metrics)
        elapsed_ms = (time.perf_counter() - start_time) * 1000
        
        print(f"\n⏱️  Medium dashboard (10 tickers): {elapsed_ms:.2f}ms")
        
        # Check performance SLA: <150ms
        assert elapsed_ms < 150.0, f"Dashboard snapshot took {elapsed_ms:.2f}ms (expected <150ms)"


# =============================================================================
# TEST: CACHE TELEMETRY PERFORMANCE
# =============================================================================

class TestCacheTelemetryPerformance:
    """Test cache telemetry performance benchmarks."""
    
    def test_telemetry_collection_small(self):
        """Test telemetry collection for small dataset (100 requests)."""
        collector = CacheTelemetryCollector()
        
        start_time = time.perf_counter()
        
        # Simulate 100 cache requests
        for i in range(100):
            collector.record_cache_request(f"key_{i}", is_hit=True, cache_level="L1", latency_ms=0.1)
        
        elapsed_collection_ms = (time.perf_counter() - start_time) * 1000
        
        # Generate report
        start_time = time.perf_counter()
        report = collector.generate_report()
        elapsed_report_ms = (time.perf_counter() - start_time) * 1000
        
        total_ms = elapsed_collection_ms + elapsed_report_ms
        
        print(f"\n⏱️  Telemetry small (100 requests): {total_ms:.2f}ms (collection: {elapsed_collection_ms:.2f}ms, report: {elapsed_report_ms:.2f}ms)")
        
        # Check performance SLA: <50ms total
        assert total_ms < 50.0, f"Telemetry took {total_ms:.2f}ms (expected <50ms)"
    
    def test_telemetry_collection_medium(self):
        """Test telemetry collection for medium dataset (1000 requests)."""
        collector = CacheTelemetryCollector()
        
        start_time = time.perf_counter()
        
        # Simulate 1000 cache requests
        for i in range(1000):
            collector.record_cache_request(f"key_{i}", is_hit=True, cache_level="L1", latency_ms=0.1)
        
        elapsed_collection_ms = (time.perf_counter() - start_time) * 1000
        
        # Generate report
        start_time = time.perf_counter()
        report = collector.generate_report()
        elapsed_report_ms = (time.perf_counter() - start_time) * 1000
        
        total_ms = elapsed_collection_ms + elapsed_report_ms
        
        print(f"\n⏱️  Telemetry medium (1000 requests): {total_ms:.2f}ms (collection: {elapsed_collection_ms:.2f}ms, report: {elapsed_report_ms:.2f}ms)")
        
        # Relaxed SLA for larger datasets: <100ms
        assert total_ms < 100.0, f"Telemetry took {total_ms:.2f}ms (expected <100ms)"


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "not slow"])
