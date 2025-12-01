"""
Market Forecast Unit Tests - AGENT-1B Phase 6
Test API endpoints, adapter logic, and persistence layer
"""

import pytest
import json
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

# Import modules under test
from api.market_forecast import bp as forecast_bp
from services.forecast_adapter import ForecastAdapter
from services.forecast_persistence import ForecastPersistence


@pytest.fixture
def test_app():
    """Flask test app with forecast blueprint"""
    from flask import Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(forecast_bp)
    return app


@pytest.fixture
def client(test_app):
    """Flask test client"""
    return test_app.test_client()


@pytest.fixture
def fixture_data():
    """Load forecast fixture"""
    fixture_path = Path("tests/fixtures/forecast/forecast_fixture.json")
    with open(fixture_path) as f:
        return json.load(f)


@pytest.fixture
def explain_data():
    """Load explanation fixture"""
    fixture_path = Path("tests/fixtures/forecast/explain_fixture.json")
    with open(fixture_path) as f:
        return json.load(f)


class TestForecastAPI:
    """Test forecast API endpoints"""
    
    def test_run_forecast_sync_success(self, client, fixture_data):
        """Test successful sync forecast execution"""
        with patch("services.forecast_adapter.ForecastAdapter.run_forecast") as mock_run:
            mock_run.return_value = fixture_data
            
            response = client.post("/api/market_forecast/run", json={
                "ticker": "AAPL",
                "horizon": 30,
                "confidence": 0.95,
                "model": "lstm",
                "mode": "sync"
            })
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["ticker"] == "AAPL"
            assert data["horizon"] == 30
            assert len(data["forecast"]) == 30
    
    def test_run_forecast_missing_ticker(self, client):
        """Test forecast request with missing ticker"""
        response = client.post("/api/market_forecast/run", json={
            "horizon": 30,
            "confidence": 0.95,
            "model": "lstm"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "ticker is required" in data["error"]
    
    def test_run_forecast_invalid_horizon(self, client):
        """Test forecast request with invalid horizon"""
        response = client.post("/api/market_forecast/run", json={
            "ticker": "AAPL",
            "horizon": 60,  # Invalid: not in [7, 30, 90]
            "confidence": 0.95,
            "model": "lstm"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "horizon must be 7, 30, or 90" in data["error"]
    
    def test_run_forecast_invalid_confidence(self, client):
        """Test forecast request with invalid confidence"""
        response = client.post("/api/market_forecast/run", json={
            "ticker": "AAPL",
            "horizon": 30,
            "confidence": 0.92,  # Invalid: not in [0.90, 0.95, 0.99]
            "model": "lstm"
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert "confidence must be 0.90, 0.95, or 0.99" in data["error"]
    
    def test_get_latest_forecast(self, client, fixture_data):
        """Test retrieving latest forecast"""
        with patch("services.forecast_adapter.ForecastAdapter.get_latest") as mock_latest:
            mock_latest.return_value = fixture_data
            
            response = client.get("/api/market_forecast/latest?ticker=AAPL")
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["ticker"] == "AAPL"
    
    def test_get_latest_forecast_not_found(self, client):
        """Test latest forecast when none exist"""
        with patch("services.forecast_adapter.ForecastAdapter.get_latest") as mock_latest:
            mock_latest.return_value = None
            
            response = client.get("/api/market_forecast/latest")
            
            assert response.status_code == 404
            data = response.get_json()
            assert "No forecasts found" in data["error"]
    
    def test_get_forecast_history(self, client, fixture_data):
        """Test retrieving forecast history"""
        with patch("services.forecast_adapter.ForecastAdapter.get_history") as mock_history:
            mock_history.return_value = {
                "forecasts": [fixture_data],
                "total": 1,
                "limit": 20,
                "offset": 0
            }
            
            response = client.get("/api/market_forecast/history?ticker=AAPL&limit=10")
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["total"] == 1
            assert len(data["forecasts"]) == 1
    
    def test_get_forecast_explanation(self, client, explain_data):
        """Test retrieving SHAP explanation"""
        with patch("services.forecast_adapter.ForecastAdapter.get_explanation") as mock_explain:
            mock_explain.return_value = explain_data
            
            response = client.get("/api/market_forecast/explain/test-forecast-001")
            
            assert response.status_code == 200
            data = response.get_json()
            assert len(data["shap_values"]) == 6
            assert data["base_value"] == 150.0
    
    def test_health_check_healthy(self, client):
        """Test health check endpoint"""
        with patch("services.forecast_adapter.ForecastAdapter.health_check") as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "bento_available": True,
                "deterministic_mode": False,
                "persistence_type": "json",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            response = client.get("/api/market_forecast/admin/health")
            
            assert response.status_code == 200
            data = response.get_json()
            assert data["status"] == "healthy"


class TestForecastAdapter:
    """Test forecast adapter logic"""
    
    def test_deterministic_mode_loads_fixture(self, fixture_data):
        """Test that deterministic mode loads from fixture"""
        adapter = ForecastAdapter(
            bento_url="http://localhost:5001/predict",
            deterministic=True
        )
        
        result = adapter.run_forecast(
            ticker="AAPL",
            horizon=30,
            confidence=0.95,
            model="lstm",
            forecast_id="test-001"
        )
        
        assert result["ticker"] == "AAPL"
        assert result["horizon"] == 30
        assert len(result["forecast"]) == 30
    
    @patch("services.forecast_adapter.requests.post")
    def test_bento_mode_calls_service(self, mock_post, fixture_data):
        """Test that non-deterministic mode calls Bento service"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = fixture_data
        mock_post.return_value = mock_response
        
        adapter = ForecastAdapter(
            bento_url="http://localhost:5001/predict",
            deterministic=False
        )
        
        result = adapter.run_forecast(
            ticker="TSLA",
            horizon=7,
            confidence=0.90,
            model="prophet",
            forecast_id="test-002"
        )
        
        # Verify HTTP call was made
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "http://localhost:5001/predict"
        assert call_args[1]["json"]["ticker"] == "TSLA"
    
    @patch("services.forecast_adapter.requests.post")
    def test_bento_failure_fallback_to_fixture(self, mock_post, fixture_data):
        """Test fallback to fixture when Bento service fails"""
        mock_post.side_effect = Exception("Bento service unavailable")
        
        adapter = ForecastAdapter(
            bento_url="http://localhost:5001/predict",
            deterministic=False
        )
        
        result = adapter.run_forecast(
            ticker="AAPL",
            horizon=30,
            confidence=0.95,
            model="lstm",
            forecast_id="test-003"
        )
        
        # Should fallback to fixture
        assert result["ticker"] == "AAPL"
        assert len(result["forecast"]) == 30


class TestForecastPersistence:
    """Test persistence layer"""
    
    def test_json_save_and_retrieve(self, fixture_data, tmp_path):
        """Test saving and retrieving forecast from JSON"""
        # Use tmp_path for isolated testing
        with patch.object(Path, "mkdir"):
            persistence = ForecastPersistence(db_url=None)
            persistence.data_dir = tmp_path / "forecast"
            persistence.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Save forecast
            persistence.save_forecast("test-001", fixture_data)
            
            # Retrieve forecast
            result = persistence.get_forecast("test-001")
            
            assert result is not None
            assert result["forecast_id"] == fixture_data["forecast_id"]
            assert result["ticker"] == fixture_data["ticker"]
    
    def test_json_get_latest(self, fixture_data, tmp_path):
        """Test retrieving latest forecast from JSON"""
        with patch.object(Path, "mkdir"):
            persistence = ForecastPersistence(db_url=None)
            persistence.data_dir = tmp_path / "forecast"
            persistence.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Save multiple forecasts
            for i in range(3):
                data = fixture_data.copy()
                data["forecast_id"] = f"test-{i:03d}"
                data["timestamp"] = f"2024-01-{15+i:02d}T12:00:00Z"
                persistence.save_forecast(f"test-{i:03d}", data)
            
            # Get latest
            result = persistence.get_latest(ticker="AAPL")
            
            assert result is not None
            # Latest should be test-002 (highest timestamp)
            assert result["forecast_id"] == "test-002"
    
    def test_json_get_history_pagination(self, fixture_data, tmp_path):
        """Test paginated history retrieval"""
        with patch.object(Path, "mkdir"):
            persistence = ForecastPersistence(db_url=None)
            persistence.data_dir = tmp_path / "forecast"
            persistence.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Save 10 forecasts
            for i in range(10):
                data = fixture_data.copy()
                data["forecast_id"] = f"test-{i:03d}"
                persistence.save_forecast(f"test-{i:03d}", data)
            
            # Get page 2 (offset=5, limit=3)
            result = persistence.get_history(limit=3, offset=5)
            
            assert result["total"] == 10
            assert len(result["forecasts"]) == 3
            assert result["limit"] == 3
            assert result["offset"] == 5


# Property-based tests require hypothesis
try:
    from hypothesis import given, strategies as st
    
    class TestForecastProperties:
        """Property-based tests for forecast logic"""
        
        @given(
            ticker=st.text(min_size=1, max_size=5, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ"),
            horizon=st.sampled_from([7, 30, 90]),
            confidence=st.sampled_from([0.90, 0.95, 0.99])
        )
        def test_forecast_always_returns_correct_length(self, ticker, horizon, confidence):
            """Property: Forecast length always matches horizon"""
            adapter = ForecastAdapter(
                bento_url="http://localhost:5001/predict",
                deterministic=True
            )
            
            result = adapter.run_forecast(
                ticker=ticker,
                horizon=horizon,
                confidence=confidence,
                model="lstm",
                forecast_id="prop-test-001"
            )
            
            assert len(result["forecast"]) <= horizon  # May be truncated to match horizon
        
        @given(
            ticker=st.text(min_size=1, max_size=5, alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ")
        )
        def test_forecast_confidence_intervals_valid(self, ticker):
            """Property: yhat_lower <= yhat <= yhat_upper for all forecasts"""
            adapter = ForecastAdapter(
                bento_url="http://localhost:5001/predict",
                deterministic=True
            )
            
            result = adapter.run_forecast(
                ticker=ticker,
                horizon=30,
                confidence=0.95,
                model="lstm",
                forecast_id="prop-test-002"
            )
            
            for point in result["forecast"]:
                assert point["yhat_lower"] <= point["yhat"], \
                    f"Lower bound {point['yhat_lower']} exceeds prediction {point['yhat']}"
                assert point["yhat"] <= point["yhat_upper"], \
                    f"Prediction {point['yhat']} exceeds upper bound {point['yhat_upper']}"

except ImportError:
    print("hypothesis not installed, skipping property-based tests")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
