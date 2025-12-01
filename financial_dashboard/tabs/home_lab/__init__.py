"""
Home Lab - Command Center & Dashboard Overview

Provides system-level insights, portfolio snapshots, cross-lab performance summaries,
and user guidance for the entire financial analytics suite.
"""

import logging

logger = logging.getLogger(__name__)

# Module-level app reference (set by index.py after initialization)
app = None

# Import layout function (deferred to avoid circular imports)
def get_layout():
    """Get the layout function for Home Lab"""
    from .layout import layout as home_layout
    return home_layout

# Expose layout directly for index.py tab loading
from .layout import layout

logger.info("✓ Home Lab module initialized")
