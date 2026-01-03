"""
MLflow Experiment Tracking & Model Registry.

This module provides comprehensive ML experiment tracking:
- Automatic metric/param logging
- Model versioning and staging
- Artifact storage
- Model comparison and selection
- Production deployment helpers

Based on ROADMAP_ULTIMATE.md Part 2: Triton & Infrastructure
"""

from __future__ import annotations

import json
import logging
import os
import pickle
import shutil
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ==================== CONDITIONAL IMPORTS ====================

try:
    import mlflow
    import mlflow.pytorch
    import mlflow.sklearn
    MLFLOW_AVAILABLE = True
except ImportError:
    mlflow = None
    MLFLOW_AVAILABLE = False
    logger.info("MLflow not installed - using local tracking fallback")

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False


# ==================== DATA CLASSES ====================

@dataclass
class ExperimentRun:
    """Represents a single experiment run."""
    run_id: str
    experiment_name: str
    run_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: str = "RUNNING"
    params: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, List[float]] = field(default_factory=dict)
    artifacts: List[str] = field(default_factory=list)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class ModelVersion:
    """Model version information."""
    name: str
    version: int
    stage: str  # "None", "Staging", "Production", "Archived"
    run_id: str
    created_at: datetime
    metrics: Dict[str, float] = field(default_factory=dict)
    description: str = ""


@dataclass
class ExperimentSummary:
    """Summary of experiment runs."""
    experiment_name: str
    total_runs: int
    best_run_id: str
    best_metric: float
    metric_name: str
    recent_runs: List[ExperimentRun] = field(default_factory=list)


# ==================== LOCAL TRACKING FALLBACK ====================

