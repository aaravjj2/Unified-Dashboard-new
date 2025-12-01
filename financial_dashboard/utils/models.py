"""
Model Management Utilities for Unified Financial Dashboard

Provides model loading, training, and versioning capabilities for ML predictions.
"""

import os
import logging
import pickle
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Define model directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
MODELS_DIR = PROJECT_ROOT / 'models'
MODELS_DIR.mkdir(parents=True, exist_ok=True)


def load_latest_model(model_name: str = 'stock_predictor') -> Optional[Any]:
    """
    Load the most recent trained model from disk.
    
    Args:
        model_name: Base name of the model to load
        
    Returns:
        Loaded model object (sklearn, xgboost, etc.) or None if no model found
    """
    try:
        # Look for model files in models directory
        model_pattern = f"{model_name}_*.pkl"
        model_files = sorted(MODELS_DIR.glob(model_pattern), reverse=True)
        
        if not model_files:
            logger.warning(f"No model files found matching pattern: {model_pattern}")
            logger.info(f"💡 Searched in: {MODELS_DIR}")
            logger.info(f"💡 To generate a model, run: python scripts/train_model.py")
            return None
        
        # Load most recent model
        latest_model_path = model_files[0]
        logger.info(f"Loading model from: {latest_model_path}")
        
        with open(latest_model_path, 'rb') as f:
            model = pickle.load(f)
        
        logger.info(f"✅ Successfully loaded model: {latest_model_path.name}")
        return model
        
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        return None


def save_model(model: Any, model_name: str = 'stock_predictor', metadata: Optional[dict] = None) -> Optional[Path]:
    """
    Save a trained model to disk with timestamp.
    
    Args:
        model: Trained model object
        model_name: Base name for the model file
        metadata: Optional metadata dict to save alongside model
        
    Returns:
        Path to saved model file, or None on error
    """
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        model_filename = f"{model_name}_{timestamp}.pkl"
        model_path = MODELS_DIR / model_filename
        
        with open(model_path, 'wb') as f:
            pickle.dump(model, f)
        
        logger.info(f"✅ Saved model to: {model_path}")
        
        # Save metadata if provided
        if metadata:
            metadata_path = model_path.with_suffix('.json')
            import json
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            logger.info(f"✅ Saved metadata to: {metadata_path}")
        
        return model_path
        
    except Exception as e:
        logger.error(f"❌ Failed to save model: {e}")
        return None


def list_available_models(model_name: str = 'stock_predictor') -> list:
    """
    List all available trained models.
    
    Args:
        model_name: Base name pattern to search for
        
    Returns:
        List of model file paths, sorted by modification time (newest first)
    """
    try:
        model_pattern = f"{model_name}_*.pkl"
        model_files = sorted(
            MODELS_DIR.glob(model_pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if model_files:
            logger.info(f"Found {len(model_files)} model(s) matching '{model_pattern}'")
            for mf in model_files:
                mtime = datetime.fromtimestamp(mf.stat().st_mtime)
                logger.info(f"  - {mf.name} (modified: {mtime})")
        else:
            logger.info(f"No models found matching '{model_pattern}'")
        
        return [str(mf) for mf in model_files]
        
    except Exception as e:
        logger.error(f"❌ Error listing models: {e}")
        return []


# For backward compatibility and testing
def get_mock_model(n_features: int = 8):
    """
    Returns a mock model for testing purposes.
    
    This is a simple sklearn-compatible model that can be used when
    no trained model is available, useful for testing SHAP generation pipeline.
    
    Args:
        n_features: Number of features the model should expect (default: 8)
                   This should match the output of prepare_features_for_date()
    """
    try:
        from sklearn.ensemble import RandomForestClassifier
        import numpy as np
        
        # Create a minimal trained model
        mock_model = RandomForestClassifier(n_estimators=10, max_depth=3, random_state=42)
        
        # Train on dummy data (n_features features, 100 samples, binary classification)
        X_dummy = np.random.randn(100, n_features)
        y_dummy = np.random.randint(0, 2, 100)
        mock_model.fit(X_dummy, y_dummy)
        
        logger.info(f"✅ Created mock RandomForestClassifier for testing (n_features={n_features})")
        return mock_model
        
    except ImportError:
        logger.warning("sklearn not available - cannot create mock model")
        return None
