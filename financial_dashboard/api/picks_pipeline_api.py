"""
Picks API Endpoints - Dry-run, Approve, Publish workflow

Implements:
- POST /api/picks/run (trigger runner with dry-run/publish mode)
- GET /api/picks/run_status?run_id=<id>
- POST /api/picks/approve (admin publish approval)
- GET /api/picks/history

Author: Agent-1B for Picks Pipeline Rebuild
"""

import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

from flask import Blueprint, request, jsonify

# Project imports
import sys
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools.picks_run import run_pipeline

logger = logging.getLogger(__name__)

# Create blueprint
picks_api_bp = Blueprint('picks_api', __name__, url_prefix='/api/picks')

# Job status storage (in-memory for now; can persist to disk/DB later)
JOB_STATUS = {}

# Admin token (from env for security)
ADMIN_TOKEN = os.environ.get('PICKS_ADMIN_TOKEN', 'change-me-in-production')

RUNS_DIR = PROJECT_ROOT / 'reports' / 'picks' / 'runs'
PUBLISHED_DIR = PROJECT_ROOT / 'data' / 'picks_published'


@picks_api_bp.route('/run', methods=['POST'])
def trigger_run():
    """
    Trigger a picks pipeline run.
    
    Request JSON:
        {
            "type": "weekly" | "monthly",
            "mode": "dryrun" | "publish",
            "params": {...}  # optional scoring params
        }
    
    Returns:
        {
            "run_id": "<uuid>",
            "status": "queued" | "running",
            "status_url": "/api/picks/run_status?run_id=<uuid>"
        }
    """
    try:
        data = request.get_json() or {}
        
        run_type = data.get('type', 'weekly')
        mode = data.get('mode', 'dryrun')
        params = data.get('params', {})
        
        if run_type not in ['weekly', 'monthly']:
            return jsonify({'error': 'Invalid type; must be weekly or monthly'}), 400
        
        if mode not in ['dryrun', 'publish']:
            return jsonify({'error': 'Invalid mode; must be dryrun or publish'}), 400
        
        logger.info(f"Starting picks run: type={run_type}, mode={mode}")
        
        # Run pipeline (blocking for now; can make async later)
        manifest, run_dir = run_pipeline(run_type, mode=mode, params=params)
        
        run_id = manifest.get('run_id')
        
        # Store job status
        JOB_STATUS[run_id] = {
            'run_id': run_id,
            'status': 'completed',
            'run_type': run_type,
            'mode': mode,
            'manifest': manifest,
            'run_dir': str(run_dir),
            'started_at': manifest.get('started_at'),
            'finished_at': manifest.get('finished_at')
        }
        
        return jsonify({
            'run_id': run_id,
            'status': 'completed',
            'status_url': f'/api/picks/run_status?run_id={run_id}',
            'manifest': manifest
        }), 200
        
    except Exception as e:
        logger.exception("Failed to trigger picks run")
        return jsonify({'error': str(e)}), 500


@picks_api_bp.route('/run_status', methods=['GET'])
def run_status():
    """
    Get status of a picks run.
    
    Query params:
        run_id: Run UUID
    
    Returns:
        {
            "run_id": "<uuid>",
            "status": "queued" | "running" | "completed" | "failed",
            "manifest": {...},
            "validation": {...},
            "artifacts": [...]
        }
    """
    run_id = request.args.get('run_id')
    
    if not run_id:
        return jsonify({'error': 'Missing run_id parameter'}), 400
    
    # Check in-memory status
    if run_id in JOB_STATUS:
        return jsonify(JOB_STATUS[run_id]), 200
    
    # Check on disk
    run_dir = RUNS_DIR / run_id
    if run_dir.exists():
        manifest_path = run_dir / 'manifest.json'
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            validation_path = run_dir / 'validation.json'
            validation = {}
            if validation_path.exists():
                with open(validation_path, 'r') as f:
                    validation = json.load(f)
            
            # List artifacts
            artifacts = [str(p.relative_to(PROJECT_ROOT)) for p in run_dir.iterdir()]
            
            return jsonify({
                'run_id': run_id,
                'status': 'completed',
                'manifest': manifest,
                'validation': validation,
                'artifacts': artifacts,
                'run_dir': str(run_dir.relative_to(PROJECT_ROOT))
            }), 200
    
    return jsonify({'error': 'Run not found'}), 404


