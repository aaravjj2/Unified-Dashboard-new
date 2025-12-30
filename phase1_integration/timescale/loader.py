"""
TimescaleDB Data Loader for Alpaca Options Lab

Provides bulk loading and query utilities for time-series data.
"""

import asyncio
import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import os
from pathlib import Path

import asyncpg
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)


@dataclass
class OHLCVRecord:
    """OHLCV record structure"""
    time: datetime
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: Optional[float] = None
    trades: Optional[int] = None
    source: str = "alpaca"


@dataclass
class OptionChainRecord:
    """Option chain record structure"""
    time: datetime
    symbol: str
    underlying: str
    expiry: date
    strike: float
    option_type: str
    bid: float
    ask: float
    last: float
    mid: float
    volume: int
    open_interest: int
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    rho: Optional[float] = None
    implied_volatility: Optional[float] = None
    source: str = "alpaca"


class TimescaleLoader:
    """
    TimescaleDB loader for Alpaca Options Lab.
    
    Features:
    - Async bulk inserts
    - Parquet/CSV loading
    - Query utilities
    - Upsert support
    
    Usage:
        loader = TimescaleLoader()
        await loader.connect()
        
        # Bulk insert OHLCV
        await loader.insert_ohlcv(records)
        
        # Load from Parquet
        await loader.load_parquet("data/ohlcv.parquet", "ohlcv")
        
        # Query
        df = await loader.query_ohlcv("GLD", days=30)
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = 5433,
        database: str = "timeseries_data",
        user: str = None,
        password: str = None,
    ):
        self.host = host or os.getenv("TIMESCALE_HOST", "localhost")
        self.port = port
        self.database = database
        self.user = user or os.getenv("POSTGRES_USER", "postgres")
        self.password = password or os.getenv("POSTGRES_PASSWORD", "postgres")
        
        self._pool: Optional[asyncpg.Pool] = None
        
        logger.info(f"TimescaleLoader initialized: {self.host}:{self.port}/{self.database}")
    
    async def connect(self, min_size: int = 5, max_size: int = 20):
        """Create connection pool"""
        self._pool = await asyncpg.create_pool(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            min_size=min_size,
            max_size=max_size,
        )
        logger.info(f"Connected to TimescaleDB pool (min={min_size}, max={max_size})")
    
    async def close(self):
        """Close connection pool"""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("TimescaleDB pool closed")
    
    async def _get_connection(self):
        """Get connection from pool"""
        if not self._pool:
            await self.connect()
        return await self._pool.acquire()
    
    # -------------------------------------------------------------------------
    # Schema Management
    # -------------------------------------------------------------------------
    
    async def init_schema(self):
        """Initialize database schema"""
        schema_path = Path(__file__).parent / "schema" / "001_init_hypertables.sql"
        
        if not schema_path.exists():
            logger.warning(f"Schema file not found: {schema_path}")
            return False
        
        async with self._pool.acquire() as conn:
            sql = schema_path.read_text()
            await conn.execute(sql)
            logger.info("Schema initialized successfully")
            return True
    
    # -------------------------------------------------------------------------
    # OHLCV Operations
    # -------------------------------------------------------------------------
    
    async def insert_ohlcv(
        self,
        records: List[OHLCVRecord],
        on_conflict: str = "DO NOTHING",
    ) -> int:
        """
        Bulk insert OHLCV records.
        
        Args:
            records: List of OHLCVRecord objects
            on_conflict: Conflict resolution ("DO NOTHING" or "UPDATE")
        
        Returns:
            Number of rows inserted
        """
        if not records:
            return 0
        
        async with self._pool.acquire() as conn:
            # Prepare data
            data = [
                (
                    r.time, r.symbol, r.open, r.high, r.low, r.close,
                    r.volume, r.vwap, r.trades, r.source
                )
                for r in records
            ]
            
            # Bulk insert using COPY
            result = await conn.copy_records_to_table(
                "ohlcv",
                records=data,
                columns=[
                    "time", "symbol", "open", "high", "low", "close",
                    "volume", "vwap", "trades", "source"
                ],
            )
            
            logger.info(f"Inserted {len(records)} OHLCV records")
            return len(records)
    
    async def query_ohlcv(
        self,
        symbol: str,
        start: datetime = None,
        end: datetime = None,
        days: int = None,
        interval: str = "1 day",
    ) -> pd.DataFrame:
        """
        Query OHLCV data.
        
        Args:
            symbol: Stock symbol
            start: Start datetime
            end: End datetime
            days: Number of days back (alternative to start/end)
            interval: Time bucket interval
        
        Returns:
            DataFrame with OHLCV data
        """
        if days and not start:
            start = datetime.utcnow() - pd.Timedelta(days=days)
        if not end:
            end = datetime.utcnow()
        
        query = """
            SELECT 
                time_bucket($4, time) AS time,
                symbol,
                first(open, time) AS open,
                max(high) AS high,
                min(low) AS low,
                last(close, time) AS close,
                sum(volume) AS volume
            FROM ohlcv
            WHERE symbol = $1 AND time >= $2 AND time <= $3
            GROUP BY time_bucket($4, time), symbol
            ORDER BY time
        """
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, symbol, start, end, interval)
            
        if not rows:
            return pd.DataFrame()
        
        df = pd.DataFrame([dict(r) for r in rows])
        df["time"] = pd.to_datetime(df["time"])
        return df
    
    async def get_latest_prices(
        self,
        symbols: List[str],
    ) -> Dict[str, Dict]:
        """Get latest prices for multiple symbols"""
        query = """
            SELECT DISTINCT ON (symbol)
                symbol, close as price, time
            FROM ohlcv
            WHERE symbol = ANY($1)
            ORDER BY symbol, time DESC
        """
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, symbols)
        
        return {r["symbol"]: {"price": r["price"], "time": r["time"]} for r in rows}
    
    # -------------------------------------------------------------------------
    # Option Chain Operations
    # -------------------------------------------------------------------------
    
    async def insert_option_chains(
        self,
        records: List[OptionChainRecord],
    ) -> int:
        """Bulk insert option chain records"""
        if not records:
            return 0
        
        async with self._pool.acquire() as conn:
            data = [
                (
                    r.time, r.symbol, r.underlying, r.expiry, r.strike, r.option_type,
                    r.bid, r.ask, r.last, r.mid, r.volume, r.open_interest,
                    r.delta, r.gamma, r.theta, r.vega, r.rho, r.implied_volatility, r.source
                )
                for r in records
            ]
            
            await conn.copy_records_to_table(
                "option_chains",
                records=data,
                columns=[
                    "time", "symbol", "underlying", "expiry", "strike", "option_type",
                    "bid", "ask", "last", "mid", "volume", "open_interest",
                    "delta", "gamma", "theta", "vega", "rho", "implied_volatility", "source"
                ],
            )
            
            logger.info(f"Inserted {len(records)} option chain records")
            return len(records)
    
    async def query_option_chain(
        self,
        underlying: str,
        expiry: date = None,
        option_type: str = None,
    ) -> pd.DataFrame:
        """Query option chain for underlying"""
        conditions = ["underlying = $1"]
        params = [underlying]
        
        if expiry:
            conditions.append(f"expiry = ${len(params) + 1}")
            params.append(expiry)
        if option_type:
            conditions.append(f"option_type = ${len(params) + 1}")
            params.append(option_type)
        
        query = f"""
            SELECT DISTINCT ON (symbol)
                *
            FROM option_chains
            WHERE {" AND ".join(conditions)}
            ORDER BY symbol, time DESC
        """
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
    
    async def get_expiries(self, underlying: str) -> List[date]:
        """Get available expiry dates for underlying"""
        query = """
            SELECT DISTINCT expiry
            FROM option_chains
            WHERE underlying = $1 AND expiry >= CURRENT_DATE
            ORDER BY expiry
        """
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, underlying)
        
        return [r["expiry"] for r in rows]
    
    # -------------------------------------------------------------------------
    # Signal Operations
    # -------------------------------------------------------------------------
    
    async def insert_signal(
        self,
        signal_id: str,
        symbol: str,
        signal_type: str,
        strategy: str = None,
        confidence: float = 0.0,
        source: str = None,
        metadata: dict = None,
    ) -> str:
        """Insert trading signal"""
        query = """
            INSERT INTO signals (time, signal_id, symbol, signal_type, strategy, confidence, source, metadata)
            VALUES (NOW(), $1, $2, $3, $4, $5, $6, $7)
            RETURNING signal_id
        """
        
        async with self._pool.acquire() as conn:
            import json
            result = await conn.fetchval(
                query, signal_id, symbol, signal_type, strategy, confidence, source,
                json.dumps(metadata) if metadata else None
            )
            return result
    
    async def query_signals(
        self,
        symbol: str = None,
        signal_type: str = None,
        hours: int = 24,
    ) -> pd.DataFrame:
        """Query recent signals"""
        conditions = [f"time > NOW() - INTERVAL '{hours} hours'"]
        params = []
        
        if symbol:
            conditions.append(f"symbol = ${len(params) + 1}")
            params.append(symbol)
        if signal_type:
            conditions.append(f"signal_type = ${len(params) + 1}")
            params.append(signal_type)
        
        query = f"""
            SELECT * FROM signals
            WHERE {" AND ".join(conditions)}
            ORDER BY time DESC
        """
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)
        
        return pd.DataFrame([dict(r) for r in rows]) if rows else pd.DataFrame()
    
    # -------------------------------------------------------------------------
    # Order/Trade Operations
    # -------------------------------------------------------------------------
    
    async def insert_order(self, order: Dict) -> str:
        """Insert order record"""
        query = """
            INSERT INTO orders (
                time, order_id, client_order_id, symbol, side, order_type,
                quantity, limit_price, status, strategy, signal_id, paper_mode, metadata
            ) VALUES (
                NOW(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
            )
            RETURNING order_id
        """
        
        async with self._pool.acquire() as conn:
            import json
            return await conn.fetchval(
                query,
                order.get("order_id"),
                order.get("client_order_id"),
                order.get("symbol"),
                order.get("side"),
                order.get("order_type"),
                order.get("quantity"),
                order.get("limit_price"),
                order.get("status"),
                order.get("strategy"),
                order.get("signal_id"),
                order.get("paper_mode", True),
                json.dumps(order.get("metadata")) if order.get("metadata") else None,
            )
    
    async def insert_trade(self, trade: Dict) -> str:
        """Insert trade record"""
        query = """
            INSERT INTO trades (
                time, trade_id, order_id, symbol, side, quantity, price, commission, pnl, strategy, metadata
            ) VALUES (
                NOW(), $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
            )
            RETURNING trade_id
        """
        
        async with self._pool.acquire() as conn:
            import json
            return await conn.fetchval(
                query,
                trade.get("trade_id"),
                trade.get("order_id"),
                trade.get("symbol"),
                trade.get("side"),
                trade.get("quantity"),
                trade.get("price"),
                trade.get("commission", 0),
                trade.get("pnl"),
                trade.get("strategy"),
                json.dumps(trade.get("metadata")) if trade.get("metadata") else None,
            )
    
    # -------------------------------------------------------------------------
    # Parquet/CSV Loading
    # -------------------------------------------------------------------------
    
    async def load_parquet(
        self,
        file_path: str,
        table: str,
        batch_size: int = 10000,
    ) -> int:
        """
        Load data from Parquet file into table.
        
        Args:
            file_path: Path to Parquet file
            table: Target table name
            batch_size: Rows per batch
        
        Returns:
            Number of rows loaded
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Read Parquet
        table_data = pq.read_table(file_path)
        df = table_data.to_pandas()
        
        total_rows = 0
        async with self._pool.acquire() as conn:
            # Get column names from DataFrame
            columns = list(df.columns)
            
            # Process in batches
            for i in range(0, len(df), batch_size):
                batch = df.iloc[i:i + batch_size]
                records = [tuple(row) for row in batch.values]
                
                await conn.copy_records_to_table(
                    table,
                    records=records,
                    columns=columns,
                )
                
                total_rows += len(records)
                logger.info(f"Loaded {total_rows}/{len(df)} rows from {path.name}")
        
        return total_rows
    
    async def load_csv(
        self,
        file_path: str,
        table: str,
        batch_size: int = 10000,
    ) -> int:
        """Load data from CSV file into table"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        df = pd.read_csv(file_path)
        
        # Convert to Parquet for efficient loading
        temp_parquet = path.with_suffix(".temp.parquet")
        df.to_parquet(temp_parquet)
        
        try:
            result = await self.load_parquet(str(temp_parquet), table, batch_size)
        finally:
            temp_parquet.unlink(missing_ok=True)
        
        return result
    
    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------
    
    async def execute(self, query: str, *args) -> Any:
        """Execute raw SQL query"""
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch(self, query: str, *args) -> List[Dict]:
        """Fetch rows from raw SQL query"""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *args)
            return [dict(r) for r in rows]
    
    async def get_table_stats(self) -> Dict[str, Dict]:
        """Get stats for all tables"""
        query = """
            SELECT 
                hypertable_schema,
                hypertable_name,
                num_chunks,
                compression_enabled
            FROM timescaledb_information.hypertables
        """
        
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query)
        
        stats = {}
        for row in rows:
            table_name = row["hypertable_name"]
            
            # Get row count
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            count = await conn.fetchval(count_query)
            
            stats[table_name] = {
                "chunks": row["num_chunks"],
                "compression_enabled": row["compression_enabled"],
                "row_count": count,
            }
        
        return stats
    
    async def health_check(self) -> Dict:
        """Check database health"""
        try:
            async with self._pool.acquire() as conn:
                # Check connection
                await conn.fetchval("SELECT 1")
                
                # Get TimescaleDB version
                version = await conn.fetchval("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
                
                # Get pool stats
                return {
                    "status": "healthy",
                    "timescaledb_version": version,
                    "pool_size": self._pool.get_size(),
                    "pool_free": self._pool.get_idle_size(),
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }


# -----------------------------------------------------------------------------
# Singleton instance
# -----------------------------------------------------------------------------

_loader_instance: Optional[TimescaleLoader] = None


async def get_loader() -> TimescaleLoader:
    """Get singleton TimescaleLoader instance"""
    global _loader_instance
    if _loader_instance is None:
        _loader_instance = TimescaleLoader()
        await _loader_instance.connect()
    return _loader_instance


# -----------------------------------------------------------------------------
# CLI for testing
# -----------------------------------------------------------------------------

async def main():
    """Test the loader"""
    logging.basicConfig(level=logging.INFO)
    
    loader = await get_loader()
    
    # Health check
    health = await loader.health_check()
    print(f"Health: {health}")
    
    # Init schema
    await loader.init_schema()
    
    # Test insert
    record = OHLCVRecord(
        time=datetime.utcnow(),
        symbol="GLD",
        open=245.0,
        high=246.5,
        low=244.5,
        close=245.5,
        volume=1000000,
    )
    
    await loader.insert_ohlcv([record])
    
    # Query
    df = await loader.query_ohlcv("GLD", days=1)
    print(f"OHLCV data:\n{df}")
    
    await loader.close()


if __name__ == "__main__":
    asyncio.run(main())
