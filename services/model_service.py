"""
Model Service API
FastAPI service for real-time model predictions.
"""
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from contextlib import asynccontextmanager

from ml.model_registry import get_latest_model, get_model_by_version
from ml.predict import load_model_from_registry, predict_market_trend, batch_predict
from services.cache_manager import get_cache_manager, generate_cache_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global state
_model = None
_model_metadata = None
_cache_manager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup
    global _model, _model_metadata, _cache_manager
    
    logger.info("Loading model on startup...")
    
    try:
        # Initialize cache manager
        _cache_manager = get_cache_manager()
        
        # Load latest model from registry
        model_metadata = get_latest_model("market_trend_rf")
        
        if model_metadata is None:
            logger.error("No model found in registry")
            _model_metadata = {
                "model_name": "market_trend_rf",
                "version": "unknown",
                "status": "not_loaded"
            }
        else:
            # Load actual model
            model, metadata = load_model_from_registry("market_trend_rf")
            
            _model = model
            _model_metadata = metadata
            
            logger.info(f"✅ Model loaded: {metadata['model_name']} {metadata['version']}")
            logger.info(f"   Accuracy: {metadata.get('metrics', {}).get('accuracy', 'N/A')}")
    
    except Exception as e:
        logger.error(f"❌ Failed to load model: {e}")
        _model_metadata = {
            "model_name": "market_trend_rf",
            "version": "error",
            "status": "load_failed",
            "error": str(e)
        }
    
    yield
    
    # Shutdown
    logger.info("Shutting down model service")


# FastAPI app with lifespan
app = FastAPI(
    title="Market Trends Model Service",
    description="Real-time ML model serving for market trend predictions",
    version="1.0.0",
    lifespan=lifespan
)


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class PredictionRequest(BaseModel):
    """Request model for single prediction."""
    price_momentum: float = Field(..., description="Price momentum indicator")
    price_change_pct: float = Field(..., description="Price change percentage")
    volume_change: float = Field(..., description="Volume change ratio")
    volatility: float = Field(..., description="Volatility measure")
    sentiment: float = Field(0.5, description="Sentiment score (0-1)")


class BatchPredictionRequest(BaseModel):
    """Request model for batch predictions."""
    features_list: List[Dict[str, float]] = Field(..., description="List of feature dictionaries")


class PredictionResponse(BaseModel):
    """Response model for predictions."""
    prediction: int = Field(..., description="Predicted class (0=down, 1=up)")
    confidence: float = Field(..., description="Prediction confidence (0-1)")
    model_version: str = Field(..., description="Model version used")
    model_name: str = Field(..., description="Model name")
    timestamp: str = Field(..., description="Prediction timestamp (ISO format)")
    cached: bool = Field(False, description="Whether result was served from cache")


class BatchPredictionResponse(BaseModel):
    """Response model for batch predictions."""
    predictions: List[PredictionResponse]
    count: int
    model_version: str
    timestamp: str


class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status (healthy/degraded/unhealthy)")
    model_name: str = Field(..., description="Loaded model name")
    model_version: str = Field(..., description="Loaded model version")
    model_accuracy: Optional[float] = Field(None, description="Model accuracy")
    cache_stats: Optional[Dict[str, Any]] = Field(None, description="Cache statistics")
    timestamp: str = Field(..., description="Health check timestamp")


class ModelInfoResponse(BaseModel):
    """Response model for model metadata."""
    model_name: str
    version: str
    timestamp: str
    metrics: Dict[str, Any]
    source_commit: str
    model_path: str


@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Returns service status and model information.
    """
    # Handle None metadata gracefully
    if _model_metadata is None:
        metadata = {"model_name": "unknown", "version": "unknown", "metrics": {}}
    else:
        metadata = _model_metadata
    
    if _model is None or _model_metadata is None:
        status_code = "unhealthy"
    elif metadata.get("status") == "load_failed":
        status_code = "degraded"
    else:
        status_code = "healthy"
    
    cache_stats = _cache_manager.stats() if _cache_manager else None
    
    return HealthResponse(
        status=status_code,
        model_name=metadata.get("model_name", "unknown"),
        model_version=metadata.get("version", "unknown"),
        model_accuracy=metadata.get("metrics", {}).get("accuracy"),
        cache_stats=cache_stats,
        timestamp=datetime.utcnow().isoformat() + "Z"
    )


@app.get("/api/model/info", response_model=ModelInfoResponse)
async def get_model_info():
    """
    Get current model metadata.
    """
    if _model_metadata is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded"
        )
    
    # Get full model info from registry
    model_info = get_latest_model("market_trend_rf")
    
    if model_info is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found in registry"
        )
    
    return ModelInfoResponse(**model_info)


@app.post("/api/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Single prediction endpoint.
    Returns market trend prediction for given features.
    """
    if _model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded"
        )
    
    # Convert request to features dict
    features = request.dict()
    
    # Check cache first
    cache_key = generate_cache_key(features)
    cached_result = _cache_manager.get(cache_key) if _cache_manager else None
    
    if cached_result:
        logger.debug(f"Cache hit for key: {cache_key}")
        return PredictionResponse(**cached_result, cached=True)
    
    # Make prediction
    try:
        result = predict_market_trend(
            model_name="market_trend_rf",
            features=features,
            version=_model_metadata.get("version")
        )
        
        response = PredictionResponse(
            prediction=result["prediction"],
            confidence=result["confidence"],
            model_version=result["model_version"],
            model_name=result["model_name"],
            timestamp=datetime.utcnow().isoformat() + "Z",
            cached=False
        )
        
        # Cache the result
        if _cache_manager:
            _cache_manager.set(cache_key, response.dict())
        
        return response
        
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Prediction failed: {str(e)}"
        )


@app.post("/api/batch_predict", response_model=BatchPredictionResponse)
async def batch_predict_endpoint(request: BatchPredictionRequest):
    """
    Batch prediction endpoint.
    Returns predictions for multiple feature sets.
    """
    if _model is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model not loaded"
        )
    
    try:
        # Make batch predictions
        results = batch_predict(
            model_name="market_trend_rf",
            feature_list=request.features_list,
            version=_model_metadata.get("version")
        )
        
        # Convert to response format
        predictions = [
            PredictionResponse(
                prediction=r["prediction"],
                confidence=r["confidence"],
                model_version=r["model_version"],
                model_name=r["model_name"],
                timestamp=datetime.utcnow().isoformat() + "Z",
                cached=False
            )
            for r in results
        ]
        
        return BatchPredictionResponse(
            predictions=predictions,
            count=len(predictions),
            model_version=_model_metadata.get("version", "unknown"),
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch prediction failed: {str(e)}"
        )


@app.get("/api/cache/stats")
async def get_cache_stats():
    """
    Get cache statistics.
    """
    if _cache_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache manager not initialized"
        )
    
    return _cache_manager.stats()


@app.post("/api/cache/clear")
async def clear_cache():
    """
    Clear prediction cache.
    """
    if _cache_manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Cache manager not initialized"
        )
    
    _cache_manager.clear_predictions()
    
    return {
        "status": "success",
        "message": "Prediction cache cleared",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
