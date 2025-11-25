"""
Options Lab Module - Canonical Phase 31 Validation

6 canonical subtabs:
1. Chain Viewer
2. Greeks Calculator
3. IV Surface & Forecast
4. Manual Trade / Paper Orders
5. Backtester / Strategy
6. Settings

All controls follow STABLE ID RULE (ol-* prefix).
Safe layout factory pattern with error boundaries.

Author: Phase 31 - Agent 1A
Status: Canonical
"""

from .layout import create_layout
from .callbacks import register_callbacks

# Backward compatibility alias for index.py
layout = create_layout

__all__ = ['create_layout', 'layout', 'register_callbacks']
