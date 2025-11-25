"""
Financial Dashboard - Application Factory (Refactored)
Clean separation: Creates Flask + Dash app, registers API endpoints only.
Layout and callbacks are handled separately.
"""
import os
import sys
import json
import logging
import subprocess
import atexit
import time
import dash
from dash import html as _dash_html_compat

# Compatibility shim: Some older code (or serialized layouts) may attempt to
# reference `dash.html.Style`. Not all Dash versions expose `Style` as a
# component. Define a safe fallback to avoid an import-time AttributeError
# during layout creation. The fallback returns a harmless `html.Div`
# placeholder so the app can start; real CSS injection should use
# `html.Script` or runtime injection (see `components/chatbot_ui.py`).
if not hasattr(_dash_html_compat, 'Style'):
    def _compat_style(children=None, **props):
        # Return a non-crashing placeholder. Do not try to render raw CSS
        # here to avoid accidental XSS or rendering problems — code that
        # requires an actual <style> node should inject it via JS instead.
        return _dash_html_compat.Div(children=children, **props)

    setattr(_dash_html_compat, 'Style', _compat_style)
# Some versions of Dash do not expose `html.Input` as an element constructor.
# Older code (or serialized layouts) may call `dash.html.Input(...)`. Provide
# a compatible shim that forwards to `dash.dcc.Input` so layout creation does
# not crash. This preserves the intended API surface for legacy code.
if not hasattr(_dash_html_compat, 'Input'):
    try:
        from dash import dcc as _dash_dcc

        def _compat_input(*args, **kwargs):
            return _dash_dcc.Input(*args, **kwargs)

        setattr(_dash_html_compat, 'Input', _compat_input)
    except Exception:
        # As a last resort, provide a non-crashing placeholder that renders
        # a harmless Div so the app can continue starting.
        def _compat_input_placeholder(*args, **kwargs):
            return _dash_html_compat.Div(**kwargs)

        setattr(_dash_html_compat, 'Input', _compat_input_placeholder)
import dash_bootstrap_components as dbc
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Setup paths
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Global chatbot process handle
_chatbot_process = None

def start_chatbot_service():
    """
    Launch chatbot service as subprocess if not already running.
    Returns True if chatbot is available, False otherwise.
    """
    global _chatbot_process
    
    # Check if already running
    try:
        import requests
        resp = requests.get("http://localhost:8062/health", timeout=2)
        if resp.status_code == 200:
            logger.info("✅ Chatbot service already running on port 8062")
            return True
    except:
        pass
    
    # Launch subprocess
    logger.info("🚀 Starting chatbot service...")
    try:
        _chatbot_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn",
            "financial_dashboard.services.chatbot_service:app",
            "--host", "0.0.0.0",
            "--port", "8062"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, cwd=os.path.dirname(APP_DIR))
        
        # Wait for service to be ready (max 30 seconds)
        import requests
        for i in range(30):
            try:
                resp = requests.get("http://localhost:8062/health", timeout=1)
                if resp.status_code == 200:
                    logger.info("✅ Chatbot service ready on port 8062")
                    return True
            except:
                time.sleep(1)
        
        logger.warning("⚠️ Chatbot service started but health check failed")
        return False
    except Exception as e:
        logger.error(f"❌ Failed to start chatbot service: {e}")
        return False

def cleanup_chatbot():
    """Terminate chatbot service on shutdown"""
    global _chatbot_process
    if _chatbot_process:
        logger.info("🛑 Stopping chatbot service...")
        try:
            _chatbot_process.terminate()
            _chatbot_process.wait(timeout=5)
            logger.info("✅ Chatbot service stopped")
        except Exception as e:
            logger.warning(f"Error stopping chatbot: {e}")
            try:
                _chatbot_process.kill()
            except:
                pass

# Register cleanup handler
atexit.register(cleanup_chatbot)


