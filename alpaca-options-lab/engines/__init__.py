"""Lightweight engines package for standalone lab (stubs).

This package provides minimal implementations for the runtime to import
so the standalone `alpaca-options-lab` can start without the full engine
dependencies. These are intentionally simple and return deterministic
example data for UI use and E2E tests.
"""

__all__ = [
    "ml",
    "execution",
    "risk",
    "monitor",
]
import os
"""
Shim package to expose local engines under the name `engines`.
This redirects imports like `engines.backtest` to `alpaca-options-lab/src/engines/backtest`.
"""
HERE = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.dirname(HERE)
SRC_ENGINES = os.path.join(APP_ROOT, 'src', 'engines')
if os.path.isdir(SRC_ENGINES):
    __path__.insert(0, SRC_ENGINES)
