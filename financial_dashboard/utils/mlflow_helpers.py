"""
MLflow helper utilities for experiment tracking and initialization.

This module provides functions to initialize MLflow tracking infrastructure,
ensuring the correct tracking server URI and experiment names are set before
any logging operations occur.
"""

import os
import mlflow


def initialize_mlflow_experiment(experiment_name: str) -> None:
    """
    Initialize MLflow tracking with the appropriate tracking URI and experiment.
    
    This function reads the MLFLOW_TRACKING_URI from the environment, sets it
    for the MLflow client, and creates/selects the specified experiment. This
    ensures all subsequent MLflow logging operations are directed to the correct
    tracking server and experiment context.
    
    Args:
        experiment_name: The name of the MLflow experiment to create or select.
                        Example: "Strategy Validation", "Model Training", etc.
    
    Raises:
        ValueError: If MLFLOW_TRACKING_URI is not set in the environment.
        
    Example:
        >>> initialize_mlflow_experiment("Strategy Validation")
        >>> # Now all mlflow.log_* calls will use the correct tracking server
        >>> with mlflow.start_run():
        ...     mlflow.log_param("strategy", "covered_call")
        ...     mlflow.log_metric("sharpe_ratio", 1.5)
    
    Notes:
        - Must be called before any MLflow logging operations
        - Safe to call multiple times with the same experiment_name
        - Creates the experiment if it doesn't exist, or selects it if it does
    """
    # Retrieve the MLflow tracking server URI from environment
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    
    if not tracking_uri:
        raise ValueError(
            "MLFLOW_TRACKING_URI environment variable is not set. "
            "Please set it to your MLflow tracking server URL (e.g., http://mlflow:5000)"
        )
    
    # Set the tracking URI for the MLflow client
    mlflow.set_tracking_uri(tracking_uri)
    
    # Create or select the specified experiment
    # This will create the experiment if it doesn't exist, or retrieve it if it does
    mlflow.set_experiment(experiment_name)
    
    print(f"✅ MLflow initialized:")
    print(f"   Tracking URI: {tracking_uri}")
    print(f"   Experiment: {experiment_name}")
