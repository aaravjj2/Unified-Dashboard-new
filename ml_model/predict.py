"""
Market Trends ML Model Prediction

Load trained model and generate trend predictions for new market data.
"""

import os
import json
import pickle
import logging
from typing import Dict, Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


def load_latest_model():
    """
    Load the most recent trained model from registry
    
    Returns:
        Loaded model object (or None if no models found)
    """
    registry_path = 'ml_model/model_registry.json'
    
    if not os.path.exists(registry_path):
        logger.error("Model registry not found. Train a model first.")
        return None
    
    with open(registry_path, 'r') as f:
        registry = json.load(f)
    
    if not registry.get('models') or len(registry['models']) == 0:
        logger.error("No models in registry. Train a model first.")
        return None
    
    # Get latest model (registry is sorted by version desc)
    latest = registry['models'][0]
    model_path = latest['path']
    
    if not os.path.exists(model_path):
        logger.error(f"Model file not found: {model_path}")
        return None
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    logger.info(f"✅ Loaded model: {latest['version']} (accuracy: {latest['metrics'].get('accuracy', 'N/A')})")
    
    return model


def predict_market_trend(
    ticker_data: Dict[str, Any],
    model: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Predict next-day market trend for a ticker
    
    Args:
        ticker_data: Dict with current market data (from fetch_market_data)
        model: Pre-loaded model (or load latest if None)
    
    Returns:
        Dict with:
            - 'ticker': str
            - 'trend': str ('bullish' or 'bearish')
            - 'confidence': float (0-1)
            - 'source': str ('ML_v{version}')
            - 'features': Dict (feature values used)
    
    Example:
        >>> ticker_data = {'ticker': 'AAPL', 'current_price': 175.0, ...}
        >>> prediction = predict_market_trend(ticker_data)
        >>> print(f"{prediction['ticker']}: {prediction['trend']} (confidence: {prediction['confidence']:.2f})")
    """
    # Load model if not provided
    if model is None:
        model = load_latest_model()
        if model is None:
            return {
                'ticker': ticker_data.get('ticker', 'UNKNOWN'),
                'trend': 'unknown',
                'confidence': 0.0,
                'source': 'ML_ERROR',
                'error': 'No model available'
            }
    
    # Extract features from ticker_data
    features = extract_features_for_prediction(ticker_data)
    
    if features is None:
        return {
            'ticker': ticker_data.get('ticker', 'UNKNOWN'),
            'trend': 'unknown',
            'confidence': 0.0,
            'source': 'ML_ERROR',
            'error': 'Insufficient data for prediction'
        }
    
    # Prepare feature vector
    feature_vector = np.array([[
        features['price_momentum'],
        features['price_change_pct'],
        features['volume_change'],
        features['volatility'],
        features['sentiment']
    ]])
    
    # Predict
    try:
        prediction_proba = model.predict_proba(feature_vector)[0]
        prediction_class = model.predict(feature_vector)[0]
        
        # Class 1 = bullish (up), Class 0 = bearish (down)
        trend = 'bullish' if prediction_class == 1 else 'bearish'
        confidence = float(max(prediction_proba))
        
        # Get model version from registry
        registry_path = 'ml_model/model_registry.json'
        version = 'unknown'
        if os.path.exists(registry_path):
            with open(registry_path, 'r') as f:
                registry = json.load(f)
                if registry.get('models'):
                    version = registry['models'][0]['version']
        
        return {
            'ticker': ticker_data.get('ticker', 'UNKNOWN'),
            'trend': trend,
            'confidence': confidence,
            'source': f'ML_v{version}',
            'features': features,
            'probabilities': {
                'bearish': float(prediction_proba[0]),
                'bullish': float(prediction_proba[1])
            }
        }
    
    except Exception as e:
        logger.error(f"Prediction error for {ticker_data.get('ticker')}: {e}")
        return {
            'ticker': ticker_data.get('ticker', 'UNKNOWN'),
            'trend': 'unknown',
            'confidence': 0.0,
            'source': 'ML_ERROR',
            'error': str(e)
        }


def extract_features_for_prediction(ticker_data: Dict[str, Any]) -> Optional[Dict[str, float]]:
    """
    Extract features from ticker data for prediction
    
    Args:
        ticker_data: Market data dict from fetch_market_data
    
    Returns:
        Dict with feature values (or None if insufficient data)
    """
    historical = ticker_data.get('historical', {})
    
    # Extract price arrays based on source format
    if 'c' in historical:  # Finnhub format
        closes = historical.get('c', [])
        volumes = historical.get('v', [])
    elif 'results' in historical:  # Polygon format
        closes = [bar.get('c') for bar in historical['results']]
        volumes = [bar.get('v') for bar in historical['results']]
    elif 'bars' in historical:  # Alpaca format
        closes = [bar.get('c') for bar in historical['bars']]
        volumes = [bar.get('v') for bar in historical['bars']]
    else:
        logger.warning(f"Unknown historical format for {ticker_data.get('ticker')}")
        return None
    
    # Need at least 20 days
    if len(closes) < 20:
        logger.warning(f"Insufficient historical data: {len(closes)} days (need 20)")
        return None
    
    # Use most recent data
    recent_closes = closes[-20:]
    recent_volumes = volumes[-20:] if len(volumes) >= 20 else [0] * 20
    
    # Calculate features (same as training)
    ma_5 = float(np.mean(recent_closes[-5:]))
    ma_20 = float(np.mean(recent_closes))
    price_momentum = (ma_5 - ma_20) / ma_20 if ma_20 != 0 else 0.0
    
    prev_close = recent_closes[-2] if len(recent_closes) >= 2 else recent_closes[-1]
    curr_close = recent_closes[-1]
    price_change_pct = ((curr_close - prev_close) / prev_close * 100) if prev_close != 0 else 0.0
    
    avg_volume = float(np.mean(recent_volumes[-5:]))
    prev_avg_volume = float(np.mean(recent_volumes[-10:-5])) if len(recent_volumes) >= 10 else avg_volume
    volume_change = ((avg_volume - prev_avg_volume) / prev_avg_volume) if prev_avg_volume != 0 else 0.0
    
    returns = [
        (recent_closes[i] - recent_closes[i-1]) / recent_closes[i-1] if recent_closes[i-1] != 0 else 0
        for i in range(-5, 0)
    ]
    volatility = float(np.std(returns)) if len(returns) > 1 else 0.0
    
    sentiment = 0.5  # Neutral by default (can enhance with news sentiment)
    
    return {
        'price_momentum': price_momentum,
        'price_change_pct': price_change_pct,
        'volume_change': volume_change,
        'volatility': volatility,
        'sentiment': sentiment
    }
