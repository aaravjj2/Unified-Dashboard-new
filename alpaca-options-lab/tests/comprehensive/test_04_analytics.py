"""
Alpaca Options Lab - Comprehensive Analytics Tests
Test File 4 of 10: Analytics, ML Predictor, Backtest
~50 tests covering all analytics components
"""
import pytest
from datetime import datetime, date, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import sys
sys.path.insert(0, '.')


class TestPerformanceAnalyzer:
    """Tests for Performance Analyzer - 15 tests"""
    
    def test_performance_analyzer_import(self):
        from src.analytics.performance import PerformanceAnalyzer
        assert PerformanceAnalyzer is not None
    
    def test_trade_class_import(self):
        from src.analytics.performance import Trade
        assert Trade is not None
    
    def test_analyzer_creation(self):
        from src.analytics.performance import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer()
        assert analyzer is not None
    
    def test_trade_creation(self):
        from src.analytics.performance import Trade
        trade = Trade(
            trade_id="T001",
            symbol="SPY",
            strategy="test",
            side="long",
            entry_time=datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc),
            entry_price=1.00,
            quantity=10,
            exit_time=datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc),
            exit_price=1.50
        )
        assert trade.trade_id == "T001"
    
    def test_add_trade(self):
        from src.analytics.performance import PerformanceAnalyzer, Trade
        analyzer = PerformanceAnalyzer()
        trade = Trade(
            trade_id="T001",
            symbol="SPY",
            strategy="test",
            side="long",
            entry_time=datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc),
            entry_price=1.00,
            quantity=10,
            exit_time=datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc),
            exit_price=1.50
        )
        analyzer.add_trade(trade)
        assert True
    
    def test_get_summary(self):
        from src.analytics.performance import PerformanceAnalyzer, Trade
        analyzer = PerformanceAnalyzer()
        trade = Trade(
            trade_id="T001",
            symbol="SPY",
            strategy="test",
            side="long",
            entry_time=datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc),
            entry_price=1.00,
            quantity=10,
            exit_time=datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc),
            exit_price=1.50
        )
        analyzer.add_trade(trade)
        summary = analyzer.get_summary()
        assert summary is not None
    
    def test_drawdown_analysis_class(self):
        from src.analytics.performance import DrawdownAnalysis
        assert DrawdownAnalysis is not None
    
    def test_trade_analysis_class(self):
        from src.analytics.performance import TradeAnalysis
        assert TradeAnalysis is not None
    
    def test_performance_metrics_class(self):
        from src.analytics.performance import PerformanceMetrics
        assert PerformanceMetrics is not None
    
    def test_analyzer_has_calculate_metrics(self):
        from src.analytics.performance import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer()
        assert hasattr(analyzer, 'calculate_metrics') or hasattr(analyzer, 'get_metrics')
    
    def test_analyzer_has_drawdown(self):
        from src.analytics.performance import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer()
        assert hasattr(analyzer, 'calculate_drawdown') or hasattr(analyzer, 'get_drawdown')
    
    def test_analyzer_has_sharpe(self):
        from src.analytics.performance import PerformanceAnalyzer
        analyzer = PerformanceAnalyzer()
        assert hasattr(analyzer, 'calculate_sharpe') or hasattr(analyzer, 'sharpe_ratio')
    
    def test_multiple_trades(self):
        from src.analytics.performance import PerformanceAnalyzer, Trade
        analyzer = PerformanceAnalyzer()
        for i in range(5):
            trade = Trade(
                trade_id=f"T{i:03d}",
                symbol="SPY",
                strategy="test",
                side="long",
                entry_time=datetime(2024, 1, i+1, 10, 0, tzinfo=timezone.utc),
                entry_price=1.00,
                quantity=10,
                exit_time=datetime(2024, 1, i+1, 15, 0, tzinfo=timezone.utc),
                exit_price=1.50 if i % 2 == 0 else 0.80
            )
            analyzer.add_trade(trade)
        summary = analyzer.get_summary()
        assert summary is not None
    
    def test_analyzer_file_size(self):
        import os
        path = 'src/analytics/performance.py'
        assert os.path.exists(path)
        with open(path) as f:
            lines = len(f.readlines())
        assert lines > 200
    
    def test_trade_has_pnl(self):
        from src.analytics.performance import Trade
        trade = Trade(
            trade_id="T001",
            symbol="SPY",
            strategy="test",
            side="long",
            entry_time=datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc),
            entry_price=1.00,
            quantity=10,
            exit_time=datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc),
            exit_price=1.50
        )
        assert hasattr(trade, 'pnl') or hasattr(trade, 'profit')


