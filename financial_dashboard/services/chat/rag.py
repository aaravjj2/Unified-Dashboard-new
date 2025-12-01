"""
RAG Orchestration - Retrieval-Augmented Generation
Combines retrieval with generation for context-aware answers
"""

import logging
import json
import re
from typing import List, Dict, Any, Optional

from financial_dashboard.services.chat.generator_client import get_generator
from financial_dashboard.services.chat.embed import get_embedder
from financial_dashboard.services.chat.faiss_index import get_index

logger = logging.getLogger(__name__)


class ActionIntentDetector:
    """
    Pre-LLM action intent detection using pattern matching
    Reduces reliance on small LLM for action extraction
    """
    
    PATTERNS = {
        "create_paper_order": [
            r"(?:create|place|submit|buy|sell).{0,30}(?:order|trade|position)",
            r"(?:buy|sell)\s+\d+\s+shares?",  # Simplified - just detect buy/sell + number + shares
            r"paper\s+(?:order|trade)",
        ],
        "open_tab": [
            r"(?:open|show|navigate to|go to).{0,20}(?:tab|page|view)",
            r"show\s+me.{0,20}(?:volatility|trends|news|positions)",
        ],
        "run_backtest": [
            r"(?:run|execute|start).{0,20}backtest",
            r"test.{0,20}strategy",
        ]
    }
    
    def detect(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Detect action intent from query
        
        Returns:
            Action suggestion dict or None
        """
        query_lower = query.lower()
        
        for action_type, patterns in self.PATTERNS.items():
            for pattern in patterns:
                # Use case-insensitive matching for most patterns
                # But pass original query to _build_action for ticker extraction
                if re.search(pattern, query_lower, re.IGNORECASE):
                    return self._build_action(action_type, query)
        
        return None
    
    def _build_action(self, action_type: str, query: str) -> Optional[Dict[str, Any]]:
        """Build action suggestion from detected intent"""
        
        if action_type == "create_paper_order":
            # Extract ticker and quantity
            ticker_match = re.search(r'\b([A-Z]{1,5})\b', query)
            qty_match = re.search(r'\b(\d+)\s*(?:shares?)?', query)
            side_match = re.search(r'\b(buy|sell)\b', query.lower())
            
            ticker = ticker_match.group(1) if ticker_match else "AAPL"
            qty = int(qty_match.group(1)) if qty_match else 1
            side = side_match.group(1) if side_match else "buy"
            
            payload = {
                "symbol": ticker,
                "qty": qty,
                "side": side,
                "type": "market",
                "paper": True
            }
            return {
                "action": "create_paper_order",
                "payload": payload,
                "confidence": 0.85,
                "method": "pattern_detection"
            }
        
        elif action_type == "open_tab":
            # Extract tab name
            tab_keywords = {
                "volatility": "vol-surface",
                "vol": "vol-surface",
                "trends": "market-trends",
                "news": "market-trends",
                "positions": "positions",
                "portfolio": "positions"
            }
            
            tab_name = "market-trends"  # default
            for keyword, tab in tab_keywords.items():
                if keyword in query.lower():
                    tab_name = tab
                    break
            
            return {
                "action": "open_tab",
                "payload": {
                    "tab_name": tab_name
                },
                "confidence": 0.75,
                "method": "pattern_detection"
            }
        
        return None


class RAGOrchestrator:
    """
    RAG orchestration layer
    
    Workflow:
    1. Embed query
    2. Retrieve relevant chunks
    3. Assemble prompt with retrieved context
    4. Generate answer
    5. Extract action suggestions if present
    """
    
    def __init__(self):
        """Initialize RAG orchestrator"""
        self.generator = get_generator()
        self.embedder = get_embedder()
        self.index = get_index()
        self.intent_detector = ActionIntentDetector()
    
    def retrieve(
        self,
        query: str,
        top_k: int = 8,
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant chunks for query
        
        Args:
            query: User query text
            top_k: Number of chunks to retrieve
            metadata_filter: Optional metadata filter
            
        Returns:
            List of retrieved chunks with score
        """
        # Embed query
        query_embedding = self.embedder.embed(query)
        
        # Search index
        results = self.index.search(
            query_embedding,
            top_k=top_k,
            filter_meta=metadata_filter
        )
        
        logger.info(f"Retrieved {len(results)} chunks for query: {query[:50]}...")
        return results
    
    def assemble_prompt(
        self,
        system_prompt: str,
        query: str,
        chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Assemble final prompt with retrieved chunks
        
        Args:
            system_prompt: System instructions
            query: User query
            chunks: Retrieved chunks
            
        Returns:
            Complete prompt string
        """
        # Build context from chunks
        context_lines = []
        context_lines.append("=== Retrieved Context ===")
        
        for idx, chunk in enumerate(chunks):
            context_lines.append(f"\n[Source {idx + 1}] {chunk['metadata'].get('source', 'unknown')}")
            context_lines.append(f"Score: {chunk['score']:.3f}")
            context_lines.append(f"Text: {chunk['text'][:300]}...")
            context_lines.append("")
        
        context_section = "\n".join(context_lines)
        
        # Assemble full prompt
        prompt = f"""{system_prompt}

{context_section}

=== User Query ===
{query}

=== Instructions ===
Answer the query based on the retrieved context above. If you can find relevant information in the sources, cite them using [Source N] notation. If you want to suggest an action (like placing a trade), output a JSON object with "action", "payload", and "confidence" fields. Otherwise, provide a natural language answer.

Answer:"""
        
        return prompt
    
    def answer_query(
        self,
        query: str,
        tab_context: Optional[Dict[str, Any]] = None,
        use_rag: bool = True,
        top_k: int = 8
    ) -> Dict[str, Any]:
        """
        Answer a query using RAG
        
        Args:
            query: User query
            tab_context: Optional context from current tab
            use_rag: If False, skip retrieval
            top_k: Number of chunks to retrieve
            
        Returns:
            Dict with answer, sources, and optionally action_suggestion
        """
        logger.info(f"Answering query (use_rag={use_rag}): {query[:100]}...")
        
        # Try pattern-based action detection first
        pattern_action = self.intent_detector.detect(query)
        
        # System prompt
        system_prompt = """You are a financial assistant with access to market data, volatility analysis, and portfolio information.

Your responsibilities:
1. Answer questions about stocks, options, volatility, and market trends
2. Suggest paper trading actions when appropriate (NEVER live trades)
3. Cite sources from retrieved context
4. Be concise and accurate

When suggesting actions, use this JSON format:
{
  "action": "create_paper_order" | "open_tab" | "run_backtest",
  "payload": {...},
  "confidence": 0.0-1.0
}"""
        
        # Optionally add tab context to system prompt
        if tab_context:
            tab_name = tab_context.get('tab', 'unknown')
            ticker = tab_context.get('ticker', None)
            system_prompt += f"\n\nCurrent context: User is viewing {tab_name}"
            if ticker:
                system_prompt += f" for ticker {ticker}"
        
        # Retrieve relevant chunks (if RAG enabled and index not empty)
        chunks = []
        if use_rag and self.index.size() > 0:
            # Apply metadata filter if tab context specifies ticker
            metadata_filter = None
            if tab_context and tab_context.get('ticker'):
                metadata_filter = {"ticker": tab_context['ticker']}
            
            chunks = self.retrieve(query, top_k=top_k, metadata_filter=metadata_filter)
            
            # Guard: If no relevant chunks found (all scores too low), inform user
            if not chunks or (chunks and all(chunk['score'] > 1.5 for chunk in chunks)):
                logger.warning(f"No relevant chunks found for query: {query[:100]}")
                return {
                    "answer": "I don't have relevant documents in my knowledge base for this query. Would you like me to fetch current data or run an ingestion?",
                    "sources": [],
                    "raw_model_text": "",
                    "retrievals": [],
                    "action_suggestion": {
                        "action": "run_ingestion",
                        "payload": {"query": query},
                        "confidence": 0.5
                    },
                    "metadata": {
                        "model": "n/a",
                        "tokens": 0,
                        "use_rag": use_rag,
                        "retrieved_chunks": 0,
                        "no_chunks_found": True
                    }
                }
        else:
            logger.info("RAG disabled or index empty, using generator only")
        
        # Assemble prompt
        if chunks:
            prompt = self.assemble_prompt(system_prompt, query, chunks)
        else:
            prompt = f"{system_prompt}\n\nUser Query: {query}\n\nAnswer:"
        
        # Generate answer (use lower max_tokens for faster response)
        # CPU inference: ~0.2s/token, so 100 tokens = ~20s, 200 tokens = ~40s
        response = self.generator.complete(prompt, max_tokens=100, temperature=0.7)
        
        # Try to parse action suggestion from response
        action_suggestion = pattern_action  # Use pattern detector result if available
        answer_text = response.text
        
        # If no pattern match, try to extract from LLM response
        if not action_suggestion:
            try:
                # Check if response contains JSON
                if '{' in answer_text and '}' in answer_text:
                    # Try to extract JSON
                    start_idx = answer_text.index('{')
                    end_idx = answer_text.rindex('}') + 1
                    json_str = answer_text[start_idx:end_idx]
                    parsed = json.loads(json_str)
                    
                    if 'action' in parsed:
                        action_suggestion = parsed
                        # Remove JSON from answer text
                        answer_text = answer_text[:start_idx] + answer_text[end_idx:]
                        answer_text = answer_text.strip()
            except (json.JSONDecodeError, ValueError) as e:
                logger.debug(f"No JSON action found in response: {e}")
        
        # Build response
        result = {
            "answer": answer_text if answer_text else json.dumps(action_suggestion),
            "sources": [
                {
                    "chunk_id": chunk['chunk_id'],
                    "text": chunk['text'][:200] + "...",
                    "score": chunk['score'],
                    "metadata": chunk['metadata']
                }
                for chunk in chunks
            ],
            "raw_model_text": response.text,
            "retrievals": chunks,
            "action_suggestion": action_suggestion,
            "metadata": {
                "model": response.model,
                "tokens": response.total_tokens,
                "use_rag": use_rag,
                "retrieved_chunks": len(chunks)
            }
        }
        
        logger.info(f"Answer generated: {len(result['answer'])} chars, {len(chunks)} sources, action={action_suggestion is not None}")
        
        return result


# Global singleton
_rag_instance: Optional[RAGOrchestrator] = None


def get_rag() -> RAGOrchestrator:
    """Get or create global RAG orchestrator"""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = RAGOrchestrator()
    return _rag_instance
