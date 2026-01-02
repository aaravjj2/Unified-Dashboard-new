"""
WebSocket Service for Real-time Updates
Implements #269 from ROADMAP_ULTIMATE.md
"""
import asyncio
import json
import logging
from typing import Dict, List, Set, Callable, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import threading
from queue import Queue
import time

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """WebSocket message types"""
    PRICE_UPDATE = "price_update"
    OPTIONS_UPDATE = "options_update"
    ALERT = "alert"
    NEWS = "news"
    PORTFOLIO_UPDATE = "portfolio_update"
    ORDER_UPDATE = "order_update"
    MARKET_STATUS = "market_status"
    HEARTBEAT = "heartbeat"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    ERROR = "error"


@dataclass
class WSMessage:
    """WebSocket message structure"""
    type: MessageType
    data: Dict[str, Any]
    timestamp: str = None
    channel: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_json(self) -> str:
        return json.dumps({
            'type': self.type.value,
            'data': self.data,
            'timestamp': self.timestamp,
            'channel': self.channel
        })
    
    @classmethod
    def from_json(cls, json_str: str) -> 'WSMessage':
        data = json.loads(json_str)
        return cls(
            type=MessageType(data['type']),
            data=data['data'],
            timestamp=data.get('timestamp'),
            channel=data.get('channel')
        )


class WebSocketManager:
    """
    Manages WebSocket connections and real-time updates
    For use with Dash/Flask applications
    """
    
    def __init__(self):
        self.clients: Set[str] = set()
        self.subscriptions: Dict[str, Set[str]] = {}  # channel -> client_ids
        self.message_queue: Queue = Queue()
        self.handlers: Dict[MessageType, List[Callable]] = {}
        self.is_running = False
        self._lock = threading.Lock()
        
        # Price cache for debouncing
        self.price_cache: Dict[str, Dict] = {}
        self.last_update: Dict[str, float] = {}
        self.update_interval = 0.5  # Min seconds between updates
        
    def register_handler(self, msg_type: MessageType, 
                        handler: Callable[[WSMessage], None]):
        """Register a message handler"""
        if msg_type not in self.handlers:
            self.handlers[msg_type] = []
        self.handlers[msg_type].append(handler)
        
    def subscribe(self, client_id: str, channel: str):
        """Subscribe client to a channel"""
        with self._lock:
            if channel not in self.subscriptions:
                self.subscriptions[channel] = set()
            self.subscriptions[channel].add(client_id)
            self.clients.add(client_id)
            logger.info(f"Client {client_id} subscribed to {channel}")
            
    def unsubscribe(self, client_id: str, channel: str = None):
        """Unsubscribe client from channel(s)"""
        with self._lock:
            if channel:
                if channel in self.subscriptions:
                    self.subscriptions[channel].discard(client_id)
            else:
                # Unsubscribe from all
                for ch in self.subscriptions.values():
                    ch.discard(client_id)
                self.clients.discard(client_id)
                
    def broadcast(self, message: WSMessage, channel: str = None):
        """Broadcast message to subscribers"""
        message.channel = channel
        self.message_queue.put(message)
        
    def send_price_update(self, ticker: str, price: float, 
                         change: float = None, volume: int = None):
        """Send price update with debouncing"""
        now = time.time()
        key = f"price_{ticker}"
        
        # Debounce
        if key in self.last_update:
            if now - self.last_update[key] < self.update_interval:
                # Update cache only
                self.price_cache[ticker] = {
                    'price': price,
                    'change': change,
                    'volume': volume
                }
                return
        
        self.last_update[key] = now
        
        message = WSMessage(
            type=MessageType.PRICE_UPDATE,
            data={
                'ticker': ticker,
                'price': price,
                'change': change,
                'change_pct': (change / (price - change) * 100) if change and price != change else 0,
                'volume': volume
            }
        )
        self.broadcast(message, f"prices:{ticker}")
        
    def send_options_update(self, ticker: str, options_data: Dict):
        """Send options chain update"""
        message = WSMessage(
            type=MessageType.OPTIONS_UPDATE,
            data={
                'ticker': ticker,
                'chain': options_data
            }
        )
        self.broadcast(message, f"options:{ticker}")
        
    def send_alert(self, alert_type: str, title: str, 
                  message_text: str, severity: str = 'info',
                  ticker: str = None):
        """Send alert notification"""
        message = WSMessage(
            type=MessageType.ALERT,
            data={
                'alert_type': alert_type,
                'title': title,
                'message': message_text,
                'severity': severity,
                'ticker': ticker
            }
        )
        self.broadcast(message, "alerts")
        
    def send_portfolio_update(self, portfolio_data: Dict):
        """Send portfolio update"""
        message = WSMessage(
            type=MessageType.PORTFOLIO_UPDATE,
            data=portfolio_data
        )
        self.broadcast(message, "portfolio")
        
    def send_order_update(self, order_data: Dict):
        """Send order status update"""
        message = WSMessage(
            type=MessageType.ORDER_UPDATE,
            data=order_data
        )
        self.broadcast(message, "orders")
        
    def send_news(self, news_item: Dict):
        """Send news update"""
        message = WSMessage(
            type=MessageType.NEWS,
            data=news_item
        )
        self.broadcast(message, f"news:{news_item.get('ticker', 'market')}")
        
    def send_market_status(self, status: str, details: Dict = None):
        """Send market status update"""
        message = WSMessage(
            type=MessageType.MARKET_STATUS,
            data={
                'status': status,
                'details': details or {}
            }
        )
        self.broadcast(message, "market")
        
    def get_subscribers(self, channel: str) -> Set[str]:
        """Get subscribers for a channel"""
        return self.subscriptions.get(channel, set())
    
    def get_pending_messages(self, max_messages: int = 100) -> List[WSMessage]:
        """Get pending messages from queue"""
        messages = []
        while not self.message_queue.empty() and len(messages) < max_messages:
            try:
                messages.append(self.message_queue.get_nowait())
            except:
                break
        return messages


