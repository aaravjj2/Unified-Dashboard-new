"""
Data Ingestion Worker for Alpaca Options Lab

Fetches data from:
- Alpaca Markets API (stocks, options)
- Yahoo Finance (backup/enrichment)
- Other data sources

Stores data in:
- TimescaleDB (historical)
- Redis Streams (real-time)
- Parquet files (batch analysis)
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import json
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Configuration
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "")
ALPACA_BASE_URL = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
TIMESCALE_HOST = os.getenv("TIMESCALE_HOST", "localhost")
INGESTION_INTERVAL = int(os.getenv("INGESTION_INTERVAL", "60"))


# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------

@dataclass
class OHLCV:
    """OHLCV bar data"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    vwap: Optional[float] = None
    trades: Optional[int] = None


@dataclass 
class OptionChain:
    """Option chain data"""
    underlying: str
    contract: str
    expiry: str
    strike: float
    right: str  # 'call' or 'put'
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    iv: float
    delta: float
    gamma: float
    theta: float
    vega: float
    timestamp: datetime


@dataclass
class Quote:
    """Real-time quote"""
    symbol: str
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    timestamp: datetime


# -----------------------------------------------------------------------------
# Data Fetchers
# -----------------------------------------------------------------------------

class AlpacaFetcher:
    """Fetch data from Alpaca Markets API"""
    
    def __init__(self, api_key: str = None, secret_key: str = None):
        self.api_key = api_key or ALPACA_API_KEY
        self.secret_key = secret_key or ALPACA_SECRET_KEY
        self.base_url = ALPACA_BASE_URL
        self._http_client = None
    
    async def get_client(self):
        """Get or create HTTP client"""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(
                headers={
                    "APCA-API-KEY-ID": self.api_key,
                    "APCA-API-SECRET-KEY": self.secret_key,
                },
                timeout=30.0,
            )
        return self._http_client
    
    async def close(self):
        """Close HTTP client"""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
    
    async def fetch_bars(
        self,
        symbol: str,
        timeframe: str = "1Day",
        start: datetime = None,
        end: datetime = None,
        limit: int = 1000,
    ) -> List[OHLCV]:
        """Fetch OHLCV bars from Alpaca"""
        client = await self.get_client()
        
        # Default to last 30 days
        if start is None:
            start = datetime.utcnow() - timedelta(days=30)
        if end is None:
            end = datetime.utcnow()
        
        url = f"https://data.alpaca.markets/v2/stocks/{symbol}/bars"
        params = {
            "timeframe": timeframe,
            "start": start.isoformat() + "Z",
            "end": end.isoformat() + "Z",
            "limit": limit,
        }
        
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            bars = []
            for bar in data.get("bars", []):
                bars.append(OHLCV(
                    symbol=symbol,
                    timestamp=datetime.fromisoformat(bar["t"].replace("Z", "")),
                    open=bar["o"],
                    high=bar["h"],
                    low=bar["l"],
                    close=bar["c"],
                    volume=bar["v"],
                    vwap=bar.get("vw"),
                    trades=bar.get("n"),
                ))
            return bars
        except Exception as e:
            logger.error(f"Failed to fetch bars for {symbol}: {e}")
            return []
    
    async def fetch_quotes(self, symbols: List[str]) -> List[Quote]:
        """Fetch latest quotes"""
        client = await self.get_client()
        
        url = "https://data.alpaca.markets/v2/stocks/quotes/latest"
        params = {"symbols": ",".join(symbols)}
        
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            quotes = []
            for symbol, quote in data.get("quotes", {}).items():
                quotes.append(Quote(
                    symbol=symbol,
                    bid=quote.get("bp", 0),
                    ask=quote.get("ap", 0),
                    bid_size=quote.get("bs", 0),
                    ask_size=quote.get("as", 0),
                    timestamp=datetime.fromisoformat(quote["t"].replace("Z", "")),
                ))
            return quotes
        except Exception as e:
            logger.error(f"Failed to fetch quotes: {e}")
            return []
    
    async def fetch_option_chain(
        self,
        underlying: str,
        expiry: str = None,
    ) -> List[OptionChain]:
        """Fetch option chain from Alpaca"""
        client = await self.get_client()
        
        url = f"https://data.alpaca.markets/v1beta1/options/snapshots/{underlying}"
        params = {}
        if expiry:
            params["expiration_date"] = expiry
        
        try:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
            
            chains = []
            for contract, snapshot in data.get("snapshots", {}).items():
                greeks = snapshot.get("greeks", {})
                quote = snapshot.get("latestQuote", {})
                trade = snapshot.get("latestTrade", {})
                
                # Parse contract symbol
                # Format: AAPL230120C00150000
                # TODO: Proper parsing
                
                chains.append(OptionChain(
                    underlying=underlying,
                    contract=contract,
                    expiry=snapshot.get("expiration_date", ""),
                    strike=snapshot.get("strike_price", 0),
                    right=snapshot.get("option_type", "call"),
                    bid=quote.get("bp", 0),
                    ask=quote.get("ap", 0),
                    last=trade.get("p", 0),
                    volume=trade.get("s", 0),
                    open_interest=snapshot.get("open_interest", 0),
                    iv=greeks.get("implied_volatility", 0),
                    delta=greeks.get("delta", 0),
                    gamma=greeks.get("gamma", 0),
                    theta=greeks.get("theta", 0),
                    vega=greeks.get("vega", 0),
                    timestamp=datetime.utcnow(),
                ))
            return chains
        except Exception as e:
            logger.error(f"Failed to fetch option chain for {underlying}: {e}")
            return []


