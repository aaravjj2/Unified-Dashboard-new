"""
Dagster Data Pipeline for Unified Financial Dashboard
Scans CSV files from models directory and loads into postgres_db
"""
from dagster import asset, AssetExecutionContext, Definitions, Config
import pandas as pd
from sqlalchemy import create_engine, text
import glob
import os
from pathlib import Path
from datetime import datetime

POSTGRES_URI = "postgresql://postgres:postgres@postgres_db:5432/market_data"

# Mount point where financial_dashboard models directory is accessible
MODELS_DIR = "/app/models"


@asset
def scan_csv_files(context: AssetExecutionContext) -> dict:
    """
    Scan the models directory for picks CSV files.
    Returns paths to weekly and monthly picks files.
    """
    context.log.info(f"Scanning {MODELS_DIR} for picks CSV files...")
    
    # Find weekly picks
    weekly_patterns = [
        f"{MODELS_DIR}/weekly_run/picks_*.csv",
        f"{MODELS_DIR}/weekly_run/weeklypicks*.csv",
        f"{MODELS_DIR}/picks_*.csv"
    ]
    
    weekly_files = []
    for pattern in weekly_patterns:
        weekly_files.extend(glob.glob(pattern))
    
    # Find monthly picks  
    monthly_patterns = [
        f"{MODELS_DIR}/**/monthly_picks_*.csv",
        f"{MODELS_DIR}/**/monthlypicks*.csv"
    ]
    
    monthly_files = []
    for pattern in monthly_patterns:
        monthly_files.extend(glob.glob(pattern, recursive=True))
    
    context.log.info(f"Found {len(weekly_files)} weekly picks files")
    context.log.info(f"Found {len(monthly_files)} monthly picks files")
    
    # Get most recent of each
    if weekly_files:
        weekly_files.sort(key=os.path.getmtime, reverse=True)
        context.log.info(f"Most recent weekly: {weekly_files[0]}")
    
    if monthly_files:
        monthly_files.sort(key=os.path.getmtime, reverse=True)
        context.log.info(f"Most recent monthly: {monthly_files[0]}")
    
    return {
        'weekly_files': weekly_files,
        'monthly_files': monthly_files
    }


@asset(deps=[scan_csv_files])
def create_picks_table(context: AssetExecutionContext):
    """
    Create the picks table in postgres_db if it doesn't exist.
    """
    context.log.info("Creating picks table schema...")
    
    engine = create_engine(POSTGRES_URI)
    
    with engine.connect() as conn:
        # Create picks table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS picks (
                id SERIAL PRIMARY KEY,
                date DATE NOT NULL,
                ticker VARCHAR(20) NOT NULL,
                pick_type VARCHAR(20) NOT NULL,
                score FLOAT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, ticker, pick_type)
            );
        """))
        
        # Create index for faster queries
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_picks_date_type 
            ON picks(date, pick_type);
        """))
        
        conn.commit()
        
    context.log.info("Picks table created successfully")
    return True


@asset(deps=[scan_csv_files, create_picks_table])
def load_weekly_picks(context: AssetExecutionContext, scan_csv_files: dict) -> pd.DataFrame:
    """
    Load the most recent weekly picks CSV file.
    """
    weekly_files = scan_csv_files['weekly_files']
    
    if not weekly_files:
        context.log.warning("No weekly picks files found")
        return pd.DataFrame()
    
    # Load most recent file
    csv_path = weekly_files[0]
    context.log.info(f"Loading weekly picks from: {csv_path}")
    
    df = pd.read_csv(csv_path)
    context.log.info(f"Loaded {len(df)} weekly picks")
    context.log.info(f"Columns: {df.columns.tolist()}")
    
    # Add metadata
    if 'date' not in df.columns:
        # Try to extract date from filename
        filename = os.path.basename(csv_path)
        import re
        date_match = re.search(r'(\d{8})', filename)
        if date_match:
            date_str = date_match.group(1)
            df['date'] = pd.to_datetime(date_str, format='%Y%m%d')
        else:
            # Use file modification time
            df['date'] = pd.to_datetime(datetime.fromtimestamp(os.path.getmtime(csv_path)))
    
    df['pick_type'] = 'weekly'
    
    # Ensure required columns exist
    if 'ticker' not in df.columns:
        context.log.error("No ticker column found in weekly picks CSV")
        return pd.DataFrame()
    
    # Add score if missing
    if 'score' not in df.columns:
        df['score'] = None
    
    return df[['date', 'ticker', 'pick_type', 'score']]


@asset(deps=[load_weekly_picks])
def ingest_weekly_to_postgres(
    context: AssetExecutionContext, 
    load_weekly_picks: pd.DataFrame
):
    """
    Insert weekly picks into postgres_db picks table.
    """
    if load_weekly_picks.empty:
        context.log.warning("No weekly picks to ingest")
        return 0
    
    context.log.info(f"Ingesting {len(load_weekly_picks)} weekly picks to postgres_db...")
    
    engine = create_engine(POSTGRES_URI)
    
    # Use to_sql with if_exists='append' and on_conflict to handle duplicates
    # Since SQLAlchemy doesn't directly support ON CONFLICT, we'll do manual insert
    inserted_count = 0
    
    with engine.connect() as conn:
        for _, row in load_weekly_picks.iterrows():
            try:
                conn.execute(text("""
                    INSERT INTO picks (date, ticker, pick_type, score)
                    VALUES (:date, :ticker, :pick_type, :score)
                    ON CONFLICT (date, ticker, pick_type) DO NOTHING
                """), {
                    'date': row['date'],
                    'ticker': row['ticker'],
                    'pick_type': row['pick_type'],
                    'score': row['score'] if pd.notna(row['score']) else None
                })
                inserted_count += 1
            except Exception as e:
                context.log.warning(f"Failed to insert {row['ticker']}: {e}")
        
        conn.commit()
    
    context.log.info(f"PostgreSQL ingestion complete: {inserted_count} records inserted")
    return inserted_count


defs = Definitions(assets=[
    scan_csv_files,
    create_picks_table,
    load_weekly_picks,
    ingest_weekly_to_postgres
])
