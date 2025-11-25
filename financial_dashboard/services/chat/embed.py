"""
Embedder - Text to vector embeddings
Uses sentence-transformers or fallback to deterministic hash-based pseudo-embeddings
"""

import os
import hashlib
import logging
import numpy as np
from typing import List, Optional

logger = logging.getLogger(__name__)


class Embedder:
    """
    Text embedder with fallback to deterministic pseudo-embeddings
    
    Supports:
    - sentence-transformers for production embeddings
    - Deterministic hash-based pseudo-embeddings for testing
    """
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        embedding_dim: int = 384,
        deterministic: bool = False
    ):
        """
        Initialize embedder
        
        Args:
            model_name: Name of sentence-transformer model
            embedding_dim: Embedding dimension
            deterministic: If True, use hash-based pseudo-embeddings
        """
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        self.deterministic = deterministic or os.getenv("OPTIONS_DETERMINISTIC") == "1"
        
        # Try to import sentence-transformers
        self._model = None
        if not self.deterministic:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(model_name)
                self.embedding_dim = self._model.get_sentence_embedding_dimension()
                logger.info(f"Loaded embedder: {model_name}, dim={self.embedding_dim}")
            except ImportError:
                logger.warning("sentence-transformers not available, using deterministic mode")
                self.deterministic = True
            except Exception as e:
                logger.warning(f"Failed to load embedder {model_name}: {e}, using deterministic mode")
                self.deterministic = True
    
    def embed(self, text: str) -> np.ndarray:
        """
        Embed a single text
        
        Args:
            text: Input text
            
        Returns:
            Numpy array of shape (embedding_dim,)
        """
        if self.deterministic or self._model is None:
            return self._deterministic_embed(text)
        
        try:
            embedding = self._model.encode(text, convert_to_numpy=True)
            return embedding
        except Exception as e:
            logger.error(f"Embedding failed: {e}, falling back to deterministic")
            return self._deterministic_embed(text)
    
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Embed a batch of texts
        
        Args:
            texts: List of input texts
            
        Returns:
            Numpy array of shape (len(texts), embedding_dim)
        """
        if self.deterministic or self._model is None:
            embeddings = [self._deterministic_embed(text) for text in texts]
            return np.array(embeddings)
        
        try:
            embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return embeddings
        except Exception as e:
            logger.error(f"Batch embedding failed: {e}, falling back to deterministic")
            embeddings = [self._deterministic_embed(text) for text in texts]
            return np.array(embeddings)
    
    def _deterministic_embed(self, text: str) -> np.ndarray:
        """
        Generate deterministic pseudo-embedding from text hash
        
        Useful for testing and fixtures
        
        Args:
            text: Input text
            
        Returns:
            Numpy array of shape (embedding_dim,)
        """
        # Hash the text to get deterministic seed
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        seed = int(text_hash[:8], 16)
        
        # Generate pseudo-random embedding with fixed seed
        rng = np.random.default_rng(seed)
        embedding = rng.standard_normal(self.embedding_dim)
        
        # Normalize to unit length (like real embeddings)
        embedding = embedding / np.linalg.norm(embedding)
        
        return embedding.astype(np.float32)


# Global singleton
_embedder_instance: Optional[Embedder] = None


def get_embedder() -> Embedder:
    """Get or create global embedder instance"""
    global _embedder_instance
    if _embedder_instance is None:
        _embedder_instance = Embedder()
    return _embedder_instance
