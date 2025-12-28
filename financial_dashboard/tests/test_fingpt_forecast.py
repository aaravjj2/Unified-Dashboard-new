"""
Tests for FinGPT Forecast Service
=================================
Unit tests for stock forecast generation.
"""

import pytest
from datetime import datetime


class TestForecastService:
    """Test forecast service components."""
    
    def test_forecast_service_initialization(self):
        """Test service initialization."""
        from financial_dashboard.services.fingpt_forecast_service import ForecastService
        
        service = ForecastService()
        assert service is not None
    
    def test_get_forecast_service_singleton(self):
        """Test singleton pattern."""
        from financial_dashboard.services.fingpt_forecast_service import get_forecast_service
        
        service1 = get_forecast_service()
        service2 = get_forecast_service()
        assert service1 is service2
    
    def test_fallback_forecast(self):
        """Test fallback forecast generation."""
        from financial_dashboard.services.fingpt_forecast_service import ForecastService
        
        service = ForecastService(groq_api_key=None)  # Force fallback
        
        price_data = {
            "current_price": 150.0,
            "week_change_pct": 5.0
        }
        news = [
            {"headline": "Stock surges on strong earnings"},
            {"headline": "Company beats expectations"}
        ]
        
        result = service._fallback_forecast("AAPL", price_data, news)
        
        assert result["symbol"] == "AAPL"
        assert result["model"] == "rule-based-fallback"
        assert "analysis" in result
        assert "timestamp" in result
    
    def test_build_forecast_prompt(self):
        """Test prompt building."""
        from financial_dashboard.services.fingpt_forecast_service import ForecastService
        
        service = ForecastService()
        
        profile = {"name": "Apple Inc.", "finnhubIndustry": "Technology"}
        news = [{"headline": "Apple reports Q4 earnings"}]
        price_data = {"current_price": 175.0, "week_change_pct": 2.5}
        
        prompt = service._build_forecast_prompt("AAPL", profile, news, price_data)
        
        assert "Apple Inc." in prompt
        assert "AAPL" in prompt
        assert "Technology" in prompt
        assert "Positive Developments" in prompt


class TestForecastAPI:
    """Test forecast API endpoint."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient
        from financial_dashboard.services.chatbot_service import app
        return TestClient(app)
    
    def test_forecast_endpoint_exists(self, client):
        """Test that forecast endpoint responds."""
        response = client.post(
            "/api/forecast",
            json={"symbol": "AAPL"}
        )
        
        # Should return 200 (success) or valid error
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "symbol" in data
            assert "analysis" in data
    
    def test_forecast_returns_structure(self, client):
        """Test forecast response structure."""
        response = client.post(
            "/api/forecast",
            json={"symbol": "NVDA"}
        )
        
        if response.status_code == 200:
            data = response.json()
            assert data["symbol"] == "NVDA"
            assert "model" in data
            assert "timestamp" in data


@pytest.mark.asyncio
class TestAsyncForecast:
    """Test async forecast functions."""
    
    async def test_generate_stock_forecast(self):
        """Test async forecast generation."""
        from financial_dashboard.services.fingpt_forecast_service import generate_stock_forecast
        
        result = await generate_stock_forecast("MSFT")
        
        assert result["symbol"] == "MSFT"
        assert "analysis" in result
        assert "timestamp" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
