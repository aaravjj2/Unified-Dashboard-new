"""
Redis Pub/Sub Wrapper for Alpaca Options Lab

Provides pub/sub channels for:
- Signal broadcasts (analysis -> trading)
- Alert notifications (monitoring -> UI)
- Price updates (data -> analysis)
- Regime changes (ML -> all)
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import os

try:
    import redis.asyncio as aioredis
    import redis
except ImportError:
    aioredis = None
    redis = None

logger = logging.getLogger(__name__)


class SignalChannel(str, Enum):
    """Pub/Sub channel definitions"""
    SIGNALS = "alpaca:signals"           # Trading signals
    ALERTS = "alpaca:alerts"             # Alert notifications
    PRICES = "alpaca:prices"             # Price updates
    REGIME = "alpaca:regime"             # Regime changes
    GREEKS = "alpaca:greeks"             # Greeks updates
    FLOW = "alpaca:flow"                 # Options flow
    ORDERS = "alpaca:orders"             # Order events
    FILLS = "alpaca:fills"               # Fill confirmations
    HEALTH = "alpaca:health"             # Health status


@dataclass
class Signal:
    """Signal message structure"""
    id: str
    type: str                    # buy, sell, hold, hedge
    symbol: str
    strategy: str                # iron_condor, spread, etc.
    confidence: float            # 0.0 - 1.0
    source: str                  # lstm, xgb, ensemble, etc.
    timestamp: str
    data: Dict[str, Any]
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, data: str) -> "Signal":
        return cls(**json.loads(data))


@dataclass
class Alert:
    """Alert message structure"""
    id: str
    severity: str                # info, warning, critical
    type: str                    # price, iv, skew, flow, risk
    symbol: str
    message: str
    timestamp: str
    data: Dict[str, Any]
    
    def to_json(self) -> str:
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, data: str) -> "Alert":
        return cls(**json.loads(data))


class RedisPubSub:
    """
    Redis Pub/Sub manager for Alpaca Options Lab.
    
    Usage:
        pubsub = RedisPubSub()
        
        # Publish a signal
        signal = Signal(id="sig1", type="buy", symbol="GLD", ...)
        await pubsub.publish_signal(signal)
        
        # Subscribe to signals
        async for signal in pubsub.subscribe_signals():
            print(f"Received: {signal}")
    """
    
    def __init__(
        self,
        host: str = None,
        port: int = 6379,
        db: int = 0,
        password: str = None,
    ):
        self.host = host or os.getenv("REDIS_HOST", "localhost")
        self.port = port
        self.db = db
        self.password = password or os.getenv("REDIS_PASSWORD")
        
        # Async client
        self._async_client: Optional[aioredis.Redis] = None
        
        # Sync client for simple operations
        self._sync_client: Optional[redis.Redis] = None
        
        # Active subscriptions
        self._subscriptions: Dict[str, asyncio.Task] = {}
        
        logger.info(f"RedisPubSub initialized: {self.host}:{self.port}")
    
    async def get_async_client(self) -> aioredis.Redis:
        """Get or create async Redis client"""
        if self._async_client is None:
            self._async_client = aioredis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
            )
        return self._async_client
    
    def get_sync_client(self) -> redis.Redis:
        """Get or create sync Redis client"""
        if self._sync_client is None:
            self._sync_client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                password=self.password,
                decode_responses=True,
            )
        return self._sync_client
    
    # -------------------------------------------------------------------------
    # Publishing
    # -------------------------------------------------------------------------
    
    async def publish(self, channel: SignalChannel, message: str) -> int:
        """Publish message to channel"""
        client = await self.get_async_client()
        subscribers = await client.publish(channel.value, message)
        logger.debug(f"Published to {channel.value}: {subscribers} subscribers")
        return subscribers
    
    async def publish_signal(self, signal: Signal) -> int:
        """Publish trading signal"""
        return await self.publish(SignalChannel.SIGNALS, signal.to_json())
    
    async def publish_alert(self, alert: Alert) -> int:
        """Publish alert notification"""
        return await self.publish(SignalChannel.ALERTS, alert.to_json())
    
    async def publish_price(self, symbol: str, price: float, data: Dict = None) -> int:
        """Publish price update"""
        msg = json.dumps({
            "symbol": symbol,
            "price": price,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data or {}
        })
        return await self.publish(SignalChannel.PRICES, msg)
    
    async def publish_regime(self, regime: str, confidence: float, data: Dict = None) -> int:
        """Publish regime change"""
        msg = json.dumps({
            "regime": regime,
            "confidence": confidence,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data or {}
        })
        return await self.publish(SignalChannel.REGIME, msg)
    
    # -------------------------------------------------------------------------
    # Subscribing (Async Generator)
    # -------------------------------------------------------------------------
    
    async def subscribe(self, channel: SignalChannel):
        """
        Subscribe to channel and yield messages.
        
        Usage:
            async for msg in pubsub.subscribe(SignalChannel.SIGNALS):
                print(msg)
        """
        client = await self.get_async_client()
        pubsub = client.pubsub()
        await pubsub.subscribe(channel.value)
        
        logger.info(f"Subscribed to {channel.value}")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield message["data"]
        finally:
            await pubsub.unsubscribe(channel.value)
            logger.info(f"Unsubscribed from {channel.value}")
    
    async def subscribe_signals(self):
        """Subscribe to trading signals"""
        async for msg in self.subscribe(SignalChannel.SIGNALS):
            yield Signal.from_json(msg)
    
    async def subscribe_alerts(self):
        """Subscribe to alerts"""
        async for msg in self.subscribe(SignalChannel.ALERTS):
            yield Alert.from_json(msg)
    
    async def subscribe_prices(self, symbols: List[str] = None):
        """Subscribe to price updates, optionally filtered by symbols"""
        async for msg in self.subscribe(SignalChannel.PRICES):
            data = json.loads(msg)
            if symbols is None or data.get("symbol") in symbols:
                yield data
    
    async def subscribe_regime(self):
        """Subscribe to regime changes"""
        async for msg in self.subscribe(SignalChannel.REGIME):
            yield json.loads(msg)
    
    # -------------------------------------------------------------------------
    # Callback-based Subscriptions
    # -------------------------------------------------------------------------
    
    async def subscribe_with_callback(
        self,
        channel: SignalChannel,
        callback: Callable[[str], None],
    ) -> asyncio.Task:
        """
        Subscribe with callback function.
        Returns task that can be cancelled.
        """
        async def _subscriber():
            async for msg in self.subscribe(channel):
                try:
                    callback(msg)
                except Exception as e:
                    logger.error(f"Callback error: {e}")
        
        task = asyncio.create_task(_subscriber())
        self._subscriptions[channel.value] = task
        return task
    
    def cancel_subscription(self, channel: SignalChannel):
        """Cancel a callback subscription"""
        if channel.value in self._subscriptions:
            self._subscriptions[channel.value].cancel()
            del self._subscriptions[channel.value]
    
    # -------------------------------------------------------------------------
    # Multi-channel Subscription
    # -------------------------------------------------------------------------
    
    async def subscribe_multiple(self, channels: List[SignalChannel]):
        """Subscribe to multiple channels"""
        client = await self.get_async_client()
        pubsub = client.pubsub()
        
        for ch in channels:
            await pubsub.subscribe(ch.value)
        
        logger.info(f"Subscribed to {[c.value for c in channels]}")
        
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield {
                        "channel": message["channel"],
                        "data": message["data"]
                    }
        finally:
            for ch in channels:
                await pubsub.unsubscribe(ch.value)
    
    # -------------------------------------------------------------------------
    # Health & Stats
    # -------------------------------------------------------------------------
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis connection health"""
        try:
            client = await self.get_async_client()
            await client.ping()
            info = await client.info("clients")
            return {
                "status": "healthy",
                "connected_clients": info.get("connected_clients", 0),
                "host": self.host,
                "port": self.port,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "host": self.host,
                "port": self.port,
            }
    
    async def get_channel_stats(self) -> Dict[str, int]:
        """Get subscriber counts per channel"""
        client = await self.get_async_client()
        stats = {}
        for channel in SignalChannel:
            result = await client.pubsub_numsub(channel.value)
            stats[channel.value] = result.get(channel.value, 0) if result else 0
        return stats
    
    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------
    
    async def close(self):
        """Close all connections"""
        # Cancel all subscriptions
        for task in self._subscriptions.values():
            task.cancel()
        self._subscriptions.clear()
        
        # Close clients
        if self._async_client:
            await self._async_client.close()
            self._async_client = None
        
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None
        
        logger.info("RedisPubSub closed")


