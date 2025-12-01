"""
Market Forecast API Blueprint - AGENT-1B Phase 2
Local-first, Bento-backed, deterministic-aware forecast API

Endpoints:
- POST /api/market_forecast/run - Execute forecast (sync/async)
- GET /api/market_forecast/latest - Latest forecast result
- GET /api/market_forecast/history - Historical forecast runs
- GET /api/market_forecast/explain/<id> - SHAP explainability data
- GET /api/market_forecast/admin/health - Service health check
"""

import os
import json
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional

from services.forecast_adapter import ForecastAdapter

bp = Blueprint("market_forecast", __name__, url_prefix="/api/market_forecast")

# Initialize adapter (Bento-first, with deterministic support)
adapter = ForecastAdapter(
    bento_url=os.getenv("FORECAST_BENTO_URL", "http://localhost:5001/predict"),
    deterministic=os.getenv("FORECAST_DETERMINISTIC", "0") == "1"
)


@bp.route("/run", methods=["POST"])
def run_forecast():
    """
    Execute market forecast
    
    Request Body:
    {
        "ticker": str,          # e.g., "AAPL"
        "horizon": int,         # 7, 30, or 90 days
        "confidence": float,    # 0.90, 0.95, or 0.99
        "model": str,           # "lstm" | "prophet" | "ensemble"
        "mode": str             # "sync" | "async"
    }
    
    Response (sync):
    {
        "forecast_id": str,
        "ticker": str,
        "forecast": [...],      # Array of {date, yhat, yhat_lower, yhat_upper}
        "metrics": {...},       # {rmse, mae, mape}
        "timestamp": str,
        "status": "completed"
    }
    
    Response (async):
    {
        "forecast_id": str,
        "status": "pending",
        "poll_url": "/api/market_forecast/status/<id>"
    }
    """
    try:
        data = request.get_json()
        
        # Validate inputs
        ticker = data.get("ticker", "").upper()
        horizon = int(data.get("horizon", 30))
        confidence = float(data.get("confidence", 0.95))
        model = data.get("model", "lstm")
        mode = data.get("mode", "sync")
        
        if not ticker:
            return jsonify({"error": "ticker is required"}), 400
        if horizon not in [7, 30, 90]:
            return jsonify({"error": "horizon must be 7, 30, or 90"}), 400
        if confidence not in [0.90, 0.95, 0.99]:
            return jsonify({"error": "confidence must be 0.90, 0.95, or 0.99"}), 400
        if model not in ["lstm", "prophet", "ensemble"]:
            return jsonify({"error": "model must be lstm, prophet, or ensemble"}), 400
        
        # Generate forecast ID
        forecast_id = str(uuid.uuid4())
        
        # Execute forecast
        if mode == "sync":
            result = adapter.run_forecast(
                ticker=ticker,
                horizon=horizon,
                confidence=confidence,
                model=model,
                forecast_id=forecast_id
            )
            return jsonify(result), 200
        else:
            # Async mode - queue forecast task
            result = adapter.queue_forecast(
                ticker=ticker,
                horizon=horizon,
                confidence=confidence,
                model=model,
                forecast_id=forecast_id
            )
            return jsonify(result), 202  # Accepted
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Internal error: {str(e)}"}), 500


@bp.route("/latest", methods=["GET"])
def get_latest_forecast():
    """
    Get the most recent forecast result
    
    Query Parameters:
    - ticker: str (optional) - Filter by ticker
    
    Response: Same as /run (sync mode)
    """
    try:
        ticker = request.args.get("ticker", "").upper()
        result = adapter.get_latest(ticker=ticker if ticker else None)
        
        if not result:
            return jsonify({"error": "No forecasts found"}), 404
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/history", methods=["GET"])
def get_forecast_history():
    """
    Get historical forecast runs
    
    Query Parameters:
    - ticker: str (optional) - Filter by ticker
    - limit: int (default: 20) - Max results
    - offset: int (default: 0) - Pagination offset
    
    Response:
    {
        "forecasts": [...],    # Array of forecast summaries
        "total": int,
        "limit": int,
        "offset": int
    }
    """
    try:
        ticker = request.args.get("ticker", "").upper()
        limit = int(request.args.get("limit", 20))
        offset = int(request.args.get("offset", 0))
        
        result = adapter.get_history(
            ticker=ticker if ticker else None,
            limit=limit,
            offset=offset
        )
        
        return jsonify(result), 200
    
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/explain/<forecast_id>", methods=["GET"])
def get_forecast_explanation(forecast_id: str):
    """
    Get SHAP explainability data for a forecast
    
    Response:
    {
        "forecast_id": str,
        "shap_values": [...],   # Array of {feature, importance}
        "base_value": float,
        "features": {...}       # Feature values used in forecast
    }
    """
    try:
        result = adapter.get_explanation(forecast_id)
        
        if not result:
            return jsonify({"error": f"Explanation not found for {forecast_id}"}), 404
        
        return jsonify(result), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@bp.route("/admin/health", methods=["GET"])
def health_check():
    """
    Service health check
    
    Response:
    {
        "status": "healthy" | "degraded" | "down",
        "bento_available": bool,
        "deterministic_mode": bool,
        "persistence_type": "postgres" | "json",
        "timestamp": str
    }
    """
    try:
        health = adapter.health_check()
        status_code = 200 if health["status"] == "healthy" else 503
        return jsonify(health), status_code
    
    except Exception as e:
        return jsonify({
            "status": "down",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }), 503


# Register blueprint in main app
def init_app(app):
    """Register blueprint with Flask app"""
    app.register_blueprint(bp)
