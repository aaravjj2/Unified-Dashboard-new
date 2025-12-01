"""Admin diagnostics blueprint (read-only). Does not auto-register."""
from flask import Blueprint, jsonify, current_app
import os, json

admin_bp = Blueprint('admin_diagnostics', __name__)


@admin_bp.route('/admin/callback_map')
def callback_map():
    """Return callback_map summary if available on `current_app`.
    This endpoint is read-only and must be registered by the operator.
    """
    app = current_app._get_current_object()
    cb_map = None
    try:
        cb_map = getattr(app, 'callback_map', None)
    except Exception:
        cb_map = None
    if cb_map is None:
        return jsonify({'ok': False, 'msg': 'callback_map not available; register blueprint in app to enable.'})
    return jsonify({'ok': True, 'callback_count': len(cb_map), 'callbacks': list(cb_map.keys())})


@admin_bp.route('/admin/tab_health/<tab>')
def tab_health(tab):
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    diag_dir = os.path.join(repo_root, 'reports', 'agent2a')
    report = os.path.join(diag_dir, 'architecture_report.json')
    if not os.path.exists(report):
        return jsonify({'ok': False, 'msg': 'No agent2a reports available'})
    with open(report) as f:
        data = json.load(f)
    # best-effort health: presence in major_tabs
    major = data.get('major_tabs', {})
    if tab not in major:
        return jsonify({'ok': False, 'msg': 'Tab not found in report'})
    return jsonify({'ok': True, 'tab': tab, 'files': major.get(tab)})
