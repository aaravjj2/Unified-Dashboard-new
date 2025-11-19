#!/usr/bin/env python3
"""
scripts/generate_attribution.py

Attribution analysis pipeline for monthly and weekly picks.

This script:
1. Loads picks CSV (monthly or weekly)
2. Computes realized returns over horizon (1w or 1m)
3. Estimates beta vs SPY using historical returns
4. Decomposes returns into beta contribution + alpha residual
5. Aggregates SHAP values by factor categories
6. Saves per-pick attribution to parquet
7. Saves portfolio-level metrics to JSON

Usage:
    # For monthly picks (1 month horizon)
    python scripts/generate_attribution.py \\
        --picks models/full_run/picks_20250101.csv \\
        --horizon 1m \\
        --output attribution/20250101

    # For weekly picks (1 week horizon)
    python scripts/generate_attribution.py \\
        --picks models/weekly_run/picks_weekly_20250101.csv \\
        --horizon 1w \\
        --output attribution/weekly_20250101

    # With SHAP explanations
    python scripts/generate_attribution.py \\
        --picks models/full_run/picks_20250101.csv \\
        --explain explain/picks_explain_20250101.json \\
        --horizon 1m \\
        --output attribution/20250101
"""

import os
import sys
import argparse
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import logging

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.attribution import (
    compute_alpha_beta_decomposition,
    compute_portfolio_attribution,
    aggregate_portfolio_metrics,
)
from utils.price_fetch import fetch_prices_batch, get_price_on_date

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def parse_horizon(horizon_str: str) -> timedelta:
    """Parse horizon string like '1w' or '1m' to timedelta."""
    horizon_str = horizon_str.lower().strip()
    
    if horizon_str.endswith('d'):
        days = int(horizon_str[:-1])
        return timedelta(days=days)
    elif horizon_str.endswith('w'):
        weeks = int(horizon_str[:-1])
        return timedelta(weeks=weeks)
    elif horizon_str.endswith('m'):
        months = int(horizon_str[:-1])
        # Approximate: 1 month = 30 days
        return timedelta(days=months * 30)
    else:
        raise ValueError(f"Invalid horizon format: {horizon_str}. Use '1w', '1m', '5d', etc.")


def load_picks_csv(picks_path: str) -> pd.DataFrame:
    """Load picks CSV and validate required columns."""
    if not os.path.exists(picks_path):
        raise FileNotFoundError(f"Picks file not found: {picks_path}")
    
    df = pd.read_csv(picks_path)
    
    # Validate required columns
    required_cols = ['ticker', 'date', 'pred_mean']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Picks CSV missing required columns: {missing}")
    
    # Parse date
    df['date'] = pd.to_datetime(df['date'])
    
    logger.info(f"Loaded {len(df)} picks from {picks_path}")
    return df


def load_shap_explanations(explain_path: str) -> dict:
    """Load SHAP explanations JSON."""
    if not explain_path or not os.path.exists(explain_path):
        logger.warning(f"SHAP explanations not found: {explain_path}")
        return {}
    
    with open(explain_path, 'r') as f:
        explain_data = json.load(f)
    
    # Convert to ticker -> shap_values dict
    shap_dict = {}
    for item in explain_data.get('explanations', []):
        ticker = item.get('ticker')
        shap_values = item.get('shap_values', {})
        if ticker:
            shap_dict[ticker] = shap_values
    
    logger.info(f"Loaded SHAP explanations for {len(shap_dict)} tickers")
    return shap_dict


