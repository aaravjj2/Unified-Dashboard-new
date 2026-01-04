import requests
import logging
from typing import Dict, Any, List, Optional
import os

logger = logging.getLogger(__name__)

class DashboardDataConnector:
    """
    Connects the Dashboard UI to the Phase 3 FastAPI Backend.
    """
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        
    def get_system_health(self) -> Dict[str, str]:
        """Get system health status."""
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code == 200:
                return response.json()
            return {"status": "error", "detail": f"Status {response.status_code}"}
        except Exception as e:
            logger.error(f"Error fetching health: {e}")
            return {"status": "offline", "detail": str(e)}

    def get_market_regime(self) -> Dict[str, Any]:
        """Get current market regime."""
        try:
            # Assuming we have an endpoint for this, or we use analytics
            # If not, we might need to add one or infer it
            response = requests.get(f"{self.base_url}/analytics/regime")
            if response.status_code == 200:
                return response.json()
            return {"regime": "Unknown", "confidence": 0.0}
        except Exception:
            return {"regime": "Unknown", "confidence": 0.0}

    def get_sentiment(self) -> Dict[str, Any]:
        """Get current market sentiment."""
        try:
            response = requests.get(f"{self.base_url}/analytics/sentiment")
            if response.status_code == 200:
                return response.json()
            return {"sentiment": "Neutral", "score": 0.0}
        except Exception:
            return {"sentiment": "Neutral", "score": 0.0}

    def get_portfolio_metrics(self) -> Dict[str, Any]:
        """Get real-time portfolio metrics (Greeks, P&L)."""
        try:
            response = requests.get(f"{self.base_url}/risk/metrics")
            if response.status_code == 200:
                return response.json()
            return {}
        except Exception:
            return {}

    def get_active_orders(self) -> List[Dict[str, Any]]:
        """Get active orders."""
        try:
            response = requests.get(f"{self.base_url}/orders")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []

    def get_positions(self) -> List[Dict[str, Any]]:
        """Get active positions."""
        try:
            response = requests.get(f"{self.base_url}/portfolio/positions")
            if response.status_code == 200:
                return response.json()
            return []
        except Exception:
            return []
    
    def list_strategies(self) -> List[Dict[str, Any]]:
        """List configured strategies from API (tries /api/v1/strategies then /strategies)."""
        try:
            urls = [f"{self.base_url}/api/v1/strategies", f"{self.base_url}/strategies"]
            for url in urls:
                try:
                    response = requests.get(url, timeout=5)
                    if response.status_code == 200:
                        return response.json()
                except Exception:
                    continue
            return []
        except Exception:
            return []

    def place_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Place an order via API POST /api/v1/orders (falls back to /orders)."""
        try:
            urls = [f"{self.base_url}/api/v1/orders", f"{self.base_url}/orders"]
            for url in urls:
                try:
                    response = requests.post(url, json=payload, timeout=10)
                    if response.status_code in (200, 201):
                        return response.json()
                    # if bad request return error
                    if response.status_code >= 400:
                        return {"error": response.text, "status_code": response.status_code}
                except Exception:
                    continue
            return {"error": "no_endpoint"}
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return {"error": str(e)}
            
# Global instance
connector = DashboardDataConnector()
