"""
Volatility Lab Package - Phase 34 Complete Rebuild
====================================================

Owner: Agent-1A
Phase: 34 (Full Rebuild with Headed Playwright Validation)

Package Structure:
- __init__.py: Package initialization, exports create_layout() and register_callbacks()
- layout.py: UI component definitions with canonical subtabs
- components.py: Reusable UI building blocks
- callbacks.py: Dash callback wiring  
- data.py: Lazy-loaded data connectors (options, prices)

Canonical Subtabs:
- IV Surface (id: vl-iv-tab)
- Surface Explorer & History (id: vl-explorer-tab)
- Signals & Strategy Ideas (id: vl-signals-tab)
- Quick Backtest & Replay (id: vl-backtest-tab)

Stable ID Rule:
All interactive controls use `vl-*` prefix for consistent testing.

API Integration:
- POST /api/volsurface/compute
- GET /api/volsurface/latest  
- GET /api/volsurface/history
- POST /api/volsurface/signal
- POST /api/volsurface/backtest

Deterministic Mode:
Set VOLLAB_DETERMINISTIC=1 to use fixtures for testing.
"""

from .layout import create_layout
from .callbacks import register_callbacks

__all__ = ['create_layout', 'register_callbacks']

__version__ = '3.0.0'
__author__ = 'Agent-1A'
__description__ = 'Phase 34 Complete Rebuild with Headed Playwright Validation'
