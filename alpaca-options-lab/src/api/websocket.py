"""
WebSocket Manager for Real-time Updates

Provides Socket.IO based real-time communication:
- Portfolio updates
- Position changes
- Order fills
- Price updates
- Risk alerts
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Set, Optional
from dataclasses import dataclass, field
import json

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class WebSocketClient:
    """Represents a connected WebSocket client"""
    sid: str
    user_id: str
    subscriptions: Set[str] = field(default_factory=set)
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class WebSocketManager:
    """
    Manages WebSocket connections and real-time updates.
    
    Channels:
    - portfolio: Portfolio value updates
    - positions: Position changes
    - orders: Order status updates
    - prices: Real-time price quotes
    - greeks: Live Greeks updates
    - alerts: Risk alerts and notifications
    - system: System status updates
    """
    
    CHANNELS = {
        "portfolio",
        "positions", 
        "orders",
        "prices",
        "greeks",
        "alerts",
        "system",
    }
    
    def __init__(self):
        self.clients: Dict[str, WebSocketClient] = {}
        self.channel_subscribers: Dict[str, Set[str]] = {
            ch: set() for ch in self.CHANNELS
        }
        self._sio = None
        self._background_tasks: Dict[str, asyncio.Task] = {}
        
    def set_socketio(self, sio):
        """Set the Socket.IO server instance"""
        self._sio = sio
        
    async def connect(self, sid: str, user_id: str):
        """Handle client connection"""
        client = WebSocketClient(sid=sid, user_id=user_id)
        self.clients[sid] = client
        
        logger.info(
            "websocket_client_connected",
            sid=sid,
            user_id=user_id,
            total_clients=len(self.clients),
        )
        
        # Send welcome message
        await self._emit(sid, "connected", {
            "message": "Connected to trading server",
            "available_channels": list(self.CHANNELS),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
    async def disconnect(self, sid: str):
        """Handle client disconnection"""
        if sid not in self.clients:
            return
            
        client = self.clients[sid]
        
        # Remove from all channels
        for channel in client.subscriptions:
            self.channel_subscribers[channel].discard(sid)
            
        del self.clients[sid]
        
        logger.info(
            "websocket_client_disconnected",
            sid=sid,
            total_clients=len(self.clients),
        )
        
    async def subscribe(self, sid: str, channels: list):
        """Subscribe client to channels"""
        if sid not in self.clients:
            return
            
        client = self.clients[sid]
        
        for channel in channels:
            if channel in self.CHANNELS:
                client.subscriptions.add(channel)
                self.channel_subscribers[channel].add(sid)
                
        logger.info(
            "websocket_subscribe",
            sid=sid,
            channels=channels,
        )
        
        await self._emit(sid, "subscribed", {
            "channels": list(client.subscriptions),
        })
        
    async def unsubscribe(self, sid: str, channels: list):
        """Unsubscribe client from channels"""
        if sid not in self.clients:
            return
            
        client = self.clients[sid]
        
        for channel in channels:
            client.subscriptions.discard(channel)
            self.channel_subscribers[channel].discard(sid)
            
        logger.info(
            "websocket_unsubscribe",
            sid=sid,
            channels=channels,
        )
        
    async def broadcast_to_channel(self, channel: str, event: str, data: Dict[str, Any]):
        """Broadcast message to all subscribers of a channel"""
        if channel not in self.CHANNELS:
            logger.warning("invalid_channel", channel=channel)
            return
            
        subscribers = self.channel_subscribers[channel]
        if not subscribers:
            return
            
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        data["channel"] = channel
        
        for sid in subscribers:
            await self._emit(sid, event, data)
            
        logger.debug(
            "channel_broadcast",
            channel=channel,
            event=event,
            recipient_count=len(subscribers),
        )
        
    async def send_to_user(self, user_id: str, event: str, data: Dict[str, Any]):
        """Send message to specific user (all their connections)"""
        data["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        for sid, client in self.clients.items():
            if client.user_id == user_id:
                await self._emit(sid, event, data)
                
    async def _emit(self, sid: str, event: str, data: Dict[str, Any]):
        """Emit event to specific client"""
        if self._sio:
            await self._sio.emit(event, data, room=sid)
        else:
            # Fallback for testing without Socket.IO
            logger.debug("emit_mock", sid=sid, event=event, data=data)
            
    # =========================================================================
    # EVENT EMITTERS
    # =========================================================================
    
    async def emit_portfolio_update(self, portfolio_data: Dict[str, Any]):
        """Emit portfolio value update"""
        await self.broadcast_to_channel("portfolio", "portfolio_update", {
            "total_value": portfolio_data.get("total_value"),
            "day_pnl": portfolio_data.get("day_pnl"),
            "day_pnl_pct": portfolio_data.get("day_pnl_pct"),
            "buying_power": portfolio_data.get("buying_power"),
        })
        
    async def emit_position_update(self, position_data: Dict[str, Any]):
        """Emit position change"""
        await self.broadcast_to_channel("positions", "position_update", {
            "action": position_data.get("action"),  # opened, closed, adjusted
            "position": position_data,
        })
        
    async def emit_order_update(self, order_data: Dict[str, Any]):
        """Emit order status change"""
        await self.broadcast_to_channel("orders", "order_update", {
            "order_id": order_data.get("order_id"),
            "status": order_data.get("status"),
            "filled_qty": order_data.get("filled_qty"),
            "avg_price": order_data.get("avg_price"),
            "order": order_data,
        })
        
    async def emit_price_update(self, symbol: str, price_data: Dict[str, Any]):
        """Emit price quote update"""
        await self.broadcast_to_channel("prices", "price_update", {
            "symbol": symbol,
            "bid": price_data.get("bid"),
            "ask": price_data.get("ask"),
            "last": price_data.get("last"),
            "volume": price_data.get("volume"),
        })
        
    async def emit_greeks_update(self, greeks_data: Dict[str, Any]):
        """Emit portfolio Greeks update"""
        await self.broadcast_to_channel("greeks", "greeks_update", {
            "portfolio_delta": greeks_data.get("delta"),
            "portfolio_gamma": greeks_data.get("gamma"),
            "portfolio_theta": greeks_data.get("theta"),
            "portfolio_vega": greeks_data.get("vega"),
        })
        
    async def emit_risk_alert(self, alert_data: Dict[str, Any]):
        """Emit risk alert"""
        await self.broadcast_to_channel("alerts", "risk_alert", {
            "severity": alert_data.get("severity"),  # warning, critical
            "type": alert_data.get("type"),
            "message": alert_data.get("message"),
            "threshold": alert_data.get("threshold"),
            "current_value": alert_data.get("current_value"),
        })
        
    async def emit_system_status(self, status_data: Dict[str, Any]):
        """Emit system status update"""
        await self.broadcast_to_channel("system", "system_status", status_data)
        
    # =========================================================================
    # BACKGROUND TASKS
    # =========================================================================
    
    async def start_background_tasks(self):
        """Start background update tasks"""
        self._background_tasks["heartbeat"] = asyncio.create_task(
            self._heartbeat_loop()
        )
        self._background_tasks["portfolio_updates"] = asyncio.create_task(
            self._portfolio_update_loop()
        )
        logger.info("websocket_background_tasks_started")
        
    async def stop_background_tasks(self):
        """Stop background update tasks"""
        for name, task in self._background_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._background_tasks.clear()
        logger.info("websocket_background_tasks_stopped")
        
    async def _heartbeat_loop(self):
        """Send periodic heartbeats to detect disconnected clients"""
        while True:
            await asyncio.sleep(30)
            
            now = datetime.now(timezone.utc)
            stale_clients = []
            
            for sid, client in self.clients.items():
                # Check for stale connections
                if (now - client.last_heartbeat).seconds > 120:
                    stale_clients.append(sid)
                else:
                    await self._emit(sid, "heartbeat", {
                        "server_time": now.isoformat(),
                    })
                    
            # Disconnect stale clients
            for sid in stale_clients:
                await self.disconnect(sid)
                
    async def _portfolio_update_loop(self):
        """Periodically fetch and broadcast portfolio updates"""
        while True:
            await asyncio.sleep(5)  # Update every 5 seconds
            
            if not self.channel_subscribers["portfolio"]:
                continue
                
            # Mock portfolio data - replace with actual fetching
            await self.emit_portfolio_update({
                "total_value": 125000.0,
                "day_pnl": 1250.0,
                "day_pnl_pct": 1.0,
                "buying_power": 45000.0,
            })
            
    def handle_heartbeat_response(self, sid: str):
        """Handle heartbeat response from client"""
        if sid in self.clients:
            self.clients[sid].last_heartbeat = datetime.now(timezone.utc)


# Global instance
websocket_manager = WebSocketManager()


def setup_socketio_handlers(sio):
    """Setup Socket.IO event handlers"""
    
    websocket_manager.set_socketio(sio)
    
    @sio.on("connect")
    async def handle_connect(sid, environ):
        # Extract user_id from auth or session
        user_id = environ.get("HTTP_X_USER_ID", "anonymous")
        await websocket_manager.connect(sid, user_id)
        
    @sio.on("disconnect")
    async def handle_disconnect(sid):
        await websocket_manager.disconnect(sid)
        
    @sio.on("subscribe")
    async def handle_subscribe(sid, data):
        channels = data.get("channels", [])
        await websocket_manager.subscribe(sid, channels)
        
    @sio.on("unsubscribe")
    async def handle_unsubscribe(sid, data):
        channels = data.get("channels", [])
        await websocket_manager.unsubscribe(sid, channels)
        
    @sio.on("heartbeat")
    async def handle_heartbeat(sid, data):
        websocket_manager.handle_heartbeat_response(sid)
        
    return sio
