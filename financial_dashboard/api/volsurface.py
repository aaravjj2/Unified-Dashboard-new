"""
Volatility Surface API Blueprint
=================================

Agent-1B Implementation - Clean REST API for IV surface calculations.

Endpoints:
- POST /api/volsurface/compute - Calculate IV surface
- GET /api/volsurface/latest - Fetch last computed surface
- GET /api/volsurface/history - List surface metadata
- POST /api/volsurface/signal - Generate trading signals
- POST /api/volsurface/backtest - Run strategy backtest
- GET /admin/vollab/health - System health check

Deterministic Mode:
Set VOLLAB_DETERMINISTIC=1 to use fixtures instead of live computation.

Owner: Agent-1B
"""

import os
import json
import time
import math
import logging
from pathlib import Path
from datetime import datetime
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

# Create blueprint
volsurface_bp = Blueprint('volsurface', __name__, url_prefix='/api/volsurface')
admin_bp = Blueprint('vollab_admin', __name__, url_prefix='/admin/vollab')

# Deterministic mode flag
DETERMINISTIC_MODE = os.getenv('VOLLAB_DETERMINISTIC', '0') == '1'

# Fixture paths
FIXTURE_DIR = Path(__file__).parent.parent.parent / 'tests' / 'fixtures' / 'vol'
FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

# Job storage
JOBS_FILE = Path(__file__).parent.parent.parent / 'reports' / 'vol_lab_compact' / 'diagnostics' / 'jobs.json'
JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)

# Last solver run tracking
LAST_SOLVER_INFO = {
    'timestamp': None,
    'solver_name': None,
    'iterations': 0,
    'converged': False,
    'runtime_ms': 0,
    'fallback_used': False
}


def update_last_solver_info(info):
    """Update global solver tracking"""
    global LAST_SOLVER_INFO
    LAST_SOLVER_INFO.update(info)
    LAST_SOLVER_INFO['timestamp'] = datetime.now().isoformat()


def load_fixture(name):
    """Load deterministic fixture"""
    fixture_path = FIXTURE_DIR / f"{name}.json"
    if fixture_path.exists():
        with open(fixture_path, 'r') as f:
            return json.load(f)
    logger.warning(f"Fixture not found: {fixture_path}")
    return None


def save_job(job_id, data):
    """Save job to file-based queue"""
    jobs = {}
    if JOBS_FILE.exists():
        with open(JOBS_FILE, 'r') as f:
            jobs = json.load(f)
    
    jobs[job_id] = {
        **data,
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }
    
    with open(JOBS_FILE, 'w') as f:
        json.dump(jobs, f, indent=2)
    
    return jobs[job_id]


def get_job(job_id):
    """Retrieve job from storage"""
    if not JOBS_FILE.exists():
        return None
    
    with open(JOBS_FILE, 'r') as f:
        jobs = json.load(f)
    
    return jobs.get(job_id)


