"""
gRPC Signal Service Implementation
Handles signal broadcasting between analysis and trading engines
"""

import asyncio
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, AsyncIterator
from collections import defaultdict
import os

import grpc
from concurrent import futures

# Will be generated from proto - using manual stubs for now
# from . import signals_pb2, signals_pb2_grpc

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Data Classes (matching proto messages)
# -----------------------------------------------------------------------------

class Signal:
    """Signal data class"""
    def __init__(
        self,
        id: str = None,
        type: str = "hold",
        symbol: str = "",
        strategy: str = "",
        confidence: float = 0.0,
        source: str = "",
        timestamp: str = None,
        data: dict = None,
        metadata: dict = None,
    ):
        self.id = id or f"sig_{uuid.uuid4().hex[:8]}"
        self.type = type
        self.symbol = symbol
        self.strategy = strategy
        self.confidence = confidence
        self.source = source
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.data = data or {}
        self.metadata = metadata or {}
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "symbol": self.symbol,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp,
            "data": self.data,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Signal":
        return cls(**data)


class SignalServiceImpl:
    """
    Signal Service implementation.
    
    Handles:
    - Signal publishing and storage
    - Subscription management
    - Signal filtering and delivery
    """
    
    def __init__(self):
        # In-memory signal store (recent signals)
        self._signals: Dict[str, Signal] = {}
        self._signal_history: List[Signal] = []
        self._max_history = 10000
        
        # Subscribers (channel -> list of queues)
        self._subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        
        # Stats
        self._signals_today = 0
        self._last_reset = datetime.utcnow().date()
        self._latencies: List[float] = []
        
        # Redis integration (optional)
        self._redis_pubsub = None
        
        logger.info("SignalService initialized")
    
    async def init_redis(self):
        """Initialize Redis pub/sub integration"""
        try:
            from ..redis import get_pubsub
            self._redis_pubsub = get_pubsub()
            logger.info("Redis pub/sub integration enabled")
        except ImportError:
            logger.warning("Redis pub/sub not available")
    
    def _reset_daily_stats(self):
        """Reset daily stats if needed"""
        today = datetime.utcnow().date()
        if today != self._last_reset:
            self._signals_today = 0
            self._last_reset = today
            self._latencies = []
    
    # -------------------------------------------------------------------------
    # Service Methods
    # -------------------------------------------------------------------------
    
    async def publish_signal(
        self,
        signal: Signal,
        broadcast: bool = True,
    ) -> tuple:
        """
        Publish a new signal.
        
        Returns:
            (success, signal_id, error)
        """
        start_time = datetime.utcnow()
        self._reset_daily_stats()
        
        try:
            # Store signal
            self._signals[signal.id] = signal
            self._signal_history.append(signal)
            
            # Trim history
            if len(self._signal_history) > self._max_history:
                old_signal = self._signal_history.pop(0)
                if old_signal.id in self._signals:
                    del self._signals[old_signal.id]
            
            # Update stats
            self._signals_today += 1
            
            # Broadcast to subscribers
            if broadcast:
                await self._broadcast_signal(signal)
            
            # Redis broadcast
            if self._redis_pubsub and broadcast:
                try:
                    from ..redis import Signal as RedisSignal
                    redis_signal = RedisSignal(
                        id=signal.id,
                        type=signal.type,
                        symbol=signal.symbol,
                        strategy=signal.strategy,
                        confidence=signal.confidence,
                        source=signal.source,
                        timestamp=signal.timestamp,
                        data=signal.data,
                    )
                    await self._redis_pubsub.publish_signal(redis_signal)
                except Exception as e:
                    logger.warning(f"Redis broadcast failed: {e}")
            
            # Track latency
            latency = (datetime.utcnow() - start_time).total_seconds() * 1000
            self._latencies.append(latency)
            if len(self._latencies) > 1000:
                self._latencies.pop(0)
            
            logger.info(f"Signal published: {signal.id} ({signal.type} {signal.symbol})")
            return (True, signal.id, None)
            
        except Exception as e:
            logger.error(f"Failed to publish signal: {e}")
            return (False, None, str(e))
    
    async def _broadcast_signal(self, signal: Signal):
        """Broadcast signal to all matching subscribers"""
        signal_dict = signal.to_dict()
        
        # Broadcast to symbol-specific subscribers
        channel = f"symbol:{signal.symbol}"
        for queue in self._subscribers.get(channel, []):
            await queue.put(signal_dict)
        
        # Broadcast to strategy-specific subscribers
        channel = f"strategy:{signal.strategy}"
        for queue in self._subscribers.get(channel, []):
            await queue.put(signal_dict)
        
        # Broadcast to all subscribers
        channel = "all"
        for queue in self._subscribers.get(channel, []):
            await queue.put(signal_dict)
    
    async def subscribe_signals(
        self,
        symbols: List[str] = None,
        strategies: List[str] = None,
        sources: List[str] = None,
        min_confidence: float = 0.0,
    ) -> AsyncIterator[Signal]:
        """
        Subscribe to signals stream.
        
        Yields signals matching the filter criteria.
        """
        queue = asyncio.Queue()
        channels = []
        
        # Determine channels to subscribe to
        if symbols:
            for symbol in symbols:
                channel = f"symbol:{symbol}"
                self._subscribers[channel].append(queue)
                channels.append(channel)
        elif strategies:
            for strategy in strategies:
                channel = f"strategy:{strategy}"
                self._subscribers[channel].append(queue)
                channels.append(channel)
        else:
            channel = "all"
            self._subscribers[channel].append(queue)
            channels.append(channel)
        
        logger.info(f"New subscriber on channels: {channels}")
        
        try:
            while True:
                signal_dict = await queue.get()
                signal = Signal.from_dict(signal_dict)
                
                # Apply filters
                if sources and signal.source not in sources:
                    continue
                if signal.confidence < min_confidence:
                    continue
                
                yield signal
        finally:
            # Clean up subscriptions
            for channel in channels:
                if queue in self._subscribers[channel]:
                    self._subscribers[channel].remove(queue)
    
    async def get_recent_signals(
        self,
        count: int = 100,
        symbol: str = None,
        strategy: str = None,
        since: str = None,
    ) -> List[Signal]:
        """Get recent signals with optional filtering"""
        signals = []
        
        # Filter by time if since is provided
        since_dt = None
        if since:
            try:
                since_dt = datetime.fromisoformat(since)
            except ValueError:
                pass
        
        for signal in reversed(self._signal_history):
            # Apply filters
            if symbol and signal.symbol != symbol:
                continue
            if strategy and signal.strategy != strategy:
                continue
            if since_dt:
                signal_dt = datetime.fromisoformat(signal.timestamp)
                if signal_dt < since_dt:
                    continue
            
            signals.append(signal)
            if len(signals) >= count:
                break
        
        return signals
    
    async def get_signal(self, signal_id: str) -> Optional[Signal]:
        """Get signal by ID"""
        return self._signals.get(signal_id)
    
    async def health_check(self) -> dict:
        """Service health check"""
        self._reset_daily_stats()
        
        avg_latency = (
            sum(self._latencies) / len(self._latencies)
            if self._latencies else 0.0
        )
        
        return {
            "healthy": True,
            "status": "running",
            "signals_today": self._signals_today,
            "avg_latency_ms": round(avg_latency, 2),
            "subscribers": sum(len(subs) for subs in self._subscribers.values()),
            "cached_signals": len(self._signals),
        }


