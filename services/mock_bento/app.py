"""
Mock Bento Forecast Service - AGENT-1B Phase 3
Standalone Flask service simulating BentoML forecast endpoint

Run with: python services/mock_bento/app.py
Endpoint: POST http://localhost:5001/predict
Health: GET http://localhost:5001/health
"""

import json
import logging
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from pathlib import Path

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load fixture data
FIXTURE_PATH = Path(__file__).parent.parent.parent / "tests/fixtures/forecast/forecast_fixture.json"


@app.route("/predict", methods=["POST"])
def predict():
    """
    Forecast prediction endpoint
    
    Request:
    {
        "ticker": str,
        "horizon": int,     # 7, 30, or 90
        "confidence": float, # 0.90, 0.95, or 0.99
        "model": str        # "lstm" | "prophet" | "ensemble"
    }
    
    Response:
    {
        "ticker": str,
        "forecast": [...],   # Array of {date, yhat, yhat_lower, yhat_upper}
        "metrics": {...},    # {rmse, mae, mape}
        "model": str,
        "horizon": int,
        "confidence": float
    }
    """
    try:
        data = request.get_json()
        ticker = data.get("ticker", "AAPL")
        horizon = int(data.get("horizon", 30))
        confidence = float(data.get("confidence", 0.95))
        model = data.get("model", "lstm")
        
        # Load base fixture
        if FIXTURE_PATH.exists():
            with open(FIXTURE_PATH) as f:
                base_result = json.load(f)
        else:
            # Fallback: generate synthetic forecast
            base_result = _generate_synthetic_forecast(ticker, horizon, confidence, model)
        
        # Override with request params
        base_result["ticker"] = ticker
        base_result["horizon"] = horizon
        base_result["confidence"] = confidence
        base_result["model"] = model
        
        # Adjust forecast length to match horizon
        if "forecast" in base_result:
            base_result["forecast"] = base_result["forecast"][:horizon]
        
        logger.info(f"Prediction for {ticker} (horizon={horizon}, model={model})")
        return jsonify(base_result), 200
    
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "mock_bento_forecast",
        "timestamp": datetime.utcnow().isoformat()
    }), 200


def _generate_synthetic_forecast(ticker: str, horizon: int, confidence: float, model: str) -> dict:
    """
    Generate synthetic forecast data (fallback when fixture missing)
    
    Creates simple linear trend with confidence intervals
    """
    start_date = datetime.utcnow()
    base_price = 150.0  # Starting price
    daily_growth = 0.002  # 0.2% daily growth
    
    # Confidence interval width (wider for higher horizons)
    ci_multiplier = {0.90: 1.645, 0.95: 1.96, 0.99: 2.576}[confidence]
    std_dev = base_price * 0.02 * (horizon / 30)  # 2% std per 30 days
    
    forecast = []
    for i in range(horizon):
        date = (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        yhat = base_price * (1 + daily_growth) ** i
        margin = ci_multiplier * std_dev
        
        forecast.append({
            "date": date,
            "yhat": round(yhat, 2),
            "yhat_lower": round(yhat - margin, 2),
            "yhat_upper": round(yhat + margin, 2)
        })
    
    return {
        "ticker": ticker,
        "forecast": forecast,
        "metrics": {
            "rmse": 2.5,
            "mae": 1.8,
            "mape": 0.012
        },
        "model": model,
        "horizon": horizon,
        "confidence": confidence
    }


if __name__ == "__main__":
    logger.info("Starting Mock Bento Forecast Service on http://localhost:5001")
    logger.info(f"Fixture path: {FIXTURE_PATH}")
    logger.info(f"Fixture exists: {FIXTURE_PATH.exists()}")
    
    app.run(host="0.0.0.0", port=5001, debug=True)
