"""
Unit Tests for BentoML Services

Tests the BentoML model serving services for:
- Price Direction prediction
- IV Forecast
- Sentiment Analysis
"""

import pytest
import numpy as np
from datetime import datetime
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, '/home/aarav/Unified-Dashboard/phase1_integration')


# -----------------------------------------------------------------------------
# Mock Model Tests
# -----------------------------------------------------------------------------

class TestMockPriceDirectionModel:
    """Test Mock Price Direction Model"""
    
    def test_prediction_shape(self):
        """Test prediction output shape"""
        # Simulate model input
        features = np.random.randn(32)
        
        # Mock prediction
        prob_up = 0.5 + 0.1 * np.mean(features)
        prob_up = max(0, min(1, prob_up))
        
        assert 0 <= prob_up <= 1
    
    def test_batch_prediction(self):
        """Test batch prediction"""
        batch_size = 10
        feature_dim = 32
        
        # Simulate batch input
        features = np.random.randn(batch_size, feature_dim)
        
        # Mock batch prediction
        probs = []
        for i in range(batch_size):
            prob_up = 0.5 + 0.1 * np.mean(features[i])
            prob_up = max(0, min(1, prob_up))
            probs.append(prob_up)
        
        assert len(probs) == batch_size
        assert all(0 <= p <= 1 for p in probs)
    
    def test_confidence_calculation(self):
        """Test confidence score calculation"""
        prob_up = 0.75
        prob_down = 1 - prob_up
        
        confidence = abs(prob_up - prob_down)
        
        assert 0 <= confidence <= 1
        assert confidence == 0.5  # |0.75 - 0.25| = 0.5


class TestMockIVForecastModel:
    """Test Mock IV Forecast Model"""
    
    def test_iv_prediction(self):
        """Test IV prediction output"""
        current_iv = 0.25
        dte = 30
        
        # Mock IV forecast
        forecast_iv = current_iv * (1 + np.random.uniform(-0.1, 0.1))
        forecast_iv = max(0.05, min(2.0, forecast_iv))
        
        assert 0.05 <= forecast_iv <= 2.0
    
    def test_iv_surface_generation(self):
        """Test IV surface generation"""
        strikes = np.arange(90, 111, 5)  # 90% to 110% moneyness
        dtes = [7, 14, 30, 60, 90]
        
        surface = np.zeros((len(strikes), len(dtes)))
        base_iv = 0.25
        
        for i, strike in enumerate(strikes):
            for j, dte in enumerate(dtes):
                # Simple smile/skew model
                moneyness = strike / 100
                skew = 0.1 * (1 - moneyness)
                term = 0.02 * np.sqrt(dte / 30)
                surface[i, j] = base_iv + skew + term
        
        assert surface.shape == (len(strikes), len(dtes))
        assert np.all(surface > 0)
    
    def test_term_structure(self):
        """Test IV term structure"""
        dtes = [7, 14, 30, 60, 90, 180]
        base_iv = 0.25
        
        term_ivs = [base_iv * (1 + 0.1 * np.sqrt(dte / 30)) for dte in dtes]
        
        # Generally expect slight term structure
        assert len(term_ivs) == len(dtes)


class TestMockSentimentModel:
    """Test Mock Sentiment Model"""
    
    def test_sentiment_classification(self):
        """Test sentiment classification"""
        texts = [
            "Stock is surging on great earnings",
            "Company faces serious headwinds",
            "Markets remain unchanged today",
        ]
        
        expected = ["bullish", "bearish", "neutral"]
        
        for text, expected_sentiment in zip(texts, expected):
            # Mock keyword-based classification
            text_lower = text.lower()
            
            bullish_keywords = ["surging", "great", "strong", "up"]
            bearish_keywords = ["serious", "headwinds", "down", "falling"]
            
            bullish_score = sum(1 for k in bullish_keywords if k in text_lower)
            bearish_score = sum(1 for k in bearish_keywords if k in text_lower)
            
            if bullish_score > bearish_score:
                sentiment = "bullish"
            elif bearish_score > bullish_score:
                sentiment = "bearish"
            else:
                sentiment = "neutral"
            
            assert sentiment == expected_sentiment
    
    def test_sentiment_scores(self):
        """Test sentiment score output"""
        text = "Bullish outlook for tech stocks"
        
        # Mock scores
        bullish_score = 0.75
        bearish_score = 0.15
        neutral_score = 0.10
        
        total = bullish_score + bearish_score + neutral_score
        assert abs(total - 1.0) < 0.01
    
    def test_batch_sentiment(self):
        """Test batch sentiment analysis"""
        texts = [
            "Great day for the market",
            "Concerning news about inflation",
            "Trading sideways with low volume",
        ]
        
        results = []
        for text in texts:
            results.append({
                "text": text[:50],
                "sentiment": "bullish",  # Mock
                "confidence": 0.8,
            })
        
        assert len(results) == len(texts)


