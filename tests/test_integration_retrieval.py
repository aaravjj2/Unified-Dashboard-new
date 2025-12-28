import os
from datetime import datetime

from financial_dashboard.services.rag.indexer import build_index
from financial_dashboard.services.rag.retriever import RAGRetriever


def test_chromadb_integration_retrieval(tmp_path):
    index_dir = str(tmp_path / 'rag_index')

    docs = [
        {
            'id': 'test_doc_1',
            'text': 'Test document about TEST ticker and its earnings',
            'metadata': {
                'title': 'Test doc',
                'source': 'test',
                'published_at': datetime.utcnow().isoformat(),
                'ticker': 'TEST'
            }
        }
    ]

    # Build a fresh index in tmp folder
    build_index(docs, index_dir=index_dir)

    # Query with retriever pointed at our tmp index
    retriever = RAGRetriever(index_dir=index_dir)
    results = retriever.query('TEST', top_k=5, filter_meta={'ticker': 'TEST'})

    assert results and any(r['metadata'].get('ticker') == 'TEST' for r in results)
