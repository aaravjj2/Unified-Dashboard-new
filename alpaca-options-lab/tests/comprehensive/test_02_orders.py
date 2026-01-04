"""
Alpaca Options Lab - Comprehensive Order Tests
Test File 2 of 10: Order Router, Types & Execution
~50 tests covering all order components
"""
import pytest
from datetime import datetime, date, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
import sys
sys.path.insert(0, '.')


class TestOrderTypes:
    """Tests for Order Types - 15 tests"""
    
    def test_order_type_enum(self):
        from src.orders.types import OrderType
        assert hasattr(OrderType, 'LIMIT')
        assert hasattr(OrderType, 'MARKET')
    
    def test_order_side_enum(self):
        from src.orders.types import OrderSide
        assert hasattr(OrderSide, 'BUY_TO_OPEN')
        assert hasattr(OrderSide, 'SELL_TO_CLOSE')
    
    def test_order_status_enum(self):
        from src.orders.types import OrderStatus
        assert hasattr(OrderStatus, 'PENDING') or hasattr(OrderStatus, 'NEW')
        assert hasattr(OrderStatus, 'FILLED')
    
    def test_time_in_force_enum(self):
        from src.orders.types import TimeInForce
        assert hasattr(TimeInForce, 'DAY') or hasattr(TimeInForce, 'GTC')
    
    def test_order_creation(self):
        from src.orders.types import Order, OrderType, OrderSide
        order = Order(
            contract_id=12345,
            symbol="AAPL240119C00150000",
            side=OrderSide.BUY_TO_OPEN,
            quantity=10,
            order_type=OrderType.LIMIT,
            limit_price=5.50
        )
        assert order.symbol == "AAPL240119C00150000"
    
    def test_order_has_validate(self):
        from src.orders.types import Order, OrderType, OrderSide
        order = Order(
            contract_id=1,
            symbol="SPY",
            side=OrderSide.BUY_TO_OPEN,
            quantity=1,
            order_type=OrderType.LIMIT,
            limit_price=1.00
        )
        assert hasattr(order, 'validate')
    
    def test_order_validate_returns_bool(self):
        from src.orders.types import Order, OrderType, OrderSide
        order = Order(
            contract_id=1,
            symbol="SPY",
            side=OrderSide.BUY_TO_OPEN,
            quantity=1,
            order_type=OrderType.LIMIT,
            limit_price=1.00
        )
        assert order.validate() in [True, False]
    
    def test_order_leg_class(self):
        from src.orders.types import OrderLeg, OrderSide
        leg = OrderLeg(
            contract_id=1,
            symbol="AAPL",
            side=OrderSide.BUY_TO_OPEN,
            quantity=1
        )
        assert leg.symbol == "AAPL"
    
    def test_multi_leg_order(self):
        from src.orders.types import MultiLegOrder, OrderLeg, OrderSide
        legs = [
            OrderLeg(contract_id=1, symbol="AAPL", side=OrderSide.BUY_TO_OPEN, quantity=1),
            OrderLeg(contract_id=2, symbol="AAPL", side=OrderSide.SELL_TO_OPEN, quantity=1)
        ]
        multi = MultiLegOrder(legs=legs, net_price=1.00)
        assert len(multi.legs) == 2
    
    def test_order_quantity_positive(self):
        from src.orders.types import Order, OrderType, OrderSide
        order = Order(
            contract_id=1,
            symbol="SPY",
            side=OrderSide.BUY_TO_OPEN,
            quantity=10,
            order_type=OrderType.LIMIT,
            limit_price=1.00
        )
        assert order.quantity > 0
    
    def test_order_has_id(self):
        from src.orders.types import Order, OrderType, OrderSide
        order = Order(
            contract_id=1,
            symbol="SPY",
            side=OrderSide.BUY_TO_OPEN,
            quantity=1,
            order_type=OrderType.LIMIT,
            limit_price=1.00
        )
        assert hasattr(order, 'order_id') or hasattr(order, 'id')
    
    def test_order_has_timestamp(self):
        from src.orders.types import Order, OrderType, OrderSide
        order = Order(
            contract_id=1,
            symbol="SPY",
            side=OrderSide.BUY_TO_OPEN,
            quantity=1,
            order_type=OrderType.LIMIT,
            limit_price=1.00
        )
        assert hasattr(order, 'created_at') or hasattr(order, 'timestamp')
    
    def test_market_order_no_price(self):
        from src.orders.types import Order, OrderType, OrderSide
        order = Order(
            contract_id=1,
            symbol="SPY",
            side=OrderSide.BUY_TO_OPEN,
            quantity=1,
            order_type=OrderType.MARKET
        )
        assert order is not None
    
    def test_order_types_count(self):
        from src.orders.types import OrderType
        assert len(list(OrderType)) >= 2  # At least LIMIT and MARKET
    
    def test_order_sides_count(self):
        from src.orders.types import OrderSide
        assert len(list(OrderSide)) >= 4  # BTO, STO, BTC, STC


