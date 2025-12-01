"""
Market Trends Backend Integration Module
Mission A1B: Integrate Dashboard with Agent 2's REST & WebSocket Endpoints

This module provides functions to:
1. Fetch predictions from REST endpoints (/api/predict, /api/batch_predict)
2. Subscribe to WebSocket streaming (/ws/predictions)
3. Handle cache fallback when endpoints fail
4. Map predictions to dashboard table rows

Agent 2 Endpoints:
- REST: http://localhost:8000/api/predict
- REST: http://localhost:8000/api/batch_predict
- WebSocket: ws://localhost:8000/ws/predictions
"""

import requests
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import websockets
from threading import Thread
import time

logger = logging.getLogger(__name__)

# Backend service configuration
MODEL_SERVICE_URL = "http://localhost:8000"
REST_PREDICT_URL = f"{MODEL_SERVICE_URL}/api/predict"
REST_BATCH_URL = f"{MODEL_SERVICE_URL}/api/batch_predict"
WS_PREDICTIONS_URL = "ws://localhost:8000/ws/predictions"

# Global cache for predictions
PREDICTION_CACHE: Dict[str, Dict[str, Any]] = {}


def update_prediction_from_rest(ticker: str, prediction_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a single prediction from REST API response
    
    Args:
        ticker: Stock ticker symbol
        prediction_data: Prediction response from /api/predict
    
    Returns:
        Dictionary with ticker, prediction, confidence, and metadata
    """
    try:
        result = {
            'ticker': ticker,
            'prediction': prediction_data.get('prediction'),
            'confidence': prediction_data.get('confidence'),
            'model_version': prediction_data.get('model_version'),
            'timestamp': prediction_data.get('timestamp', datetime.utcnow().isoformat()),
            'cached': prediction_data.get('cached', False)
        }
        
        # Update cache
        PREDICTION_CACHE[ticker] = result
        
        logger.info(f"Updated prediction for {ticker}: {result['prediction']} ({result['confidence']:.2%})")
        return result
    
    except Exception as e:
        logger.error(f"Error updating prediction for {ticker}: {e}")
        raise


def fetch_single_prediction(ticker: str, features: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    Fetch single prediction from /api/predict
    
    Args:
        ticker: Stock ticker symbol
        features: Optional feature dictionary (if None, use defaults)
    
    Returns:
        Prediction data dictionary
    """
    try:
        # Default features if not provided
        if features is None:
            features = {
                "price_momentum": 0.0,
                "price_change_pct": 0.0,
                "volume_change": 0.0,
                "volatility": 0.0,
                "sentiment": 0.0
            }
        
        # Call REST endpoint
        response = requests.post(
            REST_PREDICT_URL,
            json=features,
            timeout=5
        )
        
        if response.status_code == 200:
            prediction_data = response.json()
            return update_prediction_from_rest(ticker, prediction_data)
        else:
            logger.warning(f"Prediction request failed for {ticker}: {response.status_code}")
            return None
    
    except Exception as e:
        logger.error(f"Error fetching prediction for {ticker}: {e}")
        return None


def update_predictions_batch(predictions: List[Dict[str, Any]], all_tickers: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    Update multiple predictions from batch response
    
    Args:
        predictions: List of prediction dictionaries from /api/batch_predict
        all_tickers: Optional list of all expected tickers (for handling missing ones)
    
    Returns:
        List of updated prediction dictionaries
    """
    results = []
    
    try:
        # Update predictions that were returned
        for pred in predictions:
            ticker = pred.get('ticker')
            if ticker:
                result = {
                    'ticker': ticker,
                    'prediction': pred.get('prediction'),
                    'confidence': pred.get('confidence'),
                    'timestamp': pred.get('timestamp', datetime.utcnow().isoformat()),
                    'cached': pred.get('cached', False)
                }
                
                # Update cache
                PREDICTION_CACHE[ticker] = result
                results.append(result)
        
        # Handle missing tickers if all_tickers provided
        if all_tickers:
            returned_tickers = {pred.get('ticker') for pred in predictions}
            missing_tickers = set(all_tickers) - returned_tickers
            
            for ticker in missing_tickers:
                # Use cached value or placeholder
                if ticker in PREDICTION_CACHE:
                    cached_pred = PREDICTION_CACHE[ticker].copy()
                    cached_pred['cached'] = True
                    results.append(cached_pred)
                    logger.info(f"Using cached prediction for missing ticker {ticker}")
                else:
                    # Placeholder for missing ticker
                    results.append({
                        'ticker': ticker,
                        'prediction': None,
                        'confidence': None,
                        'timestamp': datetime.utcnow().isoformat(),
                        'cached': False,
                        'missing': True
                    })
                    logger.warning(f"No prediction available for {ticker}")
        
        logger.info(f"Updated {len(results)} predictions")
        return results
    
    except Exception as e:
        logger.error(f"Error updating batch predictions: {e}")
        raise


def fetch_batch_predictions(tickers: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch batch predictions from /api/batch_predict
    
    Args:
        tickers: List of stock ticker symbols
    
    Returns:
        List of prediction dictionaries
    """
    try:
        # Prepare batch request (simplified - real implementation would include features)
        request_data = {
            "requests": [{"features": {}} for _ in tickers]  # Placeholder features
        }
        
        response = requests.post(
            REST_BATCH_URL,
            json=request_data,
            timeout=10
        )
        
        if response.status_code == 200:
            batch_data = response.json()
            predictions = batch_data.get('predictions', [])
            
            # Add ticker info if not in response
            for i, pred in enumerate(predictions):
                if 'ticker' not in pred and i < len(tickers):
                    pred['ticker'] = tickers[i]
            
            return update_predictions_batch(predictions, all_tickers=tickers)
        else:
            logger.warning(f"Batch prediction request failed: {response.status_code}")
            return []
    
    except Exception as e:
        logger.error(f"Error fetching batch predictions: {e}")
        return []


def get_prediction_with_fallback(ticker: str, cache: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Get prediction with automatic fallback to cache on failure
    
    Args:
        ticker: Stock ticker symbol
        cache: Optional external cache dictionary
    
    Returns:
        Prediction dictionary (from API or cache)
    """
    try:
        # Try to fetch from REST API
        prediction = fetch_single_prediction(ticker)
        
        if prediction:
            return prediction
        
        # Fallback to cache
        if cache and ticker in cache:
            cached_pred = cache[ticker].copy()
            cached_pred['cached'] = True
            cached_pred['fallback'] = True
            logger.info(f"Using cached fallback for {ticker}")
            return cached_pred
        
        # Fallback to internal cache
        if ticker in PREDICTION_CACHE:
            cached_pred = PREDICTION_CACHE[ticker].copy()
            cached_pred['cached'] = True
            cached_pred['fallback'] = True
            cached_pred['cached_at'] = cached_pred.get('timestamp')
            logger.info(f"Using internal cache fallback for {ticker}")
            return cached_pred
        
        # No prediction available
        logger.warning(f"No prediction or cache available for {ticker}")
        return {
            'ticker': ticker,
            'prediction': None,
            'confidence': None,
            'cached': False,
            'error': 'No data available'
        }
    
    except Exception as e:
        logger.error(f"Error in get_prediction_with_fallback for {ticker}: {e}")
        return {
            'ticker': ticker,
            'prediction': None,
            'confidence': None,
            'cached': False,
            'error': str(e)
        }


class WebSocketStreamingHandler:
    """
    Handler for WebSocket streaming predictions
    """
    
    def __init__(self, url: str, tickers: List[str]):
        self.url = url
        self.tickers = tickers
        self.updates = []
        self.running = False
        self.thread = None
    
    def get_updates(self) -> List[Dict[str, Any]]:
        """Get all received updates"""
        updates_copy = self.updates.copy()
        self.updates.clear()
        return updates_copy
    
    async def _stream(self):
        """Async WebSocket streaming loop"""
        try:
            async with websockets.connect(self.url) as websocket:
                # Subscribe to tickers
                await websocket.send(json.dumps({
                    "action": "subscribe",
                    "tickers": self.tickers
                }))
                
                logger.info(f"Subscribed to WebSocket for tickers: {self.tickers}")
                
                # Receive updates
                while self.running:
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=15.0
                        )
                        data = json.loads(message)
                        
                        # Store update
                        self.updates.append(data)
                        
                        # Update cache
                        ticker = data.get('ticker')
                        if ticker:
                            PREDICTION_CACHE[ticker] = {
                                'ticker': ticker,
                                'prediction': data.get('prediction'),
                                'confidence': data.get('confidence'),
                                'timestamp': data.get('timestamp'),
                                'cached': False
                            }
                        
                        logger.info(f"WebSocket update for {ticker}: {data.get('prediction')}")
                    
                    except asyncio.TimeoutError:
                        logger.debug("WebSocket receive timeout, continuing...")
                        continue
                    except Exception as e:
                        logger.error(f"Error receiving WebSocket message: {e}")
                        break
        
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
    
    def _run_async_loop(self):
        """Run async loop in thread"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._stream())
    
    def start(self):
        """Start WebSocket streaming in background thread"""
        if not self.running:
            self.running = True
            self.thread = Thread(target=self._run_async_loop, daemon=True)
            self.thread.start()
            logger.info("WebSocket streaming started")
    
    def stop(self):
        """Stop WebSocket streaming"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        logger.info("WebSocket streaming stopped")


def start_websocket_streaming(url: str, tickers: List[str]) -> WebSocketStreamingHandler:
    """
    Start WebSocket streaming for live predictions
    
    Args:
        url: WebSocket URL
        tickers: List of tickers to subscribe to
    
    Returns:
        WebSocketStreamingHandler instance
    """
    handler = WebSocketStreamingHandler(url, tickers)
    handler.start()
    return handler


# Export all public functions
__all__ = [
    'update_prediction_from_rest',
    'fetch_single_prediction',
    'update_predictions_batch',
    'fetch_batch_predictions',
    'get_prediction_with_fallback',
    'start_websocket_streaming',
    'WebSocketStreamingHandler',
    'PREDICTION_CACHE'
]
