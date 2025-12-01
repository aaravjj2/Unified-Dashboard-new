"""
Strategy Lab Module

Provides comprehensive quantitative trading strategy development and testing:
- Strategy Definition (rule-based, factor-driven)
- Backtesting Engine (historical simulation)
- Performance Analytics (CAGR, Sharpe, Drawdown)
- Risk Attribution (factor decomposition)
- Visualization (equity curves, exposure breakdowns)

Architecture:
- Modular subtab design
- Isolated callbacks per component
- Mock data support with Azure ML placeholder
- No circular imports (app = None at module level)
- Full isolation (if Strategy Lab fails, other tabs unaffected)

Phase 1: Core Architecture & Layout Integration
Phase 2: Functional Prototype (mock backtesting)
Phase 3: Validation & Diagnostics
Phase 4: Documentation & Azure prep
Phase 18B: Merged Backtest Config into Execute tab (5 subtabs instead of 6)
"""

from .layout_modular import layout  # Using modular layout with merged Execute & Configure tab
from .callbacks import register_callbacks

# Module-level app/server references - NEVER INITIALIZED HERE
# All callbacks registered via register_callbacks(app) function
app = None
server = None

__all__ = ['layout', 'register_callbacks']
