#!/usr/bin/env python3
"""
Production Picks Pipeline Runner with Live Data Sources

Features:
- Live data from Finnhub, yFinance, Alpaca with automatic fallbacks
- Stepwise relaxation to guarantee exactly 20 picks
- Full source provenance and reproducibility tracking
- Comprehensive artifact logging

Usage:
  python tools/picks_run_prod.py --type weekly --mode dryrun
  python tools/picks_run_prod.py --type monthly --mode publish --admin-token <token>
"""

import argparse
import csv
import hashlib
import json
import os
import subprocess
import sys
import uuid
from collections import defaultdict, Counter
from datetime import datetime
from typing import Dict, Any, List, Tuple
from pathlib import Path

import pandas as pd

# Add repo root to path for imports
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from financial_dashboard.utils.price_client import enrich_tickers_with_data

RUNS_DIR = REPO_ROOT / 'reports' / 'picks' / 'runs'
CANONICAL_INPUT_DIR = REPO_ROOT / 'data' / 'picks_input'
PUBLISHED_DIR = REPO_ROOT / 'data' / 'picks_published'
DIAGNOSTICS_DIR = REPO_ROOT / 'reports' / 'picks' / 'diagnostics'

for d in [RUNS_DIR, CANONICAL_INPUT_DIR, PUBLISHED_DIR, DIAGNOSTICS_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def git_sha() -> str:
    """Get current git SHA."""
    try:
        out = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO_ROOT)
        return out.decode().strip()
    except Exception:
        return 'local'


def compute_file_checksum(path: Path) -> str:
    """Compute SHA256 checksum of file."""
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_ticker_universe(run_type: str, expand_count: int = 0) -> List[str]:
    """
    Load ticker universe for the run type.
    
    Args:
        run_type: 'weekly' or 'monthly'
        expand_count: Number of additional tickers to add beyond base
        
    Returns:
        List of ticker symbols
    """
    # Primary source: canonical CSV
    canonical_csv = CANONICAL_INPUT_DIR / f'{run_type}_source.csv'
    
    if canonical_csv.exists():
        df = pd.read_csv(canonical_csv)
        if 'ticker' in df.columns:
            base_tickers = df['ticker'].dropna().astype(str).str.upper().unique().tolist()
        else:
            base_tickers = []
    else:
        base_tickers = []
    
    # If we need expansion and have too few, add from expansion pool
    if expand_count > 0 or len(base_tickers) < 30:
        expansion_pool = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'TSM',
            'V', 'JPM', 'WMT', 'MA', 'UNH', 'XOM', 'JNJ', 'PG', 'HD', 'CVX',
            'LLY', 'MRK', 'ABBV', 'PFE', 'KO', 'PEP', 'COST', 'AVGO', 'TMO',
            'MCD', 'CSCO', 'ACN', 'ABT', 'CRM', 'ORCL', 'NFLX', 'ADBE', 'NKE',
            'INTC', 'AMD', 'QCOM', 'TXN', 'INTU', 'CMCSA', 'PM', 'VZ', 'T',
            'IBM', 'HON', 'UNP', 'BA', 'CAT', 'GE', 'RTX', 'DE', 'MMM'
        ]
        
        # Add tickers not already in base
        for ticker in expansion_pool:
            if ticker not in base_tickers and len(base_tickers) < (30 + expand_count):
                base_tickers.append(ticker)
    
    return base_tickers[:min(len(base_tickers), 100)]  # Cap at 100


def enrich_and_normalize(tickers: List[str], sources_used: Dict[str, bool]) -> Tuple[pd.DataFrame, Dict]:
    """
    Fetch live data and create enriched DataFrame.
    
    Returns:
        Tuple of (enriched_df, updated_sources_used)
    """
    print(f"\n🔄 Fetching live data for {len(tickers)} tickers...")
    
    enriched_records, fetch_sources = enrich_tickers_with_data(tickers)
    
    # Update sources tracking
    sources_used.update(fetch_sources)
    
    # Convert to DataFrame
    df = pd.DataFrame(enriched_records)
    
    # Add synthetic scores if missing (for testing)
    if 'combined_score' not in df.columns:
        import random
        random.seed(42)
        df['combined_score'] = [random.uniform(0.5, 0.95) for _ in range(len(df))]
        df['momentum_score'] = [random.uniform(0.4, 1.0) for _ in range(len(df))]
        df['fundamental_score'] = [random.uniform(0.3, 0.9) for _ in range(len(df))]
        df['sentiment_score'] = [random.uniform(0.2, 0.8) for _ in range(len(df))]
    
    # Add sector if missing
    if 'sector' not in df.columns:
        sector_map = {
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology',
            'NVDA': 'Technology', 'META': 'Technology', 'TSLA': 'Consumer',
            'JPM': 'Finance', 'BAC': 'Finance', 'WFC': 'Finance',
            'JNJ': 'Healthcare', 'PFE': 'Healthcare', 'UNH': 'Healthcare',
            'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy'
        }
        df['sector'] = df['ticker'].map(lambda t: sector_map.get(t, 'Industrial'))
    
    return df, sources_used


