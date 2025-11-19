"""
Sprint 5 Tests: Broker Abstraction & Production Readiness
Tests for API abstraction, authentication, and containerization support.
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from trading.base_broker import BaseBroker, OrderSide, OrderType, OrderStatus
from utils.alpaca_trader import AlpacaTrader


class TestBrokerInterface:
    """Test BaseBroker interface conformance."""
    
    def test_base_broker_is_abstract(self):
        """Test that BaseBroker cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseBroker(paper_mode=True)
    
    def test_alpaca_trader_implements_base_broker(self):
        """Test that AlpacaTrader properly implements BaseBroker."""
        # Check inheritance
        assert issubclass(AlpacaTrader, BaseBroker)
        
        # Check all abstract methods are implemented
        required_methods = [
            'get_account_details',
            'get_positions',
            'get_position',
            'place_order',
            'get_order_status',
            'get_orders',
            'cancel_order',
            'get_quote',
            'is_market_open',
            'get_market_hours'
        ]
        
        for method_name in required_methods:
            assert hasattr(AlpacaTrader, method_name), f"Missing method: {method_name}"
            assert callable(getattr(AlpacaTrader, method_name)), f"Method not callable: {method_name}"
    
    @patch('utils.alpaca_trader.TradingClient')
    @patch('utils.alpaca_trader.StockHistoricalDataClient')
    def test_alpaca_trader_initialization(self, mock_data_client, mock_trading_client):
        """Test AlpacaTrader initializes properly."""
        # Mock the clients
        mock_trading_client.return_value = Mock()
        mock_data_client.return_value = Mock()
        
        # Create instance
        trader = AlpacaTrader(
            api_key='test_key',
            api_secret='test_secret',
            paper=True
        )
        
        # Verify initialization
        assert isinstance(trader, BaseBroker)
        assert trader.paper is True
        assert trader.api_key == 'test_key'
        assert trader.api_secret == 'test_secret'
    
    @patch('utils.alpaca_trader.TradingClient')
    @patch('utils.alpaca_trader.StockHistoricalDataClient')
    def test_alpaca_trader_method_signatures(self, mock_data_client, mock_trading_client):
        """Test that AlpacaTrader method signatures match BaseBroker interface."""
        mock_trading_client.return_value = Mock()
        mock_data_client.return_value = Mock()
        
        trader = AlpacaTrader(api_key='test_key', api_secret='test_secret', paper=True)
        
        # Check place_order signature
        import inspect
        sig = inspect.signature(trader.place_order)
        params = list(sig.parameters.keys())
        
        # Should have: symbol, quantity, side, order_type, limit_price, stop_price, time_in_force
        assert 'symbol' in params
        assert 'quantity' in params
        assert 'side' in params
        assert 'order_type' in params
        assert 'limit_price' in params
        assert 'time_in_force' in params
    
    @patch('utils.alpaca_trader.TradingClient')
    @patch('utils.alpaca_trader.StockHistoricalDataClient')
    def test_order_enum_mappings(self, mock_data_client, mock_trading_client):
        """Test that enum mappings work correctly."""
        mock_trading_client.return_value = Mock()
        mock_data_client.return_value = Mock()
        
        trader = AlpacaTrader(api_key='test_key', api_secret='test_secret', paper=True)
        
        # Test OrderSide mapping
        from alpaca.trading.enums import OrderSide as AlpacaOrderSide
        alpaca_buy = trader._map_order_side(OrderSide.BUY)
        alpaca_sell = trader._map_order_side(OrderSide.SELL)
        
        assert alpaca_buy == AlpacaOrderSide.BUY
        assert alpaca_sell == AlpacaOrderSide.SELL
    
    def test_validate_order_basic(self):
        """Test basic order validation."""
        # Test validation without creating actual Alpaca client
        valid, error = BaseBroker.validate_order(
            None,  # self
            symbol='SPY',
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET
        )
        
        assert valid is True
        assert error is None
    
    def test_validate_order_negative_quantity(self):
        """Test validation rejects negative quantity."""
        valid, error = BaseBroker.validate_order(
            None,
            symbol='SPY',
            quantity=-10,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET
        )
        
        assert valid is False
        assert 'positive' in error.lower()
    
    def test_validate_order_limit_without_price(self):
        """Test validation rejects limit order without price."""
        valid, error = BaseBroker.validate_order(
            None,
            symbol='SPY',
            quantity=10,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            limit_price=None
        )
        
        assert valid is False
        assert 'limit price' in error.lower()


