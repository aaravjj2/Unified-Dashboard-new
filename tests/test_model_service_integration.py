"""
Integration tests for Model Service API
Tests with actual (small) trained model.
"""
import pytest
import json
import pickle
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient


def create_test_model_and_registry(tmp_path):
    """Create a minimal test model and registry."""
    try:
        from sklearn.ensemble import RandomForestClassifier
    except ImportError:
        pytest.skip("sklearn not available")
    
    # Train a tiny model
    X = np.random.rand(20, 5)
    y = np.random.randint(0, 2, 20)
    
    model = RandomForestClassifier(n_estimators=2, max_depth=2, random_state=42)
    model.fit(X, y)
    
    # Save model
    models_dir = tmp_path / "artifacts" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / "market_trend_rf_latest.pkl"
    
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    # Create registry
    registry = [{
        "model_name": "market_trend_rf",
        "version": "v1",
        "timestamp": "2025-10-23T00:00:00Z",
        "metrics": {"accuracy": 0.85, "f1": 0.83},
        "source_commit": "test123",
        "model_path": str(model_path),
        "feature_cols": ["price_momentum", "price_change_pct", "volume_change", "volatility", "sentiment"]
    }]
    
    registry_path = tmp_path / "artifacts" / "model_registry.json"
    with open(registry_path, 'w') as f:
        json.dump(registry, f)
    
    return registry_path, model_path


def test_model_service_integration(tmp_path, monkeypatch):
    """
    Integration test: create real model, load it, make predictions.
    """
    # Create test model and registry
    registry_path, model_path = create_test_model_and_registry(tmp_path)
    
    # Patch registry path
    import ml.model_registry as registry_module
    monkeypatch.setattr(registry_module, 'REGISTRY_PATH', registry_path)
    
    # Import app AFTER patching
    from services.model_service import app, lifespan
    import services.model_service as model_service_module
    
    # Manually trigger lifespan startup
    import asyncio
    async def setup():
        async with lifespan(app):
            pass
    
    # Run startup
    asyncio.run(setup())
    
    # Now create test client
    client = TestClient(app)
    
    # Test health endpoint
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    print(f"Health response: {data}")
    assert "status" in data
    assert data["model_name"] == "market_trend_rf"
    assert data["model_version"] == "v1"
    
    # Test predict endpoint
    response = client.post("/api/predict", json={
        "price_momentum": 0.05,
        "price_change_pct": 2.3,
        "volume_change": 0.15,
        "volatility": 0.02,
        "sentiment": 0.6
    })
    assert response.status_code == 200
    data = response.json()
    assert "prediction" in data
    assert "confidence" in data
    assert data["prediction"] in [0, 1]
    assert 0 <= data["confidence"] <= 1
    
    # Test model info endpoint
    response = client.get("/api/model/info")
    assert response.status_code == 200
    data = response.json()
    assert data["model_name"] == "market_trend_rf"
    assert data["version"] == "v1"
    
    print("✅ Integration test passed")
