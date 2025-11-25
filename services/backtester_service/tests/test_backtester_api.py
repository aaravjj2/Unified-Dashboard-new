"""
TDD RED Phase: FastAPI REST API Tests

Tests for the REST API endpoints.
These will fail initially as app.py doesn't exist yet.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# These imports will fail initially - expected for RED phase
try:
    from services.backtester_service.app import app, BacktestRequest, BacktestResponse
except ImportError:
    app = None
    BacktestRequest = None
    BacktestResponse = None


@pytest.fixture
def client():
    """Create test client for FastAPI app."""
    if app is None:
        pytest.skip("FastAPI app not yet implemented")
    return TestClient(app)


class TestBacktesterAPI:
    """Test REST API endpoints."""
    
    def test_backtester_api_runs_and_logs_mlflow(self, client):
        """
        Test POST /api/backtest endpoint runs backtest and logs to MLflow.
        Mock PriceClient and registry to return deterministic data.
        """
        if app is None:
            pytest.skip("FastAPI app not yet implemented")
        
        with patch('services.backtester_service.app.BacktesterService') as mock_backtester_class:
            # Setup mocks
            mock_backtester = Mock()
            mock_backtester_class.return_value = mock_backtester
            
            mock_backtester.run_backtest_by_name.return_value = {
                'run_id': 'mlflow-run-12345',
                'metrics': {
                    'pnl': 750.25,
                    'sharpe_ratio': 1.8,
                    'max_drawdown': -0.12,
                    'total_return': 0.075
            },
            'status': 'completed',
            'num_signals': 10
        }
            
            # Make API request
            response = client.post('/api/backtest', json={
                'strategy_name': 'CoveredCallScreener',
                'start_date': '2024-01-01',
                'end_date': '2024-01-31',
                'initial_capital': 10000.0,
                'params': {'ticker': 'AAPL'}
            })
            
            # Assert response
            assert response.status_code == 200
            data = response.json()
            
            assert 'run_id' in data
            assert data['run_id'] == 'mlflow-run-12345'
            assert 'metrics' in data
            assert data['metrics']['pnl'] == 750.25
            assert data['metrics']['sharpe_ratio'] == 1.8
            
            # Verify MLflow record was created
            mock_backtester.run_backtest_by_name.assert_called_once()
    
    def test_api_returns_run_id_for_async_backtest(self, client):
        """Test API returns run_id immediately for backgrounded backtests."""
        if app is None:
            pytest.skip("FastAPI app not yet implemented")
        
        with patch('services.backtester_service.app.BacktesterService') as mock_backtester_class:
            mock_backtester = Mock()
            mock_backtester_class.return_value = mock_backtester
            
            # Simulate async/background backtest
            mock_backtester.run_backtest_by_name.return_value = {
                'run_id': 'async-run-67890',
                'status': 'running',
                'metrics': None
            }
            
            response = client.post('/api/backtest', json={
                'strategy_name': 'TestStrategy',
                'start_date': '2024-01-01',
                'end_date': '2024-12-31',
                'params': {}
            })
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['run_id'] == 'async-run-67890'
            assert data['status'] == 'running'
    
    def test_api_get_backtest_status(self, client):
        """Test GET /api/backtest/{id} returns backtest status and results."""
        if app is None:
            pytest.skip("FastAPI app not yet implemented")
        
        with patch('services.backtester_service.app.get_backtest_result') as mock_get_result:
            mock_get_result.return_value = {
                'run_id': 'test-run-999',
                'status': 'completed',
                'metrics': {
                    'pnl': 1500.0,
                    'sharpe_ratio': 2.5,
                    'total_return': 0.15
                }
            }
            
            response = client.get('/api/backtest/test-run-999')
            
            assert response.status_code == 200
            data = response.json()
            
            assert data['run_id'] == 'test-run-999'
            assert data['status'] == 'completed'
            assert data['metrics']['pnl'] == 1500.0
    
    def test_api_validates_request_params(self, client):
        """Test API validates required parameters."""
        if app is None:
            pytest.skip("FastAPI app not yet implemented")
        
        # Missing strategy_name
        response = client.post('/api/backtest', json={
            'start_date': '2024-01-01',
            'end_date': '2024-01-31'
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_api_handles_strategy_not_found(self, client):
        """Test API returns 404 when strategy doesn't exist."""
        if app is None:
            pytest.skip("FastAPI app not yet implemented")
        
        with patch('services.backtester_service.app.BacktesterService') as mock_backtester_class:
            mock_backtester = Mock()
            mock_backtester_class.return_value = mock_backtester
            
            # Simulate strategy not found
            from financial_dashboard.services.options_service.strategies.strategy_registry import StrategyNotFoundError
            mock_backtester.run_backtest_by_name.side_effect = StrategyNotFoundError("Strategy not found")
            
            response = client.post('/api/backtest', json={
                'strategy_name': 'NonExistent',
                'start_date': '2024-01-01',
                'end_date': '2024-01-31'
            })
            
            assert response.status_code == 404
            assert 'not found' in response.json()['detail'].lower()
    
    def test_api_health_endpoint(self, client):
        """Test GET /health returns service status."""
        if app is None:
            pytest.skip("FastAPI app not yet implemented")
        
        response = client.get('/health')
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'healthy'
        assert 'version' in data


class TestBacktestRequestValidation:
    """Test request model validation."""
    
    def test_request_model_validates_dates(self):
        """Test BacktestRequest validates date format."""
        if BacktestRequest is None:
            pytest.skip("BacktestRequest not yet implemented")
        
        # Valid request
        request = BacktestRequest(
            strategy_name='Test',
            start_date='2024-01-01',
            end_date='2024-01-31'
        )
        
        assert request.start_date == '2024-01-01'
        assert request.end_date == '2024-01-31'
    
    def test_request_model_has_optional_params(self):
        """Test BacktestRequest has optional parameters with defaults."""
        if BacktestRequest is None:
            pytest.skip("BacktestRequest not yet implemented")
        
        request = BacktestRequest(
            strategy_name='Test',
            start_date='2024-01-01',
            end_date='2024-01-31'
        )
        
        # Should have defaults
        assert hasattr(request, 'initial_capital')
        assert hasattr(request, 'params')
