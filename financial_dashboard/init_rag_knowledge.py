"""
RAG Knowledge Base Initializer - Populates the vector store with financial documents
"""
import json
import os
import sys
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from financial_dashboard.llm.rag_pipeline import get_rag_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_knowledge_base():
    """Load the financial knowledge base JSON"""
    kb_path = os.path.join(
        os.path.dirname(__file__), 
        'data', 
        'rag_knowledge_base.json'
    )
    
    if not os.path.exists(kb_path):
        logger.error(f"Knowledge base not found at {kb_path}")
        return []
    
    with open(kb_path, 'r') as f:
        data = json.load(f)
    
    return data.get('documents', [])


def initialize_rag_knowledge():
    """Initialize the RAG vector store with financial knowledge"""
    logger.info("Loading RAG pipeline...")
    rag = get_rag_pipeline(deterministic=False)
    
    # Check if already populated
    vs = rag.vector_store
    if hasattr(vs, '_documents') and len(vs._documents) > 10:
        logger.info(f"Vector store already has {len(vs._documents)} documents")
        return len(vs._documents)
    
    # Load knowledge base
    logger.info("Loading knowledge base...")
    docs = load_knowledge_base()
    
    if not docs:
        logger.warning("No documents found in knowledge base")
        return 0
    
    logger.info(f"Found {len(docs)} documents to index")
    
    # Convert to document format for indexing
    formatted_docs = []
    for doc in docs:
        text = f"Title: {doc['title']}\n\n{doc['content']}"
        if doc.get('keywords'):
            text += f"\n\nKeywords: {', '.join(doc['keywords'])}"
        formatted_docs.append({
            'id': doc['id'],
            'text': text,
            'metadata': {
                'category': doc.get('category', 'general'),
                'title': doc['title']
            }
        })
    
    # Index documents
    logger.info("Indexing documents into vector store...")
    rag.index_documents(formatted_docs)
    
    logger.info(f"✅ Successfully indexed {len(formatted_docs)} documents")
    return len(formatted_docs)


def test_rag_queries():
    """Test some sample queries after initialization"""
    rag = get_rag_pipeline(deterministic=False)
    
    test_queries = [
        "What is delta in options?",
        "Tell me about Apple stock",
        "What is the RSI indicator?",
        "How does a covered call work?",
        "What is NVIDIA?"
    ]
    
    logger.info("\n--- Testing RAG Queries ---")
    for query in test_queries:
        result = rag.query(query, include_sources=True)
        logger.info(f"\nQ: {query}")
        logger.info(f"A: {result['answer'][:200]}...")
        logger.info(f"   Confidence: {result['confidence']:.0%}")
        if result.get('sources'):
            logger.info(f"   Sources: {len(result['sources'])} documents")
    
    return True


if __name__ == "__main__":
    count = initialize_rag_knowledge()
    print(f"\n✅ Indexed {count} documents into RAG vector store")
    
    if count > 0:
        test_rag_queries()