def create_app():
    """
    Application factory: creates and configures the Dash app instance.
    
    This function:
    1. Creates Flask server
    2. Registers API endpoints
    3. Creates Dash application
    4. Imports and sets layout
    5. Registers callbacks
    6. Returns configured app
    
    Returns:
        dash.Dash: Configured Dash application ready to run
    """
    logger.info("=" * 70)
    logger.info("Creating Financial Dashboard Application")
    logger.info("=" * 70)
    
    # ========================================================================
    # STEP 0: Start Chatbot Service
    # ========================================================================
    logger.info("Step 0: Starting chatbot service...")
    chatbot_available = start_chatbot_service()
    if chatbot_available:
        logger.info("✅ Chatbot service is available")
    else:
        logger.warning("⚠️ Chatbot service not available - chatbot features may not work")
    
    # ========================================================================
    # STEP 1: Create Flask Server
    # ========================================================================
    logger.info("Step 1: Creating Flask server...")
    server = Flask(__name__)
    server.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Load environment variables
    try:
        from .utils.load_env import load_environment
        env_status = load_environment(raise_on_missing=False)
        logger.info(f"Environment status: valid={env_status.get('valid')}, sources={env_status.get('sources')}")
    except Exception as e:
        logger.warning(f"Could not load environment: {e}")
    
    # ========================================================================
    # STEP 2: Register API Endpoints
    # ========================================================================
    logger.info("Step 2: Registering API endpoints...")
    
    import pandas as pd
    import time
    
    @server.route('/api/weekly_picks')
    def api_weekly_picks():
        """JSON API endpoint for weekly picks data - PostgreSQL Integration"""
        logger.info("📡 API Request: /api/weekly_picks")
        
        # Prefer JSON fallback (repo-level `data/picks/weekly_picks.json`) when available
        try:
            json_path = os.path.normpath(os.path.join(APP_DIR, '..', 'data', 'picks', 'weekly_picks.json'))
            if os.path.exists(json_path):
                with open(json_path, 'r') as jf:
                    json_data = json.load(jf)
                records = json_data.get('data', [])
                # Default to 20 when limit not provided
                limit_arg = request.args.get('limit')
                try:
                    if limit_arg is not None:
                        limit_val = int(limit_arg)
                    else:
                        limit_val = 20
                except Exception:
                    limit_val = 20

                selected = records[:limit_val]
                # Clean NaN-like values if any
                import math
                for rec in selected:
                    for k, v in list(rec.items()):
                        if v is None:
                            rec[k] = None
                        # no-op: assume JSON already serializable

                tickers = [r.get('ticker') or r.get('Ticker') for r in selected]
                return jsonify({
                    'status': 'success',
                    'count': len(selected),
                    'tickers': tickers,
                    'week_start_date': selected[0].get('week_start_date') if selected else None,
                    'data': selected,
                    'timestamp': time.time(),
                    'source': 'json_fallback'
                })
        except Exception:
            # If JSON fallback fails, continue to DB-backed path
            pass

        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'financial_dashboard'),
            'user': os.getenv('POSTGRES_USER', 'dashboard_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'newpassword')
        }
        
        try:
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Respect `limit` query param; default to 20 when omitted to match UI expectations
            limit_arg = request.args.get('limit')
            try:
                if limit_arg is not None:
                    limit_val = int(limit_arg)
                    if limit_val <= 0:
                        limit_val = 20
                else:
                    limit_val = 20
            except Exception:
                limit_val = 20

            query = f"""
                SELECT week_start_date, ticker, rank, rationale,
                       momentum_score, sentiment_score, fundamental_score,
                       combined_score, chart_array, metadata, generated_at
                FROM weekly_picks_production
                WHERE week_start_date = (SELECT MAX(week_start_date) FROM weekly_picks_production)
                ORDER BY rank ASC
                LIMIT {limit_val}
            """
            
            cursor.execute(query)
            picks = cursor.fetchall()
            cursor.close()
            conn.close()

            # If the DB returned fewer than the desired limit, try JSON fallback
            if not picks or len(picks) < limit_val:
                try:
                    # Resolve to repo-level data directory (repo_root/data/picks/...)
                    json_path = os.path.normpath(os.path.join(APP_DIR, '..', 'data', 'picks', 'weekly_picks.json'))
                    if os.path.exists(json_path):
                        with open(json_path, 'r') as jf:
                            json_data = json.load(jf)
                        json_records = json_data.get('data', [])
                        if len(json_records) >= limit_val:
                            # Use JSON file (top records) when it has sufficient picks
                            picks = []
                            for rec in json_records[:limit_val]:
                                picks.append({
                                    'week_start_date': rec.get('week_start_date'),
                                    'ticker': rec.get('ticker') or rec.get('Ticker'),
                                    'rank': rec.get('rank'),
                                    'rationale': rec.get('rationale'),
                                    'momentum_score': rec.get('momentum_score'),
                                    'sentiment_score': rec.get('sentiment_score'),
                                    'fundamental_score': rec.get('fundamental_score'),
                                    'combined_score': rec.get('combined_score'),
                                    'chart_array': rec.get('chart_array'),
                                    'metadata': rec.get('metadata'),
                                    'generated_at': rec.get('generated_at')
                                })
                except Exception:
                    # If fallback fails, continue with DB results (even if empty)
                    pass

            if not picks:
                return jsonify({
                    'status': 'error',
                    'message': 'No weekly picks data available',
                    'tickers': [],
                    'count': 0
                }), 404

            picks_data = []
            tickers = []

            for pick in picks:
                tickers.append(pick['ticker'])
                picks_data.append({
                    'rank': pick['rank'],
                    'ticker': pick['ticker'],
                    'combined_score': float(pick['combined_score']),
                    'momentum_score': float(pick['momentum_score']),
                    'sentiment_score': float(pick['sentiment_score']),
                    'fundamental_score': float(pick['fundamental_score']),
                    'rationale': pick['rationale'],
                    'chart_array': pick['chart_array'],
                    'metadata': pick['metadata'],
                    'week_start_date': pick['week_start_date'].isoformat() if pick['week_start_date'] else None,
                    'generated_at': pick['generated_at'].isoformat() if pick['generated_at'] else None
                })
            
            return jsonify({
                'status': 'success',
                'count': len(picks_data),
                'tickers': tickers,
                'week_start_date': picks[0]['week_start_date'].isoformat() if picks[0]['week_start_date'] else None,
                'data': picks_data,
                'timestamp': time.time(),
                'source': 'postgresql_production'
            })
            
        except Exception as e:
            logger.exception("Error in /api/weekly_picks endpoint")
            return jsonify({
                'status': 'error',
                'message': str(e),
                'tickers': [],
                'count': 0
            }), 500

    @server.route('/api/jobs/<job_id>', methods=['GET'])
    def api_get_job_status(job_id):
        """Return job status/result for a given job_id.

        This endpoint is provided for compatibility with E2E tests that poll
        the `/api/jobs/{job_id}` path. It prefers the in-process shared job
        registry (`financial_dashboard._shared.get_job_status`) when available,
        and falls back to reading any `/tmp/<job_id>_result.json` file written
        by background jobs.
        """
        try:
            # Prefer in-process shared registry if available
            try:
                import financial_dashboard._shared as SH_local
                if hasattr(SH_local, 'get_job_status'):
                    st = SH_local.get_job_status(job_id)
                    if st is None:
                        # try tmp file fallback
                        fn = f'/tmp/{job_id}_result.json'
                        if os.path.exists(fn):
                            with open(fn, 'r', encoding='utf-8') as fh:
                                data = json.load(fh)
                            return jsonify(data)
                        return jsonify({'error': f'Job {job_id} not found'}), 404
                    return jsonify(st)
            except Exception:
                # continue to fallback
                pass

            # Fallback to reading saved result file
            fn = f'/tmp/{job_id}_result.json'
            if os.path.exists(fn):
                with open(fn, 'r', encoding='utf-8') as fh:
                    data = json.load(fh)
                return jsonify(data)

            return jsonify({'error': f'Job {job_id} not found'}), 404

        except Exception as e:
            logger.exception('Error in /api/jobs/<job_id>')
            return jsonify({'error': str(e)}), 500
    
    @server.route('/api/monthly_picks')
    def api_monthly_picks():
        """JSON API endpoint for monthly picks data."""
        logger.info("📡 API Request: /api/monthly_picks")
        try:
            sys.path.insert(0, os.path.join(APP_DIR, 'tabs'))
            from monthly_picks import _load_and_enrich_picks
            
            result = _load_and_enrich_picks()
            picks_df = result[0] if isinstance(result, tuple) else result
            
            if picks_df is None or picks_df.empty:
                return jsonify({
                    'status': 'error',
                    'message': 'No monthly picks data available',
                    'tickers': [],
                    'count': 0
                }), 404
            
            records = picks_df.to_dict('records')
            for record in records:
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
            
            return jsonify({
                'status': 'success',
                'count': len(records),
                'tickers': list(picks_df.get('Ticker', picks_df.get('ticker', [])).values),
                'data': records,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.exception("Error in /api/monthly_picks endpoint")
            return jsonify({
                'status': 'error',
                'message': str(e),
                'tickers': [],
                'count': 0
            }), 500
    
    @server.route('/api/portfolio_summary')
    def api_portfolio_summary():
        """JSON API endpoint for portfolio summary data."""
        logger.info("📡 API Request: /api/portfolio_summary")
        try:
            from alpaca.trading.client import TradingClient
            
            key = os.getenv("APCA_API_KEY_ID") or os.getenv('APCA_API_KEY')
            secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv('APCA_API_SECRET')
            
            if not key or not secret:
                return jsonify({
                    'status': 'error',
                    'message': 'Alpaca client not available',
                    'data': {}
                }), 503
            
            client = TradingClient(key, secret, paper=True)
            account = client.get_account()
            positions = client.get_all_positions()
            
            position_data = []
            for pos in positions:
                position_data.append({
                    'ticker': pos.symbol,
                    'qty': float(pos.qty),
                    'current_price': float(pos.current_price),
                    'market_value': float(pos.market_value),
                    'cost_basis': float(pos.cost_basis),
                    'unrealized_pl': float(pos.unrealized_pl),
                    'unrealized_plpc': float(pos.unrealized_plpc) * 100,
                    'side': pos.side
                })
            
            summary = {
                'portfolio_value': float(account.equity),
                'cash': float(account.cash),
                'buying_power': float(account.buying_power),
                'total_pl': sum(float(p.unrealized_pl) for p in positions),
                'total_pl_pct': (sum(float(p.unrealized_pl) for p in positions) / float(account.equity) * 100) if float(account.equity) > 0 else 0,
                'positions_count': len(positions)
            }
            
            return jsonify({
                'status': 'success',
                'summary': summary,
                'data': position_data,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.exception("Error in /api/portfolio_summary endpoint")
            return jsonify({
                'status': 'error',
                'message': str(e),
                'data': {}
            }), 500
    
    logger.info("✅ Registered API endpoints: /api/weekly_picks, /api/monthly_picks, /api/portfolio_summary")
    
    # Register Research API Blueprint
    try:
        # Import from project root api/ directory
        import sys
        project_root = os.path.dirname(os.path.dirname(APP_DIR))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)
        
        from api.research import research_bp
        server.register_blueprint(research_bp)
        logger.info("✅ Registered Research API Blueprint: /api/research/*")
    except Exception as e:
        logger.warning(f"Could not register Research API: {e}")
    
    # Register Market Forecast API Blueprint (Agent-1B)
    try:
        from financial_dashboard.api.market_forecast import market_forecast_api
        server.register_blueprint(market_forecast_api)
        logger.info("✅ Registered Market Forecast API: /api/market_forecast/*")
    except Exception as e:
        logger.warning(f"Could not register Market Forecast API: {e}")
    
    # Register Volatility Surface API Blueprint (Agent-1B)
    try:
        from financial_dashboard.api.volsurface import register_blueprints as register_vol_blueprints
        register_vol_blueprints(server)
        logger.info("✅ Registered Volatility Surface API: /api/volsurface/*, /admin/vollab/*")
    except Exception as e:
        logger.warning(f"Could not register Volatility Surface API: {e}")
    
    # Register Options Forecast API Blueprint (Agent-1A Phase 31 STEP 3)
    try:
        from financial_dashboard.api.options_forecast import options_forecast_api
        server.register_blueprint(options_forecast_api)
        logger.info("✅ Registered Options Forecast API: /api/options/forecast")
    except Exception as e:
        logger.warning(f"Could not register Options Forecast API: {e}")
    
    # Register Options Backtest API Blueprint (Agent-1A Phase 31 STEP 9)
    try:
        from financial_dashboard.api.options_backtest import backtest_bp
        server.register_blueprint(backtest_bp)
        logger.info("✅ Registered Options Backtest API: /api/options/backtest/*")
    except Exception as e:
        logger.warning(f"Could not register Options Backtest API: {e}")
    
    # Register Picks Pipeline API Blueprint (Picks Rebuild - Agent-1B)
    try:
        from financial_dashboard.api.picks_pipeline_api import register_picks_api
        register_picks_api(server)
        logger.info("✅ Registered Picks Pipeline API: /api/picks/*")
    except Exception as e:
        logger.warning(f"Could not register Picks Pipeline API: {e}")
    
    # Register Command Center API Blueprint (Agent Engineer - CC Rebuild)
    try:
        from financial_dashboard.api.cc import register_cc_api
        register_cc_api(server)
        logger.info("✅ Registered Command Center API: /api/cc/*")
    except Exception as e:
        logger.warning(f"Could not register Command Center API: {e}")
    
    # Register Command Center Admin API Blueprint (Agent Engineer - CC Rebuild)
    try:
        from financial_dashboard.admin.cc_admin import register_cc_admin
        register_cc_admin(server)
        logger.info("✅ Registered Command Center Admin API: /admin/cc/*")
    except Exception as e:
        logger.warning(f"Could not register Command Center Admin API: {e}")
    
    # Register Callback Map Admin Endpoint (STEP A - System Fix)
    # This endpoint will be populated after app creation and callback registration
    # We'll register the endpoint now and it will access app.callback_map at runtime
    _callback_map_app_ref = {'app': None}  # Will be set after Dash app creation
    
    @server.route('/admin/callback_map')
    def admin_callback_map():
        """Return the current callback map for duplicate detection."""
        try:
            app = _callback_map_app_ref.get('app') or server.config.get('DASH_APP')
            if not app:
                return jsonify({
                    'status': 'error',
                    'error': 'Dash app not initialized yet'
                }), 503
            
            callback_map = getattr(app, 'callback_map', {})
            
            # Build output ID to callback mapping
            output_id_to_callbacks = {}
            duplicate_outputs = []
            
            for callback_id, callback_spec in callback_map.items():
                # Extract outputs
                outputs = callback_spec.get('output', [])
                if not isinstance(outputs, list):
                    outputs = [outputs]
                
                for output in outputs:
                    # Get output ID string
                    if hasattr(output, 'component_id') and hasattr(output, 'component_property'):
                        output_id = f"{output.component_id}.{output.component_property}"
                    else:
                        output_id = str(output)
                    
                    if output_id not in output_id_to_callbacks:
                        output_id_to_callbacks[output_id] = []
                    output_id_to_callbacks[output_id].append(callback_id)
            
            # Find duplicates
            for output_id, callback_ids in output_id_to_callbacks.items():
                if len(callback_ids) > 1:
                    duplicate_outputs.append({
                        'output_id': output_id,
                        'count': len(callback_ids),
                        'callback_ids': callback_ids
                    })
            
            return jsonify({
                'status': 'success',
                'total_callbacks': len(callback_map),
                'callback_ids': list(callback_map.keys())[:500],  # Truncate for size
                'duplicate_outputs': duplicate_outputs,
                'duplicate_count': len(duplicate_outputs),
                'output_id_counts': {k: len(v) for k, v in output_id_to_callbacks.items() if len(v) > 1},
                'app_id': id(app),
                'app_type': str(type(app))
            })
            
        except Exception as e:
            logger.exception("Error in /admin/callback_map")
            import traceback
            return jsonify({
                'status': 'error',
                'error': str(e),
                'traceback': traceback.format_exc()
            }), 500
    
    logger.info("✅ Registered Callback Map Admin API: /admin/callback_map")
    
    # Register System Health Endpoint (STEP D - Observability)
    @server.route('/health/systemfix')
    def health_systemfix():
        """Comprehensive system health check for systemfix validation."""
        import time
        import psutil
        from datetime import datetime
        
        try:
            app = _callback_map_app_ref.get('app') or server.config.get('DASH_APP')
            
            # Collect system metrics
            health_status = {
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'uptime_seconds': time.time() - server.config.get('START_TIME', time.time()),
                'system': {
                    'cpu_percent': psutil.cpu_percent(interval=0.1),
                    'memory_percent': psutil.virtual_memory().percent,
                    'disk_percent': psutil.disk_usage('/').percent
                },
                'dash_app': {
                    'initialized': app is not None,
                    'callback_count': len(getattr(app, 'callback_map', {})) if app else 0,
                    'app_type': str(type(app).__name__) if app else 'None'
                },
                'services': {
                    'market_sentiment_poller': 'running',  # Check if thread alive
                    'cache_manager': 'available'
                },
                'endpoints_tested': {
                    'callback_map': '/admin/callback_map',
                    'market_sentiment': '/api/cc/market_sentiment',
                    'market_trends_health': '/api/market_trends/health'
                }
            }
            
            # Check for any critical issues
            if health_status['system']['memory_percent'] > 90:
                health_status['status'] = 'degraded'
                health_status['warnings'] = ['High memory usage']
            
            return jsonify(health_status)
            
        except Exception as e:
            logger.exception("Error in /health/systemfix")
            return jsonify({
                'status': 'unhealthy',
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }), 500
    
    # Store startup time for uptime calculation
    server.config['START_TIME'] = time.time()
    logger.info("✅ Registered System Health API: /health/systemfix")
    
    # Register Market Trends Admin API Endpoints (P2 - Full Implementation)
    # Make registration robust: even if CacheManager or other imports fail,
    # still register routes and handle missing cache gracefully.
    from financial_dashboard._shared import SH  # may raise, let it bubble if critical
    try:
        from financial_dashboard.utils.cache_manager import CacheManager
        mt_cache = CacheManager(
            cache_file='market_trends_cache.json',
            cache_dir=os.path.join(APP_DIR, 'cache')
        )
    except Exception:
        logger.warning("Could not initialize Market Trends CacheManager; using fallback (in-memory)")
        mt_cache = None

    @server.route('/api/market_trends/brief', methods=['GET'])
    def api_market_trends_brief():
        """Get cached market trends data (brief summary)"""
        logger.info("📡 API Request: GET /api/market_trends/brief")
        try:
            cached = {}
            if mt_cache:
                try:
                    cached = mt_cache.load_from_disk() or {}
                except Exception as e:
                    logger.debug(f"mt_cache.load_from_disk failed: {e}")

            if not cached or not cached.get('detailed'):
                return jsonify({
                    'status': 'empty',
                    'message': 'No market trends data available',
                    'data': {}
                }), 404

            # Return summary
            return jsonify({
                'status': 'success',
                'data': {
                    'market_trend': cached.get('market_trend', {}),
                    'ticker_count': cached.get('success_count', 0),
                    'tickers': cached.get('tickers', []),
                    'generated_at': cached.get('generated_at'),
                    'cache_age_seconds': time.time() - cached.get('timestamp', time.time())
                },
                'timestamp': time.time()
            })
        except Exception as e:
            logger.exception("Error in /api/market_trends/brief")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @server.route('/api/market_trends/refresh', methods=['POST'])
    def api_market_trends_refresh():
        """Trigger background refresh of market trends data"""
        logger.info("📡 API Request: POST /api/market_trends/refresh")
        try:
            # Get tickers from request or use defaults
            data = request.get_json(silent=True) or {}
            tickers = data.get('tickers', 'SPY,QQQ,IWM,DIA,AAPL,MSFT,GOOGL,TSLA')
            period = data.get('period', '1mo')
            include_news = data.get('include_news', True)

            # Import run_full_analysis from market_trends
            from financial_dashboard.tabs.market_trends import run_full_analysis

            # Start background job
            job_id = SH.start_background_job(
                target=run_full_analysis,
                kwargs={
                    'tickers_str': tickers,
                    'period': period,
                    'include_news': include_news,
                    'include_options': False
                }
            )

            logger.info(f"✅ Started market trends refresh job: {job_id}")

            return jsonify({
                'status': 'started',
                'job_id': job_id,
                'message': 'Market trends refresh job started',
                'tickers': tickers.split(','),
                'timestamp': time.time()
            })
        except Exception as e:
            logger.exception("Error in /api/market_trends/refresh")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    @server.route('/api/market_trends/health', methods=['GET'])
    def api_market_trends_health():
        """Health check for market trends system"""
        logger.info("📡 API Request: GET /api/market_trends/health")
        try:
            cached = {}
            if mt_cache:
                try:
                    cached = mt_cache.load_from_disk() or {}
                except Exception as e:
                    logger.debug(f"mt_cache.load_from_disk failed: {e}")

            if not cached:
                return jsonify({
                    'status': 'unhealthy',
                    'message': 'No cache data available',
                    'cache_exists': False,
                    'timestamp': time.time()
                }), 503

            cache_age = time.time() - cached.get('timestamp', 0)
            is_stale = cache_age > 3600  # 1 hour

            return jsonify({
                'status': 'healthy' if not is_stale else 'stale',
                'cache_exists': True,
                'cache_age_seconds': cache_age,
                'cache_age_human': f"{cache_age // 60:.0f} minutes" if cache_age < 3600 else f"{cache_age // 3600:.1f} hours",
                'ticker_count': cached.get('success_count', 0),
                'last_update': cached.get('generated_at'),
                'is_stale': is_stale,
                'timestamp': time.time()
            })
        except Exception as e:
            logger.exception("Error in /api/market_trends/health")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500

    logger.info("✅ Registered Market Trends Admin API: /api/market_trends/brief, /refresh, /health")
    
    # Register Picks API (weekly/monthly) if available
    try:
        from financial_dashboard.api.picks_api import register_picks_api_routes
        register_picks_api_routes(server)
        logger.info("✅ Registered Picks API routes: /api/weekly_picks, /api/monthly_picks, /api/picks/reload, /api/picks/health")
    except Exception as e:
        logger.warning(f"Could not register Picks API: {e}")
    
    # Register Chat API Blueprint (RAG Chat Assistant)
    try:
        from financial_dashboard.api.chat import register_chat_api
        register_chat_api(server)
        logger.info("✅ Registered Chat API: /api/chat/*")
    except Exception as e:
        logger.warning(f"Could not register Chat API: {e}")
        logger.warning(f"Could not register Picks API routes: {e}")
    # ========================================================================
    # STEP 3: Create Dash Application
    # ========================================================================
    logger.info("Step 3: Creating Dash application...")
    
    # Prefer DashProxy + MultiplexerTransform when available to safely
    # allow multiple callbacks to target the same Output (reduces
    # 'Duplicate callback outputs' client errors). Fall back to
    # the regular Dash class if the package is not installed.
    try:
        from dash_extensions.enrich import DashProxy, MultiplexerTransform
        use_proxy = True
    except Exception:
        DashProxy = None
        MultiplexerTransform = None
        use_proxy = False

    if use_proxy and DashProxy is not None and MultiplexerTransform is not None:
        app = DashProxy(
            name=__name__,
            server=server,
            external_stylesheets=[
                dbc.themes.BOOTSTRAP,
                "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"  # Font Awesome for chatbot icons
            ],
            suppress_callback_exceptions=True,
            url_base_pathname='/',
            serve_locally=True,
            transforms=[MultiplexerTransform()]
        )
    else:
        app = dash.Dash(
            name=__name__,
            server=server,
            external_stylesheets=[
                dbc.themes.BOOTSTRAP,
                "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css"  # Font Awesome for chatbot icons
            ],
            suppress_callback_exceptions=True,
            url_base_pathname='/',
            serve_locally=True
        )
    
    app.title = "Financial Dashboard"
    
    # ========================================================================
    # INSTRUMENTATION: Trace callback registrations for duplicate detection
    # ========================================================================
    logger.info("Instrumenting callback registration tracking...")
    try:
        from .utils.callback_instrumentation import instrument_dash_app
        instrument_dash_app(app)
        logger.info("✅ Callback instrumentation active")
    except ImportError:
        from utils.callback_instrumentation import instrument_dash_app
        instrument_dash_app(app)
        logger.info("✅ Callback instrumentation active")
    except Exception as e:
        logger.warning(f"⚠️ Callback instrumentation failed: {e}")
    
    # Store Dash app instance in Flask config for admin diagnostics endpoints (Agent-1A)
    server.config['DASH_APP'] = app
    _callback_map_app_ref['app'] = app  # Also store in closure for /admin/callback_map endpoint
    
    # Configure cache control
    @server.after_request
    def set_cache_control(response):
        """Set cache control headers for Dash endpoints."""
        if request.path in ['/_dash-dependencies', '/_dash-layout', '/_dash-update-component']:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        return response
    
    logger.info("✅ Dash application created")
    
    # ========================================================================
    # STEP 4: Import and Set Layout
    # ========================================================================
    logger.info("Step 4: Setting application layout...")
    
    try:
        # Import index module (loads tabs)
        try:
            from . import index as index_module
        except ImportError:
            import index as index_module
        
        # Create layout
        layout = index_module.create_layout()
        
        # Sanitize layout to prevent React errors
        logger.info("Sanitizing layout to prevent React rendering errors...")
        try:
            from .utils.component_sanitizer import sanitize_layout
            layout = sanitize_layout(layout)
        except ImportError:
            from utils.component_sanitizer import sanitize_layout
            layout = sanitize_layout(layout)
        
        # Set sanitized layout
        app.layout = layout
        
        logger.info(f"✅ Layout set with {len(index_module.ENABLED_TABS)} tabs")
        
    except Exception as e:
        logger.error(f"❌ Failed to set layout: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        # Set fallback layout
        from dash import html
        app.layout = html.Div([
            html.H1("Dashboard Loading Error"),
            html.P(f"Error: {str(e)}"),
            html.P("Please check the logs for details.")
        ])
    
    # ========================================================================
    # STEP 5: Register Callbacks
    # ========================================================================
    logger.info("Step 5: Registering callbacks...")
    
    try:
        # Import callbacks module using absolute package path to avoid
        # resolving to an unrelated top-level module named `callbacks`.
        from financial_dashboard import callbacks as callbacks_module
        
        # Register all callbacks
        callback_count = callbacks_module.register_all_callbacks(
            app,
            loaded_tabs=index_module.loaded_tabs,
            SH=index_module.SH,
            CHATBOT_AVAILABLE=index_module.CHATBOT_AVAILABLE,
            enabled_tabs=index_module.ENABLED_TABS  # CRITICAL: Only register enabled tabs
        )
        
        logger.info(f"✅ Registered {callback_count} callbacks")
        
    except Exception as e:
        logger.error(f"❌ Failed to register callbacks: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.warning("⚠️ Dashboard will run with limited functionality")
    
    # ========================================================================
    # STEP 6: Start Background Services (Command Center)
    # ========================================================================
    logger.info("Step 6: Starting background services...")
    
    # Start market sentiment poller (Command Center)
    try:
        from background.market_sentiment_poller import start_poller, get_poller_status
        start_poller()
        status = get_poller_status()
        logger.info(f"✅ Market sentiment poller started: {status}")
    except Exception as e:
        logger.warning(f"Could not start market sentiment poller: {e}")
    
    # ========================================================================
    # STEP 7: Return Configured App
    # ========================================================================
    logger.info("=" * 70)
    logger.info("✅ Application created successfully!")
    logger.info("=" * 70)
    
    return app


# Do NOT create the Dash app at import time. Callers should invoke
# `create_app()` to get a configured application instance. Creating the
# app during module import caused duplicate callback registrations when
# the factory was invoked more than once in the same process.

# CRITICAL FIX: Do NOT create app at module level - prevents duplicates
# The app instance should ONLY be created by the calling script (index.py)
app = None
server = None

# NOTE: This module should NOT be run directly with `python -m financial_dashboard.app`
# Instead, run `python -m financial_dashboard.index` or `python financial_dashboard/index.py`
# The __main__ block below is disabled to prevent duplicate app creation.

# DISABLED: This was causing duplicate callback registrations
# if __name__ == '__main__':
#     import os
#     port = int(os.getenv('PORT', 8090))
#     debug = os.getenv('DEBUG', 'False').lower() == 'true'
#
#     print(f"\n{'='*70}")
#     print(f"🚀 Starting Financial Dashboard on http://localhost:{port}")
#     print(f"{'='*70}\n")
#
#     # Create and run the app only when executed directly
#     app = create_app()
#     server = app.server
#     app.run(debug=debug, host='0.0.0.0', port=port)
