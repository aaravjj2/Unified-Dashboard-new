# Options Bots Tab
# Automated options trading bots - OptionsAlpha style
"""
Options Bots Tab Package
========================
A dedicated tab for automated options trading bots.
Fully automated, no Python scripts required.
"""

from .layout import create_options_bots_layout
from .callbacks import register_options_bots_callbacks

# CRITICAL: Tab loader looks for `create_layout` (preferred for package modules)
def create_layout():
    """Return the options bots layout - used by tab loader."""
    return create_options_bots_layout()

# Also provide get_layout for compatibility
def get_layout():
    """Return the options bots layout."""
    return create_options_bots_layout()

def register_callbacks(app, shared=None):
    """Register callbacks for the options bots tab."""
    register_options_bots_callbacks(app)

# Note: `layout` is a function (callable) so the tab loader can call it
def layout():
    """Return the options bots layout - callable for tab loader."""
    return create_options_bots_layout()

__all__ = [
    'create_options_bots_layout',
    'register_options_bots_callbacks',
    'create_layout',
    'get_layout',
    'register_callbacks',
    'layout',
]
