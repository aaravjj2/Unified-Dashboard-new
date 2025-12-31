"""
Dashboard Layouts Package
Phase 15 - Agent-UX

Contains consolidated workspace layouts for the Alpaca Options Dashboard.
"""

from .workspaces import (
    scanner_layout,
    strategy_layout,
    command_layout,
    admin_layout,
    create_pattern_feed,
)

__all__ = [
    "scanner_layout",
    "strategy_layout",
    "command_layout",
    "admin_layout",
    "create_pattern_feed",
]
