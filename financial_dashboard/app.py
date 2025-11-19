"""
Financial Dashboard - Application Factory (Refactored)
Clean separation: Creates Flask + Dash app, registers API endpoints only.
Layout and callbacks are handled separately.
"""
import os
import sys
import json
import logging
import dash
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
            
            query = """
                SELECT week_start_date, ticker, rank, rationale,
                       momentum_score, sentiment_score, fundamental_score,
                       combined_score, chart_array, metadata, generated_at
                FROM weekly_picks_production
                WHERE week_start_date = (SELECT MAX(week_start_date) FROM weekly_picks_production)
                ORDER BY rank ASC
            """
            
            cursor.execute(query)
            picks = cursor.fetchall()
            cursor.close()
            conn.close()
            
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
    
    # Register Volatility Surface API Blueprint (Agent-1B)
    try:
        from .api.volsurface import register_blueprints as register_vol_blueprints
        register_vol_blueprints(server)
        logger.info("✅ Registered Volatility Surface API: /api/volsurface/*, /admin/vollab/*")
    except Exception as e:
        logger.warning(f"Could not register Volatility Surface API: {e}")
    
    # ========================================================================
    # STEP 3: Create Dash Application
    # ========================================================================
    logger.info("Step 3: Creating Dash application...")
    
    app = dash.Dash(
        name=__name__,
        server=server,
        external_stylesheets=[dbc.themes.BOOTSTRAP],
        suppress_callback_exceptions=True,
        url_base_pathname='/',
        serve_locally=True
    )
    
    app.title = "Financial Dashboard"
    
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
        # Import callbacks module
        from . import callbacks as callbacks_module
        
        # Register all callbacks
        callback_count = callbacks_module.register_all_callbacks(
            app,
            loaded_tabs=index_module.loaded_tabs,
            SH=index_module.SH,
            CHATBOT_AVAILABLE=index_module.CHATBOT_AVAILABLE
        )
        
        logger.info(f"✅ Registered {callback_count} callbacks")
        
    except Exception as e:
        logger.error(f"❌ Failed to register callbacks: {e}")
        import traceback
        logger.error(traceback.format_exc())
        logger.warning("⚠️ Dashboard will run with limited functionality")
    
    # ========================================================================
    # STEP 6: Return Configured App
    # ========================================================================
    logger.info("=" * 70)
    logger.info("✅ Application created successfully!")
    logger.info("=" * 70)
    
    return app


# Create singleton instance for WSGI servers
app = create_app()
server = app.server