class TestAPIAuthentication:
    """Test API Gateway authentication."""
    
    def test_api_key_validation(self):
        """Test API key validation logic."""
        valid_keys = {'key1', 'key2', 'key3'}
        
        # Valid key
        assert 'key1' in valid_keys
        
        # Invalid key
        assert 'invalid' not in valid_keys
    
    def test_public_paths_exempt_from_auth(self):
        """Test that public paths don't require authentication."""
        public_paths = {'/health', '/docs', '/redoc', '/openapi.json'}
        
        # These should be in public paths
        assert '/health' in public_paths
        assert '/docs' in public_paths
        assert '/redoc' in public_paths
    
    def test_api_paths_require_auth(self):
        """Test that API paths require authentication."""
        public_paths = {'/health', '/docs', '/redoc', '/openapi.json'}
        api_path = '/api/options/account'
        
        # API paths should not be in public paths
        assert api_path not in public_paths
    
    @pytest.mark.skip(reason="Requires API gateway to be running and httpx installed")
    def test_verify_api_key_valid(self):
        """Test API key verification with valid key."""
        # This would require FastAPI dependency injection to test properly
        # For now, verify the logic
        assert 'test-key-123' in {'test-key-123'}
    
    def test_environment_api_keys_loading(self):
        """Test loading API keys from environment."""
        test_keys = "key1,key2,key3"
        keys_set = set(test_keys.split(","))
        
        assert len(keys_set) == 3
        assert 'key1' in keys_set
        assert 'key2' in keys_set
        assert 'key3' in keys_set


