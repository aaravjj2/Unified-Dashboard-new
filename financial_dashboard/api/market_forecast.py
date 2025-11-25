"""
Market Forecast API Blueprint
Flask routes for forecast service
"""

from flask import Blueprint, request, jsonify
import os
import json
import logging
from datetime import datetime
from pathlib import Path

# Import adapter
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from services.forecast_adapter import run_predict, run_explain, validate_forecast_response

logger = logging.getLogger(__name__)

# Create Blueprint
market_forecast_api = Blueprint('market_forecast_api', __name__, url_prefix='/api/market_forecast')

# Configuration
FORECAST_DETERMINISTIC = os.getenv('FORECAST_DETERMINISTIC', '0') == '1'
DATA_DIR = os.path.join(os.path.dirname(__file__), '../data/forecast')
EXPLAIN_DIR = os.path.join(os.path.dirname(__file__), '../explain')

# Ensure directories exist
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
Path(EXPLAIN_DIR).mkdir(parents=True, exist_ok=True)

# In-memory job store (for async mode)
JOBS = {}
NEXT_JOB_ID = 1

def save_forecast_to_file(forecast_id: str, data: dict):
    """Save forecast to JSON file"""
    path = os.path.join(DATA_DIR, f"{forecast_id}.json")
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)
    logger.info(f"[MARKET_FORECAST_API] Saved forecast to {path}")

