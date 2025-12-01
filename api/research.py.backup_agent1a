"""
Research API - RESTful endpoints for research brief management.

Provides CRUD operations for research briefs with local JSON storage.
Includes screening and backtest preview capabilities.
"""

import os
import json
import logging
import fcntl
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file

logger = logging.getLogger(__name__)

# Create Blueprint
research_bp = Blueprint('research', __name__, url_prefix='/api/research')

# Configuration
RESEARCH_DATA_DIR = Path(os.getenv('RESEARCH_DATA_DIR', 'data/research'))
BRIEFS_FILE = RESEARCH_DATA_DIR / 'briefs.json'
FIXTURES_DIR = Path('tests/fixtures/research')
RESEARCH_DETERMINISTIC = os.getenv('RESEARCH_DETERMINISTIC', '1') == '1'
RESEARCH_DB_ENABLED = os.getenv('RESEARCH_DB_ENABLED', 'false').lower() == 'true'

# Ensure data directory exists
RESEARCH_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Optional: Register Bento LLM integration
try:
    from .research_bento import create_summary_endpoint
    # Will be called after store is initialized
    BENTO_AVAILABLE = True
except ImportError:
    BENTO_AVAILABLE = False
    logger.info("Bento integration module not available (optional)")


class ResearchStore:
    """
    Abstract base class for research brief storage.
    Provides interface for JSON and DB implementations.
    """
    
    def list_briefs(self) -> List[Dict]:
        """List all research briefs."""
        raise NotImplementedError
    
    def get_brief(self, brief_id: str) -> Optional[Dict]:
        """Get a specific brief by ID."""
        raise NotImplementedError
    
    def create_brief(self, brief_data: Dict) -> Dict:
        """Create a new brief."""
        raise NotImplementedError
    
    def update_brief(self, brief_id: str, brief_data: Dict) -> Optional[Dict]:
        """Update an existing brief."""
        raise NotImplementedError
    
    def delete_brief(self, brief_id: str) -> bool:
        """Delete a brief."""
        raise NotImplementedError


