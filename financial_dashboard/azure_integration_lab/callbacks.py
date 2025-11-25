"""
Azure Integration Lab - Callback and helper stubs

Contains pure-Python stub functions describing the expected behaviors for
deployments, scaling, and monitoring. These functions intentionally do not
perform network operations. They describe inputs/outputs for later wiring.
"""
from typing import Dict, Any


def deploy_to_azure(model_path: str, compute_target: str, config: Dict) -> Dict:
    """Pretend to deploy a model and return deployment metadata.

    Returns a dict with keys: endpoint_url, status, created_at
    """
    return {"endpoint_url": None, "status": "not_deployed", "created_at": None}


def get_endpoint_metrics(endpoint_url: str, since: str = None) -> Dict:
    """Return placeholder metrics (latency, error_rate, throughput) for an endpoint."""
    return {"latency_ms": None, "error_rate": None, "throughput": None}


def recommend_autoscale_policy(metrics_history: Any, budget: Dict) -> Dict:
    """Return a recommended autoscale policy dict given historic metrics and budget."""
    return {"policy": None}


def tail_logs(endpoint_url: str, last_n: int = 100) -> Dict:
    """Return a small sample of recent logs (placeholder)."""
    return {"logs": []}
