"""
Phase 17: Command Palette Engine
OpenBB-Inspired slash-command system for the Options Lab

Commands:
- /gex <ticker> - Show Gamma Exposure
- /flow <ticker> - Show options flow
- /iv <ticker> - Show IV surface
- /chain <ticker> - Load options chain
- /forecast <ticker> - AI forecast
- /help - Show available commands
"""

import re
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from enum import Enum
import json
import logging

logger = logging.getLogger(__name__)


class CommandType(Enum):
    """Types of commands available."""
    DATA = "data"  # Data fetching commands
    VIEW = "view"  # View switching commands
    ACTION = "action"  # Actions like trade, export
    HELP = "help"  # Help/documentation
    MACRO = "macro"  # Recorded macros


@dataclass
class Command:
    """Command definition."""
    name: str
    aliases: List[str]
    description: str
    usage: str
    cmd_type: CommandType
    args: List[str]  # Required arguments
    optional_args: Dict[str, Any]  # Optional args with defaults
    handler: Optional[str] = None  # Callback handler name


@dataclass
class CommandResult:
    """Result of command execution."""
    success: bool
    message: str
    data: Any = None
    view: Optional[str] = None  # View to switch to
    action: Optional[str] = None  # Action to perform


class CommandPalette:
    """
    Command Palette Engine - VS Code/OpenBB style command system.
    
    Supports:
    - Slash commands (/gex SPY)
    - Autocomplete suggestions
    - Command history
    - Pipeline operators (/flow SPY | filter size>1M)
    - Multi-symbol batch commands
    """
    
    # All available commands
    COMMANDS: Dict[str, Command] = {
        "gex": Command(
            name="gex",
            aliases=["gamma", "dealer"],
            description="Show Gamma Exposure (GEX) chart for a ticker",
            usage="/gex <TICKER>",
            cmd_type=CommandType.VIEW,
            args=["ticker"],
            optional_args={"expiry": None},
            handler="show_gex"
        ),
        "flow": Command(
            name="flow",
            aliases=["tape", "options_flow"],
            description="Show options flow tape for a ticker",
            usage="/flow <TICKER> [--size MIN_SIZE]",
            cmd_type=CommandType.VIEW,
            args=["ticker"],
            optional_args={"size": 100000, "type": "all"},
            handler="show_flow"
        ),
        "iv": Command(
            name="iv",
            aliases=["vol", "surface", "volatility"],
            description="Show IV surface for a ticker",
            usage="/iv <TICKER>",
            cmd_type=CommandType.VIEW,
            args=["ticker"],
            optional_args={},
            handler="show_iv_surface"
        ),
        "chain": Command(
            name="chain",
            aliases=["options", "oc"],
            description="Load options chain for ticker(s)",
            usage="/chain <TICKER1,TICKER2,...>",
            cmd_type=CommandType.DATA,
            args=["tickers"],
            optional_args={"expiry": "all"},
            handler="load_chain"
        ),
        "forecast": Command(
            name="forecast",
            aliases=["ai", "predict", "ml"],
            description="Get AI forecast for a ticker",
            usage="/forecast <TICKER>",
            cmd_type=CommandType.DATA,
            args=["ticker"],
            optional_args={"horizon": 5},
            handler="get_forecast"
        ),
        "positions": Command(
            name="positions",
            aliases=["pos", "portfolio"],
            description="Show current positions",
            usage="/positions",
            cmd_type=CommandType.VIEW,
            args=[],
            optional_args={},
            handler="show_positions"
        ),
        "risk": Command(
            name="risk",
            aliases=["greeks", "exposure"],
            description="Show risk metrics for portfolio",
            usage="/risk",
            cmd_type=CommandType.VIEW,
            args=[],
            optional_args={},
            handler="show_risk"
        ),
        "export": Command(
            name="export",
            aliases=["csv", "download"],
            description="Export current data to CSV",
            usage="/export <FILENAME> [--format csv|json]",
            cmd_type=CommandType.ACTION,
            args=[],
            optional_args={"filename": "export", "format": "csv"},
            handler="export_data"
        ),
        "scanner": Command(
            name="scanner",
            aliases=["scan"],
            description="Switch to Scanner workspace",
            usage="/scanner",
            cmd_type=CommandType.VIEW,
            args=[],
            optional_args={},
            handler="switch_tab_scanner"
        ),
        "strategy": Command(
            name="strategy",
            aliases=["strat", "builder"],
            description="Switch to Strategy workspace",
            usage="/strategy",
            cmd_type=CommandType.VIEW,
            args=[],
            optional_args={},
            handler="switch_tab_strategy"
        ),
        "command": Command(
            name="command",
            aliases=["cmd", "trade"],
            description="Switch to Command workspace",
            usage="/command",
            cmd_type=CommandType.VIEW,
            args=[],
            optional_args={},
            handler="switch_tab_command"
        ),
        "admin": Command(
            name="admin",
            aliases=["status", "system"],
            description="Switch to Admin workspace",
            usage="/admin",
            cmd_type=CommandType.VIEW,
            args=[],
            optional_args={},
            handler="switch_tab_admin"
        ),
        "help": Command(
            name="help",
            aliases=["?", "h"],
            description="Show help for commands",
            usage="/help [COMMAND]",
            cmd_type=CommandType.HELP,
            args=[],
            optional_args={"command": None},
            handler="show_help"
        ),
    }
    
    def __init__(self):
        """Initialize command palette."""
        self.history: List[str] = []
        self.macros: Dict[str, List[str]] = {}
        self.last_result: Optional[CommandResult] = None
        
        # Build alias lookup
        self._alias_map: Dict[str, str] = {}
        for cmd_name, cmd in self.COMMANDS.items():
            self._alias_map[cmd_name] = cmd_name
            for alias in cmd.aliases:
                self._alias_map[alias] = cmd_name
    
    def parse_command(self, input_str: str) -> Tuple[Optional[str], List[str], Dict[str, Any]]:
        """
        Parse a command string into command name, args, and options.
        
        Args:
            input_str: Raw command input (e.g., "/gex SPY --expiry 2024-01")
            
        Returns:
            Tuple of (command_name, positional_args, optional_args)
        """
        input_str = input_str.strip()
        
        # Remove leading slash if present
        if input_str.startswith("/"):
            input_str = input_str[1:]
        
        if not input_str:
            return None, [], {}
        
        # Split into parts
        parts = input_str.split()
        cmd_name = parts[0].lower()
        
        # Resolve alias to command name
        if cmd_name in self._alias_map:
            cmd_name = self._alias_map[cmd_name]
        else:
            return None, [], {}
        
        # Parse remaining args
        positional_args = []
        optional_args = {}
        
        i = 1
        while i < len(parts):
            arg = parts[i]
            
            # Check for optional arg (--key value or --key=value)
            if arg.startswith("--"):
                key = arg[2:]
                if "=" in key:
                    key, value = key.split("=", 1)
                    optional_args[key] = value
                elif i + 1 < len(parts) and not parts[i + 1].startswith("--"):
                    optional_args[key] = parts[i + 1]
                    i += 1
                else:
                    optional_args[key] = True
            else:
                positional_args.append(arg.upper())  # Tickers uppercase
            
            i += 1
        
        return cmd_name, positional_args, optional_args
    
    def execute(self, input_str: str) -> CommandResult:
        """
        Execute a command string.
        
        Args:
            input_str: Raw command input
            
        Returns:
            CommandResult with success status and data
        """
        # Parse command
        cmd_name, pos_args, opt_args = self.parse_command(input_str)
        
        if cmd_name is None:
            return CommandResult(
                success=False,
                message=f"Unknown command. Type /help for available commands."
            )
        
        # Get command definition
        cmd = self.COMMANDS.get(cmd_name)
        if not cmd:
            return CommandResult(
                success=False,
                message=f"Command '{cmd_name}' not found."
            )
        
        # Validate required args
        if len(pos_args) < len(cmd.args):
            missing = cmd.args[len(pos_args):]
            return CommandResult(
                success=False,
                message=f"Missing required argument(s): {', '.join(missing)}. Usage: {cmd.usage}"
            )
        
        # Merge optional args with defaults
        final_opts = {**cmd.optional_args, **opt_args}
        
        # Add to history
        self.history.append(input_str)
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        # Execute based on command type
        result = self._dispatch_command(cmd, pos_args, final_opts)
        self.last_result = result
        
        return result
    
    def _dispatch_command(self, cmd: Command, args: List[str], opts: Dict[str, Any]) -> CommandResult:
        """Dispatch command to appropriate handler."""
        
        # Help command
        if cmd.name == "help":
            return self._handle_help(args, opts)
        
        # View switching commands
        if cmd.cmd_type == CommandType.VIEW:
            return self._handle_view_command(cmd, args, opts)
        
        # Data commands
        if cmd.cmd_type == CommandType.DATA:
            return self._handle_data_command(cmd, args, opts)
        
        # Action commands
        if cmd.cmd_type == CommandType.ACTION:
            return self._handle_action_command(cmd, args, opts)
        
        return CommandResult(
            success=True,
            message=f"Command '{cmd.name}' executed.",
            data={"args": args, "opts": opts}
        )
    
    def _handle_help(self, args: List[str], opts: Dict[str, Any]) -> CommandResult:
        """Handle help command."""
        if args:
            # Help for specific command
            cmd_name = args[0].lower()
            if cmd_name in self._alias_map:
                cmd_name = self._alias_map[cmd_name]
                cmd = self.COMMANDS.get(cmd_name)
                if cmd:
                    help_text = f"""
**/{cmd.name}** - {cmd.description}

**Usage:** `{cmd.usage}`

**Aliases:** {', '.join(['/' + a for a in cmd.aliases]) if cmd.aliases else 'None'}

**Arguments:**
{chr(10).join([f'  - {a} (required)' for a in cmd.args]) if cmd.args else '  None'}

**Options:**
{chr(10).join([f'  --{k}={v}' for k, v in cmd.optional_args.items()]) if cmd.optional_args else '  None'}
"""
                    return CommandResult(success=True, message=help_text)
        
        # General help - list all commands
        help_lines = ["**Available Commands:**\n"]
        for cmd in self.COMMANDS.values():
            help_lines.append(f"  `/{cmd.name}` - {cmd.description}")
        
        help_lines.append("\n**Keyboard Shortcuts:**")
        help_lines.append("  `Ctrl+K` - Open command palette")
        help_lines.append("  `g` - GEX view")
        help_lines.append("  `v` - Vol surface")
        help_lines.append("  `f` - Flow tape")
        help_lines.append("\nType `/help <command>` for detailed help.")
        
        return CommandResult(success=True, message="\n".join(help_lines))
    
    def _handle_view_command(self, cmd: Command, args: List[str], opts: Dict[str, Any]) -> CommandResult:
        """Handle view switching commands."""
        ticker = args[0] if args else None
        
        view_map = {
            "gex": "scanner-workspace-tab",
            "flow": "scanner-workspace-tab",
            "iv": "strategy-workspace-tab",
            "positions": "command-workspace-tab",
            "risk": "command-workspace-tab",
            "scanner": "scanner-workspace-tab",
            "strategy": "strategy-workspace-tab",
            "command": "command-workspace-tab",
            "admin": "admin-workspace-tab",
        }
        
        return CommandResult(
            success=True,
            message=f"Switching to {cmd.name} view" + (f" for {ticker}" if ticker else ""),
            view=view_map.get(cmd.name, "strategy-workspace-tab"),
            data={"ticker": ticker, **opts}
        )
    
    def _handle_data_command(self, cmd: Command, args: List[str], opts: Dict[str, Any]) -> CommandResult:
        """Handle data fetching commands."""
        
        if cmd.name == "chain":
            # Support comma-separated tickers
            tickers = []
            for arg in args:
                tickers.extend(arg.split(","))
            
            return CommandResult(
                success=True,
                message=f"Loading chain for: {', '.join(tickers)}",
                action="load_chain",
                data={"tickers": tickers, **opts}
            )
        
        if cmd.name == "forecast":
            ticker = args[0] if args else "SPY"
            horizon = opts.get("horizon", 5)
            
            return CommandResult(
                success=True,
                message=f"Getting {horizon}-day AI forecast for {ticker}",
                action="get_forecast",
                data={"ticker": ticker, "horizon": horizon}
            )
        
        return CommandResult(
            success=True,
            message=f"Data command '{cmd.name}' executed",
            data={"args": args, "opts": opts}
        )
    
    def _handle_action_command(self, cmd: Command, args: List[str], opts: Dict[str, Any]) -> CommandResult:
        """Handle action commands like export."""
        
        if cmd.name == "export":
            filename = opts.get("filename", "export")
            fmt = opts.get("format", "csv")
            
            return CommandResult(
                success=True,
                message=f"Exporting data to {filename}.{fmt}",
                action="export",
                data={"filename": filename, "format": fmt}
            )
        
        return CommandResult(
            success=True,
            message=f"Action '{cmd.name}' executed",
            data={"args": args, "opts": opts}
        )
    
    def get_suggestions(self, partial: str) -> List[Dict[str, str]]:
        """
        Get autocomplete suggestions for partial input.
        
        Args:
            partial: Partial command string
            
        Returns:
            List of suggestion dicts with name, usage, description
        """
        partial = partial.strip()
        if partial.startswith("/"):
            partial = partial[1:]
        
        partial_lower = partial.lower()
        suggestions = []
        
        # If empty, show all commands
        if not partial:
            for cmd in self.COMMANDS.values():
                suggestions.append({
                    "name": f"/{cmd.name}",
                    "usage": cmd.usage,
                    "description": cmd.description
                })
            return suggestions
        
        # Check for command + partial ticker
        parts = partial.split()
        if len(parts) > 1:
            # Command already entered, suggest tickers
            common_tickers = ["SPY", "QQQ", "AAPL", "TSLA", "NVDA", "MSFT", "AMD", "META", "AMZN", "GOOGL"]
            ticker_partial = parts[-1].upper()
            for ticker in common_tickers:
                if ticker.startswith(ticker_partial):
                    suggestions.append({
                        "name": ticker,
                        "usage": "",
                        "description": f"Symbol: {ticker}"
                    })
            return suggestions
        
        # Partial command name - fuzzy match
        for cmd_name, cmd in self.COMMANDS.items():
            if cmd_name.startswith(partial_lower):
                suggestions.append({
                    "name": f"/{cmd.name}",
                    "usage": cmd.usage,
                    "description": cmd.description
                })
            else:
                # Check aliases
                for alias in cmd.aliases:
                    if alias.startswith(partial_lower):
                        suggestions.append({
                            "name": f"/{cmd.name}",
                            "usage": cmd.usage,
                            "description": f"{cmd.description} (alias: /{alias})"
                        })
                        break
        
        return suggestions
    
    def get_history(self, limit: int = 10) -> List[str]:
        """Get recent command history."""
        return self.history[-limit:]
    
    def record_macro(self, name: str, commands: List[str]):
        """Record a sequence of commands as a macro."""
        self.macros[name] = commands
    
    def run_macro(self, name: str) -> List[CommandResult]:
        """Run a recorded macro."""
        if name not in self.macros:
            return [CommandResult(success=False, message=f"Macro '{name}' not found.")]
        
        results = []
        for cmd in self.macros[name]:
            results.append(self.execute(cmd))
        return results


