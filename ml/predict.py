"""
Model Prediction with Registry Integration

Loads versioned models from registry and generates predictions.
"""

import os
import pickle
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Import registry manager
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from ml.model_registry import get_latest_model, get_model_by_version

MODELS_DIR = Path(__file__).parent.parent / "artifacts" / "models"


def load_model_from_registry(
    model_name: str,
    version: Optional[str] = None
):
    """
    Load a model from the registry.
    
    Args:
        model_name: Name of the model
        version: Specific version to load (if None, loads latest)
    
    Returns:
        Loaded model object
    """
    if version is None:
        model_entry = get_latest_model(model_name)
    else:
        model_entry = get_model_by_version(model_name, version)
    
    if model_entry is None:
        raise ValueError(f"Model {model_name} (version={version}) not found in registry")
    
    model_path = model_entry.get('model_path')
    if not model_path or not Path(model_path).exists():
        raise FileNotFoundError(f"Model file not found: {model_path}")
    
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    logger.info(f"✅ Loaded model {model_name} {model_entry['version']} from {model_path}")
    
    return model, model_entry


def predict_market_trend(
    model_name: str,
    features: Dict[str, float],
    version: Optional[str] = None
) -> Dict[str, Any]:
    """
    Predict market trend using registered model.
    
    Args:
        model_name: Name of the model
        features: Dictionary of feature values
        version: Specific model version (if None, uses latest)
    
    Returns:
        Dictionary with prediction, confidence, and metadata
    """
    # Load model from registry
    model, model_entry = load_model_from_registry(model_name, version)
    
    # Extract feature values in correct order
    feature_cols = model_entry.get('feature_cols', [
        'price_momentum', 'price_change_pct', 'volume_change', 'volatility', 'sentiment'
    ])
    
    feature_values = np.array([[features.get(col, 0.0) for col in feature_cols]])
    
    # Make prediction
    prediction = int(model.predict(feature_values)[0])
    confidence = float(model.predict_proba(feature_values)[0][prediction])
    
    result = {
        'prediction': prediction,
        'confidence': confidence,
        'model_name': model_name,
        'model_version': model_entry['version'],
        'features': features,
        'feature_cols': feature_cols
    }
    
    logger.info(f"Prediction: {prediction} (confidence: {confidence:.4f})")
    
    return result


def batch_predict(
    model_name: str,
    feature_list: List[Dict[str, float]],
    version: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Batch prediction for multiple feature sets.
    
    Args:
        model_name: Name of the model
        feature_list: List of feature dictionaries
        version: Specific model version (if None, uses latest)
    
    Returns:
        List of prediction dictionaries
    """
    # Load model once for batch processing
    model, model_entry = load_model_from_registry(model_name, version)
    
    feature_cols = model_entry.get('feature_cols', [
        'price_momentum', 'price_change_pct', 'volume_change', 'volatility', 'sentiment'
    ])
    
    # Build feature matrix
    X = np.array([[f.get(col, 0.0) for col in feature_cols] for f in feature_list])
    
    # Batch predict
    predictions = model.predict(X)
    probabilities = model.predict_proba(X)
    
    results = []
    for i, (pred, proba, features) in enumerate(zip(predictions, probabilities, feature_list)):
        results.append({
            'prediction': int(pred),
            'confidence': float(proba[pred]),
            'model_name': model_name,
            'model_version': model_entry['version'],
            'features': features,
            'index': i
        })
    
    logger.info(f"Batch prediction completed: {len(results)} predictions")
    
    return results
