"""
Picks Data Loader - Load CSV into DB or JSON fallback

Supports both SQLite database and JSON file fallback for picks data.
Includes automatic schema migration and data validation.

Usage:
    python tools/picks_load.py --type weekly --csv path/to/picks.csv
    python tools/picks_load.py --type monthly --csv path/to/picks.csv --fixture
"""

import os
import sys
import json
import argparse
import sqlite3
import pandas as pd
from datetime import datetime, date
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from financial_dashboard.utils.picks_fetcher import PicksFetcher, create_deterministic_fixture


# JSON fallback paths
WEEKLY_JSON = PROJECT_ROOT / 'data' / 'picks' / 'weekly_picks.json'
MONTHLY_JSON = PROJECT_ROOT / 'data' / 'picks' / 'monthly_picks.json'
AUDIT_JSON = PROJECT_ROOT / 'data' / 'picks' / 'picks_audit.json'

# Default DB path
DEFAULT_DB = PROJECT_ROOT / 'data' / 'picks.db'


class PicksLoader:
    """Load picks data into DB or JSON with atomic writes and audit trail."""
    
    def __init__(self, db_path: str = None, use_json_fallback: bool = False):
        """
        Initialize loader.
        
        Args:
            db_path: Path to SQLite database (optional)
            use_json_fallback: If True, use JSON files instead of DB
        """
        self.db_path = Path(db_path) if db_path else DEFAULT_DB
        self.use_json_fallback = use_json_fallback
        
        if not use_json_fallback:
            self._ensure_db_schema()
        else:
            self._ensure_json_dirs()
    
    def _ensure_db_schema(self):
        """Run migrations to ensure DB schema exists."""
        migration_file = PROJECT_ROOT / 'migrations' / '0002_create_picks_tables.sql'
        
        if not migration_file.exists():
            print(f"⚠️  Migration file not found: {migration_file}")
            return
        
        # Create DB directory if needed
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Run migration
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(migration_sql)
            conn.commit()
            print(f"✅ Database schema initialized: {self.db_path}")
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise
        finally:
            conn.close()
    
    def _ensure_json_dirs(self):
        """Ensure JSON fallback directories exist."""
        for json_path in [WEEKLY_JSON, MONTHLY_JSON, AUDIT_JSON]:
            json_path.parent.mkdir(parents=True, exist_ok=True)
    
    def load_csv_to_db(
        self,
        csv_path: str,
        pick_type: str,
        pick_date_or_month: str = None,
        uploader: str = 'system'
    ) -> int:
        """
        Load CSV into database table.
        
        Args:
            csv_path: Path to CSV file
            pick_type: 'weekly' or 'monthly'
            pick_date_or_month: Pick date (YYYY-MM-DD) or month (YYYY-MM)
            uploader: User/system that uploaded the data
            
        Returns:
            Number of rows loaded
        """
        # Load CSV
        fetcher = PicksFetcher()
        df = fetcher.load_from_csv(csv_path)
        
        if df.empty:
            print(f"⚠️  CSV is empty: {csv_path}")
            return 0
        
        # Auto-detect pick_date_or_month if not provided
        if not pick_date_or_month:
            pick_date_or_month = date.today().isoformat()
            if pick_type == 'monthly':
                pick_date_or_month = pick_date_or_month[:7]  # YYYY-MM
        
        # Add pick date/month column
        date_col = 'pick_date' if pick_type == 'weekly' else 'pick_month'
        df[date_col] = pick_date_or_month
        
        # Normalize column names (CSV may have different casing)
        column_mapping = {
            'ticker': 'ticker',
            'Ticker': 'ticker',
            'TICKER': 'ticker',
            'Company': 'company',
            'company': 'company',
            'Rank': 'rank',
            'rank': 'rank',
            'Score': 'score',
            'score': 'score',
            'Sector': 'sector',
            'sector': 'sector',
            'Market Cap': 'market_cap',
            'MarketCap': 'market_cap',
            'market_cap': 'market_cap',
            'Recommendation': 'recommendation',
            'recommendation': 'recommendation',
            'Target Price': 'target_price',
            'TargetPrice': 'target_price',
            'target_price': 'target_price'
        }
        
        df.rename(columns=column_mapping, inplace=True)
        
        # Select only DB columns
        db_columns = [
            'ticker', 'company', 'rank', 'score', 'sector',
            'market_cap', 'recommendation', 'target_price', date_col
        ]
        df_db = df[[col for col in db_columns if col in df.columns]]
        
        # Insert into DB
        table_name = f"{pick_type}_picks"
        conn = sqlite3.connect(self.db_path)
        
        try:
            # Delete existing records for this date/month
            conn.execute(f"DELETE FROM {table_name} WHERE {date_col} = ?", (pick_date_or_month,))
            
            # Insert new records
            df_db.to_sql(table_name, conn, if_exists='append', index=False)
            
            # Log audit entry
            audit_entry = {
                'pick_type': pick_type,
                'action': 'load',
                'source': 'csv',
                'record_count': len(df_db),
                'uploader': uploader,
                'details': json.dumps({
                    'csv_path': str(csv_path),
                    date_col: pick_date_or_month,
                    'columns': list(df_db.columns)
                })
            }
            
            audit_df = pd.DataFrame([audit_entry])
            audit_df.to_sql('picks_audit', conn, if_exists='append', index=False)
            
            conn.commit()
            print(f"✅ Loaded {len(df_db)} {pick_type} picks into DB for {pick_date_or_month}")
            
            return len(df_db)
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Failed to load into DB: {e}")
            raise
        finally:
            conn.close()
    
    def load_csv_to_json(
        self,
        csv_path: str,
        pick_type: str,
        pick_date_or_month: str = None,
        uploader: str = 'system'
    ) -> int:
        """
        Load CSV into JSON fallback file.
        
        Args:
            csv_path: Path to CSV file
            pick_type: 'weekly' or 'monthly'
            pick_date_or_month: Pick date or month
            uploader: User/system that uploaded
            
        Returns:
            Number of rows loaded
        """
        # Load CSV
        fetcher = PicksFetcher()
        df = fetcher.load_from_csv(csv_path)
        
        if df.empty:
            print(f"⚠️  CSV is empty: {csv_path}")
            return 0
        
        # Auto-detect date/month
        if not pick_date_or_month:
            pick_date_or_month = date.today().isoformat()
            if pick_type == 'monthly':
                pick_date_or_month = pick_date_or_month[:7]
        
        # Convert to JSON-serializable format
        records = df.to_dict('records')
        
        # Clean NaN values
        for record in records:
            for key, value in list(record.items()):
                if pd.isna(value):
                    record[key] = None
        
        # Prepare data structure
        data = {
            'pick_type': pick_type,
            'pick_date' if pick_type == 'weekly' else 'pick_month': pick_date_or_month,
            'loaded_at': datetime.now().isoformat(),
            'source': 'csv',
            'source_path': str(csv_path),
            'record_count': len(records),
            'data': records
        }
        
        # Determine output path
        json_path = WEEKLY_JSON if pick_type == 'weekly' else MONTHLY_JSON
        
        # Atomic write
        temp_path = json_path.with_suffix('.json.tmp')
        with open(temp_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        temp_path.replace(json_path)
        
        # Audit log
        self._append_audit_json(pick_type, 'load', 'csv', len(records), uploader, {
            'csv_path': str(csv_path),
            'pick_date_or_month': pick_date_or_month
        })
        
        print(f"✅ Loaded {len(records)} {pick_type} picks into JSON: {json_path}")
        return len(records)
    
    def _append_audit_json(
        self,
        pick_type: str,
        action: str,
        source: str,
        record_count: int,
        uploader: str,
        details: dict
    ):
        """Append audit entry to JSON audit log."""
        # Load existing audit log
        if AUDIT_JSON.exists():
            with open(AUDIT_JSON, 'r') as f:
                audit_log = json.load(f)
        else:
            audit_log = []
        
        # Append new entry
        audit_log.append({
            'pick_type': pick_type,
            'action': action,
            'source': source,
            'record_count': record_count,
            'uploader': uploader,
            'details': details,
            'created_at': datetime.now().isoformat()
        })
        
        # Atomic write
        temp_path = AUDIT_JSON.with_suffix('.json.tmp')
        with open(temp_path, 'w') as f:
            json.dump(audit_log, f, indent=2)
        
        temp_path.replace(AUDIT_JSON)
    
    def load_csv(
        self,
        csv_path: str,
        pick_type: str,
        pick_date_or_month: str = None,
        uploader: str = 'system'
    ) -> int:
        """
        Load CSV using DB or JSON based on configuration.
        
        Args:
            csv_path: Path to CSV
            pick_type: 'weekly' or 'monthly'
            pick_date_or_month: Date or month
            uploader: Uploader name
            
        Returns:
            Number of records loaded
        """
        if self.use_json_fallback:
            return self.load_csv_to_json(csv_path, pick_type, pick_date_or_month, uploader)
        else:
            return self.load_csv_to_db(csv_path, pick_type, pick_date_or_month, uploader)


def main():
    parser = argparse.ArgumentParser(description='Load picks data from CSV')
    parser.add_argument('--type', choices=['weekly', 'monthly'], required=True,
                        help='Type of picks (weekly or monthly)')
    parser.add_argument('--csv', help='Path to CSV file (not required for --fixture mode)')
    parser.add_argument('--date', help='Pick date (YYYY-MM-DD) or month (YYYY-MM)')
    parser.add_argument('--db', help='Path to SQLite database (default: data/picks.db)')
    parser.add_argument('--json', action='store_true', help='Use JSON fallback instead of DB')
    parser.add_argument('--fixture', action='store_true', help='Create deterministic fixture')
    parser.add_argument('--uploader', default='cli', help='Name of uploader (default: cli)')
    
    args = parser.parse_args()
    
    # Create fixture mode
    if args.fixture:
        fixture_dir = PROJECT_ROOT / 'reports' / 'picks' / 'fixtures'
        fixture_dir.mkdir(parents=True, exist_ok=True)
        
        fixture_path = fixture_dir / f'{args.type}_fixture.json'
        create_deterministic_fixture(
            output_path=str(fixture_path),
            pick_type=args.type,
            num_picks=20 if args.type == 'weekly' else 20
        )
        print(f"✅ Created deterministic fixture: {fixture_path}")
        return
    
    # Validate CSV exists (required when not in fixture mode)
    if not args.csv:
        print("❌ --csv argument is required when not using --fixture mode")
        sys.exit(1)
    
    if not os.path.exists(args.csv):
        print(f"❌ CSV file not found: {args.csv}")
        sys.exit(1)
    
    # Load data
    loader = PicksLoader(db_path=args.db, use_json_fallback=args.json)
    
    try:
        count = loader.load_csv(
            csv_path=args.csv,
            pick_type=args.type,
            pick_date_or_month=args.date,
            uploader=args.uploader
        )
        
        print(f"\n🎉 Successfully loaded {count} {args.type} picks")
        
    except Exception as e:
        print(f"\n❌ Failed to load picks: {e}")
        sys.exit(1)


def load_canonical_source(run_type: str, deterministic: bool = None) -> pd.DataFrame:
    """
    Load canonical source data for pipeline runs (STEP 1 of picks pipeline).
    
    Args:
        run_type: 'weekly' or 'monthly'
        deterministic: If True or env OPTIONS_DETERMINISTIC=1, use fixtures
        
    Returns:
        DataFrame with source data
        
    Loading order:
        1. If deterministic mode: load from fixtures
        2. Canonical CSV: data/picks_input/<type>_source.csv
        3. Fallback published: data/picks/<type>_picks.json
        4. Fallback outputs: financial_dashboard/outputs/market_brief.json
        5. Empty DataFrame if all fail
    """
    import json
    
    if deterministic is None:
        deterministic = os.environ.get('OPTIONS_DETERMINISTIC', '0') == '1'
    
    CANONICAL_INPUT_DIR = PROJECT_ROOT / 'data' / 'picks_input'
    FIXTURES_DIR = PROJECT_ROOT / 'reports' / 'picks' / 'fixtures'
    OUTPUTS_DIR = PROJECT_ROOT / 'financial_dashboard' / 'outputs'
    
    CANONICAL_INPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
    
    # Mode 1: Deterministic fixture
    if deterministic:
        fixture_path = FIXTURES_DIR / f'{run_type}_fixture.json'
        if fixture_path.exists():
            print(f"[DETERMINISTIC MODE] Loading fixture: {fixture_path}")
            with open(fixture_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Handle both array and dict formats
            if isinstance(data, dict):
                records = data.get('picks') or data.get('selected') or data.get('detailed', [])
            else:
                records = data
            
            if records:
                df = pd.DataFrame(records)
                print(f"  Loaded {len(df)} rows from fixture")
                return df
    
    # Mode 2: Canonical CSV
    canonical_csv = CANONICAL_INPUT_DIR / f'{run_type}_source.csv'
    if canonical_csv.exists():
        print(f"Loading canonical CSV: {canonical_csv}")
        df = pd.read_csv(canonical_csv)
        print(f"  Loaded {len(df)} rows")
        return df
    
    # Mode 3: Fallback published JSON
    published_json = PROJECT_ROOT / 'data' / 'picks' / f'{run_type}_picks.json'
    if published_json.exists():
        print(f"Loading fallback: {published_json}")
        with open(published_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, dict):
            records = data.get('picks') or data.get('selected') or data.get('data', [])
        else:
            records = data
        
        if records:
            df = pd.DataFrame(records)
            print(f"  Loaded {len(df)} rows")
            return df
    
    # Mode 4: market_brief.json
    market_brief = OUTPUTS_DIR / 'market_brief.json'
    if market_brief.exists():
        print(f"Loading fallback: {market_brief}")
        with open(market_brief, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        detailed = data.get('detailed', [])
        if detailed:
            df = pd.DataFrame(detailed)
            print(f"  Loaded {len(df)} rows from market_brief")
            return df
    
    print(f"WARNING: No source data found for {run_type}")
    return pd.DataFrame()


if __name__ == '__main__':
    main()
