"""
Enhanced Market Trends ML Model Training with Registry Integration

Trains a RandomForest classifier and logs comprehensive metrics to the model registry.
"""

import os
import json
import pickle
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

import numpy as np
import pandas as pd

# Import new registry manager
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from ml.model_registry import register_model

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

ARTIFACTS_DIR = Path(__file__).parent.parent / "artifacts"
METRICS_DIR = ARTIFACTS_DIR / "metrics"
MODELS_DIR = ARTIFACTS_DIR / "models"


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


def calculate_sharpe_ratio(returns: np.ndarray, risk_free_rate: float = 0.02) -> float:
    """
    Calculate approximate Sharpe ratio from returns.
    
    Args:
        returns: Array of returns
        risk_free_rate: Annual risk-free rate (default 2%)
    
    Returns:
        Sharpe ratio
    """
    if len(returns) == 0:
        return 0.0
    
    mean_return = np.mean(returns)
    std_return = np.std(returns)
    
    if std_return == 0:
        return 0.0
    
    # Annualize (assuming daily returns)
    sharpe = (mean_return - risk_free_rate / 252) / std_return * np.sqrt(252)
    return float(sharpe)


def train_market_trends_model(
    data: List[Dict[str, Any]], 
    model_name: str = "market_trend_rf",
    test_size: float = 0.2,
    random_state: int = 42,
    register: bool = True
) -> Optional[Tuple[RandomForestClassifier, Dict[str, Any]]]:
    """
    Train RandomForest model for market trend prediction with full metrics logging.
    
    Args:
        data: List of ticker data dicts with historical prices
        model_name: Name for model registration
        test_size: Fraction of data to use for testing
        random_state: Random seed for reproducibility
        register: Whether to register model in registry
    
    Returns:
        Tuple of (trained model, metrics dict) or None if training fails
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
    
    # Evaluate on test set
    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    
    # Calculate comprehensive metrics
    accuracy = float(accuracy_score(y_test, y_pred))
    precision = float(precision_score(y_test, y_pred, average='binary', zero_division=0))
    recall = float(recall_score(y_test, y_pred, average='binary', zero_division=0))
    f1 = float(f1_score(y_test, y_pred, average='binary', zero_division=0))
    
    # Calculate approximate Sharpe ratio from prediction confidence
    returns = (y_pred_proba - 0.5) * 2  # Scale to [-1, 1] as proxy for returns
    sharpe = calculate_sharpe_ratio(returns)
    
    # Feature importance
    feature_importance = {
        feature_cols[i]: float(model.feature_importances_[i])
        for i in range(len(feature_cols))
    }
    
    metrics = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'sharpe_ratio': sharpe,
        'dataset_size': len(df),
        'train_size': len(X_train),
        'test_size': len(X_test),
        'time_window_days': int(df['timestamp'].nunique()) if 'timestamp' in df else 0,
        'feature_importance': feature_importance
    }
    
    logger.info(f"Model Metrics: accuracy={accuracy:.4f}, f1={f1:.4f}, sharpe={sharpe:.4f}")
    
    # Save model
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_filename = f'{model_name}_latest.pkl'
    model_path = MODELS_DIR / model_filename
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    logger.info(f"✅ Model saved to {model_path}")
    
    # Register model in new registry system
    if register:
        registry_entry = register_model(
            model_name=model_name,
            metrics=metrics,
            model_path=str(model_path),
            additional_metadata={
                'feature_cols': feature_cols,
                'model_type': 'RandomForest',
                'hyperparameters': {
                    'n_estimators': 100,
                    'max_depth': 10,
                    'min_samples_split': 5,
                    'random_state': random_state
                }
            }
        )
        
        # Save detailed metrics to separate file
        METRICS_DIR.mkdir(parents=True, exist_ok=True)
        version = registry_entry['version']
        metrics_file = METRICS_DIR / f"{model_name}_{version}.json"
        
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        
        logger.info(f"✅ Model registered as {model_name} {version}")
        logger.info(f"✅ Metrics saved to {metrics_file}")
    
    return model, metrics
