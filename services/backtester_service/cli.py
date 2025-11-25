"""
Backtester Service Command-Line Interface

CLI for running ad-hoc backtests from the command line.

Usage:
    python -m services.backtester_service.cli run --strategy CoveredCallScreener \\
        --start 2024-01-01 --end 2024-12-31 --params '{"ticker": "AAPL"}'
"""

import argparse
import sys
import json
from datetime import datetime

from backtester_service.backtester import BacktesterService
from financial_dashboard.services.options_service.strategies.strategy_registry import (
    StrategyRegistry,
    StrategyNotFoundError
)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run strategy backtests from the command line"
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Run command
    run_parser = subparsers.add_parser('run', help='Run a backtest')
    run_parser.add_argument(
        '--strategy',
        required=True,
        help='Name of strategy to backtest'
    )
    run_parser.add_argument(
        '--start',
        required=True,
        help='Start date (YYYY-MM-DD)'
    )
    run_parser.add_argument(
        '--end',
        required=True,
        help='End date (YYYY-MM-DD)'
    )
    run_parser.add_argument(
        '--initial-capital',
        type=float,
        default=10000.0,
        help='Initial capital (default: 10000.0)'
    )
    run_parser.add_argument(
        '--params',
        type=str,
        default='{}',
        help='Strategy parameters as JSON string'
    )
    run_parser.add_argument(
        '--mlflow-experiment',
        type=str,
        default='backtester-cli',
        help='MLflow experiment name'
    )
    run_parser.add_argument(
        '--no-mlflow',
        action='store_true',
        help='Disable MLflow tracking'
    )
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available strategies')
    
    return parser.parse_args()


def list_strategies():
    """List all available strategies."""
    registry = StrategyRegistry.get_instance()
    strategies = registry.list_strategies()
    
    print(f"\n Available Strategies ({len(strategies)}):")
    print("=" * 60)
    
    for strategy_name in strategies:
        try:
            metadata = registry.get_strategy_metadata(strategy_name)
            print(f"\n  {metadata['name']}")
            print(f"    Module: {metadata['module']}")
            if metadata.get('docstring'):
                # Print first line of docstring
                first_line = metadata['docstring'].strip().split('\n')[0]
                print(f"    {first_line}")
        except Exception as e:
            print(f"\n  {strategy_name}")
            print(f"    (Error loading metadata: {e})")
    
    print("\n" + "=" * 60)
    print()


def run_backtest(args):
    """Run a backtest with the given arguments."""
    try:
        # Parse strategy params
        try:
            strategy_params = json.loads(args.params)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --params: {e}", file=sys.stderr)
            return 1
        
        # Verify strategy exists
        registry = StrategyRegistry.get_instance()
        try:
            registry.get_strategy(args.strategy)
        except StrategyNotFoundError:
            print(f"Error: Strategy '{args.strategy}' not found", file=sys.stderr)
            print(f"\nAvailable strategies:", file=sys.stderr)
            for name in registry.list_strategies():
                print(f"  - {name}", file=sys.stderr)
            return 1
        
        # Initialize backtester
        backtester = BacktesterService(
            price_client=None,  # TODO: Inject real PriceClient
            mlflow_tracking=not args.no_mlflow,
            mlflow_experiment=args.mlflow_experiment
        )
        
        print(f"\n Running Backtest")
        print("=" * 60)
        print(f"  Strategy: {args.strategy}")
        print(f"  Period: {args.start} to {args.end}")
        print(f"  Capital: ${args.initial_capital:,.2f}")
        print(f"  Params: {json.dumps(strategy_params, indent=4)}")
        print("=" * 60)
        print()
        
        # Run backtest
        result = backtester.run_backtest_by_name(
            strategy_name=args.strategy,
            start_date=args.start,
            end_date=args.end,
            initial_capital=args.initial_capital,
            strategy_params=strategy_params
        )
        
        # Display results
        print(f"\n Backtest Results")
        print("=" * 60)
        print(f"  Run ID: {result['run_id']}")
        print(f"  Status: {result.get('status', 'completed')}")
        print(f"  Signals Generated: {result.get('num_signals', 0)}")
        print()
        print("  Metrics:")
        
        metrics = result.get('metrics', {})
        for metric_name, metric_value in metrics.items():
            if isinstance(metric_value, float):
                if 'return' in metric_name.lower():
                    print(f"    {metric_name}: {metric_value*100:.2f}%")
                else:
                    print(f"    {metric_name}: {metric_value:.4f}")
            else:
                print(f"    {metric_name}: {metric_value}")
        
        print("=" * 60)
        print()
        
        if not args.no_mlflow:
            print(f"  MLflow run logged to experiment: {args.mlflow_experiment}")
            print(f"  View in MLflow UI: http://localhost:5000/#/experiments")
            print()
        
        return 0
        
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error running backtest: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


def main():
    """Main CLI entry point."""
    args = parse_args()
    
    if args.command is None:
        print("Error: No command specified. Use --help for usage.", file=sys.stderr)
        sys.exit(1)
    
    if args.command == 'list':
        list_strategies()
        sys.exit(0)
    elif args.command == 'run':
        exit_code = run_backtest(args)
        sys.exit(exit_code)
    else:
        print(f"Error: Unknown command: {args.command}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
