"""
Options Forecast API Blueprint
Flask routes for options forecast service with deterministic fixture support.

Phase 31 Agent 1A - STEP 3
"""

from flask import Blueprint, request, jsonify
import os
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Create Blueprint
options_forecast_api = Blueprint('options_forecast_api', __name__, url_prefix='/api/options')

# Configuration
OPTIONS_DETERMINISTIC = os.getenv('OPTIONS_DETERMINISTIC', '0') == '1'
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), '../../tests/fixtures/options')
DATA_DIR = os.path.join(os.path.dirname(__file__), '../data/options')

# Ensure directories exist
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)

# Azure blocking logging
AZURE_BLOCKED_LOG = os.path.join(os.path.dirname(__file__), '../../reports/options_validation/diagnostics/azure_blocked.log')

def block_azure_call(endpoint: str, reason: str):
    """Log and block Azure API calls"""
    log_entry = {
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'endpoint': endpoint,
        'reason': reason,
        'blocked': True
    }
    
    Path(os.path.dirname(AZURE_BLOCKED_LOG)).mkdir(parents=True, exist_ok=True)
    with open(AZURE_BLOCKED_LOG, 'a') as f:
        f.write(json.dumps(log_entry) + '\n')
    
    logger.warning(f"🚫 AZURE BLOCKED: {endpoint} - {reason}")


def load_deterministic_fixture():
    """Load deterministic forecast fixture from tests/fixtures/options/"""
    fixture_path = os.path.join(FIXTURES_DIR, 'forecast_fixture.json')
    
    if not os.path.exists(fixture_path):
        logger.error(f"Fixture not found: {fixture_path}")
        return None
    
    with open(fixture_path, 'r') as f:
        return json.load(f)


@options_forecast_api.route('/forecast', methods=['POST'])
def options_forecast():
    """
    POST /api/options/forecast
    
    Payload: {
        ticker: str,
        expiration_days: int (default 30),
        deterministic: bool (default False),
        model_version: str (optional)
    }
    
    Returns: {
        error: bool,
        result: {...} or null,
        message: str (if error)
    }
    
    If OPTIONS_DETERMINISTIC=1 or payload.deterministic=True:
        Returns deterministic fixture from tests/fixtures/options/forecast_fixture.json
    
    Otherwise:
        Would call real model (but Azure is blocked, so returns error)
    """
    try:
        data = request.json or {}
        ticker = data.get('ticker', 'AAPL').upper()
        expiration_days = data.get('expiration_days', 30)
        deterministic = OPTIONS_DETERMINISTIC or data.get('deterministic', True)
        model_version = data.get('model_version', 'mock_v1')
        
        logger.info(f"📊 OPTIONS FORECAST REQUEST: ticker={ticker}, deterministic={deterministic}")
        
        # DETERMINISTIC MODE: Return fixture
        if deterministic:
            fixture = load_deterministic_fixture()
            
            if fixture is None:
                return jsonify({
                    'error': True,
                    'message': 'Deterministic fixture not found'
                }), 500
            
            # Customize fixture with request parameters
            result = fixture.copy()
            result['ticker'] = ticker
            result['expiration_days'] = expiration_days
            result['generated_at'] = datetime.utcnow().isoformat() + 'Z'
            
            logger.info(f"✅ Returning deterministic fixture for {ticker}")
            return jsonify(result), 200
        
        # NON-DETERMINISTIC MODE: Block Azure and return error
        block_azure_call(
            endpoint='/api/options/forecast',
            reason='AZURE_DISABLED: Live model calls not permitted during validation'
        )
        
        return jsonify({
            'error': True,
            'message': 'Live options forecast disabled during validation. Use deterministic=true.'
        }), 403
        
    except Exception as e:
        logger.error(f"❌ OPTIONS FORECAST ERROR: {e}", exc_info=True)
        return jsonify({
            'error': True,
            'message': str(e)
        }), 500


@options_forecast_api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'service': 'options_forecast_api',
        'deterministic_mode': OPTIONS_DETERMINISTIC,
        'timestamp': datetime.utcnow().isoformat() + 'Z'
    }), 200


# ============================================================================
# ADMIN ENDPOINTS (STEP 4: Paper Orders Safety)
# ============================================================================

@options_forecast_api.route('/admin/orders/audit', methods=['GET'])
def admin_orders_audit():
    """
    GET /api/options/admin/orders/audit?paper=true&limit=100
    
    Returns stored orders for auditing.
    Query params:
    - paper: "true"|"false" to filter by paper trading flag
    - limit: max records to return (default 100)
    - ticker: filter by ticker (optional)
    """
    try:
        paper_filter = request.args.get('paper', 'true').lower() == 'true'
        limit = int(request.args.get('limit', 100))
        ticker_filter = request.args.get('ticker', '').upper()
        
        # Try to load from database if available
        try:
            import psycopg2
            import psycopg2.extras
            
            conn_string = os.getenv('DATABASE_URL')
            if not conn_string:
                raise Exception("DATABASE_URL not set")
            
            conn = psycopg2.connect(conn_string)
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            
            query = "SELECT * FROM options_orders WHERE paper = %s"
            params: list = [paper_filter]
            
            if ticker_filter:
                query += " AND ticker = %s"
                params.append(ticker_filter)
            
            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            
            cur.execute(query, params)
            rows = cur.fetchall()
            
            cur.close()
            conn.close()
            
            # Convert datetime to ISO string
            for row in rows:
                for key in ['created_at', 'filled_at']:
                    if key in row and row[key]:
                        row[key] = row[key].isoformat() + 'Z'
            
            logger.info(f"✅ Fetched {len(rows)} orders from database (paper={paper_filter})")
            
            return jsonify({
                'error': False,
                'count': len(rows),
                'paper_filter': paper_filter,
                'orders': rows
            }), 200
            
        except Exception as db_err:
            logger.warning(f"Database unavailable, using JSON fallback: {db_err}")
            
            # Fallback: Read from JSON file
            json_file = os.path.join(DATA_DIR, 'orders.json')
            if not os.path.exists(json_file):
                return jsonify({
                    'error': False,
                    'count': 0,
                    'paper_filter': paper_filter,
                    'orders': [],
                    'source': 'json_fallback_empty'
                }), 200
            
            with open(json_file, 'r') as f:
                all_orders = json.load(f)
            
            # Filter
            filtered = [o for o in all_orders if o.get('paper') == paper_filter]
            if ticker_filter:
                filtered = [o for o in filtered if o.get('ticker') == ticker_filter]
            
            filtered = filtered[:limit]
            
            return jsonify({
                'error': False,
                'count': len(filtered),
                'paper_filter': paper_filter,
                'orders': filtered,
                'source': 'json_fallback'
            }), 200
            
    except Exception as e:
        logger.error(f"❌ Admin orders audit error: {e}", exc_info=True)
        return jsonify({
            'error': True,
            'message': str(e)
        }), 500


# Export blueprint
__all__ = ['options_forecast_api']
