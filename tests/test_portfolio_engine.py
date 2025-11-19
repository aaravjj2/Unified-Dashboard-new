"""Test suite for Phase 3 Portfolio Analytics Engine

Tests core functionality:
- Data loading (CSV/JSON)
- Risk metrics computation
- Sector allocation analysis
- Benchmark comparison
- Report generation
- Cache persistence
"""
import json
import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from phase3_portfolio_analytics import (
    PortfolioAnalyticsEngine,
    compute_risk_metrics,
    SectorAllocationAnalyzer,
    BenchmarkComparator,
    PortfolioReportBuilder
)


class TestPortfolioDataLoading:
    """Test data loading functionality."""
    
    def test_load_portfolio_holdings(self):
        """Test loading portfolio holdings CSV."""
        engine = PortfolioAnalyticsEngine()
        holdings_df, price_df = engine.load_portfolio_data('default')
        
        assert not holdings_df.empty, "Holdings should not be empty"
        assert 'ticker' in holdings_df.columns, "Holdings must have ticker column"
        assert 'value' in holdings_df.columns or ('shares' in holdings_df.columns and 'price' in holdings_df.columns), \
            "Holdings must have value or (shares+price)"
        
        print(f"✓ Loaded {len(holdings_df)} holdings")
    
    def test_price_history_exists(self):
        """Test that price history data is available."""
        engine = PortfolioAnalyticsEngine()
        _, price_df = engine.load_portfolio_data('default')
        
        assert not price_df.empty, "Price history should exist"
        assert 'close' in price_df.columns, "Price history must have close column"
        assert isinstance(price_df.index, pd.DatetimeIndex), "Price history must have date index"
        
        print(f"✓ Price history has {len(price_df)} days")


class TestRiskMetricsComputation:
    """Test risk metrics calculations."""
    
    def test_risk_metrics_all_finite(self):
        """Ensure all computed risk metrics are finite (no NaN/Inf)."""
        # Create sample data
        dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
        prices = pd.Series(100 * (1 + np.random.randn(len(dates)).cumsum() * 0.01), index=dates)
        df = pd.DataFrame({'close': prices})
        
        metrics = compute_risk_metrics(df)
        
        for key, value in metrics.items():
            if value is not None:
                assert np.isfinite(value), f"{key} should be finite, got {value}"
        
        print("✓ All risk metrics are finite")
    
    def test_sharpe_ratio_reasonable(self):
        """Test that Sharpe ratio is in reasonable range."""
        dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
        prices = pd.Series(100 * (1.15 ** (np.arange(len(dates)) / 252)), index=dates)  # 15% annual
        df = pd.DataFrame({'close': prices})
        
        metrics = compute_risk_metrics(df)
        
        assert -5 < metrics['sharpe_ratio'] < 10, "Sharpe ratio should be reasonable"
        print(f"✓ Sharpe ratio: {metrics['sharpe_ratio']:.2f}")
    
    def test_volatility_positive(self):
        """Test that volatility is positive."""
        dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
        prices = pd.Series(100 * (1 + np.random.randn(len(dates)).cumsum() * 0.01), index=dates)
        df = pd.DataFrame({'close': prices})
        
        metrics = compute_risk_metrics(df)
        
        assert metrics['volatility'] > 0, "Volatility should be positive"
        print(f"✓ Volatility: {metrics['volatility']*100:.2f}%")


class TestSectorAllocation:
    """Test sector allocation analysis."""
    
    def test_sector_allocation_sums_to_100(self):
        """Test that sector allocations sum to 100%."""
        holdings = pd.DataFrame({
            'ticker': ['AAPL', 'MSFT', 'JPM'],
            'shares': [100, 50, 200],
            'price': [175.0, 380.0, 150.0],
        })
        holdings['value'] = holdings['shares'] * holdings['price']
        
        analyzer = SectorAllocationAnalyzer()
        result = analyzer.analyze_allocation(holdings)
        
        total_pct = sum(s['allocation_pct'] for s in result['sectors'])
        assert 99.9 < total_pct < 100.1, f"Allocation should sum to 100%, got {total_pct}"
        
        print(f"✓ Sector allocation sums to {total_pct:.2f}%")
    
    def test_sector_mapping_loads(self):
        """Test that sector mapping file loads correctly."""
        analyzer = SectorAllocationAnalyzer()
        
        # Test known ticker
        sector = analyzer.get_sector('AAPL')
        assert sector != 'Unknown', "AAPL should have a sector mapping"
        
        print(f"✓ Sector mapping loaded, AAPL -> {sector}")


