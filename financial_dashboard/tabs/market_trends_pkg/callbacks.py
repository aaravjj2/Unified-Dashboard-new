"""Migration shim for Market Trends callbacks.

This module is intentionally a placeholder: it does NOT register callbacks nor
modify existing callback decorators. It is provided as a landing place so that
Agent-1A can gradually refactor callback definitions to import data from
`market_trends_pkg.data`. Do NOT wire this automatically.
"""
import logging
logger = logging.getLogger(__name__)


def register_callbacks(app):
    logger.info('market_trends_pkg.register_callbacks called - shim (no-op).')
    # TODO for Agent-1A: Move existing callback definitions from
    # `financial_dashboard/tabs/market_trends.py` into this file, updating
    # imports to `from .data import ...` and `from .components import ...`.
    # DO NOT change callback decorators during merge without coordination.
    return
