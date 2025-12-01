"""
TDD RED Phase: CLI Tests

Tests for command-line interface.
These will fail initially as cli.py doesn't exist yet.
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock
from io import StringIO

# These imports will fail initially - expected for RED phase
try:
    from services.backtester_service import cli
except ImportError:
    cli = None


class TestBacktesterCLI:
    """Test command-line interface functionality."""
    
    def test_backtester_cli_fails_without_strategy(self):
        """CLI should return non-zero exit code when strategy not found."""
        if cli is None:
            pytest.skip("CLI module not yet implemented")
        
        # Mock sys.argv
        test_args = [
            'cli.py', 'run',
            '--strategy', 'NonExistentStrategy',
            '--start', '2024-01-01',
            '--end', '2024-01-31'
        ]
        
        with patch('sys.argv', test_args):
            with patch('services.backtester_service.cli.StrategyRegistry') as mock_registry_class:
                mock_registry = Mock()
                mock_registry_class.get_instance.return_value = mock_registry
                
                # Simulate strategy not found
                from financial_dashboard.services.options_service.strategies.strategy_registry import StrategyNotFoundError
                mock_registry.get_strategy.side_effect = StrategyNotFoundError("Strategy not found")
                
                # CLI should exit with non-zero
                with pytest.raises(SystemExit) as exc_info:
                    cli.main()
                
                assert exc_info.value.code != 0, "CLI should exit with error code when strategy not found"
    
    def test_backtester_cli_runs_successfully(self):
        """CLI should successfully run backtest when all params are valid."""
        if cli is None:
            pytest.skip("CLI module not yet implemented")
        
        test_args = [
            'cli.py', 'run',
            '--strategy', 'CoveredCallScreener',
            '--start', '2024-01-01',
            '--end', '2024-01-31',
            '--params', '{"ticker": "AAPL"}'
        ]
        
        with patch('sys.argv', test_args):
            with patch('services.backtester_service.cli.BacktesterService') as mock_backtester_class:
                with patch('services.backtester_service.cli.StrategyRegistry') as mock_registry_class:
                    mock_registry = Mock()
                    mock_registry_class.get_instance.return_value = mock_registry
                    mock_registry.get_strategy.return_value = Mock()  # Strategy exists
                    
                    mock_backtester = Mock()
                    mock_backtester_class.return_value = mock_backtester
                    
                    # Mock successful backtest
                    mock_backtester.run_backtest_by_name.return_value = {
                        'run_id': 'test-run-123',
                        'status': 'completed',
                        'metrics': {
                            'pnl': 500.0,
                            'sharpe_ratio': 1.5,
                            'total_return': 0.05
                        }
                    }
                    
                    # Should exit with 0
                    with pytest.raises(SystemExit) as exc_info:
                        cli.main()
                    
                    assert exc_info.value.code == 0, "CLI should exit successfully with valid params"
    
    def test_backtester_cli_accepts_all_parameters(self):
        """CLI should accept and pass all parameters correctly."""
        if cli is None:
            pytest.skip("CLI module not yet implemented")
        
        test_args = [
            'cli.py', 'run',
            '--strategy', 'TestStrategy',
            '--start', '2024-01-01',
            '--end', '2024-01-31',
            '--initial-capital', '50000',
            '--params', '{"ticker": "MSFT", "threshold": 0.7}',
            '--mlflow-experiment', 'custom-experiment'
        ]
        
        with patch('sys.argv', test_args):
            with patch('services.backtester_service.cli.BacktesterService') as mock_backtester_class:
                with patch('services.backtester_service.cli.StrategyRegistry') as mock_registry_class:
                    mock_registry = Mock()
                    mock_registry_class.get_instance.return_value = mock_registry
                    mock_registry.get_strategy.return_value = Mock()  # Strategy exists
                    
                    mock_backtester = Mock()
                    mock_backtester_class.return_value = mock_backtester
                    mock_backtester.run_backtest_by_name.return_value = {
                        'run_id': 'test-run-456',
                        'status': 'completed',
                        'metrics': {}
                    }
                    
                    try:
                        cli.main()
                    except SystemExit:
                        pass
                    
                    # Verify parameters were passed correctly
                    mock_backtester.run_backtest_by_name.assert_called_once()
                    call_kwargs = mock_backtester.run_backtest_by_name.call_args[1]
                    
                    assert call_kwargs['strategy_name'] == 'TestStrategy'
                    assert call_kwargs['start_date'] == '2024-01-01'
                    assert call_kwargs['end_date'] == '2024-01-31'
                    assert call_kwargs['initial_capital'] == 50000.0
                    assert call_kwargs['strategy_params']['ticker'] == 'MSFT'

    
    def test_backtester_cli_outputs_results(self):
        """CLI should output backtest results to stdout."""
        if cli is None:
            pytest.skip("CLI module not yet implemented")
        
        test_args = [
            'cli.py', 'run',
            '--strategy', 'TestStrategy',
            '--start', '2024-01-01',
            '--end', '2024-01-31'
        ]
        
        with patch('sys.argv', test_args):
            with patch('services.backtester_service.cli.BacktesterService') as mock_backtester_class:
                with patch('services.backtester_service.cli.StrategyRegistry') as mock_registry_class:
                    mock_registry = Mock()
                    mock_registry_class.get_instance.return_value = mock_registry
                    mock_registry.get_strategy.return_value = Mock()  # Strategy exists
                    
                    mock_backtester = Mock()
                    mock_backtester_class.return_value = mock_backtester
                    mock_backtester.run_backtest_by_name.return_value = {
                        'run_id': 'test-run-789',
                        'status': 'completed',
                        'metrics': {
                            'pnl': 1250.50,
                            'sharpe_ratio': 2.1,
                            'total_return': 0.125
                        }
                    }
                    
                    # Capture stdout
                    captured_output = StringIO()
                    with patch('sys.stdout', captured_output):
                        try:
                            cli.main()
                        except SystemExit:
                            pass
                    
                    output = captured_output.getvalue()
                    
                    # Should display metrics
                    assert 'pnl' in output.lower() or '1250' in output
                    assert 'run_id' in output.lower() or 'test-run-789' in output