class LocalTracker:
    """
    Local file-based experiment tracking when MLflow unavailable.
    
    Stores metrics/params in JSON files for later analysis.
    """
    
    def __init__(self, base_dir: str = "./mlruns_local"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.current_run: Optional[ExperimentRun] = None
    
    def start_run(
        self,
        experiment_name: str,
        run_name: str,
        tags: Dict[str, str] = None
    ) -> ExperimentRun:
        """Start a new tracking run."""
        run_id = f"{int(time.time())}_{run_name.replace(' ', '_')}"
        
        run = ExperimentRun(
            run_id=run_id,
            experiment_name=experiment_name,
            run_name=run_name,
            start_time=datetime.now(),
            tags=tags or {}
        )
        
        self.current_run = run
        
        # Create run directory
        run_dir = self.base_dir / experiment_name / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Started local run: {run_id}")
        return run
    
    def log_param(self, key: str, value: Any) -> None:
        """Log a parameter."""
        if self.current_run:
            self.current_run.params[key] = value
    
    def log_params(self, params: Dict[str, Any]) -> None:
        """Log multiple parameters."""
        if self.current_run:
            self.current_run.params.update(params)
    
    def log_metric(self, key: str, value: float, step: int = None) -> None:
        """Log a metric."""
        if self.current_run:
            if key not in self.current_run.metrics:
                self.current_run.metrics[key] = []
            self.current_run.metrics[key].append(value)
    
    def log_metrics(self, metrics: Dict[str, float], step: int = None) -> None:
        """Log multiple metrics."""
        for key, value in metrics.items():
            self.log_metric(key, value, step)
    
    def log_artifact(self, local_path: str, artifact_path: str = None) -> None:
        """Log an artifact (copy file)."""
        if not self.current_run:
            return
        
        src = Path(local_path)
        if not src.exists():
            logger.warning(f"Artifact not found: {local_path}")
            return
        
        run_dir = self.base_dir / self.current_run.experiment_name / self.current_run.run_id
        artifacts_dir = run_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        dest = artifacts_dir / (artifact_path or src.name)
        if src.is_file():
            shutil.copy2(src, dest)
        else:
            shutil.copytree(src, dest, dirs_exist_ok=True)
        
        self.current_run.artifacts.append(str(dest))
    
    def log_model(self, model: Any, artifact_path: str) -> None:
        """Log a model artifact."""
        if not self.current_run:
            return
        
        run_dir = self.base_dir / self.current_run.experiment_name / self.current_run.run_id
        model_dir = run_dir / "models" / artifact_path
        model_dir.mkdir(parents=True, exist_ok=True)
        
        model_path = model_dir / "model.pkl"
        with open(model_path, "wb") as f:
            pickle.dump(model, f)
        
        self.current_run.artifacts.append(str(model_path))
        logger.info(f"Model saved to {model_path}")
    
    def end_run(self, status: str = "FINISHED") -> None:
        """End the current run and save metadata."""
        if not self.current_run:
            return
        
        self.current_run.end_time = datetime.now()
        self.current_run.status = status
        
        # Save run metadata
        run_dir = self.base_dir / self.current_run.experiment_name / self.current_run.run_id
        meta_path = run_dir / "run_metadata.json"
        
        metadata = {
            "run_id": self.current_run.run_id,
            "experiment_name": self.current_run.experiment_name,
            "run_name": self.current_run.run_name,
            "start_time": self.current_run.start_time.isoformat(),
            "end_time": self.current_run.end_time.isoformat(),
            "status": self.current_run.status,
            "params": self.current_run.params,
            "metrics": {k: v[-1] if v else None for k, v in self.current_run.metrics.items()},
            "metrics_history": self.current_run.metrics,
            "artifacts": self.current_run.artifacts,
            "tags": self.current_run.tags
        }
        
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
        
        logger.info(f"Run ended: {self.current_run.run_id}")
        self.current_run = None
    
    def list_runs(self, experiment_name: str) -> List[Dict]:
        """List all runs for an experiment."""
        exp_dir = self.base_dir / experiment_name
        if not exp_dir.exists():
            return []
        
        runs = []
        for run_dir in exp_dir.iterdir():
            if run_dir.is_dir():
                meta_path = run_dir / "run_metadata.json"
                if meta_path.exists():
                    with open(meta_path) as f:
                        runs.append(json.load(f))
        
        return sorted(runs, key=lambda x: x.get("start_time", ""), reverse=True)


# ==================== MLFLOW TRACKER ====================

class MLflowExperimentTracker:
    """
    MLflow-based experiment tracking with local fallback.
    
    Features:
    - Automatic metric/param logging
    - Model versioning
    - Artifact storage
    - Model registry integration
    - Local fallback when MLflow unavailable
    
    Example:
        tracker = MLflowExperimentTracker(experiment_name="forecasting")
        
        with tracker.start_run("lstm_v1"):
            tracker.log_params({"learning_rate": 0.001, "epochs": 100})
            
            for epoch in range(100):
                loss = train_epoch()
                tracker.log_metric("loss", loss, step=epoch)
            
            tracker.log_model(model, "lstm_model")
    """
    
    def __init__(
        self,
        tracking_uri: str = None,
        experiment_name: str = "unified-dashboard-forecasting",
        artifact_location: str = None
    ):
        self.experiment_name = experiment_name
        self.tracking_uri = tracking_uri or os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
        self.artifact_location = artifact_location
        
        self._mlflow_available = MLFLOW_AVAILABLE
        self._local_tracker = LocalTracker()
        self._current_run = None
        
        if self._mlflow_available:
            try:
                mlflow.set_tracking_uri(self.tracking_uri)
                mlflow.set_experiment(experiment_name)
                logger.info(f"MLflow tracking enabled: {self.tracking_uri}")
            except Exception as e:
                logger.warning(f"MLflow setup failed, using local tracking: {e}")
                self._mlflow_available = False
    
    @contextmanager
    def start_run(
        self,
        run_name: str = None,
        tags: Dict[str, str] = None,
        nested: bool = False
    ):
        """
        Context manager for experiment runs.
        
        Example:
            with tracker.start_run("experiment_v1"):
                tracker.log_params(...)
                tracker.log_metrics(...)
        """
        run_name = run_name or f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        try:
            if self._mlflow_available:
                self._current_run = mlflow.start_run(run_name=run_name, tags=tags, nested=nested)
            else:
                self._current_run = self._local_tracker.start_run(
                    self.experiment_name, run_name, tags
                )
            
            yield self._current_run
            
        except Exception as e:
            logger.error(f"Error during run: {e}")
            self.end_run(status="FAILED")
            raise
        
        finally:
            self.end_run()
    
    def log_param(self, key: str, value: Any) -> None:
        """Log a single parameter."""
        if self._mlflow_available:
            mlflow.log_param(key, value)
        else:
            self._local_tracker.log_param(key, value)
    
    def log_params(self, params: Dict[str, Any]) -> None:
        """Log multiple parameters."""
        if self._mlflow_available:
            mlflow.log_params(params)
        else:
            self._local_tracker.log_params(params)
    
    def log_metric(self, key: str, value: float, step: int = None) -> None:
        """Log a single metric."""
        if self._mlflow_available:
            mlflow.log_metric(key, value, step=step)
        else:
            self._local_tracker.log_metric(key, value, step)
    
    def log_metrics(self, metrics: Dict[str, float], step: int = None) -> None:
        """Log multiple metrics."""
        if self._mlflow_available:
            mlflow.log_metrics(metrics, step=step)
        else:
            self._local_tracker.log_metrics(metrics, step)
    
    def log_artifact(self, local_path: str, artifact_path: str = None) -> None:
        """Log an artifact file or directory."""
        if self._mlflow_available:
            mlflow.log_artifact(local_path, artifact_path)
        else:
            self._local_tracker.log_artifact(local_path, artifact_path)
    
    def log_model(
        self,
        model: Any,
        artifact_path: str,
        registered_model_name: str = None,
        signature = None,
        input_example = None
    ) -> None:
        """
        Log a model to the tracking server.
        
        Args:
            model: Model object (PyTorch, sklearn, etc.)
            artifact_path: Path within run artifacts
            registered_model_name: Name for model registry
            signature: Model signature for input/output schema
            input_example: Example input for documentation
        """
        if self._mlflow_available:
            # Detect model type and use appropriate logger
            if TORCH_AVAILABLE and isinstance(model, torch.nn.Module):
                mlflow.pytorch.log_model(
                    model,
                    artifact_path,
                    registered_model_name=registered_model_name,
                    signature=signature,
                    input_example=input_example
                )
            elif hasattr(model, 'fit') and hasattr(model, 'predict'):
                # sklearn-like model
                mlflow.sklearn.log_model(
                    model,
                    artifact_path,
                    registered_model_name=registered_model_name,
                    signature=signature,
                    input_example=input_example
                )
            else:
                # Generic pickle
                mlflow.log_artifact(artifact_path)
        else:
            self._local_tracker.log_model(model, artifact_path)
    
    def log_figure(self, figure, artifact_file: str) -> None:
        """Log a matplotlib figure."""
        if self._mlflow_available:
            mlflow.log_figure(figure, artifact_file)
        else:
            # Save figure to temp file and log
            import tempfile
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                figure.savefig(f.name)
                self._local_tracker.log_artifact(f.name, artifact_file)
    
    def set_tag(self, key: str, value: str) -> None:
        """Set a tag on the current run."""
        if self._mlflow_available:
            mlflow.set_tag(key, value)
    
    def end_run(self, status: str = "FINISHED") -> None:
        """End the current run."""
        if self._mlflow_available and mlflow.active_run():
            mlflow.end_run(status)
        elif not self._mlflow_available:
            self._local_tracker.end_run(status)
        self._current_run = None
    
    def get_run(self, run_id: str) -> Optional[Dict]:
        """Get run information by ID."""
        if self._mlflow_available:
            try:
                run = mlflow.get_run(run_id)
                return {
                    "run_id": run.info.run_id,
                    "status": run.info.status,
                    "start_time": run.info.start_time,
                    "end_time": run.info.end_time,
                    "params": run.data.params,
                    "metrics": run.data.metrics,
                    "tags": run.data.tags
                }
            except:
                return None
        return None
    
    def search_runs(
        self,
        filter_string: str = "",
        order_by: List[str] = None,
        max_results: int = 100
    ) -> pd.DataFrame:
        """Search runs with filters."""
        if self._mlflow_available:
            try:
                return mlflow.search_runs(
                    filter_string=filter_string,
                    order_by=order_by or ["metrics.loss ASC"],
                    max_results=max_results
                )
            except:
                pass
        
        # Fallback to local
        runs = self._local_tracker.list_runs(self.experiment_name)
        return pd.DataFrame(runs)
    
    def get_best_run(
        self,
        metric: str = "loss",
        ascending: bool = True
    ) -> Optional[Dict]:
        """Get the best run based on a metric."""
        runs_df = self.search_runs(
            order_by=[f"metrics.{metric} {'ASC' if ascending else 'DESC'}"],
            max_results=1
        )
        
        if len(runs_df) > 0:
            return runs_df.iloc[0].to_dict()
        return None


# ==================== MODEL REGISTRY ====================

class ModelRegistry:
    """
    Model registry for versioning and staging.
    
    Manages model versions and deployment stages:
    - None: Just registered
    - Staging: Being tested
    - Production: Live in production
    - Archived: Deprecated
    """
    
    def __init__(self, tracker: MLflowExperimentTracker):
        self.tracker = tracker
        self._local_registry: Dict[str, List[ModelVersion]] = {}
        self._registry_path = Path("./model_registry")
        self._registry_path.mkdir(parents=True, exist_ok=True)
    
    def register_model(
        self,
        model_uri: str,
        name: str,
        description: str = ""
    ) -> ModelVersion:
        """
        Register a model from a run.
        
        Args:
            model_uri: URI to logged model (e.g., "runs:/run_id/model")
            name: Registered model name
            description: Model description
        
        Returns:
            ModelVersion object
        """
        if MLFLOW_AVAILABLE and self.tracker._mlflow_available:
            try:
                result = mlflow.register_model(model_uri, name)
                return ModelVersion(
                    name=name,
                    version=int(result.version),
                    stage="None",
                    run_id=result.run_id,
                    created_at=datetime.now(),
                    description=description
                )
            except Exception as e:
                logger.warning(f"MLflow registration failed: {e}")
        
        # Local fallback
        if name not in self._local_registry:
            self._local_registry[name] = []
        
        version = len(self._local_registry[name]) + 1
        model_version = ModelVersion(
            name=name,
            version=version,
            stage="None",
            run_id=model_uri,
            created_at=datetime.now(),
            description=description
        )
        self._local_registry[name].append(model_version)
        self._save_local_registry()
        
        return model_version
    
    def transition_model_stage(
        self,
        name: str,
        version: int,
        stage: str
    ) -> ModelVersion:
        """
        Transition a model version to a new stage.
        
        Args:
            name: Model name
            version: Version number
            stage: Target stage ("Staging", "Production", "Archived")
        """
        if MLFLOW_AVAILABLE and self.tracker._mlflow_available:
            try:
                from mlflow.tracking import MlflowClient
                client = MlflowClient()
                client.transition_model_version_stage(
                    name=name,
                    version=str(version),
                    stage=stage
                )
                # Get updated version
                mv = client.get_model_version(name, str(version))
                return ModelVersion(
                    name=mv.name,
                    version=int(mv.version),
                    stage=mv.current_stage,
                    run_id=mv.run_id,
                    created_at=datetime.fromisoformat(mv.creation_timestamp.isoformat()) if hasattr(mv.creation_timestamp, 'isoformat') else datetime.now()
                )
            except Exception as e:
                logger.warning(f"MLflow stage transition failed: {e}")
        
        # Local fallback
        if name in self._local_registry:
            for mv in self._local_registry[name]:
                if mv.version == version:
                    mv.stage = stage
                    self._save_local_registry()
                    return mv
        
        raise ValueError(f"Model {name} version {version} not found")
    
    def get_latest_version(
        self,
        name: str,
        stage: str = None
    ) -> Optional[ModelVersion]:
        """Get latest version of a model, optionally filtered by stage."""
        if MLFLOW_AVAILABLE and self.tracker._mlflow_available:
            try:
                from mlflow.tracking import MlflowClient
                client = MlflowClient()
                
                if stage:
                    versions = client.get_latest_versions(name, stages=[stage])
                else:
                    versions = client.get_latest_versions(name)
                
                if versions:
                    mv = versions[0]
                    return ModelVersion(
                        name=mv.name,
                        version=int(mv.version),
                        stage=mv.current_stage,
                        run_id=mv.run_id,
                        created_at=datetime.now()
                    )
            except Exception as e:
                logger.debug(f"MLflow get version failed: {e}")
        
        # Local fallback
        if name in self._local_registry:
            versions = self._local_registry[name]
            if stage:
                versions = [v for v in versions if v.stage == stage]
            if versions:
                return max(versions, key=lambda v: v.version)
        
        return None
    
    def load_model(
        self,
        name: str,
        version: int = None,
        stage: str = None
    ) -> Any:
        """
        Load a model from the registry.
        
        Args:
            name: Model name
            version: Specific version (or None for latest)
            stage: Stage filter (or None for any)
        """
        if MLFLOW_AVAILABLE and self.tracker._mlflow_available:
            try:
                if version:
                    model_uri = f"models:/{name}/{version}"
                elif stage:
                    model_uri = f"models:/{name}/{stage}"
                else:
                    model_uri = f"models:/{name}/latest"
                
                return mlflow.pyfunc.load_model(model_uri)
            except Exception as e:
                logger.warning(f"MLflow model load failed: {e}")
        
        # Local fallback - not implemented for simplicity
        logger.warning("Local model loading not implemented")
        return None
    
    def list_models(self) -> List[str]:
        """List all registered model names."""
        if MLFLOW_AVAILABLE and self.tracker._mlflow_available:
            try:
                from mlflow.tracking import MlflowClient
                client = MlflowClient()
                return [m.name for m in client.search_registered_models()]
            except:
                pass
        
        return list(self._local_registry.keys())
    
    def _save_local_registry(self) -> None:
        """Save local registry to disk."""
        registry_file = self._registry_path / "registry.json"
        
        data = {}
        for name, versions in self._local_registry.items():
            data[name] = [
                {
                    "name": v.name,
                    "version": v.version,
                    "stage": v.stage,
                    "run_id": v.run_id,
                    "created_at": v.created_at.isoformat(),
                    "description": v.description
                }
                for v in versions
            ]
        
        with open(registry_file, "w") as f:
            json.dump(data, f, indent=2)
    
    def _load_local_registry(self) -> None:
        """Load local registry from disk."""
        registry_file = self._registry_path / "registry.json"
        
        if registry_file.exists():
            with open(registry_file) as f:
                data = json.load(f)
            
            for name, versions in data.items():
                self._local_registry[name] = [
                    ModelVersion(
                        name=v["name"],
                        version=v["version"],
                        stage=v["stage"],
                        run_id=v["run_id"],
                        created_at=datetime.fromisoformat(v["created_at"]),
                        description=v.get("description", "")
                    )
                    for v in versions
                ]


# ==================== TRAINING CALLBACKS ====================

class TrainingCallback:
    """Callback for automatic logging during training."""
    
    def __init__(self, tracker: MLflowExperimentTracker):
        self.tracker = tracker
    
    def on_epoch_end(
        self,
        epoch: int,
        logs: Dict[str, float]
    ) -> None:
        """Called at the end of each epoch."""
        self.tracker.log_metrics(logs, step=epoch)
    
    def on_train_end(
        self,
        model: Any,
        final_metrics: Dict[str, float]
    ) -> None:
        """Called at the end of training."""
        self.tracker.log_metrics(final_metrics)


# ==================== CONVENIENCE FUNCTIONS ====================

def create_tracker(
    experiment_name: str = "unified-dashboard",
    tracking_uri: str = None
) -> MLflowExperimentTracker:
    """Create and configure an experiment tracker."""
    return MLflowExperimentTracker(
        experiment_name=experiment_name,
        tracking_uri=tracking_uri
    )


def get_mlflow_availability() -> Dict[str, bool]:
    """Check MLflow availability."""
    return {
        "mlflow_available": MLFLOW_AVAILABLE,
        "torch_available": TORCH_AVAILABLE
    }


# ==================== MODULE EXPORTS ====================

__all__ = [
    "MLflowExperimentTracker",
    "ModelRegistry",
    "TrainingCallback",
    "LocalTracker",
    "ExperimentRun",
    "ModelVersion",
    "ExperimentSummary",
    "create_tracker",
    "get_mlflow_availability",
    "MLFLOW_AVAILABLE"
]