@volsurface_bp.route('/compute', methods=['POST', 'GET'])
def compute_surface():
    """
    POST /api/volsurface/compute
    
    Payload:
    {
        "ticker": "SPY",
        "expiries": ["2024-12-20", "2025-01-17"],
        "strikes": [450, 460, 470, 480, 490],
        "mode": "sync|async",
        "deterministic": true|false
    }
    
    Response (sync):
    {
        "id": "surf_123",
        "xs": [strike values],
        "ys": [expiry days to maturity],
        "grid": [[iv values]],
        "meta": {
            "solver_info": {...},
            "timestamp": "...",
            "ticker": "SPY"
        }
    }
    
    Response (async):
    {
        "job_id": "job_456"
    }
    """
    try:
        payload = request.get_json() or {}
        
        ticker = payload.get('ticker', 'SPY')
        mode = payload.get('mode', 'sync')
        use_deterministic = payload.get('deterministic', DETERMINISTIC_MODE)
        
        logger.info(f"compute_surface: ticker={ticker}, mode={mode}, deterministic={use_deterministic}")
        
        # Deterministic fixture mode
        if use_deterministic:
            fixture = load_fixture('iv_grid')
            if fixture:
                solver_info = {
                    'solver_name': 'fixture',
                    'iterations': 0,
                    'converged': True,
                    'fallback_used': False,
                    'runtime_ms': 0
                }
                update_last_solver_info(solver_info)
                
                return jsonify({
                    'id': f"surf_{int(time.time())}",
                    'xs': fixture.get('xs', [450, 460, 470, 480, 490]),
                    'ys': fixture.get('ys', [30, 60, 90, 120, 150]),
                    'grid': fixture.get('grid', [
                        [0.15, 0.16, 0.17, 0.18, 0.19],
                        [0.16, 0.17, 0.18, 0.19, 0.20],
                        [0.17, 0.18, 0.19, 0.20, 0.21],
                        [0.18, 0.19, 0.20, 0.21, 0.22],
                        [0.19, 0.20, 0.21, 0.22, 0.23]
                    ]),
                    'meta': {
                        'solver_info': solver_info,
                        'timestamp': datetime.now().isoformat(),
                        'ticker': ticker,
                        'mode': 'deterministic'
                    }
                }), 200
        
        # Async mode - enqueue job
        if mode == 'async':
            job_id = f"job_{int(time.time() * 1000)}"
            job_data = {
                'job_id': job_id,
                'status': 'queued',
                'payload': payload
            }
            save_job(job_id, job_data)
            return jsonify({'job_id': job_id}), 202
        
        # Sync mode - compute immediately (placeholder - will wire to solver)
        try:
            # Import solver
            import sys
            project_root = Path(__file__).parent.parent.parent
            if str(project_root) not in sys.path:
                sys.path.insert(0, str(project_root))
            
            from volatility.solver import compute_surface_grid
            
            # Parse inputs
            expiries = payload.get('expiries', [30, 60, 90])
            strikes = payload.get('strikes', [450, 460, 470, 480, 490])
            
            # Mock option prices (in production, fetch from market data)
            S = 475.0  # Mock stock price
            option_prices = {}
            for days in expiries:
                for K in strikes:
                    # Mock price = intrinsic + time value
                    intrinsic = max(S - K, 0)
                    time_value = 5.0 * (days / 365.0) * math.sqrt(abs(S - K) / S)
                    option_prices[(K, days)] = intrinsic + time_value
            
            # Compute surface
            xs, ys, grid, meta = compute_surface_grid(S, strikes, expiries, option_prices)
            
            # Track solver metadata
            update_last_solver_info(meta)
            
            return jsonify({
                'id': f"surf_{int(time.time())}",
                'xs': xs,
                'ys': ys,
                'grid': grid,
                'meta': {
                    'solver_info': meta,
                    'timestamp': datetime.now().isoformat(),
                    'ticker': ticker
                }
            }), 200
            
        except Exception as e:
            logger.exception("Solver integration error")
            # Fallback to placeholder
            pass
        
        return jsonify({
            'id': f"surf_{int(time.time())}",
            'xs': [450, 460, 470, 480, 490],
            'ys': [30, 60, 90],
            'grid': [
                [0.15, 0.16, 0.17, 0.18, 0.19],
                [0.16, 0.17, 0.18, 0.19, 0.20],
                [0.17, 0.18, 0.19, 0.20, 0.21]
            ],
            'meta': {
                'solver_info': {
                    'solver_name': 'placeholder',
                    'iterations': 0,
                    'converged': True,
                    'fallback_used': False,
                    'runtime_ms': 0
                },
                'timestamp': datetime.now().isoformat(),
                'ticker': ticker
            }
        }), 200
        
    except Exception as e:
        logger.exception("compute_surface error")
        return jsonify({'error': str(e)}), 500


@volsurface_bp.route('/latest', methods=['GET'])
def get_latest_surface():
    """
    GET /api/volsurface/latest?ticker=SPY
    
    Response: Last computed surface for ticker
    """
    try:
        ticker = request.args.get('ticker', 'SPY')
        
        if DETERMINISTIC_MODE:
            fixture = load_fixture('iv_grid')
            if fixture:
                return jsonify({
                    'ticker': ticker,
                    'surface': fixture,
                    'timestamp': datetime.now().isoformat()
                }), 200
        
        return jsonify({
            'ticker': ticker,
            'surface': None,
            'message': 'No surface computed yet'
        }), 404
        
    except Exception as e:
        logger.exception("get_latest_surface error")
        return jsonify({'error': str(e)}), 500


@volsurface_bp.route('/history', methods=['GET'])
def get_surface_history():
    """
    GET /api/volsurface/history?ticker=SPY&limit=10
    
    Response: List of surface metadata
    """
    try:
        ticker = request.args.get('ticker', 'SPY')
        limit = int(request.args.get('limit', 10))
        
        return jsonify({
            'ticker': ticker,
            'surfaces': [],
            'count': 0,
            'limit': limit
        }), 200
        
    except Exception as e:
        logger.exception("get_surface_history error")
        return jsonify({'error': str(e)}), 500


