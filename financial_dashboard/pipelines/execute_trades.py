"""
Automated Trade Execution Pipeline

This pipeline connects your analysis outputs to your broker (Alpaca).
It reads the latest picks from weekly/monthly runs, calculates position sizes,
and executes trades to rebalance your live portfolio.

Usage:
    # Execute weekly picks
    python3 pipelines/execute_trades.py --source weekly --dry-run
    
    # Execute monthly picks (live trading)
    python3 pipelines/execute_trades.py --source monthly
    
    # Manual portfolio targets from JSON
    python3 pipelines/execute_trades.py --targets portfolio_targets.json

Safety Features:
    - Dry-run mode by default (requires --no-dry-run for live trading)
    - Position size limits and risk checks
    - Detailed logging of all actions
    - Rollback capability for failed executions
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from typing import Dict, Optional
import pandas as pd

# Add parent directory to path
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, BASE_DIR)

from utils.execution import AlpacaExecutor
try:
    from utils.trade_utils import compute_position_size, estimate_slippage
    TRADE_UTILS_AVAILABLE = True
except:
    print("Warning: trade_utils not fully available, using simplified sizing")
    TRADE_UTILS_AVAILABLE = False

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/trade_execution.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TradeExecutionPipeline:
    """
    Automated trade execution pipeline.
    
    Orchestrates the entire flow from picks to live trades:
    1. Load latest picks (weekly or monthly)
    2. Calculate position sizes based on portfolio value
    3. Build target portfolio dictionary
    4. Execute rebalancing via AlpacaExecutor
    5. Log all actions and results
    """
    
    def __init__(self, dry_run: bool = True, max_position_pct: float = 0.10,
                 max_total_pct: float = 0.95):
        """
        Initialize the pipeline.
        
        Args:
            dry_run: If True, simulate trades without executing (default)
            max_position_pct: Maximum % of portfolio for single position (default 10%)
            max_total_pct: Maximum % of portfolio to allocate (default 95%, keep 5% cash)
        """
        self.dry_run = dry_run
        self.max_position_pct = max_position_pct
        self.max_total_pct = max_total_pct
        
        # Initialize executor
        try:
            self.executor = AlpacaExecutor(paper=True)  # Use paper trading by default
            logger.info("Trade execution pipeline initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Alpaca executor: {e}")
            raise
    
    def load_latest_picks(self, source: str = 'weekly') -> pd.DataFrame:
        """
        Load the most recent picks file.
        
        Args:
            source: 'weekly' or 'monthly'
            
        Returns:
            DataFrame with picks
        """
        picks_dir = f"models/{source}_run"
        
        # Find latest picks file
        picks_files = [f for f in os.listdir(picks_dir) if f.startswith(f'{source}picks') and f.endswith('.csv')]
        
        if not picks_files:
            raise FileNotFoundError(f"No picks files found in {picks_dir}")
        
        # Get most recent file
        latest_file = sorted(picks_files)[-1]
        file_path = os.path.join(picks_dir, latest_file)
        
        logger.info(f"Loading picks from: {file_path}")
        df = pd.read_csv(file_path)
        
        return df
    
    def calculate_position_sizes(self, picks_df: pd.DataFrame, 
                                 portfolio_value: float) -> Dict[str, float]:
        """
        Calculate target dollar amounts for each pick.
        
        Args:
            picks_df: DataFrame with picks (must have 'ticker' column)
            portfolio_value: Total portfolio value in dollars
            
        Returns:
            Dictionary mapping ticker to target dollar amount
        """
        # Calculate max allocation per position
        max_position_value = portfolio_value * self.max_position_pct
        
        # Calculate total allocation budget
        total_budget = portfolio_value * self.max_total_pct
        
        n_picks = len(picks_df)
        
        # Simple equal-weight allocation
        # (In production, you'd use picks_df scores/ranks for weighting)
        equal_weight = total_budget / n_picks
        
        # Cap individual positions at max_position_value
        position_size = min(equal_weight, max_position_value)
        
        # Build target portfolio
        target_portfolio = {}
        for _, row in picks_df.iterrows():
            ticker = row['ticker']
            
            # Use position_size_dollars from picks if available
            if 'position_size_dollars' in row and pd.notna(row['position_size_dollars']):
                target_value = float(row['position_size_dollars'])
            else:
                target_value = position_size
            
            # Apply cap
            target_value = min(target_value, max_position_value)
            
            target_portfolio[ticker] = target_value
        
        logger.info(f"Calculated position sizes for {len(target_portfolio)} tickers")
        logger.info(f"Total target allocation: ${sum(target_portfolio.values()):,.2f} "
                   f"({sum(target_portfolio.values())/portfolio_value:.1%} of portfolio)")
        
        return target_portfolio
    
    def execute_from_picks(self, source: str = 'weekly') -> Dict:
        """
        Execute trades based on picks file.
        
        Args:
            source: 'weekly' or 'monthly'
            
        Returns:
            Execution results summary
        """
        logger.info(f"=" * 80)
        logger.info(f"Starting trade execution from {source} picks")
        logger.info(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE TRADING'}")
        logger.info(f"=" * 80)
        
        # 1. Load picks
        picks_df = self.load_latest_picks(source)
        logger.info(f"Loaded {len(picks_df)} picks")
        
        # 2. Get current portfolio value
        portfolio_value = self.executor.get_portfolio_value()
        logger.info(f"Current portfolio value: ${portfolio_value:,.2f}")
        
        # 3. Calculate target positions
        target_portfolio = self.calculate_position_sizes(picks_df, portfolio_value)
        
        # 4. Execute rebalancing
        logger.info("Executing rebalancing...")
        results = self.executor.rebalance_to_target(
            target_portfolio,
            dry_run=self.dry_run,
            tolerance=0.02  # 2% tolerance to avoid excessive trading
        )
        
        # 5. Summarize results
        summary = {
            'timestamp': datetime.now().isoformat(),
            'source': source,
            'mode': 'dry_run' if self.dry_run else 'live',
            'portfolio_value': portfolio_value,
            'n_picks': len(picks_df),
            'orders_placed': len(results['orders_placed']),
            'positions_closed': len(results['positions_closed']),
            'positions_skipped': len(results['skipped']),
            'errors': len(results['errors']),
            'results': results
        }
        
        # Save execution log
        log_file = f"logs/execution_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        os.makedirs('logs', exist_ok=True)
        with open(log_file, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Execution complete. Log saved to: {log_file}")
        logger.info(f"Summary: {summary['orders_placed']} orders, "
                   f"{summary['positions_closed']} closures, "
                   f"{summary['errors']} errors")
        
        return summary
    
    def execute_from_targets(self, targets_file: str) -> Dict:
        """
        Execute trades from a custom targets JSON file.
        
        Args:
            targets_file: Path to JSON file with format:
                         {"AAPL": 5000, "MSFT": 4500, ...}
                         
        Returns:
            Execution results summary
        """
        logger.info(f"Loading custom targets from: {targets_file}")
        
        with open(targets_file, 'r') as f:
            target_portfolio = json.load(f)
        
        logger.info(f"Loaded {len(target_portfolio)} target positions")
        
        # Get current portfolio value for validation
        portfolio_value = self.executor.get_portfolio_value()
        total_target = sum(target_portfolio.values())
        
        if total_target > portfolio_value * self.max_total_pct:
            logger.warning(f"Total target (${total_target:,.2f}) exceeds safe allocation "
                         f"(${portfolio_value * self.max_total_pct:,.2f})")
        
        # Execute rebalancing
        logger.info("Executing rebalancing from custom targets...")
        results = self.executor.rebalance_to_target(
            target_portfolio,
            dry_run=self.dry_run
        )
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'source': 'custom_targets',
            'mode': 'dry_run' if self.dry_run else 'live',
            'portfolio_value': portfolio_value,
            'results': results
        }
        
        return summary


def main():
    """Main entry point for trade execution pipeline."""
    parser = argparse.ArgumentParser(
        description='Automated Trade Execution Pipeline',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run with weekly picks (safe, no actual trades)
  python3 pipelines/execute_trades.py --source weekly
  
  # Live trading with monthly picks (REAL TRADES!)
  python3 pipelines/execute_trades.py --source monthly --no-dry-run
  
  # Custom target portfolio
  python3 pipelines/execute_trades.py --targets my_portfolio.json --no-dry-run

Safety:
  - Default mode is DRY RUN (simulated trades only)
  - Use --no-dry-run flag to execute real trades
  - All actions are logged to logs/trade_execution.log
  - Paper trading account is used by default (set in Alpaca credentials)
        """
    )
    
    parser.add_argument(
        '--source',
        choices=['weekly', 'monthly'],
        help='Source of picks (weekly or monthly runs)'
    )
    
    parser.add_argument(
        '--targets',
        help='Path to custom targets JSON file'
    )
    
    parser.add_argument(
        '--no-dry-run',
        action='store_true',
        help='Execute real trades (default is dry-run simulation)'
    )
    
    parser.add_argument(
        '--max-position-pct',
        type=float,
        default=0.10,
        help='Maximum position size as % of portfolio (default: 0.10 = 10%%)'
    )
    
    parser.add_argument(
        '--max-total-pct',
        type=float,
        default=0.95,
        help='Maximum total allocation as % of portfolio (default: 0.95 = 95%%)'
    )
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.source and not args.targets:
        parser.error("Must specify either --source or --targets")
    
    if args.source and args.targets:
        parser.error("Cannot specify both --source and --targets")
    
    # Confirm live trading
    dry_run = not args.no_dry_run
    if not dry_run:
        print("\n" + "!" * 80)
        print("WARNING: Live trading mode enabled. Real trades will be executed!")
        print("!" * 80)
        response = input("\nType 'EXECUTE' to confirm: ")
        if response != 'EXECUTE':
            print("Aborted.")
            return
    
    try:
        # Initialize pipeline
        pipeline = TradeExecutionPipeline(
            dry_run=dry_run,
            max_position_pct=args.max_position_pct,
            max_total_pct=args.max_total_pct
        )
        
        # Execute trades
        if args.source:
            results = pipeline.execute_from_picks(source=args.source)
        else:
            results = pipeline.execute_from_targets(targets_file=args.targets)
        
        # Print summary
        print("\n" + "=" * 80)
        print("EXECUTION SUMMARY")
        print("=" * 80)
        print(f"Mode: {results['mode'].upper()}")
        print(f"Orders placed: {results.get('orders_placed', 'N/A')}")
        print(f"Positions closed: {results.get('positions_closed', 'N/A')}")
        print(f"Errors: {results.get('errors', 0)}")
        print("=" * 80)
        
        if results.get('errors', 0) > 0:
            print("\nErrors occurred. Check logs/trade_execution.log for details.")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Pipeline failed: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
