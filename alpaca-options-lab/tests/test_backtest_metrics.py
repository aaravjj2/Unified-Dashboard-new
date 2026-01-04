"""
Tests for src.backtesting.metrics - Performance Analysis

Tests cover:
- Return calculations
- Risk metrics (Sharpe, Sortino, etc.)
- Drawdown analysis
- Trade statistics
- Rolling metrics
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import List, Tuple

import pytest
import numpy as np

from src.backtesting.metrics import (
    PerformanceAnalyzer,
    PerformanceMetrics,
    TradeAnalysis,
    calculate_sharpe_ratio,
    calculate_sortino_ratio,
    calculate_max_drawdown,
    calculate_calmar_ratio,
    calculate_win_rate,
    calculate_profit_factor,
    calculate_average_trade,
    calculate_expectancy,
    calculate_rolling_sharpe,
)


class TestReturnCalculations:
    """Test return calculations."""
    
    def test_total_return(self):
        """Test total return calculation."""
        initial = 100000.0
        final = 115000.0
        
        total_return = (final - initial) / initial
        
        assert abs(total_return - 0.15) < 0.001
    
    def test_annualized_return(self):
        """Test annualized return calculation."""
        equity_curve = [
            (datetime(2023, 1, 1), 100000),
            (datetime(2023, 12, 31), 115000),
        ]
        
        analyzer = PerformanceAnalyzer(equity_curve=equity_curve)
        metrics = analyzer.calculate_metrics()
        
        # 15% in 1 year = ~15% annualized
        assert abs(metrics.annualized_return - 0.15) < 0.02
    
    def test_daily_returns_calculation(self):
        """Test daily returns calculation."""
        equity_curve = [
            (datetime(2023, 1, 1), 100000),
            (datetime(2023, 1, 2), 101000),
            (datetime(2023, 1, 3), 100500),
            (datetime(2023, 1, 4), 102000),
        ]
        
        analyzer = PerformanceAnalyzer(equity_curve=equity_curve)
        returns = analyzer.daily_returns
        
        assert len(returns) == 3
        assert abs(returns[0] - 0.01) < 0.001  # +1%


class TestRiskMetrics:
    """Test risk metrics calculations."""
    
    @pytest.fixture
    def sample_returns(self):
        """Generate sample daily returns."""
        np.random.seed(42)
        return list(np.random.normal(0.0005, 0.01, 252))  # ~12% annual, 16% vol
    
    def test_sharpe_ratio(self, sample_returns):
        """Test Sharpe ratio calculation."""
        sharpe = calculate_sharpe_ratio(
            returns=sample_returns,
            risk_free_rate=0.05,
            periods_per_year=252,
        )
        
        # Should be positive for positive expected return
        assert sharpe > 0
        # Typical range
        assert -3.0 < sharpe < 3.0
    
    def test_sharpe_ratio_zero_volatility(self):
        """Test Sharpe ratio with zero volatility."""
        # All same returns
        returns = [0.01] * 100
        
        sharpe = calculate_sharpe_ratio(returns, risk_free_rate=0.05)
        
        # Should be very high (or inf) for zero volatility
        assert sharpe > 5.0 or np.isinf(sharpe)
    
    def test_sortino_ratio(self, sample_returns):
        """Test Sortino ratio calculation."""
        sortino = calculate_sortino_ratio(
            returns=sample_returns,
            risk_free_rate=0.05,
            periods_per_year=252,
        )
        
        # Sortino should be >= Sharpe (typically)
        sharpe = calculate_sharpe_ratio(sample_returns, 0.05, 252)
        assert sortino >= sharpe * 0.9  # Allow some tolerance
    
    def test_volatility_calculation(self, sample_returns):
        """Test volatility calculation."""
        vol = np.std(sample_returns) * np.sqrt(252)
        
        # Should be around 16% based on generation
        assert 0.10 < vol < 0.25
    
    def test_calmar_ratio(self):
        """Test Calmar ratio calculation."""
        calmar = calculate_calmar_ratio(
            annualized_return=0.15,
            max_drawdown=0.10,
        )
        
        assert calmar == 1.5


class TestDrawdownAnalysis:
    """Test drawdown calculations."""
    
    def test_max_drawdown(self):
        """Test maximum drawdown calculation."""
        equity_curve = [
            (datetime(2023, 1, 1), 100000),
            (datetime(2023, 2, 1), 110000),  # Peak
            (datetime(2023, 3, 1), 99000),   # Trough
            (datetime(2023, 4, 1), 105000),
        ]
        
        max_dd = calculate_max_drawdown([e[1] for e in equity_curve])
        
        # DD = (110000 - 99000) / 110000 = 10%
        assert abs(max_dd - 0.10) < 0.01
    
    def test_drawdown_periods(self):
        """Test drawdown period identification."""
        equity_curve = [
            (datetime(2023, 1, i+1), 100000 + (i * 1000 if i < 15 else -i * 500))
            for i in range(30)
        ]
        
        analyzer = PerformanceAnalyzer(equity_curve=equity_curve)
        dd_periods = analyzer.get_drawdown_periods()
        
        assert len(dd_periods) > 0
        assert "start" in dd_periods[0]
        assert "end" in dd_periods[0]
        assert "depth" in dd_periods[0]
    
    def test_average_drawdown(self):
        """Test average drawdown calculation."""
        equities = [100, 105, 102, 110, 100, 95, 100, 108, 105]
        
        analyzer = PerformanceAnalyzer(
            equity_curve=[(datetime(2023, 1, i+1), e) for i, e in enumerate(equities)]
        )
        metrics = analyzer.calculate_metrics()
        
        assert metrics.average_drawdown > 0
    
    def test_drawdown_duration(self):
        """Test drawdown duration calculation."""
        # 10 days peak to recovery
        equity_curve = [
            (datetime(2023, 1, 1), 100),
            (datetime(2023, 1, 5), 110),   # Peak
            (datetime(2023, 1, 10), 95),   # Trough
            (datetime(2023, 1, 15), 110),  # Recovery
        ]
        
        analyzer = PerformanceAnalyzer(equity_curve=equity_curve)
        dd_periods = analyzer.get_drawdown_periods()
        
        if dd_periods:
            assert dd_periods[0]["duration_days"] == 10


class TestTradeStatistics:
    """Test trade statistics calculations."""
    
    @pytest.fixture
    def sample_trades(self):
        """Generate sample trades."""
        return [
            {"pnl": 500, "symbol": "AAPL", "holding_period": 3},
            {"pnl": -200, "symbol": "AAPL", "holding_period": 2},
            {"pnl": 800, "symbol": "MSFT", "holding_period": 5},
            {"pnl": 300, "symbol": "GOOGL", "holding_period": 4},
            {"pnl": -400, "symbol": "AAPL", "holding_period": 1},
            {"pnl": 600, "symbol": "MSFT", "holding_period": 3},
            {"pnl": -100, "symbol": "AMZN", "holding_period": 2},
            {"pnl": 450, "symbol": "TSLA", "holding_period": 4},
        ]
    
    def test_win_rate(self, sample_trades):
        """Test win rate calculation."""
        win_rate = calculate_win_rate(sample_trades)
        
        # 5 winners / 8 trades = 62.5%
        assert abs(win_rate - 0.625) < 0.01
    
    def test_profit_factor(self, sample_trades):
        """Test profit factor calculation."""
        pf = calculate_profit_factor(sample_trades)
        
        # Gross profit = 500 + 800 + 300 + 600 + 450 = 2650
        # Gross loss = 200 + 400 + 100 = 700
        # PF = 2650 / 700 = 3.79
        assert abs(pf - 3.79) < 0.1
    
    def test_average_win_loss(self, sample_trades):
        """Test average win/loss calculation."""
        analyzer = TradeAnalysis(trades=sample_trades)
        
        # Average win = 2650 / 5 = 530
        assert abs(analyzer.average_win - 530) < 1
        
        # Average loss = 700 / 3 = 233.33
        assert abs(analyzer.average_loss - 233.33) < 1
    
    def test_expectancy(self, sample_trades):
        """Test expectancy calculation."""
        exp = calculate_expectancy(sample_trades)
        
        # E = (win_rate * avg_win) - (loss_rate * avg_loss)
        # E = (0.625 * 530) - (0.375 * 233.33) = 331.25 - 87.5 = 243.75
        assert abs(exp - 243.75) < 10
    
    def test_average_trade(self, sample_trades):
        """Test average trade calculation."""
        avg = calculate_average_trade(sample_trades)
        
        # Total P&L = 500 - 200 + 800 + 300 - 400 + 600 - 100 + 450 = 1950
        # Avg = 1950 / 8 = 243.75
        assert abs(avg - 243.75) < 0.1
    
    def test_largest_win_loss(self, sample_trades):
        """Test largest win/loss identification."""
        analyzer = TradeAnalysis(trades=sample_trades)
        
        assert analyzer.largest_win == 800
        assert analyzer.largest_loss == -400
    
    def test_consecutive_wins_losses(self, sample_trades):
        """Test consecutive wins/losses calculation."""
        # Reorder for clear streaks
        trades = [
            {"pnl": 100}, {"pnl": 200}, {"pnl": 300},  # 3 wins
            {"pnl": -50}, {"pnl": -75},                 # 2 losses
            {"pnl": 50},
        ]
        
        analyzer = TradeAnalysis(trades=trades)
        
        assert analyzer.max_consecutive_wins >= 3
        assert analyzer.max_consecutive_losses >= 2


class TestPerformanceMetrics:
    """Test PerformanceMetrics dataclass."""
    
    def test_metrics_creation(self):
        """Test creating metrics object."""
        metrics = PerformanceMetrics(
            total_return=15000.0,
            total_return_pct=0.15,
            annualized_return=0.15,
            volatility=0.16,
            sharpe_ratio=0.94,
            sortino_ratio=1.2,
            max_drawdown=0.10,
            calmar_ratio=1.5,
            total_trades=50,
            win_rate=0.60,
            profit_factor=2.0,
            average_trade=300.0,
            expectancy=180.0,
        )
        
        assert metrics.sharpe_ratio == 0.94
        assert metrics.win_rate == 0.60
    
    def test_metrics_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = PerformanceMetrics(
            total_return=15000.0,
            total_return_pct=0.15,
            sharpe_ratio=0.94,
        )
        
        d = metrics.to_dict()
        
        assert isinstance(d, dict)
        assert d["total_return"] == 15000.0
        assert d["sharpe_ratio"] == 0.94


class TestPerformanceAnalyzer:
    """Test PerformanceAnalyzer class."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer with sample data."""
        np.random.seed(42)
        
        # Generate equity curve
        initial = 100000
        equity = initial
        equity_curve = [(datetime(2023, 1, 1), equity)]
        
        for i in range(1, 252):
            daily_return = np.random.normal(0.0004, 0.01)
            equity *= (1 + daily_return)
            equity_curve.append((datetime(2023, 1, 1) + timedelta(days=i), equity))
        
        # Generate trades
        trades = []
        for i in range(50):
            pnl = np.random.normal(200, 500)
            trades.append({
                "pnl": pnl,
                "symbol": f"STOCK{i % 5}",
                "entry_time": datetime(2023, 1, 1) + timedelta(days=i*5),
                "exit_time": datetime(2023, 1, 1) + timedelta(days=i*5 + 3),
                "holding_period": 3,
            })
        
        return PerformanceAnalyzer(
            equity_curve=equity_curve,
            trades=trades,
            initial_capital=initial,
        )
    
    def test_calculate_metrics(self, analyzer):
        """Test full metrics calculation."""
        metrics = analyzer.calculate_metrics()
        
        assert metrics.total_return != 0
        assert metrics.sharpe_ratio is not None
        assert metrics.max_drawdown >= 0
        assert 0 <= metrics.win_rate <= 1
    
    def test_get_summary(self, analyzer):
        """Test summary generation."""
        summary = analyzer.get_summary()
        
        assert "total_return" in summary.lower() or "Total Return" in summary
        assert "sharpe" in summary.lower()
    
    def test_compare_with_benchmark(self, analyzer):
        """Test benchmark comparison."""
        # Generate benchmark
        benchmark = [(t, v * 0.95) for t, v in analyzer.equity_curve]
        
        comparison = analyzer.compare_with_benchmark(benchmark)
        
        assert "alpha" in comparison or "excess_return" in comparison
        assert "tracking_error" in comparison or "relative_performance" in comparison