def save_explain_to_file(forecast_id: str, data: dict):
    """Save explanation to JSON file"""
    explain_path = os.path.join(EXPLAIN_DIR, forecast_id)
    Path(explain_path).mkdir(parents=True, exist_ok=True)
    
    shap_file = os.path.join(explain_path, 'shap.json')
    with open(shap_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    logger.info(f"[MARKET_FORECAST_API] Saved explanation to {shap_file}")
    return shap_file

@market_forecast_api.route('/run', methods=['POST'])
def run_forecast():
    """
    POST /api/market_forecast/run
    
    Payload: {ticker, horizon, confidence, model_version?, mode: "sync"|"async"}
    Returns: {forecast_id, result, explain_path?} or {job_id} for async
    """
    try:
        data = request.json
        ticker = data.get('ticker', '').upper()
        horizon = data.get('horizon', 30)
        confidence = data.get('confidence', 0.95)
        mode = data.get('mode', 'sync')
        model_version = data.get('model_version', 'v1.0.0')
        
        if not ticker:
            return jsonify({'error': 'ticker required'}), 400
        
        # Add deterministic flag
        payload = {
            'ticker': ticker,
            'horizon': horizon,
            'confidence': confidence,
            'model_version': model_version,
            'deterministic': FORECAST_DETERMINISTIC or data.get('deterministic', False)
        }
        
        logger.info(f"[MARKET_FORECAST_API] /run called: {payload}, mode={mode}")
        
        # Async mode: enqueue and return job_id
        if mode == 'async':
            global NEXT_JOB_ID
            job_id = f"job_{NEXT_JOB_ID}"
            NEXT_JOB_ID += 1
            
            JOBS[job_id] = {
                'status': 'pending',
                'payload': payload,
                'created_at': datetime.utcnow().isoformat() + 'Z'
            }
            
            logger.info(f"[MARKET_FORECAST_API] Enqueued async job: {job_id}")
            
            # In real implementation, would dispatch to background worker
            # For now, execute immediately
            result = run_predict(payload)
            forecast_id = f"{ticker}_{int(datetime.utcnow().timestamp())}"
            
            JOBS[job_id].update({
                'status': 'completed',
                'forecast_id': forecast_id,
                'result': result,
                'completed_at': datetime.utcnow().isoformat() + 'Z'
            })
            
            # Save to file
            save_forecast_to_file(forecast_id, {
                'forecast_id': forecast_id,
                'params': payload,
                'result': result,
                'created_at': datetime.utcnow().isoformat() + 'Z'
            })
            
            return jsonify({
                'job_id': job_id,
                'status': 'completed',  # Immediate for mock
                'forecast_id': forecast_id
            }), 200
        
        # Sync mode: run immediately
        result = run_predict(payload)
        
        if not validate_forecast_response(result):
            return jsonify({'error': 'Invalid forecast response schema'}), 500
        
        # Generate forecast ID
        forecast_id = f"{ticker}_{int(datetime.utcnow().timestamp())}"
        
        # Save to file
        forecast_record = {
            'forecast_id': forecast_id,
            'params': payload,
            'result': result,
            'created_at': datetime.utcnow().isoformat() + 'Z'
        }
        save_forecast_to_file(forecast_id, forecast_record)
        
        return jsonify({
            'forecast_id': forecast_id,
            'result': result,
            'saved': True
        }), 200
        
    except Exception as e:
        logger.error(f"[MARKET_FORECAST_API] /run error: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@market_forecast_api.route('/latest', methods=['GET'])
def get_latest():
    """GET /api/market_forecast/latest?ticker=AAPL"""
    try:
        ticker = request.args.get('ticker', '').upper()
        
        if not ticker:
            return jsonify({'error': 'ticker parameter required'}), 400
        
        # Find latest forecast file for ticker
        forecast_files = sorted(Path(DATA_DIR).glob(f"{ticker}_*.json"), reverse=True)
        
        if not forecast_files:
            return jsonify({'error': 'No forecasts found for ticker'}), 404
        
        with open(forecast_files[0], 'r') as f:
            forecast = json.load(f)
        
        return jsonify(forecast), 200
        
    except Exception as e:
        logger.error(f"[MARKET_FORECAST_API] /latest error: {e}")
        return jsonify({'error': str(e)}), 500

@market_forecast_api.route('/history', methods=['GET'])
def get_history():
    """GET /api/market_forecast/history?ticker=AAPL&limit=10"""
    try:
        ticker = request.args.get('ticker', '').upper()
        limit = int(request.args.get('limit', 10))
        
        if ticker:
            forecast_files = sorted(Path(DATA_DIR).glob(f"{ticker}_*.json"), reverse=True)[:limit]
        else:
            forecast_files = sorted(Path(DATA_DIR).glob("*.json"), reverse=True)[:limit]
        
        forecasts = []
        for file in forecast_files:
            with open(file, 'r') as f:
                forecasts.append(json.load(f))
        
        return jsonify({
            'count': len(forecasts),
            'forecasts': forecasts
        }), 200
        
    except Exception as e:
        logger.error(f"[MARKET_FORECAST_API] /history error: {e}")
        return jsonify({'error': str(e)}), 500

@market_forecast_api.route('/explain', methods=['GET'])
def get_explain():
    """GET /api/market_forecast/explain?id=<forecast_id>"""
    try:
        forecast_id = request.args.get('id')
        
        if not forecast_id:
            return jsonify({'error': 'id parameter required'}), 400
        
        explain_file = os.path.join(EXPLAIN_DIR, forecast_id, 'shap.json')
        
        if not os.path.exists(explain_file):
            # Generate explanation on-demand
            # Load forecast to get ticker
            forecast_file = os.path.join(DATA_DIR, f"{forecast_id}.json")
            if not os.path.exists(forecast_file):
                return jsonify({'error': 'Forecast not found'}), 404
            
            with open(forecast_file, 'r') as f:
                forecast_data = json.load(f)
            
            ticker = forecast_data['params']['ticker']
            
            # Generate explanation
            explain_result = run_explain({'ticker': ticker, 'deterministic': FORECAST_DETERMINISTIC})
            
            # Save it
            save_explain_to_file(forecast_id, explain_result)
            
            return jsonify(explain_result), 200
        
        with open(explain_file, 'r') as f:
            explain_data = json.load(f)
        
        return jsonify(explain_data), 200
        
    except Exception as e:
        logger.error(f"[MARKET_FORECAST_API] /explain error: {e}")
        return jsonify({'error': str(e)}), 500

@market_forecast_api.route('/job/<job_id>', methods=['GET'])
def get_job(job_id):
    """GET /api/market_forecast/job/<job_id>"""
    if job_id not in JOBS:
        return jsonify({'error': 'Job not found'}), 404
    
    return jsonify(JOBS[job_id]), 200

# Register with main app in financial_dashboard/__init__.py or app.py
