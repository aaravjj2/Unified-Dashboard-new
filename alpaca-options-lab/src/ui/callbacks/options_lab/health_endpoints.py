"""
Health Check Endpoints for Options Lab

Provides health and readiness probes for monitoring.
"""

import logging
from datetime import datetime
from typing import Dict, Any
from flask import Blueprint, jsonify

logger = logging.getLogger(__name__)

# Create Blueprint for health endpoints
health_bp = Blueprint('options_health', __name__, url_prefix='/api/options')


@health_bp.route('/health', methods=['GET'])
def health_check() -> tuple:
    """
    Basic health check endpoint.
    
    Returns:
        JSON response with health status
    """
    return jsonify({
        'status': 'healthy',
        'service': 'options-lab',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@health_bp.route('/ready', methods=['GET'])
def readiness_check() -> tuple:
    """
    Readiness probe - checks if service can handle requests.
    
    Returns:
        JSON response with readiness status
    """
    checks = {
        'alpaca_client': False,
        'cache': False
    }
    
    try:
        # Check Alpaca client
        from .alpaca_options import get_alpaca_client
        client = get_alpaca_client()
        checks['alpaca_client'] = client is not None
        checks['alpaca_available'] = getattr(client, 'available', False)
    except Exception as e:
        logger.warning(f"Alpaca client check failed: {e}")
    
    try:
        # Check cache
        from .options_cache import get_options_cache
        cache = get_options_cache()
        checks['cache'] = cache is not None
        checks['cache_size'] = cache.stats.size
    except Exception as e:
        logger.warning(f"Cache check failed: {e}")
    
    # Ready if at least cache is working
    is_ready = checks.get('cache', False)
    status_code = 200 if is_ready else 503
    
    return jsonify({
        'status': 'ready' if is_ready else 'not_ready',
        'service': 'options-lab',
        'timestamp': datetime.utcnow().isoformat(),
        'checks': checks
    }), status_code


@health_bp.route('/metrics', methods=['GET'])
def get_metrics() -> tuple:
    """
    Get service metrics.
    
    Returns:
        JSON response with metrics
    """
    metrics = {
        'timestamp': datetime.utcnow().isoformat(),
        'service': 'options-lab'
    }
    
    try:
        # Get Alpaca metrics
        from .alpaca_options import get_alpaca_metrics
        metrics['alpaca'] = get_alpaca_metrics()
    except Exception as e:
        metrics['alpaca_error'] = str(e)
    
    try:
        # Get cache metrics
        from .options_cache import get_options_cache
        cache = get_options_cache()
        metrics['cache'] = cache.stats.to_dict()
    except Exception as e:
        metrics['cache_error'] = str(e)
    
    try:
        # Get circuit breaker stats
        from .circuit_breaker import get_all_breaker_stats
        metrics['circuit_breakers'] = get_all_breaker_stats()
    except Exception as e:
        metrics['circuit_breaker_error'] = str(e)
    
    return jsonify(metrics), 200


@health_bp.route('/cache/info', methods=['GET'])
def cache_info() -> tuple:
    """Get detailed cache information."""
    try:
        from .options_cache import get_options_cache
        cache = get_options_cache()
        return jsonify(cache.get_info()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@health_bp.route('/cache/clear', methods=['POST'])
def clear_cache() -> tuple:
    """Clear the options cache."""
    try:
        from .options_cache import get_options_cache
        cache = get_options_cache()
        count = cache.clear()
        logger.info(f"Cache cleared via API: {count} entries")
        return jsonify({
            'status': 'cleared',
            'entries_removed': count
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def register_health_endpoints(app):
    """
    Register health endpoints with Flask app.
    
    Args:
        app: Flask/Dash server instance
    """
    try:
        app.register_blueprint(health_bp)
        logger.info("✅ Options health endpoints registered")
    except Exception as e:
        logger.error(f"❌ Failed to register health endpoints: {e}")
