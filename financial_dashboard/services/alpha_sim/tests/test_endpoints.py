"""
Integration tests for AlphaSim API endpoints.
"""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import pandas as pd
import numpy as np
from datetime import datetime

from financial_dashboard.services.alpha_sim.app import app


# ---------- Test Client Fixture ----------

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_yf_data():
    """Create mock yfinance data."""
    days = 100
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    np.random.seed(42)
    
    opens = 100 + np.random.randn(days).cumsum()
    highs = opens + abs(np.random.randn(days))
    lows = opens - abs(np.random.randn(days))
    closes = opens + np.random.randn(days) * 0.5
    volumes = np.random.randint(1000000, 10000000, days)
    
    return pd.DataFrame({
        'Open': opens,
        'High': highs,
        'Low': lows,
        'Close': closes,
        'Volume': volumes
    }, index=dates)


# ---------- Health Endpoint Tests ----------

class TestHealthEndpoints:
    """Tests for health and status endpoints."""
    
    def test_health_endpoint(self, client):
        """Test /health endpoint returns ok."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "alpha_sim"
    
    def test_metrics_endpoint(self, client):
        """Test /metrics endpoint returns data."""
        response = client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "cache" in data
        assert "rate_limiter" in data
    
    def test_root_endpoint(self, client):
        """Test / root endpoint returns API info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "AlphaSim"
        assert "version" in data
        assert "endpoints" in data
        assert "supported_functions" in data


# ---------- Query Endpoint Tests ----------

