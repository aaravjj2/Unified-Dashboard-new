"""
Model Registry Manager
Handles model versioning, registration, retrieval, and comparison.
"""
import os
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

REGISTRY_PATH = Path(__file__).parent.parent / "artifacts" / "model_registry.json"

def _get_commit_hash() -> str:
    """Get current git commit hash for reproducibility."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"

def _load_registry() -> List[Dict[str, Any]]:
    """Load existing registry or return empty list."""
    if REGISTRY_PATH.exists():
        with open(REGISTRY_PATH, 'r') as f:
            return json.load(f)
    return []

def _save_registry(registry: List[Dict[str, Any]]) -> None:
    """Save registry to disk."""
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REGISTRY_PATH, 'w') as f:
        json.dump(registry, f, indent=2)

def _get_next_version(model_name: str) -> str:
    """Auto-increment version for a model."""
    registry = _load_registry()
    model_entries = [e for e in registry if e.get("model_name") == model_name]
    
    if not model_entries:
        return "v1"
    
    # Extract version numbers and find max
    versions = []
    for entry in model_entries:
        version_str = entry.get("version", "v0")
        try:
            version_num = int(version_str.lstrip("v"))
            versions.append(version_num)
        except ValueError:
            continue
    
    next_version = max(versions) + 1 if versions else 1
    return f"v{next_version}"

def register_model(
    model_name: str,
    metrics: Dict[str, float],
    version_tag: Optional[str] = None,
    model_path: Optional[str] = None,
    additional_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Register a new model version in the registry.
    
    Args:
        model_name: Name of the model (e.g., 'market_trend_rf')
        metrics: Dictionary of model metrics (accuracy, f1, precision, etc.)
        version_tag: Optional version tag; auto-incremented if None
        model_path: Optional path to saved model file
        additional_metadata: Optional extra metadata to store
    
    Returns:
        Dictionary with registered model entry
    """
    registry = _load_registry()
    
    # Auto-increment version if not provided
    if version_tag is None:
        version_tag = _get_next_version(model_name)
    
    # Build entry
    entry = {
        "model_name": model_name,
        "version": version_tag,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "metrics": metrics,
        "source_commit": _get_commit_hash()
    }
    
    if model_path:
        entry["model_path"] = model_path
    
    if additional_metadata:
        entry.update(additional_metadata)
    
    registry.append(entry)
    _save_registry(registry)
    
    return entry

def get_latest_model(model_name: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve the latest version of a model by name.
    
    Args:
        model_name: Name of the model
    
    Returns:
        Latest model entry or None if not found
    """
    registry = _load_registry()
    model_entries = [e for e in registry if e.get("model_name") == model_name]
    
    if not model_entries:
        return None
    
    # Sort by timestamp descending
    sorted_entries = sorted(
        model_entries,
        key=lambda x: x.get("timestamp", ""),
        reverse=True
    )
    
    return sorted_entries[0]

def compare_models(model_name: str, metric_key: str = "accuracy") -> List[Dict[str, Any]]:
    """
    Compare all versions of a model by a specific metric.
    
    Args:
        model_name: Name of the model
        metric_key: Metric to compare (default: 'accuracy')
    
    Returns:
        List of model entries sorted by metric (descending)
    """
    registry = _load_registry()
    model_entries = [e for e in registry if e.get("model_name") == model_name]
    
    if not model_entries:
        return []
    
    # Sort by specified metric descending
    sorted_entries = sorted(
        model_entries,
        key=lambda x: x.get("metrics", {}).get(metric_key, 0),
        reverse=True
    )
    
    return sorted_entries

def get_all_models() -> List[Dict[str, Any]]:
    """Retrieve all registered models."""
    return _load_registry()

def get_model_by_version(model_name: str, version: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a specific model version.
    
    Args:
        model_name: Name of the model
        version: Version tag (e.g., 'v1', 'v2')
    
    Returns:
        Model entry or None if not found
    """
    registry = _load_registry()
    for entry in registry:
        if entry.get("model_name") == model_name and entry.get("version") == version:
            return entry
    return None
