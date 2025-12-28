import pytest
from financial_dashboard.services.rag.ingestion_service import RAGDataIngestionService


def test_process_and_ingest_single_symbol_tags_ticker(monkeypatch, tmp_path):
    called = {}

    def fake_update_index(docs, index_dir=None, collection_name='financial_docs'):
        called['docs'] = docs
        return {'success': True, 'added_count': len(docs)}

    # Monkeypatch the update_index import in the rag package
    import financial_dashboard.services.rag as rag_pkg
    monkeypatch.setattr(rag_pkg, 'update_index', fake_update_index)

    svc = RAGDataIngestionService(index_dir=str(tmp_path))

    # Sample article that references a single symbol
    article = {
        'title': 'Test AAPL earnings',
        'content': 'Apple Q4 earnings beat expectations',
        'url': 'https://example.com/aapl-earnings',
        'published_at': '2024-12-01T12:00:00',
        'source': 'test',
        'symbols': ['AAPL']
    }

    count = svc.process_and_ingest_articles([article])
    assert count > 0

    # Ensure update_index was called and that at least one chunk metadata includes ticker=AAPL
    assert 'docs' in called
    docs = called['docs']
    assert any(d['metadata'].get('ticker') == 'AAPL' for d in docs)
