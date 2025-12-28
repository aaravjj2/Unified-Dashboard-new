"""
Chat API Endpoints
RESTful API for RAG chat assistant
"""

import os
import logging
import time
import json
from flask import Blueprint, request, jsonify
from typing import Dict, Any

from financial_dashboard.services.chat.generator_client import get_generator
from financial_dashboard.services.chat.faiss_index import get_index
from financial_dashboard.services.chat.ingest import IngestionPipeline
from financial_dashboard.services.chat.rag import get_rag
from financial_dashboard.services.chat.actions import get_executor

logger = logging.getLogger(__name__)

# Create Blueprint
chat_api = Blueprint('chat_api', __name__, url_prefix='/api/chat')


@chat_api.route('/health', methods=['GET'])
def health():
    """
    Check chat service health
    
    Returns generator status and vector index health
    
    GET /api/chat/health
    
    Response:
        {
            "status": "healthy" | "degraded" | "unhealthy",
            "generator": {...},
            "vector_index": {...},
            "timestamp": "2024-11-22T10:30:00Z"
        }
    """
    try:
        # Check generator
        generator = get_generator()
        generator_health = generator.health_check()
        
        # Check vector index
        index = get_index()
        index_health = index.health_check()
        index_health["status"] = "healthy" if index_health["size"] > 0 else "empty"
        
        # Determine overall status
        if generator_health["status"] == "healthy":
            overall_status = "healthy"
        elif generator_health["status"] == "degraded":
            overall_status = "degraded"
        else:
            overall_status = "unhealthy"
        
        return jsonify({
            "status": overall_status,
            "generator": generator_health,
            "vector_index": index_health,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 200
        
    except Exception as e:
        logger.error(f"Health check error: {e}", exc_info=True)
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }), 500