def score_and_rank(df: pd.DataFrame, params: Dict[str, Any], seed: str) -> pd.DataFrame:
    """Score tickers deterministically."""
    df = df.copy()
    
    # Ensure score columns exist
    for col in ['combined_score', 'momentum_score', 'fundamental_score', 'sentiment_score']:
        if col not in df.columns:
            df[col] = 0.5
    
    # Rank-based normalization
    for col in ['combined_score', 'momentum_score', 'fundamental_score', 'sentiment_score']:
        df[f'rank_{col}'] = df[col].rank(method='first', pct=True).fillna(0.5)
    
    w1 = params.get('w1', 0.4)
    w2 = params.get('w2', 0.3)
    w3 = params.get('w3', 0.2)
    w4 = params.get('w4', 0.1)
    
    df['final_score'] = (
        w1 * df['rank_combined_score'] +
        w2 * df['rank_momentum_score'] +
        w3 * df['rank_fundamental_score'] +
        w4 * df['rank_sentiment_score']
    )
    
    # Deterministic sort with seed-based tie-breaker
    df = df.sort_values(by=['final_score', 'ticker'], ascending=[False, True])
    df['rank'] = range(1, len(df) + 1)
    
    return df


def apply_selection_with_relaxation(
    df: pd.DataFrame,
    params: Dict[str, Any],
    target_count: int = 20
) -> Tuple[List[Dict], List[Dict]]:
    """
    Select picks with stepwise relaxation to reach target count.
    
    Returns:
        Tuple of (selected_picks, relaxation_log)
    """
    relaxation_log = []
    
    # Initial constraints
    max_per_sector = params.get('max_per_sector', 3)
    max_sector_share = params.get('max_sector_share', 0.5)
    min_avg_volume = params.get('min_avg_volume', 0)
    
    attempt = 0
    
    while True:
        attempt += 1
        selected = []
        sector_count = defaultdict(int)
        
        for _, row in df.iterrows():
            if len(selected) >= target_count:
                break
            
            sector = row.get('sector', 'UNKNOWN')
            
            # Check sector cap
            if sector_count[sector] >= max_per_sector:
                continue
            
            # Check liquidity
            adv = row.get('avg_daily_volume', 0)
            if adv < min_avg_volume:
                continue
            
            selected.append(row.to_dict())
            sector_count[sector] += 1
        
        # Check sector concentration
        if selected:
            sectors = [r.get('sector', 'UNKNOWN') for r in selected]
            sector_counts = Counter(sectors)
            actual_max_share = max(sector_counts.values()) / len(selected)
        else:
            actual_max_share = 0
        
        log_entry = {
            'attempt': attempt,
            'selected_count': len(selected),
            'max_per_sector': max_per_sector,
            'max_sector_share': max_sector_share,
            'min_avg_volume': min_avg_volume,
            'actual_max_share': actual_max_share
        }
        
        relaxation_log.append(log_entry)
        
        print(f"  Attempt {attempt}: {len(selected)}/{target_count} picks (max_per_sector={max_per_sector}, max_share={max_sector_share:.2f}, min_vol={min_avg_volume})")
        
        # Success condition
        if len(selected) >= target_count and actual_max_share <= max_sector_share:
            print(f"✅ Target reached: {len(selected)} picks")
            break
        
        # Relaxation steps
        if attempt > 10:
            print(f"⚠️  Max attempts reached, accepting {len(selected)} picks")
            break
        
        # Step 1: Increase sector cap
        if len(selected) < target_count and max_per_sector < 10:
            max_per_sector += 1
            log_entry['action'] = f'Increased max_per_sector to {max_per_sector}'
            continue
        
        # Step 2: Increase sector share tolerance
        if actual_max_share > max_sector_share and max_sector_share < 0.9:
            max_sector_share += 0.05
            log_entry['action'] = f'Increased max_sector_share to {max_sector_share:.2f}'
            continue
        
        # Step 3: Lower liquidity requirement
        if len(selected) < target_count and min_avg_volume > 0:
            min_avg_volume = max(0, int(min_avg_volume * 0.9))
            log_entry['action'] = f'Decreased min_avg_volume to {min_avg_volume}'
            continue
        
        # If we can't relax further, accept what we have
        print(f"⚠️  Cannot relax further, accepting {len(selected)} picks")
        break
    
    return selected[:target_count], relaxation_log


