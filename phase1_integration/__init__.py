"""
Phase 1 Integration Package for Alpaca Options Lab

Containerization & Data Fabric Infrastructure
"""

__version__ = "1.0.0"

# Import submodules lazily to avoid circular imports
def get_pubsub():
    """Get Redis PubSub instance"""
    from .redis_client.pubsub import RedisPubSub
    return RedisPubSub()


def get_streams():
    """Get Redis Streams instance"""
    from .redis_client.streams import RedisStreams
    return RedisStreams()


def get_loader():
    """Get TimescaleDB loader instance"""
    from .timescale.loader import TimescaleLoader
    return TimescaleLoader()


__all__ = [
    "get_pubsub",
    "get_streams",
    "get_loader",
    "__version__",
]
