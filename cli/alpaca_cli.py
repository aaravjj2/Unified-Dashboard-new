#!/usr/bin/env python3
"""
Alpaca Options Lab CLI
Phase 8 - Operations & DX (Items 581-600)

Command-line interface for:
- Dashboard management (start, stop, status)
- Backtest execution
- Data export
- Environment diagnostics
- Model inspection
"""

import argparse
import sys
import os
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, List

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def print_banner():
    """Print CLI banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║     █████╗ ██╗     ██████╗  █████╗  ██████╗ █████╗           ║
║    ██╔══██╗██║     ██╔══██╗██╔══██╗██╔════╝██╔══██╗          ║
║    ███████║██║     ██████╔╝███████║██║     ███████║          ║
║    ██╔══██║██║     ██╔═══╝ ██╔══██║██║     ██╔══██║          ║
║    ██║  ██║███████╗██║     ██║  ██║╚██████╗██║  ██║          ║
║    ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝          ║
║                                                               ║
║              OPTIONS LAB - Command Line Interface             ║
╚═══════════════════════════════════════════════════════════════╝
    """
    print("\033[93m" + banner + "\033[0m")


def print_success(msg: str):
    """Print success message."""
    print(f"\033[92m✓ {msg}\033[0m")


def print_error(msg: str):
    """Print error message."""
    print(f"\033[91m✗ {msg}\033[0m")


def print_warning(msg: str):
    """Print warning message."""
    print(f"\033[93m⚠ {msg}\033[0m")


def print_info(msg: str):
    """Print info message."""
    print(f"\033[94mℹ {msg}\033[0m")