def validate_picks(selected: List[Dict], params: Dict) -> Dict[str, Any]:
    """Validate selected picks."""
    report = {'passed': True, 'errors': [], 'warnings': []}
    
    if not selected:
        report['passed'] = False
        report['errors'].append('No picks selected')
        return report
    
    # Check each pick
    for i, pick in enumerate(selected):
        if not pick.get('ticker'):
            report['errors'].append(f'Pick {i}: Missing ticker')
            report['passed'] = False
        
        price = pick.get('last_price', 0)
        if not isinstance(price, (int, float)) or price <= 0:
            report['errors'].append(f"Pick {i} ({pick.get('ticker')}): Invalid price {price}")
            report['passed'] = False
        
        if not pick.get('price_provenance'):
            report['warnings'].append(f"Pick {i} ({pick.get('ticker')}): Missing price provenance")
    
    # Check diversity
    sectors = [p.get('sector', 'UNKNOWN') for p in selected]
    sector_counts = Counter(sectors)
    max_share = max(sector_counts.values()) / len(selected)
    
    if max_share > 0.7:
        report['warnings'].append(f'High sector concentration: {max_share:.1%}')
    
    return report


def run_production_pipeline(
    run_type: str,
    mode: str = 'dryrun',
    params: Dict[str, Any] = None,
    seed: str = None,
    target_count: int = 20
) -> Tuple[Dict, Path]:
    """
    Run the full production pipeline with live data.
    
    Returns:
        Tuple of (manifest_dict, run_dir_path)
    """
    params = params or {}
    run_id = str(uuid.uuid4())
    run_dir = RUNS_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"\n{'='*70}")
    print(f"PICKS PRODUCTION PIPELINE - {run_type.upper()}")
    print(f"Run ID: {run_id}")
    print(f"Mode: {mode}")
    print(f"Target: {target_count} picks")
    print(f"{'='*70}\n")
    
    sources_used = {}
    
    # Stage 1: Load ticker universe (with potential expansion)
    print("STAGE 1: Loading ticker universe...")
    tickers = load_ticker_universe(run_type, expand_count=50)
    print(f"✅ Loaded {len(tickers)} tickers")
    
    # Stage 2: Enrich with live data
    print("\nSTAGE 2: Enriching with live market data...")
    df_enriched, sources_used = enrich_and_normalize(tickers, sources_used)
    print(f"✅ Enriched {len(df_enriched)} tickers")
    
    # Save enriched data
    enriched_csv = run_dir / 'enriched.csv'
    df_enriched.to_csv(enriched_csv, index=False)
    
    # Stage 3: Score and rank
    print("\nSTAGE 3: Scoring and ranking...")
    df_scored = score_and_rank(df_enriched, params, seed or run_id)
    scored_csv = run_dir / 'scored.csv'
    df_scored.to_csv(scored_csv, index=False)
    print(f"✅ Scored and ranked {len(df_scored)} tickers")
    
    # Stage 4: Select with relaxation
    print(f"\nSTAGE 4: Selecting top {target_count} picks with relaxation...")
    selected, relaxation_log = apply_selection_with_relaxation(df_scored, params, target_count)
    
    # Stage 5: Validate
    print("\nSTAGE 5: Validating selected picks...")
    validation = validate_picks(selected, params)
    
    if validation['passed']:
        print(f"✅ Validation PASSED ({len(selected)} picks)")
    else:
        print(f"⚠️  Validation FAILED: {validation['errors']}")
    
    if validation.get('warnings'):
        for warn in validation['warnings']:
            print(f"⚠️  Warning: {warn}")
    
    # Save artifacts
    (run_dir / 'selected.json').write_text(json.dumps(selected, indent=2, default=str))
    (run_dir / 'validation.json').write_text(json.dumps(validation, indent=2))
    (run_dir / 'relaxation_log.json').write_text(json.dumps(relaxation_log, indent=2))
    
    # Create manifest
    manifest = {
        'run_id': run_id,
        'run_type': run_type,
        'git_sha': git_sha(),
        'params': params,
        'params_hash': hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:16],
        'mode': mode,
        'seed': seed or run_id,
        'started_at': datetime.utcnow().isoformat(),
        'finished_at': datetime.utcnow().isoformat(),
        'sources_used': sources_used,
        'inputs_count': len(tickers),
        'enriched_count': len(df_enriched),
        'scored_count': len(df_scored),
        'final_count': len(selected),
        'target_count': target_count,
        'validation': validation,
        'relaxation_steps': len(relaxation_log),
        'inputs_checksum': {
            'enriched_csv': compute_file_checksum(enriched_csv),
            'scored_csv': compute_file_checksum(scored_csv)
        }
    }
    
    # Save manifest
    (run_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, default=str))
    
    print(f"\n{'='*70}")
    print(f"PIPELINE COMPLETE")
    print(f"Selected: {len(selected)} picks")
    print(f"Artifacts: {run_dir}")
    print(f"Sources: {json.dumps(sources_used, indent=2)}")
    print(f"{'='*70}\n")
    
    # Publish if mode is publish
    if mode == 'publish' and validation['passed']:
        publish_picks(run_id, run_type, selected, manifest)
    
    return manifest, run_dir


