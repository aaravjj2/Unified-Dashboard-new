"""
Picks Fetcher - Data ingestion and enrichment for Weekly and Monthly Picks

Provides deterministic data loading with price provenance and robust fallbacks.

Features:
- Load from CSV, DB, or deterministic fixtures
- Price enrichment with yfinance fallback
- Provenance tracking (source, timestamp)
- Thread-safe operations
- Comprehensive error handling

Author: Agent-1B
Created: 2025-11-21
"""

import os
import json
import logging
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
import threading

logger = logging.getLogger(__name__)

# Thread lock for concurrent fetcher operations
_fetcher_lock = threading.RLock()


def is_deterministic_mode() -> bool:
    """Check if deterministic mode is enabled (re-reads env var each time)."""
    return os.environ.get('OPTIONS_DETERMINISTIC', '0') == '1'


class PicksFetcher:
    """
    Manages loading and enriching pick data from multiple sources.
    
    Supports:
    - CSV files
    - Database tables
    - Deterministic fixtures (for testing)
    - Price enrichment with provenance
    """
    
    def __init__(self, fixture_path: Optional[str] = None, price_client=None):
        """
        Initialize PicksFetcher.
        
        Args:
            fixture_path: Path to deterministic fixture JSON (optional)
            price_client: Price client instance for enrichment (optional, will use fallback)
        """
        self.fixture_path = fixture_path
        self.price_client = price_client
        self._cache = {}
        self._lock = threading.RLock()
        
        logger.info(f"PicksFetcher initialized (deterministic={is_deterministic_mode()})")
    
    def load_from_csv(self, csv_path: str, required_columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Load picks from CSV file with validation.
        
        Args:
            csv_path: Path to CSV file
            required_columns: List of required column names (optional)
            
        Returns:
            DataFrame with picks data
            
        Raises:
            FileNotFoundError: If CSV doesn't exist
            ValueError: If required columns are missing
        """
        with self._lock:
            if not os.path.exists(csv_path):
                logger.error(f"CSV file not found: {csv_path}")
                raise FileNotFoundError(f"CSV not found: {csv_path}")
            
            try:
                df = pd.read_csv(csv_path)
                logger.info(f"Loaded {len(df)} rows from CSV: {csv_path}")
                
                # Validate required columns
                if required_columns:
                    missing = set(required_columns) - set(df.columns)
                    if missing:
                        raise ValueError(f"Missing required columns: {missing}")
                
                # Add data provenance
                df['_source'] = 'csv'
                df['_source_path'] = csv_path
                df['_loaded_at'] = datetime.now(timezone.utc).isoformat()
                
                return df
                
            except pd.errors.EmptyDataError:
                logger.warning(f"CSV file is empty: {csv_path}")
                return pd.DataFrame()
            except Exception as e:
                logger.error(f"Failed to load CSV {csv_path}: {e}")
                raise
    
    def load_from_db(self, table_name: str, db_connection=None, limit: Optional[int] = None) -> pd.DataFrame:
        """
        Load picks from database table.
        
        Args:
            table_name: Name of database table
            db_connection: Database connection object (optional, uses default)
            limit: Optional row limit
            
        Returns:
            DataFrame with picks data
        """
        with self._lock:
            try:
                # Import DB utils dynamically to avoid circular dependency
                from utils import db_utils
                
                query = f"SELECT * FROM {table_name}"
                if limit:
                    query += f" LIMIT {limit}"
                
                conn = db_connection or db_utils.get_connection()
                df = pd.read_sql_query(query, conn)
                
                logger.info(f"Loaded {len(df)} rows from DB table: {table_name}")
                
                # Add data provenance
                df['_source'] = 'database'
                df['_source_table'] = table_name
                df['_loaded_at'] = datetime.now(timezone.utc).isoformat()
                
                return df
                
            except Exception as e:
                logger.error(f"Failed to load from DB table {table_name}: {e}")
                # Return empty DataFrame rather than raising
                return pd.DataFrame()
    
    def load_from_fixture(self, fixture_path: Optional[str] = None) -> pd.DataFrame:
        """
        Load deterministic fixture data for testing.
        
        Args:
            fixture_path: Path to fixture JSON (uses self.fixture_path if not provided)
            
        Returns:
            DataFrame with fixture data
        """
        with self._lock:
            path = fixture_path or self.fixture_path
            
            if not path or not os.path.exists(path):
                logger.warning(f"Fixture not found: {path}")
                return pd.DataFrame()
            
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
                
                # Handle both list-of-records and dict-with-records formats
                if isinstance(data, dict) and 'data' in data:
                    records = data['data']
                elif isinstance(data, list):
                    records = data
                else:
                    records = [data]
                
                df = pd.DataFrame(records)
                logger.info(f"Loaded {len(df)} rows from fixture: {path}")
                
                # Add data provenance
                df['_source'] = 'fixture'
                df['_source_path'] = path
                df['_loaded_at'] = datetime.now(timezone.utc).isoformat()
                
                return df
                
            except Exception as e:
                logger.error(f"Failed to load fixture {path}: {e}")
                return pd.DataFrame()
    
    def enrich_with_prices(
        self,
        picks_df: pd.DataFrame,
        ticker_column: str = 'Ticker',
        provenance: bool = True
    ) -> pd.DataFrame:
        """
        Enrich picks DataFrame with current prices and provenance.
        
        Args:
            picks_df: DataFrame containing picks
            ticker_column: Name of ticker column (default 'Ticker')
            provenance: Whether to add price provenance columns (default True)
            
        Returns:
            DataFrame with added price columns:
            - current_price: Latest price
            - price_source: Data source (e.g., 'yfinance', 'alpaca', 'cache')
            - price_fetched_at: ISO timestamp of price fetch
            - price_age_seconds: Age of price data
        """
        with self._lock:
            if picks_df.empty:
                logger.warning("Cannot enrich empty DataFrame")
                return picks_df

            # Normalize column names and attempt to find the ticker column case-insensitively
            cols = list(picks_df.columns)
            cols_lower = {c.lower(): c for c in cols}
            if ticker_column not in cols:
                # Try case-insensitive match
                if ticker_column.lower() in cols_lower:
                    actual_col = cols_lower[ticker_column.lower()]
                    logger.info(f"Mapping ticker column '{actual_col}' -> '{ticker_column}' (case-insensitive)")
                    picks_df = picks_df.rename(columns={actual_col: ticker_column})
                else:
                    # Try common alternatives
                    for alt in ('ticker', 'symbol', 'ticker_symbol'):
                        if alt in cols_lower:
                            actual_col = cols_lower[alt]
                            logger.info(f"Mapping ticker column '{actual_col}' -> '{ticker_column}' (fallback)")
                            picks_df = picks_df.rename(columns={actual_col: ticker_column})
                            break

            if ticker_column not in picks_df.columns:
                logger.error(f"Ticker column '{ticker_column}' not found in DataFrame")
                return picks_df
            
            enriched = picks_df.copy()
            
            # Initialize price columns
            enriched['current_price'] = None
            if provenance:
                enriched['price_source'] = None
                enriched['price_fetched_at'] = None
                enriched['price_age_seconds'] = None
            
            tickers = enriched[ticker_column].dropna().unique()
            logger.info(f"Enriching {len(tickers)} tickers with prices")
            
            for ticker in tickers:
                try:
                    price_data = self._fetch_price_with_provenance(ticker)
                    
                    if price_data:
                        mask = enriched[ticker_column] == ticker
                        enriched.loc[mask, 'current_price'] = price_data.get('price')
                        
                        if provenance:
                            enriched.loc[mask, 'price_source'] = price_data.get('source')
                            enriched.loc[mask, 'price_fetched_at'] = price_data.get('fetched_at')
                            enriched.loc[mask, 'price_age_seconds'] = price_data.get('age_seconds', 0)
                    else:
                        logger.warning(f"No price data for {ticker}")
                        
                except Exception as e:
                    logger.error(f"Failed to fetch price for {ticker}: {e}")
                    continue
            
            successful = enriched['current_price'].notna().sum()
            logger.info(f"Successfully enriched {successful}/{len(enriched)} rows with prices")
            
            return enriched
    
    def _fetch_price_with_provenance(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Fetch price with full provenance tracking.
        
        Priority order:
        1. price_client (if provided)
        2. yfinance fallback
        3. Deterministic fixtures (if enabled)
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dict with keys: price, source, fetched_at, age_seconds
        """
        fetched_at = datetime.now(timezone.utc).isoformat()
        
        # DETERMINISTIC MODE: return synthetic prices
        if is_deterministic_mode():
            synthetic_price = 100.0 + (hash(ticker) % 100)  # Deterministic pseudo-random
            return {
                'price': synthetic_price,
                'source': 'deterministic_fixture',
                'fetched_at': fetched_at,
                'age_seconds': 0
            }
        
        # Try price_client if available
        if self.price_client:
            try:
                price = self.price_client.get_current_price(ticker)
                if price:
                    return {
                        'price': price,
                        'source': 'price_client',
                        'fetched_at': fetched_at,
                        'age_seconds': 0
                    }
            except Exception as e:
                logger.warning(f"Price client failed for {ticker}: {e}")
        
        # Fallback to yfinance
        try:
            import yfinance as yf
            
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            
            # Try multiple price fields
            price = (
                info.get('regularMarketPrice') or
                info.get('currentPrice') or
                info.get('previousClose')
            )
            
            if price:
                return {
                    'price': float(price),
                    'source': 'yfinance',
                    'fetched_at': fetched_at,
                    'age_seconds': 0
                }
            else:
                logger.warning(f"No price found in yfinance for {ticker}")
                
        except Exception as e:
            logger.error(f"yfinance fallback failed for {ticker}: {e}")
        
        return None
    
    def load_picks(
        self,
        source_type: str = 'auto',
        csv_path: Optional[str] = None,
        db_table: Optional[str] = None,
        fixture_path: Optional[str] = None
    ) -> pd.DataFrame:
        """
        Load picks from specified source with automatic fallback.
        
        Args:
            source_type: 'csv', 'db', 'fixture', or 'auto' (default)
            csv_path: Path to CSV file (for source_type='csv')
            db_table: Database table name (for source_type='db')
            fixture_path: Path to fixture (for source_type='fixture')
            
        Returns:
            DataFrame with picks data
        """
        with self._lock:
            # Auto-detect source or use deterministic mode
            if is_deterministic_mode() or source_type == 'fixture':
                return self.load_from_fixture(fixture_path)
            
            if source_type == 'csv' and csv_path:
                return self.load_from_csv(csv_path)
            
            if source_type == 'db' and db_table:
                return self.load_from_db(db_table)
            
            # Auto fallback: try DB, then CSV, then fixture
            if source_type == 'auto':
                logger.info("Auto-loading picks (trying DB → CSV → fixture)")
                
                # Try DB first
                if db_table:
                    df = self.load_from_db(db_table)
                    if not df.empty:
                        return df
                
                # Try CSV
                if csv_path:
                    try:
                        df = self.load_from_csv(csv_path)
                        if not df.empty:
                            return df
                    except FileNotFoundError:
                        pass
                
                # Fallback to fixture
                df = self.load_from_fixture(fixture_path)
                if not df.empty:
                    return df
            
            logger.warning("All pick sources failed, returning empty DataFrame")
            return pd.DataFrame()


def create_deterministic_fixture(
    output_path: str,
    pick_type: str = 'weekly',
    num_picks: int = 20
) -> str:
    """
    Create a deterministic fixture file for testing.
    
    Args:
        output_path: Where to save the fixture JSON
        pick_type: 'weekly' or 'monthly'
        num_picks: Number of picks to generate
        
    Returns:
        Path to created fixture file
    """
    tickers = [
        'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'AMD',
        'NFLX', 'DIS', 'V', 'MA', 'JPM', 'BAC', 'WMT', 'COST', 'HD', 'NKE',
        'PEP', 'KO', 'MCD', 'SBUX', 'INTC', 'CSCO', 'ORCL', 'CRM'
    ]
    
    picks = []
    for i in range(min(num_picks, len(tickers))):
        ticker = tickers[i]
        pick = {
            'Ticker': ticker,
            'Company': f'{ticker} Inc.',
            'Rank': i + 1,
            'Score': 100 - (i * 2),
            'Sector': 'Technology' if i % 3 == 0 else 'Consumer' if i % 3 == 1 else 'Finance',
            'MarketCap': f'${(500 - i*10)}B',
            'Recommendation': 'BUY' if i < 10 else 'HOLD',
            'TargetPrice': 150.0 + i * 5,
            'generated_at': datetime.now(timezone.utc).isoformat()
        }
        picks.append(pick)
    
    fixture_data = {
        'pick_type': pick_type,
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'deterministic': True,
        'count': len(picks),
        'data': picks
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(fixture_data, f, indent=2)
    
    logger.info(f"Created deterministic fixture: {output_path} ({len(picks)} picks)")
    return output_path


# Convenience function for quick loading
def load_and_enrich_picks(
    pick_type: str = 'weekly',
    csv_path: Optional[str] = None,
    db_table: Optional[str] = None,
    fixture_path: Optional[str] = None,
    enrich_prices: bool = True
) -> pd.DataFrame:
    """
    One-liner to load and enrich picks.
    
    Args:
        pick_type: 'weekly' or 'monthly'
        csv_path: Path to CSV (optional)
        db_table: DB table name (optional)
        fixture_path: Fixture path (optional)
        enrich_prices: Whether to enrich with prices (default True)
        
    Returns:
        Enriched DataFrame
    """
    fetcher = PicksFetcher(fixture_path=fixture_path)
    
    picks_df = fetcher.load_picks(
        source_type='auto',
        csv_path=csv_path,
        db_table=db_table,
        fixture_path=fixture_path
    )
    
    if enrich_prices and not picks_df.empty:
        picks_df = fetcher.enrich_with_prices(picks_df)
    
    return picks_df