@picks_api_bp.route('/approve', methods=['POST'])
def approve_run():
    """
    Approve and publish a dry-run (admin only).
    
    Request JSON:
        {
            "run_id": "<uuid>",
            "approver": "admin_name",
            "token": "admin_token"
        }
    
    Returns:
        {"status": "published", "run_id": "..."}
    """
    try:
        data = request.get_json() or {}
        
        run_id = data.get('run_id')
        approver = data.get('approver', 'unknown')
        token = data.get('token')
        
        if not run_id:
            return jsonify({'error': 'Missing run_id'}), 400
        
        # Token check
        if token != ADMIN_TOKEN:
            logger.warning(f"Invalid admin token for approve: {approver}")
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Load run manifest
        run_dir = RUNS_DIR / run_id
        if not run_dir.exists():
            return jsonify({'error': 'Run not found'}), 404
        
        manifest_path = run_dir / 'manifest.json'
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        # Check validation
        validation = manifest.get('validation', {})
        if not validation.get('passed'):
            return jsonify({
                'error': 'Validation failed; cannot approve',
                'validation': validation
            }), 400
        
        # Load selected picks
        selected_path = run_dir / 'selected.json'
        with open(selected_path, 'r') as f:
            selected = json.load(f)
        
        # Publish: copy to published directory
        run_type = manifest.get('run_type', 'weekly')
        published_path = PUBLISHED_DIR / f'{run_type}_picks_published.json'
        
        published_data = {
            'run_id': run_id,
            'published_at': datetime.utcnow().isoformat(),
            'approver': approver,
            'selected': selected,
            'manifest': manifest
        }
        
        with open(published_path, 'w', encoding='utf-8') as f:
            json.dump(published_data, f, indent=2, default=str)
        
        # Also update canonical published file for UI
        canonical_published = PROJECT_ROOT / 'data' / 'picks' / f'{run_type}_picks.json'
        with open(canonical_published, 'w', encoding='utf-8') as f:
            json.dump(selected, f, indent=2, default=str)
        
        logger.info(f"Approved and published run {run_id} by {approver}")
        
        return jsonify({
            'status': 'published',
            'run_id': run_id,
            'approver': approver,
            'published_path': str(published_path.relative_to(PROJECT_ROOT))
        }), 200
        
    except Exception as e:
        logger.exception("Failed to approve run")
        return jsonify({'error': str(e)}), 500


@picks_api_bp.route('/history', methods=['GET'])
def get_history():
    """
    Get history of picks runs.
    
    Query params:
        limit: Max results (default 20)
    
    Returns:
        {
            "runs": [{run_id, type, status, started_at, finished_at}, ...]
        }
    """
    limit = int(request.args.get('limit', 20))
    
    runs = []
    
    if RUNS_DIR.exists():
        for run_path in sorted(RUNS_DIR.iterdir(), reverse=True):
            if not run_path.is_dir():
                continue
            
            manifest_path = run_path / 'manifest.json'
            if manifest_path.exists():
                with open(manifest_path, 'r') as f:
                    manifest = json.load(f)
                
                runs.append({
                    'run_id': manifest.get('run_id'),
                    'run_type': manifest.get('run_type'),
                    'mode': manifest.get('mode'),
                    'status': 'completed' if manifest.get('finished_at') else 'running',
                    'validation_passed': (manifest.get('validation') or {}).get('passed'),
                    'started_at': manifest.get('started_at'),
                    'finished_at': manifest.get('finished_at')
                })
                
                if len(runs) >= limit:
                    break
    
    return jsonify({'runs': runs, 'count': len(runs)}), 200


# Register blueprint with app
def register_picks_api(app):
    """Register picks API blueprint with Flask app."""
    app.register_blueprint(picks_api_bp)
    logger.info("Registered picks API endpoints")
