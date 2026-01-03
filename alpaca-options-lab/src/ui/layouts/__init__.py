"""
Dash Layouts Package
====================
Contains modular UI layouts for the dashboard.

Layouts:
- scanner_workspace: Hybrid Sentiment Scanner with hype gauges and news feed
"""

from .scanner_workspace import create_scanner_layout, register_scanner_callbacks

__all__ = ['create_scanner_layout', 'register_scanner_callbacks']

