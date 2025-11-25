"""
Command Center Package - Central mission control dashboard
Provides skeleton layout with lazy-loaded widgets and diagnostic tools.
"""

from .layout import create_layout
from .callbacks import register_callbacks

__all__ = ['create_layout', 'register_callbacks']
