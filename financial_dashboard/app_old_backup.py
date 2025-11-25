"""
Financial Dashboard - Dash Application Factory
Creates and configures the main DashProxy instance.
Sprint 0: Clean modular architecture
"""
import os
import sys
import json
import logging
import dash
import dash_bootstrap_components as dbc
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Setup paths
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Application version for cache invalidation
# Updated to force browser cache invalidation for Research Lab integration
DASHBOARD_VERSION = "v2025102701_research_lab"

def create_app():
    """
    Application factory: creates and configures the Dash app instance.
    
    Returns:
        DashProxy: Configured Dash application
    """
    # Create Flask server
    server = Flask(__name__)

    # Ensure environment variables (keys.env / doppler) are loaded for the server process
    try:
        # Import locally to avoid top-level dependency if utils missing
        from .utils.load_env import load_environment
        # Do not raise on missing here; we want the server to start and surface missing keys via logs
        env_status = load_environment(raise_on_missing=False)
        logger.info(f"Environment loader status on app startup: valid={env_status.get('valid')}, sources={env_status.get('sources')}")
    except Exception as e:
        logger.warning(f"Could not pre-load environment in create_app(): {e}")
    
    # ============================================================================
    # AGENT 1B FIX: Register API endpoints BEFORE Dash initialization
    # This ensures they take precedence over Dash's catch-all routing
    # ============================================================================
    import pandas as pd
    import time
    from flask import jsonify
    
    @server.route('/api/weekly_picks')
    def api_weekly_picks():
        """JSON API endpoint for weekly picks data - Phase 14 PostgreSQL Integration"""
        logger.info("📡 API Request: /api/weekly_picks (PostgreSQL)")
        
        import psycopg2
        from psycopg2.extras import RealDictCursor
        
        # Database connection config
        db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': int(os.getenv('POSTGRES_PORT', 5432)),
            'database': os.getenv('POSTGRES_DB', 'financial_dashboard'),
            'user': os.getenv('POSTGRES_USER', 'dashboard_user'),
            'password': os.getenv('POSTGRES_PASSWORD', 'newpassword')
        }
        
        try:
            # Connect to PostgreSQL
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            # Query latest weekly picks from production table
            query = """
                SELECT 
                    week_start_date,
                    ticker,
                    rank,
                    rationale,
                    momentum_score,
                    sentiment_score,
                    fundamental_score,
                    combined_score,
                    chart_array,
                    metadata,
                    generated_at
                FROM weekly_picks_production
                WHERE week_start_date = (
                    SELECT MAX(week_start_date) 
                    FROM weekly_picks_production
                )
                ORDER BY rank ASC
            """
            
            cursor.execute(query)
            picks = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            if not picks:
                logger.warning("No weekly picks data available in PostgreSQL")
                return jsonify({
                    'status': 'error',
                    'message': 'No weekly picks data available',
                    'tickers': [],
                    'count': 0
                }), 404
            
            # Convert to JSON-serializable format
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
                    'chart_array': pick['chart_array'],  # Already JSON from JSONB column
                    'metadata': pick['metadata'],
                    'week_start_date': pick['week_start_date'].isoformat() if pick['week_start_date'] else None,
                    'generated_at': pick['generated_at'].isoformat() if pick['generated_at'] else None
                })
            
            logger.info(f"✅ Returning {len(picks_data)} weekly picks from PostgreSQL")
            return jsonify({
                'status': 'success',
                'count': len(picks_data),
                'tickers': tickers,
                'week_start_date': picks[0]['week_start_date'].isoformat() if picks[0]['week_start_date'] else None,
                'data': picks_data,
                'timestamp': time.time(),
                'source': 'postgresql_production'
            })
            
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL error in /api/weekly_picks: {e}")
            return jsonify({
                'status': 'error',
                'message': f'Database error: {str(e)}',
                'tickers': [],
                'count': 0
            }), 500
        except Exception as e:
            logger.exception("Error in /api/weekly_picks endpoint")
            return jsonify({
                'status': 'error',
                'message': str(e),
                'tickers': [],
                'count': 0
            }), 500

    @server.route('/api/monthly_picks')
    def api_monthly_picks():
        """JSON API endpoint for monthly picks data."""
        logger.info("📡 API Request: /api/monthly_picks")
        try:
            import sys
            import os as _os
            tabs_dir = _os.path.join(_os.path.dirname(__file__), 'tabs')
            if tabs_dir not in sys.path:
                sys.path.insert(0, tabs_dir)
            
            from monthly_picks import _find_latest_monthly_picks, _load_and_enrich_picks
            
            # Load the latest monthly picks CSV and enrich with live prices
            # _load_and_enrich_picks returns (df, error, summary)
            result = _load_and_enrich_picks()
            picks_df = result[0] if isinstance(result, tuple) else result
            
            if picks_df is None or picks_df.empty:
                logger.warning("No monthly picks data available")
                return jsonify({
                    'status': 'error',
                    'message': 'No monthly picks data available',
                    'tickers': [],
                    'count': 0
                }), 404
            
            # Convert to JSON-serializable format
            records = picks_df.to_dict('records')
            
            # Clean up NaN values
            for record in records:
                for key, value in record.items():
                    if pd.isna(value):
                        record[key] = None
            
            logger.info(f"✅ Returning {len(records)} monthly picks")
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
            # Try to get portfolio data from Alpaca
            import os
            from alpaca.trading.client import TradingClient
            
            def get_alpaca_client():
                """Get Alpaca trading client from environment."""
                key = os.getenv("APCA_API_KEY_ID") or os.getenv('APCA_API_KEY')
                secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv('APCA_API_SECRET')
                if not key or not secret:
                    return None
                # Default to paper trading
                paper = True
                return TradingClient(key, secret, paper=paper)
            
            client = get_alpaca_client()
            if not client:
                logger.warning("Alpaca client not available")
                return jsonify({
                    'status': 'error',
                    'message': 'Alpaca client not available',
                    'data': {}
                }), 503
            
            # Fetch account and positions
            account = client.get_account()
            positions = client.get_all_positions()
            
            # Build position data
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
            
            logger.info(f"✅ Returning portfolio with {len(position_data)} positions")
            # Attempt to persist a server-side cache so server-rendered layouts
            # can show live values on first render without requiring an HTTP
            # round-trip from the layout code.
            try:
                from pathlib import Path
                from datetime import datetime
                import json as _json

                cache_dir = Path(__file__).parent.parent / 'cache'
                cache_dir.mkdir(parents=True, exist_ok=True)
                cache_path = cache_dir / 'portfolio_data.json'

                payload = {
                    'positions': position_data,
                    'account': {
                        'portfolio_value': float(summary.get('portfolio_value', 0.0)),
                        'equity': float(summary.get('portfolio_value', 0.0)),
                        'buying_power': float(summary.get('buying_power', 0.0)),
                        'cash': float(summary.get('cash', 0.0))
                    },
                    'timestamp': datetime.now().isoformat()
                }

                tmp_path = str(cache_path) + '.tmp'
                with open(tmp_path, 'w') as _f:
                    _json.dump(payload, _f)
                # atomic replace
                import os as _os
                _os.replace(tmp_path, str(cache_path))
                logger.info(f"Saved portfolio cache to {cache_path}")
            except Exception as _e:
                logger.warning(f"Failed to write portfolio cache: {_e}")

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
    
    # =========================================================================
    # ML ENDPOINTS - Phase 13 Local ML Integration
    # =========================================================================
    
    @server.route('/ml/predict', methods=['POST'])
    def ml_predict():
        """ML inference endpoint for local models."""
        logger.info("📡 API Request: /ml/predict")
        try:
            # Import ML runner
            import sys
            from pathlib import Path
            ml_runner_path = Path(__file__).parent.parent
            if str(ml_runner_path) not in sys.path:
                sys.path.insert(0, str(ml_runner_path))
            
            from ml_runner import predict, initialize
            
            # Get request data
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'No JSON data provided'
                }), 400
            
            model_type = data.get('model')
            input_data = data.get('input')
            
            if not model_type or not input_data:
                return jsonify({
                    'status': 'error',
                    'message': 'Missing required fields: model, input'
                }), 400
            
            # Valid model types
            valid_models = ['forecast', 'clustering', 'strategy']
            if model_type not in valid_models:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid model type. Must be one of: {valid_models}'
                }), 400
            
            # Initialize ML runner (idempotent)
            initialize()
            
            # Run prediction
            result = predict(model_type, input_data)
            
            logger.info(f"✅ ML prediction complete: {model_type}")
            return jsonify({
                'status': 'success',
                'model': model_type,
                'result': result,
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.exception(f"Error in /ml/predict endpoint: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    @server.route('/ml/status', methods=['GET'])
    def ml_status():
        """Get ML system status and available models."""
        logger.info("📡 API Request: /ml/status")
        try:
            import sys
            from pathlib import Path
            ml_runner_path = Path(__file__).parent.parent
            if str(ml_runner_path) not in sys.path:
                sys.path.insert(0, str(ml_runner_path))
            
            from ml_runner import manager, config
            
            status = manager.get_status()
            
            return jsonify({
                'status': 'success',
                'ml_system': 'operational',
                'models': status,
                'config': {
                    'models_dir': str(config.models_dir),
                    'cache_db': str(config.cache_db),
                    'telemetry_db': str(config.telemetry_db)
                },
                'timestamp': time.time()
            })
            
        except Exception as e:
            logger.exception(f"Error in /ml/status endpoint: {e}")
            return jsonify({
                'status': 'error',
                'message': str(e),
                'ml_system': 'unavailable'
            }), 500
    
    # =========================================================================
    # PHASE 22B: TradingView Webhook Integration
    # =========================================================================
    
    @server.route('/api/tradingview', methods=['POST'])
    def tradingview_webhook():
        """
        TradingView webhook endpoint - receives trading signals.
        Phase 22B Enhancement: PostgreSQL storage + Sentry/Datadog observability.
        """
        logger.info("📡 API Request: /api/tradingview (POST)")
        
        # Phase 22B: Observability
        try:
            from observability.sentry_config import capture_exception, add_breadcrumb
            from observability.datadog_config import increment_counter, record_timing
            OBSERVABILITY_AVAILABLE = True
        except ImportError:
            OBSERVABILITY_AVAILABLE = False
            def capture_exception(*args, **kwargs): pass
            def add_breadcrumb(*args, **kwargs): pass
            def increment_counter(*args, **kwargs): pass
            def record_timing(*args, **kwargs): pass
        
        start_time = time.time()
        
        try:
            # Parse webhook payload
            data = request.get_json()
            if not data:
                return jsonify({
                    'status': 'error',
                    'message': 'No JSON data provided'
                }), 400
            
            # Extract signal fields
            ticker = data.get('ticker', data.get('symbol', 'UNKNOWN'))
            signal = data.get('signal', data.get('action', 'HOLD'))
            price = float(data.get('price', 0.0))
            strategy = data.get('strategy', 'webhook')
            confidence = float(data.get('confidence', 0.75))
            timestamp_str = data.get('timestamp', pd.Timestamp.now().isoformat())
            
            # Add breadcrumb
            if OBSERVABILITY_AVAILABLE:
                add_breadcrumb(
                    f"TradingView signal received: {ticker} {signal} @ ${price}",
                    category='webhook',
                    level='info'
                )
            
            # Store in PostgreSQL
            import psycopg2
            from datetime import datetime
            
            db_config = {
                'host': os.getenv('POSTGRES_HOST', 'localhost'),
                'port': int(os.getenv('POSTGRES_PORT', 5432)),
                'database': os.getenv('POSTGRES_DB', 'financial_dashboard'),
                'user': os.getenv('POSTGRES_USER', 'dashboard_user'),
                'password': os.getenv('POSTGRES_PASSWORD', 'newpassword')
            }
            
            conn = psycopg2.connect(**db_config)
            cursor = conn.cursor()
            
            # Create table if not exists
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tradingview_signals (
                    id SERIAL PRIMARY KEY,
                    ticker VARCHAR(20) NOT NULL,
                    signal VARCHAR(20) NOT NULL,
                    price NUMERIC(10, 2),
                    strategy VARCHAR(50),
                    confidence NUMERIC(5, 4),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Insert signal
            cursor.execute("""
                INSERT INTO tradingview_signals 
                (ticker, signal, price, strategy, confidence, timestamp, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                ticker.upper(),
                signal.upper(),
                price,
                strategy,
                confidence,
                timestamp_str,
                json.dumps(data)
            ))
            
            signal_id = cursor.fetchone()[0]
            conn.commit()
            cursor.close()
            conn.close()
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Emit metrics
            if OBSERVABILITY_AVAILABLE:
                increment_counter('dashboard.tradingview.webhook', tags=[f'signal:{signal}', f'ticker:{ticker}'])
                record_timing('dashboard.tradingview.webhook.latency', elapsed_ms)
            
            logger.info(f"✅ TradingView signal stored: {ticker} {signal} @ ${price} (ID: {signal_id})")
            
            return jsonify({
                'status': 'success',
                'signal_id': signal_id,
                'ticker': ticker,
                'signal': signal,
                'price': price,
                'timestamp': timestamp_str,
                'latency_ms': round(elapsed_ms, 2)
            }), 201
            
        except Exception as e:
            logger.exception(f"Error in /api/tradingview webhook: {e}")
            if OBSERVABILITY_AVAILABLE:
                capture_exception(e, context='tradingview_webhook')
                increment_counter('dashboard.tradingview.webhook.errors')
            
            return jsonify({
                'status': 'error',
                'message': str(e)
            }), 500
    
    logger.info("✅ Pre-registered API endpoints: /api/weekly_picks, /api/monthly_picks, /api/portfolio_summary")
    logger.info("✅ Pre-registered ML endpoints: /ml/predict, /ml/status")
    logger.info("✅ Pre-registered TradingView webhook: /api/tradingview (Phase 22B)")
    
    # Create Dash app with DashProxy for advanced features
    # CRITICAL FIX: Added MultiplexerTransform back - it's REQUIRED for allow_duplicate=True to work
    # The duplicate callback issue was elsewhere
    # PHASE 0 FIX: Force serve_locally=True to prevent Plotly.js CDN timeout errors
    app = dash.Dash(
        name=__name__,
        server=server,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
        url_base_pathname='/',
        serve_locally=True
    )
    
    app.title = "Financial Dashboard"
    
    # Development: disable aggressive caching for faster iteration
    try:
        server.send_file_max_age_default = 0
    except Exception:
        pass
    
    @server.after_request
    def _set_response_no_cache(response):
        """Mark responses as no-cache for development - MINIMAL approach."""
        try:
            # Only apply cache control to specific endpoints that need it
            if request.path in ['/_dash-dependencies', '/_dash-layout', '/_dash-update-component']:
                response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                response.headers['Pragma'] = 'no-cache'
                response.headers['Expires'] = '0'
            # Remove the problematic Clear-Site-Data header that causes console spam
        except Exception:
            pass
        return response
    
    logger.info("✓ Created Dash application instance")

    # Inject an early, tiny sentinel table into the page using document.write
    # so Playwright selectors that pick the first <table> will encounter a
    # TEMPORARILY DISABLED: Custom index_string might be interfering with eager loading
    # visible table before any server-rendered hidden/template tables. This
    # uses the Dash index_string to place the script early in the document
    # head so it executes during parse time.
    # try:
    #     app.index_string = """<!DOCTYPE html>
    # ... (rest of HTML) ...
    # """
    # except Exception:
    #     # Non-fatal: if index_string can't be set for some reason, continue
    #     # with the default behavior.
    #     pass
    
    # Use default Dash index_string for now to ensure eager loading works
    logger.info("✅ Using default Dash index_string to ensure eager loading")

    # ============================================================================
    # DEDUPLICATION HOOK - must be registered BEFORE any requests are made
    # ============================================================================
    @server.after_request
    def deduplicate_dependencies_response(response):
        """Intercept /_dash-dependencies responses and deduplicate them
        
        Dash allows duplicate outputs via allow_duplicate=True, which appends
        a hash suffix to the output signature. We only remove TRUE duplicates
        (same exact output signature), NOT intentional duplicates with different hashes.
        """
        # Only intercept the dependencies endpoint
        if request.path != '/_dash-dependencies':
            return response
        
        try:
            # Parse JSON from response
            data = json.loads(response.get_data(as_text=True))
            
            if isinstance(data, list):
                original_count = len(data)
                seen_outputs = set()
                unique_data = []
                
                for item in data:
                    # Get the FULL output signature including hash suffix
                    # Callbacks with allow_duplicate=True have @HASH appended
                    output_sig = item.get('output', '')
                    
                    # Only remove if we've seen the EXACT same signature
                    # (including hash suffix for allow_duplicate callbacks)
                    if output_sig not in seen_outputs:
                        seen_outputs.add(output_sig)
                        unique_data.append(item)
                    # else: skip - exact duplicate
                
                if original_count != len(unique_data):
                    logger.info(f"🔧 Deduplicated /_dash-dependencies response: {original_count} → {len(unique_data)} callbacks (removed {original_count - len(unique_data)} exact duplicates)")
                    # Create new response with deduplicated data
                    response.set_data(json.dumps(unique_data))
                    response.headers['Content-Length'] = len(response.get_data())
                    # CRITICAL: Disable caching for dependencies endpoint
                    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                    response.headers['Pragma'] = 'no-cache'
                    response.headers['Expires'] = '0'
        except Exception as e:
            logger.error(f"Failed to deduplicate dependencies response: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        return response
    
    logger.info("✅ Installed after_request hook to deduplicate /_dash-dependencies")

    # --- Startup pre-warm: attempt to populate portfolio_data.json cache ---
    # CRITICAL FIX: Delay prewarm until AFTER layout is set (moved to post-import)
    # The prewarm will be triggered after index.py sets app.layout
    # This avoids NoLayoutException during startup
    
    # ========================================================================
    # CRITICAL FIX: Set layout INSIDE create_app() to disable lazy loading
    # If we set it after create_app() returns, Dash has already configured
    # the renderer for lazy loading mode, which causes the loading screen issue
    # ========================================================================
    logger.info("🔵 Setting app.layout inside create_app() to force eager loading...")
    
    # Import index module here (after app is created but before returning)
    # This avoids circular import issues
    # CRITICAL FIX: Handle both package and script execution
    logger.info("🔵 About to import index module and set layout...")
    try:
        try:
            from . import index as index_module
            logger.info("✅ Successfully imported index module (relative import)")
        except ImportError:
            import index as index_module
            logger.info("✅ Successfully imported index module (absolute import)")
        
        logger.info("🔵 Calling create_layout()...")
        layout = index_module.create_layout()
        logger.info(f"✅ create_layout() returned: {type(layout)}")
        
        app.layout = layout
        logger.info(f"✅ [create_app()] Set app.layout with {len(index_module.ENABLED_TABS)} tabs (eager loading)")
    except Exception as e:
        logger.error(f"❌ Failed to set layout in create_app(): {e}")
        import traceback
        logger.error(traceback.format_exc())
        # Set a minimal fallback layout to prevent crashes
        from dash_extensions.enrich import html
        app.layout = html.Div([html.H1("Dashboard Loading Error"), html.P(str(e))])
    
    return app

# Singleton instance
app = create_app()
server = app.server

# BREAKING CIRCULAR IMPORT FIX:
# Import index module (this loads tab modules and creates layout function)
# CRITICAL FIX: Handle both package and script execution
try:
    from . import index  # noqa: E402, F401
except ImportError:
    import index  # noqa: E402, F401

# Register ALL callbacks BEFORE setting layout
logger.info("🔵 Registering callbacks...")

# 1. Register tab-specific callbacks via callbacks.py
from financial_dashboard import callbacks
try:
    _callback_count = callbacks.register_all_callbacks(
        app,
        loaded_tabs=index.loaded_tabs,
        SH=index.SH,
        CHATBOT_AVAILABLE=index.CHATBOT_AVAILABLE
    )
    logger.info(f"✅ Registered {_callback_count} tab callbacks")
except Exception as e:
    logger.warning(f"⚠️ Some tab callbacks failed to register: {e}")
    # Continue without all callbacks - basic dashboard will still work

# 2. Register global callbacks (search, theme, chatbot)
from financial_dashboard.index_callbacks_temp import register_global_callbacks
try:
    _global_count = register_global_callbacks(
        app,
        loaded_tabs=index.loaded_tabs,
        CHATBOT_AVAILABLE=index.CHATBOT_AVAILABLE
    )
    logger.info(f"✅ Registered {_global_count} global callbacks")
except Exception as e:
    logger.warning(f"⚠️ Some global callbacks failed to register: {e}")
    # Continue without all callbacks - basic dashboard will still work

# ============================================================================
# CRITICAL FIX: Force DashProxy to register all pending callbacks FIRST
# DashProxy uses lazy registration - decorators like @app.callback() don't
# immediately populate callback_map. We must call register_callbacks() BEFORE
# setting app.layout, otherwise React will fail to render components that
# reference callback outputs that don't exist yet.
# ============================================================================
logger.info("🔵 Forcing DashProxy to register pending callbacks...")
try:
    _before_count = len(getattr(app, 'callback_map', {}))
    logger.info(f"📊 Callback map BEFORE registration: {_before_count} entries")
    
    # Standard Dash handles callback registration automatically
    # app.register_callbacks()  # Not needed for standard Dash
    
    _after_count = len(getattr(app, 'callback_map', {}))
    logger.info(f"📊 Callback map AFTER registration: {_after_count} entries")
    
    # ========================================================================
    # CRITICAL FIX: Deduplicate callbacks in callback_map AND dependencies endpoint
    # DashProxy creates duplicate entries - remove them to prevent React errors
    # ========================================================================
    if hasattr(app, 'callback_map') and app.callback_map:
        original_count = len(app.callback_map)
        seen_outputs = {}
        duplicates_removed = []
        
        for callback_id in list(app.callback_map.keys()):
            # Extract output signature (before @ symbol if present)
            output_sig = callback_id.split('@')[0] if '@' in callback_id else callback_id
            
            if output_sig in seen_outputs:
                # Duplicate found - remove it
                del app.callback_map[callback_id]
                duplicates_removed.append(callback_id[:80])
            else:
                seen_outputs[output_sig] = callback_id
        
        final_count = len(app.callback_map)
        logger.info(f"🔧 Deduplicated callback_map: {original_count} → {final_count} callbacks ({len(duplicates_removed)} duplicates removed)")
    
    _after_count = len(getattr(app, 'callback_map', {}))
    
    if _after_count == 0:
        logger.error("❌ CRITICAL: callback_map still empty! Check if tabs use @app.callback() decorators.")
    elif _after_count > 0:
        logger.info(f"✅ Successfully registered {_after_count} callbacks")
        # Diagnostic: dump the full callback_map to a file for offline inspection
        try:
            import json as _json, os as _os
            _out_dir = _os.path.join(_os.path.dirname(__file__), '..', 'test-artifacts', 'pre24')
            _out_dir = _os.path.normpath(_out_dir)
            _os.makedirs(_out_dir, exist_ok=True)
            _cb_path = _os.path.join(_out_dir, 'callback_map_full.json')
            # Convert callback_map to a serializable structure
            serializable = {k: v for k, v in getattr(app, 'callback_map', {}).items()}
            with open(_cb_path, 'w') as _f:
                _json.dump(serializable, _f, indent=2)
            logger.info(f"🔍 Wrote full callback_map to {_cb_path}")
        except Exception as _e:
            logger.warning(f"Failed to write callback_map_full.json: {_e}")
        # Also write a sanitized callback_map with only primitive fields for analysis
        try:
            _san_path = _os.path.join(_out_dir, 'callback_map_sanitized.json')
            sanitized = {}
            for k, v in getattr(app, 'callback_map', {}).items():
                try:
                    entry = {}
                    # outputs may be list/dict - include as-is if JSON-serializable
                    entry['outputs'] = v.get('outputs') if isinstance(v, dict) else None
                    entry['inputs'] = v.get('inputs') if isinstance(v, dict) else None
                    entry['state'] = v.get('state') if isinstance(v, dict) else None
                    entry['background'] = v.get('background') if isinstance(v, dict) else v.get('background')
                    sanitized[k] = entry
                except Exception:
                    sanitized[k] = {'error': 'entry not serializable'}

            with open(_san_path, 'w') as _f:
                _json.dump(sanitized, _f, indent=2)
            logger.info(f"🔍 Wrote sanitized callback_map to {_san_path}")
        except Exception as _e:
            logger.warning(f"Failed to write callback_map_sanitized.json: {_e}")
        # Log sample callback IDs for verification
        sample_keys = list(app.callback_map.keys())[:5]
        logger.info(f"📋 Sample callback IDs: {sample_keys}")
except Exception as e:
    logger.error(f"❌ Failed to register callbacks: {e}")
    import traceback
    logger.error(traceback.format_exc())

# DISABLED: Layout is now set INSIDE create_app() to force eager loading
# Setting it here causes Dash to use lazy loading mode (loading screen issue)
# import time
# layout_timestamp = time.time()
# app.layout = index.create_layout()
# logger.info(f"✅ [app.py @ {layout_timestamp}] Set app.layout to actual layout (called create_layout)")


# NOTE: Debug endpoints must be registered INSIDE create_app() to avoid Flask setup errors
# @server.route('/_debug/callbacks')
# def _debug_callbacks():
#     try:
#         cm = getattr(app, 'callback_map', {})
#         outputs = []
#         for k, v in cm.items():
#             outs = v.get('outputs') if isinstance(v, dict) else None
#             if outs:
#                 for o in outs:
#                     outputs.append({'key': k, 'output': o})
#         return server.response_class(json.dumps({'count': len(outputs), 'outputs': outputs}), mimetype='application/json')
#     except Exception as e:
#         return server.response_class(str(e), mimetype='text/plain')


# ============================================================================
# MAIN ENTRY POINT: Allow running dashboard directly with `python app.py`
# ============================================================================
if __name__ == "__main__":
    import os
    port = int(os.environ.get("DASH_PORT", 8050))
    debug = os.environ.get("DASH_DEBUG", "false").lower() == "true"
    
    logger.info("🚀 Starting dashboard from __main__ block...")
    logger.info(f"📍 Dashboard running at: http://0.0.0.0:{port}")
    logger.info(f"🔧 Debug mode: {debug}")
    
    app.run(host="0.0.0.0", port=port, debug=debug)