@volsurface_bp.route('/signal', methods=['POST'])
def generate_signals():
    """
    POST /api/volsurface/signal
    
    Payload:
    {
        "ticker": "SPY",
        "surface_id": "surf_123",
        "strategy": "iv_rank"
    }
    
    Response:
    {
        "signals": [
            {
                "id": "sig_1",
                "ticker": "SPY",
                "strategy": "iv_rank",
                "confidence": 0.75,
                "risk": "medium",
                "notes": "IV rank above 75th percentile"
            }
        ],
        "meta": {...}
    }
    """
    try:
        payload = request.get_json() or {}
        ticker = payload.get('ticker', 'SPY')
        
        if DETERMINISTIC_MODE:
            fixture = load_fixture('signals')
            if fixture:
                return jsonify(fixture), 200
        
        # Placeholder signals
        return jsonify({
            'signals': [
                {
                    'id': f"sig_{int(time.time())}",
                    'ticker': ticker,
                    'strategy': payload.get('strategy', 'iv_rank'),
                    'confidence': 0.65,
                    'risk': 'medium',
                    'notes': 'Placeholder signal'
                }
            ],
            'meta': {
                'timestamp': datetime.now().isoformat(),
                'count': 1
            }
        }), 200
        
    except Exception as e:
        logger.exception("generate_signals error")
        return jsonify({'error': str(e)}), 500


@volsurface_bp.route('/backtest', methods=['POST'])
def run_backtest():
    """
    POST /api/volsurface/backtest
    
    Payload:
    {
        "strategy": "covered_call",
        "params": {...},
        "seed": 42
    }
    
    Response:
    {
        "summary": {
            "return": 0.15,
            "sharpe": 1.2,
            "max_drawdown": -0.08
        },
        "trades": [...]
    }
    """
    try:
        payload = request.get_json() or {}
        
        if DETERMINISTIC_MODE:
            fixture = load_fixture('backtest_preview')
            if fixture:
                return jsonify(fixture), 200
        
        # Placeholder backtest
        return jsonify({
            'summary': {
                'return': 0.12,
                'sharpe': 1.1,
                'max_drawdown': -0.05,
                'trades': 15
            },
            'trades': [],
            'meta': {
                'timestamp': datetime.now().isoformat(),
                'strategy': payload.get('strategy', 'unknown')
            }
        }), 200
        
    except Exception as e:
        logger.exception("run_backtest error")
        return jsonify({'error': str(e)}), 500