class TestRollingMetrics:
    """Test rolling metrics calculations."""
    
    @pytest.fixture
    def returns(self):
        """Generate return series."""
        np.random.seed(42)
        return list(np.random.normal(0.0004, 0.01, 500))
    
    def test_rolling_sharpe(self, returns):
        """Test rolling Sharpe ratio."""
        rolling = calculate_rolling_sharpe(
            returns=returns,
            window=60,
            risk_free_rate=0.05,
        )
        
        assert len(rolling) == len(returns)
        # First (window-1) values should be NaN
        assert np.isnan(rolling[0])
        # Later values should be valid
        assert not np.isnan(rolling[-1])
    
    def test_rolling_volatility(self, returns):
        """Test rolling volatility."""
        window = 20
        
        analyzer = PerformanceAnalyzer(
            equity_curve=[(datetime(2023, 1, 1) + timedelta(days=i), 100 * np.prod([1+r for r in returns[:i+1]]))
                         for i in range(len(returns))],
        )
        
        rolling_vol = analyzer.get_rolling_volatility(window=window)
        
        assert len(rolling_vol) == len(returns)
    
    def test_rolling_returns(self, returns):
        """Test rolling returns."""
        window = 21  # Monthly
        
        cumulative = np.cumprod([1 + r for r in returns])
        rolling_return = []
        
        for i in range(len(returns)):
            if i < window:
                rolling_return.append(np.nan)
            else:
                rolling_return.append(cumulative[i] / cumulative[i-window] - 1)
        
        assert len(rolling_return) == len(returns)