def compute_realized_returns(
    picks_df: pd.DataFrame,
    horizon: timedelta,
    price_cache_ttl: int = 3600,
) -> pd.DataFrame:
    """
    Compute realized returns for each pick over the specified horizon.
    
    Args:
        picks_df: DataFrame with columns [ticker, date, pred_mean]
        horizon: Time horizon for return calculation
        price_cache_ttl: Cache TTL for price fetching (seconds)
    
    Returns:
        DataFrame with additional columns [entry_price, exit_price, realized_return]
    """
    results = []
    
    for _, row in picks_df.iterrows():
        ticker = row['ticker']
        entry_date = row['date']
        exit_date = entry_date + horizon
        
        try:
            # Fetch entry and exit prices
            entry_price = get_price_on_date(
                ticker,
                entry_date,
                cache_ttl=price_cache_ttl
            )
            exit_price = get_price_on_date(
                ticker,
                exit_date,
                cache_ttl=price_cache_ttl
            )
            
            if entry_price and exit_price:
                realized_return = (exit_price - entry_price) / entry_price
            else:
                realized_return = np.nan
                logger.warning(
                    f"Could not compute return for {ticker}: "
                    f"entry_price={entry_price}, exit_price={exit_price}"
                )
        
        except Exception as e:
            logger.error(f"Error computing return for {ticker}: {e}")
            entry_price = np.nan
            exit_price = np.nan
            realized_return = np.nan
        
        results.append({
            'ticker': ticker,
            'date': entry_date,
            'exit_date': exit_date,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'realized_return': realized_return,
        })
    
    results_df = pd.DataFrame(results)
    
    # Merge back with picks_df
    picks_with_returns = picks_df.merge(
        results_df,
        on=['ticker', 'date'],
        how='left'
    )
    
    # Log statistics
    valid_returns = picks_with_returns['realized_return'].dropna()
    if len(valid_returns) > 0:
        logger.info(
            f"Computed realized returns for {len(valid_returns)}/{len(picks_df)} picks. "
            f"Mean: {valid_returns.mean():.2%}, Median: {valid_returns.median():.2%}"
        )
    else:
        logger.warning("No valid realized returns computed!")
    
    return picks_with_returns


def fetch_benchmark_returns(
    benchmark: str,
    start_date: datetime,
    end_date: datetime,
    horizon: timedelta,
) -> tuple:
    """
    Fetch benchmark return over the same horizon.
    
    Returns:
        Tuple of (benchmark_return_over_horizon, returns_history_df)
    """
    # Fetch horizon return
    bench_entry = get_price_on_date(benchmark, start_date)
    bench_exit = get_price_on_date(benchmark, start_date + horizon)
    
    if bench_entry and bench_exit:
        benchmark_return = (bench_exit - bench_entry) / bench_entry
    else:
        logger.warning(f"Could not compute benchmark return for {benchmark}")
        benchmark_return = 0.0
    
    # Fetch historical returns for beta estimation (past 6 months)
    history_start = start_date - timedelta(days=180)
    history_df = fetch_historical_returns(
        benchmark,
        history_start,
        end_date
    )
    
    return benchmark_return, history_df


def fetch_historical_returns(
    ticker: str,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """
    Fetch historical daily returns for beta estimation.
    
    Returns:
        DataFrame with columns [date, returns]
    """
    try:
        import yfinance as yf
        
        # Download historical data
        data = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            progress=False,
            auto_adjust=True
        )
        
        if data.empty:
            logger.warning(f"No historical data for {ticker}")
            return pd.DataFrame(columns=['date', 'returns'])
        
        # Compute daily returns
        data['returns'] = data['Close'].pct_change()
        data = data.dropna(subset=['returns'])
        
        # Reset index to get date as column
        data = data.reset_index()
        data = data[['Date', 'returns']]
        data.columns = ['date', 'returns']
        
        return data
    
    except Exception as e:
        logger.error(f"Error fetching historical returns for {ticker}: {e}")
        return pd.DataFrame(columns=['date', 'returns'])


