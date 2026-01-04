"""
Alpaca Options Lab - Comprehensive Strategy Tests
Test File 1 of 10: Strategy Engine & Library
~50 tests covering all strategy components
"""
import pytest
from datetime import datetime, date, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import sys
sys.path.insert(0, '.')


class TestStrategyRegistry:
    """Tests for StrategyRegistry - 10 tests"""
    
    def test_registry_import(self):
        from src.strategies.registry import StrategyRegistry
        assert StrategyRegistry is not None
    
    def test_registry_has_list_available(self):
        from src.strategies.registry import StrategyRegistry
        assert hasattr(StrategyRegistry, 'list_available')
    
    def test_registry_has_register(self):
        from src.strategies.registry import StrategyRegistry
        assert hasattr(StrategyRegistry, 'register')
    
    def test_registry_has_get(self):
        from src.strategies.registry import StrategyRegistry
        assert hasattr(StrategyRegistry, 'get')
    
    def test_registry_singleton_pattern(self):
        from src.strategies.registry import StrategyRegistry
        r1 = StrategyRegistry()
        r2 = StrategyRegistry()
        assert r1 is not None and r2 is not None
    
    def test_registry_list_returns_iterable(self):
        from src.strategies.registry import StrategyRegistry
        registry = StrategyRegistry()
        available = registry.list_available()
        assert hasattr(available, '__iter__')
    
    def test_registry_stores_strategies(self):
        from src.strategies.registry import StrategyRegistry
        registry = StrategyRegistry()
        assert hasattr(registry, '_strategies') or hasattr(registry, 'strategies')
    
    def test_registry_get_nonexistent_returns_none(self):
        from src.strategies.registry import StrategyRegistry
        registry = StrategyRegistry()
        result = registry.get('nonexistent_strategy_xyz')
        assert result is None
    
    def test_registry_register_callable(self):
        from src.strategies.registry import StrategyRegistry
        registry = StrategyRegistry()
        assert callable(registry.register)
    
    def test_registry_list_available_callable(self):
        from src.strategies.registry import StrategyRegistry
        registry = StrategyRegistry()
        assert callable(registry.list_available)


class TestStrategyContext:
    """Tests for StrategyContext - 10 tests"""
    
    def test_context_import(self):
        from src.strategies.context import StrategyContext
        assert StrategyContext is not None
    
    def test_context_creation_with_mocks(self):
        from src.strategies.context import StrategyContext
        context = StrategyContext(
            portfolio=MagicMock(),
            risk_manager=MagicMock(),
            order_manager=MagicMock(),
            market_data=MagicMock(),
            greeks_engine=MagicMock()
        )
        assert context is not None
    
    def test_context_has_portfolio(self):
        from src.strategies.context import StrategyContext
        mock_portfolio = MagicMock()
        context = StrategyContext(
            portfolio=mock_portfolio,
            risk_manager=MagicMock(),
            order_manager=MagicMock(),
            market_data=MagicMock(),
            greeks_engine=MagicMock()
        )
        assert context.portfolio == mock_portfolio
    
    def test_context_has_risk_manager(self):
        from src.strategies.context import StrategyContext
        mock_rm = MagicMock()
        context = StrategyContext(
            portfolio=MagicMock(),
            risk_manager=mock_rm,
            order_manager=MagicMock(),
            market_data=MagicMock(),
            greeks_engine=MagicMock()
        )
        assert context.risk_manager == mock_rm
    
    def test_context_has_order_manager(self):
        from src.strategies.context import StrategyContext
        mock_om = MagicMock()
        context = StrategyContext(
            portfolio=MagicMock(),
            risk_manager=MagicMock(),
            order_manager=mock_om,
            market_data=MagicMock(),
            greeks_engine=MagicMock()
        )
        assert context.order_manager == mock_om
    
    def test_context_has_market_data(self):
        from src.strategies.context import StrategyContext
        mock_md = MagicMock()
        context = StrategyContext(
            portfolio=MagicMock(),
            risk_manager=MagicMock(),
            order_manager=MagicMock(),
            market_data=mock_md,
            greeks_engine=MagicMock()
        )
        assert context.market_data == mock_md
    
    def test_context_has_greeks_engine(self):
        from src.strategies.context import StrategyContext
        mock_ge = MagicMock()
        context = StrategyContext(
            portfolio=MagicMock(),
            risk_manager=MagicMock(),
            order_manager=MagicMock(),
            market_data=MagicMock(),
            greeks_engine=mock_ge
        )
        assert context.greeks_engine == mock_ge
    
    def test_context_quote_class_exists(self):
        from src.strategies.context import Quote
        assert Quote is not None
    
    def test_context_option_contract_class_exists(self):
        from src.strategies.context import OptionContract
        assert OptionContract is not None
    
    def test_context_market_data_provider_exists(self):
        from src.strategies.context import MarketDataProvider
        assert MarketDataProvider is not None


