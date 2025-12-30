"""
Redis Streams Wrapper for Alpaca Options Lab

Provides persistent event streams for:
- Order lifecycle events
- Trade executions
- Position changes
- Audit trail
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import os
import uuid

try:
    import redis.asyncio as aioredis
    import redis
except ImportError:
    aioredis = None
    redis = None

logger = logging.getLogger(__name__)


class StreamName(str, Enum):
    """Stream name definitions"""
    ORDERS = "alpaca:stream:orders"       # Order lifecycle
    TRADES = "alpaca:stream:trades"       # Executed trades
    POSITIONS = "alpaca:stream:positions" # Position changes
    RISK = "alpaca:stream:risk"           # Risk events
    AUDIT = "alpaca:stream:audit"         # Audit trail
    ALERTS = "alpaca:stream:alerts"       # Alert history


class OrderStatus(str, Enum):
    """Order status values"""
    PENDING = "pending"
    SUBMITTED = "submitted"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class OrderEvent:
    """Order event structure"""
    order_id: str
    status: str
    symbol: str
    side: str                    # buy, sell
    quantity: int
    order_type: str              # limit, market, stop
    price: Optional[float] = None
    filled_qty: int = 0
    avg_fill_price: Optional[float] = None
    strategy: str = ""
    legs: List[Dict] = field(default_factory=list)
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to Redis stream format (all values must be strings)"""
        data = asdict(self)
        return {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                for k, v in data.items()}
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "OrderEvent":
        """Create from Redis stream data"""
        parsed = {}
        for k, v in data.items():
            try:
                parsed[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                parsed[k] = v
        return cls(**parsed)


@dataclass
class TradeEvent:
    """Trade execution event"""
    trade_id: str
    order_id: str
    symbol: str
    side: str
    quantity: int
    price: float
    commission: float = 0.0
    strategy: str = ""
    pnl: Optional[float] = None
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, str]:
        data = asdict(self)
        return {k: json.dumps(v) if isinstance(v, (dict, list)) else str(v) 
                for k, v in data.items()}
    
    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "TradeEvent":
        parsed = {}
        for k, v in data.items():
            try:
                parsed[k] = json.loads(v)
            except (json.JSONDecodeError, TypeError):
                parsed[k] = v
        # Handle numeric fields
        for field_name in ['quantity', 'price', 'commission']:
            if field_name in parsed and isinstance(parsed[field_name], str):
                try:
                    parsed[field_name] = float(parsed[field_name]) if '.' in str(parsed[field_name]) else int(parsed[field_name])
                except ValueError:
                    pass
        return cls(**parsed)


