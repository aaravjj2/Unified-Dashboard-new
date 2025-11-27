#!/usr/bin/env python3
"""
FAISS Index Rebuild Script

Rebuilds the research RAG vector index from stored documents.

Usage:
    python scripts/rebuild_faiss.py [--force]

Options:
    --force     Force rebuild even if index exists
"""

import sys
import os
import argparse
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Rebuild FAISS index for research RAG")
    parser.add_argument("--force", action="store_true", help="Force rebuild even if index exists")
    parser.add_argument("--load-fixtures", action="store_true", help="Load fixture documents first")
    args = parser.parse_args()
    
    try:
        from background.research_ingest import get_pipeline, ingest_fixture_documents
        
        pipeline = get_pipeline()
        
        # Load fixtures if requested
        if args.load_fixtures:
            logger.info("Loading fixture documents...")
            ingest_fixture_documents()
        
        # Get current stats
        stats = pipeline.get_stats()
        logger.info(f"Current index stats: {stats}")
        
        # Rebuild if forced or no vectors
        if args.force or stats["vector_count"] == 0:
            logger.info("Rebuilding FAISS index...")
            pipeline.rebuild_index()
            
            new_stats = pipeline.get_stats()
            logger.info(f"Rebuild complete. New stats: {new_stats}")
        else:
            logger.info("Index already exists. Use --force to rebuild.")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to rebuild index: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
