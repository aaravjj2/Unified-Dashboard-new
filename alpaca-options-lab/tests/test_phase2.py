"""
Alpaca Options Lab - Phase 2 Tests
100% Pass Rate Required
"""
import pytest
from datetime import datetime, date, timezone
from unittest.mock import MagicMock
import sys
sys.path.insert(0, '.')


class TestStrategyEngine:
    def test_strategy_registry(self):
        from src.strategies.registry import StrategyRegistry
        assert hasattr(StrategyRegistry, 'list_available')
        
    def test_strategy_context(self):
        from src.strategies.context import StrategyContext
        context = StrategyContext(portfolio=MagicMock(), risk_manager=MagicMock(),
            order_manager=MagicMock(), market_data=MagicMock(), greeks_engine=MagicMock())
        assert context is not None
        
    def test_strategy_executor(self):
        from src.strategies.executor import StrategyExecutor
        executor = StrategyExecutor(context=MagicMock())
        assert executor is not None
        
    def test_iron_condor_strategy(self):
        from src.strategies.library import iron_condor
        assert hasattr(iron_condor, 'IronCondor0DTEStrategy')


class TestOrderRouter:
    def test_order_types(self):
        from src.orders.types import Order, OrderType, OrderSide
        order = Order(contract_id=12345, symbol="AAPL240119C00150000",
                      side=OrderSide.BUY_TO_OPEN, quantity=10, order_type=OrderType.LIMIT, limit_price=5.50)
        assert order.symbol == "AAPL240119C00150000"
        
    def test_multi_leg_order(self):
        from src.orders.types import MultiLegOrder, OrderLeg, OrderSide
        legs = [OrderLeg(contract_id=1, symbol="AAPL", side=OrderSide.BUY_TO_OPEN, quantity=1),
                OrderLeg(contract_id=2, symbol="AAPL", side=OrderSide.SELL_TO_OPEN, quantity=1)]
        multi = MultiLegOrder(legs=legs, net_price=1.00)
        assert len(multi.legs) == 2
        
    def test_smart_order_router(self):
        from src.orders.router import SmartOrderRouter, RoutingConfig
        router = SmartOrderRouter(broker=MagicMock(), config=RoutingConfig())
        assert router is not None
        
    def test_execution_simulator(self):
        from src.orders.execution import ExecutionSimulator, SimulatorConfig, FillMode
        simulator = ExecutionSimulator(config=SimulatorConfig(fill_mode=FillMode.REALISTIC))
        simulator.set_quote("AAPL", bid=150.0, ask=150.10)
        assert simulator.get_quote("AAPL").bid == 150.0


class TestVolatilityLab:
    def test_volatility_surface(self):
        from src.volatility.surface import VolatilitySurface, SurfaceConfig
        surface = VolatilitySurface(symbol="SPY", spot_price=450.0, config=SurfaceConfig())
        assert surface.symbol == "SPY"
        
    def test_iv_engine(self):
        from src.volatility.iv_engine import IVEngine, IVModel
        engine = IVEngine(risk_free_rate=0.05)
        result = engine.calculate_iv(market_price=10.0, spot=100.0, strike=100.0,
                                     time_to_expiry=30/365, is_call=True, model=IVModel.NEWTON_RAPHSON)
        assert result.iv > 0
        
    def test_greeks_calculation(self):
        from src.volatility.iv_engine import IVEngine
        engine = IVEngine()
        greeks = engine.all_greeks(spot=100.0, strike=100.0, time_to_expiry=30/365, volatility=0.25, is_call=True)
        assert "delta" in greeks and "gamma" in greeks
        
    def test_term_structure(self):
        from src.volatility.term_structure import TermStructure
        from datetime import timedelta
        term = TermStructure(symbol="SPY", spot_price=450.0)
        future_expiry = date.today() + timedelta(days=30)  # Future date
        term.add_point(expiry=future_expiry, iv=0.15)
        assert len(term._points) > 0  # Using private attr
        
    def test_volatility_skew(self):
        from src.volatility.skew import VolatilitySkew
        from datetime import timedelta
        future_expiry = date.today() + timedelta(days=30)  # Future date
        skew = VolatilitySkew(symbol="SPY", expiry=future_expiry, spot_price=450.0)
        skew.add_point(strike=440.0, iv=0.18)
        skew.add_point(strike=450.0, iv=0.15)
        assert len(skew._points) == 2  # Using private attr


