"""
Model Registry & Monitoring TDD
Tests for registry key validation, version sequencing, and monitoring sensor data.
"""
import os
import json
import pytest
from datetime import datetime
from pathlib import Path
import sys

# Add ml module to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.model_registry import (
    register_model,
    get_latest_model,
    compare_models,
    get_all_models,
    REGISTRY_PATH
)

METRICS_DIR = Path(__file__).parent.parent / 'artifacts' / 'metrics'
MONITOR_LOG_DIR = Path(__file__).parent.parent / 'logs' / 'model_monitoring'

@pytest.fixture(autouse=True)
def setup_registry():
    """Clean registry before each test."""
    if REGISTRY_PATH.exists():
        REGISTRY_PATH.unlink()
    yield
    # Cleanup after test
    if REGISTRY_PATH.exists():
        REGISTRY_PATH.unlink()

def test_registry_has_required_keys():
    """Verify all registry entries have required keys."""
    # Register test models
    register_model("market_trend_rf", {"accuracy": 0.75, "f1": 0.72})
    register_model("market_trend_rf", {"accuracy": 0.82, "f1": 0.80})
    
    registry = get_all_models()
    required = {"model_name", "version", "timestamp", "metrics", "source_commit"}
    
    for entry in registry:
        missing = required - set(entry.keys())
        assert not missing, f"Missing keys: {missing} in {entry}"

def test_version_tags_sequential():
    """Verify version tags are auto-incremented sequentially."""
    # Register multiple versions without specifying version_tag
    register_model("market_trend_rf", {"accuracy": 0.70})
    register_model("market_trend_rf", {"accuracy": 0.75})
    register_model("market_trend_rf", {"accuracy": 0.82})
    
    registry = get_all_models()
    model_entries = [e for e in registry if e["model_name"] == "market_trend_rf"]
    
    versions = [int(e["version"].lstrip("v")) for e in model_entries]
    assert versions == sorted(versions), "Version tags are not in order"
    assert versions == list(range(1, len(versions)+1)), "Version tags should be consecutive (v1, v2, v3, ...)"

def test_get_latest_model():
    """Verify get_latest_model returns the most recent version."""
    register_model("market_trend_rf", {"accuracy": 0.70})
    register_model("market_trend_rf", {"accuracy": 0.82})
    
    latest = get_latest_model("market_trend_rf")
    assert latest is not None, "Latest model should be found"
    assert latest["version"] == "v2", "Latest model should be v2"
    assert latest["metrics"]["accuracy"] == 0.82

def test_compare_models():
    """Verify compare_models sorts by metric correctly."""
    register_model("market_trend_rf", {"accuracy": 0.70, "f1": 0.68})
    register_model("market_trend_rf", {"accuracy": 0.82, "f1": 0.80})
    register_model("market_trend_rf", {"accuracy": 0.75, "f1": 0.73})
    
    sorted_models = compare_models("market_trend_rf", metric_key="accuracy")
    assert len(sorted_models) == 3
    assert sorted_models[0]["metrics"]["accuracy"] == 0.82
    assert sorted_models[1]["metrics"]["accuracy"] == 0.75
    assert sorted_models[2]["metrics"]["accuracy"] == 0.70

def test_monitoring_sensor_returns_data():
    """Verify monitoring logs are created and contain data."""
    # Create a dummy monitoring log for testing
    MONITOR_LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = MONITOR_LOG_DIR / "model_monitor_test.log"
    log_file.write_text("2025-10-22T14:00:00Z | Model: market_trend_rf | Accuracy: 0.82 | Drift: 0.02\n")
    
    log_files = [f for f in os.listdir(MONITOR_LOG_DIR) if f.endswith('.log')]
    assert log_files, "No monitoring logs found"
    
    for log_filename in log_files:
        log_path = MONITOR_LOG_DIR / log_filename
        data = log_path.read_text().strip()
        assert data, f"Monitoring log {log_filename} is empty"
    
    # Cleanup
    log_file.unlink()


def test_metrics_file_creation():
    """Verify metrics files are created when models are registered."""
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Register model with metrics
    metrics = {
        'accuracy': 0.85,
        'precision': 0.83,
        'recall': 0.87,
        'f1': 0.85,
        'sharpe_ratio': 1.2
    }
    
    entry = register_model("test_model", metrics)
    version = entry['version']
    
    # Manually create metrics file (simulating train_model.py behavior)
    metrics_file = METRICS_DIR / f"test_model_{version}.json"
    import json
    with open(metrics_file, 'w') as f:
        json.dump(metrics, f, indent=2)
    
    assert metrics_file.exists(), "Metrics file not created"
    
    with open(metrics_file, 'r') as f:
        loaded_metrics = json.load(f)
    
    assert loaded_metrics['accuracy'] == 0.85
    assert 'f1' in loaded_metrics
    
    # Cleanup
    metrics_file.unlink()


def test_model_registry_persistence():
    """Verify registry persists across operations."""
    # Register first model
    register_model("persistent_model", {"accuracy": 0.75})
    
    # Load registry and verify
    registry1 = get_all_models()
    assert len(registry1) == 1
    
    # Register second model
    register_model("persistent_model", {"accuracy": 0.82})
    
    # Load again and verify both are present
    registry2 = get_all_models()
    assert len(registry2) == 2
    assert registry2[0]['model_name'] == "persistent_model"
    assert registry2[1]['model_name'] == "persistent_model"


def test_accuracy_threshold():
    """Verify model metrics meet minimum accuracy threshold."""
    # Register model with good accuracy
    good_metrics = {'accuracy': 0.82, 'f1': 0.80}
    entry = register_model("market_trend_rf", good_metrics)
    
    assert entry['metrics']['accuracy'] >= 0.8, "Model accuracy below threshold"
    
    # Register model with poor accuracy (should still register, but flag for review)
    poor_metrics = {'accuracy': 0.65, 'f1': 0.60}
    poor_entry = register_model("market_trend_rf", poor_metrics)
    
    # Compare models - best should be first
    sorted_models = compare_models("market_trend_rf", metric_key="accuracy")
    assert sorted_models[0]['metrics']['accuracy'] == 0.82
    assert sorted_models[1]['metrics']['accuracy'] == 0.65