# -----------------------------------------------------------------------------
# gRPC Server
# -----------------------------------------------------------------------------

class SignalServiceGRPC:
    """gRPC server wrapper for SignalService"""
    
    def __init__(self, service: SignalServiceImpl = None):
        self.service = service or SignalServiceImpl()
        self.server = None
    
    async def start(self, port: int = 50051):
        """Start gRPC server"""
        self.server = grpc.aio.server(
            futures.ThreadPoolExecutor(max_workers=10)
        )
        
        # Add service (would use generated code in production)
        # signals_pb2_grpc.add_SignalServiceServicer_to_server(
        #     self.service, self.server
        # )
        
        listen_addr = f"[::]:{port}"
        self.server.add_insecure_port(listen_addr)
        
        await self.server.start()
        logger.info(f"SignalService gRPC server started on {listen_addr}")
        
        # Initialize Redis
        await self.service.init_redis()
    
    async def stop(self):
        """Stop gRPC server"""
        if self.server:
            await self.server.stop(grace=5)
            logger.info("SignalService gRPC server stopped")


# -----------------------------------------------------------------------------
# Standalone Server
# -----------------------------------------------------------------------------

async def serve():
    """Run standalone signal service"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    
    port = int(os.getenv("SIGNAL_SERVICE_PORT", "50051"))
    
    grpc_server = SignalServiceGRPC()
    await grpc_server.start(port)
    
    # Keep running
    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        await grpc_server.stop()


if __name__ == "__main__":
    asyncio.run(serve())
