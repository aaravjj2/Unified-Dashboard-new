"""
Picks API Endpoints - REST API for weekly and monthly picks

Endpoints:
- GET /api/weekly_picks?limit=&offset= - Paginated weekly picks
- GET /api/monthly_picks?limit=&offset= - Paginated monthly picks
- POST /api/picks/reload - Admin: reload picks from CSV
- GET /api/picks/health - Health check

Author: Agent-1B
Date: 2025-11-21
"""

import os
import json
import logging
from datetime import datetime
from typing import Optional
from flask import jsonify, request
import pandas as pd

from utils.picks_fetcher import PicksFetcher, is_deterministic_mode

logger = logging.getLogger(__name__)

# Simple auth token (should be in environment in production)
ADMIN_TOKEN = os.environ.get('PICKS_ADMIN_TOKEN', 'dev_token_change_me')


def check_admin_auth() -> bool:
    """
    Check if request has valid admin token.
    
    Returns:
        True if authorized, False otherwise
    """
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    return token == ADMIN_TOKEN


def api_weekly_picks():
    """
    GET /api/weekly_picks
    
    Query params:
        limit: Max records to return (default 100)
        offset: Offset for pagination (default 0)
        fixture: Use deterministic fixture (true/false)
    
    Returns:
        JSON with weekly picks data
    """
    try:
        logger.info("📡 API Request: /api/weekly_picks")
        
        # Parse query params
        limit_arg = request.args.get('limit')
        offset = int(request.args.get('offset', 0))
        # If client did not provide a limit, return the full list by default
        limit = int(limit_arg) if limit_arg is not None else None
        use_fixture = request.args.get('fixture', '').lower() == 'true'
        
        # Load picks
        fixture_path = 'reports/picks/fixtures/weekly_fixture.json' if use_fixture else None
        fetcher = PicksFetcher(fixture_path=fixture_path)
        
        if use_fixture or is_deterministic_mode():
            picks_df = fetcher.load_from_fixture()
        else:
            # Try JSON fallback first
            json_path = 'data/picks/weekly_picks.json'
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    data = json.load(f)
                picks_df = pd.DataFrame(data.get('data', []))
            else:
                picks_df = fetcher.load_from_db('weekly_picks')
        
        # Enrich with prices if needed
        if not picks_df.empty and 'current_price' not in picks_df.columns:
            picks_df = fetcher.enrich_with_prices(picks_df, provenance=True)
        
        # Apply pagination
        total_count = len(picks_df)
        # Default to returning up to 20 records when client omits `limit`
        if limit is None:
            default_limit = 20
            picks_df_page = picks_df.iloc[offset:offset+default_limit]
            effective_limit = min(default_limit, max(0, total_count - offset))
        else:
            picks_df_page = picks_df.iloc[offset:offset+limit]
            effective_limit = limit
        
        # Convert to JSON-serializable format
        records = picks_df_page.to_dict('records')
        
        # Clean NaN values
        for record in records:
            for key, value in list(record.items()):
                if pd.isna(value):
                    record[key] = None
        
        response = {
            'status': 'success',
            'pick_type': 'weekly',
            'count': len(records),
            'total_count': total_count,
            'offset': offset,
            'limit': effective_limit,
            'has_more': (offset + effective_limit) < total_count,
            'data': records,
            'timestamp': datetime.now().isoformat(),
            'deterministic': use_fixture or is_deterministic_mode()
        }
        
        logger.info(f"✅ Returning {len(records)} weekly picks (total: {total_count})")
        return jsonify(response)
        
    except Exception as e:
        logger.exception("Error in /api/weekly_picks endpoint")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'pick_type': 'weekly',
            'count': 0
        }), 500


