"""
Volatility Lab - Modular Package Structure
==========================================

Agent-1A Refactor: Breaking monolithic volatility_lab_compact.py into modular components.

Package Structure:
- __init__.py (this file): Package initialization and exports
- layout.py: UI component definitions (panels, cards, controls)
- callbacks.py: Dash callback wiring (6 callbacks from original)
- components.py: Reusable UI building blocks (cards, tables, charts)

Migration from volatility_lab_compact.py:
- Original: 561 lines monolithic file
- New: 4-file modular package with clear separation of concerns

Owner: Agent-1A
Status: Scaffold Complete
"""

from .layout import layout
from .callbacks import register_callbacks

__all__ = ['layout', 'register_callbacks']

# Package metadata
__version__ = '2.0.0'
__author__ = 'Agent-1A'
__description__ = 'Modular Volatility Lab with job queue and admin diagnostics'
