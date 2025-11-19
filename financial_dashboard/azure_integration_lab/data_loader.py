"""
Azure Integration Lab - Data access stubs

Provides non-networking stubs that describe inputs/outputs for Azure workflows
such as model artifact locations, container images, and telemetry storage paths.
"""
from typing import Optional, Dict


def model_artifact_location(model_name: str) -> Dict:
    """Return a placeholder location descriptor for a model artifact.

    Example return: {"storage_uri": "https://<storage>.blob.core.windows.net/models/<id>"}
    """
    return {"storage_uri": None}


def telemetry_storage_info(workspace: str) -> Dict:
    """Return placeholder info for logging/metrics storage for a workspace."""
    return {"app_insights_key": None, "storage_account": None}


def list_compute_targets(workspace: str) -> Dict:
    """Return placeholder list of compute targets (AKS, ACI, KV)."""
    return {"compute_targets": []}