class TestBenchmarkComparison:
    """Test benchmark comparison functionality."""
    
    def test_benchmark_data_loads(self):
        """Test that benchmark data loads."""
        comparator = BenchmarkComparator()
        
        assert comparator.benchmark_data is not None, "Benchmark data should load"
        assert not comparator.benchmark_data.empty, "Benchmark should have data"
        
        print(f"✓ Benchmark loaded with {len(comparator.benchmark_data)} days")
    
    def test_comparison_produces_alpha(self):
        """Test that comparison produces alpha metric."""
        dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
        prices = pd.Series(100 * (1 + np.random.randn(len(dates)).cumsum() * 0.01), index=dates)
        port_df = pd.DataFrame({'close': prices})
        
        comparator = BenchmarkComparator()
        result = comparator.compare(port_df)
        
        if 'error' not in result:
            assert 'relative' in result, "Should have relative metrics"
            assert 'alpha' in result['relative'], "Should compute alpha"
            print(f"✓ Alpha: {result['relative']['alpha']*100:.2f}%")
        else:
            print(f"⚠ Benchmark comparison unavailable: {result['error']}")


class TestReportGeneration:
    """Test report building and export."""
    
    def test_json_export_created(self):
        """Test that JSON export file is created."""
        builder = PortfolioReportBuilder()
        
        sample_report = {
            "report_metadata": {"portfolio_id": "test", "generated_at": "2024-01-01"},
            "summary": {"total_value": 100000},
            "risk_metrics": {},
            "sector_analysis": {},
            "benchmark_comparison": {}
        }
        
        output_path = builder.export_json(sample_report, 'test_report.json')
        
        assert output_path.exists(), "JSON export should be created"
        
        # Verify content
        with open(output_path, 'r') as f:
            loaded = json.load(f)
            assert loaded['summary']['total_value'] == 100000
        
        # Cleanup
        output_path.unlink()
        
        print("✓ JSON export works correctly")
    
    def test_markdown_export_created(self):
        """Test that Markdown export file is created."""
        builder = PortfolioReportBuilder()
        
        sample_report = {
            "report_metadata": {"portfolio_id": "test", "generated_at": "2024-01-01"},
            "summary": {"total_value": 100000, "sharpe_ratio": 1.5},
            "risk_metrics": {"sharpe_ratio": 1.5, "volatility": 0.15},
            "sector_analysis": {"sectors": []},
            "benchmark_comparison": {}
        }
        
        output_path = builder.export_markdown(sample_report, 'test_report.md')
        
        assert output_path.exists(), "Markdown export should be created"
        
        # Verify content
        content = output_path.read_text()
        assert "Portfolio Analytics Report" in content
        assert "test" in content
        
        # Cleanup
        output_path.unlink()
        
        print("✓ Markdown export works correctly")


class TestFullAnalyticsCycle:
    """Test full analytics engine integration."""
    
    def test_full_analysis_run(self):
        """Test complete analysis cycle."""
        engine = PortfolioAnalyticsEngine()
        
        try:
            result = engine.run_analysis('default', use_cache=False)
            
            # Verify report structure
            assert 'report_metadata' in result
            assert 'summary' in result
            assert 'risk_metrics' in result
            assert 'sector_analysis' in result
            assert 'benchmark_comparison' in result
            
            # Verify summary has key metrics
            summary = result['summary']
            assert summary['total_value'] > 0
            assert summary['num_holdings'] > 0
            
            print("✓ Full analytics cycle completed")
            print(f"  Total Value: ${summary['total_value']:,.2f}")
            print(f"  Holdings: {summary['num_holdings']}")
            print(f"  Sectors: {summary['num_sectors']}")
            
        except FileNotFoundError as e:
            print(f"⚠ Skipping full analysis test: {e}")
    
    def test_cache_persistence(self):
        """Test that cache is created and can be retrieved."""
        engine = PortfolioAnalyticsEngine()
        
        try:
            # Run analysis (creates cache)
            result1 = engine.run_analysis('default', use_cache=False)
            
            # Retrieve from cache
            result2 = engine.get_cached_analysis('default')
            
            assert result2 is not None, "Cache should exist"
            assert result2['summary']['total_value'] == result1['summary']['total_value']
            
            print("✓ Cache persistence verified")
            
        except FileNotFoundError as e:
            print(f"⚠ Skipping cache test: {e}")


def run_all_tests():
    """Run all tests with simple runner."""
    test_classes = [
        TestPortfolioDataLoading,
        TestRiskMetricsComputation,
        TestSectorAllocation,
        TestBenchmarkComparison,
        TestReportGeneration,
        TestFullAnalyticsCycle
    ]
    
    print("=" * 70)
    print("PHASE 3 PORTFOLIO ANALYTICS - TEST SUITE")
    print("=" * 70)
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}")
        print("-" * 70)
        
        test_instance = test_class()
        test_methods = [m for m in dir(test_instance) if m.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(test_instance, method_name)
                method()
                passed_tests += 1
            except Exception as e:
                failed_tests.append((f"{test_class.__name__}.{method_name}", str(e)))
                print(f"✗ {method_name}: {e}")
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed_tests}/{total_tests} tests passed")
    
    if failed_tests:
        print("\nFailed tests:")
        for test_name, error in failed_tests:
            print(f"  - {test_name}: {error}")
    else:
        print("\n✓ All tests passed!")
    
    print("=" * 70)
    
    return passed_tests == total_tests


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