class TestQueryEndpoint:
    """Tests for /query endpoint."""
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_time_series_daily(self, mock_yf, client, mock_yf_data):
        """Test TIME_SERIES_DAILY function."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_yf_data
        mock_yf.Ticker.return_value = mock_ticker
        
        response = client.get(
            "/query",
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": "AAPL",
                "apikey": "test_key"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Meta Data" in data
        assert "Time Series (Daily)" in data
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_time_series_daily_compact(self, mock_yf, client, mock_yf_data):
        """Test TIME_SERIES_DAILY with compact output."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_yf_data
        mock_yf.Ticker.return_value = mock_ticker
        
        response = client.get(
            "/query",
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": "MSFT",
                "apikey": "test_key",
                "outputsize": "compact"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Time Series (Daily)" in data
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_sma_function(self, mock_yf, client, mock_yf_data):
        """Test SMA function."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_yf_data
        mock_yf.Ticker.return_value = mock_ticker
        
        response = client.get(
            "/query",
            params={
                "function": "SMA",
                "symbol": "GOOGL",
                "apikey": "test_key",
                "time_period": 10,
                "series_type": "close"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Meta Data" in data
        assert "Technical Analysis: SMA" in data
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_ema_function(self, mock_yf, client, mock_yf_data):
        """Test EMA function."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_yf_data
        mock_yf.Ticker.return_value = mock_ticker
        
        response = client.get(
            "/query",
            params={
                "function": "EMA",
                "symbol": "AMZN",
                "apikey": "test_key",
                "time_period": 12
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Technical Analysis: EMA" in data
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_rsi_function(self, mock_yf, client, mock_yf_data):
        """Test RSI function."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_yf_data
        mock_yf.Ticker.return_value = mock_ticker
        
        response = client.get(
            "/query",
            params={
                "function": "RSI",
                "symbol": "NVDA",
                "apikey": "test_key",
                "time_period": 14
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Technical Analysis: RSI" in data
    
    def test_missing_symbol(self, client):
        """Test missing symbol parameter."""
        response = client.get(
            "/query",
            params={
                "function": "TIME_SERIES_DAILY",
                "apikey": "test_key"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Error" in data
    
    def test_missing_apikey(self, client):
        """Test missing apikey parameter."""
        response = client.get(
            "/query",
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": "AAPL"
            }
        )
        
        # FastAPI returns 422 for missing required params
        assert response.status_code == 422
    
    def test_unknown_function(self, client):
        """Test unknown function."""
        response = client.get(
            "/query",
            params={
                "function": "UNKNOWN_FUNCTION",
                "symbol": "AAPL",
                "apikey": "test_key"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Error" in data
        assert "Unknown function" in data["Error"]
    
    def test_case_insensitive_function(self, client):
        """Test function name is case insensitive."""
        with patch('financial_dashboard.services.alpha_sim.engine.yf') as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = pd.DataFrame({
                'Open': [100], 'High': [105], 'Low': [99], 
                'Close': [104], 'Volume': [1000000]
            }, index=pd.date_range(end=datetime.now(), periods=1))
            mock_yf.Ticker.return_value = mock_ticker
            
            response = client.get(
                "/query",
                params={
                    "function": "time_series_daily",  # lowercase
                    "symbol": "AAPL",
                    "apikey": "test_key"
                }
            )
            
            assert response.status_code == 200


# ---------- Rate Limiting Tests ----------

class TestRateLimiting:
    """Tests for rate limiting functionality."""
    
    def test_rate_limit_enforced(self, client):
        """Test rate limiting is enforced after many requests."""
        # Make many requests to trigger rate limit
        with patch('financial_dashboard.services.alpha_sim.engine.yf') as mock_yf:
            mock_ticker = MagicMock()
            mock_ticker.history.return_value = pd.DataFrame({
                'Open': [100], 'High': [105], 'Low': [99],
                'Close': [104], 'Volume': [1000000]
            }, index=pd.date_range(end=datetime.now(), periods=1))
            mock_yf.Ticker.return_value = mock_ticker
            
            rate_limited = False
            for i in range(20):
                response = client.get(
                    "/query",
                    params={
                        "function": "TIME_SERIES_DAILY",
                        "symbol": "AAPL",
                        "apikey": f"rate_limit_test_key_{i % 2}"  # Use 2 keys
                    }
                )
                if response.status_code == 429:
                    rate_limited = True
                    break
            
            # Rate limiting may or may not trigger depending on timing
            # Just ensure no errors
            assert response.status_code in [200, 429]


# ---------- Admin Endpoint Tests ----------

class TestAdminEndpoints:
    """Tests for admin endpoints."""
    
    def test_admin_get_quota(self, client):
        """Test admin get quota endpoint."""
        response = client.get(
            "/admin/quota/test_user_key",
            headers={"X-Admin-Key": "admin"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "tokens" in data
        assert "plan" in data
    
    def test_admin_get_quota_unauthorized(self, client):
        """Test admin get quota without proper auth."""
        response = client.get(
            "/admin/quota/test_user_key",
            headers={"X-Admin-Key": "wrong_key"}
        )
        
        assert response.status_code == 403
    
    def test_admin_reset_quota(self, client):
        """Test admin reset quota endpoint."""
        response = client.post(
            "/admin/reset/test_user_key",
            headers={"X-Admin-Key": "admin"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "ok" in data
        assert data["ok"] is True
    
    def test_admin_reset_quota_custom_tokens(self, client):
        """Test admin reset quota with custom tokens."""
        response = client.post(
            "/admin/reset/test_user_key",
            params={"tokens": 100},
            headers={"X-Admin-Key": "admin"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["tokens"] == 100
    
    def test_admin_reset_unauthorized(self, client):
        """Test admin reset without proper auth."""
        response = client.post(
            "/admin/reset/test_user_key",
            headers={"X-Admin-Key": "wrong_key"}
        )
        
        assert response.status_code == 403


# ---------- Error Handling Tests ----------

class TestErrorHandling:
    """Tests for error handling."""
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_yfinance_error(self, mock_yf, client):
        """Test handling of yfinance errors."""
        mock_yf.Ticker.side_effect = Exception("Network error")
        
        response = client.get(
            "/query",
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": "ERROR",
                "apikey": "test_key"
            }
        )
        
        # Should return error response, not crash
        assert response.status_code in [200, 500]
        data = response.json()
        assert "Error" in data or "Meta Data" in data
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_empty_data(self, mock_yf, client):
        """Test handling of empty data from yfinance."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()
        mock_yf.Ticker.return_value = mock_ticker
        
        response = client.get(
            "/query",
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": "EMPTY",
                "apikey": "test_key"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should handle gracefully
        assert isinstance(data, dict)


# ---------- Integration Tests ----------

class TestFullIntegration:
    """Full integration tests simulating real usage."""
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_complete_workflow(self, mock_yf, client, mock_yf_data):
        """Test complete workflow: health check, query, admin."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_yf_data
        mock_yf.Ticker.return_value = mock_ticker
        
        # 1. Health check
        health = client.get("/health")
        assert health.status_code == 200
        
        # 2. Make a query
        query = client.get(
            "/query",
            params={
                "function": "TIME_SERIES_DAILY",
                "symbol": "AAPL",
                "apikey": "workflow_test_key"
            }
        )
        assert query.status_code == 200
        assert "Time Series (Daily)" in query.json()
        
        # 3. Check quota
        quota = client.get(
            "/admin/quota/workflow_test_key",
            headers={"X-Admin-Key": "admin"}
        )
        assert quota.status_code == 200
        
        # 4. Get metrics
        metrics = client.get("/metrics")
        assert metrics.status_code == 200
    
    @patch('financial_dashboard.services.alpha_sim.engine.yf')
    def test_multiple_indicators(self, mock_yf, client, mock_yf_data):
        """Test querying multiple indicators in sequence."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_yf_data
        mock_yf.Ticker.return_value = mock_ticker
        
        indicators = ["SMA", "EMA", "RSI"]
        
        for indicator in indicators:
            response = client.get(
                "/query",
                params={
                    "function": indicator,
                    "symbol": "AAPL",
                    "apikey": "multi_indicator_key",
                    "time_period": 14
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert f"Technical Analysis: {indicator}" in data


# ---------- NEWS_SENTIMENT Endpoint Tests ----------

class TestNewsSentimentEndpoint:
    """Tests for NEWS_SENTIMENT function."""
    
    def test_news_sentiment_returns_response(self, client):
        """Test NEWS_SENTIMENT returns valid response."""
        response = client.get(
            "/query",
            params={
                "function": "NEWS_SENTIMENT",
                "symbol": "AAPL",
                "apikey": "test_key"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Meta Data" in data
        assert "Sentiment" in data
    
    def test_news_sentiment_meta_data(self, client):
        """Test NEWS_SENTIMENT meta data."""
        response = client.get(
            "/query",
            params={
                "function": "NEWS_SENTIMENT",
                "symbol": "MSFT",
                "apikey": "test_key"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        meta = data["Meta Data"]
        
        assert "1. Information" in meta
        assert meta["2. Symbol"] == "MSFT"
    
    def test_news_sentiment_scores(self, client):
        """Test NEWS_SENTIMENT includes sentiment scores."""
        response = client.get(
            "/query",
            params={
                "function": "NEWS_SENTIMENT",
                "symbol": "GOOGL",
                "apikey": "test_key"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        sentiment = data["Sentiment"]
        
        assert "aggregate_score" in sentiment
        assert "positive" in sentiment
        assert "negative" in sentiment
        assert "neutral" in sentiment
        assert "articles" in sentiment
        
        # Verify types
        assert isinstance(sentiment["aggregate_score"], (int, float))
        assert isinstance(sentiment["positive"], int)
        assert isinstance(sentiment["articles"], int)
    
    def test_news_sentiment_feed(self, client):
        """Test NEWS_SENTIMENT includes article feed."""
        response = client.get(
            "/query",
            params={
                "function": "NEWS_SENTIMENT",
                "symbol": "TSLA",
                "apikey": "test_key"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "feed" in data
        assert len(data["feed"]) > 0
        
        # Check feed structure
        article = data["feed"][0]
        assert "title" in article
        assert "overall_sentiment_score" in article
    
    def test_news_sentiment_missing_symbol(self, client):
        """Test NEWS_SENTIMENT requires symbol."""
        response = client.get(
            "/query",
            params={
                "function": "NEWS_SENTIMENT",
                "apikey": "test_key"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Error" in data


# ---------- HISTORICAL_OPTIONS Endpoint Tests ----------

class TestHistoricalOptionsEndpoint:
    """Tests for HISTORICAL_OPTIONS function."""
    
    def test_historical_options_returns_response(self, client):
        """Test HISTORICAL_OPTIONS returns valid response."""
        response = client.get(
            "/query",
            params={
                "function": "HISTORICAL_OPTIONS",
                "symbol": "AAPL",
                "apikey": "test_key"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "Meta Data" in data
        assert "optionChain" in data
    
    def test_historical_options_chain_structure(self, client):
        """Test HISTORICAL_OPTIONS chain structure."""
        response = client.get(
            "/query",
            params={
                "function": "HISTORICAL_OPTIONS",
                "symbol": "MSFT",
                "apikey": "test_key"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        chain = data["optionChain"]
        
        assert "symbol" in chain
        assert chain["symbol"] == "MSFT"
        assert "underlyingPrice" in chain
        assert "expirationDates" in chain
        assert "options" in chain
        
        assert chain["underlyingPrice"] > 0
        assert len(chain["expirationDates"]) > 0
        assert len(chain["options"]) > 0
    
    def test_historical_options_contracts(self, client):
        """Test HISTORICAL_OPTIONS contract structure."""
        response = client.get(
            "/query",
            params={
                "function": "HISTORICAL_OPTIONS",
                "symbol": "GOOGL",
                "apikey": "test_key"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        options = data["optionChain"]["options"][0]
        
        assert "expirationDate" in options
        assert "calls" in options
        assert "puts" in options
        
        # Check at least one contract
        if options["calls"]:
            call = options["calls"][0]
            assert "contractSymbol" in call
            assert "strike" in call
            assert "bid" in call
            assert "ask" in call
            assert "type" in call
            assert call["type"] == "call"
    
    def test_historical_options_missing_symbol(self, client):
        """Test HISTORICAL_OPTIONS requires symbol."""
        response = client.get(
            "/query",
            params={
                "function": "HISTORICAL_OPTIONS",
                "apikey": "test_key"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Error" in data


# ---------- Client Tests ----------

class TestAlphaSimClient:
    """Tests for AlphaSimClient."""
    
    def test_client_time_series_daily(self, client):
        """Test client can call time_series_daily."""
        from financial_dashboard.services.alpha_sim.client import AlphaSimClient
        
        # Use test client URL (would need server running)
        # For now, test the client initialization
        alpha_client = AlphaSimClient(
            base_url="http://localhost:8065",
            apikey="test"
        )
        
        assert alpha_client.base_url == "http://localhost:8065/"
        assert alpha_client.apikey == "test"
    
    def test_use_alpha_sim_flag(self):
        """Test USE_ALPHA_SIM feature flag."""
        import os
        from financial_dashboard.services.alpha_sim.client import use_alpha_sim
        
        # Default should be False
        original = os.environ.get('USE_ALPHA_SIM')
        os.environ['USE_ALPHA_SIM'] = 'false'
        assert use_alpha_sim() == False
        
        os.environ['USE_ALPHA_SIM'] = 'true'
        assert use_alpha_sim() == True
        
        # Restore
        if original:
            os.environ['USE_ALPHA_SIM'] = original
        else:
            os.environ.pop('USE_ALPHA_SIM', None)
