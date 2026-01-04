"""
Conftest for comprehensive test suite
"""
import pytest
import sys
import os

# Ensure the src directory is in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'src'))


@pytest.fixture(scope="session")
def test_config():
    """Provide test configuration"""
    return {
        "initial_capital": 100000.0,
        "risk_free_rate": 0.05,
        "default_volatility": 0.25,
    }