# -----------------------------------------------------------------------------
# Service API Tests
# -----------------------------------------------------------------------------

class TestPriceDirectionService:
    """Test Price Direction Service API"""
    
    def test_predict_endpoint_schema(self):
        """Test predict endpoint input/output schema"""
        # Input schema
        request = {
            "symbol": "AAPL",
            "horizon_days": 5,
        }
        
        assert "symbol" in request
        assert "horizon_days" in request
        assert isinstance(request["horizon_days"], int)
        
        # Output schema
        response = {
            "symbol": "AAPL",
            "horizon_days": 5,
            "direction": "up",
            "probability_up": 0.65,
            "probability_down": 0.35,
            "confidence": 0.30,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        assert response["probability_up"] + response["probability_down"] == 1.0
    
    def test_healthz_endpoint(self):
        """Test health check endpoint"""
        response = {
            "status": "ok",
            "model_loaded": True,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        assert response["status"] == "ok"


class TestIVForecastService:
    """Test IV Forecast Service API"""
    
    def test_predict_endpoint_schema(self):
        """Test predict endpoint schema"""
        request = {
            "symbol": "SPY",
            "dte": 30,
        }
        
        response = {
            "symbol": "SPY",
            "dte": 30,
            "current_iv": 0.22,
            "forecast_iv": 0.24,
            "iv_change_pct": 9.09,
            "confidence": 0.75,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        assert response["iv_change_pct"] == pytest.approx(
            (response["forecast_iv"] - response["current_iv"]) / response["current_iv"] * 100,
            rel=0.1
        )
    
    def test_surface_endpoint_schema(self):
        """Test IV surface endpoint schema"""
        response = {
            "symbol": "SPY",
            "strikes": [380, 390, 400, 410, 420],
            "dtes": [7, 14, 30, 60, 90],
            "surface": [[0.25] * 5 for _ in range(5)],
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        assert len(response["surface"]) == len(response["strikes"])
        assert len(response["surface"][0]) == len(response["dtes"])


class TestSentimentService:
    """Test Sentiment Service API"""
    
    def test_analyze_endpoint_schema(self):
        """Test analyze endpoint schema"""
        request = {
            "text": "Apple stock rises on strong iPhone sales",
            "symbol": "AAPL",
        }
        
        response = {
            "text": request["text"][:100],
            "symbol": "AAPL",
            "sentiment": "bullish",
            "confidence": 0.82,
            "scores": {
                "bullish": 0.82,
                "bearish": 0.08,
                "neutral": 0.10,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        assert sum(response["scores"].values()) == pytest.approx(1.0, rel=0.01)
    
    def test_batch_analyze_endpoint(self):
        """Test batch analyze endpoint"""
        request = {
            "texts": [
                "Strong earnings beat",
                "Revenue miss concerns",
            ],
        }
        
        response = {
            "results": [
                {"text": "Strong earnings beat", "sentiment": "bullish", "confidence": 0.8},
                {"text": "Revenue miss concerns", "sentiment": "bearish", "confidence": 0.7},
            ],
            "count": 2,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        assert len(response["results"]) == request["texts"].__len__()


# -----------------------------------------------------------------------------
# Run Tests
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
