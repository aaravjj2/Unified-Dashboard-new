"""
Migration script to load historical picks data from CSV files into PostgreSQL.
Parses all picks_*.csv files from models/ directories and populates picks_history table.
"""
import os
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.db_utils import (
    initialize_pg_pool,
    execute_pg_many,
    create_picks_history_table,
    close_pg_pool
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def parse_date_from_filename(filename):
    """
    Extract date from picks filename.
    
    Examples:
        picks_20251001.csv -> 2025-10-01
        picks_20251012.csv -> 2025-10-12
    """
    try:
        # Extract YYYYMMDD from filename
        date_str = filename.replace('picks_', '').replace('.csv', '')
        return datetime.strptime(date_str, '%Y%m%d').date()
    except Exception as e:
        logger.error(f"Could not parse date from filename {filename}: {e}")
        return None


def determine_pick_type(file_path):
    """
    Determine if picks are monthly or weekly based on directory.
    
    Args:
        file_path: Path object to CSV file
    
    Returns:
        'monthly' or 'weekly'
    """
    path_str = str(file_path)
    if 'weekly_run' in path_str or 'weekly' in path_str:
        return 'weekly'
    elif 'full_run' in path_str or 'monthly' in path_str:
        return 'monthly'
    else:
        # Default to monthly if can't determine
        logger.warning(f"Could not determine pick type for {path_str}, defaulting to monthly")
        return 'monthly'


def load_csv_to_db(csv_file, pick_date, pick_type):
    """
    Load a single CSV file into the picks_history table.
    
    Args:
        csv_file: Path to CSV file
        pick_date: Date of picks
        pick_type: 'monthly' or 'weekly'
    
    Returns:
        Number of rows inserted
    """
    try:
        df = pd.read_csv(csv_file)
        
        # Required column: ticker (handle various naming conventions)
        ticker_col = None
        for col in ['ticker', 'Ticker', 'symbol', 'Symbol', 'TICKER']:
            if col in df.columns:
                ticker_col = col
                break
        
        if ticker_col is None:
            logger.error(f"No ticker column found in {csv_file}")
            return 0
        
        # Optional columns with fallback defaults
        predicted_return_col = None
        for col in ['predicted_return', 'return', 'expected_return', 'pred_return']:
            if col in df.columns:
                predicted_return_col = col
                break
        
        confidence_col = None
        for col in ['confidence', 'score', 'probability']:
            if col in df.columns:
                confidence_col = col
                break
        
        sector_col = None
        for col in ['sector', 'Sector', 'industry']:
            if col in df.columns:
                sector_col = col
                break
        
        market_cap_col = None
        for col in ['market_cap', 'marketcap', 'mktcap']:
            if col in df.columns:
                market_cap_col = col
                break
        
        # Build parameter list for bulk insert
        params_list = []
        for _, row in df.iterrows():
            ticker = str(row[ticker_col]).strip().upper()
            
            # Skip invalid tickers
            if not ticker or ticker == 'NAN' or len(ticker) > 20:
                continue
            
            predicted_return = float(row[predicted_return_col]) if predicted_return_col and pd.notna(row[predicted_return_col]) else None
            confidence = float(row[confidence_col]) if confidence_col and pd.notna(row[confidence_col]) else None
            sector = str(row[sector_col]) if sector_col and pd.notna(row[sector_col]) else None
            market_cap = float(row[market_cap_col]) if market_cap_col and pd.notna(row[market_cap_col]) else None
            
            params_list.append((
                ticker,
                pick_date,
                pick_type,
                predicted_return,
                confidence,
                sector,
                market_cap
            ))
        
        if not params_list:
            logger.warning(f"No valid rows to insert from {csv_file}")
            return 0
        
        # Insert into database (ON CONFLICT DO NOTHING to handle duplicates)
        insert_query = """
        INSERT INTO picks_history (ticker, pick_date, pick_type, predicted_return, confidence, sector, market_cap)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (ticker, pick_date, pick_type) DO NOTHING
        """
        
        execute_pg_many(insert_query, params_list)
        logger.info(f"Inserted {len(params_list)} rows from {csv_file.name} ({pick_type}, {pick_date})")
        return len(params_list)
        
    except Exception as e:
        logger.error(f"Error loading {csv_file}: {e}")
        return 0


def migrate_all_picks():
    """
    Find and migrate all picks_*.csv files from models/ directories.
    """
    logger.info("=" * 60)
    logger.info("Starting picks migration to PostgreSQL")
    logger.info("=" * 60)
    
    # Initialize database
    try:
        initialize_pg_pool()
        create_picks_history_table()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return
    
    # Find all picks CSV files
    base_dir = Path(__file__).parent.parent / 'models'
    
    if not base_dir.exists():
        logger.error(f"Models directory not found: {base_dir}")
        return
    
    csv_files = list(base_dir.rglob('picks_*.csv'))
    logger.info(f"Found {len(csv_files)} picks CSV files")
    
    if not csv_files:
        logger.warning("No picks CSV files found. Nothing to migrate.")
        return
    
    total_inserted = 0
    total_files = 0
    
    for csv_file in sorted(csv_files):
        pick_date = parse_date_from_filename(csv_file.name)
        if pick_date is None:
            logger.warning(f"Skipping {csv_file.name} - could not parse date")
            continue
        
        pick_type = determine_pick_type(csv_file)
        
        inserted = load_csv_to_db(csv_file, pick_date, pick_type)
        total_inserted += inserted
        total_files += 1
    
    logger.info("=" * 60)
    logger.info(f"Migration complete!")
    logger.info(f"  Files processed: {total_files}")
    logger.info(f"  Total rows inserted: {total_inserted}")
    logger.info("=" * 60)
    
    close_pg_pool()


if __name__ == "__main__":
    migrate_all_picks()