class DashWebSocketCallback:
    """
    WebSocket-like behavior for Dash using intervals
    Since Dash doesn't support true WebSocket, we simulate it
    """
    
    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self.client_data: Dict[str, Dict] = {}
        
    def get_update_data(self, client_id: str) -> Dict[str, Any]:
        """Get accumulated updates for a client"""
        messages = self.ws_manager.get_pending_messages()
        
        updates = {
            'prices': {},
            'options': {},
            'alerts': [],
            'news': [],
            'portfolio': None,
            'orders': [],
            'market_status': None
        }
        
        for msg in messages:
            if msg.type == MessageType.PRICE_UPDATE:
                ticker = msg.data.get('ticker')
                if ticker:
                    updates['prices'][ticker] = msg.data
                    
            elif msg.type == MessageType.OPTIONS_UPDATE:
                ticker = msg.data.get('ticker')
                if ticker:
                    updates['options'][ticker] = msg.data.get('chain')
                    
            elif msg.type == MessageType.ALERT:
                updates['alerts'].append(msg.data)
                
            elif msg.type == MessageType.NEWS:
                updates['news'].append(msg.data)
                
            elif msg.type == MessageType.PORTFOLIO_UPDATE:
                updates['portfolio'] = msg.data
                
            elif msg.type == MessageType.ORDER_UPDATE:
                updates['orders'].append(msg.data)
                
            elif msg.type == MessageType.MARKET_STATUS:
                updates['market_status'] = msg.data
        
        return updates
    
    def create_interval_callback(self, interval_ms: int = 1000):
        """
        Create Dash interval callback component data
        Returns dict with callback input/output specs
        """
        return {
            'interval_component': {
                'type': 'dcc.Interval',
                'id': 'ws-interval',
                'interval': interval_ms,
                'n_intervals': 0
            },
            'store_component': {
                'type': 'dcc.Store',
                'id': 'ws-data-store',
                'data': {}
            }
        }


class PriceStreamer:
    """
    Simulates price streaming for demo/testing
    """
    
    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self.tickers: Dict[str, float] = {}
        self.is_streaming = False
        self._thread = None
        
    def add_ticker(self, ticker: str, initial_price: float):
        """Add ticker to stream"""
        self.tickers[ticker] = initial_price
        
    def remove_ticker(self, ticker: str):
        """Remove ticker from stream"""
        self.tickers.pop(ticker, None)
        
    def start(self, interval: float = 1.0):
        """Start streaming"""
        self.is_streaming = True
        self._thread = threading.Thread(target=self._stream_loop, args=(interval,))
        self._thread.daemon = True
        self._thread.start()
        
    def stop(self):
        """Stop streaming"""
        self.is_streaming = False
        if self._thread:
            self._thread.join(timeout=2)
            
    def _stream_loop(self, interval: float):
        """Main streaming loop"""
        import random
        
        while self.is_streaming:
            for ticker, price in list(self.tickers.items()):
                # Simulate price movement
                change_pct = random.gauss(0, 0.001)  # 0.1% std dev
                new_price = price * (1 + change_pct)
                change = new_price - price
                
                self.tickers[ticker] = new_price
                
                self.ws_manager.send_price_update(
                    ticker=ticker,
                    price=new_price,
                    change=change,
                    volume=random.randint(1000, 100000)
                )
            
            time.sleep(interval)


# Global instances
_ws_manager = None
_dash_callback = None

def get_ws_manager() -> WebSocketManager:
    global _ws_manager
    if _ws_manager is None:
        _ws_manager = WebSocketManager()
    return _ws_manager

def get_dash_callback() -> DashWebSocketCallback:
    global _dash_callback
    if _dash_callback is None:
        _dash_callback = DashWebSocketCallback(get_ws_manager())
    return _dash_callback


# Dash components for real-time updates
def create_realtime_components():
    """
    Create Dash components for real-time updates
    Returns HTML/components to be added to layout
    """
    return """
    // Real-time update handler
    window.dashRealtime = {
        prices: {},
        callbacks: [],
        
        onPriceUpdate: function(callback) {
            this.callbacks.push(callback);
        },
        
        updatePrice: function(ticker, data) {
            this.prices[ticker] = data;
            this.callbacks.forEach(cb => cb(ticker, data));
        }
    };
    """
