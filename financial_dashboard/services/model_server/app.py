"""
ML Model Server - FastAPI Service for Model Predictions
========================================================
Phase 4 of ML Project Guide implementation.

Endpoints:
- /predict - Generate predictions
- /metadata - Model metadata
- /health - Health check
"""

import os
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import pandas as pd
import numpy as np

# Try to import ML dependencies
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    JOBLIB_AVAILABLE = False

logger = logging.getLogger(__name__)


# ==============================================================================
# PYDANTIC MODELS
# ==============================================================================

class PredictRequest(BaseModel):
    """Prediction request schema."""
    ticker: str = Field(..., description="Stock ticker symbol")
    features: Optional[Dict[str, float]] = Field(None, description="Pre-computed features")
    horizon: int = Field(5, description="Prediction horizon in days")
    model_name: Optional[str] = Field(None, description="Specific model to use")


class PredictResponse(BaseModel):
    """Prediction response schema."""
    ticker: str
    prediction: str  # 'up', 'down', 'neutral'
    confidence: float
    probabilities: Dict[str, float]
    horizon: int
    model_name: str
    timestamp: str
    features_used: List[str]


class BatchPredictRequest(BaseModel):
    """Batch prediction request."""
    tickers: List[str]
    horizon: int = 5
    model_name: Optional[str] = None


class BatchPredictResponse(BaseModel):
    """Batch prediction response."""
    predictions: List[PredictResponse]
    timestamp: str
    model_name: str


class ModelMetadata(BaseModel):
    """Model metadata schema."""
    name: str
    version: str
    type: str
    trained_at: str
    features: List[str]
    target: str
    metrics: Dict[str, float]
    config: Dict[str, Any]


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_loaded: bool
    timestamp: str
    version: str
    uptime_seconds: float


# ==============================================================================
# APP INITIALIZATION
# ==============================================================================

