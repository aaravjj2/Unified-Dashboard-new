"""
RAG Indexer - build and manage vector indices for document retrieval.
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Union
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def build_index(
    documents: List[Dict[str, Any]],
    index_dir: str = None,
    embeddings_model: str = "sentence-transformers/all-mpnet-base-v2",
    collection_name: str = "financial_docs"
) -> Dict[str, Any]:
    """
    Build a vector index from documents.
    
    Args:
        documents: List of document dicts with 'text', 'metadata' keys
        index_dir: Directory to persist the index
        embeddings_model: Model for embeddings
        collection_name: Name of the collection
        
    Returns:
        Build metadata
    """
    if index_dir is None:
        index_dir = os.path.join(os.path.dirname(__file__), "../../../data/rag_index")
    
    os.makedirs(index_dir, exist_ok=True)
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        # Initialize ChromaDB client
        client = chromadb.PersistentClient(
            path=index_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Delete existing collection if it exists
        try:
            client.delete_collection(collection_name)
            logger.info(f"Deleted existing collection '{collection_name}'")
        except:
            pass
        
        # Create new collection
        collection = client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Prepare data for indexing
        ids = []
        texts = []
        metadatas = []
        
        for i, doc in enumerate(documents):
            doc_id = doc.get('id', f"doc_{i}")
            ids.append(doc_id)
            texts.append(doc['text'])
            
            # Ensure metadata is serializable
            meta = doc.get('metadata', {})
            if meta is None:
                meta = {}
            metadatas.append(meta)
        
        # Add documents to collection
        if ids:
            collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
        
        logger.info(f"Built index with {len(ids)} documents at {index_dir}")
        
        return {
            'success': True,
            'document_count': len(ids),
            'index_dir': index_dir,
            'collection_name': collection_name,
            'timestamp': datetime.now().isoformat()
        }
        
    except ImportError:
        logger.error("chromadb not installed. Install with: pip install chromadb")
        raise
    except Exception as e:
        logger.error(f"Failed to build index: {e}")
        raise


def load_index(index_dir: str = None, collection_name: str = "financial_docs") -> Dict[str, Any]:
    """
    Load an existing index and return metadata.
    
    Args:
        index_dir: Directory containing the index
        collection_name: Name of the collection
        
    Returns:
        Index metadata
    """
    if index_dir is None:
        index_dir = os.path.join(os.path.dirname(__file__), "../../../data/rag_index")
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        client = chromadb.PersistentClient(
            path=index_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        collection = client.get_collection(collection_name)
        count = collection.count()
        
        return {
            'success': True,
            'document_count': count,
            'index_dir': index_dir,
            'collection_name': collection_name
        }
        
    except Exception as e:
        logger.error(f"Failed to load index: {e}")
        return {
            'success': False,
            'error': str(e)
        }


def update_index(
    documents: List[Dict[str, Any]],
    index_dir: str = None,
    collection_name: str = "financial_docs"
) -> Dict[str, Any]:
    """
    Update existing index with new documents (incremental).
    
    Args:
        documents: New documents to add
        index_dir: Index directory
        collection_name: Collection name
        
    Returns:
        Update metadata
    """
    if index_dir is None:
        index_dir = os.path.join(os.path.dirname(__file__), "../../../data/rag_index")
    
    try:
        import chromadb
        from chromadb.config import Settings
        
        client = chromadb.PersistentClient(
            path=index_dir,
            settings=Settings(anonymized_telemetry=False)
        )
        
        collection = client.get_collection(collection_name)
        
        # Prepare data
        ids = []
        texts = []
        metadatas = []
        
        for i, doc in enumerate(documents):
            doc_id = doc.get('id', f"update_doc_{i}_{datetime.now().timestamp()}")
            ids.append(doc_id)
            texts.append(doc['text'])
            
            meta = doc.get('metadata', {})
            if meta is None:
                meta = {}
            metadatas.append(meta)
        
        # Add to collection
        if ids:
            collection.add(
                ids=ids,
                documents=texts,
                metadatas=metadatas
            )
        
        new_count = collection.count()
        
        logger.info(f"Updated index with {len(ids)} new documents. Total: {new_count}")
        
        return {
            'success': True,
            'added_count': len(ids),
            'total_count': new_count,
            'timestamp': datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to update index: {e}")
        raise
