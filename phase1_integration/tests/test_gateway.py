"""
Unit Tests for FastAPI Gateway

Tests the gateway API endpoints for:
- Health checks
- Signal management
- Order management
- ML predictions
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

import sys
sys.path.insert(0, '/home/aarav/Unified-Dashboard/phase1_integration')


# Mock the imports before loading gateway
with patch.dict('sys.modules', {
    'redis': MagicMock(),
    'redis.asyncio': MagicMock(),
    'grpcio': MagicMock(),
    'grpcio-tools': MagicMock(),
}):
    from gateway.main import app


# -----------------------------------------------------------------------------
# Gateway Tests
# -----------------------------------------------------------------------------

class TestHealthEndpoints:
    """Test health check endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_health_check(self, client):
        """Test main health endpoint"""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "gateway" in data
        assert data["gateway"] == "healthy"
        assert "timestamp" in data


class TestSignalEndpoints:
    """Test signal API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_create_signal(self, client):
        """Test creating a signal"""
        request_data = {
            "type": "buy",
            "symbol": "AAPL",
            "strategy": "momentum",
            "confidence": 0.85,
            "source": "test",
            "data": {},
        }
        
        response = client.post("/api/signals", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
        assert data["success"] is True
    
    def test_create_signal_invalid(self, client):
        """Test creating an invalid signal"""
        # Missing required field
        request_data = {
            "type": "buy",
            # Missing symbol
            "confidence": 0.5,
        }
        
        response = client.post("/api/signals", json=request_data)
        
        # Should fail validation
        assert response.status_code == 422
    
    def test_get_signals(self, client):
        """Test getting signals"""
        response = client.get("/api/signals")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "signals" in data
        assert isinstance(data["signals"], list)
    
    def test_get_signals_with_filters(self, client):
        """Test getting signals with filters"""
        response = client.get(
            "/api/signals",
            params={"symbol": "AAPL", "count": 10}
        )
        
        assert response.status_code == 200


class TestOrderEndpoints:
    """Test order API endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    def test_create_order(self, client):
        """Test creating an order"""
        request_data = {
            "symbol": "AAPL",
            "side": "buy",
            "order_type": "limit",
            "quantity": 100,
            "limit_price": 150.0,
            "strategy": "test",
        }
        
        response = client.post("/api/orders", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "success" in data
    
    def test_create_market_order(self, client):
        """Test creating a market order"""
        request_data = {
            "symbol": "MSFT",
            "side": "buy",
            "order_type": "market",
            "quantity": 50,
        }
        
        response = client.post("/api/orders", json=request_data)
        
        assert response.status_code == 200
    
    def test_get_orders(self, client):
        """Test getting orders"""
        response = client.get("/api/orders")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "orders" in data
    
    def test_cancel_order(self, client):
        """Test canceling an order"""
        response = client.delete("/api/orders/test-order-123")
        
        # May fail if order doesn't exist, but endpoint should work
        assert response.status_code in [200, 400, 503]


class TestPredictionEndpoints:
    """Test ML prediction endpoints"""
    
    @pytest.fixture
    def client(self):
        """Create test client"""
        return TestClient(app)
    
    @patch('gateway.main.client')
    def test_predict_direction(self, mock_client, client):
        """Test price direction prediction"""
        # Mock the HTTP client response
        mock_client.post = AsyncMock(return_value={
            "symbol": "AAPL",
            "direction": "up",
            "probability_up": 0.65,
            "confidence": 0.30,
        })
        
        request_data = {
            "symbol": "AAPL",
            "horizon_days": 5,
        }
        
        response = client.post("/api/predict/direction", json=request_data)
        
        assert response.status_code == 200
    
    @patch('gateway.main.client')
    def test_predict_iv(self, mock_client, client):
        """Test IV forecast"""
        mock_client.post = AsyncMock(return_value={
            "symbol": "SPY",
            "current_iv": 0.22,
            "forecast_iv": 0.24,
        })
        
        request_data = {
            "symbol": "SPY",
            "dte": 30,
        }
        
        response = client.post("/api/predict/iv", json=request_data)
        
        assert response.status_code == 200
    
    @patch('gateway.main.client')
    def test_analyze_sentiment(self, mock_client, client):
        """Test sentiment analysis"""
        mock_client.post = AsyncMock(return_value={
            "sentiment": "bullish",
            "confidence": 0.85,
        })
        
        request_data = {
            "text": "Apple reports record iPhone sales",
            "symbol": "AAPL",
        }
        
        response = client.post("/api/predict/sentiment", json=request_data)
        
        assert response.status_code == 200
    
    @patch('gateway.main.client')
    def test_ensemble_predict(self, mock_client, client):
        """Test ensemble prediction"""
        mock_client.post = AsyncMock(return_value={
            "direction": "up",
            "iv_forecast": 0.25,
        })
        
        request_data = {
            "symbol": "AAPL",
            "horizon_days": 5,
        }
        
        response = client.post("/api/predict/ensemble", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert "symbol" in data
        assert "timestamp" in data


# -----------------------------------------------------------------------------
# Request/Response Model Tests
# -----------------------------------------------------------------------------

class TestRequestModels:
    """Test Pydantic request models"""
    
    def test_signal_request_validation(self):
        """Test SignalRequest validation"""
        from gateway.main import SignalRequest
        
        # Valid request
        request = SignalRequest(
            type="buy",
            symbol="AAPL",
            strategy="test",
            confidence=0.8,
        )
        
        assert request.type == "buy"
        assert request.symbol == "AAPL"
        assert request.confidence == 0.8
    
    def test_order_request_validation(self):
        """Test OrderRequest validation"""
        from gateway.main import OrderRequest
        
        request = OrderRequest(
            symbol="MSFT",
            side="sell",
            order_type="limit",
            quantity=50,
            limit_price=350.0,
        )
        
        assert request.side == "sell"
        assert request.quantity == 50
    
    def test_prediction_request_validation(self):
        """Test PredictionRequest validation"""
        from gateway.main import PredictionRequest
        
        request = PredictionRequest(
            symbol="GOOGL",
            horizon_days=10,
        )
        
        assert request.symbol == "GOOGL"
        assert request.horizon_days == 10
    
    def test_sentiment_request_validation(self):
        """Test SentimentRequest validation"""
        from gateway.main import SentimentRequest
        
        request = SentimentRequest(
            text="Great earnings report!",
            symbol="NVDA",
        )
        
        assert request.text == "Great earnings report!"
        assert request.symbol == "NVDA"


# -----------------------------------------------------------------------------
# Run Tests
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
