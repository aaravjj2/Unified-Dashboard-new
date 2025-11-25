"""
Unit Tests for IV Solver - Deterministic Fixtures
==================================================

Phase 34 test suite for IV solver validation.
"""

import pytest
import numpy as np
from financial_dashboard.solvers.iv_solver import (
    calculate_iv,
    validate_iv_grid,
    black_scholes_price,
    IV_MIN,
    IV_MAX
)


# Deterministic fixtures
@pytest.fixture
def valid_grid_5x5():
    """Minimum valid grid - 5x5 with reasonable IVs."""
    return [
        [0.18, 0.17, 0.16, 0.15, 0.16],
        [0.19, 0.18, 0.17, 0.16, 0.17],
        [0.20, 0.19, 0.18, 0.17, 0.18],
        [0.21, 0.20, 0.19, 0.18, 0.19],
        [0.22, 0.21, 0.20, 0.19, 0.20]
    ]


@pytest.fixture
def invalid_grid_with_nans():
    """Grid with NaN values - should fail validation."""
    return [
        [0.18, np.nan, 0.16, 0.15, 0.16],
        [0.19, 0.18, 0.17, np.nan, 0.17],
        [0.20, 0.19, 0.18, 0.17, 0.18],
        [0.21, 0.20, 0.19, 0.18, 0.19],
        [0.22, 0.21, 0.20, 0.19, 0.20]
    ]


# Test Black-Scholes pricing
def test_black_scholes_atm_call():
    """Test BS price for ATM call."""
    price = black_scholes_price(S=100, K=100, T=1, r=0.05, sigma=0.2, option_type='call')
    assert 5 < price < 15  # Reasonable range for ATM call


def test_black_scholes_deep_itm_call():
    """Test BS price for deep ITM call."""
    price = black_scholes_price(S=120, K=100, T=1, r=0.05, sigma=0.2, option_type='call')
    assert price > 20  # Should be at least intrinsic value


# Test IV calculation
def test_calculate_iv_converges():
    """Test IV solver converges for standard case."""
    target_price = black_scholes_price(100, 100, 1, 0.05, 0.25)
    result = calculate_iv(target_price, 100, 100, 1, 0.05)
    
    assert result['converged']
    assert abs(result['iv'] - 0.25) < 0.001  # Should recover original vol
    assert result['method'] == 'newton-raphson'


def test_calculate_iv_bounds_check():
    """Test IV stays within bounds."""
    result = calculate_iv(50, 100, 100, 1, 0.05)  # Unrealistic price
    
    assert IV_MIN <= result['iv'] <= IV_MAX


# Test grid validation
def test_validate_grid_accepts_valid(valid_grid_5x5):
    """Test validator accepts valid 5x5 grid."""
    validation = validate_iv_grid(valid_grid_5x5)
    
    assert validation['valid']
    assert len(validation['errors']) == 0


def test_validate_grid_rejects_nans(invalid_grid_with_nans):
    """Test validator rejects grid with NaNs."""
    validation = validate_iv_grid(invalid_grid_with_nans)
    
    assert not validation['valid']
    assert any('NaN' in err for err in validation['errors'])


def test_validate_grid_rejects_small():
    """Test validator rejects grid smaller than 5x5."""
    small_grid = [[0.2, 0.2], [0.2, 0.2]]
    validation = validate_iv_grid(small_grid)
    
    assert not validation['valid']
    assert any('shape' in err.lower() for err in validation['errors'])


def test_validate_grid_warns_out_of_bounds():
    """Test validator warns for out-of-bounds values."""
    grid = [[5.0] * 5 for _ in range(5)]  # All values above IV_MAX
    validation = validate_iv_grid(grid)
    
    assert len(validation['warnings']) > 0
    assert any('bounds' in warn.lower() for warn in validation['warnings'])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
