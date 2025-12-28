"""
Tests for FinGPT Sentiment Service
==================================
Unit tests for sentiment analysis including model loading, inference, and fallback behavior.
"""

import pytest
from datetime import datetime


class TestSentimentFallback:
    """Test rule-based fallback sentiment analysis."""
    
    def test_positive_sentiment(self):
        """Test positive sentiment detection."""
        from financial_dashboard.services.fingpt_sentiment_service import analyze_sentiment_fallback
        
        text = "NVDA stock surges 10% on strong earnings beat"
        result = analyze_sentiment_fallback(text)
        
        assert result["sentiment"] == "positive"
        assert result["score"] > 0
        assert result["model"] == "rule-based"
        assert "timestamp" in result
    
    def test_negative_sentiment(self):
        """Test negative sentiment detection."""
        from financial_dashboard.services.fingpt_sentiment_service import analyze_sentiment_fallback
        
        text = "Tech stocks crash as recession fears mount, major decline expected"
        result = analyze_sentiment_fallback(text)
        
        assert result["sentiment"] == "negative"
        assert result["score"] < 0
        assert result["model"] == "rule-based"
    
    def test_neutral_sentiment(self):
        """Test neutral sentiment detection."""
        from financial_dashboard.services.fingpt_sentiment_service import analyze_sentiment_fallback
        
        text = "Apple announces new product launch next Tuesday"
        result = analyze_sentiment_fallback(text)
        
        assert result["sentiment"] == "neutral"
        assert result["score"] == 0.0
        assert result["model"] == "rule-based"
    
    def test_confidence_is_lower_for_fallback(self):
        """Fallback should have lower confidence than FinGPT."""
        from financial_dashboard.services.fingpt_sentiment_service import analyze_sentiment_fallback
        
        result = analyze_sentiment_fallback("Some stock news")
        assert result["confidence"] == 0.5  # Lower than FinGPT's 0.85


class TestSentimentMain:
    """Test main sentiment analysis function."""
    
    def test_analyze_sentiment_returns_dict(self):
        """Test that analyze_sentiment_fingpt returns proper dict structure."""
        from financial_dashboard.services.fingpt_sentiment_service import analyze_sentiment_fingpt
        
        text = "Market rally continues with strong gains"
        result = analyze_sentiment_fingpt(text)
        
        # Check structure
        assert "sentiment" in result
        assert "score" in result
        assert "confidence" in result
        assert "model" in result
        assert "timestamp" in result
        
        # Check valid sentiment
        assert result["sentiment"] in ["positive", "negative", "neutral"]
    
    def test_batch_sentiment(self):
        """Test batch sentiment analysis."""
        from financial_dashboard.services.fingpt_sentiment_service import analyze_batch_sentiment
        
        texts = [
            "Stock surges on earnings",
            "Market crashes today",
            "Company reports results"
        ]
        
        results = analyze_batch_sentiment(texts)
        
        assert len(results) == 3
        assert results[0]["sentiment"] == "positive"
        assert results[1]["sentiment"] == "negative"


class TestFinGPTAvailability:
    """Test FinGPT model availability checks."""
    
    def test_fingpt_availability_check(self):
        """Test is_fingpt_available function."""
        from financial_dashboard.services.fingpt_sentiment_service import is_fingpt_available
        
        # By default, FinGPT is not loaded (requires GPU)
        available = is_fingpt_available()
        assert isinstance(available, bool)


class TestSentimentAPI:
    """Test sentiment API endpoint via HTTP."""
    
    @pytest.fixture
    def client(self):
        """Create test client for chatbot service."""
        from fastapi.testclient import TestClient
        from financial_dashboard.services.chatbot_service import app
        return TestClient(app)
    
    def test_sentiment_endpoint(self, client):
        """Test /api/sentiment endpoint."""
        response = client.post(
            "/api/sentiment",
            json={"text": "Stock price rises sharply"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["sentiment"] == "positive"
        assert "score" in data
    
    def test_sentiment_endpoint_negative(self, client):
        """Test negative sentiment via API."""
        response = client.post(
            "/api/sentiment",
            json={"text": "Major losses reported as stock plunges"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["sentiment"] == "negative"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
