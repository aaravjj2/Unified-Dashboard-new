import threading
import json
import logging
from typing import Callable, Any

logger = logging.getLogger(__name__)

class WebSocketConnector:
    """Lightweight WebSocket-like connector using server-sent events fallback.
    This is a stub: if backend supports an SSE or websocket endpoint, it can
    be used to push updates to the UI cache. For now it exposes subscribe(callback).
    """
    def __init__(self):
        self._callbacks = []

    def subscribe(self, cb: Callable[[str, Any], None]):
        self._callbacks.append(cb)

    def _emit(self, channel: str, payload: Any):
        for cb in self._callbacks:
            try:
                cb(channel, payload)
            except Exception as e:
                logger.exception('Callback error')

    # Example helper to simulate incoming messages (used in dev/test)
    def simulate_message(self, channel: str, payload: Any):
        self._emit(channel, payload)

# Global connector instance
connector = WebSocketConnector()