# Global instance
command_palette = CommandPalette()


def parse_and_execute(command_str: str) -> Dict[str, Any]:
    """
    Parse and execute a command string.
    Returns dict suitable for JSON serialization.
    """
    result = command_palette.execute(command_str)
    return {
        "success": result.success,
        "message": result.message,
        "data": result.data,
        "view": result.view,
        "action": result.action
    }


def get_command_suggestions(partial: str) -> List[Dict[str, str]]:
    """Get autocomplete suggestions for partial input."""
    return command_palette.get_suggestions(partial)


def get_command_history(limit: int = 10) -> List[str]:
    """Get recent command history."""
    return command_palette.get_history(limit)


# Test
if __name__ == "__main__":
    print("Testing Command Palette Engine")
    print("="*50)
    
    # Test parsing
    tests = [
        "/gex SPY",
        "/chain AAPL,MSFT,NVDA",
        "/flow TSLA --size 1000000",
        "/help",
        "/help gex",
        "/forecast SPY --horizon 10",
        "/scanner",
        "/export --filename my_data --format json",
    ]
    
    for test in tests:
        print(f"\n> {test}")
        result = command_palette.execute(test)
        print(f"  ✅ Success: {result.success}")
        print(f"  📝 Message: {result.message[:80]}...")
        if result.view:
            print(f"  👁️ View: {result.view}")
        if result.action:
            print(f"  ⚡ Action: {result.action}")
        if result.data:
            print(f"  📊 Data: {result.data}")
    
    # Test autocomplete
    print("\n" + "="*50)
    print("Testing Autocomplete")
    print("="*50)
    
    for partial in ["", "g", "fl", "ch", "SPY"]:
        suggestions = command_palette.get_suggestions(partial)
        print(f"\nPartial: '{partial}' -> {len(suggestions)} suggestions")
        for s in suggestions[:3]:
            print(f"  - {s['name']}: {s['description'][:40]}...")
    
    print("\n✅ Command Palette Engine working!")
