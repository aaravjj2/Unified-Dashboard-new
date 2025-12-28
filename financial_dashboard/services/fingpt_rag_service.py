"""
FinGPT RAG Service
==================
Document retrieval and RAG (Retrieval-Augmented Generation) for enhanced chatbot responses.
Uses FAISS for vector similarity search with sentence-transformers embeddings.

Based on: FinGPT-RAG (https://github.com/AI4Finance-Foundation/FinGPT/tree/master/fingpt/FinGPT_RAG)
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import hashlib

logger = logging.getLogger(__name__)

# Try to import FAISS and sentence-transformers
try:
    import faiss
    import numpy as np
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    logger.warning("FAISS not available - install with: pip install faiss-cpu")

try:
    from sentence_transformers import SentenceTransformer
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    logger.warning("sentence-transformers not available")


class DocumentStore:
    """Simple document store with vector embeddings for RAG."""
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """Initialize document store.
        
        Args:
            embedding_model: Sentence transformer model name
        """
        self.documents: List[Dict] = []
        self.embeddings: Optional[np.ndarray] = None
        self.index: Optional[faiss.IndexFlatL2] = None
        self.model: Optional[SentenceTransformer] = None
        self.embedding_dim = 384  # Default for MiniLM
        
        if EMBEDDINGS_AVAILABLE:
            try:
                self.model = SentenceTransformer(embedding_model)
                self.embedding_dim = self.model.get_sentence_embedding_dimension()
                logger.info(f"Loaded embedding model: {embedding_model}")
            except Exception as e:
                logger.warning(f"Failed to load embedding model: {e}")
        
        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatL2(self.embedding_dim)
    
    def add_document(self, text: str, metadata: Optional[Dict] = None) -> str:
        """Add a document to the store.
        
        Args:
            text: Document text
            metadata: Optional metadata dict
            
        Returns:
            Document ID
        """
        doc_id = hashlib.md5(text.encode()).hexdigest()[:12]
        
        doc = {
            "id": doc_id,
            "text": text,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.documents.append(doc)
        
        # Add embedding if available
        if self.model and self.index:
            embedding = self.model.encode([text])
            self.index.add(embedding.astype('float32'))
        
        return doc_id
    
    def add_documents(self, texts: List[str], metadatas: Optional[List[Dict]] = None) -> List[str]:
        """Add multiple documents."""
        metadatas = metadatas or [{}] * len(texts)
        return [self.add_document(t, m) for t, m in zip(texts, metadatas)]
    
    def search(self, query: str, k: int = 3) -> List[Dict]:
        """Search for similar documents.
        
        Args:
            query: Search query
            k: Number of results to return
            
        Returns:
            List of similar documents with scores
        """
        if not self.model or not self.index or self.index.ntotal == 0:
            # Fallback to simple keyword search
            return self._keyword_search(query, k)
        
        # Vector search
        query_embedding = self.model.encode([query]).astype('float32')
        distances, indices = self.index.search(query_embedding, min(k, len(self.documents)))
        
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx < len(self.documents):
                doc = self.documents[idx].copy()
                doc["score"] = float(1 / (1 + dist))  # Convert distance to similarity
                results.append(doc)
        
        return results
    
    def _keyword_search(self, query: str, k: int) -> List[Dict]:
        """Simple keyword-based fallback search."""
        query_words = set(query.lower().split())
        
        scored_docs = []
        for doc in self.documents:
            doc_words = set(doc["text"].lower().split())
            overlap = len(query_words & doc_words)
            if overlap > 0:
                scored_docs.append((overlap / len(query_words), doc))
        
        scored_docs.sort(reverse=True, key=lambda x: x[0])
        
        return [
            {**doc, "score": score} 
            for score, doc in scored_docs[:k]
        ]
    
    def clear(self):
        """Clear all documents."""
        self.documents = []
        if FAISS_AVAILABLE:
            self.index = faiss.IndexFlatL2(self.embedding_dim)


class RAGService:
    """RAG service for enhanced chatbot responses."""
    
    def __init__(self):
        """Initialize RAG service."""
        self.document_store = DocumentStore()
        self._initialized = False
    
    def initialize_with_financial_knowledge(self):
        """Load base financial knowledge into the document store."""
        if self._initialized:
            return
        
        # Add financial concepts
        financial_concepts = [
            {
                "text": "Delta measures how much an option's price changes for a $1 move in the underlying stock. Call options have positive delta (0 to 1), put options have negative delta (-1 to 0). ATM options have delta around 0.5.",
                "metadata": {"topic": "options", "concept": "delta"}
            },
            {
                "text": "Gamma measures the rate of change in delta for each $1 move in the underlying. Gamma is highest for ATM options and increases as expiration approaches. High gamma means delta can change quickly.",
                "metadata": {"topic": "options", "concept": "gamma"}
            },
            {
                "text": "Theta represents time decay - how much value an option loses each day. Long options have negative theta (lose value over time), while short options benefit from time decay.",
                "metadata": {"topic": "options", "concept": "theta"}
            },
            {
                "text": "Implied Volatility (IV) represents the market's expectation of future price movement. High IV means expensive options, low IV means cheap options. IV Rank compares current IV to historical range.",
                "metadata": {"topic": "options", "concept": "iv"}
            },
            {
                "text": "The Sharpe Ratio measures risk-adjusted returns: (Portfolio Return - Risk-Free Rate) / Portfolio Volatility. Higher Sharpe ratios indicate better risk-adjusted performance.",
                "metadata": {"topic": "portfolio", "concept": "sharpe"}
            },
            {
                "text": "Mean reversion is a trading strategy based on the idea that prices tend to return to their average over time. Pairs trading exploits temporary price divergences between correlated assets.",
                "metadata": {"topic": "strategy", "concept": "mean_reversion"}
            },
            {
                "text": "RSI (Relative Strength Index) measures momentum on a scale of 0-100. Values above 70 indicate overbought conditions, below 30 indicate oversold. Used to identify potential reversals.",
                "metadata": {"topic": "technical", "concept": "rsi"}
            },
            {
                "text": "MACD (Moving Average Convergence Divergence) shows the relationship between two moving averages. A bullish signal occurs when MACD crosses above the signal line.",
                "metadata": {"topic": "technical", "concept": "macd"}
            }
        ]
        
        for concept in financial_concepts:
            self.document_store.add_document(
                concept["text"], 
                concept["metadata"]
            )
        
        self._initialized = True
        logger.info(f"Initialized RAG with {len(financial_concepts)} financial concepts")
    
    def add_news_context(self, news_items: List[Dict]):
        """Add news articles to the document store.
        
        Args:
            news_items: List of news dicts with 'headline', 'summary', 'symbol'
        """
        for item in news_items:
            text = f"{item.get('headline', '')}. {item.get('summary', '')}"
            metadata = {
                "type": "news",
                "symbol": item.get("symbol", ""),
                "source": item.get("source", ""),
                "date": item.get("datetime", "")
            }
            self.document_store.add_document(text, metadata)
    
    def retrieve_context(self, query: str, k: int = 3) -> str:
        """Retrieve relevant context for a query.
        
        Args:
            query: User query
            k: Number of documents to retrieve
            
        Returns:
            Formatted context string
        """
        self.initialize_with_financial_knowledge()
        
        results = self.document_store.search(query, k)
        
        if not results:
            return ""
        
        context_parts = ["[Retrieved Context]"]
        for i, doc in enumerate(results, 1):
            score = doc.get("score", 0)
            context_parts.append(f"{i}. {doc['text'][:300]} (relevance: {score:.2f})")
        
        return "\n".join(context_parts)
    
    def get_augmented_prompt(self, query: str) -> Tuple[str, List[Dict]]:
        """Get query augmented with retrieved context.
        
        Args:
            query: Original user query
            
        Returns:
            Tuple of (augmented_prompt, retrieved_docs)
        """
        self.initialize_with_financial_knowledge()
        
        results = self.document_store.search(query, k=3)
        
        if not results:
            return query, []
        
        context = "\n".join([doc["text"][:200] for doc in results])
        
        augmented = f"""Use the following context to help answer the question:

{context}

User Question: {query}"""
        
        return augmented, results


# Module-level singleton
_rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Get or create RAG service singleton."""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service


def retrieve_context_for_query(query: str, k: int = 3) -> str:
    """Convenience function to retrieve context.
    
    Args:
        query: User query
        k: Number of documents
        
    Returns:
        Context string or empty string
    """
    service = get_rag_service()
    return service.retrieve_context(query, k)
