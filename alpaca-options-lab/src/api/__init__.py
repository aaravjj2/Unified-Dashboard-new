"""
API Module - FastAPI Backend for Options Lab

Provides REST API and WebSocket endpoints for:
- Portfolio management
- Strategy configuration
- Risk monitoring
- Real-time updates
"""

from src.api.websocket import WebSocketManager, websocket_manager
from src.api.main import create_app, app
from src.api.routes import portfolio, strategies, risk, orders, analytics

__all__ = [
    "create_app",
    "app",
    "WebSocketManager",
    "websocket_manager",
]
