#!/usr/bin/env python3
"""
Historical Picks Data Migration Script
=======================================
One-time migration script to transfer historical picks from CSV files
to the centralized PostgreSQL database.

Features:
- Scans Financial_Data/ for picks_*.csv files
- Parses CSV data and inserts into picks_history table
- Idempotent: safe to run multiple times (uses UPSERT logic)
- Progress tracking and error handling
- Dry-run mode for validation

Usage:
    python scripts/migrate_picks_to_db.py                    # Execute migration
    python scripts/migrate_picks_to_db.py --dry-run          # Preview without changes
    python scripts/migrate_picks_to_db.py --directory /path  # Custom CSV directory
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime
import pandas as pd
from typing import List, Dict, Any
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_utils import (
    initialize_postgres_pool,
    initialize_postgres_schema,
    get_postgres_connection,
    POSTGRES_AVAILABLE
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def find_picks_csv_files(directory: str) -> List[Path]:
    """
    Find all picks CSV files in the given directory.
    
    Args:
        directory: Path to search for CSV files
    
    Returns:
        List of Path objects for picks_*.csv files
    """
    search_path = Path(directory)
    if not search_path.exists():
        logger.error(f"Directory not found: {directory}")
        return []
    
    # Find all CSV files matching various picks patterns
    csv_files = []
    patterns = ["*picks*.csv", "picks_*.csv", "monthly_picks_*.csv", "weekly_picks_*.csv"]
    
    for pattern in patterns:
        csv_files.extend(search_path.rglob(pattern))
    
    # Remove duplicates
    csv_files = list(set(csv_files))
    
    logger.info(f"Found {len(csv_files)} picks CSV files in {directory}")
    return sorted(csv_files)


def parse_picks_csv(file_path: Path) -> List[Dict[str, Any]]:
    """
    Parse a picks CSV file and return list of records.
    
    Args:
        file_path: Path to CSV file
    
    Returns:
        List of dict records ready for database insertion
    """
    try:
        df = pd.read_csv(file_path)
        logger.info(f"Loaded {len(df)} records from {file_path.name}")
        
        # Standardize column names (case-insensitive)
        df.columns = df.columns.str.lower().str.strip()
        
        # Extract pick type from file path
        pick_type = 'unknown'
        if 'monthly' in str(file_path).lower():
            pick_type = 'monthly'
        elif 'weekly' in str(file_path).lower():
            pick_type = 'weekly'
        
        # Extract date from filename if not in CSV
        filename = file_path.stem
        pick_date = _extract_date_from_csv_or_filename(df, filename)
        
        # Build standardized records
        records = []
        for idx, row in df.iterrows():
            record = {
                'pick_date': row.get('date') or row.get('pick_date') or pick_date,
                'ticker': row.get('ticker') or row.get('symbol') or row.get('stock'),
                'price': _safe_float(row.get('price') or row.get('entry_price') or row.get('current_price')),
                'target_price': _safe_float(row.get('target') or row.get('target_price')),
                'stop_loss': _safe_float(row.get('stop') or row.get('stop_loss')),
                'sector': row.get('sector') or row.get('industry'),
                'catalyst': row.get('catalyst') or row.get('thesis') or row.get('rationale'),
                'timeframe': row.get('timeframe') or row.get('horizon') or pick_type,
                'risk_level': row.get('risk') or row.get('risk_level') or 'medium',
                'confidence': _safe_float(row.get('confidence') or row.get('score')),
                'metadata': _extract_metadata(row, pick_type)
            }
            
            # Validate required fields
            if not record['pick_date'] or not record['ticker']:
                logger.warning(f"Skipping row {idx}: missing required fields (date={record['pick_date']}, ticker={record['ticker']})")
                continue
            
            records.append(record)
        
        logger.info(f"✓ Parsed {len(records)} valid records from {file_path.name}")
        return records
        
    except Exception as e:
        logger.error(f"Error parsing {file_path.name}: {e}")
        import traceback
        traceback.print_exc()
        return []


def _extract_date_from_csv_or_filename(df: pd.DataFrame, filename: str) -> str:
    """Extract date from CSV data or filename."""
    # Check if date exists in first row
    if 'date' in df.columns and len(df) > 0:
        return str(df['date'].iloc[0])
    if 'pick_date' in df.columns and len(df) > 0:
        return str(df['pick_date'].iloc[0])
    
    # Try to parse date from filename
    # Pattern: picks_2024_01_15.csv or monthly_picks_2024_01.csv
    parts = filename.split('_')
    date_parts = [p for p in parts if p.isdigit() and len(p) <= 4]
    
    if len(date_parts) >= 3:
        year, month, day = date_parts[:3]
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    elif len(date_parts) == 2:
        year, month = date_parts
        return f"{year}-{month.zfill(2)}-01"
    
    # Default to today if no date found
    logger.warning(f"Could not extract date from {filename}, using today")
    return datetime.now().strftime('%Y-%m-%d')


def _safe_float(value) -> float:
    """Safely convert value to float, returning None if not possible."""
    if value is None or value == '' or pd.isna(value):
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _extract_metadata(row: pd.Series, pick_type: str) -> str:
    """Extract additional metadata from row into JSON string."""
    metadata = {'pick_type': pick_type}
    
    # List of standard columns to exclude from metadata
    standard_cols = {
        'date', 'pick_date', 'ticker', 'symbol', 'stock', 
        'price', 'entry_price', 'current_price', 'target', 'target_price',
        'stop', 'stop_loss', 'sector', 'industry',
        'catalyst', 'thesis', 'rationale', 'timeframe', 
        'horizon', 'risk', 'risk_level', 'confidence', 'score'
    }
    
    for col, val in row.items():
        if col.lower() not in standard_cols and pd.notna(val):
            metadata[col] = str(val)
    
    return json.dumps(metadata) if len(metadata) > 1 else None


def insert_picks_to_db(records: List[Dict[str, Any]], dry_run: bool = False) -> int:
    """
    Insert picks records into PostgreSQL database.
    Uses UPSERT logic (ON CONFLICT DO UPDATE) for idempotency.
    
    Args:
        records: List of pick records to insert
        dry_run: If True, only log what would be inserted without executing
    
    Returns:
        Number of records inserted/updated
    """
    if not POSTGRES_AVAILABLE:
        logger.error("PostgreSQL not available - cannot migrate data")
        return 0
    
    if dry_run:
        logger.info(f"[DRY RUN] Would insert {len(records)} records")
        for i, record in enumerate(records[:5], 1):
            logger.info(f"  {i}. {record['pick_date']}: {record['ticker']} @ ${record['price']}")
        if len(records) > 5:
            logger.info(f"  ... and {len(records) - 5} more")
        return len(records)
    
    try:
        with get_postgres_connection() as conn:
            cursor = conn.cursor()
            
            inserted_count = 0
            for record in records:
                try:
                    # UPSERT: Insert or update on conflict
                    cursor.execute('''
                        INSERT INTO picks_history (
                            pick_date, ticker, price, target_price, stop_loss,
                            sector, catalyst, timeframe, risk_level, confidence, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (pick_date, ticker) 
                        DO UPDATE SET
                            price = EXCLUDED.price,
                            target_price = EXCLUDED.target_price,
                            stop_loss = EXCLUDED.stop_loss,
                            sector = EXCLUDED.sector,
                            catalyst = EXCLUDED.catalyst,
                            timeframe = EXCLUDED.timeframe,
                            risk_level = EXCLUDED.risk_level,
                            confidence = EXCLUDED.confidence,
                            metadata = EXCLUDED.metadata
                    ''', (
                        record['pick_date'],
                        record['ticker'],
                        record['price'],
                        record['target_price'],
                        record['stop_loss'],
                        record['sector'],
                        record['catalyst'],
                        record['timeframe'],
                        record['risk_level'],
                        record['confidence'],
                        record['metadata']
                    ))
                    inserted_count += 1
                    
                except Exception as e:
                    logger.error(f"Error inserting record {record.get('ticker', 'UNKNOWN')}: {e}")
                    continue
            
            conn.commit()
            logger.info(f"✓ Inserted/updated {inserted_count} records in picks_history table")
            return inserted_count
            
    except Exception as e:
        logger.error(f"Database error during migration: {e}")
        import traceback
        traceback.print_exc()
        return 0


def migrate_picks_data(csv_directory: str, dry_run: bool = False) -> Dict[str, Any]:
    """
    Main migration function: scan CSV files and migrate to database.
    
    Args:
        csv_directory: Directory containing picks CSV files
        dry_run: If True, preview without making changes
    
    Returns:
        Dict with migration summary statistics
    """
    logger.info("="*70)
    logger.info("HISTORICAL PICKS DATA MIGRATION")
    logger.info("="*70)
    
    if dry_run:
        logger.info("🔍 DRY RUN MODE - No database changes will be made")
    
    # Step 1: Initialize database
    if not dry_run:
        logger.info("Step 1: Initializing PostgreSQL connection and schema...")
        if not initialize_postgres_pool():
            logger.error("Failed to initialize PostgreSQL connection pool")
            return {'success': False, 'error': 'Database connection failed'}
        
        if not initialize_postgres_schema():
            logger.error("Failed to initialize PostgreSQL schema")
            return {'success': False, 'error': 'Schema initialization failed'}
        
        logger.info("✓ Database initialized")
    
    # Step 2: Find CSV files
    logger.info(f"Step 2: Scanning {csv_directory} for picks CSV files...")
    csv_files = find_picks_csv_files(csv_directory)
    
    if not csv_files:
        logger.warning("No CSV files found to migrate")
        return {
            'success': True,
            'files_found': 0,
            'records_migrated': 0,
            'message': 'No CSV files found'
        }
    
    # Step 3: Parse and migrate each file
    logger.info(f"Step 3: Parsing and migrating {len(csv_files)} files...")
    
    total_records = 0
    migrated_records = 0
    
    for csv_file in csv_files:
        logger.info(f"Processing: {csv_file.name}")
        records = parse_picks_csv(csv_file)
        total_records += len(records)
        
        if records:
            count = insert_picks_to_db(records, dry_run=dry_run)
            migrated_records += count
    
    # Step 4: Summary
    logger.info("="*70)
    logger.info("MIGRATION COMPLETE")
    logger.info("="*70)
    logger.info(f"Files processed: {len(csv_files)}")
    logger.info(f"Total records found: {total_records}")
    logger.info(f"Records migrated: {migrated_records}")
    
    if dry_run:
        logger.info("\n🔍 This was a DRY RUN - no data was actually inserted")
        logger.info("Run without --dry-run flag to execute the migration")
    else:
        logger.info("\n✓ Migration successful!")
    
    return {
        'success': True,
        'files_found': len(csv_files),
        'total_records': total_records,
        'records_migrated': migrated_records,
        'dry_run': dry_run
    }


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Migrate historical picks data from CSV to PostgreSQL'
    )
    parser.add_argument(
        '--directory',
        default='Financial_Data',
        help='Directory containing picks CSV files (default: Financial_Data)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview migration without making database changes'
    )
    
    args = parser.parse_args()
    
    # Resolve directory path relative to project root
    project_root = Path(__file__).parent.parent
    csv_dir = project_root / args.directory
    
    if not csv_dir.exists():
        logger.error(f"Directory not found: {csv_dir}")
        sys.exit(1)
    
    # Run migration
    result = migrate_picks_data(str(csv_dir), dry_run=args.dry_run)
    
    # Exit with appropriate code
    sys.exit(0 if result['success'] else 1)


if __name__ == '__main__':
    main()