def api_monthly_picks():
    """
    GET /api/monthly_picks
    
    Query params:
        limit: Max records to return (default 100)
        offset: Offset for pagination (default 0)
        fixture: Use deterministic fixture (true/false)
    
    Returns:
        JSON with monthly picks data
    """
    try:
        logger.info("📡 API Request: /api/monthly_picks")
        
        # Parse query params
        limit_arg = request.args.get('limit')
        offset = int(request.args.get('offset', 0))
        # If client did not provide a limit, return the full list by default
        limit = int(limit_arg) if limit_arg is not None else None
        use_fixture = request.args.get('fixture', '').lower() == 'true'
        
        # Load picks
        fixture_path = 'reports/picks/fixtures/monthly_fixture.json' if use_fixture else None
        fetcher = PicksFetcher(fixture_path=fixture_path)
        
        if use_fixture or is_deterministic_mode():
            picks_df = fetcher.load_from_fixture()
        else:
            # Try JSON fallback first
            json_path = 'data/picks/monthly_picks.json'
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    data = json.load(f)
                picks_df = pd.DataFrame(data.get('data', []))
            else:
                picks_df = fetcher.load_from_db('monthly_picks')
        
        # Enrich with prices if needed
        if not picks_df.empty and 'current_price' not in picks_df.columns:
            picks_df = fetcher.enrich_with_prices(picks_df, provenance=True)
        
        # Apply pagination
        total_count = len(picks_df)
        # Default to returning up to 20 records when client omits `limit`
        if limit is None:
            default_limit = 20
            picks_df_page = picks_df.iloc[offset:offset+default_limit]
            effective_limit = min(default_limit, max(0, total_count - offset))
        else:
            picks_df_page = picks_df.iloc[offset:offset+limit]
            effective_limit = limit
        
        # Convert to JSON-serializable format
        records = picks_df_page.to_dict('records')
        
        # Clean NaN values
        for record in records:
            for key, value in list(record.items()):
                if pd.isna(value):
                    record[key] = None
        
        response = {
            'status': 'success',
            'pick_type': 'monthly',
            'count': len(records),
            'total_count': total_count,
            'offset': offset,
            'limit': effective_limit,
            'has_more': (offset + effective_limit) < total_count,
            'data': records,
            'timestamp': datetime.now().isoformat(),
            'deterministic': use_fixture or is_deterministic_mode()
        }
        
        logger.info(f"✅ Returning {len(records)} monthly picks (total: {total_count})")
        return jsonify(response)
        
    except Exception as e:
        logger.exception("Error in /api/monthly_picks endpoint")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'pick_type': 'monthly',
            'count': 0
        }), 500


def api_picks_reload():
    """
    POST /api/picks/reload
    
    Admin endpoint to trigger background price update.
    Requires Authorization header with valid token.
    
    Returns:
        JSON with reload status
    """
    if not check_admin_auth():
        return jsonify({
            'status': 'error',
            'message': 'Unauthorized'
        }), 401
    
    try:
        logger.info("📡 API Request: /api/picks/reload (admin)")
        
        # Trigger background update
        from background.picks_updater import run_picks_update
        
        result = run_picks_update()
        
        logger.info(f"✅ Reload triggered: {result.get('status')}")
        return jsonify(result)
        
    except Exception as e:
        logger.exception("Error in /api/picks/reload endpoint")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def api_picks_health():
    """
    GET /api/picks/health
    
    Returns health status and last run info.
    
    Returns:
        JSON with health data
    """
    try:
        logger.info("📡 API Request: /api/picks/health")
        
        # Load last run summary if it exists
        summary_file = 'reports/picks/logs/last_run.json'
        last_run = None
        
        if os.path.exists(summary_file):
            with open(summary_file, 'r') as f:
                last_run = json.load(f)
        
        # Count records in DB/JSON
        weekly_count = 0
        monthly_count = 0
        
        # Try JSON files
        weekly_json = 'data/picks/weekly_picks.json'
        monthly_json = 'data/picks/monthly_picks.json'
        
        if os.path.exists(weekly_json):
            with open(weekly_json, 'r') as f:
                data = json.load(f)
                weekly_count = data.get('count', len(data.get('data', [])))
        
        if os.path.exists(monthly_json):
            with open(monthly_json, 'r') as f:
                data = json.load(f)
                monthly_count = data.get('count', len(data.get('data', [])))
        
        # Build response
        response = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'deterministic_mode': is_deterministic_mode(),
            'counts': {
                'weekly_picks': weekly_count,
                'monthly_picks': monthly_count
            },
            'last_run': last_run,
            'endpoints': {
                'weekly_picks': '/api/weekly_picks',
                'monthly_picks': '/api/monthly_picks',
                'reload': '/api/picks/reload (admin)',
                'health': '/api/picks/health'
            }
        }
        
        logger.info("✅ Health check OK")
        return jsonify(response)
        
    except Exception as e:
        logger.exception("Error in /api/picks/health endpoint")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


def register_picks_api_routes(server):
    """
    Register all picks API routes with Flask server.
    
    Args:
        server: Flask server instance
    """
    # Use distinct endpoint names to avoid clashing with existing app-level handlers
    server.add_url_rule('/api/weekly_picks', 'picks_api_weekly_picks', api_weekly_picks, methods=['GET'])
    server.add_url_rule('/api/monthly_picks', 'picks_api_monthly_picks', api_monthly_picks, methods=['GET'])
    server.add_url_rule('/api/picks/reload', 'picks_api_picks_reload', api_picks_reload, methods=['POST'])
    server.add_url_rule('/api/picks/health', 'picks_api_picks_health', api_picks_health, methods=['GET'])
    
    logger.info("✅ Picks API routes registered")


# Module exports
__all__ = [
    'api_weekly_picks',
    'api_monthly_picks',
    'api_picks_reload',
    'api_picks_health',
    'register_picks_api_routes'
]
