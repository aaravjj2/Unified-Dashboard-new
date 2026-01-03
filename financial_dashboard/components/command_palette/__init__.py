"""
Phase 17: Command Palette Module
"""

from .command_engine import (
    CommandPalette,
    command_palette,
    parse_and_execute,
    get_command_suggestions,
    get_command_history,
)

from .command_ui import (
    create_command_palette,
    register_command_palette_callbacks,
    get_all_commands,
    filter_commands,
)

__all__ = [
    'CommandPalette',
    'command_palette',
    'parse_and_execute',
    'get_command_suggestions',
    'get_command_history',
    'create_command_palette',
    'register_command_palette_callbacks',
    'get_all_commands',
    'filter_commands',
]