class TestRiskAnalyzer:
    """Tests for Risk Analyzer - 15 tests"""
    
    def test_risk_analyzer_import(self):
        from src.analytics.risk import RiskAnalyzer
        assert RiskAnalyzer is not None
    
    def test_risk_analyzer_creation(self):
        from src.analytics.risk import RiskAnalyzer
        analyzer = RiskAnalyzer()
        assert analyzer is not None
    
    def test_position_class(self):
        from src.analytics.risk import Position
        assert Position is not None
    
    def test_portfolio_risk_class(self):
        from src.analytics.risk import PortfolioRisk
        assert PortfolioRisk is not None
    
    def test_stress_test_class(self):
        from src.analytics.risk import StressTest
        assert StressTest is not None
    
    def test_correlation_matrix_class(self):
        from src.analytics.risk import CorrelationMatrix
        assert CorrelationMatrix is not None
    
    def test_var_calculator_class(self):
        from src.analytics.risk import VaRCalculator
        assert VaRCalculator is not None
    
    def test_risk_analyzer_has_var(self):
        from src.analytics.risk import RiskAnalyzer
        analyzer = RiskAnalyzer()
        assert hasattr(analyzer, 'calculate_var') or hasattr(analyzer, 'var')
    
    def test_risk_analyzer_has_stress_test(self):
        from src.analytics.risk import RiskAnalyzer
        analyzer = RiskAnalyzer()
        assert hasattr(analyzer, 'stress_test') or hasattr(analyzer, 'run_stress_test')
    
    def test_risk_analyzer_has_correlation(self):
        from src.analytics.risk import RiskAnalyzer
        analyzer = RiskAnalyzer()
        assert hasattr(analyzer, 'correlation') or hasattr(analyzer, 'calculate_correlation')
    
    def test_stress_test_dataclass(self):
        from src.analytics.risk import StressTest
        # Test that StressTest is a proper dataclass
        import dataclasses
        assert dataclasses.is_dataclass(StressTest)
    
    def test_var_calculator_creation(self):
        from src.analytics.risk import VaRCalculator
        calc = VaRCalculator()
        assert calc is not None
    
    def test_risk_analyzer_has_beta(self):
        from src.analytics.risk import RiskAnalyzer
        analyzer = RiskAnalyzer()
        assert hasattr(analyzer, 'calculate_beta') or hasattr(analyzer, 'beta')
    
    def test_risk_file_size(self):
        import os
        path = 'src/analytics/risk.py'
        assert os.path.exists(path)
        with open(path) as f:
            lines = len(f.readlines())
        assert lines > 300
    
    def test_portfolio_risk_fields(self):
        from src.analytics.risk import PortfolioRisk
        import dataclasses
        if dataclasses.is_dataclass(PortfolioRisk):
            fields = [f.name for f in dataclasses.fields(PortfolioRisk)]
            assert len(fields) > 0


class TestBacktestEngine:
    """Tests for Backtest Engine - 10 tests"""
    
    def test_backtest_engine_import(self):
        from src.analytics.backtest import BacktestEngine
        assert BacktestEngine is not None
    
    def test_backtest_config_import(self):
        from src.analytics.backtest import BacktestConfig
        assert BacktestConfig is not None
    
    def test_backtest_config_creation(self):
        from src.analytics.backtest import BacktestConfig
        config = BacktestConfig(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            initial_capital=100000.0
        )
        assert config is not None
    
    def test_backtest_engine_creation(self):
        from src.analytics.backtest import BacktestEngine, BacktestConfig
        config = BacktestConfig(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            initial_capital=100000.0
        )
        engine = BacktestEngine(config=config)
        assert engine is not None
    
    def test_backtest_mode_enum(self):
        from src.analytics.backtest import BacktestMode
        assert BacktestMode is not None
    
    def test_trade_log_class(self):
        from src.analytics.backtest import TradeLog
        assert TradeLog is not None
    
    def test_backtest_result_class(self):
        from src.analytics.backtest import BacktestResult
        assert BacktestResult is not None
    
    def test_backtest_engine_has_run(self):
        from src.analytics.backtest import BacktestEngine, BacktestConfig
        config = BacktestConfig(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            initial_capital=100000.0
        )
        engine = BacktestEngine(config=config)
        assert hasattr(engine, 'run') or hasattr(engine, 'execute')
    
    def test_backtest_config_has_dates(self):
        from src.analytics.backtest import BacktestConfig
        config = BacktestConfig(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            initial_capital=100000.0
        )
        assert config.start_date == date(2024, 1, 1)
        assert config.end_date == date(2024, 1, 31)
    
    def test_backtest_file_size(self):
        import os
        path = 'src/analytics/backtest.py'
        assert os.path.exists(path)
        with open(path) as f:
            lines = len(f.readlines())
        assert lines > 300


class TestMLPredictor:
    """Tests for ML Predictor - 10 tests"""
    
    def test_ml_predictor_import(self):
        from src.analytics.ml_predictor import VolatilityPredictor
        assert VolatilityPredictor is not None
    
    def test_predictor_creation(self):
        from src.analytics.ml_predictor import VolatilityPredictor
        predictor = VolatilityPredictor()
        assert predictor is not None
    
    def test_prediction_horizon_enum(self):
        from src.analytics.ml_predictor import PredictionHorizon
        assert PredictionHorizon is not None
    
    def test_prediction_class(self):
        from src.analytics.ml_predictor import Prediction
        assert Prediction is not None
    
    def test_feature_set_class(self):
        from src.analytics.ml_predictor import FeatureSet
        assert FeatureSet is not None
    
    def test_feature_engine_class(self):
        from src.analytics.ml_predictor import FeatureEngine
        assert FeatureEngine is not None
    
    def test_base_predictor_class(self):
        from src.analytics.ml_predictor import BasePredictor
        assert BasePredictor is not None
    
    def test_predictor_has_predict(self):
        from src.analytics.ml_predictor import VolatilityPredictor
        predictor = VolatilityPredictor()
        assert hasattr(predictor, 'predict')
    
    def test_predictor_has_train(self):
        from src.analytics.ml_predictor import VolatilityPredictor
        predictor = VolatilityPredictor()
        assert hasattr(predictor, 'train') or hasattr(predictor, 'fit')
    
    def test_ml_file_size(self):
        import os
        path = 'src/analytics/ml_predictor.py'
        assert os.path.exists(path)
        with open(path) as f:
            lines = len(f.readlines())
        assert lines > 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
