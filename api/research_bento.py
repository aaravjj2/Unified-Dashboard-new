"""
Optional Bento LLM Integration for Research Lab.

Provides AI-generated research summaries when BENTO_RESEARCH_ENABLED=true.
Falls back to deterministic templates when disabled or unreachable.
"""

import os
import logging
import requests
from typing import Optional, Dict

logger = logging.getLogger(__name__)

# Configuration
BENTO_RESEARCH_ENABLED = os.getenv('BENTO_RESEARCH_ENABLED', 'false').lower() == 'true'
RESEARCH_BENTO_URL = os.getenv('RESEARCH_BENTO_URL', 'http://localhost:5001/predict')


def generate_summary(brief: Dict, prompt: str = "") -> str:
    """
    Generate an AI summary for a research brief.
    
    Args:
        brief: Research brief dictionary
        prompt: Optional custom prompt
        
    Returns:
        Generated summary text
    """
    if not BENTO_RESEARCH_ENABLED:
        return _generate_template_summary(brief)
    
    try:
        # Call Bento service
        response = requests.post(
            RESEARCH_BENTO_URL,
            json={
                'title': brief.get('title', ''),
                'body': brief.get('body', ''),
                'prompt': prompt or "Generate a concise executive summary of this research brief"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get('summary', _generate_template_summary(brief))
        else:
            logger.warning(f"Bento service returned {response.status_code}, using template")
            return _generate_template_summary(brief)
            
    except requests.exceptions.ConnectionError:
        logger.warning("Bento service unreachable, using template summary")
        return _generate_template_summary(brief)
    except Exception as e:
        logger.error(f"Error calling Bento service: {e}")
        return _generate_template_summary(brief)


def _generate_template_summary(brief: Dict) -> str:
    """
    Generate a deterministic template summary.
    
    Args:
        brief: Research brief dictionary
        
    Returns:
        Template-based summary
    """
    title = brief.get('title', 'Untitled Research')
    tags = brief.get('tags', [])
    tags_str = ', '.join(tags) if tags else 'general research'
    
    return f"""This is a generated summary for "{title}" — enable Bento to get an AI-powered summary.

**Topic:** {tags_str}

**Key Points:**
- Analysis covers {title.lower()}
- Research methodology follows quantitative approaches
- Findings are documented in the brief body

*Note: This is a placeholder summary. Set BENTO_RESEARCH_ENABLED=true and configure RESEARCH_BENTO_URL to enable AI-generated summaries.*
"""


# Export a Flask route for the summary endpoint
def create_summary_endpoint(research_bp):
    """
    Add the /generate_summary endpoint to the research blueprint.
    
    Args:
        research_bp: Flask Blueprint instance
    """
    
    @research_bp.route('/generate_summary', methods=['POST'])
    def generate_research_summary():
        """
        Generate an AI summary for a research brief.
        
        Request Body:
            brief_id: Brief identifier
            prompt: Optional custom prompt
            
        Returns:
            JSON: Generated summary
        """
        from flask import request, jsonify
        
        try:
            data = request.get_json() or {}
            brief_id = data.get('brief_id')
            custom_prompt = data.get('prompt', '')
            
            if not brief_id:
                return jsonify({'error': 'brief_id is required'}), 400
            
            # Load the brief
            from api.research import store
            brief = store.get_brief(brief_id)
            
            if not brief:
                return jsonify({'error': 'Brief not found'}), 404
            
            # Generate summary
            summary = generate_summary(brief, custom_prompt)
            
            return jsonify({
                'summary': summary,
                'source': 'bento' if BENTO_RESEARCH_ENABLED else 'template',
                'brief_id': brief_id
            }), 200
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}")
            return jsonify({'error': str(e)}), 500
