"""
ML Integration Lab - Layout placeholders

This module provides placeholder layout factory functions for the upcoming
ML subtabs. These functions intentionally do NOT import Dash components.

Each subtab layout function returns a plain dict describing the placeholder
content and expected inputs/outputs so Agent 1A or UI devs can wire real
Dash components later.
"""
from typing import Dict


def ml_predictions_layout() -> Dict:
    """Placeholder for ML Predictions subtab.

    Returns a dict describing the UI placeholder and expected contract:
    - inputs: historical_returns: DataFrame (date-indexed), features: DataFrame
    - outputs: predictions: DataFrame (date-indexed), confidence: Series
    """
    return {
        "name": "ML Predictions",
        "description": "Placeholder layout for model predictions and quick controls.",
        "expected_inputs": ["historical_returns", "features"],
        "expected_outputs": ["predictions", "confidence"]
    }


def feature_importance_layout() -> Dict:
    """Placeholder for Feature Importance subtab.

    Expected outputs: table of features and importance scores, SHAP summary plots.
    """
    return {
        "name": "Feature Importance",
        "description": "Placeholder for feature importance and SHAP visuals.",
        "expected_outputs": ["importance_table", "shap_summary"]
    }


def model_metrics_layout() -> Dict:
    """Placeholder for Model Metrics subtab.

    Expected outputs: backtest metrics (Sharpe, CAGR, MaxDD), validation metrics
    (ROC AUC, precision/recall if applicable).
    """
    return {
        "name": "Model Metrics",
        "description": "Placeholder for model evaluation and backtest metrics.",
        "expected_outputs": ["backtest_metrics", "validation_metrics"]
    }


def strategy_recommendations_layout() -> Dict:
    """Placeholder for Strategy Recommendations subtab.

    Expected outputs: recommended weights, suggested rebalancing cadence.
    """
    return {
        "name": "Strategy Recommendations",
        "description": "Placeholder listing recommended portfolio actions.",
        "expected_outputs": ["weights", "rebalancing_plan"]
    }


def user_feedback_layout() -> Dict:
    """Placeholder for User Feedback subtab.

    Expected outputs: feedback forms, usage telemetry (non-PHI).
    """
    return {
        "name": "User Feedback",
        "description": "Placeholder for collecting UX feedback and notes.",
        "expected_outputs": ["feedback_entries"]
    }


def layout() -> Dict:
    """Return a top-level layout description for the ML Integration Lab."""
    return {
        "lab": "ML Integration Lab",
        "subtabs": [
            ml_predictions_layout(),
            feature_importance_layout(),
            model_metrics_layout(),
            strategy_recommendations_layout(),
            user_feedback_layout(),
        ]
    }