class AlpacaCLI:
    """Main CLI class."""
    
    def __init__(self):
        self.project_root = PROJECT_ROOT
        
    def cmd_start(self, args):
        """Start the dashboard server."""
        print_info("Starting Alpaca Options Lab...")
        
        port = args.port or 8053
        env = os.environ.copy()
        env["UX_CONSOLIDATED"] = "true"
        
        if args.debug:
            env["DEBUG"] = "true"
            print_warning("Debug mode enabled")
        
        cmd = [sys.executable, "run_alpaca_enhanced_server.py"]
        
        if args.background:
            subprocess.Popen(cmd, cwd=self.project_root, env=env, 
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(2)
            print_success(f"Dashboard started in background on port {port}")
            print_info(f"Open http://localhost:{port} in your browser")
        else:
            print_info(f"Starting dashboard on port {port}...")
            print_info("Press Ctrl+C to stop")
            subprocess.run(cmd, cwd=self.project_root, env=env)
    
    def cmd_stop(self, args):
        """Stop the dashboard server."""
        print_info("Stopping Alpaca Options Lab...")
        
        result = subprocess.run(["pkill", "-f", "run_alpaca_enhanced_server"], 
                               capture_output=True)
        
        if result.returncode == 0:
            print_success("Dashboard stopped")
        else:
            print_warning("No running dashboard found")
    
    def cmd_status(self, args):
        """Check dashboard status."""
        import requests
        
        port = args.port or 8053
        url = f"http://localhost:{port}/api/options/ready"
        
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print_success(f"Dashboard is running on port {port}")
                data = response.json()
                print_info(f"Status: {data.get('status', 'unknown')}")
            else:
                print_warning(f"Dashboard responded with status {response.status_code}")
        except requests.exceptions.ConnectionError:
            print_error(f"Dashboard is not running on port {port}")
        except Exception as e:
            print_error(f"Error checking status: {e}")
    
    def cmd_backtest(self, args):
        """Run a backtest."""
        print_info("Running backtest...")
        
        try:
            from engines.backtesting.options_backtester import (
                quick_backtest, StrategyType, BacktestConfig
            )
            
            strategy = StrategyType(args.strategy) if args.strategy else StrategyType.IRON_CONDOR
            
            result = quick_backtest(
                ticker=args.ticker or "SPY",
                strategy=strategy,
                start_date=args.start or "2023-01-01",
                end_date=args.end or "2024-12-31",
                initial_capital=args.capital or 100000,
            )
            
            print("\n" + "="*50)
            print(f"\033[93mBACKTEST RESULTS: {strategy.value.upper()}\033[0m")
            print("="*50)
            print(f"Total Return:     \033[92m{result.total_return:+.2f}%\033[0m")
            print(f"CAGR:             {result.cagr:+.2f}%")
            print(f"Sharpe Ratio:     {result.sharpe_ratio:.2f}")
            print(f"Sortino Ratio:    {result.sortino_ratio:.2f}")
            print(f"Max Drawdown:     \033[91m{result.max_drawdown:.2f}%\033[0m")
            print(f"Win Rate:         {result.win_rate:.1f}%")
            print(f"Profit Factor:    {result.profit_factor:.2f}")
            print(f"Total Trades:     {result.total_trades}")
            print(f"Avg Days Held:    {result.avg_days_held:.1f}")
            print("="*50)
            
            if args.output:
                output_data = {
                    "strategy": strategy.value,
                    "ticker": args.ticker or "SPY",
                    "start_date": args.start or "2023-01-01",
                    "end_date": args.end or "2024-12-31",
                    "total_return": result.total_return,
                    "cagr": result.cagr,
                    "sharpe_ratio": result.sharpe_ratio,
                    "sortino_ratio": result.sortino_ratio,
                    "max_drawdown": result.max_drawdown,
                    "win_rate": result.win_rate,
                    "profit_factor": result.profit_factor,
                    "total_trades": result.total_trades,
                }
                with open(args.output, "w") as f:
                    json.dump(output_data, f, indent=2)
                print_success(f"Results saved to {args.output}")
                
        except Exception as e:
            print_error(f"Backtest failed: {e}")
    
    def cmd_doctor(self, args):
        """Run environment diagnostics."""
        print_banner()
        print("\n\033[93mENVIRONMENT DIAGNOSTICS\033[0m\n")
        
        checks = []
        
        # Python version
        py_version = sys.version_info
        if py_version >= (3, 10):
            checks.append(("Python Version", f"{py_version.major}.{py_version.minor}.{py_version.micro}", True))
        else:
            checks.append(("Python Version", f"{py_version.major}.{py_version.minor}.{py_version.micro} (3.10+ recommended)", False))
        
        # Required packages
        required_packages = [
            "dash", "plotly", "pandas", "numpy", "dash_bootstrap_components",
            "requests", "scipy", "ta"
        ]
        
        for pkg in required_packages:
            try:
                __import__(pkg.replace("-", "_"))
                checks.append((f"Package: {pkg}", "✓ Installed", True))
            except ImportError:
                checks.append((f"Package: {pkg}", "✗ Missing", False))
        
        # Environment variables
        env_vars = ["ALPACA_API_KEY", "ALPACA_SECRET_KEY"]
        for var in env_vars:
            if os.environ.get(var):
                checks.append((f"Env: {var}", "✓ Set", True))
            else:
                checks.append((f"Env: {var}", "⚠ Not set", None))
        
        # Project structure
        required_dirs = ["financial_dashboard", "engines", "dashboard_layouts"]
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                checks.append((f"Directory: {dir_name}", "✓ Found", True))
            else:
                checks.append((f"Directory: {dir_name}", "✗ Missing", False))
        
        # Print results
        print(f"{'Check':<30} {'Status':<30}")
        print("-" * 60)
        
        passed = 0
        failed = 0
        warnings = 0
        
        for name, status, success in checks:
            if success is True:
                color = "\033[92m"
                passed += 1
            elif success is False:
                color = "\033[91m"
                failed += 1
            else:
                color = "\033[93m"
                warnings += 1
            print(f"{name:<30} {color}{status}\033[0m")
        
        print("-" * 60)
        print(f"\n\033[92m{passed} passed\033[0m, \033[91m{failed} failed\033[0m, \033[93m{warnings} warnings\033[0m")
        
        if failed > 0:
            print_error("\nSome checks failed. Please fix the issues above.")
            return 1
        elif warnings > 0:
            print_warning("\nSome checks have warnings. The app may work with limited functionality.")
            return 0
        else:
            print_success("\nAll checks passed! Environment is ready.")
            return 0
    
    def cmd_export(self, args):
        """Export data."""
        print_info(f"Exporting {args.type} data...")
        
        output_file = args.output or f"alpaca_export_{args.type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{args.format}"
        
        try:
            if args.type == "positions":
                data = {"positions": [], "timestamp": datetime.now().isoformat()}
            elif args.type == "trades":
                data = {"trades": [], "timestamp": datetime.now().isoformat()}
            elif args.type == "config":
                data = {
                    "port": 8053,
                    "theme": "dark",
                    "layout": "trading",
                    "timestamp": datetime.now().isoformat(),
                }
            else:
                print_error(f"Unknown export type: {args.type}")
                return
            
            if args.format == "json":
                with open(output_file, "w") as f:
                    json.dump(data, f, indent=2)
            elif args.format == "csv":
                import csv
                with open(output_file, "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=data.keys())
                    writer.writeheader()
                    writer.writerow(data)
            
            print_success(f"Exported to {output_file}")
            
        except Exception as e:
            print_error(f"Export failed: {e}")
    
    def cmd_logs(self, args):
        """View logs."""
        log_file = self.project_root / "logs" / "alpaca.log"
        
        if not log_file.exists():
            print_warning("No log file found")
            return
        
        lines = args.lines or 50
        
        with open(log_file, "r") as f:
            all_lines = f.readlines()
            for line in all_lines[-lines:]:
                # Color code by level
                if "ERROR" in line:
                    print(f"\033[91m{line}\033[0m", end="")
                elif "WARNING" in line:
                    print(f"\033[93m{line}\033[0m", end="")
                elif "INFO" in line:
                    print(f"\033[94m{line}\033[0m", end="")
                else:
                    print(line, end="")
    
    def cmd_models(self, args):
        """List or inspect models."""
        models_dir = self.project_root / "models"
        
        if args.inspect:
            model_path = models_dir / args.inspect
            if model_path.exists():
                print_info(f"Model: {args.inspect}")
                print(f"Size: {model_path.stat().st_size / 1024:.2f} KB")
                print(f"Modified: {datetime.fromtimestamp(model_path.stat().st_mtime)}")
            else:
                print_error(f"Model not found: {args.inspect}")
        else:
            print_info("Available Models:")
            if models_dir.exists():
                for model_file in models_dir.glob("*.pkl"):
                    size = model_file.stat().st_size / 1024
                    print(f"  • {model_file.name} ({size:.1f} KB)")
                for model_file in models_dir.glob("*.h5"):
                    size = model_file.stat().st_size / 1024
                    print(f"  • {model_file.name} ({size:.1f} KB)")
            else:
                print_warning("Models directory not found")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Alpaca Options Lab CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the dashboard")
    start_parser.add_argument("-p", "--port", type=int, help="Port number (default: 8053)")
    start_parser.add_argument("-b", "--background", action="store_true", help="Run in background")
    start_parser.add_argument("-d", "--debug", action="store_true", help="Enable debug mode")
    
    # Stop command
    subparsers.add_parser("stop", help="Stop the dashboard")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check dashboard status")
    status_parser.add_argument("-p", "--port", type=int, help="Port number (default: 8053)")
    
    # Backtest command
    bt_parser = subparsers.add_parser("backtest", help="Run a backtest")
    bt_parser.add_argument("-s", "--strategy", help="Strategy type (e.g., iron_condor, put_spread)")
    bt_parser.add_argument("-t", "--ticker", help="Ticker symbol (default: SPY)")
    bt_parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
    bt_parser.add_argument("--end", help="End date (YYYY-MM-DD)")
    bt_parser.add_argument("-c", "--capital", type=float, help="Initial capital")
    bt_parser.add_argument("-o", "--output", help="Output file for results")
    
    # Doctor command
    subparsers.add_parser("doctor", help="Run environment diagnostics")
    
    # Export command
    export_parser = subparsers.add_parser("export", help="Export data")
    export_parser.add_argument("type", choices=["positions", "trades", "config"], help="Data type to export")
    export_parser.add_argument("-f", "--format", choices=["json", "csv"], default="json", help="Output format")
    export_parser.add_argument("-o", "--output", help="Output file path")
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="View logs")
    logs_parser.add_argument("-n", "--lines", type=int, help="Number of lines to show")
    
    # Models command
    models_parser = subparsers.add_parser("models", help="List or inspect models")
    models_parser.add_argument("-i", "--inspect", help="Model file to inspect")
    
    args = parser.parse_args()
    
    if not args.command:
        print_banner()
        parser.print_help()
        return
    
    cli = AlpacaCLI()
    
    commands = {
        "start": cli.cmd_start,
        "stop": cli.cmd_stop,
        "status": cli.cmd_status,
        "backtest": cli.cmd_backtest,
        "doctor": cli.cmd_doctor,
        "export": cli.cmd_export,
        "logs": cli.cmd_logs,
        "models": cli.cmd_models,
    }
    
    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
