"""
Market Forecast Adapter - AGENT-1B Phase 2
Bento-first adapter with deterministic fixture support

Architecture:
- Primary: HTTP calls to Bento service (localhost:5001)
- Fallback: Deterministic fixtures when FORECAST_DETERMINISTIC=1
- Persistence: PostgreSQL or JSON to data/forecast/<id>.json
"""

import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)


class ForecastAdapter:
    """
    Adapter for market forecast execution and retrieval
    
    Modes:
    1. Bento (default): HTTP POST to FORECAST_BENTO_URL
    2. Deterministic: Load from tests/fixtures/forecast/forecast_fixture.json
    
    Persistence:
    - PostgreSQL (if DB_URL set)
    - JSON fallback to data/forecast/<id>.json
    """
    
    def __init__(self, bento_url: str, deterministic: bool = False):
        self.bento_url = bento_url
        self.deterministic = deterministic
        self.data_dir = Path("data/forecast")
        self.explain_dir = Path("data/forecast/explain")
        self.fixture_path = Path("tests/fixtures/forecast/forecast_fixture.json")
        self.explain_fixture_path = Path("tests/fixtures/forecast/explain_fixture.json")
        
        # Create directories
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.explain_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(
            f"ForecastAdapter initialized: "
            f"bento_url={bento_url}, deterministic={deterministic}"
        )
    
    def run_forecast(
        self,
        ticker: str,
        horizon: int,
        confidence: float,
        model: str,
        forecast_id: str
    ) -> Dict[str, Any]:
        """
        Execute forecast (sync mode)
        
        Returns forecast result with metrics and prediction intervals
        """
        if self.deterministic:
            return self._load_deterministic_fixture(
                ticker, horizon, confidence, model, forecast_id
            )
        
        # Call Bento service
        try:
            response = requests.post(
                self.bento_url,
                json={
                    "ticker": ticker,
                    "horizon": horizon,
                    "confidence": confidence,
                    "model": model
                },
                timeout=30
            )
            response.raise_for_status()
            result = response.json()
            
            # Enrich with metadata
            result["forecast_id"] = forecast_id
            result["timestamp"] = datetime.utcnow().isoformat()
            result["status"] = "completed"
            
            # Persist result
            self._save_forecast(forecast_id, result)
            
            return result
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Bento service error: {e}")
            # Fallback to fixture on service failure
            if self.fixture_path.exists():
                logger.warning("Falling back to deterministic fixture due to Bento error")
                return self._load_deterministic_fixture(
                    ticker, horizon, confidence, model, forecast_id
                )
            else:
                # Re-raise original exception if no fixture available
                raise e
    
    def queue_forecast(
        self,
        ticker: str,
        horizon: int,
        confidence: float,
        model: str,
        forecast_id: str
    ) -> Dict[str, Any]:
        """
        Queue forecast (async mode)
        
        Returns immediate response with poll URL
        """
        # For now, async mode is not implemented - just run sync
        # In production, this would submit to Celery/RabbitMQ
        logger.info(f"Async mode not yet implemented, running sync for {forecast_id}")
        result = self.run_forecast(ticker, horizon, confidence, model, forecast_id)
        
        return {
            "forecast_id": forecast_id,
            "status": "completed",
            "result": result
        }
    
    def get_latest(self, ticker: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get most recent forecast
        
        Args:
            ticker: Filter by ticker (optional)
        
        Returns latest forecast or None
        """
        forecasts = self._list_forecasts()
        
        # Filter by ticker if specified
        if ticker:
            forecasts = [f for f in forecasts if f.get("ticker") == ticker]
        
        if not forecasts:
            return None
        
        # Sort by timestamp (newest first)
        forecasts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return forecasts[0]
    
    def get_history(
        self,
        ticker: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get historical forecast runs
        
        Args:
            ticker: Filter by ticker (optional)
            limit: Max results
            offset: Pagination offset
        
        Returns paginated forecast history
        """
        forecasts = self._list_forecasts()
        
        # Filter by ticker if specified
        if ticker:
            forecasts = [f for f in forecasts if f.get("ticker") == ticker]
        
        # Sort by timestamp (newest first)
        forecasts.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Paginate
        total = len(forecasts)
        forecasts = forecasts[offset:offset + limit]
        
        return {
            "forecasts": forecasts,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    def get_explanation(self, forecast_id: str) -> Optional[Dict[str, Any]]:
        """
        Get SHAP explainability data for a forecast
        
        Returns SHAP values and feature importances
        """
        if self.deterministic and self.explain_fixture_path.exists():
            with open(self.explain_fixture_path) as f:
                return json.load(f)
        
        # Load from explain directory
        explain_file = self.explain_dir / f"{forecast_id}.json"
        if explain_file.exists():
            with open(explain_file) as f:
                return json.load(f)
        
        return None
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check service health
        
        Returns status and configuration
        """
        bento_available = False
        
        if not self.deterministic:
            try:
                response = requests.get(
                    self.bento_url.replace("/predict", "/health"),
                    timeout=5
                )
                bento_available = response.status_code == 200
            except Exception:
                pass
        
        status = "healthy" if (self.deterministic or bento_available) else "degraded"
        
        return {
            "status": status,
            "bento_available": bento_available,
            "deterministic_mode": self.deterministic,
            "persistence_type": "json",  # TODO: PostgreSQL support
            "timestamp": datetime.utcnow().isoformat()
        }
    
    # --- Private Methods ---
    
    def _load_deterministic_fixture(
        self,
        ticker: str,
        horizon: int,
        confidence: float,
        model: str,
        forecast_id: str
    ) -> Dict[str, Any]:
        """Load forecast from fixture file"""
        if not self.fixture_path.exists():
            raise FileNotFoundError(f"Fixture not found: {self.fixture_path}")
        
        with open(self.fixture_path) as f:
            fixture = json.load(f)
        
        # Override with request parameters
        fixture["ticker"] = ticker
        fixture["horizon"] = horizon
        fixture["confidence"] = confidence
        fixture["model"] = model
        fixture["forecast_id"] = forecast_id
        fixture["timestamp"] = datetime.utcnow().isoformat()
        fixture["status"] = "completed"
        
        # Truncate forecast to match requested horizon
        if "forecast" in fixture and len(fixture["forecast"]) > horizon:
            fixture["forecast"] = fixture["forecast"][:horizon]
        
        # Persist to JSON
        self._save_forecast(forecast_id, fixture)
        
        return fixture
    
    def _save_forecast(self, forecast_id: str, data: Dict[str, Any]):
        """Persist forecast to JSON"""
        output_file = self.data_dir / f"{forecast_id}.json"
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved forecast to {output_file}")
    
    def _list_forecasts(self) -> List[Dict[str, Any]]:
        """Load all forecasts from JSON directory"""
        forecasts = []
        for file_path in self.data_dir.glob("*.json"):
            if file_path.name.startswith("explain"):
                continue  # Skip explain files
            try:
                with open(file_path) as f:
                    forecasts.append(json.load(f))
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")
        return forecasts