class TestAnalytics:
    def test_performance_analyzer(self):
        from src.analytics.performance import PerformanceAnalyzer, Trade
        analyzer = PerformanceAnalyzer()
        analyzer.add_trade(Trade(trade_id="T001", symbol="SPY", strategy="test", side="long",
            entry_time=datetime(2024, 1, 2, 10, 0, tzinfo=timezone.utc), entry_price=1.00, quantity=10,
            exit_time=datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc), exit_price=1.50))
        summary = analyzer.get_summary()
        assert summary is not None
        
    def test_risk_analyzer(self):
        from src.analytics.risk import RiskAnalyzer
        analyzer = RiskAnalyzer()
        assert analyzer is not None
        
    def test_backtest_engine(self):
        from src.analytics.backtest import BacktestEngine, BacktestConfig
        config = BacktestConfig(start_date=date(2024, 1, 1), end_date=date(2024, 1, 31), initial_capital=100000.0)
        engine = BacktestEngine(config=config)
        assert engine is not None
        
    def test_ml_predictor(self):
        from src.analytics.ml_predictor import VolatilityPredictor
        predictor = VolatilityPredictor()
        assert predictor is not None


class TestMultiAccount:
    def test_account_manager(self):
        from src.accounts.manager import AccountManager, AccountType
        manager = AccountManager()
        manager.add_account(name="Test", account_type=AccountType.LIVE)
        accounts = manager.get_all_accounts()
        assert len(accounts) > 0
        
    def test_capital_allocator(self):
        from src.accounts.allocator import CapitalAllocator
        from src.accounts.manager import AccountManager
        allocator = CapitalAllocator(account_manager=AccountManager())
        assert allocator is not None
        
    def test_position_aggregator(self):
        from src.accounts.aggregator import PositionAggregator
        from src.accounts.manager import AccountManager
        aggregator = PositionAggregator(account_manager=AccountManager())
        assert aggregator is not None


class TestPaperTrading:
    def test_simulated_portfolio(self):
        from src.paper_trading.portfolio import SimulatedPortfolio
        portfolio = SimulatedPortfolio(initial_capital=100000.0)
        assert portfolio.cash == 100000.0
        
    def test_market_data_feed(self):
        from src.paper_trading.market_data import MarketDataFeed
        feed = MarketDataFeed()
        feed.set_price("AAPL", 150.0)
        assert feed.get_last_price("AAPL") == 150.0
        
    def test_order_simulator(self):
        from src.paper_trading.simulator import OrderSimulator
        simulator = OrderSimulator(slippage_bps=5.0)
        assert simulator is not None
        
    def test_paper_trading_engine(self):
        from src.paper_trading.engine import PaperTradingEngine, EngineConfig
        config = EngineConfig(initial_capital=100000.0)
        engine = PaperTradingEngine(config=config)
        assert engine is not None


class TestProductionComponents:
    def test_circuit_breaker(self):
        from src.production.circuit_breaker import CircuitBreaker, CircuitState, CircuitBreakerConfig
        config = CircuitBreakerConfig(failure_threshold=5, reset_timeout_seconds=30.0)
        breaker = CircuitBreaker("test_service", config)
        assert breaker.state == CircuitState.CLOSED
        
    def test_rate_limiter(self):
        from src.production.rate_limiter import RateLimiter, RateLimitConfig
        config = RateLimitConfig(requests_per_second=100)
        limiter = RateLimiter(config=config)
        assert limiter is not None
        
    @pytest.mark.asyncio
    async def test_health_check(self):
        from src.production.health_check import HealthMonitor, HealthStatus
        monitor = HealthMonitor()
        async def check_db(): return HealthStatus.HEALTHY
        monitor.register("database", check_db)
        status = await monitor.check_all()
        assert "database" in status
        
    @pytest.mark.asyncio
    async def test_alert_manager(self):
        from src.production.alerts import AlertManager, AlertLevel
        manager = AlertManager()
        await manager.alert(title="High CPU", message="CPU above 90%", level=AlertLevel.WARNING)
        
    def test_metrics_collector(self):
        from src.production.metrics import MetricsCollector
        collector = MetricsCollector()
        orders = collector.counter("orders_total", "Total orders processed")
        orders.inc()
        orders.inc()
        assert orders.value == 2


class TestIntegration:
    def test_end_to_end_paper_trading(self):
        from src.paper_trading.portfolio import SimulatedPortfolio
        from src.paper_trading.market_data import MarketDataFeed
        portfolio = SimulatedPortfolio(initial_capital=100000.0)
        feed = MarketDataFeed()
        feed.set_price("SPY", 450.0)
        assert portfolio.cash == 100000.0 and feed.get_last_price("SPY") == 450.0
        
    def test_strategy_to_execution(self):
        from src.orders.types import Order, OrderType, OrderSide
        from src.orders.execution import ExecutionSimulator
        order = Order(contract_id=1, symbol="SPY240216C00450000", side=OrderSide.BUY_TO_OPEN,
                      quantity=10, order_type=OrderType.LIMIT, limit_price=5.00)
        simulator = ExecutionSimulator()
        simulator.set_quote("SPY240216C00450000", bid=4.95, ask=5.05)
        assert order.validate() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
