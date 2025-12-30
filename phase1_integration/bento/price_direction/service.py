"""
BentoML Price Direction Prediction Service

Serves LSTM/XGBoost models for price direction forecasting.
"""

from __future__ import annotations
import bentoml
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


# Mock model for demonstration - replace with actual trained model
class MockPriceModel:
    """Mock price direction model"""
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Return mock predictions"""
        # Random predictions for demo
        n_samples = len(features)
        probs = np.random.rand(n_samples, 3)  # up, down, neutral
        probs = probs / probs.sum(axis=1, keepdims=True)
        return probs
    
    def predict_proba(self, features: np.ndarray) -> np.ndarray:
        return self.predict(features)


# Try to load actual model, fall back to mock
try:
    model = bentoml.models.get("price_direction:latest").load()
    logger.info("Loaded trained price direction model")
except Exception:
    model = MockPriceModel()
    logger.info("Using mock price direction model")


@bentoml.service(
    name="price_direction",
    resources={"cpu": "500m", "memory": "512Mi"},
    traffic={"timeout": 30},
)
class PriceDirectionService:
    """
    BentoML service for price direction prediction.
    
    Endpoints:
        POST /predict - Single prediction
        POST /batch_predict - Batch predictions
        GET /healthz - Health check
    """
    
    def __init__(self):
        self.model = model
        self.labels = ["up", "down", "neutral"]
        logger.info("PriceDirectionService initialized")
    
    @bentoml.api
    async def predict(
        self,
        symbol: str,
        features: List[float] = None,
        horizon_days: int = 5,
    ) -> Dict[str, Any]:
        """
        Predict price direction for a symbol.
        
        Args:
            symbol: Stock symbol
            features: Optional custom features
            horizon_days: Prediction horizon
        
        Returns:
            Prediction with confidence and probabilities
        """
        try:
            # Generate features if not provided
            if features is None:
                features = np.random.randn(1, 20)  # Mock features
            else:
                features = np.array(features).reshape(1, -1)
            
            # Get prediction
            probs = self.model.predict_proba(features)[0]
            
            # Determine direction
            direction_idx = np.argmax(probs)
            direction = self.labels[direction_idx]
            confidence = float(probs[direction_idx])
            
            return {
                "symbol": symbol,
                "direction": direction,
                "confidence": confidence,
                "probability_up": float(probs[0]),
                "probability_down": float(probs[1]),
                "probability_neutral": float(probs[2]),
                "horizon_days": horizon_days,
                "model_version": "1.0.0",
            }
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {
                "symbol": symbol,
                "direction": "neutral",
                "confidence": 0.0,
                "error": str(e),
            }
    
    @bentoml.api
    async def batch_predict(
        self,
        symbols: List[str],
        horizon_days: int = 5,
    ) -> Dict[str, Dict[str, Any]]:
        """Batch predictions for multiple symbols"""
        results = {}
        for symbol in symbols:
            results[symbol] = await self.predict(symbol, horizon_days=horizon_days)
        return results
    
    @bentoml.api
    def healthz(self) -> Dict[str, str]:
        """Health check endpoint"""
        return {"status": "healthy", "service": "price_direction"}
