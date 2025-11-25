#!/usr/bin/env python3
"""Programmatic runner to execute the ingestion asset graph in-process.

This avoids using the `dagster` CLI which can fail loading a temporary instance
when custom dagster.yaml content is present. It builds an assets job from the
assets registered in `repository.py` and executes it with the `DATABASE_URL`
environment variable passed through.
"""
import os
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine
import sys
import time

# Make imports robust to different mount layouts when running inside containers.
# The repo is sometimes mounted as /opt/dagster_project (containing the package
# directory `dagster_project`) or as /opt (containing `dagster_project`). Add
# both parents to sys.path if needed so `import dagster_project...` works.
if "/opt/dagster_project" not in sys.path:
    sys.path.insert(0, "/opt/dagster_project")
if "/opt" not in sys.path:
    sys.path.insert(0, "/opt")

# import pure transform implementations
from dagster_project.assets.transforms import clean_picks_df_impl, clean_financial_df_impl


def discover_files(repo_root: Path):
    """Discover picks_*.csv and *.parquet files with exhaustive diagnostic logging.
    
    PRODUCTION MODE: Searches multiple directories for picks CSVs and Financial_Data for parquets.
    
    Picks CSV locations:
    - financial_dashboard/models/ (all subdirectories)
    - financial_dashboard/outputs/
    - financial_dashboard/picks/
    
    Parquet location:
    - financial_dashboard/Financial_Data/ (recursive)
    """
    # FIXED: Correct repo_root resolution - should be /opt/dagster_project, not /opt
    # The script is at /opt/dagster_project/tests/run_ingestion_programmatic.py
    # So we go up 1 level (parent.parent) to get /opt/dagster_project
    correct_repo_root = Path(__file__).resolve().parent.parent
    financial_dashboard_dir = correct_repo_root / "financial_dashboard"
    parquet_data_dir = financial_dashboard_dir / "Financial_Data"
    
    # EXHAUSTIVE DIAGNOSTIC LOGGING
    print("=" * 80)
    print("[PROGRAMMATIC RUNNER - FILE DISCOVERY DIAGNOSTICS]")
    print(f"[MODE] PRODUCTION - Searching for real data files")
    print(f"[1] Script location: {__file__}")
    print(f"[2] Corrected repo_root path: {correct_repo_root}")
    print(f"[3] Financial dashboard dir: {financial_dashboard_dir}")
    print(f"[4] Parquet data_dir: {parquet_data_dir}")
    print("=" * 80)
    
    picks = []
    parquets = []
    
    # PICKS CSV SEARCH - PRODUCTION MODE (MULTIPLE LOCATIONS)
    picks_pattern = "picks_*.csv"
    picks_search_dirs = [
        financial_dashboard_dir / "models",
        financial_dashboard_dir / "outputs",
        financial_dashboard_dir / "picks"
    ]
    
    print(f"\n[PICKS CSV SEARCH - PRODUCTION DATA]")
    print(f"  Glob pattern: '{picks_pattern}'")
    print(f"  Searching in {len(picks_search_dirs)} locations:")
    
    for search_dir in picks_search_dirs:
        print(f"\n  📂 Searching: {search_dir}")
        print(f"     Exists: {search_dir.exists()}, Is dir: {search_dir.is_dir()}")
        
        if search_dir.exists() and search_dir.is_dir():
            # Search recursively for picks_*.csv in this directory
            found_in_dir = list(search_dir.glob(f"**/{picks_pattern}"))
            picks.extend(found_in_dir)
            
            if found_in_dir:
                print(f"     ✅ Found {len(found_in_dir)} picks CSV files:")
                for i, p in enumerate(found_in_dir[:3], 1):
                    print(f"        {i}. {p.relative_to(financial_dashboard_dir)}")
                if len(found_in_dir) > 3:
                    print(f"        ... and {len(found_in_dir) - 3} more")
            else:
                print(f"     ℹ️  No picks files found in this location")
        else:
            print(f"     ⚠️  Directory does not exist or is not accessible")
    
    print(f"\n  📊 TOTAL PICKS CSV FILES FOUND: {len(picks)}")
    if picks:
        print(f"  ✅ SUCCESS: Picks CSV files will be loaded")
    else:
        print(f"  ⚠️  WARNING: No picks_*.csv files found in any location!")
    
    # PARQUET DISCOVERY - PRODUCTION DATA
    print(f"\n[PARQUET SEARCH - PRODUCTION DATA]")
    if parquet_data_dir.exists() and parquet_data_dir.is_dir():
        print(f"  Glob pattern: '**/*.parquet'")
        print(f"  Searching in: {parquet_data_dir}")
        parquets = list(parquet_data_dir.glob("**/*.parquet"))
        print(f"  Result: Found {len(parquets)} parquet files")
        if parquets:
            print(f"  ✅ SUCCESS: First 5 parquet files:")
            for i, p in enumerate(parquets[:5], 1):
                print(f"    {i}. {p.name} (full: {p.resolve()})")
            if len(parquets) > 5:
                print(f"    ... and {len(parquets) - 5} more")
        else:
            print(f"  ⚠️  WARNING: No .parquet files found!")
    else:
        print(f"  ❌ ERROR: parquet_data_dir does NOT exist or is NOT a directory!")
    
    print("=" * 80)
    return [str(p.resolve()) for p in picks], [str(p.resolve()) for p in parquets]


