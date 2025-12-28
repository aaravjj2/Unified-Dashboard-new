#!/usr/bin/env python3
"""
Build the RAG index with sample financial data.
Run this script once to initialize the vector database for testing.
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from financial_dashboard.agents.fingpt_ingest import create_sample_financial_data
from financial_dashboard.services.rag.indexer import build_index


def main():
    """Build the RAG index with sample data."""
    print("=" * 60)
    print("Building RAG Index with Sample Financial Data")
    print("=" * 60)
    
    # Get sample documents
    print("\n[1/3] Creating sample financial documents...")
    documents = create_sample_financial_data()
    print(f"   ✓ Created {len(documents)} sample documents")
    
    # Build index
    print("\n[2/3] Building vector index...")
    index_dir = project_root / "data" / "rag_index"
    
    try:
        result = build_index(
            documents=documents,
            index_dir=str(index_dir),
            embeddings_model="sentence-transformers/all-mpnet-base-v2",
            collection_name="financial_docs"
        )
        
        if result['success']:
            print(f"   ✓ Index built successfully")
            print(f"   - Documents indexed: {result['document_count']}")
            print(f"   - Index directory: {result['index_dir']}")
            print(f"   - Timestamp: {result['timestamp']}")
        else:
            print(f"   ✗ Index build failed")
            return 1
            
    except Exception as e:
        print(f"   ✗ Error building index: {e}")
        print("\n   Make sure chromadb is installed:")
        print("   pip install chromadb sentence-transformers")
        return 1
    
    # Test query
    print("\n[3/3] Testing retrieval...")
    try:
        from financial_dashboard.services.rag import query_retriever
        
        test_query = "What is Apple's earnings performance?"
        results = query_retriever(test_query, top_k=3)
        
        print(f"   ✓ Retrieved {len(results)} results for test query")
        if results:
            print(f"\n   Top result:")
            print(f"   - Source: {results[0]['metadata'].get('source', 'unknown')}")
            print(f"   - Score: {results[0]['score']:.3f}")
            print(f"   - Snippet: {results[0]['text'][:100]}...")
        
    except Exception as e:
        print(f"   ✗ Test query failed: {e}")
        return 1
    
    print("\n" + "=" * 60)
    print("✅ RAG Index Ready!")
    print("=" * 60)
    print("\nYou can now:")
    print("  1. Start the dashboard: python financial_dashboard/index.py")
    print("  2. Navigate to Research Lab > RAG Chat tab")
    print("  3. Ask questions like:")
    print("     - 'What are Apple's earnings results?'")
    print("     - 'Tell me about NVIDIA's AI chips'")
    print("     - 'What is portfolio beta?'")
    print("\n")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