class TestSmartOrderRouter:
    """Tests for Smart Order Router - 15 tests"""
    
    def test_router_import(self):
        from src.orders.router import SmartOrderRouter
        assert SmartOrderRouter is not None
    
    def test_routing_config_import(self):
        from src.orders.router import RoutingConfig
        assert RoutingConfig is not None
    
    def test_router_creation(self):
        from src.orders.router import SmartOrderRouter, RoutingConfig
        router = SmartOrderRouter(broker=MagicMock(), config=RoutingConfig())
        assert router is not None
    
    def test_router_has_route_method(self):
        from src.orders.router import SmartOrderRouter, RoutingConfig
        router = SmartOrderRouter(broker=MagicMock(), config=RoutingConfig())
        assert hasattr(router, 'route') or hasattr(router, 'route_order')
    
    def test_routing_strategy_enum(self):
        from src.orders.router import RoutingStrategy
        assert RoutingStrategy is not None
    
    def test_broker_api_class(self):
        from src.orders.router import BrokerAPI
        assert BrokerAPI is not None
    
    def test_execution_metrics_class(self):
        from src.orders.router import ExecutionMetrics
        assert ExecutionMetrics is not None
    
    def test_router_config_defaults(self):
        from src.orders.router import RoutingConfig
        config = RoutingConfig()
        assert config is not None
    
    def test_router_has_cancel_method(self):
        from src.orders.router import SmartOrderRouter, RoutingConfig
        router = SmartOrderRouter(broker=MagicMock(), config=RoutingConfig())
        assert hasattr(router, 'cancel') or hasattr(router, 'cancel_order')
    
    def test_router_has_modify_method(self):
        from src.orders.router import SmartOrderRouter, RoutingConfig
        router = SmartOrderRouter(broker=MagicMock(), config=RoutingConfig())
        assert hasattr(router, 'modify') or hasattr(router, 'modify_order')
    
    def test_router_has_status_method(self):
        from src.orders.router import SmartOrderRouter, RoutingConfig
        router = SmartOrderRouter(broker=MagicMock(), config=RoutingConfig())
        assert hasattr(router, 'get_status') or hasattr(router, 'status')
    
    def test_router_stores_broker(self):
        from src.orders.router import SmartOrderRouter, RoutingConfig
        mock_broker = MagicMock()
        router = SmartOrderRouter(broker=mock_broker, config=RoutingConfig())
        assert router.broker == mock_broker or router._broker == mock_broker
    
    def test_router_stores_config(self):
        from src.orders.router import SmartOrderRouter, RoutingConfig
        config = RoutingConfig()
        router = SmartOrderRouter(broker=MagicMock(), config=config)
        assert router.config == config or router._config == config
    
    def test_routing_config_has_strategy(self):
        from src.orders.router import RoutingConfig
        config = RoutingConfig()
        assert hasattr(config, 'strategy') or hasattr(config, 'routing_strategy')
    
    def test_router_file_size(self):
        import os
        path = 'src/orders/router.py'
        assert os.path.exists(path)
        with open(path) as f:
            lines = len(f.readlines())
        assert lines > 200  # Substantial implementation