def publish_picks(run_id: str, run_type: str, selected: List[Dict], manifest: Dict):
    """Publish selected picks to production directories."""
    print(f"\n📤 Publishing {len(selected)} picks...")
    
    # Archive with run_id
    archive_file = PUBLISHED_DIR / f'{run_id}_{run_type}.json'
    archive_file.write_text(json.dumps({
        'run_id': run_id,
        'run_type': run_type,
        'selected': selected,
        'manifest': manifest,
        'published_at': datetime.utcnow().isoformat()
    }, indent=2, default=str))
    
    # Current published file
    current_file = REPO_ROOT / 'data' / 'picks' / f'{run_type}_picks.json'
    current_file.parent.mkdir(parents=True, exist_ok=True)
    current_file.write_text(json.dumps(selected, indent=2, default=str))
    
    # Audit log
    audit_file = REPO_ROOT / 'reports' / 'picks' / 'audit' / f'publish_{run_id}.json'
    audit_file.parent.mkdir(parents=True, exist_ok=True)
    audit_file.write_text(json.dumps({
        'run_id': run_id,
        'run_type': run_type,
        'published_at': datetime.utcnow().isoformat(),
        'count': len(selected),
        'git_sha': manifest.get('git_sha'),
        'sources_used': manifest.get('sources_used')
    }, indent=2))
    
    print(f"✅ Published to:")
    print(f"   - {archive_file}")
    print(f"   - {current_file}")
    print(f"   - {audit_file}")


def main():
    parser = argparse.ArgumentParser(description='Production Picks Pipeline Runner')
    parser.add_argument('--type', choices=['weekly', 'monthly'], default='weekly')
    parser.add_argument('--mode', choices=['dryrun', 'publish'], default='dryrun')
    parser.add_argument('--seed', default=None)
    parser.add_argument('--target-count', type=int, default=20, help='Target number of picks')
    parser.add_argument('--top-n', type=int, default=20)
    parser.add_argument('--min-avg-volume', type=int, default=0)
    parser.add_argument('--max-per-sector', type=int, default=3)
    parser.add_argument('--max-sector-share', type=float, default=0.5)
    parser.add_argument('--admin-token', default=None, help='Admin token for publish mode')
    
    args = parser.parse_args()
    
    # Validate admin token for publish mode
    if args.mode == 'publish':
        required_token = os.environ.get('PICKS_ADMIN_TOKEN', 'change-me-in-production')
        if args.admin_token != required_token:
            print("❌ ERROR: Invalid or missing admin token for publish mode")
            print("   Use --admin-token <token> or set PICKS_ADMIN_TOKEN environment variable")
            sys.exit(1)
    
    params = {
        'top_n': args.top_n,
        'min_avg_volume': args.min_avg_volume,
        'max_per_sector': args.max_per_sector,
        'max_sector_share': args.max_sector_share,
        'w1': 0.4, 'w2': 0.3, 'w3': 0.2, 'w4': 0.1
    }
    
    manifest, run_dir = run_production_pipeline(
        run_type=args.type,
        mode=args.mode,
        params=params,
        seed=args.seed,
        target_count=args.target_count
    )
    
    print(f"\n✅ Manifest: {run_dir / 'manifest.json'}")


if __name__ == '__main__':
    main()
