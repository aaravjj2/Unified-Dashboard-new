"""
Sprint 5 Unit Tests: Production Readiness & Broker Abstraction
==============================================================

Tests for:
- Broker abstraction layer (BaseBroker interface compliance)
- API authentication system
- Docker configuration validation
- Production-ready features

Run with:
    pytest tests/test_sprint_5_unit.py -v
"""

import pytest
import os
import yaml
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any


# =============================================================================
# Test Group 1: Broker Abstraction Layer
# =============================================================================

class TestBrokerAbstraction:
    """Test that AlpacaTrader correctly implements BaseBroker interface."""
    
    def test_broker_interface_import(self):
        """Test that broker interface and implementation can be imported."""
        from trading.base_broker import BaseBroker, OrderSide, OrderType, OrderStatus
        from utils.alpaca_trader import AlpacaTrader
        
        # Verify enums exist
        assert hasattr(OrderSide, 'BUY')
        assert hasattr(OrderSide, 'SELL')
        assert hasattr(OrderType, 'MARKET')
        assert hasattr(OrderType, 'LIMIT')
        assert hasattr(OrderStatus, 'PENDING')
        assert hasattr(OrderStatus, 'FILLED')
    
    def test_alpaca_implements_base_broker(self):
        """Test that AlpacaTrader is a subclass of BaseBroker."""
        from trading.base_broker import BaseBroker
        from utils.alpaca_trader import AlpacaTrader
        
        assert issubclass(AlpacaTrader, BaseBroker)
    
    def test_broker_interface_methods_exist(self):
        """Test that all required interface methods exist on AlpacaTrader."""
        from utils.alpaca_trader import AlpacaTrader
        
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
            assert callable(getattr(AlpacaTrader, method_name))
    
    @patch('utils.alpaca_trader.TradingClient')
    @patch('utils.alpaca_trader.StockHistoricalDataClient')
    def test_alpaca_initialization_with_paper_mode(self, mock_data_client, mock_trading_client):
        """Test AlpacaTrader initialization in paper mode."""
        from utils.alpaca_trader import AlpacaTrader
        
        # Create trader with paper_mode=True
        with patch.dict(os.environ, {'ALPACA_API_KEY': 'test_key', 'ALPACA_API_SECRET': 'test_secret'}):
            trader = AlpacaTrader(paper_mode=True)
            
            assert trader.paper_mode is True
            assert mock_trading_client.called
            # Check that TradingClient was called with paper=True
            call_args = mock_trading_client.call_args
            assert call_args[1]['paper'] is True
    
    @patch('utils.alpaca_trader.TradingClient')
    @patch('utils.alpaca_trader.StockHistoricalDataClient')
    def test_alpaca_initialization_with_config(self, mock_data_client, mock_trading_client):
        """Test AlpacaTrader initialization with config dict."""
        from utils.alpaca_trader import AlpacaTrader
        
        config = {
            'api_key': 'config_key',
            'api_secret': 'config_secret',
            'custom_param': 'value'
        }
        
        trader = AlpacaTrader(paper_mode=True, config=config)
        
        assert trader.config == config
        assert trader.config.get('custom_param') == 'value'
    
    @patch('utils.alpaca_trader.TradingClient')
    @patch('utils.alpaca_trader.StockHistoricalDataClient')
    def test_get_account_details_returns_correct_structure(self, mock_data_client, mock_trading_client):
        """Test that get_account_details returns the correct dict structure."""
        from utils.alpaca_trader import AlpacaTrader
        
        # Mock account object
        mock_account = Mock()
        mock_account.account_number = 'TEST123'
        mock_account.cash = 10000.0
        mock_account.portfolio_value = 50000.0
        mock_account.buying_power = 20000.0
        mock_account.equity = 50000.0
        mock_account.last_equity = 49000.0
        mock_account.pattern_day_trader = False
        mock_account.trading_blocked = False
        mock_account.account_blocked = False
        
        mock_trading_client.return_value.get_account.return_value = mock_account
        
        with patch.dict(os.environ, {'ALPACA_API_KEY': 'test_key', 'ALPACA_API_SECRET': 'test_secret'}):
            trader = AlpacaTrader(paper_mode=True)
            account_info = trader.get_account_details()
        
        # Check required BaseBroker interface fields
        required_fields = ['account_id', 'buying_power', 'cash', 'portfolio_value', 'equity', 'currency']
        for field in required_fields:
            assert field in account_info, f"Missing required field: {field}"
        
        assert account_info['account_id'] == 'TEST123'
        assert account_info['cash'] == 10000.0
        assert account_info['currency'] == 'USD'
    
    @patch('utils.alpaca_trader.TradingClient')
    @patch('utils.alpaca_trader.StockHistoricalDataClient')
    def test_get_positions_returns_correct_structure(self, mock_data_client, mock_trading_client):
        """Test that get_positions returns correctly structured list."""
        from utils.alpaca_trader import AlpacaTrader
        
        # Mock position objects
        mock_pos1 = Mock()
        mock_pos1.symbol = 'AAPL'
        mock_pos1.qty = '10'
        mock_pos1.market_value = 1500.0
        mock_pos1.cost_basis = 1400.0
        mock_pos1.unrealized_pl = 100.0
        mock_pos1.unrealized_plpc = 0.0714
        mock_pos1.current_price = 150.0
        mock_pos1.avg_entry_price = 140.0
        mock_pos1.side = 'long'
        mock_pos1.asset_class = 'us_equity'
        
        mock_trading_client.return_value.get_all_positions.return_value = [mock_pos1]
        
        with patch.dict(os.environ, {'ALPACA_API_KEY': 'test_key', 'ALPACA_API_SECRET': 'test_secret'}):
            trader = AlpacaTrader(paper_mode=True)
            positions = trader.get_positions()
        
        assert len(positions) == 1
        
        # Check required BaseBroker interface fields
        required_fields = ['symbol', 'quantity', 'market_value', 'cost_basis', 
                          'unrealized_pl', 'unrealized_plpc', 'current_price', 'avg_entry_price']
        for field in required_fields:
            assert field in positions[0], f"Missing required field: {field}"
        
        assert positions[0]['symbol'] == 'AAPL'
        assert positions[0]['quantity'] == 10  # Should be int
        assert isinstance(positions[0]['quantity'], int)


