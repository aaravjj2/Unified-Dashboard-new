"""
Research Lab Tab Package

Provides research brief management with integrated analysis tools.
Imports from individual modules:
- layout: UI layout construction
- callbacks: Interactive behavior
- components: Reusable UI components
"""

from .layout import create_layout as layout
from .callbacks import register_callbacks

__all__ = ['layout', 'register_callbacks']
