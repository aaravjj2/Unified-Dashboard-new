"""
Document ingestion utilities for RAG.
Aliased from fingpt_ingest for consistency.
"""
from financial_dashboard.agents.fingpt_ingest import (
    chunk_text,
    ingest_documents,
    ingest_news_json,
    create_sample_financial_data
)

__all__ = [
    'chunk_text',
    'ingest_documents',
    'ingest_news_json',
    'create_sample_financial_data'
]