# =============================================================================
# Test Group 2: API Authentication
# =============================================================================

class TestAPIAuthentication:
    """Test API Gateway authentication system."""
    
    def test_api_gateway_imports(self):
        """Test that API Gateway with auth can be imported."""
        from fastapi.security import APIKeyHeader
        import api_gateway
        
        # Verify auth components exist
        assert hasattr(api_gateway, 'verify_api_key')
        assert hasattr(api_gateway, 'api_key_header')
    
    @pytest.mark.asyncio
    async def test_valid_api_key_authentication(self):
        """Test that valid API key grants access."""
        from fastapi import Request, HTTPException
        from api_gateway import verify_api_key, VALID_API_KEYS
        
        # Create a mock request from localhost (bypasses API key)
        mock_request = Mock(spec=Request)
        mock_request.client = Mock()
        mock_request.client.host = "127.0.0.1"
        
        # Should not raise exception for localhost
        result = await verify_api_key(mock_request, None)
        assert result is not None
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self):
        """Test that invalid API key is rejected."""
        from fastapi import Request, HTTPException
        from api_gateway import verify_api_key
        
        # Create a mock request from remote host with invalid key
        mock_request = Mock(spec=Request)
        mock_request.client = Mock()
        mock_request.client.host = "192.168.1.100"
        
        # Should raise 401 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(mock_request, "invalid_key_123")
        
        assert exc_info.value.status_code == 401
    
    @pytest.mark.asyncio
    async def test_missing_api_key_rejected(self):
        """Test that missing API key is rejected for remote requests."""
        from fastapi import Request, HTTPException
        from api_gateway import verify_api_key
        
        # Create a mock request from remote host without key
        mock_request = Mock(spec=Request)
        mock_request.client = Mock()
        mock_request.client.host = "10.0.0.5"
        
        # Should raise 401 HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await verify_api_key(mock_request, None)
        
        assert exc_info.value.status_code == 401
    
    def test_public_paths_configuration(self):
        """Test that public paths are correctly configured."""
        from api_gateway import PUBLIC_PATHS
        
        # Verify essential public paths exist
        assert "/health" in PUBLIC_PATHS
        assert "/docs" in PUBLIC_PATHS or "/openapi.json" in PUBLIC_PATHS


# =============================================================================
# Test Group 3: Docker Configuration
# =============================================================================