class YFinanceFetcher:
    """Fetch data from Yahoo Finance (backup source)"""
    
    async def fetch_bars(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> List[OHLCV]:
        """Fetch bars from Yahoo Finance"""
        try:
            import yfinance as yf
            
            # yfinance is synchronous, run in thread pool
            loop = asyncio.get_event_loop()
            ticker = yf.Ticker(symbol)
            
            df = await loop.run_in_executor(
                None,
                lambda: ticker.history(period=period, interval=interval)
            )
            
            bars = []
            for idx, row in df.iterrows():
                bars.append(OHLCV(
                    symbol=symbol,
                    timestamp=idx.to_pydatetime(),
                    open=row["Open"],
                    high=row["High"],
                    low=row["Low"],
                    close=row["Close"],
                    volume=int(row["Volume"]),
                ))
            return bars
        except Exception as e:
            logger.error(f"yfinance fetch failed for {symbol}: {e}")
            return []
    
    async def fetch_option_chain(self, underlying: str) -> List[OptionChain]:
        """Fetch option chain from Yahoo Finance"""
        try:
            import yfinance as yf
            
            loop = asyncio.get_event_loop()
            ticker = yf.Ticker(underlying)
            
            # Get available expirations
            expirations = await loop.run_in_executor(
                None, lambda: ticker.options
            )
            
            if not expirations:
                return []
            
            chains = []
            # Fetch first 3 expirations
            for expiry in expirations[:3]:
                opt = await loop.run_in_executor(
                    None, lambda e=expiry: ticker.option_chain(e)
                )
                
                for idx, row in opt.calls.iterrows():
                    chains.append(OptionChain(
                        underlying=underlying,
                        contract=row["contractSymbol"],
                        expiry=expiry,
                        strike=row["strike"],
                        right="call",
                        bid=row.get("bid", 0),
                        ask=row.get("ask", 0),
                        last=row.get("lastPrice", 0),
                        volume=int(row.get("volume", 0) or 0),
                        open_interest=int(row.get("openInterest", 0) or 0),
                        iv=row.get("impliedVolatility", 0),
                        delta=0,  # Not available from yfinance
                        gamma=0,
                        theta=0,
                        vega=0,
                        timestamp=datetime.utcnow(),
                    ))
                
                for idx, row in opt.puts.iterrows():
                    chains.append(OptionChain(
                        underlying=underlying,
                        contract=row["contractSymbol"],
                        expiry=expiry,
                        strike=row["strike"],
                        right="put",
                        bid=row.get("bid", 0),
                        ask=row.get("ask", 0),
                        last=row.get("lastPrice", 0),
                        volume=int(row.get("volume", 0) or 0),
                        open_interest=int(row.get("openInterest", 0) or 0),
                        iv=row.get("impliedVolatility", 0),
                        delta=0,
                        gamma=0,
                        theta=0,
                        vega=0,
                        timestamp=datetime.utcnow(),
                    ))
            
            return chains
        except Exception as e:
            logger.error(f"yfinance option chain failed for {underlying}: {e}")
            return []


# -----------------------------------------------------------------------------
# Data Storage
# -----------------------------------------------------------------------------

class DataStorage:
    """Store data to TimescaleDB and Redis"""
    
    def __init__(self):
        self._timescale = None
        self._redis_streams = None
    
    async def init(self):
        """Initialize storage connections"""
        try:
            from ..timescale import get_loader
            self._timescale = get_loader()
            await self._timescale.connect()
            logger.info("TimescaleDB connection established")
        except Exception as e:
            logger.warning(f"TimescaleDB not available: {e}")
        
        try:
            from ..redis import get_streams
            self._redis_streams = get_streams()
            await self._redis_streams.connect()
            logger.info("Redis Streams connection established")
        except Exception as e:
            logger.warning(f"Redis Streams not available: {e}")
    
    async def close(self):
        """Close storage connections"""
        if self._timescale:
            await self._timescale.close()
        if self._redis_streams:
            await self._redis_streams.close()
    
    async def store_bars(self, bars: List[OHLCV]):
        """Store OHLCV bars"""
        if not bars:
            return
        
        if self._timescale:
            records = []
            for bar in bars:
                records.append({
                    "timestamp": bar.timestamp,
                    "symbol": bar.symbol,
                    "open": bar.open,
                    "high": bar.high,
                    "low": bar.low,
                    "close": bar.close,
                    "volume": bar.volume,
                    "vwap": bar.vwap,
                    "trades": bar.trades,
                })
            await self._timescale.bulk_insert_ohlcv(records)
            logger.info(f"Stored {len(records)} OHLCV bars to TimescaleDB")
        
        # Also publish latest to Redis for real-time consumers
        if self._redis_streams and bars:
            latest = bars[-1]
            await self._redis_streams.publish_price_update(
                symbol=latest.symbol,
                price=latest.close,
                volume=latest.volume,
            )
    
    async def store_option_chains(self, chains: List[OptionChain]):
        """Store option chain data"""
        if not chains:
            return
        
        if self._timescale:
            records = []
            for chain in chains:
                records.append({
                    "timestamp": chain.timestamp,
                    "underlying": chain.underlying,
                    "symbol": chain.contract,
                    "expiry": chain.expiry,
                    "strike": chain.strike,
                    "right": chain.right,
                    "bid": chain.bid,
                    "ask": chain.ask,
                    "last": chain.last,
                    "volume": chain.volume,
                    "open_interest": chain.open_interest,
                    "iv": chain.iv,
                    "delta": chain.delta,
                    "gamma": chain.gamma,
                    "theta": chain.theta,
                    "vega": chain.vega,
                })
            await self._timescale.bulk_insert_option_chains(records)
            logger.info(f"Stored {len(records)} option contracts to TimescaleDB")
    
    async def store_quotes(self, quotes: List[Quote]):
        """Store real-time quotes"""
        if self._redis_streams and quotes:
            for quote in quotes:
                await self._redis_streams.publish_price_update(
                    symbol=quote.symbol,
                    price=(quote.bid + quote.ask) / 2,
                    bid=quote.bid,
                    ask=quote.ask,
                )


# -----------------------------------------------------------------------------
# Ingestion Worker
# -----------------------------------------------------------------------------

class IngestionWorker:
    """Main ingestion worker orchestrating data fetching and storage"""
    
    def __init__(
        self,
        symbols: List[str] = None,
        interval: int = None,
    ):
        self.symbols = symbols or [
            "AAPL", "MSFT", "GOOGL", "AMZN", "META",
            "NVDA", "TSLA", "SPY", "QQQ", "IWM",
        ]
        self.interval = interval or INGESTION_INTERVAL
        
        self.alpaca = AlpacaFetcher()
        self.yfinance = YFinanceFetcher()
        self.storage = DataStorage()
        
        self._running = False
    
    async def start(self):
        """Start the ingestion worker"""
        logger.info("Starting ingestion worker...")
        
        await self.storage.init()
        self._running = True
        
        while self._running:
            try:
                await self._ingest_cycle()
            except Exception as e:
                logger.error(f"Ingestion cycle failed: {e}")
            
            await asyncio.sleep(self.interval)
    
    async def stop(self):
        """Stop the ingestion worker"""
        logger.info("Stopping ingestion worker...")
        self._running = False
        
        await self.alpaca.close()
        await self.storage.close()
    
    async def _ingest_cycle(self):
        """Single ingestion cycle"""
        logger.info(f"Running ingestion cycle for {len(self.symbols)} symbols")
        
        # Fetch and store bars for each symbol
        for symbol in self.symbols:
            try:
                # Try Alpaca first
                bars = await self.alpaca.fetch_bars(symbol, timeframe="1Hour")
                
                # Fallback to yfinance if Alpaca fails
                if not bars:
                    bars = await self.yfinance.fetch_bars(symbol, interval="1h")
                
                await self.storage.store_bars(bars)
                
            except Exception as e:
                logger.error(f"Failed to ingest bars for {symbol}: {e}")
        
        # Fetch quotes
        try:
            quotes = await self.alpaca.fetch_quotes(self.symbols)
            await self.storage.store_quotes(quotes)
        except Exception as e:
            logger.error(f"Failed to ingest quotes: {e}")
        
        # Fetch option chains for select symbols
        option_symbols = ["SPY", "QQQ", "AAPL", "NVDA"]
        for symbol in option_symbols:
            if symbol in self.symbols:
                try:
                    # Try Alpaca first
                    chains = await self.alpaca.fetch_option_chain(symbol)
                    
                    # Fallback to yfinance
                    if not chains:
                        chains = await self.yfinance.fetch_option_chain(symbol)
                    
                    await self.storage.store_option_chains(chains)
                    
                except Exception as e:
                    logger.error(f"Failed to ingest options for {symbol}: {e}")
        
        logger.info("Ingestion cycle complete")
    
    async def backfill(
        self,
        symbols: List[str] = None,
        days: int = 365,
    ):
        """Backfill historical data"""
        symbols = symbols or self.symbols
        logger.info(f"Backfilling {days} days of data for {len(symbols)} symbols")
        
        await self.storage.init()
        
        start = datetime.utcnow() - timedelta(days=days)
        end = datetime.utcnow()
        
        for symbol in symbols:
            try:
                # Daily bars
                bars = await self.alpaca.fetch_bars(
                    symbol,
                    timeframe="1Day",
                    start=start,
                    end=end,
                    limit=days + 10,
                )
                
                if not bars:
                    bars = await self.yfinance.fetch_bars(
                        symbol,
                        period=f"{days}d",
                        interval="1d",
                    )
                
                await self.storage.store_bars(bars)
                logger.info(f"Backfilled {len(bars)} bars for {symbol}")
                
            except Exception as e:
                logger.error(f"Backfill failed for {symbol}: {e}")
        
        await self.storage.close()
        logger.info("Backfill complete")


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------

async def main():
    """Main entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    worker = IngestionWorker()
    
    try:
        await worker.start()
    except KeyboardInterrupt:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
