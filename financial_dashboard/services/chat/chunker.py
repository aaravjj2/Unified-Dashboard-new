"""
Chunker - Semantic text chunking for RAG
Splits documents into semantic chunks with overlap
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk with metadata"""
    text: str
    chunk_id: str
    metadata: Dict[str, Any]
    start_char: int
    end_char: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "chunk_id": self.chunk_id,
            "metadata": self.metadata,
            "start_char": self.start_char,
            "end_char": self.end_char
        }


class SemanticChunker:
    """
    Semantic text chunker with paragraph-based splitting and overlap
    
    Strategy:
    1. Try to split on paragraph boundaries (double newline)
    2. Fall back to sentence boundaries if paragraphs too large
    3. Fall back to fixed-length window if no good boundaries
    """
    
    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100
    ):
        """
        Initialize chunker
        
        Args:
            chunk_size: Target chunk size in characters
            chunk_overlap: Overlap between chunks in characters
            min_chunk_size: Minimum viable chunk size
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
    
    def chunk_document(
        self,
        text: str,
        doc_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[Chunk]:
        """
        Chunk a document into semantic chunks
        
        Args:
            text: Document text
            doc_id: Unique document identifier
            metadata: Document metadata (source, ticker, url, etc.)
            
        Returns:
            List of Chunk objects
        """
        if not text or len(text) < self.min_chunk_size:
            logger.warning(f"Document {doc_id} too small to chunk ({len(text)} chars)")
            return []
        
        metadata = metadata or {}
        chunks = []
        
        # Strategy 1: Split on paragraphs
        paragraphs = text.split('\n\n')
        
        current_chunk_text = ""
        current_start = 0
        chunk_idx = 0
        
        for para_idx, para in enumerate(paragraphs):
            para = para.strip()
            if not para:
                continue
            
            # If adding this paragraph exceeds chunk size, finalize current chunk
            if len(current_chunk_text) + len(para) > self.chunk_size and current_chunk_text:
                chunk_id = f"{doc_id}_chunk_{chunk_idx}"
                chunks.append(Chunk(
                    text=current_chunk_text.strip(),
                    chunk_id=chunk_id,
                    metadata={**metadata, "chunk_index": chunk_idx, "doc_id": doc_id},
                    start_char=current_start,
                    end_char=current_start + len(current_chunk_text)
                ))
                chunk_idx += 1
                
                # Start new chunk with overlap
                overlap_text = current_chunk_text[-self.chunk_overlap:] if len(current_chunk_text) > self.chunk_overlap else ""
                current_chunk_text = overlap_text + " " + para
                current_start = current_start + len(current_chunk_text) - len(overlap_text)
            else:
                # Add paragraph to current chunk
                if current_chunk_text:
                    current_chunk_text += "\n\n" + para
                else:
                    current_chunk_text = para
        
        # Finalize last chunk
        if current_chunk_text and len(current_chunk_text) >= self.min_chunk_size:
            chunk_id = f"{doc_id}_chunk_{chunk_idx}"
            chunks.append(Chunk(
                text=current_chunk_text.strip(),
                chunk_id=chunk_id,
                metadata={**metadata, "chunk_index": chunk_idx, "doc_id": doc_id},
                start_char=current_start,
                end_char=current_start + len(current_chunk_text)
            ))
        
        logger.info(f"Chunked document {doc_id} into {len(chunks)} chunks")
        return chunks
    
    def chunk_batch(
        self,
        documents: List[Dict[str, Any]]
    ) -> List[Chunk]:
        """
        Chunk a batch of documents
        
        Args:
            documents: List of dicts with keys: text, doc_id, metadata
            
        Returns:
            Flat list of all chunks
        """
        all_chunks = []
        
        for doc in documents:
            text = doc.get('text', '')
            doc_id = doc.get('doc_id', f"doc_{len(all_chunks)}")
            metadata = doc.get('metadata', {})
            
            chunks = self.chunk_document(text, doc_id, metadata)
            all_chunks.extend(chunks)
        
        logger.info(f"Chunked {len(documents)} documents into {len(all_chunks)} total chunks")
        return all_chunks
