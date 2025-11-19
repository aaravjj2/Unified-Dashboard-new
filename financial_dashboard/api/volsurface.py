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


@volsurface_bp.route('/compute', methods=['POST'])
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
                        'solver_info': {
                            'solver_name': 'fixture',
                            'iterations': 0,
                            'converged': True,
                            'fallback_used': False,
                            'runtime_ms': 0
                        },
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
        if JOBS_FILE.exists():
            with open(JOBS_FILE, 'r') as f:
                jobs = json.load(f)
                job_count = len(jobs)
        
        return jsonify({
            'status': 'ok',
            'last_surface_ts': None,
            'last_solver_info': None,
            'queue_length': job_count,
            'diagnostics_version': '1.0',
            'deterministic_mode': DETERMINISTIC_MODE,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.exception("health_check error")
        return jsonify({'error': str(e)}), 500


# Blueprint registration helper
def register_blueprints(app):
    """Register volsurface blueprints with Flask app"""
    app.register_blueprint(volsurface_bp)
    app.register_blueprint(admin_bp)
    logger.info("✓ Volatility Surface API blueprints registered")
    logger.info(f"  Deterministic mode: {DETERMINISTIC_MODE}")
