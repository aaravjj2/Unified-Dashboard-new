"""
Phase 9C Backtest Summary API
==============================

Flask REST API endpoint serving Phase 9C backtest results.
Enables Agent 1A to validate front-end data rendering.

Endpoint:
    GET /api/backtest/summary

Response Format:
    JSON with orchestrator results, performance metrics, and trade logs

Usage:
    python api_backtest_summary.py
    
    # Access at: http://localhost:5000/api/backtest/summary

Author: Agent 1B — Unified Financial Dashboard Team
Version: 1.0
Date: October 29, 2025
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from flask import Flask, jsonify, request
    from flask_cors import CORS
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    print("⚠️  Flask not installed. Install with: pip install flask flask-cors")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
if FLASK_AVAILABLE:
    app = Flask(__name__)
    CORS(app)  # Enable CORS for dashboard integration


# ============================================================================
# DATA LOADER
# ============================================================================

class BacktestDataLoader:
    """Load and serve Phase 9C backtest results"""
    
    def __init__(self, data_dir: Path = Path("outputs/phase9c")):
        self.data_dir = Path(data_dir)
        self.results_cache: Optional[Dict[str, Any]] = None
        self.cache_timestamp: Optional[datetime] = None
        self.performance_cache: Optional[List[Dict[str, Any]]] = None  # Cache for CSV data
    
    def load_results(self, force_reload: bool = False) -> Dict[str, Any]:
        """Load phase9c_results.json with caching"""
        
        results_path = self.data_dir / "phase9c_results.json"
        
        # Check if file exists
        if not results_path.exists():
            logger.warning(f"⚠️  Results file not found: {results_path}")
            return {
                "error": "No backtest results available",
                "message": "Run validation first: python run_phase9c_validation.py"
            }
        
        # Check cache
        file_mtime = datetime.fromtimestamp(results_path.stat().st_mtime)
        if not force_reload and self.results_cache and self.cache_timestamp:
            if file_mtime <= self.cache_timestamp:
                logger.info("📦 Serving cached results")
                return self.results_cache
        
        # Load fresh data
        try:
            with open(results_path, 'r') as f:
                results = json.load(f)
            
            self.results_cache = results
            self.cache_timestamp = file_mtime
            
            logger.info(f"✅ Loaded results from: {results_path}")
            return results
        
        except json.JSONDecodeError as e:
            logger.error(f"❌ Failed to parse JSON: {e}")
            return {
                "error": "Invalid JSON format",
                "message": str(e)
            }
        except Exception as e:
            logger.error(f"❌ Failed to load results: {e}")
            return {
                "error": "Failed to load results",
                "message": str(e)
            }
    
    def load_performance_summary(self) -> List[Dict[str, Any]]:
        """Load performance summary CSV as JSON with caching"""
        
        # Return cached data if available
        if self.performance_cache is not None:
            logger.info("📦 Serving cached performance data")
            return self.performance_cache
        
        csv_path = self.data_dir / "phase9c_performance_summary.csv"
        
        if not csv_path.exists():
            return [{"error": "Performance summary not found"}]
        
        try:
            import pandas as pd
            df = pd.read_csv(csv_path)
            result = df.to_dict(orient='records')
            
            # Cache the result
            self.performance_cache = result
            logger.info(f"✅ Loaded and cached {len(result)} performance records")
            
            return result
        except Exception as e:
            logger.error(f"❌ Failed to load performance summary: {e}")
            return [{"error": str(e)}]
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """Get high-level summary statistics"""
        
        results = self.load_results()
        
        if "error" in results:
            return results
        
        # Extract key stats
        stats = {
            "timestamp": results.get("timestamp"),
            "mode": results.get("mode"),
            "total_trades": results.get("total_trades", 0),
            "total_pnl": results.get("total_pnl", 0),
            "win_rate": results.get("win_rate", 0),
            "mean_return": results.get("mean_return", 0),
            "max_drawdown": results.get("max_drawdown", 0),
            "determinism_passed": results.get("all_deterministic", False),  # Dashboard expects this name
            "all_sla_met": results.get("all_sla_met", False),
            "tiers_tested": list(results.get("tiers", {}).keys()),  # Dashboard expects this
            "tiers": {
                tier_name: {
                    "num_tickers": tier.get("num_tickers", 0),
                    "total_trades": tier.get("total_trades", 0),
                    "avg_time_ms": tier.get("avg_time_ms", 0),
                    "total_pnl": tier.get("total_pnl", 0),
                    "deterministic": tier.get("deterministic", False),
                    "sla_met": tier.get("sla_met", False)
                }
                for tier_name, tier in results.get("tiers", {}).items()
            }
        }
        
        return stats


# Initialize data loader
data_loader = BacktestDataLoader()


# ============================================================================
# API ENDPOINTS
# ============================================================================

if FLASK_AVAILABLE:
    
    @app.route('/api/backtest/summary', methods=['GET'])
    def get_backtest_summary():
        """
        GET /api/backtest/summary
        
        Returns comprehensive backtest results including:
        - Overall statistics
        - Per-tier results
        - Performance metrics
        - Determinism validation
        
        Query Parameters:
        - full (bool): Return full results with all trades (default: false)
        - tier (str): Filter by specific tier (small/medium/large)
        """
        
        try:
            # Get query parameters
            full = request.args.get('full', 'false').lower() == 'true'
            tier_filter = request.args.get('tier', None)
            
            # Load results
            if full:
                results = data_loader.load_results()
            else:
                results = data_loader.get_summary_stats()
            
            # Filter by tier if requested
            if tier_filter and tier_filter in ['small', 'medium', 'large']:
                if "tiers" in results and tier_filter in results["tiers"]:
                    results = {
                        "tier": tier_filter,
                        "data": results["tiers"][tier_filter],
                        "timestamp": results.get("timestamp")
                    }
            
            return jsonify(results), 200
        
        except Exception as e:
            logger.error(f"❌ API error: {e}")
            return jsonify({
                "error": "Internal server error",
                "message": str(e)
            }), 500
    
    @app.route('/api/backtest/performance', methods=['GET'])
    def get_performance_metrics():
        """
        GET /api/backtest/performance
        
        Returns detailed performance metrics from CSV
        """
        
        try:
            metrics = data_loader.load_performance_summary()
            return jsonify(metrics), 200
        
        except Exception as e:
            logger.error(f"❌ API error: {e}")
            return jsonify({
                "error": "Internal server error",
                "message": str(e)
            }), 500
    
    @app.route('/api/backtest/health', methods=['GET'])
    def health_check():
        """
        GET /api/backtest/health
        
        Health check endpoint
        """
        
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "phase9c-backtest-api",
            "version": "1.0"
        }), 200
    
    @app.route('/api/backtest/reload', methods=['POST'])
    def reload_data():
        """
        POST /api/backtest/reload
        
        Force reload of backtest data from disk
        """
        
        try:
            results = data_loader.load_results(force_reload=True)
            
            return jsonify({
                "status": "success",
                "message": "Data reloaded successfully",
                "timestamp": datetime.now().isoformat()
            }), 200
        
        except Exception as e:
            logger.error(f"❌ Reload failed: {e}")
            return jsonify({
                "error": "Reload failed",
                "message": str(e)
            }), 500


# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Run Flask development server"""
    
    if not FLASK_AVAILABLE:
        print("❌ Flask not available. Install with: pip install flask flask-cors")
        return 1
    
    import argparse
    parser = argparse.ArgumentParser(description='Phase 9C Backtest API Server')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    parser.add_argument('--port', type=int, default=5000, help='Port to run on')
    args = parser.parse_args()
    
    logger.info("\n" + "="*80)
    logger.info("PHASE 9C BACKTEST SUMMARY API")
    logger.info("="*80)
    logger.info("\nEndpoints:")
    logger.info("  GET  /api/backtest/summary       - Get backtest summary")
    logger.info("  GET  /api/backtest/performance   - Get performance metrics")
    logger.info("  GET  /api/backtest/health        - Health check")
    logger.info("  POST /api/backtest/reload        - Reload data")
    logger.info(f"\nStarting server on http://localhost:{args.port}")
    logger.info(f"Debug mode: {args.debug}")
    logger.info("="*80 + "\n")
    
    app.run(
        host='0.0.0.0',
        port=args.port,
        debug=args.debug,
        use_reloader=args.debug  # Only use reloader in debug mode
    )


if __name__ == "__main__":
    main()
