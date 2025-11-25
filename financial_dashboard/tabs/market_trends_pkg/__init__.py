"""Market Trends package (Agent-2A migration scaffold)

This package is a migration scaffold: it provides a pure `create_layout()`
implementation (lazy) and helper modules. It does NOT register callbacks nor
modify existing callback files. To adopt this package, Agent-1A can update the
app's tab loader to import `financial_dashboard.tabs.market_trends_pkg.create_layout`
in place of the old module.
"""
from .layout import create_layout
from .components import build_brief_card
from .data import load_cached_briefs

__all__ = ["create_layout", "build_brief_card", "load_cached_briefs"]
