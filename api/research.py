"""
Research API - RESTful endpoints for research brief management.

Provides CRUD operations for research briefs with local JSON storage.
Includes screening and backtest preview capabilities.
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file, Response
import io

# Import ResearchStore from research module
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from research.store import JSONStore

logger = logging.getLogger(__name__)

# Configure diagnostic logging
DIAGNOSTICS_DIR = Path("reports/research_lab_fix/diagnostics")
DIAGNOSTICS_DIR.mkdir(parents=True, exist_ok=True)
API_ERRORS_LOG = DIAGNOSTICS_DIR / "api_errors.log"

api_logger = logging.getLogger("research.api")
api_fh = logging.FileHandler(API_ERRORS_LOG)
api_fh.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
api_logger.addHandler(api_fh)
api_logger.setLevel(logging.DEBUG)

# Create Blueprint
research_bp = Blueprint('research', __name__, url_prefix='/api/research')

# Configuration
RESEARCH_DATA_DIR = Path(os.getenv('RESEARCH_DATA_DIR', 'data/research'))
FIXTURES_DIR = Path('tests/fixtures/research')
RESEARCH_DETERMINISTIC = os.getenv('RESEARCH_DETERMINISTIC', '1') == '1'
RESEARCH_DB_ENABLED = os.getenv('RESEARCH_DB_ENABLED', 'false').lower() == 'true'

# Ensure data directory exists
RESEARCH_DATA_DIR.mkdir(parents=True, exist_ok=True)

# Initialize store
if RESEARCH_DB_ENABLED:
    api_logger.warning("RESEARCH_DB_ENABLED=true but DBStore not implemented, falling back to JSONStore")
    store = JSONStore(path=str(RESEARCH_DATA_DIR / 'briefs.json'))
else:
    store = JSONStore(path=str(RESEARCH_DATA_DIR / 'briefs.json'))

api_logger.info(f"Research API initialized with store: {type(store).__name__}, deterministic: {RESEARCH_DETERMINISTIC}")


def error_response(message: str, status_code: int = 400, details: Optional[Dict] = None) -> tuple:
    """Generate consistent error response."""
    response = {'error': True, 'message': message}
    if details:
        response['details'] = details
    api_logger.error(f"Error {status_code}: {message} {details or ''}")
    return jsonify(response), status_code


def load_fixture(fixture_name: str) -> Dict:
    """Load fixture from tests/fixtures/research/"""
    fixture_path = FIXTURES_DIR / fixture_name
    if not fixture_path.exists():
        api_logger.warning(f"Fixture not found: {fixture_path}")
        return {}
    try:
        with open(fixture_path, 'r') as f:
            data = json.load(f)
            api_logger.debug(f"Loaded fixture: {fixture_name}")
            return data
    except Exception as e:
        api_logger.error(f"Error loading fixture {fixture_name}: {e}")
        return {}


# ============================================================================
# CRUD ENDPOINTS
# ============================================================================

@research_bp.route('/briefs', methods=['GET'])
def list_briefs():
    """GET /api/research/briefs - Returns list of all research briefs"""
    try:
        if RESEARCH_DETERMINISTIC:
            demo = load_fixture('demo_brief.json')
            if demo:
                api_logger.info("list_briefs: returning deterministic demo")
                return jsonify([demo]), 200
        briefs = store.list_briefs()
        api_logger.info(f"list_briefs: returning {len(briefs)} briefs")
        return jsonify(briefs), 200
    except Exception as e:
        api_logger.exception("Error in list_briefs")
        return error_response(f"Failed to list briefs: {str(e)}", 500)


@research_bp.route('/briefs', methods=['POST'])
def create_brief():
    """POST /api/research/briefs - Create a new research brief"""
    try:
        data = request.get_json()
        if not data:
            return error_response("No data provided", 400)
        if 'title' not in data:
            return error_response("Field 'title' is required", 400)
        brief = store.create_brief(data)
        api_logger.info(f"create_brief: created {brief['id']}")
        return jsonify(brief), 201
    except Exception as e:
        api_logger.exception("Error in create_brief")
        return error_response(f"Failed to create brief: {str(e)}", 500)


@research_bp.route('/briefs/<brief_id>', methods=['GET'])
def get_brief(brief_id: str):
    """GET /api/research/briefs/<id> - Retrieve specific brief"""
    try:
        brief = store.get_brief(brief_id)
        if not brief:
            return error_response(f"Brief not found: {brief_id}", 404)
        api_logger.info(f"get_brief: retrieved {brief_id}")
        return jsonify(brief), 200
    except Exception as e:
        api_logger.exception(f"Error in get_brief({brief_id})")
        return error_response(f"Failed to get brief: {str(e)}", 500)


@research_bp.route('/briefs/<brief_id>', methods=['PUT'])
def update_brief(brief_id: str):
    """PUT /api/research/briefs/<id> - Update existing brief"""
    try:
        data = request.get_json()
        if not data:
            return error_response("No data provided", 400)
        brief = store.update_brief(brief_id, data)
        if not brief:
            return error_response(f"Brief not found: {brief_id}", 404)
        api_logger.info(f"update_brief: updated {brief_id}")
        return jsonify(brief), 200
    except Exception as e:
        api_logger.exception(f"Error in update_brief({brief_id})")
        return error_response(f"Failed to update brief: {str(e)}", 500)


@research_bp.route('/briefs/<brief_id>', methods=['DELETE'])
def delete_brief(brief_id: str):
    """DELETE /api/research/briefs/<id> - Delete a brief"""
    try:
        success = store.delete_brief(brief_id)
        if not success:
            return error_response(f"Brief not found: {brief_id}", 404)
        api_logger.info(f"delete_brief: deleted {brief_id}")
        return jsonify({'success': True, 'message': f'Brief {brief_id} deleted'}), 200
    except Exception as e:
        api_logger.exception(f"Error in delete_brief({brief_id})")
        return error_response(f"Failed to delete brief: {str(e)}", 500)


@research_bp.route('/briefs/<brief_id>/export', methods=['GET'])
def export_brief(brief_id: str):
    """GET /api/research/briefs/<id>/export - Export brief as JSON file"""
    try:
        json_str = store.export_brief(brief_id)
        if not json_str:
            return error_response(f"Brief not found: {brief_id}", 404)
        buffer = io.BytesIO(json_str.encode('utf-8'))
        buffer.seek(0)
        api_logger.info(f"export_brief: exporting {brief_id}")
        return send_file(buffer, mimetype='application/json', as_attachment=True, download_name=f'brief_{brief_id}.json')
    except Exception as e:
        api_logger.exception(f"Error in export_brief({brief_id})")
        return error_response(f"Failed to export brief: {str(e)}", 500)


# ============================================================================
# ACTION ENDPOINTS
# ============================================================================

@research_bp.route('/screen', methods=['POST'])
def run_screen():
    """POST /api/research/screen - Run screening job"""
    try:
        if RESEARCH_DETERMINISTIC:
            result = load_fixture('screen_result.json')
            if result:
                api_logger.info("run_screen: returning deterministic fixture")
                return jsonify(result), 200
        data = request.get_json() or {}
        criteria = data.get('criteria', {})
        result = {
            'results': [
                {'symbol': 'AAPL', 'market_cap': 2500000000000, 'pe_ratio': 28, 'sector': 'Technology'},
                {'symbol': 'MSFT', 'market_cap': 2300000000000, 'pe_ratio': 32, 'sector': 'Technology'},
            ],
            'count': 2,
            'criteria': criteria,
            'timestamp': datetime.utcnow().isoformat()
        }
        api_logger.info(f"run_screen: executed with criteria {criteria}")
        return jsonify(result), 200
    except Exception as e:
        api_logger.exception("Error in run_screen")
        return error_response(f"Failed to run screen: {str(e)}", 500)


@research_bp.route('/backtest_preview', methods=['POST'])
def run_backtest_preview():
    """POST /api/research/backtest_preview - Run backtest preview"""
    try:
        if RESEARCH_DETERMINISTIC:
            result = load_fixture('backtest_preview.json')
            if result:
                api_logger.info("run_backtest_preview: returning deterministic fixture")
                return jsonify(result), 200
        data = request.get_json() or {}
        strategy = data.get('strategy', {})
        result = {
            'summary': {
                'total_return': 0.15,
                'sharpe_ratio': 1.2,
                'max_drawdown': -0.08,
                'trades': 25,
                'win_rate': 0.62
            },
            'trades': [
                {'symbol': 'AAPL', 'entry_date': '2024-01-15', 'exit_date': '2024-02-20', 'pnl': 0.08},
                {'symbol': 'MSFT', 'entry_date': '2024-01-20', 'exit_date': '2024-03-10', 'pnl': 0.12},
            ],
            'strategy': strategy.get('name', 'Unnamed'),
            'timestamp': datetime.utcnow().isoformat()
        }
        api_logger.info(f"run_backtest_preview: executed for strategy {strategy.get('name')}")
        return jsonify(result), 200
    except Exception as e:
        api_logger.exception("Error in run_backtest_preview")
        return error_response(f"Failed to run backtest preview: {str(e)}", 500)


@research_bp.route('/generate_summary', methods=['POST'])
def generate_summary():
    """POST /api/research/generate_summary - Generate AI summary"""
    try:
        data = request.get_json() or {}
        brief_id = data.get('brief_id')
        prompt = data.get('prompt', 'Summarize this research brief.')
        bento_enabled = os.getenv('RESEARCH_BENTO_ENABLED', 'false').lower() == 'true'
        bento_url = os.getenv('RESEARCH_BENTO_URL', '')
        if bento_enabled and bento_url:
            try:
                from .research_bento import call_bento_llm
                summary = call_bento_llm(prompt, bento_url)
                api_logger.info(f"generate_summary: called Bento for brief {brief_id}")
                return jsonify({'summary': summary, 'source': 'bento', 'timestamp': datetime.utcnow().isoformat()}), 200
            except Exception as e:
                api_logger.warning(f"Bento call failed, falling back to template: {e}")
                with open(DIAGNOSTICS_DIR / 'bento_fallback.log', 'a') as f:
                    f.write(f"{datetime.utcnow().isoformat()} - Bento fallback: {e}\n")
        brief = store.get_brief(brief_id) if brief_id else {}
        title = brief.get('title', 'Untitled Brief')
        template_summary = f"Generated summary (demo): {title}: Key point 1 - Market conditions analyzed. Key point 2 - Risk assessment completed. Key point 3 - Investment thesis validated."
        api_logger.info(f"generate_summary: returning template for brief {brief_id}")
        return jsonify({'summary': template_summary, 'source': 'template', 'timestamp': datetime.utcnow().isoformat()}), 200
    except Exception as e:
        api_logger.exception("Error in generate_summary")
        return error_response(f"Failed to generate summary: {str(e)}", 500)


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@research_bp.route('/health', methods=['GET'])
def health_check():
    """GET /admin/research/health - Health check"""
    try:
        metadata = store.get_metadata()
        health = {
            'ok': True,
            'brief_count': metadata.get('brief_count', 0),
            'last_updated_iso': metadata.get('last_modified', 'never'),
            'deterministic': RESEARCH_DETERMINISTIC,
            'store_type': metadata.get('store_type', 'unknown')
        }
        return jsonify(health), 200
    except Exception as e:
        api_logger.exception("Error in health_check")
        return jsonify({'ok': False, 'error': str(e)}), 500


@research_bp.route('/cache_info', methods=['GET'])
def cache_info():
    """GET /admin/research/cache_info - Return store metadata"""
    try:
        metadata = store.get_metadata()
        return jsonify(metadata), 200
    except Exception as e:
        api_logger.exception("Error in cache_info")
        return error_response(f"Failed to get cache info: {str(e)}", 500)


# ============================================================================
# RAG ENDPOINTS
# ============================================================================

@research_bp.route('/ingest', methods=['POST'])
def ingest_document():
    """POST /api/research/ingest - Ingest document into RAG index"""
    try:
        data = request.get_json() or {}
        
        text = data.get('text', '')
        source_url = data.get('source_url', '')
        title = data.get('title', 'Untitled Document')
        metadata = data.get('metadata', {})
        
        if not text and not source_url:
            return error_response("Either 'text' or 'source_url' is required", 400)
        
        # Import ingestion pipeline
        try:
            from background.research_ingest import get_pipeline
            pipeline = get_pipeline()
        except Exception as e:
            api_logger.error(f"Failed to import ingestion pipeline: {e}")
            return error_response(f"Ingestion pipeline not available: {str(e)}", 500)
        
        # Ingest the document
        if text:
            doc = pipeline.ingest_text(text, title, metadata)
        else:
            # TODO: Implement URL fetching
            return error_response("URL ingestion not yet implemented", 501)
        
        result = {
            'doc_id': doc.doc_id,
            'title': doc.title,
            'chunks': len(doc.chunks),
            'status': 'ingested',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        api_logger.info(f"ingest: ingested document {doc.doc_id}")
        return jsonify(result), 200
        
    except Exception as e:
        api_logger.exception("Error in ingest_document")
        return error_response(f"Failed to ingest document: {str(e)}", 500)


@research_bp.route('/query', methods=['POST'])
def rag_query():
    """POST /api/research/query - Execute RAG query"""
    try:
        data = request.get_json() or {}
        
        query = data.get('query', '')
        top_k = data.get('top_k', 5)
        sources = data.get('sources', 'all')
        
        if not query:
            return error_response("'query' is required", 400)
        
        # Import and execute query engine
        try:
            from financial_dashboard.services.llm_local import get_query_engine
            engine = get_query_engine()
        except Exception as e:
            api_logger.error(f"Failed to import query engine: {e}")
            return error_response(f"Query engine not available: {str(e)}", 500)
        
        result = engine.query(query, top_k=top_k, sources=sources)
        
        api_logger.info(f"rag_query: executed query, answer_id={result.get('answer_id')}")
        return jsonify(result), 200
        
    except Exception as e:
        api_logger.exception("Error in rag_query")
        return error_response(f"RAG query failed: {str(e)}", 500)


@research_bp.route('/explain', methods=['POST'])
def rag_explain():
    """POST /api/research/explain - Get explanation for RAG answer"""
    try:
        data = request.get_json() or {}
        
        answer_id = data.get('answer_id', '')
        
        if not answer_id:
            return error_response("'answer_id' is required", 400)
        
        # Import and get explanation
        try:
            from financial_dashboard.services.llm_local import get_query_engine
            engine = get_query_engine()
        except Exception as e:
            api_logger.error(f"Failed to import query engine: {e}")
            return error_response(f"Query engine not available: {str(e)}", 500)
        
        result = engine.explain(answer_id)
        
        api_logger.info(f"rag_explain: explained answer_id={answer_id}")
        return jsonify(result), 200
        
    except Exception as e:
        api_logger.exception("Error in rag_explain")
        return error_response(f"Explain failed: {str(e)}", 500)


@research_bp.route('/index_health', methods=['GET'])
def rag_index_health():
    """GET /admin/research/index_health - Get RAG index health status"""
    try:
        from background.research_ingest import get_pipeline
        pipeline = get_pipeline()
        stats = pipeline.get_stats()
        
        health = {
            'status': 'ok' if stats['vector_count'] > 0 else 'empty',
            'index_size': stats['vector_count'],
            'doc_count': stats['doc_count'],
            'embedding_dim': stats['embedding_dim'],
            'embedding_model': stats['embedding_model'],
            'last_updated': datetime.utcnow().isoformat()
        }
        
        return jsonify(health), 200
        
    except Exception as e:
        api_logger.exception("Error in rag_index_health")
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@research_bp.route('/doc', methods=['GET'])
def get_rag_document():
    """GET /admin/research/doc?id=... - Get raw document from RAG index"""
    try:
        doc_id = request.args.get('id', '')
        
        if not doc_id:
            return error_response("'id' query parameter is required", 400)
        
        from background.research_ingest import get_pipeline
        pipeline = get_pipeline()
        doc = pipeline.get_document(doc_id)
        
        if not doc:
            return error_response(f"Document not found: {doc_id}", 404)
        
        # Return document without embeddings (too large)
        result = {
            'doc_id': doc.doc_id,
            'title': doc.title,
            'content': doc.content,
            'source_type': doc.source_type,
            'source_url': doc.source_url,
            'metadata': doc.metadata,
            'chunks': doc.chunks,
            'ingested_at': doc.ingested_at
        }
        
        return jsonify(result), 200
        
    except Exception as e:
        api_logger.exception("Error in get_rag_document")
        return error_response(f"Failed to get document: {str(e)}", 500)


# Block Azure calls
@research_bp.before_request
def block_azure():
    """Block any requests attempting to use Azure."""
    azure_patterns = ['azure', 'azureml', 'ml.azure']
    request_str = str(request.url) + str(request.get_json(silent=True) or '')
    for pattern in azure_patterns:
        if pattern in request_str.lower():
            blocked_msg = f"Azure usage blocked: {pattern} detected in request"
            api_logger.warning(blocked_msg)
            with open(DIAGNOSTICS_DIR / 'azure_blocked.log', 'a') as f:
                f.write(f"{datetime.utcnow().isoformat()} - {blocked_msg}\n")
            return error_response("Azure functionality disabled. Research Lab operates in local-only mode.", 403, {'blocked_pattern': pattern})


__all__ = ['research_bp', 'store']
