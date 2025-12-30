"""
BentoML IV Forecast Service

Serves XGBoost/Prophet models for implied volatility forecasting.
"""

from __future__ import annotations
import bentoml
import numpy as np
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)


class MockIVModel:
    """Mock IV forecast model"""
    
    def predict(self, features: np.ndarray) -> np.ndarray:
        """Return mock IV predictions"""
        n_samples = len(features)
        # Generate realistic IV values (15-80% range)
        base_iv = np.random.uniform(0.15, 0.50, n_samples)
        return base_iv


try:
    model = bentoml.models.get("iv_forecast:latest").load()
    logger.info("Loaded trained IV forecast model")
except Exception:
    model = MockIVModel()
    logger.info("Using mock IV forecast model")


@bentoml.service(
    name="iv_forecast",
    resources={"cpu": "500m", "memory": "512Mi"},
    traffic={"timeout": 30},
)
class IVForecastService:
    """
    BentoML service for implied volatility forecasting.
    
    Endpoints:
        POST /predict - Single IV prediction
        POST /surface - Full IV surface
        GET /healthz - Health check
    """
    
    def __init__(self):
        self.model = model
        logger.info("IVForecastService initialized")
    
    @bentoml.api
    async def predict(
        self,
        symbol: str,
        dte: int = 30,
        historical_iv: List[float] = None,
    ) -> Dict[str, Any]:
        """
        Predict IV for a symbol at given DTE.
        
        Args:
            symbol: Stock symbol
            dte: Days to expiration
            historical_iv: Optional historical IV series
        
        Returns:
            IV prediction with confidence interval
        """
        try:
            # Generate features
            if historical_iv:
                features = np.array(historical_iv[-20:]).reshape(1, -1)
            else:
                features = np.random.randn(1, 20)
            
            # Get prediction
            predicted_iv = float(self.model.predict(features)[0])
            
            # Calculate IV percentile (mock)
            iv_percentile = min(100, max(0, predicted_iv * 150))
            
            # Confidence interval
            confidence_low = predicted_iv * 0.9
            confidence_high = predicted_iv * 1.1
            
            return {
                "symbol": symbol,
                "dte": dte,
                "predicted_iv": round(predicted_iv, 4),
                "iv_percentile": round(iv_percentile, 2),
                "confidence_low": round(confidence_low, 4),
                "confidence_high": round(confidence_high, 4),
                "model_version": "1.0.0",
            }
        except Exception as e:
            logger.error(f"IV prediction error: {e}")
            return {
                "symbol": symbol,
                "dte": dte,
                "predicted_iv": 0.25,
                "error": str(e),
            }
    
    @bentoml.api
    async def surface(
        self,
        symbol: str,
        dtes: List[int] = None,
        moneyness: List[float] = None,
    ) -> Dict[str, Any]:
        """Generate IV surface"""
        if dtes is None:
            dtes = [7, 14, 21, 30, 45, 60, 90]
        if moneyness is None:
            moneyness = [0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15]
        
        # Generate mock surface
        surface = []
        for dte in dtes:
            for m in moneyness:
                # Simple smile approximation
                atm_iv = 0.20 + (dte / 365) * 0.05
                smile_adj = 0.02 * abs(m - 1.0) ** 2
                iv = atm_iv + smile_adj
                surface.append({
                    "dte": dte,
                    "moneyness": m,
                    "iv": round(iv, 4),
                })
        
        return {
            "symbol": symbol,
            "surface": surface,
            "model_version": "1.0.0",
        }
    
    @bentoml.api
    def healthz(self) -> Dict[str, str]:
        return {"status": "healthy", "service": "iv_forecast"}