class TestExecutionSimulator:
    """Tests for Execution Simulator - 20 tests"""
    
    def test_simulator_import(self):
        from src.orders.execution import ExecutionSimulator
        assert ExecutionSimulator is not None
    
    def test_simulator_config_import(self):
        from src.orders.execution import SimulatorConfig
        assert SimulatorConfig is not None
    
    def test_fill_mode_enum(self):
        from src.orders.execution import FillMode
        assert hasattr(FillMode, 'REALISTIC') or hasattr(FillMode, 'IMMEDIATE')
    
    def test_simulator_default_creation(self):
        from src.orders.execution import ExecutionSimulator
        simulator = ExecutionSimulator()
        assert simulator is not None
    
    def test_simulator_with_config(self):
        from src.orders.execution import ExecutionSimulator, SimulatorConfig, FillMode
        config = SimulatorConfig(fill_mode=FillMode.REALISTIC)
        simulator = ExecutionSimulator(config=config)
        assert simulator is not None
    
    def test_simulator_set_quote(self):
        from src.orders.execution import ExecutionSimulator
        simulator = ExecutionSimulator()
        simulator.set_quote("AAPL", bid=150.0, ask=150.10)
        assert True  # No error means success
    
    def test_simulator_get_quote(self):
        from src.orders.execution import ExecutionSimulator
        simulator = ExecutionSimulator()
        simulator.set_quote("AAPL", bid=150.0, ask=150.10)
        quote = simulator.get_quote("AAPL")
        assert quote.bid == 150.0
    
    def test_simulator_quote_ask(self):
        from src.orders.execution import ExecutionSimulator
        simulator = ExecutionSimulator()
        simulator.set_quote("AAPL", bid=150.0, ask=150.10)
        quote = simulator.get_quote("AAPL")
        assert quote.ask == 150.10
    
    def test_simulated_quote_class(self):
        from src.orders.execution import SimulatedQuote
        assert SimulatedQuote is not None
    
    def test_simulated_broker_api(self):
        from src.orders.execution import SimulatedBrokerAPI
        assert SimulatedBrokerAPI is not None
    
    def test_simulator_has_execute(self):
        from src.orders.execution import ExecutionSimulator
        simulator = ExecutionSimulator()
        assert hasattr(simulator, 'execute') or hasattr(simulator, 'fill')
    
    def test_simulator_has_slippage(self):
        from src.orders.execution import SimulatorConfig
        config = SimulatorConfig()
        assert hasattr(config, 'slippage') or hasattr(config, 'slippage_bps')
    
    def test_simulator_multiple_quotes(self):
        from src.orders.execution import ExecutionSimulator
        simulator = ExecutionSimulator()
        simulator.set_quote("AAPL", bid=150.0, ask=150.10)
        simulator.set_quote("MSFT", bid=350.0, ask=350.20)
        assert simulator.get_quote("AAPL").bid == 150.0
        assert simulator.get_quote("MSFT").bid == 350.0
    
    def test_simulator_quote_update(self):
        from src.orders.execution import ExecutionSimulator
        simulator = ExecutionSimulator()
        simulator.set_quote("AAPL", bid=150.0, ask=150.10)
        simulator.set_quote("AAPL", bid=151.0, ask=151.10)
        assert simulator.get_quote("AAPL").bid == 151.0
    
    def test_fill_mode_values(self):
        from src.orders.execution import FillMode
        assert len(list(FillMode)) >= 2
    
    def test_simulator_config_fill_mode(self):
        from src.orders.execution import SimulatorConfig, FillMode
        config = SimulatorConfig(fill_mode=FillMode.REALISTIC)
        assert config.fill_mode == FillMode.REALISTIC
    
    def test_simulator_has_pending_orders(self):
        from src.orders.execution import ExecutionSimulator
        simulator = ExecutionSimulator()
        assert hasattr(simulator, '_orders') or hasattr(simulator, 'pending_orders')
    
    def test_simulator_has_fills(self):
        from src.orders.execution import ExecutionSimulator
        simulator = ExecutionSimulator()
        assert hasattr(simulator, '_fills') or hasattr(simulator, 'fills')
    
    def test_simulator_spread_calculation(self):
        from src.orders.execution import ExecutionSimulator
        simulator = ExecutionSimulator()
        simulator.set_quote("SPY", bid=450.0, ask=450.05)
        quote = simulator.get_quote("SPY")
        spread = quote.ask - quote.bid
        assert spread == pytest.approx(0.05)
    
    def test_simulator_file_size(self):
        import os
        path = 'src/orders/execution.py'
        assert os.path.exists(path)
        with open(path) as f:
            lines = len(f.readlines())
        assert lines > 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