class RedisStreams:
    """
    Redis Streams manager for persistent event storage.
    
    Features:
    - Persistent storage of order/trade events
    - Consumer groups for reliable processing
    - Time-based queries for replay
    - Automatic trimming of old events
    
    Usage:
        streams = RedisStreams()
        
        # Add order event
        event = OrderEvent(order_id="ord1", status="submitted", ...)
        msg_id = await streams.add_order_event(event)
        
        # Read recent orders
        orders = await streams.read_orders(count=100)
        
        # Consumer group processing
        async for event in streams.consume_orders("my-consumer"):
            process(event)
            await streams.ack_order(event.msg_id)
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = 6379,
        db: int = 0,
        password: str = None,
        max_stream_length: int = 100000,
    ):
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port
        self.db = db
        self.password = password or os.getenv("REDIS_PASSWORD")
        self.max_len = max_stream_length
        
        self._client: Optional[aioredis.Redis] = None
        self._consumer_groups_initialized: set = set()
        
        logger.info(f"RedisStreams initialized: {self.host}:{self.port}")
    
    async def get_client(self) -> aioredis.Redis:
        """Get or create async Redis client"""
        if self._client is None:
            self._client = aioredis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
            )
        return self._client
    
    # -------------------------------------------------------------------------
    # Stream Operations
    # -------------------------------------------------------------------------
    
    async def add(self, stream: StreamName, data: Dict[str, str]) -> str:
        """Add entry to stream, returns message ID"""
        client = await self.get_client()
        msg_id = await client.xadd(
            stream.value,
            data,
            maxlen=self.max_len,
            approximate=True,
        )
        logger.debug(f"Added to {stream.value}: {msg_id}")
        return msg_id
    
    async def add_order_event(self, event: OrderEvent) -> str:
        """Add order event to orders stream"""
        return await self.add(StreamName.ORDERS, event.to_dict())
    
    async def add_trade_event(self, event: TradeEvent) -> str:
        """Add trade event to trades stream"""
        return await self.add(StreamName.TRADES, event.to_dict())
    
    async def add_audit(self, action: str, details: Dict[str, Any]) -> str:
        """Add audit trail entry"""
        data = {
            "action": action,
            "details": json.dumps(details),
            "timestamp": datetime.utcnow().isoformat(),
        }
        return await self.add(StreamName.AUDIT, data)
    
    # -------------------------------------------------------------------------
    # Reading Streams
    # -------------------------------------------------------------------------
    
    async def read(
        self,
        stream: StreamName,
        count: int = 100,
        start: str = "-",
        end: str = "+",
    ) -> List[Tuple[str, Dict]]:
        """
        Read entries from stream.
        
        Args:
            stream: Stream to read from
            count: Max entries to return
            start: Start ID ("-" for oldest)
            end: End ID ("+" for newest)
        
        Returns:
            List of (message_id, data) tuples
        """
        client = await self.get_client()
        result = await client.xrange(stream.value, start, end, count=count)
        return result
    
    async def read_orders(
        self,
        count: int = 100,
        symbol: str = None,
        status: str = None,
    ) -> List[OrderEvent]:
        """Read order events with optional filtering"""
        entries = await self.read(StreamName.ORDERS, count=count)
        events = []
        for msg_id, data in entries:
            event = OrderEvent.from_dict(data)
            event.metadata["msg_id"] = msg_id
            
            # Apply filters
            if symbol and event.symbol != symbol:
                continue
            if status and event.status != status:
                continue
            
            events.append(event)
        return events
    
    async def read_trades(
        self,
        count: int = 100,
        symbol: str = None,
    ) -> List[TradeEvent]:
        """Read trade events with optional filtering"""
        entries = await self.read(StreamName.TRADES, count=count)
        events = []
        for msg_id, data in entries:
            event = TradeEvent.from_dict(data)
            event.metadata["msg_id"] = msg_id
            
            if symbol and event.symbol != symbol:
                continue
            
            events.append(event)
        return events
    
    async def read_latest(
        self,
        stream: StreamName,
        count: int = 10,
    ) -> List[Tuple[str, Dict]]:
        """Read latest entries (newest first)"""
        client = await self.get_client()
        result = await client.xrevrange(stream.value, "+", "-", count=count)
        return result
    
    # -------------------------------------------------------------------------
    # Consumer Groups
    # -------------------------------------------------------------------------
    
    async def create_consumer_group(
        self,
        stream: StreamName,
        group: str,
        start_from: str = "$",
    ):
        """
        Create consumer group for stream.
        
        Args:
            stream: Stream name
            group: Consumer group name
            start_from: "$" for new messages, "0" for all messages
        """
        client = await self.get_client()
        key = f"{stream.value}:{group}"
        
        if key in self._consumer_groups_initialized:
            return
        
        try:
            await client.xgroup_create(
                stream.value,
                group,
                start_from,
                mkstream=True,
            )
            logger.info(f"Created consumer group: {group} on {stream.value}")
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.debug(f"Consumer group already exists: {group}")
            else:
                raise
        
        self._consumer_groups_initialized.add(key)
    
    async def consume(
        self,
        stream: StreamName,
        group: str,
        consumer: str,
        count: int = 10,
        block: int = 5000,
    ) -> List[Tuple[str, Dict]]:
        """
        Read messages as consumer group member.
        
        Returns unacked messages for this consumer.
        """
        await self.create_consumer_group(stream, group)
        
        client = await self.get_client()
        result = await client.xreadgroup(
            group,
            consumer,
            {stream.value: ">"},
            count=count,
            block=block,
        )
        
        if not result:
            return []
        
        # Result format: [[stream_name, [(msg_id, data), ...]]]
        return result[0][1] if result else []
    
    async def consume_orders(
        self,
        group: str = "order-processors",
        consumer: str = None,
    ):
        """
        Async generator for consuming order events.
        
        Usage:
            async for event in streams.consume_orders("my-consumer"):
                process(event)
                await streams.ack_order(event.metadata["msg_id"])
        """
        consumer = consumer or f"consumer-{uuid.uuid4().hex[:8]}"
        
        while True:
            entries = await self.consume(StreamName.ORDERS, group, consumer)
            for msg_id, data in entries:
                event = OrderEvent.from_dict(data)
                event.metadata["msg_id"] = msg_id
                event.metadata["group"] = group
                yield event
    
    async def consume_trades(
        self,
        group: str = "trade-processors",
        consumer: str = None,
    ):
        """Async generator for consuming trade events"""
        consumer = consumer or f"consumer-{uuid.uuid4().hex[:8]}"
        
        while True:
            entries = await self.consume(StreamName.TRADES, group, consumer)
            for msg_id, data in entries:
                event = TradeEvent.from_dict(data)
                event.metadata["msg_id"] = msg_id
                event.metadata["group"] = group
                yield event
    
    async def ack(self, stream: StreamName, group: str, msg_id: str):
        """Acknowledge message processing"""
        client = await self.get_client()
        await client.xack(stream.value, group, msg_id)
        logger.debug(f"Acked {msg_id} in {group}")
    
    async def ack_order(self, msg_id: str, group: str = "order-processors"):
        """Ack order event"""
        await self.ack(StreamName.ORDERS, group, msg_id)
    
    async def ack_trade(self, msg_id: str, group: str = "trade-processors"):
        """Ack trade event"""
        await self.ack(StreamName.TRADES, group, msg_id)
    
    # -------------------------------------------------------------------------
    # Time-based Queries
    # -------------------------------------------------------------------------
    
    async def read_since(
        self,
        stream: StreamName,
        since_ms: int,
        count: int = 1000,
    ) -> List[Tuple[str, Dict]]:
        """Read entries since timestamp (milliseconds)"""
        return await self.read(stream, count=count, start=f"{since_ms}-0")
    
    async def read_time_range(
        self,
        stream: StreamName,
        start_ms: int,
        end_ms: int,
        count: int = 1000,
    ) -> List[Tuple[str, Dict]]:
        """Read entries in time range"""
        return await self.read(
            stream,
            count=count,
            start=f"{start_ms}-0",
            end=f"{end_ms}-0",
        )
    
    # -------------------------------------------------------------------------
    # Stream Management
    # -------------------------------------------------------------------------
    
    async def trim(self, stream: StreamName, maxlen: int):
        """Trim stream to max length"""
        client = await self.get_client()
        await client.xtrim(stream.value, maxlen=maxlen, approximate=True)
    
    async def get_length(self, stream: StreamName) -> int:
        """Get stream length"""
        client = await self.get_client()
        return await client.xlen(stream.value)
    
    async def get_info(self, stream: StreamName) -> Dict[str, Any]:
        """Get stream info"""
        client = await self.get_client()
        try:
            return await client.xinfo_stream(stream.value)
        except redis.ResponseError:
            return {"length": 0, "first-entry": None, "last-entry": None}
    
    async def get_all_stream_stats(self) -> Dict[str, Dict]:
        """Get stats for all streams"""
        stats = {}
        for stream in StreamName:
            info = await self.get_info(stream)
            stats[stream.value] = {
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
            }
        return stats
    
    # -------------------------------------------------------------------------
    # Health & Cleanup
    # -------------------------------------------------------------------------
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis streams health"""
        try:
            client = await self.get_client()
            await client.ping()
            
            stats = await self.get_all_stream_stats()
            total_entries = sum(s["length"] for s in stats.values())
            
            return {
                "status": "healthy",
                "total_entries": total_entries,
                "streams": stats,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }
    
    async def close(self):
        """Close connection"""
        if self._client:
            await self._client.close()
            self._client = None
        logger.info("RedisStreams closed")


