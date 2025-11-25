"""
Command Center Admin API
Diagnostic and admin endpoints for Command Center

Endpoints:
    GET /admin/cc/diagnostics - System diagnostics
    GET /admin/cc/callback_integrity - Callback integrity check
    POST /admin/cc/reindex - Reindex data sources
"""

import os
import logging
import time
import json
from pathlib import Path
from flask import Blueprint, request, jsonify
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Create Blueprint
cc_admin_api = Blueprint('cc_admin_api', __name__, url_prefix='/admin/cc')


@cc_admin_api.route('/diagnostics', methods=['GET'])
def diagnostics():
    """
    Get Command Center system diagnostics
    
    GET /admin/cc/diagnostics
    
    Response:
        {
            "status": "success",
            "system": {
                "python_version": "3.11.5",
                "dash_version": "2.14.0",
                "port": 8050
            },
            "sentiment_poller": {
                "status": "running",
                "last_update": "2024-11-23T10:30:00Z",
                "log_count": 450
            },
            "disk_usage": {
                "artifacts_mb": 125.5,
                "logs_mb": 45.2
            },
            "timestamp": "2024-11-23T10:30:00Z"
        }
    """
    try:
        import sys
        import dash
        
        # System info
        system_info = {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "dash_version": dash.__version__,
            "port": int(os.getenv("CC_PORT", "8050"))
        }
        
        # Sentiment poller status
        sentiment_log_dir = Path("reports/command_center/logs/market_sentiment")
        poller_status = "stopped"
        last_update = "N/A"
        log_count = 0
        
        if sentiment_log_dir.exists():
            log_files = list(sentiment_log_dir.glob("sentiment_*.json"))
            log_count = len(log_files)
            
            if log_files:
                latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
                age_seconds = time.time() - latest_log.stat().st_mtime
                
                if age_seconds < 120:
                    poller_status = "running"
                    last_update = time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ",
                        time.gmtime(latest_log.stat().st_mtime)
                    )
        
        # Disk usage
        artifacts_dir = Path("reports/command_center")
        artifacts_mb = 0.0
        logs_mb = 0.0
        
        if artifacts_dir.exists():
            for file in artifacts_dir.rglob("*"):
                if file.is_file():
                    size_mb = file.stat().st_size / (1024 * 1024)
                    if "logs" in str(file):
                        logs_mb += size_mb
                    else:
                        artifacts_mb += size_mb
        
        return jsonify({
            "status": "success",
            "system": system_info,
            "sentiment_poller": {
                "status": poller_status,
                "last_update": last_update,
                "log_count": log_count
            },
            "disk_usage": {
                "artifacts_mb": round(artifacts_mb, 2),
                "logs_mb": round(logs_mb, 2)
            },
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 200
        
    except Exception as e:
        logger.exception("Diagnostics error")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 500


@cc_admin_api.route('/callback_integrity', methods=['GET'])
def callback_integrity():
    """
    Check callback integrity (duplicate IDs, missing outputs, etc.)
    
    GET /admin/cc/callback_integrity
    
    Response:
        {
            "status": "success",
            "issues": [],
            "total_callbacks": 45,
            "timestamp": "2024-11-23T10:30:00Z"
        }
    """
    try:
        # This would require introspecting the Dash app instance
        # For now, return a placeholder
        return jsonify({
            "status": "success",
            "message": "Callback integrity check not implemented yet",
            "issues": [],
            "total_callbacks": 0,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 200
        
    except Exception as e:
        logger.exception("Callback integrity error")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 500


@cc_admin_api.route('/reindex', methods=['POST'])
def reindex():
    """
    Reindex data sources (chat vector index, etc.)
    
    POST /admin/cc/reindex
    
    Request:
        {
            "target": "all" | "chat" | "picks"
        }
    
    Response:
        {
            "status": "success",
            "message": "Reindex completed",
            "results": {...},
            "timestamp": "2024-11-23T10:30:00Z"
        }
    """
    try:
        data = request.get_json() or {}
        target = data.get("target", "all")
        
        results = {}
        
        if target in ["all", "chat"]:
            # Trigger chat vector index rebuild
            try:
                from financial_dashboard.services.chat.ingest import IngestionPipeline
                pipeline = IngestionPipeline()
                pipeline.ingest_all()
                results["chat"] = "success"
            except Exception as e:
                logger.exception("Chat reindex failed")
                results["chat"] = f"error: {str(e)[:50]}"
        
        if target in ["all", "picks"]:
            # Trigger picks data reload (placeholder)
            results["picks"] = "not_implemented"
        
        return jsonify({
            "status": "success",
            "message": f"Reindex completed for {target}",
            "results": results,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 200
        
    except Exception as e:
        logger.exception("Reindex error")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 500


def register_cc_admin(server):
    """
    Register Command Center Admin API blueprint with Flask server
    
    Args:
        server: Flask server instance
    """
    server.register_blueprint(cc_admin_api)
    logger.info("✅ Registered Command Center Admin API: /admin/cc/*")