def main():
    os.environ.setdefault('DATABASE_URL', 'postgresql+psycopg2://postgres:postgres@postgres_db:5432/market_data')
    database_url = os.environ['DATABASE_URL']
    repo_root = Path(__file__).resolve().parents[2]
    print('Repo root:', repo_root)

    picks_paths, parquet_paths = discover_files(repo_root)
    print('Discovered picks:', len(picks_paths), 'parquets:', len(parquet_paths))

    picks_dfs = []
    for p in picks_paths:
        try:
            print('Reading:', p)
            picks_dfs.append(pd.read_csv(p))
        except Exception as e:
            print('Failed to read', p, e)

    picks_df = pd.concat(picks_dfs, ignore_index=True) if picks_dfs else pd.DataFrame()
    cleaned_picks = clean_picks_df_impl(picks_df)
    print('Cleaned picks rows:', len(cleaned_picks))

    # Process parquet files incrementally to avoid high memory usage
    print('Processing parquets incrementally')
    # create engine with simple retry/backoff to handle transient network/name resolution issues
    max_retries = 3
    delay_seconds = 2
    engine = None
    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            engine = create_engine(database_url, echo=False)
            # quick test
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            print('Successfully created engine on attempt', attempt)
            break
        except Exception as e:
            last_exc = e
            print(f'Engine creation attempt {attempt}/{max_retries} failed:', e)
            if attempt < max_retries:
                time.sleep(delay_seconds)
    if engine is None:
        print('Failed to create DB engine after retries:', last_exc)
        raise last_exc
    first_fin_write = True
    total_fin_rows = 0
    for p in parquet_paths:
        try:
            print('Reading parquet:', p)
            df_part = pd.read_parquet(p)
            cleaned_part = clean_financial_df_impl(df_part)
            print('  cleaned rows:', len(cleaned_part))
            if not cleaned_part.empty:
                # write with retries
                def _retry_write(df, table_name, if_exists='append'):
                    max_retries = 3
                    delay_seconds = 2
                    last_exc = None
                    for attempt in range(1, max_retries + 1):
                        try:
                            df.to_sql(table_name, con=engine, if_exists=if_exists, index=False, method='multi', chunksize=1000)
                            return len(df)
                        except Exception as exc:
                            last_exc = exc
                            print(f'Write attempt {attempt}/{max_retries} to {table_name} failed:', exc)
                            if attempt < max_retries:
                                time.sleep(delay_seconds)
                    print(f'Failed writing to {table_name} after {max_retries} attempts:', last_exc)
                    raise last_exc

                if first_fin_write:
                    rows = _retry_write(cleaned_part, 'financial_features', if_exists='replace')
                    first_fin_write = False
                    print('  wrote (replace) rows:', rows)
                else:
                    rows = _retry_write(cleaned_part, 'financial_features', if_exists='append')
                    print('  appended rows:', rows)
                total_fin_rows += rows
        except Exception as e:
            print('Failed to process parquet', p, e)

    print('Total financial rows written:', total_fin_rows)

    # Write picks if present
    print('DATABASE_URL=', database_url)
    if not cleaned_picks.empty:
        try:
            # reuse retry helper
            def _retry_write_picks(df, table_name='picks'):
                max_retries = 3
                delay_seconds = 2
                last_exc = None
                for attempt in range(1, max_retries + 1):
                    try:
                        df.to_sql(table_name, con=engine, if_exists='replace', index=False, method='multi', chunksize=1000)
                        return len(df)
                    except Exception as exc:
                        last_exc = exc
                        print(f'Picks write attempt {attempt}/{max_retries} failed:', exc)
                        if attempt < max_retries:
                            time.sleep(delay_seconds)
                print('Failed writing picks after retries:', last_exc)
                raise last_exc

            wrote = _retry_write_picks(cleaned_picks)
            print('Wrote picks rows:', wrote)
        except Exception as e:
            print('Failed to write picks table after retries', e)
    else:
        print('No picks to write')


if __name__ == '__main__':
    main()