@chat_api.route('/query', methods=['POST'])
def query():
    """
    Query the RAG chat assistant
    
    POST /api/chat/query
    
    Request body:
        {
            "query": "What is the volatility for AAPL?",
            "use_rag": true,
            "tab_context": {
                "tab": "volatility_lab",
                "ticker": "AAPL",
                "data": {...}
            },
            "top_k": 8
        }
    
    Response:
        {
            "answer": "Based on the retrieved data...",
            "sources": [
                {"chunk_id": "...", "text": "...", "score": 0.95},
                ...
            ],
            "raw_model_text": "...",
            "retrievals": [...],
            "action_suggestion": {...} | null
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' in request body"}), 400
        
        query_text = data['query']
        use_rag = data.get('use_rag', True)
        tab_context = data.get('tab_context', None)
        top_k = data.get('top_k', 8)
        
        logger.info(f"Received query: {query_text[:100]}, use_rag={use_rag}")
        
        # Use RAG orchestrator
        rag = get_rag()
        result = rag.answer_query(
            query=query_text,
            tab_context=tab_context,
            use_rag=use_rag,
            top_k=top_k
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Query error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@chat_api.route('/execute_action', methods=['POST'])
def execute_action():
    """
    Execute a confirmed action
    
    POST /api/chat/execute_action
    
    Request body:
        {
            "action_id": "...",
            "action_type": "create_paper_order",
            "payload": {...},
            "confirmed": true,
            "user_id": "optional_user_id"
        }
    
    Response:
        {
            "success": true,
            "result": {...},
            "action_id": "..."
        }
    """
    try:
        data = request.get_json()
        
        if not data or 'action_type' not in data:
            return jsonify({"error": "Missing 'action_type' in request body"}), 400
        
        if not data.get('confirmed', False):
            return jsonify({"error": "Action must be confirmed by user"}), 403
        
        action_id = data.get('action_id', f"action_{int(time.time() * 1000)}")
        action_type = data['action_type']
        payload = data.get('payload', {})
        confirmed = data.get('confirmed', False)
        user_id = data.get('user_id', None)
        
        logger.info(f"Executing action: {action_type} (id={action_id})")
        
        # Execute via ActionExecutor
        executor = get_executor()
        result = executor.execute(
            action_id=action_id,
            action_type=action_type,
            payload=payload,
            confirmed=confirmed,
            user_id=user_id
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
        
    except Exception as e:
        logger.error(f"Action execution error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@chat_api.route('/reindex', methods=['POST'])
def reindex():
    """
    Trigger reindexing of vector index
    
    POST /api/chat/reindex
    
    Response:
        {
            "success": true,
            "documents_indexed": 123,
            "duration_ms": 4567
        }
    """
    try:
        start_time = time.time()
        
        # Reingest from fixtures
        pipeline = IngestionPipeline()
        stats = pipeline.ingest_fixtures()
        
        duration_ms = (time.time() - start_time) * 1000
        
        logger.info(f"Reindexing complete in {duration_ms:.0f}ms: {stats}")
        
        return jsonify({
            "success": True,
            "documents_indexed": stats['documents'],
            "chunks_created": stats['chunks'],
            "indexed": stats['indexed'],
            "duration_ms": duration_ms
        }), 200


@chat_api.route('/execute_picks', methods=['POST'])
def execute_picks_endpoint():
    """
    Generate stock picks and optionally execute market orders.
    POST body:
      { "n": 5, "allocation_per_pick": 500, "execute": false }

    Safety: To perform live orders (execute=true & dry_run=False), environment variable
    ALLOW_AUTO_BUY must be set to '1'. Otherwise orders will remain dry-run.
    """
    try:
        payload = request.get_json() or {}
        n = int(payload.get('n', 5))
        allocation = float(payload.get('allocation_per_pick', 500.0))
        execute_flag = bool(payload.get('execute', False))

        # If execute_flag is True, require explicit ALLOW_AUTO_BUY env var
        if execute_flag and os.getenv('ALLOW_AUTO_BUY', '0') != '1':
            return jsonify({"error": "Auto-buy disabled. Set ALLOW_AUTO_BUY=1 to enable live execution"}), 403

        svc = AIMorningBriefService()
        res = svc.generate_and_execute_picks(n=n, allocation_per_pick=allocation, execute=execute_flag)
        return jsonify({"success": True, "result": res}), 200

    except Exception as e:
        logger.error(f"Execute picks endpoint error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
        
    except Exception as e:
        logger.error(f"Reindex error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@chat_api.route('/ingest', methods=['POST'])
def ingest():
    """
    Ingest documents into vector index
    
    POST /api/chat/ingest
    
    Request body:
        {
            "documents": [
                {"text": "...", "doc_id": "...", "metadata": {...}},
                ...
            ],
            "use_fixtures": false
        }
    
    Response:
        {
            "success": true,
            "documents": 10,
            "chunks_created": 234,
            "indexed": 234
        }
    """
    try:
        data = request.get_json() or {}
        
        use_fixtures = data.get('use_fixtures', False)
        documents = data.get('documents', [])
        
        logger.info(f"Ingest requested: {len(documents)} docs, fixtures={use_fixtures}")
        
        pipeline = IngestionPipeline()
        
        if use_fixtures:
            stats = pipeline.ingest_fixtures()
        elif documents:
            stats = pipeline.ingest_documents(documents)
        else:
            return jsonify({"error": "No documents provided and use_fixtures=false"}), 400
        
        return jsonify({
            "success": True,
            **stats
        }), 200
        
    except Exception as e:
        logger.error(f"Ingest error: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


def register_chat_api(app):
    """Register chat API blueprint with Flask app"""
    app.register_blueprint(chat_api)
    
    # Add diagnostic endpoint for color validation (debug-only)
    @app.route('/api/_diag/chat_color', methods=['GET'])
    def chat_color_diagnostic():
        """
        Debug-only endpoint to expose computed chat color for testing
        Returns the last computed chat color from client-side JS
        """
        try:
            # This endpoint is meant to be queried by Playwright tests
            # The actual color value is computed client-side via chat_color_diagnostic.js
            # and exposed on window.__chat_last_computed_color
            return jsonify({
                "info": "Query window.__chat_last_computed_color in browser console",
                "expected": "rgb(0, 0, 0)",
                "test_element": "#chat-color-diagnostic",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            }), 200
        except Exception as e:
            logger.error(f"Chat color diagnostic error: {e}")
            return jsonify({"error": str(e)}), 500
    
    logger.info("Chat API registered at /api/chat/*")
