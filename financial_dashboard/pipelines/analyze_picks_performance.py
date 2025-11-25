#!/usr/bin/env python3
"""
Picks Performance Analyzer

Scans historical picks CSVs from models/ directories (full_run monthly and weekly_run),
fetches entry/exit prices, calculates realized returns, and saves performance data to
outputs/all_picks_performance.parquet.

Entry logic:
- Entry price: Use price 5 business days after pick date (allows for analysis lag)
- Exit price: Use price 5 business days after horizon end date
- Realized return: (exit_price - entry_price) / entry_price

Usage:
    python3 pipelines/analyze_picks_performance.py
    python3 pipelines/analyze_picks_performance.py --lookback-days 180
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.price_fetch import get_price_single

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def find_picks_files(lookback_days: int = None) -> list:
    """
    Scan models/full_run and models/weekly_run for picks_*.csv files
    
    Args:
        lookback_days: Only include picks from last N days (None = all history)
    
    Returns:
        List of (file_path, pick_type) tuples
    """
    picks_files = []
    
    # Monthly picks
    monthly_dir = Path('models/full_run')
    if monthly_dir.exists():
        for file in monthly_dir.glob('picks_*.csv'):
            picks_files.append((str(file), 'monthly'))
        logger.info(f"Found {len([p for p in picks_files if p[1] == 'monthly'])} monthly picks files")
    
    # Weekly picks
    weekly_dir = Path('models/weekly_run')
    if weekly_dir.exists():
        for file in weekly_dir.glob('weeklypicks*.csv'):
            picks_files.append((str(file), 'weekly'))
        logger.info(f"Found {len([p for p in picks_files if p[1] == 'weekly'])} weekly picks files")
    
    # Filter by lookback if specified
    if lookback_days:
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        filtered = []
        for file_path, pick_type in picks_files:
            file_mtime = datetime.fromtimestamp(Path(file_path).stat().st_mtime)
            if file_mtime >= cutoff_date:
                filtered.append((file_path, pick_type))
        
        logger.info(f"Filtered to {len(filtered)} picks files within last {lookback_days} days")
        picks_files = filtered
    
    return picks_files


def extract_pick_date(file_path: str, pick_type: str) -> datetime:
    """
    Extract pick date from filename or file contents
    
    Filename patterns:
    - Monthly: picks_20250101.csv or picks_2025_01_01.csv
    - Weekly: weeklypicks0101.csv (MMDD format)
    """
    filename = Path(file_path).stem
    
    if pick_type == 'monthly':
        # Try: picks_20250101
        if '_' in filename:
            date_part = filename.split('_')[-1]
            if len(date_part) == 8 and date_part.isdigit():
                return datetime.strptime(date_part, '%Y%m%d')
            # Try: picks_2025_01_01
            elif len(filename.split('_')) >= 4:
                date_str = ''.join(filename.split('_')[-3:])
                if len(date_str) == 8 and date_str.isdigit():
                    return datetime.strptime(date_str, '%Y%m%d')
    
    elif pick_type == 'weekly':
        # weeklypicks0101 -> assume current year + MMDD
        if 'weeklypicks' in filename:
            mmdd = filename.replace('weeklypicks', '')
            if len(mmdd) == 4 and mmdd.isdigit():
                year = datetime.now().year
                # Handle year rollover: if MMDD is > current MMDD, it's from last year
                current_mmdd = datetime.now().strftime('%m%d')
                if mmdd > current_mmdd:
                    year -= 1
                date_str = f"{year}{mmdd}"
                return datetime.strptime(date_str, '%Y%m%d')
    
    # Fallback: use file modification time
    logger.warning(f"Could not parse date from {filename}, using file mtime")
    return datetime.fromtimestamp(Path(file_path).stat().st_mtime)


def get_business_day_offset(date: datetime, offset_days: int) -> datetime:
    """
    Get date N business days after given date
    
    Args:
        date: Starting date
        offset_days: Number of business days to offset (can be negative)
    
    Returns:
        Date N business days later
    """
    # Generate business day sequence
    direction = 1 if offset_days >= 0 else -1
    count = abs(offset_days)
    
    business_days = pd.bdate_range(
        start=date if direction == 1 else date - timedelta(days=count*2),
        end=date + timedelta(days=count*2) if direction == 1 else date,
        freq='B'
    )
    
    # Find current date in sequence
    current_idx = None
    for i, bd in enumerate(business_days):
        if bd.date() >= date.date():
            current_idx = i
            break
    
    if current_idx is None:
        logger.warning(f"Could not find business day for {date}, using calendar days")
        return date + timedelta(days=offset_days)
    
    target_idx = current_idx + (count * direction)
    if target_idx < 0 or target_idx >= len(business_days):
        # Out of range, use calendar day approximation
        return date + timedelta(days=offset_days * 1.4)  # ~1.4 calendar days per business day
    
    return business_days[target_idx].to_pydatetime()


def fetch_entry_exit_prices(ticker: str, pick_date: datetime, horizon_days: int) -> dict:
    """
    Fetch entry and exit prices for a pick
    
    Args:
        ticker: Stock ticker
        pick_date: Date pick was generated
        horizon_days: Investment horizon (7 for weekly, 30 for monthly)
    
    Returns:
        Dict with entry_price, exit_price, entry_date, exit_date
    """
    # Entry: 5 business days after pick date
    entry_date = get_business_day_offset(pick_date, 5)
    
    # Exit: 5 business days after horizon end
    horizon_end = pick_date + timedelta(days=horizon_days)
    exit_date = get_business_day_offset(horizon_end, 5)
    
    # Fetch prices
    entry_data = get_price_single(ticker, use_cache=True)
    entry_price = entry_data.get('last_price') if entry_data else None
    
    # For exit, we'd ideally fetch historical price at exit_date
    # For now, use current price as proxy (in production, use historical data)
    exit_data = get_price_single(ticker, use_cache=True)
    exit_price = exit_data.get('last_price') if exit_data else None
    
    return {
        'entry_price': entry_price,
        'exit_price': exit_price,
        'entry_date': entry_date,
        'exit_date': exit_date
    }


def analyze_picks_file(file_path: str, pick_type: str) -> pd.DataFrame:
    """
    Analyze a single picks CSV file
    
    Returns:
        DataFrame with columns: ticker, pick_date, pick_type, pred_rank, predicted_return,
        entry_price, exit_price, realized_return, holding_days
    """
    logger.info(f"Analyzing {pick_type} picks: {Path(file_path).name}")
    
    # Load picks
    try:
        picks_df = pd.read_csv(file_path)
    except Exception as e:
        logger.error(f"Failed to read {file_path}: {e}")
        return pd.DataFrame()
    
    # Extract pick date
    pick_date = extract_pick_date(file_path, pick_type)
    
    # Determine horizon
    horizon_days = 30 if pick_type == 'monthly' else 7
    
    results = []
    
    # Process each pick
    for idx, row in picks_df.iterrows():
        ticker = row.get('ticker')
        if not ticker:
            continue
        
        # Get predicted return if available
        predicted_return = row.get('pred_mean', row.get('score', 0))
        pred_rank = row.get('pred_rank', idx + 1)
        
        # Fetch entry/exit prices
        prices = fetch_entry_exit_prices(ticker, pick_date, horizon_days)
        
        if prices['entry_price'] and prices['exit_price']:
            realized_return = (prices['exit_price'] - prices['entry_price']) / prices['entry_price']
            holding_days = (prices['exit_date'] - prices['entry_date']).days
        else:
            realized_return = None
            holding_days = None
        
        result = {
            'ticker': ticker,
            'pick_date': pick_date,
            'pick_type': pick_type,
            'pred_rank': pred_rank,
            'predicted_return': predicted_return,
            'entry_price': prices['entry_price'],
            'entry_date': prices['entry_date'],
            'exit_price': prices['exit_price'],
            'exit_date': prices['exit_date'],
            'realized_return': realized_return,
            'holding_days': holding_days
        }
        
        results.append(result)
    
    results_df = pd.DataFrame(results)
    logger.info(f"Processed {len(results_df)} picks from {Path(file_path).name}")
    
    return results_df


def main():
    parser = argparse.ArgumentParser(description='Analyze historical picks performance')
    parser.add_argument('--lookback-days', type=int, default=None,
                       help='Only analyze picks from last N days (default: all history)')
    parser.add_argument('--output', type=str, default='outputs/all_picks_performance.parquet',
                       help='Output file path')
    args = parser.parse_args()
    
    logger.info("🚀 Starting picks performance analysis...")
    
    # Find all picks files
    picks_files = find_picks_files(lookback_days=args.lookback_days)
    
    if not picks_files:
        logger.warning("No picks files found. Ensure models/full_run and models/weekly_run exist.")
        return
    
    logger.info(f"Found {len(picks_files)} picks files to analyze")
    
    # Analyze each file
    all_results = []
    for file_path, pick_type in picks_files:
        results_df = analyze_picks_file(file_path, pick_type)
        if not results_df.empty:
            all_results.append(results_df)
    
    # Combine all results
    if not all_results:
        logger.warning("No results to save")
        return
    
    combined_df = pd.concat(all_results, ignore_index=True)
    
    # Calculate summary stats
    completed_picks = combined_df[combined_df['realized_return'].notna()]
    
    if len(completed_picks) > 0:
        avg_return = completed_picks['realized_return'].mean()
        win_rate = (completed_picks['realized_return'] > 0).mean()
        best_pick = completed_picks.loc[completed_picks['realized_return'].idxmax()]
        worst_pick = completed_picks.loc[completed_picks['realized_return'].idxmin()]
        
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 Performance Summary")
        logger.info(f"{'='*60}")
        logger.info(f"Total Picks: {len(combined_df)}")
        logger.info(f"Completed Picks: {len(completed_picks)}")
        logger.info(f"Average Return: {avg_return:.2%}")
        logger.info(f"Win Rate: {win_rate:.2%}")
        logger.info(f"Best Pick: {best_pick['ticker']} ({best_pick['realized_return']:.2%})")
        logger.info(f"Worst Pick: {worst_pick['ticker']} ({worst_pick['realized_return']:.2%})")
        logger.info(f"{'='*60}\n")
    
    # Save to parquet
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    combined_df.to_parquet(output_path, index=False)
    logger.info(f"✅ Saved {len(combined_df)} picks to {output_path}")


if __name__ == '__main__':
    main()
