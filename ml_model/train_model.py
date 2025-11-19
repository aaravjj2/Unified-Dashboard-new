"""
Market Trends ML Model Training

Trains a RandomForest classifier to predict next-day trend (up/down) based on:
- Price momentum (moving averages)
- Volume changes
- Sentiment (if available)
"""

import os
import json
import pickle
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Lazy import of ML libraries
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
    SKLEARN_AVAILABLE = True
except ImportError:
    logger.warning("scikit-learn not available. Install with: pip install scikit-learn")
    SKLEARN_AVAILABLE = False


def engineer_features(data: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Engineer features from market data
    
    Args:
        data: List of ticker data dicts with historical prices
    
    Returns:
        DataFrame with engineered features
    """
    records = []
    
    for ticker_data in data:
        ticker = ticker_data.get('ticker')
        historical = ticker_data.get('historical', {})
        
        # Extract OHLCV arrays (handle different API formats)
        if 'c' in historical:  # Finnhub format
            closes = historical.get('c', [])
            volumes = historical.get('v', [])
            timestamps = historical.get('t', [])
        elif 'results' in historical:  # Polygon format
            closes = [bar.get('c') for bar in historical['results']]
            volumes = [bar.get('v') for bar in historical['results']]
            timestamps = [bar.get('t') for bar in historical['results']]
        elif 'bars' in historical:  # Alpaca format
            closes = [bar.get('c') for bar in historical['bars']]
            volumes = [bar.get('v') for bar in historical['bars']]
            timestamps = [bar.get('t') for bar in historical['bars']]
        else:
            logger.warning(f"Unknown historical data format for {ticker}")
            continue
        
        # Need at least 20 days for moving averages
        if len(closes) < 20:
            logger.warning(f"Insufficient data for {ticker}: {len(closes)} days")
            continue
        
        # Calculate features for each day (except last 1 since we need next-day label)
        for i in range(19, len(closes) - 1):  # Start at 19 to have 20-day MA
            # Price momentum features
            ma_5 = np.mean(closes[i-4:i+1])  # 5-day moving average
            ma_20 = np.mean(closes[i-19:i+1])  # 20-day moving average
            price_momentum = (ma_5 - ma_20) / ma_20 if ma_20 != 0 else 0
            
            # Price change percentage
            prev_close = closes[i-1] if i > 0 else closes[i]
            curr_close = closes[i]
            price_change_pct = ((curr_close - prev_close) / prev_close * 100) if prev_close != 0 else 0
            
            # Volume change
            avg_volume = np.mean(volumes[i-4:i+1]) if len(volumes) > i else 0
            prev_avg_volume = np.mean(volumes[i-9:i-4]) if i >= 9 and len(volumes) > i else avg_volume
            volume_change = ((avg_volume - prev_avg_volume) / prev_avg_volume) if prev_avg_volume != 0 else 0
            
            # Volatility (standard deviation of returns)
            returns = [
                (closes[j] - closes[j-1]) / closes[j-1] if closes[j-1] != 0 else 0 
                for j in range(i-4, i+1)
            ]
            volatility = np.std(returns) if len(returns) > 1 else 0
            
            # Label: next day trend (1 = up, 0 = down)
            next_day_close = closes[i+1]
            label = 1 if next_day_close > curr_close else 0
            
            # Sentiment placeholder (can be enhanced with news data)
            sentiment = 0.5  # Neutral by default
            
            records.append({
                'ticker': ticker,
                'timestamp': timestamps[i] if i < len(timestamps) else None,
                'price_momentum': price_momentum,
                'price_change_pct': price_change_pct,
                'volume_change': volume_change,
                'volatility': volatility,
                'sentiment': sentiment,
                'label': label
            })
    
    df = pd.DataFrame(records)
    logger.info(f"Engineered {len(df)} training samples from {len(data)} tickers")
    
    return df


def train_market_trends_model(
    data: List[Dict[str, Any]], 
    test_size: float = 0.2,
    random_state: int = 42
) -> Optional[RandomForestClassifier]:
    """
    Train RandomForest model for market trend prediction
    
    Args:
        data: List of ticker data dicts with historical prices
        test_size: Fraction of data to use for testing
        random_state: Random seed for reproducibility
    
    Returns:
        Trained RandomForestClassifier model (or None if training fails)
    """
    if not SKLEARN_AVAILABLE:
        logger.error("Cannot train model: scikit-learn not available")
        return None
    
    # Engineer features
    df = engineer_features(data)
    
    if len(df) < 10:
        logger.error(f"Insufficient training data: {len(df)} samples (need at least 10)")
        return None
    
    # Split features and labels
    feature_cols = ['price_momentum', 'price_change_pct', 'volume_change', 'volatility', 'sentiment']
    X = df[feature_cols].values
    y = df['label'].values
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    
    logger.info(f"Training set: {len(X_train)} samples, Test set: {len(X_test)} samples")
    
    # Train model
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        min_samples_split=5,
        random_state=random_state,
        n_jobs=-1
    )
    
    logger.info("Training RandomForest model...")
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    
    metrics = {
        'accuracy': float(accuracy_score(y_test, y_pred)),
        'precision': float(precision_score(y_test, y_pred, average='binary')),
        'recall': float(recall_score(y_test, y_pred, average='binary')),
        'f1': float(f1_score(y_test, y_pred, average='binary'))
    }
    
    logger.info(f"Model Metrics: {metrics}")
    
    # Save model
    model_version = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    model_filename = f'model_v{model_version}.pkl'
    model_path = os.path.join('ml_model', 'artifacts', model_filename)
    
    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    logger.info(f"✅ Model saved to {model_path}")
    
    # Update model registry
    update_model_registry(model_path, metrics, feature_cols)
    
    return model


def update_model_registry(
    model_path: str, 
    metrics: Dict[str, float],
    features: List[str]
) -> None:
    """
    Update model registry with new model metadata
    
    Args:
        model_path: Path to saved model file
        metrics: Performance metrics dict
        features: List of feature names used
    """
    registry_path = 'ml_model/model_registry.json'
    
    # Load existing registry or create new
    if os.path.exists(registry_path):
        with open(registry_path, 'r') as f:
            registry = json.load(f)
    else:
        registry = {'models': []}
    
    # Extract version from path
    model_filename = os.path.basename(model_path)
    version = model_filename.replace('model_', '').replace('.pkl', '')
    
    # Add new model entry
    registry['models'].append({
        'version': version,
        'path': model_path,
        'trained_at': datetime.utcnow().isoformat(),
        'metrics': metrics,
        'features': features,
        'model_type': 'RandomForest'
    })
    
    # Sort by version (newest first)
    registry['models'].sort(key=lambda x: x['version'], reverse=True)
    
    # Save registry
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)
    
    logger.info(f"✅ Model registry updated: {len(registry['models'])} models")
