#!/usr/bin/env python3
"""
Phase 9C Validation Runner
===========================

Comprehensive validation script for Strategy Bot + Backtester integration.

Usage:
    python run_phase9c_validation.py --mode mock --iterations 3 --tiers small medium large

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0
Date: October 29, 2025
"""

import sys
import os
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

import logging
from datetime import datetime

from strategy_orchestrator import (
    StrategyOrchestrator,
    OrchestratorMode
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Phase 9C Integration Validation Runner'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        default='mock',
        choices=['mock', 'paper', 'backtest'],
        help='Execution mode (default: mock)'
    )
    
    parser.add_argument(
        '--iterations',
        type=int,
        default=3,
        help='Number of iterations per tier (default: 3)'
    )
    
    parser.add_argument(
        '--tiers',
        type=str,
        nargs='+',
        default=['small', 'medium', 'large'],
        choices=['small', 'medium', 'large'],
        help='Portfolio tiers to test (default: all)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default='outputs/phase9c',
        help='Output directory (default: outputs/phase9c)'
    )
    
    parser.add_argument(
        '--cache',
        action='store_true',
        default=True,
        help='Enable Phase 9 cache engine (default: True)'
    )
    
    return parser.parse_args()


def main():
    """Main execution"""
    
    args = parse_args()
    
    logger.info(f"\n{'#'*100}")
    logger.info(f"# PHASE 9C VALIDATION RUNNER")
    logger.info(f"# Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"# Mode: {args.mode}")
    logger.info(f"# Iterations: {args.iterations}")
    logger.info(f"# Tiers: {', '.join(args.tiers)}")
    logger.info(f"# Output Directory: {args.output_dir}")
    logger.info(f"{'#'*100}\n")
    
    try:
        # Map mode string to enum
        mode_map = {
            'mock': OrchestratorMode.MOCK,
            'paper': OrchestratorMode.PAPER,
            'backtest': OrchestratorMode.BACKTEST
        }
        mode = mode_map[args.mode]
        
        # Initialize orchestrator
        logger.info("🔧 Initializing Strategy Orchestrator...")
        orchestrator = StrategyOrchestrator(
            mode=mode,
            output_dir=Path(args.output_dir),
            use_cache=args.cache
        )
        
        # Run validation
        logger.info("🚀 Starting validation...\n")
        start_time = datetime.now()
        
        results = orchestrator.run_full_validation(
            tiers=args.tiers,
            num_iterations=args.iterations
        )
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        # Print final summary
        logger.info(f"\n{'#'*100}")
        logger.info(f"# ✅ VALIDATION COMPLETE")
        logger.info(f"# Duration: {duration:.2f} seconds")
        logger.info(f"# Total Trades: {results.get('total_trades', 0)}")
        logger.info(f"# Total P&L: ${results.get('total_pnl', 0):,.2f}")
        logger.info(f"# Deterministic: {'✅ YES' if results.get('all_deterministic', False) else '❌ NO'}")
        logger.info(f"# SLA Compliance: {'✅ YES' if results.get('all_sla_met', False) else '❌ NO'}")
        logger.info(f"{'#'*100}\n")
        
        logger.info("📁 Output Files:")
        logger.info(f"   - {args.output_dir}/phase9c_integration_report.md")
        logger.info(f"   - {args.output_dir}/phase9c_results.json")
        logger.info(f"   - {args.output_dir}/phase9c_performance_summary.csv")
        logger.info(f"   - {args.output_dir}/phase9c_trade_log.html\n")
        
        # Exit code based on success
        if results.get('all_deterministic', False) and results.get('all_sla_met', False):
            logger.info("🎉 All validation checks PASSED!")
            return 0
        else:
            logger.warning("⚠️  Some validation checks FAILED!")
            return 1
        
    except Exception as e:
        logger.error(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
