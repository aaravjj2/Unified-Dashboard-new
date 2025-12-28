"""
RAG (Retrieval-Augmented Generation) service for Research Lab.
Provides document indexing, retrieval, and query augmentation.
"""
from .retriever import RAGRetriever, query_retriever
from .indexer import build_index, load_index, update_index
from .ingester import ingest_documents, chunk_text

__all__ = [
    'RAGRetriever',
    'query_retriever',
    'build_index',
    'load_index',
    'update_index',
    'ingest_documents',
    'chunk_text'
]
