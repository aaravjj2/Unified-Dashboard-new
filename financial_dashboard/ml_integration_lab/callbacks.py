"""
ML Integration Lab - Callback stubs

This module contains callback function stubs (pure Python functions with
docstrings) that describe the expected inputs and outputs for each subtab.

IMPORTANT: These are NOT Dash callbacks and do not register with the app.
They exist to document the contract and to be swapped in later by Agent 1A.
"""
from typing import Any, Dict


def predict_models(historical_df: Any, features_df: Any, model_spec: Dict) -> Dict:
    """Generate predictions given historical returns and feature matrix.

    Args:
        historical_df: DataFrame-like, date indexed price/return history.
        features_df: DataFrame-like, features aligned to dates/tickers.
        model_spec: dict with model identifier, hyperparameters.

    Returns:
        dict with keys:
            - predictions: DataFrame-like
            - confidence: Series-like
            - metadata: dict

    Note: Implementation should be side-effect free and return serializable types.
    """
    return {"predictions": None, "confidence": None, "metadata": {}}


def compute_feature_importance(model_spec: Dict, features_df: Any) -> Dict:
    """Return feature importance summary for the provided model.

    Returns:
        dict with keys: importance_table (list/dict), shap_summary (path or dict)
    """
    return {"importance_table": [], "shap_summary": None}


def evaluate_model_metrics(predictions: Any, labels: Any) -> Dict:
    """Compute model metrics (CAGR, Sharpe, AUC etc.).

    Returns dict of metric name -> value
    """
    return {"cagr": None, "sharpe": None, "max_dd": None}


def recommend_strategy(predictions: Any, constraints: Dict) -> Dict:
    """Generate portfolio recommendations from predictions.

    Returns a dict with recommended weights and metadata.
    """
    return {"weights": None, "plan": None}


def collect_user_feedback(feedback_payload: Dict) -> Dict:
    """Persist or format user feedback payload for later ingestion.

    For now, returns an acknowledgment dict.
    """
    return {"status": "ok", "received": feedback_payload}
