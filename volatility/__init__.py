"""
Volatility Solver Module

Provides implied volatility calculation and surface generation.
"""

__version__ = "1.0.0"
__author__ = "Agent-1B"

from .solver import (
    compute_surface_grid,
    solve_iv,
    newton_raphson_iv,
    brent_fallback_iv,
    black_scholes_call,
    vega
)

__all__ = [
    'compute_surface_grid',
    'solve_iv',
    'newton_raphson_iv',
    'brent_fallback_iv',
    'black_scholes_call',
    'vega'
]
