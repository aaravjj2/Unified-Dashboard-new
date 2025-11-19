"""File discovery asset

Scans the repository for picks_*.csv and Financial_Data/**/*.parquet
and returns lists of discovered file paths.
"""
from dagster import asset
from pathlib import Path
from typing import List


@asset
def discovered_picks() -> List[str]:
    """Discover picks_*.csv files under financial_dashboard/Financial_Data.

    Returns a list of absolute paths as strings.
    """
    repo_root = Path(__file__).resolve().parents[2]
    data_dir = repo_root / "financial_dashboard" / "Financial_Data"
    
    # EXHAUSTIVE DIAGNOSTIC LOGGING
    print("=" * 80)
    print("[PICKS DISCOVERY - EXHAUSTIVE DIAGNOSTICS]")
    print(f"[1] Absolute repo_root path: {repo_root}")
    print(f"[2] Absolute data_dir path: {data_dir}")
    print(f"[3] data_dir.exists() check: {data_dir.exists()}")
    print(f"[4] data_dir.is_dir() check: {data_dir.is_dir() if data_dir.exists() else 'N/A (path does not exist)'}")
    print(f"[5] Exact glob pattern: '**/picks_*.csv'")
    print(f"[6] Full search path: {data_dir}/**/picks_*.csv")
    print("=" * 80)
    
    picks = []
    if data_dir.exists() and data_dir.is_dir():
        print(f"[EXECUTING GLOB] Searching in: {data_dir}")
        picks = list(data_dir.glob("**/picks_*.csv"))
        print(f"[GLOB RESULT] Found {len(picks)} picks CSV files")
        if picks:
            print(f"[FULL FILE LIST]:")
            for i, p in enumerate(picks, 1):
                print(f"  {i}. {p.resolve()}")
        else:
            print(f"[FULL FILE LIST]: EMPTY - No picks_*.csv files found!")
    else:
        print(f"[ERROR] data_dir does NOT exist or is NOT a directory!")
        print(f"[FALLBACK] Attempting search from repo_root: {repo_root}")
        picks = list(repo_root.glob("**/picks_*.csv"))
        print(f"[FALLBACK RESULT] Found {len(picks)} picks files in repo_root")
    
    picks_list = [str(p.resolve()) for p in picks]
    print(f"[FINAL] Returning {len(picks_list)} picks file paths")
    print("=" * 80)
    return picks_list


@asset
def discovered_parquet() -> List[str]:
    """Discover parquet files under financial_dashboard/Financial_Data.

    Returns a list of absolute paths as strings.
    """
    repo_root = Path(__file__).resolve().parents[2]
    data_dir = repo_root / "financial_dashboard" / "Financial_Data"
    
    # EXHAUSTIVE DIAGNOSTIC LOGGING
    print("=" * 80)
    print("[PARQUET DISCOVERY - EXHAUSTIVE DIAGNOSTICS]")
    print(f"[1] Absolute repo_root path: {repo_root}")
    print(f"[2] Absolute data_dir path: {data_dir}")
    print(f"[3] data_dir.exists() check: {data_dir.exists()}")
    print(f"[4] data_dir.is_dir() check: {data_dir.is_dir() if data_dir.exists() else 'N/A (path does not exist)'}")
    print(f"[5] Exact glob pattern: '**/*.parquet'")
    print(f"[6] Full search path: {data_dir}/**/*.parquet")
    print("=" * 80)
    
    parquet_files = []
    if data_dir.exists() and data_dir.is_dir():
        print(f"[EXECUTING GLOB] Searching in: {data_dir}")
        parquet_files = list(data_dir.glob("**/*.parquet"))
        print(f"[GLOB RESULT] Found {len(parquet_files)} parquet files")
        if parquet_files:
            print(f"[SAMPLE FILES] First 5 parquet files:")
            for i, p in enumerate(parquet_files[:5], 1):
                print(f"  {i}. {p.name} (full: {p.resolve()})")
        else:
            print(f"[FULL FILE LIST]: EMPTY - No .parquet files found!")
    else:
        print(f"[ERROR] data_dir does NOT exist or is NOT a directory!")
        print(f"[FALLBACK] Attempting search from repo_root: {repo_root}")
        parquet_files = list(repo_root.glob("**/*.parquet"))
        print(f"[FALLBACK RESULT] Found {len(parquet_files)} parquet files in repo_root")
    
    parquet_list = [str(p.resolve()) for p in parquet_files]
    print(f"[FINAL] Returning {len(parquet_list)} parquet file paths")
    print("=" * 80)
    return parquet_list
