"""
Pytest configuration and fixtures for the test suite
"""
import pytest
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Create necessary directories for tests
@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """Set up test environment before running tests."""
    test_dirs = [
        'tests/data',
        'tests/outputs',
        'tests/cache',
        'tests/logs'
    ]
    
    for dir_path in test_dirs:
        full_path = PROJECT_ROOT / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
    
    yield
    
    # Cleanup after tests (optional)
    # Can be enabled if needed
    pass

@pytest.fixture
def sample_ticker():
    """Provide a sample ticker for tests."""
    return 'AAPL'

@pytest.fixture
def sample_tickers():
    """Provide sample tickers list for tests."""
    return ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']

@pytest.fixture
def mock_portfolio_value():
    """Provide mock portfolio value."""
    return 100000.0  # $100K

@pytest.fixture
def mock_volatility():
    """Provide mock volatility value."""
    return 0.25  # 25% annualized

@pytest.fixture
def mock_prediction():
    """Provide mock return prediction."""
    return 0.08  # 8% expected return
