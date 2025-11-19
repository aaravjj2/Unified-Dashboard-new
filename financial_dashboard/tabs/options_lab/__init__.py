"""
Options Lab Module - Production-Ready Options Analytics

A comprehensive options trading analytics platform with:
- Live options chain viewer
- Greeks dashboard with real-time calculations
- 3D volatility surface visualization  
- Trade simulator for strategy testing

Architecture:
- Modular design with separation of concerns
- Data loader for yfinance integration
- Independent callbacks for each subtab
- Graceful error handling and loading states

Author: Phase 0.8 Expansion - Agent 1B
Status: Integration-Ready
"""

from .layout import layout
from .callbacks import register_callbacks

__all__ = ['layout', 'register_callbacks']
