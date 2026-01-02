"""
Dash Pages Module.
"""

from .system_status import create_system_status_layout, register_system_status_callbacks

__all__ = [
    'create_system_status_layout',
    'register_system_status_callbacks',
]