# -----------------------------------------------------------------------------
# Singleton instance
# -----------------------------------------------------------------------------

_pubsub_instance: Optional[RedisPubSub] = None


def get_pubsub() -> RedisPubSub:
    """Get singleton RedisPubSub instance"""
    global _pubsub_instance
    if _pubsub_instance is None:
        _pubsub_instance = RedisPubSub()
    return _pubsub_instance


# -----------------------------------------------------------------------------
# Example usage
# -----------------------------------------------------------------------------

async def example_publisher():
    """Example signal publisher"""
    pubsub = get_pubsub()
    
    signal = Signal(
        id="sig_001",
        type="buy",
        symbol="GLD",
        strategy="iron_condor",
        confidence=0.85,
        source="ensemble",
        timestamp=datetime.utcnow().isoformat(),
        data={
            "strikes": [240, 245, 250, 255],
            "expiry": "2025-01-17",
            "credit": 1.25,
        }
    )
    
    await pubsub.publish_signal(signal)
    print(f"Published signal: {signal.id}")


async def example_subscriber():
    """Example signal subscriber"""
    pubsub = get_pubsub()
    
    print("Listening for signals...")
    async for signal in pubsub.subscribe_signals():
        print(f"Received: {signal.id} - {signal.type} {signal.symbol}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "pub":
        asyncio.run(example_publisher())
    else:
        asyncio.run(example_subscriber())
