"""Offline Portfolio Analytics Engine

Main orchestrator for Phase 3 portfolio analytics.
Coordinates risk metrics, sector analysis, benchmark comparison, and report generation.

Entry point for running comprehensive portfolio analysis:
    engine = PortfolioAnalyticsEngine()
    result = engine.run_analysis('my_portfolio')
"""
from __future__ import annotations
import json
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

from .risk_metrics_computer import compute_risk_metrics
from .sector_allocation_analyzer import SectorAllocationAnalyzer
from .benchmark_comparator import BenchmarkComparator
from .portfolio_report_builder import PortfolioReportBuilder


class PortfolioAnalyticsEngine:
    """Main orchestrator for portfolio analytics."""
    
    def __init__(self, data_dir: Optional[Path] = None, cache_dir: Optional[Path] = None):
        """Initialize analytics engine.
        
        Args:
            data_dir: Directory containing portfolio data files
            cache_dir: Directory for caching results
        """
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / 'data'
        if cache_dir is None:
            cache_dir = data_dir / 'portfolio_offline_cache'
        
        self.data_dir = Path(data_dir)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize components
        self.sector_analyzer = SectorAllocationAnalyzer()
        self.benchmark_comparator = BenchmarkComparator()
        self.report_builder = PortfolioReportBuilder(output_dir=self.data_dir)
    
    def load_portfolio_data(self, portfolio_id: str) -> tuple[pd.DataFrame, pd.DataFrame]:
        """Load portfolio holdings and price history.
        
        Args:
            portfolio_id: Portfolio identifier
        
        Returns:
            Tuple of (holdings_df, price_history_df)
        """
        # Load holdings
        holdings_path = self.data_dir / f'portfolio_holdings.csv'
        if not holdings_path.exists():
            holdings_path = self.data_dir / f'{portfolio_id}_holdings.csv'
        
        if not holdings_path.exists():
            raise FileNotFoundError(f"Holdings file not found: {holdings_path}")
        
        holdings_df = pd.read_csv(holdings_path)
        
        # Load price history
        price_path = self.data_dir / f'portfolio_prices.csv'
        if not price_path.exists():
            price_path = self.data_dir / f'{portfolio_id}_prices.csv'
        
        if price_path.exists():
            price_df = pd.read_csv(price_path)
            if 'date' in price_df.columns:
                price_df['date'] = pd.to_datetime(price_df['date'])
                price_df = price_df.set_index('date')
        else:
            # Create dummy price history if not available
            price_df = pd.DataFrame()
        
        return holdings_df, price_df
    
    def run_analysis(self, portfolio_id: str, use_cache: bool = True) -> Dict:
        """Run comprehensive portfolio analysis.
        
        Args:
            portfolio_id: Portfolio identifier
            use_cache: Whether to use cached results if available
        
        Returns:
            Complete analytics report dictionary
        """
        # Check cache
        cache_file = self.cache_dir / f'{portfolio_id}_analytics.json'
        if use_cache and cache_file.exists():
            with open(cache_file, 'r', encoding='utf8') as f:
                cached = json.load(f)
                # Check if cache is recent (less than 1 hour old)
                if 'report_metadata' in cached:
                    gen_time = cached['report_metadata'].get('generated_at', '')
                    # For now, just return cached (can add time check later)
                    return cached
        
        # Load portfolio data
        holdings_df, price_df = self.load_portfolio_data(portfolio_id)
        
        # Compute risk metrics
        if not price_df.empty and 'close' in price_df.columns:
            risk_metrics = compute_risk_metrics(
                price_df,
                df_benchmark=self.benchmark_comparator.benchmark_data,
                price_col='close'
            )
        else:
            # Provide default metrics if price history unavailable
            risk_metrics = {
                "total_return": 0.0,
                "annualized_return": 0.0,
                "volatility": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "var_95": 0.0,
                "max_drawdown": 0.0,
                "beta": None,
                "tracking_error": None,
                "information_ratio": None
            }
        
        # Sector allocation analysis
        sector_analysis = self.sector_analyzer.analyze_allocation(holdings_df)
        
        # Benchmark comparison
        if not price_df.empty:
            benchmark_comparison = self.benchmark_comparator.compare(price_df)
        else:
            benchmark_comparison = {"error": "No price history available"}
        
        # Build report
        metadata = {
            "portfolio_id": portfolio_id,
            "num_holdings": len(holdings_df),
            "has_price_history": not price_df.empty,
            "dataset_hash": self.report_builder.compute_dataset_hash(holdings_df.to_json())
        }
        
        report = self.report_builder.build_report(
            portfolio_id=portfolio_id,
            risk_metrics=risk_metrics,
            sector_analysis=sector_analysis,
            benchmark_comparison=benchmark_comparison,
            metadata=metadata
        )
        
        # Cache results
        with open(cache_file, 'w', encoding='utf8') as f:
            json.dump(report, f, indent=2)
        
        # Export reports
        self.report_builder.export_json(report)
        self.report_builder.export_markdown(report)
        
        return report
    
    def get_cached_analysis(self, portfolio_id: str) -> Optional[Dict]:
        """Retrieve cached analysis if available.
        
        Args:
            portfolio_id: Portfolio identifier
        
        Returns:
            Cached report or None
        """
        cache_file = self.cache_dir / f'{portfolio_id}_analytics.json'
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf8') as f:
                return json.load(f)
        return None
    
    def clear_cache(self, portfolio_id: Optional[str] = None) -> None:
        """Clear cached analytics.
        
        Args:
            portfolio_id: If provided, clear only this portfolio's cache. 
                         Otherwise clear all.
        """
        if portfolio_id:
            cache_file = self.cache_dir / f'{portfolio_id}_analytics.json'
            if cache_file.exists():
                cache_file.unlink()
        else:
            for cache_file in self.cache_dir.glob('*_analytics.json'):
                cache_file.unlink()


def run_portfolio_analytics(portfolio_id: str = 'default', 
                           data_dir: Optional[Path] = None,
                           use_cache: bool = True) -> Dict:
    """Convenience function to run portfolio analytics.
    
    Args:
        portfolio_id: Portfolio identifier
        data_dir: Data directory path
        use_cache: Whether to use cached results
    
    Returns:
        Analytics report dictionary
    """
    engine = PortfolioAnalyticsEngine(data_dir=data_dir)
    return engine.run_analysis(portfolio_id, use_cache=use_cache)


if __name__ == '__main__':
    # Example usage
    print("Phase 3 Portfolio Analytics Engine")
    print("=" * 50)
    
    try:
        result = run_portfolio_analytics('default')
        print("\nAnalysis completed successfully!")
        print(f"Total Value: ${result['summary']['total_value']:,.2f}")
        print(f"Annualized Return: {result['summary']['annualized_return']*100:.2f}%")
        print(f"Sharpe Ratio: {result['summary']['sharpe_ratio']:.2f}")
        print(f"\nFull report saved to data/portfolio_analytics_summary.json")
    except FileNotFoundError as e:
        print(f"\nError: {e}")
        print("Please ensure portfolio_holdings.csv exists in the data directory.")
