"""
WebSocket Streaming Server for Real-Time Predictions
Mission A4 Phase 2: Real-Time Streaming & CI/CD Deployment

Architecture:
- FastAPI WebSocket endpoint at /ws/predictions
- Subscription-based model: clients subscribe to specific tickers
- Broadcasts predictions every 5-10 seconds
- Integrates with cache_manager for efficient predictions
- Supports multiple concurrent clients

Message Format:
{
    "ticker": "AAPL",
    "prediction": 0,
    "confidence": 0.85,
    "timestamp": "2025-10-23T12:34:56.789012"
}
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, Set, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import numpy as np

from services.cache_manager import get_cache_manager
from ml import model_registry
import numpy as np


def predict(model, features: np.ndarray) -> dict:
    """
    Simple prediction wrapper for sklearn models
    
    Args:
        model: Trained sklearn model
        features: Feature array
    
    Returns:
        dict with prediction and confidence
    """
    if model is None:
        return {"prediction": 0, "confidence": 0.5}
    
    prediction = int(model.predict(features.reshape(1, -1))[0])
    
    # Get confidence from predict_proba
    if hasattr(model, 'predict_proba'):
        proba = model.predict_proba(features.reshape(1, -1))[0]
        confidence = float(proba[prediction])
    else:
        confidence = 0.5
    
    return {
        "prediction": prediction,
        "confidence": confidence
    }


# Global state
active_connections: Dict[WebSocket, Set[str]] = {}  # WebSocket -> subscribed tickers
model = None
model_info = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown logic for loading model"""
    global model, model_info
    
    # Load model on startup - get latest production model
    # For Phase 2, we'll use a simple test model
    # In production, this would query the registry for production models
    all_models = model_registry.get_all_models()
    
    if all_models:
        # Get the latest model
        latest = sorted(all_models, key=lambda x: x.get("timestamp", ""), reverse=True)[0]
        model_info = latest
        
        # Load the model file
        model_path = latest.get("model_path")
        if model_path and os.path.exists(model_path):
            import joblib
            model = joblib.load(model_path)
            print(f"✅ Loaded model: {latest['model_name']} v{latest['version']}")
        else:
            print(f"⚠️  Model path not found: {model_path}")
    else:
        print("⚠️  No models found in registry")
    
    yield
    
    # Cleanup on shutdown
    print("🔌 Shutting down streaming server")


# Create FastAPI app
app = FastAPI(
    title="Market Trends Streaming Service",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConnectionManager:
    """Manages WebSocket connections and subscriptions"""
    
    def __init__(self):
        self.active_connections: Dict[WebSocket, Set[str]] = {}
        self.broadcast_task = None
    
    async def connect(self, websocket: WebSocket):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections[websocket] = set()
        print(f"✅ New connection: {len(self.active_connections)} total")
    
    def disconnect(self, websocket: WebSocket):
        """Remove disconnected client"""
        if websocket in self.active_connections:
            del self.active_connections[websocket]
            print(f"🔌 Disconnected: {len(self.active_connections)} remaining")
    
    def subscribe(self, websocket: WebSocket, tickers: List[str]):
        """Subscribe client to ticker updates"""
        if websocket in self.active_connections:
            self.active_connections[websocket].update(tickers)
            print(f"📊 Subscribed to: {tickers}")
    
    def unsubscribe(self, websocket: WebSocket, tickers: List[str]):
        """Unsubscribe client from ticker updates"""
        if websocket in self.active_connections:
            for ticker in tickers:
                self.active_connections[websocket].discard(ticker)
            print(f"🔕 Unsubscribed from: {tickers}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"❌ Error sending to client: {e}")
    
    async def broadcast_predictions(self):
        """Continuously broadcast predictions to all subscribed clients"""
        cache_manager = get_cache_manager()
        
        while True:
            try:
                # Collect all unique tickers across all clients
                all_tickers = set()
                for tickers in self.active_connections.values():
                    all_tickers.update(tickers)
                
                if not all_tickers or not model:
                    await asyncio.sleep(5)
                    continue
                
                # Generate predictions for each ticker
                for ticker in all_tickers:
                    prediction_data = await self._generate_prediction(ticker, cache_manager)
                    
                    # Send to all clients subscribed to this ticker
                    for websocket, subscribed_tickers in self.active_connections.items():
                        if ticker in subscribed_tickers:
                            await self.send_personal_message(prediction_data, websocket)
                
                # Wait 5-10 seconds before next broadcast
                await asyncio.sleep(np.random.uniform(5, 10))
                
            except Exception as e:
                print(f"❌ Broadcast error: {e}")
                await asyncio.sleep(5)
    
    async def _generate_prediction(self, ticker: str, cache_manager) -> dict:
        """Generate prediction for ticker with cache integration"""
        # Generate sample features (in production, fetch from data source)
        features = self._generate_sample_features(ticker)
        
        # Check cache first
        cache_key = cache_manager.generate_cache_key(
            model_name=model_info["model_name"] if model_info else "unknown",
            version=model_info["version"] if model_info else "v0",
            features=features
        )
        
        cached_result = cache_manager.prediction_cache.get(cache_key)
        
        if cached_result:
            # Use cached prediction
            prediction = cached_result["prediction"]
            confidence = cached_result["confidence"]
            print(f"📦 Cache hit for {ticker}")
        else:
            # Generate new prediction
            result = predict(model, features)
            prediction = int(result["prediction"])
            confidence = float(result["confidence"])
            
            # Cache the result
            cache_manager.prediction_cache.set(cache_key, {
                "prediction": prediction,
                "confidence": confidence
            })
            print(f"🔮 New prediction for {ticker}")
        
        return {
            "ticker": ticker,
            "prediction": prediction,
            "confidence": round(confidence, 4),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _generate_sample_features(self, ticker: str) -> np.ndarray:
        """Generate sample feature vector for testing"""
        # In production, fetch real market data
        # For now, generate random features based on ticker hash
        np.random.seed(hash(ticker) % 2**32)
        return np.random.rand(10)  # 10 features
    
    def start_broadcasting(self):
        """Start background task for broadcasting predictions"""
        if self.broadcast_task is None or self.broadcast_task.done():
            self.broadcast_task = asyncio.create_task(self.broadcast_predictions())
            print("📡 Broadcasting started")


# Global connection manager
manager = ConnectionManager()


@app.on_event("startup")
async def startup_event():
    """Start broadcasting on app startup"""
    manager.start_broadcasting()


@app.websocket("/ws/predictions")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time prediction streaming
    
    Client sends:
        {"action": "subscribe", "tickers": ["AAPL", "GOOGL"]}
        {"action": "unsubscribe", "tickers": ["AAPL"]}
    
    Server sends:
        {"ticker": "AAPL", "prediction": 0, "confidence": 0.85, "timestamp": "..."}
    """
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive subscription commands from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            action = message.get("action")
            tickers = message.get("tickers", [])
            
            if action == "subscribe":
                manager.subscribe(websocket, tickers)
            elif action == "unsubscribe":
                manager.unsubscribe(websocket, tickers)
            else:
                await manager.send_personal_message({
                    "error": f"Unknown action: {action}"
                }, websocket)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        manager.disconnect(websocket)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_connections": len(manager.active_connections),
        "model_loaded": model is not None,
        "model_info": model_info
    }


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Market Trends Streaming Service",
        "version": "1.0.0",
        "endpoints": {
            "websocket": "/ws/predictions",
            "health": "/health"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
