"""
Attribution Analysis Lab Module

Provides comprehensive portfolio attribution analysis with:
- Performance Overview (portfolio vs benchmark)
- Factor Contribution (Fama-French, momentum)
- Sector/Asset Class Analysis
- Residual/Specific Attribution

Architecture:
- Modular subtab design
- Isolated callbacks per subtab
- Real portfolio data integration
- Deterministic computations
"""

from .layout import layout
from .callbacks import register_callbacks

__all__ = ['layout', 'register_callbacks']