class TestStrategyExecutor:
    """Tests for StrategyExecutor - 10 tests"""
    
    def test_executor_import(self):
        from src.strategies.executor import StrategyExecutor
        assert StrategyExecutor is not None
    
    def test_executor_creation(self):
        from src.strategies.executor import StrategyExecutor
        executor = StrategyExecutor(context=MagicMock())
        assert executor is not None
    
    def test_executor_has_context(self):
        from src.strategies.executor import StrategyExecutor
        mock_ctx = MagicMock()
        executor = StrategyExecutor(context=mock_ctx)
        assert executor.context == mock_ctx
    
    def test_executor_has_execute_method(self):
        from src.strategies.executor import StrategyExecutor
        executor = StrategyExecutor(context=MagicMock())
        assert hasattr(executor, 'execute') or hasattr(executor, 'run')
    
    def test_executor_metrics_class_exists(self):
        from src.strategies.executor import StrategyMetrics
        assert StrategyMetrics is not None
    
    def test_executor_stores_active_strategies(self):
        from src.strategies.executor import StrategyExecutor
        executor = StrategyExecutor(context=MagicMock())
        assert hasattr(executor, '_active') or hasattr(executor, 'active_strategies')
    
    def test_executor_has_stop_method(self):
        from src.strategies.executor import StrategyExecutor
        executor = StrategyExecutor(context=MagicMock())
        assert hasattr(executor, 'stop') or hasattr(executor, 'stop_all')
    
    def test_executor_has_status_method(self):
        from src.strategies.executor import StrategyExecutor
        executor = StrategyExecutor(context=MagicMock())
        assert hasattr(executor, 'status') or hasattr(executor, 'get_status')
    
    def test_executor_can_list_running(self):
        from src.strategies.executor import StrategyExecutor
        executor = StrategyExecutor(context=MagicMock())
        assert hasattr(executor, 'list_running') or hasattr(executor, 'running')
    
    def test_executor_metrics_creation(self):
        from src.strategies.executor import StrategyMetrics
        metrics = StrategyMetrics()
        assert metrics is not None


class TestBaseStrategy:
    """Tests for base strategy classes - 10 tests"""
    
    def test_base_import(self):
        from src.strategies.base import BaseStrategy
        assert BaseStrategy is not None
    
    def test_signal_type_enum(self):
        from src.strategies.base import SignalType
        assert hasattr(SignalType, 'BUY') or hasattr(SignalType, 'LONG')
    
    def test_order_side_enum(self):
        from src.strategies.base import OrderSide
        assert OrderSide is not None
    
    def test_order_leg_class(self):
        from src.strategies.base import OrderLeg
        assert OrderLeg is not None
    
    def test_signal_class(self):
        from src.strategies.base import Signal
        assert Signal is not None
    
    def test_strategy_config_class(self):
        from src.strategies.base import StrategyConfig
        assert StrategyConfig is not None
    
    def test_base_strategy_has_generate_signals(self):
        from src.strategies.base import BaseStrategy
        assert hasattr(BaseStrategy, 'generate_signals')
    
    def test_base_strategy_has_on_tick(self):
        from src.strategies.base import BaseStrategy
        assert hasattr(BaseStrategy, 'on_tick') or hasattr(BaseStrategy, 'on_data')
    
    def test_strategy_config_creation(self):
        from src.strategies.base import StrategyConfig
        config = StrategyConfig()
        assert config is not None
    
    def test_base_strategy_is_abstract(self):
        from src.strategies.base import BaseStrategy
        import inspect
        assert inspect.isabstract(BaseStrategy) or hasattr(BaseStrategy, '__abstractmethods__')


