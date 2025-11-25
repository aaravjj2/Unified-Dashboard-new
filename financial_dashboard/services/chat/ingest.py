"""
Ingest - Document ingestion pipeline
Chunks documents, generates embeddings, and indexes them
"""

import os
import json
import logging
from typing import List, Dict, Any
from pathlib import Path

from financial_dashboard.services.chat.chunker import SemanticChunker
from financial_dashboard.services.chat.embed import get_embedder
from financial_dashboard.services.chat.faiss_index import get_index

logger = logging.getLogger(__name__)


class IngestionPipeline:
    """
    Document ingestion pipeline
    
    Steps:
    1. Chunk documents
    2. Generate embeddings
    3. Index chunks
    """
    
    def __init__(self):
        """Initialize ingestion pipeline"""
        self.chunker = SemanticChunker(chunk_size=512, chunk_overlap=50)
        self.embedder = get_embedder()
        self.index = get_index()
    
    def ingest_documents(
        self,
        documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Ingest a batch of documents
        
        Args:
            documents: List of dicts with keys: text, doc_id, metadata
            
        Returns:
            Dict with ingestion stats
        """
        logger.info(f"Starting ingestion of {len(documents)} documents")
        
        # Step 1: Chunk documents
        chunks = self.chunker.chunk_batch(documents)
        
        if not chunks:
            logger.warning("No chunks created from documents")
            return {
                "documents": len(documents),
                "chunks": 0,
                "indexed": 0
            }
        
        # Step 2: Generate embeddings
        chunk_texts = [chunk.text for chunk in chunks]
        embeddings = self.embedder.embed_batch(chunk_texts)
        
        # Step 3: Prepare chunk dicts for indexing
        chunk_dicts = [chunk.to_dict() for chunk in chunks]
        
        # Step 4: Add to index
        indexed_count = self.index.add(chunk_dicts, embeddings)
        
        # Step 5: Save index
        self.index.save()
        
        logger.info(f"Ingestion complete: {len(documents)} docs -> {len(chunks)} chunks -> {indexed_count} indexed")
        
        return {
            "documents": len(documents),
            "chunks": len(chunks),
            "indexed": indexed_count
        }
    
    def ingest_fixtures(
        self,
        fixture_dir: str = "reports/chat_agent/fixtures"
    ) -> Dict[str, Any]:
        """
        Ingest documents from fixture directory
        
        Args:
            fixture_dir: Path to fixture directory
            
        Returns:
            Dict with ingestion stats
        """
        fixture_path = Path(fixture_dir)
        
        if not fixture_path.exists():
            logger.warning(f"Fixture directory does not exist: {fixture_dir}")
            return {"documents": 0, "chunks": 0, "indexed": 0}
        
        # Load fixture files
        documents = []
        
        for json_file in fixture_path.glob("*.json"):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    
                    # Convert fixture data to document format
                    if isinstance(data, list):
                        # Array of items
                        for idx, item in enumerate(data):
                            text = json.dumps(item, indent=2)
                            documents.append({
                                "text": text,
                                "doc_id": f"{json_file.stem}_{idx}",
                                "metadata": {
                                    "source": str(json_file),
                                    "fixture": True,
                                    "type": json_file.stem
                                }
                            })
                    else:
                        # Single object
                        text = json.dumps(data, indent=2)
                        documents.append({
                            "text": text,
                            "doc_id": json_file.stem,
                            "metadata": {
                                "source": str(json_file),
                                "fixture": True,
                                "type": json_file.stem
                            }
                        })
                
                logger.info(f"Loaded fixture: {json_file.name}")
                
            except Exception as e:
                logger.error(f"Failed to load fixture {json_file}: {e}")
        
        if not documents:
            logger.warning("No fixture documents loaded")
            return {"documents": 0, "chunks": 0, "indexed": 0}
        
        # Ingest the fixture documents
        return self.ingest_documents(documents)


def ingest_from_fixtures() -> Dict[str, Any]:
    """
    Convenience function to ingest from default fixture directory
    
    Returns:
        Dict with ingestion stats
    """
    pipeline = IngestionPipeline()
    return pipeline.ingest_fixtures()