class JSONStore(ResearchStore):
    """
    JSON file-based storage for research briefs.
    Uses file locking to prevent concurrent write conflicts.
    """
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        if not self.file_path.exists():
            self._write_briefs([])
    
    def _read_briefs(self) -> List[Dict]:
        """Read briefs from JSON file with locking."""
        try:
            with open(self.file_path, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                briefs = json.load(f)
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                return briefs
        except (FileNotFoundError, json.JSONDecodeError):
            return []
    
    def _write_briefs(self, briefs: List[Dict]):
        """Write briefs to JSON file with locking."""
        with open(self.file_path, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(briefs, f, indent=2)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    
    def list_briefs(self) -> List[Dict]:
        return self._read_briefs()
    
    def get_brief(self, brief_id: str) -> Optional[Dict]:
        briefs = self._read_briefs()
        return next((b for b in briefs if b.get('id') == brief_id), None)
    
    def create_brief(self, brief_data: Dict) -> Dict:
        briefs = self._read_briefs()
        
        # Generate ID if not provided
        if 'id' not in brief_data:
            brief_data['id'] = f"brief_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Add timestamps
        now = datetime.now().isoformat()
        brief_data['created_at'] = now
        brief_data['last_updated'] = now
        
        # Ensure required fields
        brief_data.setdefault('notes', '')
        brief_data.setdefault('attachments', [])
        
        briefs.append(brief_data)
        self._write_briefs(briefs)
        
        logger.info(f"Created brief: {brief_data['id']}")
        return brief_data
    
    def update_brief(self, brief_id: str, brief_data: Dict) -> Optional[Dict]:
        briefs = self._read_briefs()
        
        for i, brief in enumerate(briefs):
            if brief.get('id') == brief_id:
                # Update timestamp
                brief_data['last_updated'] = datetime.now().isoformat()
                
                # Merge updates (don't replace entire brief)
                briefs[i].update(brief_data)
                self._write_briefs(briefs)
                
                logger.info(f"Updated brief: {brief_id}")
                return briefs[i]
        
        return None
    
    def delete_brief(self, brief_id: str) -> bool:
        briefs = self._read_briefs()
        original_len = len(briefs)
        
        briefs = [b for b in briefs if b.get('id') != brief_id]
        
        if len(briefs) < original_len:
            self._write_briefs(briefs)
            logger.info(f"Deleted brief: {brief_id}")
            return True
        
        return False


class DBStore(ResearchStore):
    """
    Database-backed storage for research briefs.
    Optional implementation when RESEARCH_DB_ENABLED=true.
    """
    
    def __init__(self):
        # TODO: Implement DB connection
        logger.warning("DBStore not yet implemented, falling back to JSONStore")
        self._fallback = JSONStore(BRIEFS_FILE)
    
    def list_briefs(self):
        return self._fallback.list_briefs()
    
    def get_brief(self, brief_id):
        return self._fallback.get_brief(brief_id)
    
    def create_brief(self, brief_data):
        return self._fallback.create_brief(brief_data)
    
    def update_brief(self, brief_id, brief_data):
        return self._fallback.update_brief(brief_id, brief_data)
    
    def delete_brief(self, brief_id):
        return self._fallback.delete_brief(brief_id)


# Initialize store
store = DBStore() if RESEARCH_DB_ENABLED else JSONStore(BRIEFS_FILE)

# Register optional Bento endpoints
if BENTO_AVAILABLE:
    try:
        create_summary_endpoint(research_bp)
        logger.info("✓ Registered Bento LLM integration endpoints")
    except Exception as e:
        logger.warning(f"Could not register Bento endpoints: {e}")


# ========================================================================
# API ENDPOINTS
# ========================================================================

@research_bp.route('/demo_brief', methods=['GET'])
def get_demo_brief():
    """
    Get the demo research brief fixture.
    
    Returns:
        JSON: Demo brief data
    """
    try:
        demo_file = FIXTURES_DIR / 'demo_brief.json'
        with open(demo_file, 'r') as f:
            demo_brief = json.load(f)
        return jsonify(demo_brief), 200
    except Exception as e:
        logger.error(f"Error loading demo brief: {e}")
        return jsonify({'error': str(e)}), 500


@research_bp.route('/briefs', methods=['GET'])
def list_briefs():
    """
    List all research briefs.
    
    Returns:
        JSON: Array of brief objects
    """
    try:
        briefs = store.list_briefs()
        return jsonify(briefs), 200
    except Exception as e:
        logger.error(f"Error listing briefs: {e}")
        return jsonify({'error': str(e)}), 500


@research_bp.route('/briefs', methods=['POST'])
def create_brief():
    """
    Create a new research brief.
    
    Request Body:
        title: Brief title
        tags: List of tags
        summary: Short summary
        body: Full content (markdown)
        notes: Additional notes
        
    Returns:
        JSON: Created brief object
    """
    try:
        brief_data = request.get_json()
        
        # Validate required fields
        if not brief_data.get('title'):
            return jsonify({'error': 'Title is required'}), 400
        
        # Check for Azure attempts (FORBIDDEN)
        brief_str = json.dumps(brief_data).lower()
        if 'azure' in brief_str:
            log_azure_block(f"Blocked Azure attempt in create_brief: {brief_str[:100]}")
            return jsonify({'error': 'Azure usage is forbidden'}), 403
        
        created_brief = store.create_brief(brief_data)
        return jsonify(created_brief), 200
        
    except Exception as e:
        logger.error(f"Error creating brief: {e}")
        return jsonify({'error': str(e)}), 500


@research_bp.route('/briefs/<brief_id>', methods=['GET'])
def get_brief(brief_id):
    """
    Get a specific research brief.
    
    Args:
        brief_id: Brief identifier
        
    Returns:
        JSON: Brief object or error
    """
    try:
        brief = store.get_brief(brief_id)
        if brief:
            return jsonify(brief), 200
        else:
            return jsonify({'error': 'Brief not found'}), 404
    except Exception as e:
        logger.error(f"Error getting brief {brief_id}: {e}")
        return jsonify({'error': str(e)}), 500


@research_bp.route('/briefs/<brief_id>', methods=['PUT'])
def update_brief(brief_id):
    """
    Update an existing research brief.
    
    Args:
        brief_id: Brief identifier
        
    Request Body:
        Fields to update (partial update supported)
        
    Returns:
        JSON: Updated brief object
    """
    try:
        brief_data = request.get_json()
        
        # Check for Azure attempts (FORBIDDEN)
        brief_str = json.dumps(brief_data).lower()
        if 'azure' in brief_str:
            log_azure_block(f"Blocked Azure attempt in update_brief: {brief_str[:100]}")
            return jsonify({'error': 'Azure usage is forbidden'}), 403
        
        updated_brief = store.update_brief(brief_id, brief_data)
        if updated_brief:
            return jsonify(updated_brief), 200
        else:
            return jsonify({'error': 'Brief not found'}), 404
            
    except Exception as e:
        logger.error(f"Error updating brief {brief_id}: {e}")
        return jsonify({'error': str(e)}), 500


@research_bp.route('/briefs/<brief_id>', methods=['DELETE'])
def delete_brief(brief_id):
    """
    Delete a research brief.
    
    Args:
        brief_id: Brief identifier
        
    Returns:
        JSON: Success message or error
    """
    try:
        success = store.delete_brief(brief_id)
        if success:
            return jsonify({'message': 'Brief deleted successfully'}), 200
        else:
            return jsonify({'error': 'Brief not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting brief {brief_id}: {e}")
        return jsonify({'error': str(e)}), 500


@research_bp.route('/screen', methods=['POST'])
def run_screen():
    """
    Run a screening job on market data.
    
    Request Body:
        brief_id: Associated brief ID (optional)
        
    Returns:
        JSON: Screening results
    """
    try:
        data = request.get_json() or {}
        
        # In deterministic mode, return fixture
        if RESEARCH_DETERMINISTIC:
            fixture_file = FIXTURES_DIR / 'screen_result.json'
            with open(fixture_file, 'r') as f:
                results = json.load(f)
            return jsonify(results), 200
        
        # TODO: Implement real screening logic here
        # For now, return deterministic results
        logger.warning("Non-deterministic screening not yet implemented, using fixture")
        fixture_file = FIXTURES_DIR / 'screen_result.json'
        with open(fixture_file, 'r') as f:
            results = json.load(f)
        return jsonify(results), 200
        
    except Exception as e:
        logger.error(f"Error running screen: {e}")
        return jsonify({'error': str(e)}), 500


@research_bp.route('/backtest_preview', methods=['POST'])
def run_backtest_preview():
    """
    Run a quick backtest preview.
    
    Request Body:
        brief_id: Associated brief ID (optional)
        
    Returns:
        JSON: Backtest preview results
    """
    try:
        data = request.get_json() or {}
        
        # In deterministic mode, return fixture
        if RESEARCH_DETERMINISTIC:
            fixture_file = FIXTURES_DIR / 'backtest_preview.json'
            with open(fixture_file, 'r') as f:
                results = json.load(f)
            return jsonify(results), 200
        
        # TODO: Implement real backtest logic here
        # For now, return deterministic results
        logger.warning("Non-deterministic backtest not yet implemented, using fixture")
        fixture_file = FIXTURES_DIR / 'backtest_preview.json'
        with open(fixture_file, 'r') as f:
            results = json.load(f)
        return jsonify(results), 200
        
    except Exception as e:
        logger.error(f"Error running backtest preview: {e}")
        return jsonify({'error': str(e)}), 500


@research_bp.route('/briefs/<brief_id>/export', methods=['GET'])
def export_brief(brief_id):
    """
    Export a brief as JSON file download.
    
    Args:
        brief_id: Brief identifier
        
    Returns:
        File: JSON download
    """
    try:
        brief = store.get_brief(brief_id)
        if not brief:
            return jsonify({'error': 'Brief not found'}), 404
        
        # Create temp file
        export_path = RESEARCH_DATA_DIR / f"{brief_id}_export.json"
        with open(export_path, 'w') as f:
            json.dump(brief, f, indent=2)
        
        return send_file(
            export_path,
            mimetype='application/json',
            as_attachment=True,
            download_name=f"{brief.get('title', brief_id)}.json"
        )
        
    except Exception as e:
        logger.error(f"Error exporting brief {brief_id}: {e}")
        return jsonify({'error': str(e)}), 500


@research_bp.route('/briefs/<brief_id>/attachments', methods=['POST'])
def upload_attachment(brief_id):
    """
    Upload an attachment to a brief.
    
    Args:
        brief_id: Brief identifier
        
    Returns:
        JSON: Attachment metadata
    """
    # TODO: Implement file upload
    return jsonify({'error': 'Not yet implemented'}), 501


# ========================================================================
# ADMIN / OBSERVABILITY ENDPOINTS
# ========================================================================

@research_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for research API.
    
    Returns:
        JSON: Health status and metadata
    """
    try:
        briefs = store.list_briefs()
        
        last_modified = None
        if BRIEFS_FILE.exists():
            last_modified = datetime.fromtimestamp(
                BRIEFS_FILE.stat().st_mtime
            ).isoformat()
        
        return jsonify({
            'ok': True,
            'count_briefs': len(briefs),
            'last_modified': last_modified,
            'store_type': 'db' if RESEARCH_DB_ENABLED else 'json',
            'deterministic_mode': RESEARCH_DETERMINISTIC
        }), 200
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'ok': False,
            'error': str(e)
        }), 500


# ========================================================================
# HELPER FUNCTIONS
# ========================================================================

def log_azure_block(message: str):
    """Log Azure usage attempts to diagnostic file."""
    azure_log = Path('reports/research_lab_fix/diagnostics/azure_blocked.log')
    azure_log.parent.mkdir(parents=True, exist_ok=True)
    
    with open(azure_log, 'a') as f:
        timestamp = datetime.now().isoformat()
        f.write(f"[{timestamp}] {message}\n")
    
    logger.warning(f"🚫 BLOCKED AZURE ATTEMPT: {message}")
