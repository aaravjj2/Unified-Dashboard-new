"""Benchmark Comparator

Compares portfolio performance against a benchmark index:
- Relative performance (alpha)
- Correlation analysis
- Drawdown comparison
- Up/down capture ratios
- Rolling performance windows

Operates fully offline using local benchmark data (e.g., SPY.csv).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, Optional
from .risk_metrics_computer import compute_returns


class BenchmarkComparator:
    """Compares portfolio to benchmark index."""
    
    def __init__(self, benchmark_path: Optional[Path] = None):
        """Initialize with benchmark data file.
        
        Args:
            benchmark_path: Path to CSV with benchmark price history
        """
        if benchmark_path is None:
            benchmark_path = Path(__file__).parent.parent / 'data' / 'benchmark_spy.csv'
        
        self.benchmark_path = Path(benchmark_path)
        self.benchmark_data = self._load_benchmark()
    
    def _load_benchmark(self) -> Optional[pd.DataFrame]:
        """Load benchmark data from CSV."""
        if not self.benchmark_path.exists():
            return None
        
        df = pd.read_csv(self.benchmark_path)
        
        # Ensure date column
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        
        return df
    
    def compare(self, portfolio_df: pd.DataFrame, 
                portfolio_price_col: str = 'close',
                benchmark_price_col: str = 'close') -> Dict:
        """Compare portfolio to benchmark.
        
        Args:
            portfolio_df: Portfolio price DataFrame with date index
            portfolio_price_col: Column name for portfolio prices
            benchmark_price_col: Column name for benchmark prices
        
        Returns:
            Dictionary with comparison metrics
        """
        if self.benchmark_data is None:
            return {
                "error": "Benchmark data not available",
                "benchmark_path": str(self.benchmark_path)
            }
        
        # Ensure portfolio has date index
        if not isinstance(portfolio_df.index, pd.DatetimeIndex):
            if 'date' in portfolio_df.columns:
                portfolio_df = portfolio_df.copy().set_index('date')
        
        # Align dates
        aligned = pd.DataFrame({
            'portfolio': portfolio_df[portfolio_price_col],
            'benchmark': self.benchmark_data[benchmark_price_col]
        }).dropna()
        
        if len(aligned) < 2:
            return {"error": "Insufficient overlapping data"}
        
        # Compute returns
        port_returns = compute_returns(aligned['portfolio'])
        bench_returns = compute_returns(aligned['benchmark'])
        
        # Total returns
        port_total = (aligned['portfolio'].iloc[-1] / aligned['portfolio'].iloc[0]) - 1
        bench_total = (aligned['benchmark'].iloc[-1] / aligned['benchmark'].iloc[0]) - 1
        
        # Annualized returns
        n_days = len(aligned)
        port_annual = ((aligned['portfolio'].iloc[-1] / aligned['portfolio'].iloc[0]) ** (252 / n_days)) - 1
        bench_annual = ((aligned['benchmark'].iloc[-1] / aligned['benchmark'].iloc[0]) ** (252 / n_days)) - 1
        
        # Alpha (excess return)
        alpha = port_annual - bench_annual
        
        # Correlation
        correlation = port_returns.corr(bench_returns)
        
        # Up/down capture ratios
        up_markets = bench_returns > 0
        down_markets = bench_returns < 0
        
        up_capture = 0.0
        down_capture = 0.0
        
        if up_markets.sum() > 0:
            port_up_avg = port_returns[up_markets].mean()
            bench_up_avg = bench_returns[up_markets].mean()
            if bench_up_avg != 0:
                up_capture = port_up_avg / bench_up_avg
        
        if down_markets.sum() > 0:
            port_down_avg = port_returns[down_markets].mean()
            bench_down_avg = bench_returns[down_markets].mean()
            if bench_down_avg != 0:
                down_capture = port_down_avg / bench_down_avg
        
        # Drawdown comparison
        port_cummax = aligned['portfolio'].cummax()
        bench_cummax = aligned['benchmark'].cummax()
        
        port_dd = ((aligned['portfolio'] - port_cummax) / port_cummax).min()
        bench_dd = ((aligned['benchmark'] - bench_cummax) / bench_cummax).min()
        
        result = {
            "period_start": str(aligned.index[0].date()),
            "period_end": str(aligned.index[-1].date()),
            "num_days": int(n_days),
            "portfolio": {
                "total_return": float(port_total),
                "annualized_return": float(port_annual),
                "max_drawdown": float(abs(port_dd))
            },
            "benchmark": {
                "total_return": float(bench_total),
                "annualized_return": float(bench_annual),
                "max_drawdown": float(abs(bench_dd))
            },
            "relative": {
                "alpha": float(alpha),
                "correlation": float(correlation),
                "up_capture": float(up_capture),
                "down_capture": float(down_capture),
                "outperformance_pct": float((port_total - bench_total) * 100)
            }
        }
        
        return result
    
    def get_correlation_matrix(self, portfolio_df: pd.DataFrame,
                               portfolio_price_col: str = 'close') -> Dict:
        """Get correlation matrix between portfolio and benchmark.
        
        Args:
            portfolio_df: Portfolio DataFrame
            portfolio_price_col: Price column name
        
        Returns:
            Correlation data
        """
        if self.benchmark_data is None:
            return {"error": "Benchmark data not available"}
        
        # Ensure date index
        if not isinstance(portfolio_df.index, pd.DatetimeIndex):
            if 'date' in portfolio_df.columns:
                portfolio_df = portfolio_df.copy().set_index('date')
        
        # Align and compute returns
        aligned = pd.DataFrame({
            'Portfolio': portfolio_df[portfolio_price_col],
            'Benchmark': self.benchmark_data['close']
        }).dropna()
        
        returns = aligned.pct_change().dropna()
        corr_matrix = returns.corr()
        
        return {
            "correlation_matrix": corr_matrix.to_dict(),
            "portfolio_benchmark_corr": float(corr_matrix.loc['Portfolio', 'Benchmark'])
        }


if __name__ == '__main__':
    # Quick test with synthetic data
    dates = pd.date_range('2024-01-01', '2024-12-31', freq='D')
    
    # Generate synthetic portfolio and benchmark
    port_prices = pd.Series(100 * (1 + np.random.randn(len(dates)).cumsum() * 0.012), index=dates)
    bench_prices = pd.Series(100 * (1 + np.random.randn(len(dates)).cumsum() * 0.01), index=dates)
    
    # Save synthetic benchmark
    bench_df = pd.DataFrame({'close': bench_prices})
    bench_df.index.name = 'date'
    
    comparator = BenchmarkComparator()
    port_df = pd.DataFrame({'close': port_prices})
    
    # Note: This will fail if benchmark file doesn't exist, which is expected for demo
    result = comparator.compare(port_df)
    print("Benchmark Comparison:")
    print(result)