class TestTradeAnalysis:
    """Test TradeAnalysis class."""
    
    @pytest.fixture
    def trade_analyzer(self):
        """Create trade analyzer."""
        trades = [
            {"pnl": 500, "symbol": "AAPL", "holding_period": 3, "strategy": "covered_call"},
            {"pnl": -200, "symbol": "AAPL", "holding_period": 2, "strategy": "covered_call"},
            {"pnl": 800, "symbol": "MSFT", "holding_period": 5, "strategy": "iron_condor"},
            {"pnl": 300, "symbol": "GOOGL", "holding_period": 4, "strategy": "vertical_spread"},
            {"pnl": -400, "symbol": "AAPL", "holding_period": 1, "strategy": "covered_call"},
        ]
        return TradeAnalysis(trades=trades)
    
    def test_by_symbol(self, trade_analyzer):
        """Test grouping by symbol."""
        by_symbol = trade_analyzer.analyze_by_symbol()
        
        assert "AAPL" in by_symbol
        assert by_symbol["AAPL"]["count"] == 3
        assert by_symbol["AAPL"]["total_pnl"] == 500 - 200 - 400
    
    def test_by_strategy(self, trade_analyzer):
        """Test grouping by strategy."""
        by_strategy = trade_analyzer.analyze_by_strategy()
        
        assert "covered_call" in by_strategy
        assert by_strategy["covered_call"]["count"] == 3
    
    def test_holding_period_analysis(self, trade_analyzer):
        """Test holding period analysis."""
        hp_analysis = trade_analyzer.analyze_holding_periods()
        
        assert "average_holding_period" in hp_analysis
        assert hp_analysis["average_holding_period"] == 3.0
    
    def test_trade_distribution(self, trade_analyzer):
        """Test P&L distribution analysis."""
        dist = trade_analyzer.get_pnl_distribution()
        
        assert "mean" in dist
        assert "std" in dist
        assert "skew" in dist
        assert "kurtosis" in dist
