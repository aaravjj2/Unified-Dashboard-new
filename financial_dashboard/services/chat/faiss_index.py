"""
FAISS Index Manager
Persistent vector index with metadata mapping for RAG retrieval
"""

import os
import json
import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class FAISSIndex:
    """
    FAISS-based vector index with persistent storage
    
    Features:
    - Add chunks with embeddings
    - Search with metadata filtering
    - Persistent storage to disk
    - Metadata mapping (chunk_id -> metadata)
    """
    
    def __init__(
        self,
        index_dir: str = "data/faiss_index",
        embedding_dim: int = 384,
        index_type: str = "Flat"
    ):
        """
        Initialize FAISS index
        
        Args:
            index_dir: Directory for index files
            embedding_dim: Dimension of embeddings
            index_type: FAISS index type (Flat, IVF, HNSW)
        """
        self.index_dir = Path(index_dir)
        self.embedding_dim = embedding_dim
        self.index_type = index_type
        
        self.index_path = self.index_dir / "index.faiss"
        self.metadata_path = self.index_dir / "metadata.json"
        
        # Create directory if needed
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
        # Try to import faiss
        try:
            import faiss
            self.faiss = faiss
            self.has_faiss = True
            logger.info("FAISS library loaded successfully")
        except ImportError:
            self.has_faiss = False
            logger.warning("FAISS not available, using in-memory fallback")
        
        # Initialize index and metadata
        self._index = None
        self._metadata = {}  # Maps index_id -> chunk metadata
        self._chunk_id_map = {}  # Maps chunk_id -> index_id
        
        # Load existing index if available
        if self.index_path.exists() and self.metadata_path.exists():
            self.load()
        else:
            self._init_new_index()
    
    def _init_new_index(self):
        """Initialize a new empty index"""
        if self.has_faiss:
            if self.index_type == "Flat":
                self._index = self.faiss.IndexFlatL2(self.embedding_dim)
            elif self.index_type == "IVF":
                quantizer = self.faiss.IndexFlatL2(self.embedding_dim)
                self._index = self.faiss.IndexIVFFlat(quantizer, self.embedding_dim, 100)
            else:
                self._index = self.faiss.IndexFlatL2(self.embedding_dim)
            
            logger.info(f"Initialized new {self.index_type} index with dim={self.embedding_dim}")
        else:
            # Fallback: store embeddings in memory
            self._index = []
            logger.info("Using in-memory fallback index")
        
        self._metadata = {}
        self._chunk_id_map = {}
    
    def add(
        self,
        chunks: List[Dict[str, Any]],
        embeddings: np.ndarray
    ) -> int:
        """
        Add chunks with embeddings to index
        
        Args:
            chunks: List of chunk dicts (must have 'chunk_id', 'text', 'metadata')
            embeddings: Numpy array of shape (len(chunks), embedding_dim)
            
        Returns:
            Number of chunks added
        """
        if len(chunks) != len(embeddings):
            raise ValueError(f"Chunks count ({len(chunks)}) != embeddings count ({len(embeddings)})")
        
        # Get current index size
        current_size = self.size()
        
        # Add to FAISS index
        if self.has_faiss:
            self._index.add(embeddings.astype(np.float32))
        else:
            # Fallback: append to list
            if not isinstance(self._index, list):
                self._index = []
            for emb in embeddings:
                self._index.append(emb.astype(np.float32))
        
        # Add metadata mapping
        for idx, chunk in enumerate(chunks):
            index_id = current_size + idx
            chunk_id = chunk['chunk_id']
            
            self._metadata[index_id] = {
                "chunk_id": chunk_id,
                "text": chunk['text'],
                "metadata": chunk.get('metadata', {})
            }
            self._chunk_id_map[chunk_id] = index_id
        
        logger.info(f"Added {len(chunks)} chunks to index (new size: {self.size()})")
        return len(chunks)
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 8,
        filter_meta: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search index for similar chunks
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            filter_meta: Optional metadata filter (e.g., {"ticker": "AAPL"})
            
        Returns:
            List of dicts with keys: chunk_id, text, metadata, score
        """
        if self.size() == 0:
            logger.warning("Index is empty, returning no results")
            return []
        
        # Reshape query for FAISS
        query_vec = query_embedding.reshape(1, -1).astype(np.float32)
        
        # Search
        if self.has_faiss:
            # FAISS search
            distances, indices = self._index.search(query_vec, min(top_k * 2, self.size()))
            distances = distances[0]
            indices = indices[0]
        else:
            # Fallback: brute-force cosine similarity
            index_embeddings = np.array(self._index)
            similarities = np.dot(index_embeddings, query_vec.T).flatten()
            # Convert to L2 distance for consistency
            distances = 1.0 - similarities
            indices = np.argsort(distances)[:min(top_k * 2, len(self._index))]
            distances = distances[indices]
        
        # Collect results with metadata
        results = []
        for dist, idx in zip(distances, indices):
            if idx < 0 or idx >= self.size():
                continue
            
            meta_entry = self._metadata.get(int(idx), {})
            
            # Apply metadata filter if provided
            if filter_meta:
                chunk_meta = meta_entry.get('metadata', {})
                if not all(chunk_meta.get(k) == v for k, v in filter_meta.items()):
                    continue
            
            results.append({
                "chunk_id": meta_entry.get('chunk_id', f"idx_{idx}"),
                "text": meta_entry.get('text', ''),
                "metadata": meta_entry.get('metadata', {}),
                "score": float(dist)
            })
            
            if len(results) >= top_k:
                break
        
        logger.info(f"Search returned {len(results)} results (top_k={top_k})")
        return results
    
    def size(self) -> int:
        """Get number of vectors in index"""
        if self.has_faiss:
            return self._index.ntotal if self._index else 0
        else:
            return len(self._index) if isinstance(self._index, list) else 0
    
    def save(self):
        """Save index and metadata to disk"""
        try:
            if self.has_faiss and self._index:
                self.faiss.write_index(self._index, str(self.index_path))
                logger.info(f"Saved FAISS index to {self.index_path}")
            
            # Save metadata
            with open(self.metadata_path, 'w') as f:
                json.dump({
                    "metadata": {str(k): v for k, v in self._metadata.items()},
                    "chunk_id_map": self._chunk_id_map,
                    "size": self.size(),
                    "embedding_dim": self.embedding_dim
                }, f, indent=2)
            logger.info(f"Saved metadata to {self.metadata_path}")
            
        except Exception as e:
            logger.error(f"Failed to save index: {e}", exc_info=True)
    
    def load(self):
        """Load index and metadata from disk"""
        try:
            if self.has_faiss and self.index_path.exists():
                self._index = self.faiss.read_index(str(self.index_path))
                logger.info(f"Loaded FAISS index from {self.index_path} (size: {self._index.ntotal})")
            
            if self.metadata_path.exists():
                with open(self.metadata_path, 'r') as f:
                    data = json.load(f)
                    self._metadata = {int(k): v for k, v in data.get('metadata', {}).items()}
                    self._chunk_id_map = data.get('chunk_id_map', {})
                    logger.info(f"Loaded metadata from {self.metadata_path} ({len(self._metadata)} entries)")
            
        except Exception as e:
            logger.error(f"Failed to load index: {e}", exc_info=True)
            self._init_new_index()
    
    def health_check(self) -> Dict[str, Any]:
        """Check index health"""
        return {
            "size": self.size(),
            "has_faiss": self.has_faiss,
            "index_type": self.index_type,
            "embedding_dim": self.embedding_dim,
            "metadata_entries": len(self._metadata),
            "index_exists": self.index_path.exists(),
            "metadata_exists": self.metadata_path.exists()
        }


# Global singleton
_index_instance: Optional[FAISSIndex] = None


def get_index() -> FAISSIndex:
    """Get or create global index instance"""
    global _index_instance
    if _index_instance is None:
        _index_instance = FAISSIndex()
    return _index_instance
