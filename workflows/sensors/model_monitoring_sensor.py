"""
Model Monitoring Sensor for Dagster

Daily sensor that checks model performance drift and data quality.
Flags alerts if accuracy drops >5% or data drift exceeds threshold.
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional

import numpy as np
from scipy import stats

logger = logging.getLogger(__name__)

MONITOR_LOG_DIR = Path(__file__).parent.parent.parent / "logs" / "model_monitoring"
ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "artifacts"

# Import registry manager
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from ml.model_registry import get_latest_model


def calculate_ks_statistic(
    reference_data: np.ndarray, 
    current_data: np.ndarray
) -> float:
    """
    Calculate Kolmogorov-Smirnov statistic for data drift detection.
    
    Args:
        reference_data: Historical reference distribution
        current_data: Current data distribution
    
    Returns:
        KS statistic (0 = no drift, 1 = complete drift)
    """
    if len(reference_data) == 0 or len(current_data) == 0:
        return 0.0
    
    ks_stat, _ = stats.ks_2samp(reference_data, current_data)
    return float(ks_stat)


def check_model_performance_drift(
    model_name: str,
    current_predictions: List[Dict[str, Any]],
    accuracy_threshold: float = 0.05,
    ks_threshold: float = 0.1
) -> Dict[str, Any]:
    """
    Check if model performance has drifted from baseline.
    
    Args:
        model_name: Name of model to monitor
        current_predictions: List of recent predictions with ground truth
        accuracy_threshold: Max acceptable accuracy drop (default 5%)
        ks_threshold: Max acceptable KS statistic for data drift (default 0.1)
    
    Returns:
        Dictionary with drift detection results
    """
    # Get latest registered model
    latest_model = get_latest_model(model_name)
    
    if latest_model is None:
        logger.warning(f"No registered model found for {model_name}")
        return {
            'status': 'error',
            'message': f'No model found: {model_name}',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    baseline_metrics = latest_model.get('metrics', {})
    baseline_accuracy = baseline_metrics.get('accuracy', 0.0)
    
    # Calculate current accuracy from predictions
    if len(current_predictions) == 0:
        logger.warning("No current predictions provided")
        return {
            'status': 'warning',
            'message': 'No predictions to evaluate',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
    
    # Extract predictions and ground truth
    y_pred = np.array([p.get('prediction', 0) for p in current_predictions])
    y_true = np.array([p.get('ground_truth', 0) for p in current_predictions])
    
    # Calculate current accuracy
    current_accuracy = float(np.mean(y_pred == y_true))
    
    # Check accuracy drift
    accuracy_drop = baseline_accuracy - current_accuracy
    accuracy_alert = accuracy_drop > accuracy_threshold
    
    # Extract feature distributions for drift detection
    # Assume predictions include feature values
    reference_features = baseline_metrics.get('feature_importance', {})
    
    # Calculate KS statistic for each feature (if available)
    drift_stats = {}
    max_ks_stat = 0.0
    
    if 'features' in current_predictions[0]:
        # Compare distributions
        for feature_name in reference_features.keys():
            current_feature_values = np.array([
                p.get('features', {}).get(feature_name, 0) 
                for p in current_predictions
            ])
            
            # Use a synthetic reference (in production, load from historical data)
            reference_values = np.random.normal(0, 1, len(current_feature_values))
            
            ks_stat = calculate_ks_statistic(reference_values, current_feature_values)
            drift_stats[feature_name] = ks_stat
            max_ks_stat = max(max_ks_stat, ks_stat)
    
    # Check data drift
    drift_alert = max_ks_stat > ks_threshold
    
    # Build result
    result = {
        'model_name': model_name,
        'model_version': latest_model.get('version', 'unknown'),
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'baseline_accuracy': baseline_accuracy,
        'current_accuracy': current_accuracy,
        'accuracy_drop': accuracy_drop,
        'accuracy_alert': accuracy_alert,
        'max_ks_statistic': max_ks_stat,
        'drift_alert': drift_alert,
        'drift_stats': drift_stats,
        'num_predictions': len(current_predictions),
        'status': 'alert' if (accuracy_alert or drift_alert) else 'healthy'
    }
    
    return result


def log_monitoring_result(result: Dict[str, Any]) -> None:
    """
    Write monitoring result to log file.
    
    Args:
        result: Monitoring result dictionary
    """
    MONITOR_LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # Create daily log file
    date_str = datetime.utcnow().strftime('%Y%m%d')
    log_file = MONITOR_LOG_DIR / f"model_monitor_{date_str}.log"
    
    # Format log entry
    log_entry = (
        f"{result['timestamp']} | "
        f"Model: {result['model_name']} | "
        f"Accuracy: {result['current_accuracy']:.4f} "
        f"(baseline: {result['baseline_accuracy']:.4f}, "
        f"drop: {result['accuracy_drop']:.4f}) | "
        f"Drift: {result['max_ks_statistic']:.4f} | "
        f"Status: {result['status']}\n"
    )
    
    with open(log_file, 'a') as f:
        f.write(log_entry)
    
    logger.info(f"Monitoring result logged to {log_file}")


def monitor_model_performance(
    model_name: str = "market_trend_rf",
    prediction_window_days: int = 1
) -> Dict[str, Any]:
    """
    Main monitoring function - checks model performance and logs results.
    
    Args:
        model_name: Name of model to monitor
        prediction_window_days: Number of days of predictions to evaluate
    
    Returns:
        Monitoring result dictionary
    """
    logger.info(f"Starting model monitoring for {model_name}...")
    
    # In production, load recent predictions from database or cache
    # For now, use synthetic data for testing
    current_predictions = generate_synthetic_predictions(num_samples=100)
    
    # Check for drift
    result = check_model_performance_drift(
        model_name=model_name,
        current_predictions=current_predictions,
        accuracy_threshold=0.05,
        ks_threshold=0.1
    )
    
    # Log result
    log_monitoring_result(result)
    
    # Alert if necessary
    if result['status'] == 'alert':
        logger.warning(
            f"⚠️ Model performance alert for {model_name}: "
            f"accuracy drop={result['accuracy_drop']:.4f}, "
            f"drift={result['max_ks_statistic']:.4f}"
        )
    else:
        logger.info(f"✅ Model {model_name} performance is healthy")
    
    return result


def generate_synthetic_predictions(num_samples: int = 100) -> List[Dict[str, Any]]:
    """
    Generate synthetic predictions for testing.
    In production, replace with actual predictions from model inference.
    
    Args:
        num_samples: Number of synthetic predictions
    
    Returns:
        List of prediction dictionaries
    """
    np.random.seed(42)
    
    predictions = []
    for i in range(num_samples):
        prediction = np.random.choice([0, 1], p=[0.4, 0.6])
        ground_truth = np.random.choice([0, 1], p=[0.35, 0.65])
        
        predictions.append({
            'prediction': int(prediction),
            'ground_truth': int(ground_truth),
            'confidence': float(np.random.uniform(0.6, 0.95)),
            'features': {
                'price_momentum': float(np.random.normal(0, 0.1)),
                'price_change_pct': float(np.random.normal(0, 2)),
                'volume_change': float(np.random.normal(0, 0.3)),
                'volatility': float(np.random.uniform(0, 0.05)),
                'sentiment': float(np.random.uniform(0.4, 0.6))
            },
            'timestamp': (datetime.utcnow() - timedelta(hours=i)).isoformat() + 'Z'
        })
    
    return predictions


# Dagster sensor definition (to be imported in workflows)
def create_monitoring_sensor():
    """
    Create Dagster sensor for daily model monitoring.
    This function should be called in Dagster definitions.
    """
    try:
        from dagster import sensor, RunRequest, SkipReason
        
        @sensor(name="model_performance_monitor", minimum_interval_seconds=86400)
        def model_monitoring_sensor(context):
            """
            Daily sensor that monitors model performance.
            Triggers if drift detected.
            """
            result = monitor_model_performance()
            
            if result['status'] == 'alert':
                yield RunRequest(
                    run_key=f"monitor_{result['timestamp']}",
                    run_config={
                        "ops": {
                            "alert_model_drift": {
                                "config": {
                                    "model_name": result['model_name'],
                                    "accuracy_drop": result['accuracy_drop'],
                                    "drift": result['max_ks_statistic']
                                }
                            }
                        }
                    }
                )
            else:
                yield SkipReason(f"Model {result['model_name']} is healthy")
        
        return model_monitoring_sensor
    except ImportError:
        logger.warning("Dagster not available, sensor not created")
        return None