def build_returns_dataframe(
    picks_df: pd.DataFrame,
    benchmark: str,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    """
    Build a unified returns DataFrame for all tickers + benchmark.
    
    Returns:
        DataFrame with columns [date, ticker, returns]
    """
    all_tickers = list(picks_df['ticker'].unique()) + [benchmark]
    
    returns_data = []
    
    for ticker in all_tickers:
        ticker_returns = fetch_historical_returns(ticker, start_date, end_date)
        ticker_returns['ticker'] = ticker
        returns_data.append(ticker_returns)
    
    if not returns_data:
        return pd.DataFrame(columns=['date', 'ticker', 'returns'])
    
    returns_df = pd.concat(returns_data, ignore_index=True)
    
    logger.info(
        f"Built returns DataFrame: {len(returns_df)} observations, "
        f"{len(all_tickers)} tickers"
    )
    
    return returns_df


# ============================================================================
# Main Pipeline
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate attribution analysis for picks'
    )
    parser.add_argument(
        '--picks',
        required=True,
        help='Path to picks CSV file'
    )
    parser.add_argument(
        '--horizon',
        default='1m',
        help='Return horizon (e.g., "1w", "1m", "5d")'
    )
    parser.add_argument(
        '--explain',
        default=None,
        help='Path to SHAP explanations JSON (optional)'
    )
    parser.add_argument(
        '--benchmark',
        default='SPY',
        help='Benchmark ticker (default: SPY)'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output path prefix (e.g., "attribution/20250101")'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force recomputation even if output exists'
    )
    
    args = parser.parse_args()
    
    # Parse horizon
    horizon = parse_horizon(args.horizon)
    logger.info(f"Using horizon: {args.horizon} ({horizon.days} days)")
    
    # Check if output already exists
    output_parquet = f"{args.output}_per_pick.parquet"
    output_json = f"{args.output}_portfolio.json"
    
    if not args.force and os.path.exists(output_parquet) and os.path.exists(output_json):
        logger.info(f"Attribution already exists at {args.output}. Use --force to recompute.")
        return
    
    # Create output directory
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    
    # Load picks
    picks_df = load_picks_csv(args.picks)
    
    # Load SHAP explanations (if provided)
    shap_dict = load_shap_explanations(args.explain) if args.explain else {}
    
    # Get date range
    min_date = picks_df['date'].min()
    max_date = picks_df['date'].max()
    end_date = max_date + horizon + timedelta(days=7)  # Add buffer
    
    logger.info(f"Date range: {min_date} to {end_date}")
    
    # Compute realized returns
    logger.info("Computing realized returns...")
    picks_with_returns = compute_realized_returns(picks_df, horizon)
    
    # Filter out picks without valid returns
    valid_picks = picks_with_returns.dropna(subset=['realized_return'])
    
    if len(valid_picks) == 0:
        logger.error("No valid picks with realized returns. Cannot compute attribution.")
        return
    
    logger.info(f"Valid picks with returns: {len(valid_picks)}/{len(picks_df)}")
    
    # Fetch benchmark return
    logger.info(f"Fetching benchmark ({args.benchmark}) returns...")
    benchmark_return, _ = fetch_benchmark_returns(
        args.benchmark,
        min_date,
        max_date,
        horizon
    )
    logger.info(f"Benchmark return over horizon: {benchmark_return:.2%}")
    
    # Build returns DataFrame for beta estimation
    logger.info("Building historical returns DataFrame for beta estimation...")
    history_start = min_date - timedelta(days=180)
    returns_df = build_returns_dataframe(
        valid_picks,
        args.benchmark,
        history_start,
        end_date
    )
    
    # Add benchmark return column to picks
    valid_picks['benchmark_return'] = benchmark_return
    
    # Compute attribution for each pick
    logger.info("Computing attribution...")
    attribution_df = compute_portfolio_attribution(
        valid_picks,
        returns_df,
        shap_dict=shap_dict if shap_dict else None,
        benchmark=args.benchmark
    )
    
    # Aggregate portfolio metrics
    logger.info("Aggregating portfolio metrics...")
    portfolio_metrics = aggregate_portfolio_metrics(attribution_df)
    
    # Add metadata
    portfolio_metrics['metadata'] = {
        'picks_file': args.picks,
        'n_picks_total': len(picks_df),
        'n_picks_valid': len(valid_picks),
        'horizon': args.horizon,
        'horizon_days': horizon.days,
        'benchmark': args.benchmark,
        'benchmark_return': round(benchmark_return, 4),
        'explain_file': args.explain,
        'generated_at': datetime.now().isoformat(),
    }
    
    # Save per-pick attribution
    logger.info(f"Saving per-pick attribution to {output_parquet}...")
    attribution_df.to_parquet(output_parquet, index=False)
    
    # Save portfolio metrics
    logger.info(f"Saving portfolio metrics to {output_json}...")
    with open(output_json, 'w') as f:
        json.dump(portfolio_metrics, f, indent=2, default=str)
    
    # Print summary
    print("\n" + "="*80)
    print("ATTRIBUTION SUMMARY")
    print("="*80)
    print(f"Total Picks: {portfolio_metrics['n_picks']}")
    print(f"Total Return: {portfolio_metrics['total_return']:.2%}")
    print(f"Beta Contribution: {portfolio_metrics['total_beta_contrib']:.2%}")
    print(f"Alpha (Residual): {portfolio_metrics['total_alpha']:.2%}")
    print(f"Average Beta: {portfolio_metrics['avg_beta']:.2f}")
    print(f"Benchmark Return: {benchmark_return:.2%}")
    
    if 'top_factors' in portfolio_metrics:
        print(f"\nTop Factors:")
        for item in portfolio_metrics['top_factors']:
            print(f"  {item['factor']}: {item['contribution']:.2%}")
    
    print(f"\nOutputs saved:")
    print(f"  Per-pick: {output_parquet}")
    print(f"  Portfolio: {output_json}")
    print("="*80)
    
    logger.info("Attribution generation complete!")


if __name__ == '__main__':
    main()