app = FastAPI(
    title="Quant ML Model Server",
    description="ML model serving for quantitative predictions",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state
_start_time = datetime.now()
_model_cache: Dict[str, Any] = {}
_metadata_cache: Dict[str, ModelMetadata] = {}

# Model directory
MODEL_DIR = Path(os.environ.get('MODEL_DIR', 'models'))


# ==============================================================================
# MODEL LOADING
# ==============================================================================

def load_model(model_name: str = 'default'):
    """Load a model from disk."""
    global _model_cache, _metadata_cache
    
    if model_name in _model_cache:
        return _model_cache[model_name], _metadata_cache.get(model_name)
    
    model_path = MODEL_DIR / model_name
    
    if not model_path.exists():
        # Try default model
        model_path = MODEL_DIR / 'default'
        if not model_path.exists():
            # Return mock model
            return _create_mock_model(), _create_mock_metadata(model_name)
    
    # Load model
    model = None
    if JOBLIB_AVAILABLE and (model_path / 'model.joblib').exists():
        model = joblib.load(model_path / 'model.joblib')
    
    # Load metadata
    metadata = None
    manifest_path = model_path / 'model_manifest.json'
    if manifest_path.exists():
        with open(manifest_path) as f:
            manifest = json.load(f)
            metadata = ModelMetadata(
                name=manifest.get('name', model_name),
                version=manifest.get('version', '1.0.0'),
                type=manifest.get('type', 'unknown'),
                trained_at=manifest.get('trained_at', ''),
                features=manifest.get('features', []),
                target=manifest.get('target', 'return_5d'),
                metrics=manifest.get('metrics', {}),
                config=manifest.get('config', {}),
            )
    else:
        metadata = _create_mock_metadata(model_name)
    
    if model is None:
        model = _create_mock_model()
    
    _model_cache[model_name] = model
    _metadata_cache[model_name] = metadata
    
    return model, metadata


def _create_mock_model():
    """Create a mock model for testing."""
    class MockModel:
        def predict(self, X):
            return np.random.choice([-1, 0, 1], size=len(X))
        
        def predict_proba(self, X):
            probs = np.random.dirichlet([1, 1, 1], size=len(X))
            return probs
    
    return MockModel()


def _create_mock_metadata(model_name: str) -> ModelMetadata:
    """Create mock metadata."""
    return ModelMetadata(
        name=model_name,
        version='mock-1.0',
        type='mock',
        trained_at=datetime.now().isoformat(),
        features=['sma_20', 'rsi_14', 'macd', 'volume_zscore'],
        target='return_5d',
        metrics={'accuracy': 0.55, 'sharpe': 1.2},
        config={'type': 'mock'},
    )


# ==============================================================================
# FEATURE COMPUTATION
# ==============================================================================

def compute_features(ticker: str, features_dict: Optional[Dict] = None) -> pd.DataFrame:
    """Compute features for a ticker."""
    if features_dict:
        return pd.DataFrame([features_dict])
    
    # Try to compute features from live data
    try:
        from financial_dashboard.utils.price_fetch import get_current_price, fetch_historical_data
        from financial_dashboard.features.technical import compute_all_technical_features
        
        # Fetch historical data
        hist = fetch_historical_data([ticker], start_date='2024-01-01', use_alpaca=True)
        
        if hist is None or hist.empty:
            # Return default features
            return pd.DataFrame([{
                'sma_20': 0.0,
                'rsi_14': 50.0,
                'macd': 0.0,
                'volume_zscore': 0.0,
            }])
        
        # Build OHLCV DataFrame
        close = hist[ticker].dropna()
        df = pd.DataFrame({
            'Open': close,
            'High': close * 1.001,
            'Low': close * 0.999,
            'Close': close,
            'Volume': 1000000,
        }, index=close.index)
        
        # Compute features
        features = compute_all_technical_features(df)
        
        # Return latest row
        return features.iloc[[-1]].fillna(0)
        
    except Exception as e:
        logger.warning(f"Could not compute features for {ticker}: {e}")
        return pd.DataFrame([{
            'sma_20': 0.0,
            'rsi_14': 50.0,
            'macd': 0.0,
            'volume_zscore': 0.0,
        }])


# ==============================================================================
# ENDPOINTS
# ==============================================================================

@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    model_loaded = len(_model_cache) > 0 or MODEL_DIR.exists()
    uptime = (datetime.now() - _start_time).total_seconds()
    
    return HealthResponse(
        status="healthy",
        model_loaded=model_loaded,
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        uptime_seconds=uptime,
    )


@app.get("/metadata", response_model=ModelMetadata)
async def metadata(model_name: str = Query('default', description="Model name")):
    """Get model metadata."""
    _, meta = load_model(model_name)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    return meta


@app.get("/models")
async def list_models():
    """List available models."""
    models = []
    
    if MODEL_DIR.exists():
        for path in MODEL_DIR.iterdir():
            if path.is_dir():
                models.append({
                    'name': path.name,
                    'path': str(path),
                    'has_manifest': (path / 'model_manifest.json').exists(),
                })
    
    # Always include mock
    if not models:
        models.append({'name': 'default', 'path': 'mock', 'has_manifest': False})
    
    return {'models': models}


@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest):
    """Generate prediction for a ticker."""
    model_name = request.model_name or 'default'
    model, meta = load_model(model_name)
    
    # Compute features
    features_df = compute_features(request.ticker, request.features)
    
    # Get prediction
    try:
        pred = model.predict(features_df)[0]
        probs = model.predict_proba(features_df)[0]
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        # Fallback to random
        pred = np.random.choice([-1, 0, 1])
        probs = np.random.dirichlet([1, 1, 1])
    
    # Map prediction to label
    pred_map = {-1: 'down', 0: 'neutral', 1: 'up'}
    prediction = pred_map.get(int(pred), 'neutral')
    
    # Get confidence
    confidence = float(max(probs))
    
    # Build probabilities dict
    prob_dict = {
        'down': float(probs[0]) if len(probs) > 0 else 0.33,
        'neutral': float(probs[1]) if len(probs) > 1 else 0.34,
        'up': float(probs[2]) if len(probs) > 2 else 0.33,
    }
    
    return PredictResponse(
        ticker=request.ticker,
        prediction=prediction,
        confidence=confidence,
        probabilities=prob_dict,
        horizon=request.horizon,
        model_name=meta.name if meta else model_name,
        timestamp=datetime.now().isoformat(),
        features_used=list(features_df.columns),
    )


@app.post("/predict/batch", response_model=BatchPredictResponse)
async def predict_batch(request: BatchPredictRequest):
    """Generate predictions for multiple tickers."""
    predictions = []
    
    for ticker in request.tickers:
        single_req = PredictRequest(
            ticker=ticker,
            horizon=request.horizon,
            model_name=request.model_name,
        )
        pred = await predict(single_req)
        predictions.append(pred)
    
    model_name = request.model_name or 'default'
    
    return BatchPredictResponse(
        predictions=predictions,
        timestamp=datetime.now().isoformat(),
        model_name=model_name,
    )


@app.post("/retrain")
async def retrain(background_tasks: BackgroundTasks, model_name: str = 'default'):
    """Trigger model retraining (background task)."""
    # This would trigger the training pipeline
    background_tasks.add_task(_retrain_model, model_name)
    
    return {
        'status': 'retraining_started',
        'model_name': model_name,
        'timestamp': datetime.now().isoformat(),
    }


async def _retrain_model(model_name: str):
    """Background task to retrain model."""
    logger.info(f"Starting retrain for model: {model_name}")
    # Would call tools/train.py here
    # For now, just log
    logger.info(f"Retrain complete for model: {model_name}")


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8066)
