"""
Quality Tests Module - Phase 4
==============================
Contains golden vector tests and math verification.
"""

from .golden_vectors import (
    run_startup_checks,
    run_startup_checks_safe,
    validate_before_startup,
    get_math_integrity_status,
    black_scholes_call,
    black_scholes_put,
)

__all__ = [
    'run_startup_checks',
    'run_startup_checks_safe',
    'validate_before_startup',
    'get_math_integrity_status',
    'black_scholes_call',
    'black_scholes_put',
]