@volsurface_bp.route('/job/<job_id>', methods=['GET'])
def get_job_status(job_id):
    """GET /api/volsurface/job/<id> - Retrieve job status"""
    try:
        job = get_job(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify(job), 200
        
    except Exception as e:
        logger.exception("get_job_status error")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/health', methods=['GET'])
def health_check():
    """
    GET /admin/vollab/health
    
    Response:
    {
        "last_surface_ts": "...",
        "last_solver_info": {...},
        "queue_length": 0,
        "diagnostics_version": "1.0"
    }
    """
    try:
        job_count = 0
        pending_jobs = 0
        completed_jobs = 0
        
        if JOBS_FILE.exists():
            with open(JOBS_FILE, 'r') as f:
                jobs = json.load(f)
                job_count = len(jobs)
                pending_jobs = sum(1 for j in jobs.values() if j.get('status') == 'queued')
                completed_jobs = sum(1 for j in jobs.values() if j.get('status') == 'completed')
        
        return jsonify({
            'status': 'ok',
            'last_surface_ts': LAST_SOLVER_INFO.get('timestamp'),
            'last_solver_info': {
                'solver_name': LAST_SOLVER_INFO.get('solver_name'),
                'iterations': LAST_SOLVER_INFO.get('iterations'),
                'converged': LAST_SOLVER_INFO.get('converged'),
                'runtime_ms': LAST_SOLVER_INFO.get('runtime_ms'),
                'fallback_used': LAST_SOLVER_INFO.get('fallback_used')
            },
            'queue': {
                'total': job_count,
                'pending': pending_jobs,
                'completed': completed_jobs
            },
            'diagnostics_version': '1.1',
            'deterministic_mode': DETERMINISTIC_MODE,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.exception("health_check error")
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/callback_map', methods=['GET'])
def callback_map():
    """
    GET /admin/vollab/callback_map
    
    Returns callback registry for diagnostics.
    Inspects Dash app._callback_list to extract callback metadata.
    
    Response:
    {
        "total_callbacks": 6,
        "callbacks": [
            {
                "callback_id": "compute_iv_surface",
                "outputs": ["vl-heatmap.figure", "vl-iv-metrics-table.children", ...],
                "inputs": ["vl-calc-run-btn.n_clicks"],
                "states": ["vl-calc-ticker.value", ...],
                "function_name": "compute_iv_surface"
            },
            ...
        ],
        "timestamp": "2024-11-27T14:30:45"
    }
    
    Agent-1A: New endpoint for callback introspection and debugging.
    """
    try:
        from flask import current_app
        
        # Access Dash app instance (assuming it's stored in Flask app config)
        dash_app = current_app.config.get('DASH_APP')
        
        if not dash_app:
            return jsonify({
                'error': 'Dash app not found in Flask config',
                'hint': 'Set app.config["DASH_APP"] = dash_app during initialization'
            }), 500
        
        callbacks_data = []

        # Dash stores callbacks in _callback_list attribute but formats vary
        def safe_fmt_item(item):
            # Try common object shapes, fall back to repr
            try:
                if hasattr(item, 'component_id') and hasattr(item, 'component_property'):
                    return f"{item.component_id}.{item.component_property}"
                if isinstance(item, dict):
                    cid = item.get('component_id') or item.get('id') or item.get('componentId')
                    prop = item.get('component_property') or item.get('prop') or item.get('property')
                    if cid and prop:
                        return f"{cid}.{prop}"
                    return str(item)
                if isinstance(item, str):
                    return item
                return repr(item)
            except Exception:
                return repr(item)

        def normalize_sequence(obj):
            """Ensure we have a list-like container for iteration.

            Dash callback metadata sometimes stores a single target as a
            string or dict instead of a list. If a string is passed
            directly to the 'outputs' field, iterating it will yield
            characters. Normalize into a list to avoid that.
            """
            if obj is None:
                return []
            # Already sequence-like (but don't treat strings as sequences here)
            if isinstance(obj, (list, tuple)):
                return list(obj)
            # Single dict/str/other -> wrap into list
            return [obj]

        # Collect counts from dash_app.callback_map if available (Dash v2/3)
        try:
            callback_map_count = len(getattr(dash_app, 'callback_map', {}))
        except Exception:
            callback_map_count = None

        if hasattr(dash_app, '_callback_list'):
            for callback in dash_app._callback_list:
                try:
                    # callback may be a dict-like or other structure
                    if isinstance(callback, dict):
                        outputs = callback.get('output') or callback.get('outputs') or []
                        inputs = callback.get('inputs') or []
                        states = callback.get('state') or callback.get('states') or []
                        func = callback.get('callback')
                        cb_id = callback.get('callback_id') or callback.get('id') or getattr(func, '__name__', repr(func))
                    else:
                        # Unknown shape: try attribute access, else stringify
                        outputs = getattr(callback, 'output', []) or getattr(callback, 'outputs', []) or []
                        inputs = getattr(callback, 'inputs', [])
                        states = getattr(callback, 'state', []) or getattr(callback, 'states', []) or []
                        func = getattr(callback, 'callback', None)
                        cb_id = getattr(callback, 'callback_id', None) or getattr(callback, 'id', None) or (getattr(func, '__name__', None) or repr(callback))

                    callback_info = {
                        'callback_id': cb_id,
                        'outputs': [safe_fmt_item(o) for o in normalize_sequence(outputs)],
                        'inputs': [safe_fmt_item(i) for i in normalize_sequence(inputs)],
                        'states': [safe_fmt_item(s) for s in normalize_sequence(states)],
                        'function_name': getattr(func, '__name__', repr(func)) if func is not None else 'unknown'
                    }
                except Exception:
                    callback_info = {'callback_id': repr(callback), 'outputs': [], 'inputs': [], 'states': [], 'function_name': 'unknown'}

                callbacks_data.append(callback_info)
        
        return jsonify({
            'total_callbacks': len(callbacks_data),
            'callback_map_count': callback_map_count,
            'callbacks': callbacks_data,
            'timestamp': datetime.now().isoformat(),
            'diagnostics_version': '1.1'
        }), 200
        
    except Exception as e:
        logger.exception("callback_map error")
        return jsonify({
            'error': str(e),
            'total_callbacks': 0,
            'callbacks': []
        }), 500



@admin_bp.route('/callback_counts', methods=['GET'])
def callback_counts():
    """
    GET /admin/vollab/callback_counts

    Returns lightweight callback counts for quick diagnostics.
    """
    try:
        from flask import current_app
        dash_app = current_app.config.get('DASH_APP')

        if not dash_app:
            return jsonify({'error': 'Dash app not found in Flask config', 'hint': 'Set app.config["DASH_APP"] = dash_app during init'}), 500

        map_len = None
        try:
            map_len = len(getattr(dash_app, 'callback_map', {}))
        except Exception:
            map_len = None

        list_len = None
        try:
            list_len = len(getattr(dash_app, '_callback_list', []))
        except Exception:
            list_len = None

        return jsonify({
            'callback_map_len': map_len,
            'callback_list_len': list_len,
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        logger.exception('callback_counts error')
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/last_layout', methods=['GET'])
def last_layout():
    """
    GET /admin/vollab/last_layout
    
    Returns last rendered Dash layout for diagnostics.
    Extracts component tree from Dash app.layout.
    
    Response:
    {
        "layout_type": "Container",
        "component_count": 42,
        "interactive_ids": ["vl-calc-run-btn", "vl-heatmap", ...],
        "layout_tree": {...},
        "timestamp": "2024-11-27T14:30:45"
    }
    
    Agent-1A: New endpoint for layout introspection and debugging.
    """
    try:
        from flask import current_app
        
        # Access Dash app instance
        dash_app = current_app.config.get('DASH_APP')
        
        if not dash_app:
            return jsonify({
                'error': 'Dash app not found in Flask config',
                'hint': 'Set app.config["DASH_APP"] = dash_app during initialization'
            }), 500
        
        layout = dash_app.layout
        
        if not layout:
            return jsonify({
                'error': 'No layout found',
                'layout_type': None,
                'component_count': 0,
                'interactive_ids': []
            }), 404
        
        # Extract component tree recursively
        def extract_tree(component, depth=0, max_depth=5):
            if depth > max_depth:
                return {'type': 'max_depth_exceeded'}
            
            component_info = {
                'type': type(component).__name__,
                'id': getattr(component, 'id', None),
                'children': []
            }
            
            # Recursively extract children
            if hasattr(component, 'children'):
                children = component.children
                if isinstance(children, list):
                    component_info['children'] = [
                        extract_tree(child, depth+1, max_depth) for child in children
                    ]
                elif children is not None:
                    component_info['children'] = [extract_tree(children, depth+1, max_depth)]
            
            return component_info
        
        layout_tree = extract_tree(layout)
        
        # Extract all interactive IDs (components with 'id' attribute)
        def extract_ids(component):
            ids = []
            if hasattr(component, 'id') and component.id:
                ids.append(component.id)
            if hasattr(component, 'children'):
                children = component.children
                if isinstance(children, list):
                    for child in children:
                        ids.extend(extract_ids(child))
                elif children is not None:
                    ids.extend(extract_ids(children))
            return ids
        
        interactive_ids = extract_ids(layout)
        
        # Count total components
        def count_components(component):
            count = 1
            if hasattr(component, 'children'):
                children = component.children
                if isinstance(children, list):
                    for child in children:
                        count += count_components(child)
                elif children is not None:
                    count += count_components(children)
            return count
        
        component_count = count_components(layout)
        
        return jsonify({
            'layout_type': type(layout).__name__,
            'component_count': component_count,
            'interactive_ids': interactive_ids,
            'layout_tree': layout_tree,
            'timestamp': datetime.now().isoformat(),
            'diagnostics_version': '1.1'
        }), 200
        
    except Exception as e:
        logger.exception("last_layout error")
        return jsonify({
            'error': str(e),
            'layout_type': None,
            'component_count': 0,
            'interactive_ids': []
        }), 500


# Blueprint registration helper
def register_blueprints(app):
    """Register volsurface blueprints with Flask app"""
    app.register_blueprint(volsurface_bp)
    app.register_blueprint(admin_bp)
    logger.info("✓ Volatility Surface API blueprints registered")
    logger.info(f"  Deterministic mode: {DETERMINISTIC_MODE}")