# -----------------------------------------------------------------------------
# Singleton instance
# -----------------------------------------------------------------------------

_streams_instance: Optional[RedisStreams] = None


def get_streams() -> RedisStreams:
    """Get singleton RedisStreams instance"""
    global _streams_instance
    if _streams_instance is None:
        _streams_instance = RedisStreams()
    return _streams_instance


# -----------------------------------------------------------------------------
# Example usage
# -----------------------------------------------------------------------------

async def example_producer():
    """Example order event producer"""
    streams = get_streams()
    
    order = OrderEvent(
        order_id=f"ord_{uuid.uuid4().hex[:8]}",
        status=OrderStatus.SUBMITTED.value,
        symbol="GLD",
        side="sell",
        quantity=1,
        order_type="limit",
        price=245.50,
        strategy="iron_condor",
        legs=[
            {"strike": 240, "type": "put", "side": "sell"},
            {"strike": 235, "type": "put", "side": "buy"},
            {"strike": 250, "type": "call", "side": "sell"},
            {"strike": 255, "type": "call", "side": "buy"},
        ],
    )
    
    msg_id = await streams.add_order_event(order)
    print(f"Added order: {msg_id}")
    
    # Add audit
    await streams.add_audit("order_submitted", {"order_id": order.order_id})


async def example_consumer():
    """Example order event consumer"""
    streams = get_streams()
    
    print("Consuming orders...")
    async for event in streams.consume_orders():
        print(f"Processing: {event.order_id} - {event.status}")
        await streams.ack_order(event.metadata["msg_id"])


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "produce":
        asyncio.run(example_producer())
    else:
        asyncio.run(example_consumer())
