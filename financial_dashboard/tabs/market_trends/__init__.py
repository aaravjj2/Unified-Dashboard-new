"""
Market Trends Package - Phase 1 Integration

Contains OpenBB macro data loader and UI components.
"""

from .macro_loader import (
    MacroDataLoader,
    SUPPORTED_INDICATORS,
    get_macro_data
)

__all__ = [
    'MacroDataLoader',
    'SUPPORTED_INDICATORS',
    'get_macro_data'
]
