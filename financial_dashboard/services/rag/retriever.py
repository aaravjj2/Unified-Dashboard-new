"""
RAG Retriever - query vector database and retrieve relevant documents.
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class RAGRetriever:
    """Retriever client for querying indexed documents."""
    
    def __init__(self, index_dir: str = None, embeddings_model: str = "sentence-transformers/all-mpnet-base-v2"):
        """
        Initialize retriever.
        
        Args:
            index_dir: Directory containing the vector index
            embeddings_model: Model name for embeddings
        """
        self.index_dir = index_dir or os.path.join(os.path.dirname(__file__), "../../../data/rag_index")
        self.embeddings_model = embeddings_model
        self.collection = None
        self._initialized = False
        
    def initialize(self):
        """Lazy initialization of vector DB connection."""
        if self._initialized:
            return
            
        try:
            import chromadb
            from chromadb.config import Settings
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=self.index_dir,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Load or create collection
            try:
                self.collection = self.client.get_collection("financial_docs")
                logger.info(f"Loaded existing collection with {self.collection.count()} documents")
            except Exception as e:
                logger.warning(f"Collection not found, will create on first index: {e}")
                self.collection = None
                
            self._initialized = True
            
        except ImportError:
            logger.error("chromadb not installed. Install with: pip install chromadb")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize retriever: {e}")
            raise
    
    def query(self, query_text: str, top_k: int = 5, filter_meta: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Query the vector database.
        
        Args:
            query_text: Query string
            top_k: Number of results to return
            filter_meta: Optional metadata filters
            
        Returns:
            List of results with score, text, and metadata
        """
        self.initialize()
        
        if not self.collection:
            logger.warning("No collection available, returning empty results")
            return []
        
        try:
            # Query ChromaDB
            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k,
                where=filter_meta
            )
            
            # Format results
            formatted_results = []
            if results and results['documents'] and len(results['documents']) > 0:
                docs = results['documents'][0]
                metadatas = results['metadatas'][0] if results['metadatas'] else [{}] * len(docs)
                distances = results['distances'][0] if results['distances'] else [0.0] * len(docs)
                
                for doc, meta, dist in zip(docs, metadatas, distances):
                    formatted_results.append({
                        'text': doc,
                        'score': 1.0 - dist,  # Convert distance to similarity score
                        'metadata': meta,
                        'source': meta.get('source', 'unknown'),
                        'date': meta.get('date', 'unknown')
                    })
            
            logger.info(f"Query returned {len(formatted_results)} results")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []
    
    def get_status(self) -> Dict[str, Any]:
        """Get retriever status."""
        try:
            self.initialize()
            if self.collection:
                count = self.collection.count()
                return {
                    'initialized': True,
                    'document_count': count,
                    'index_dir': self.index_dir,
                    'embeddings_model': self.embeddings_model
                }
            else:
                return {
                    'initialized': False,
                    'document_count': 0,
                    'index_dir': self.index_dir,
                    'message': 'No collection found'
                }
        except Exception as e:
            return {
                'initialized': False,
                'error': str(e)
            }


# Global retriever instance
_retriever_instance = None


def query_retriever(query_text: str, top_k: int = 5, filter_meta: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    Convenience function to query the global retriever instance.
    
    Args:
        query_text: Query string
        top_k: Number of results to return
        filter_meta: Optional metadata filters
        
    Returns:
        List of results
    """
    global _retriever_instance
    
    if _retriever_instance is None:
        _retriever_instance = RAGRetriever()
    
    return _retriever_instance.query(query_text, top_k, filter_meta)