class TestDockerConfiguration:
    """Test Docker and docker-compose configuration."""
    
    def test_docker_compose_file_exists(self):
        """Test that docker-compose.yml exists."""
        assert os.path.exists('docker-compose.yml'), "docker-compose.yml not found"
    
    def test_docker_compose_valid_yaml(self):
        """Test that docker-compose.yml is valid YAML."""
        with open('docker-compose.yml', 'r') as f:
            config = yaml.safe_load(f)
        
        assert config is not None
        assert 'services' in config
    
    def test_docker_compose_has_required_services(self):
        """Test that all required services are defined."""
        with open('docker-compose.yml', 'r') as f:
            config = yaml.safe_load(f)
        
        required_services = ['postgres', 'api_gateway', 'options_service', 'dashboard']
        
        for service in required_services:
            assert service in config['services'], f"Missing service: {service}"
    
    def test_docker_compose_postgres_config(self):
        """Test PostgreSQL service configuration."""
        with open('docker-compose.yml', 'r') as f:
            config = yaml.safe_load(f)
        
        postgres = config['services']['postgres']
        
        # Check essential postgres config
        assert 'image' in postgres
        assert 'postgres' in postgres['image']
        assert 'environment' in postgres
        assert 'POSTGRES_DB' in postgres['environment']
        assert 'healthcheck' in postgres
    
    def test_docker_compose_api_gateway_config(self):
        """Test API Gateway service configuration."""
        with open('docker-compose.yml', 'r') as f:
            config = yaml.safe_load(f)
        
        gateway = config['services']['api_gateway']
        
        # Check essential gateway config
        assert 'build' in gateway
        assert 'ports' in gateway
        assert '8049' in str(gateway['ports'])  # Should expose port 8049
        assert 'healthcheck' in gateway
        assert 'environment' in gateway
        assert 'API_GATEWAY_KEYS' in gateway['environment']
    
    def test_docker_compose_options_service_config(self):
        """Test Options Service configuration."""
        with open('docker-compose.yml', 'r') as f:
            config = yaml.safe_load(f)
        
        options = config['services']['options_service']
        
        # Check essential options service config
        assert 'build' in options
        assert 'ports' in options
        assert '8060' in str(options['ports'])  # Should expose port 8060
        assert 'healthcheck' in options
    
    def test_docker_compose_dashboard_config(self):
        """Test Dashboard service configuration."""
        with open('docker-compose.yml', 'r') as f:
            config = yaml.safe_load(f)
        
        dashboard = config['services']['dashboard']
        
        # Check essential dashboard config
        assert 'build' in dashboard
        assert 'ports' in dashboard
        assert '8050' in str(dashboard['ports'])  # Should expose port 8050
        assert 'depends_on' in dashboard
        assert 'postgres' in dashboard['depends_on']
    
    def test_docker_compose_network_configuration(self):
        """Test network configuration."""
        with open('docker-compose.yml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Should have network definition
        assert 'networks' in config
        
        # All services should be on the same network
        for service_name, service_config in config['services'].items():
            assert 'networks' in service_config, f"Service {service_name} not on any network"
    
    def test_docker_compose_volumes_configuration(self):
        """Test volumes configuration."""
        with open('docker-compose.yml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Should have volumes for postgres persistence
        assert 'volumes' in config
        assert 'postgres_data' in config['volumes']
    
    def test_dockerfile_exists(self):
        """Test that main Dockerfile exists."""
        assert os.path.exists('Dockerfile'), "Dockerfile not found"
    
    def test_dockerfile_gateway_exists(self):
        """Test that API Gateway Dockerfile exists."""
        assert os.path.exists('Dockerfile.gateway'), "Dockerfile.gateway not found"
    
    def test_dockerfile_options_exists(self):
        """Test that Options Service Dockerfile exists."""
        assert os.path.exists('Dockerfile.options'), "Dockerfile.options not found"
    
    def test_dockerfiles_have_healthchecks(self):
        """Test that all Dockerfiles include health checks."""
        dockerfiles = ['Dockerfile', 'Dockerfile.gateway', 'Dockerfile.options']
        
        for dockerfile in dockerfiles:
            with open(dockerfile, 'r') as f:
                content = f.read()
            
            assert 'HEALTHCHECK' in content, f"{dockerfile} missing HEALTHCHECK"


# =============================================================================
# Test Group 4: Options Service Broker Integration
# =============================================================================

class TestOptionsServiceBrokerIntegration:
    """Test that options service uses BaseBroker interface."""
    
    def test_options_service_imports_base_broker(self):
        """Test that options service imports BaseBroker."""
        import services.options_service as options_svc
        
        # Should have BaseBroker imported
        from trading.base_broker import BaseBroker
        
        # Verify the module can access BaseBroker
        assert 'BaseBroker' in dir(options_svc) or 'broker' in dir(options_svc)
    
    def test_options_service_has_broker_endpoints(self):
        """Test that options service has broker-related endpoints."""
        from services.options_service import app
        
        # Get all route paths
        routes = [route.path for route in app.routes]
        
        # Should have broker endpoints
        assert any('/broker/account' in route for route in routes), "Missing /broker/account endpoint"
        assert any('/broker/positions' in route for route in routes), "Missing /broker/positions endpoint"


# =============================================================================
# Summary Test
# =============================================================================

def test_sprint_5_all_components_present():
    """Meta-test: Verify all Sprint 5 components are present."""
    components = {
        'BaseBroker interface': 'trading/base_broker.py',
        'AlpacaTrader implementation': 'utils/alpaca_trader.py',
        'API Gateway with auth': 'api_gateway.py',
        'Docker compose': 'docker-compose.yml',
        'Main Dockerfile': 'Dockerfile',
        'Gateway Dockerfile': 'Dockerfile.gateway',
        'Options Dockerfile': 'Dockerfile.options',
    }
    
    for name, path in components.items():
        assert os.path.exists(path), f"Missing component: {name} ({path})"
    
    print("\n✓ All Sprint 5 production readiness components are present")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