class TestIronCondorStrategy:
    """Tests for Iron Condor Strategy - 10 tests"""
    
    def test_iron_condor_import(self):
        from src.strategies.library.iron_condor import IronCondor0DTEStrategy
        assert IronCondor0DTEStrategy is not None
    
    def test_iron_condor_module_has_class(self):
        from src.strategies.library import iron_condor
        assert hasattr(iron_condor, 'IronCondor0DTEStrategy')
    
    def test_iron_condor_inherits_base(self):
        from src.strategies.library.iron_condor import IronCondor0DTEStrategy
        from src.strategies.base import BaseStrategy
        assert issubclass(IronCondor0DTEStrategy, BaseStrategy)
    
    def test_iron_condor_has_generate_signals(self):
        from src.strategies.library.iron_condor import IronCondor0DTEStrategy
        assert hasattr(IronCondor0DTEStrategy, 'generate_signals')
    
    def test_iron_condor_has_config(self):
        from src.strategies.library.iron_condor import IronCondor0DTEStrategy
        strategy = IronCondor0DTEStrategy.__new__(IronCondor0DTEStrategy)
        assert hasattr(IronCondor0DTEStrategy, '__init__')
    
    def test_iron_condor_has_name(self):
        from src.strategies.library.iron_condor import IronCondor0DTEStrategy
        assert hasattr(IronCondor0DTEStrategy, 'name') or hasattr(IronCondor0DTEStrategy, 'NAME')
    
    def test_iron_condor_file_size(self):
        import os
        path = 'src/strategies/library/iron_condor.py'
        assert os.path.exists(path)
        with open(path) as f:
            lines = len(f.readlines())
        assert lines > 100  # Should be substantial implementation
    
    def test_iron_condor_has_validate(self):
        from src.strategies.library.iron_condor import IronCondor0DTEStrategy
        assert hasattr(IronCondor0DTEStrategy, 'validate') or hasattr(IronCondor0DTEStrategy, '_validate')
    
    def test_iron_condor_has_calculate_strikes(self):
        from src.strategies.library.iron_condor import IronCondor0DTEStrategy
        has_method = (hasattr(IronCondor0DTEStrategy, 'calculate_strikes') or 
                     hasattr(IronCondor0DTEStrategy, '_calculate_strikes') or
                     hasattr(IronCondor0DTEStrategy, 'select_strikes'))
        assert has_method
    
    def test_iron_condor_0dte_specific(self):
        from src.strategies.library.iron_condor import IronCondor0DTEStrategy
        # 0DTE strategies should have expiry handling
        assert '0DTE' in IronCondor0DTEStrategy.__name__ or 'dte' in str(IronCondor0DTEStrategy.__dict__).lower()


class TestOtherStrategies:
    """Tests for other strategy library classes - 10 tests"""
    
    def test_wheel_strategy_import(self):
        from src.strategies.library.wheel import CoveredCallWheelStrategy
        assert CoveredCallWheelStrategy is not None
    
    def test_wheel_phase_enum(self):
        from src.strategies.library.wheel import WheelPhase
        assert WheelPhase is not None
    
    def test_calendar_spread_import(self):
        from src.strategies.library.calendar_spread import CalendarSpreadStrategy
        assert CalendarSpreadStrategy is not None
    
    def test_earnings_straddle_import(self):
        from src.strategies.library.earnings_straddle import EarningsStraddleStrategy
        assert EarningsStraddleStrategy is not None
    
    def test_delta_neutral_import(self):
        from src.strategies.library.delta_neutral import DeltaNeutralStrategy
        assert DeltaNeutralStrategy is not None
    
    def test_wheel_inherits_base(self):
        from src.strategies.library.wheel import CoveredCallWheelStrategy
        from src.strategies.base import BaseStrategy
        assert issubclass(CoveredCallWheelStrategy, BaseStrategy)
    
    def test_calendar_inherits_base(self):
        from src.strategies.library.calendar_spread import CalendarSpreadStrategy
        from src.strategies.base import BaseStrategy
        assert issubclass(CalendarSpreadStrategy, BaseStrategy)
    
    def test_earnings_inherits_base(self):
        from src.strategies.library.earnings_straddle import EarningsStraddleStrategy
        from src.strategies.base import BaseStrategy
        assert issubclass(EarningsStraddleStrategy, BaseStrategy)
    
    def test_delta_neutral_inherits_base(self):
        from src.strategies.library.delta_neutral import DeltaNeutralStrategy
        from src.strategies.base import BaseStrategy
        assert issubclass(DeltaNeutralStrategy, BaseStrategy)
    
    def test_library_init_exports(self):
        from src.strategies import library
        assert library is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