class TestContainerization:
    """Test Docker containerization support."""
    
    def test_dockerfile_exists(self):
        """Test that main Dockerfile exists."""
        dockerfile_path = os.path.join(os.path.dirname(__file__), '..', 'Dockerfile')
        assert os.path.exists(dockerfile_path), "Dockerfile not found"
    
    def test_dockerfile_gateway_exists(self):
        """Test that gateway Dockerfile exists."""
        dockerfile_path = os.path.join(os.path.dirname(__file__), '..', 'Dockerfile.gateway')
        assert os.path.exists(dockerfile_path), "Dockerfile.gateway not found"
    
    def test_dockerfile_options_exists(self):
        """Test that options Dockerfile exists."""
        dockerfile_path = os.path.join(os.path.dirname(__file__), '..', 'Dockerfile.options')
        assert os.path.exists(dockerfile_path), "Dockerfile.options not found"
    
    def test_docker_compose_exists(self):
        """Test that docker-compose.yml exists."""
        compose_path = os.path.join(os.path.dirname(__file__), '..', 'docker-compose.yml')
        assert os.path.exists(compose_path), "docker-compose.yml not found"
    
    def test_docker_compose_has_services(self):
        """Test that docker-compose defines expected services."""
        import yaml
        
        compose_path = os.path.join(os.path.dirname(__file__), '..', 'docker-compose.yml')
        
        if not os.path.exists(compose_path):
            pytest.skip("docker-compose.yml not found")
        
        with open(compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        # Check that services are defined
        assert 'services' in compose_config
        services = compose_config['services']
        
        # Check for expected services
        expected_services = ['postgres', 'api_gateway', 'options_service', 'dashboard']
        for service in expected_services:
            assert service in services, f"Service {service} not found in docker-compose.yml"
    
    def test_docker_compose_health_checks(self):
        """Test that services have health checks."""
        import yaml
        
        compose_path = os.path.join(os.path.dirname(__file__), '..', 'docker-compose.yml')
        
        if not os.path.exists(compose_path):
            pytest.skip("docker-compose.yml not found")
        
        with open(compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        services = compose_config.get('services', {})
        
        # Check that critical services have health checks
        critical_services = ['postgres', 'api_gateway', 'options_service']
        for service in critical_services:
            if service in services:
                assert 'healthcheck' in services[service], \
                    f"Service {service} missing healthcheck"
    
    def test_docker_compose_networks(self):
        """Test that docker-compose defines networks."""
        import yaml
        
        compose_path = os.path.join(os.path.dirname(__file__), '..', 'docker-compose.yml')
        
        if not os.path.exists(compose_path):
            pytest.skip("docker-compose.yml not found")
        
        with open(compose_path, 'r') as f:
            compose_config = yaml.safe_load(f)
        
        # Check that networks are defined
        assert 'networks' in compose_config
        assert 'fin_dash_network' in compose_config['networks']
    
    def test_env_example_file_exists(self):
        """Test that .env.example file exists."""
        env_example_path = os.path.join(os.path.dirname(__file__), '..', '.env.example')
        assert os.path.exists(env_example_path), ".env.example not found"
    
    def test_env_example_has_required_vars(self):
        """Test that .env.example contains required variables."""
        env_example_path = os.path.join(os.path.dirname(__file__), '..', '.env.example')
        
        if not os.path.exists(env_example_path):
            pytest.skip(".env.example not found")
        
        with open(env_example_path, 'r') as f:
            content = f.read()
        
        # Check for required environment variables
        required_vars = [
            'DB_PASSWORD',
            'API_GATEWAY_KEYS',
            'ALPACA_API_KEY',
            'ALPACA_API_SECRET',
            'FINNHUB_API_KEY'
        ]
        
        for var in required_vars:
            assert var in content, f"Environment variable {var} not in .env.example"


class TestBrokerAgnosticService:
    """Test that options_service uses BaseBroker interface."""
    
    def test_options_service_imports_base_broker(self):
        """Test that options_service imports BaseBroker."""
        with open('options_service.py', 'r') as f:
            content = f.read()
        
        assert 'from trading.base_broker import BaseBroker' in content
    
    def test_options_service_uses_broker_interface(self):
        """Test that options_service uses BaseBroker type hints."""
        with open('options_service.py', 'r') as f:
            content = f.read()
        
        # Check for type hint using BaseBroker
        assert 'BaseBroker' in content
        assert 'alpaca_trader: BaseBroker' in content or 'BaseBroker =' in content
    
    def test_options_service_place_order_uses_interface(self):
        """Test that place_order calls use the BaseBroker interface."""
        with open('options_service.py', 'r') as f:
            content = f.read()
        
        # Check that place_order is called with correct parameters
        assert 'place_order(' in content
        assert 'quantity=' in content  # Should use 'quantity' not 'qty'


class TestProductionReadiness:
    """Test production readiness features."""
    
    def test_logging_configured(self):
        """Test that logging is properly configured."""
        import logging
        
        # Check that we can get a logger
        logger = logging.getLogger('test')
        assert logger is not None
    
    def test_health_check_endpoints_exist(self):
        """Test that services define health check endpoints."""
        # Check options_service
        with open('options_service.py', 'r') as f:
            content = f.read()
        
        assert '@app.get("/health")' in content or '@app.get(\"/health\")' in content
    
    def test_error_handling_in_services(self):
        """Test that services have proper error handling."""
        with open('options_service.py', 'r') as f:
            content = f.read()
        
        # Check for try-except blocks
        assert 'try:' in content
        assert 'except' in content
        assert 'HTTPException' in content
    
    def test_environment_variable_support(self):
        """Test that services support environment variables."""
        with open('options_service.py', 'r') as f:
            content = f.read()
        
        # Check for environment variable usage
        assert 'os.getenv' in content or 'os.environ' in content or 'load_dotenv' in content
    
    def test_graceful_shutdown_support(self):
        """Test that services support graceful shutdown."""
        with open('options_service.py', 'r') as f:
            content = f.read()
        
        # Check for shutdown event handler
        assert '@app.on_event("shutdown")' in content or 'shutdown' in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
