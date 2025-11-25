"""
Command Center API Blueprint
RESTful API for Command Center dashboard components

Endpoints:
    POST /api/cc/run_smoke - Execute smoke tests
    GET /api/cc/portfolio_snapshot - Current portfolio positions
    GET /api/cc/market_sentiment - Latest market sentiment score
    GET /api/cc/last_run - Last pipeline run metadata
"""

import os
import logging
import time
import json
from pathlib import Path
from flask import Blueprint, request, jsonify
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Create Blueprint
cc_api = Blueprint('cc_api', __name__, url_prefix='/api/cc')


@cc_api.route('/health', methods=['GET'])
def health():
    """
    Command Center health check
    
    GET /api/cc/health
    
    Response:
        {
            "status": "healthy" | "degraded",
            "sentiment_poller": "running" | "stopped",
            "timestamp": "2024-11-23T10:30:00Z"
        }
    """
    try:
        # Check if sentiment poller is running (check recent log files)
        sentiment_log_dir = Path("reports/command_center/logs/market_sentiment")
        poller_status = "stopped"
        
        if sentiment_log_dir.exists():
            recent_logs = sorted(
                sentiment_log_dir.glob("sentiment_*.json"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            if recent_logs:
                latest_log = recent_logs[0]
                age_seconds = time.time() - latest_log.stat().st_mtime
                # Consider running if last update was within 2 minutes
                if age_seconds < 120:
                    poller_status = "running"
        
        return jsonify({
            "status": "healthy" if poller_status == "running" else "degraded",
            "sentiment_poller": poller_status,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 200
        
    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 500


@cc_api.route('/run_smoke', methods=['POST'])
def run_smoke():
    """
    Execute smoke tests via Playwright
    
    POST /api/cc/run_smoke
    
    Response:
        {
            "status": "success" | "failed",
            "total": 5,
            "passed": 5,
            "failed": 0,
            "skipped": 0,
            "all_passed": true,
            "results": [...],
            "timestamp": "2024-11-23T10:30:00Z"
        }
    """
    try:
        # Import test runner
        import subprocess
        
        logger.info("🧪 Running Command Center smoke tests...")
        
        # Run Playwright tests
        result = subprocess.run(
            ["pytest", "tests/playwright/cc_headed_smoke.py", "-v", "--json-report"],
            cwd="/home/aarav/unified-dashboard",
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Parse test results
        test_output = result.stdout
        test_results = {
            "status": "success" if result.returncode == 0 else "failed",
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "all_passed": result.returncode == 0,
            "output": test_output[:500],  # Truncate for display
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        
        # Try to parse pytest output for counts
        for line in test_output.split('\n'):
            if 'passed' in line.lower():
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == 'passed':
                        try:
                            test_results['passed'] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
        
        return jsonify(test_results), 200 if test_results['all_passed'] else 500
        
    except subprocess.TimeoutExpired:
        logger.error("Smoke tests timed out")
        return jsonify({
            "status": "timeout",
            "error": "Tests timed out after 120 seconds",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 500
    except Exception as e:
        logger.exception("Smoke test error")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 500


@cc_api.route('/portfolio_snapshot', methods=['GET'])
def portfolio_snapshot():
    """
    Get current portfolio positions
    
    GET /api/cc/portfolio_snapshot
    
    Response:
        {
            "status": "success",
            "positions": [
                {
                    "symbol": "AAPL",
                    "qty": 10,
                    "current_price": 175.50,
                    "market_value": 1755.00,
                    "unrealized_pl": 50.00
                }
            ],
            "total_value": 25000.00,
            "timestamp": "2024-11-23T10:30:00Z"
        }
    """
    try:
        # Determine if Alpaca connector is available/enabled.
        # Allow read-only position fetches when the connector reports enabled (autodetect via connector),
        # even if CC_SAFE_MODE is set — safe mode should prevent writes, not reads.
        safe_mode = os.getenv("CC_SAFE_MODE", "true").lower() == "true"

        alpaca_enabled_env = os.getenv("ALPACA_ENABLED", "").lower() == "true"
        alpaca_enabled = alpaca_enabled_env
        try:
            # Prefer the connector's own autodetection (it checks APCA_* / ALPACA_* env vars)
            from services.cc import alpaca_market as _alpaca
            alpaca_enabled = alpaca_enabled or getattr(_alpaca, "ALPACA_ENABLED", False)
        except Exception:
            # If the connector cannot be imported, fall back to env var only
            pass

        # If Alpaca is not enabled by env or connector autodetection, return mock data.
        if not alpaca_enabled:
            # Try a best-effort direct import & read: some environments may have the connector
            # available even if ALPACA_ENABLED env var isn't set. Attempt to call the helper
            # and use any real positions returned before falling back to mocks.
            try:
                from services.cc.alpaca_market import get_alpaca_positions
                positions = get_alpaca_positions()
                if positions:
                    total_value = sum(p.get("market_value", 0) for p in positions)
                    return jsonify({
                        "status": "success",
                        "positions": positions,
                        "total_value": total_value,
                        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }), 200
            except Exception:
                # Fall through to mock response below
                pass

            return jsonify({
                "status": "mock",
                "message": "Safe mode or Alpaca not enabled - showing mock data",
                "positions": [
                    {"symbol": "AAPL", "qty": 10, "current_price": 175.50, "market_value": 1755.0},
                    {"symbol": "MSFT", "qty": 5, "current_price": 380.25, "market_value": 1901.25},
                ],
                "total_value": 3656.25,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }), 200

        # Live Alpaca read (safe mode must be false and Alpaca enabled)
        try:
            from services.cc.alpaca_market import get_alpaca_positions
            positions = get_alpaca_positions()

            total_value = sum(p.get("market_value", 0) for p in positions)

            return jsonify({
                "status": "success",
                "positions": positions,
                "total_value": total_value,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }), 200
        except ImportError:
            logger.warning("Alpaca connector not available - returning mock data")
            return jsonify({
                "status": "mock",
                "message": "Alpaca connector unavailable",
                "positions": [],
                "total_value": 0.0,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }), 200
        
    except Exception as e:
        logger.exception("Portfolio snapshot error")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 500


@cc_api.route('/market_sentiment', methods=['GET'])
def market_sentiment():
    """
    Get latest market sentiment score
    
    GET /api/cc/market_sentiment
    
    Response:
        {
            "status": "success",
            "score": 0.45,  # Range: -1.0 (bearish) to +1.0 (bullish)
            "label": "Bullish",
            "sources": ["finnhub", "alpaca"],
            "timestamp": "2024-11-23T10:30:00Z"
        }
    """
    try:
        # Read latest sentiment log
        sentiment_log_dir = Path("reports/command_center/logs/market_sentiment")
        
        if not sentiment_log_dir.exists():
            return jsonify({
                "status": "no_data",
                "score": 0.0,
                "label": "Neutral",
                "sources": [],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }), 200
        
        # Find most recent log file
        recent_logs = sorted(
            sentiment_log_dir.glob("sentiment_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        if not recent_logs:
            return jsonify({
                "status": "no_data",
                "score": 0.0,
                "label": "Neutral",
                "sources": [],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }), 200
        
        # Load latest sentiment data
        with open(recent_logs[0], 'r') as f:
            sentiment_data = json.load(f)
        
        score = sentiment_data.get("market_sentiment_score", 0.0)
        
        # Determine label
        if score > 0.2:
            label = "Bullish"
        elif score < -0.2:
            label = "Bearish"
        else:
            label = "Neutral"
        
        return jsonify({
            "status": "success",
            "score": score,
            "label": label,
            "sources": sentiment_data.get("sources", []),
            "timestamp": sentiment_data.get("timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
        }), 200
        
    except Exception as e:
        logger.exception("Market sentiment error")
        return jsonify({
            "status": "error",
            "error": str(e),
            "score": 0.0,
            "label": "Neutral",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 500


@cc_api.route('/last_run', methods=['GET'])
def last_run():
    """
    Get metadata for last pipeline runs
    
    GET /api/cc/last_run
    
    Response:
        {
            "status": "success",
            "picks": {
                "last_run_id": "picks_20241123_103045",
                "status": "completed",
                "count": 15
            },
            "backtest": {
                "last_run_id": "bt_20241123_103045",
                "status": "completed"
            },
            "timestamp": "2024-11-23T10:30:00Z"
        }
    """
    try:
        # Check for recent job result files
        results_dir = Path("/tmp")
        
        # Find latest picks job
        picks_jobs = sorted(
            results_dir.glob("picks_job_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        picks_data = {}
        if picks_jobs:
            try:
                with open(picks_jobs[0], 'r') as f:
                    picks_result = json.load(f)
                picks_data = {
                    "last_run_id": picks_jobs[0].stem,
                    "status": picks_result.get("status", "unknown"),
                    "count": len(picks_result.get("picks", []))
                }
            except Exception as e:
                logger.warning(f"Failed to parse picks job: {e}")
                picks_data = {"last_run_id": "N/A", "status": "error"}
        else:
            picks_data = {"last_run_id": "N/A", "status": "not_run", "count": 0}
        
        # Find latest backtest job
        backtest_jobs = sorted(
            results_dir.glob("backtest_job_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        
        backtest_data = {}
        if backtest_jobs:
            try:
                with open(backtest_jobs[0], 'r') as f:
                    bt_result = json.load(f)
                backtest_data = {
                    "last_run_id": backtest_jobs[0].stem,
                    "status": bt_result.get("status", "unknown")
                }
            except Exception as e:
                logger.warning(f"Failed to parse backtest job: {e}")
                backtest_data = {"last_run_id": "N/A", "status": "error"}
        else:
            backtest_data = {"last_run_id": "N/A", "status": "not_run"}
        
        return jsonify({
            "status": "success",
            "picks": picks_data,
            "backtest": backtest_data,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 200
        
    except Exception as e:
        logger.exception("Last run error")
        return jsonify({
            "status": "error",
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 500


def register_cc_api(server):
    """
    Register Command Center API blueprint with Flask server
    
    Args:
        server: Flask server instance
    """
    server.register_blueprint(cc_api)
    logger.info("✅ Registered Command Center API: /api/cc/*")
