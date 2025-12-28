"""
Tests for FinGPT RAG Service
============================
Unit tests for document retrieval and RAG functionality.
"""

import pytest


class TestDocumentStore:
    """Test document store functionality."""
    
    def test_document_store_initialization(self):
        """Test store initializes correctly."""
        from financial_dashboard.services.fingpt_rag_service import DocumentStore
        
        store = DocumentStore()
        assert store is not None
        assert len(store.documents) == 0
    
    def test_add_document(self):
        """Test adding a document."""
        from financial_dashboard.services.fingpt_rag_service import DocumentStore
        
        store = DocumentStore()
        doc_id = store.add_document("Delta measures option sensitivity to stock price")
        
        assert doc_id is not None
        assert len(store.documents) == 1
        assert "Delta" in store.documents[0]["text"]
    
    def test_add_multiple_documents(self):
        """Test adding multiple documents."""
        from financial_dashboard.services.fingpt_rag_service import DocumentStore
        
        store = DocumentStore()
        ids = store.add_documents([
            "Theta is time decay",
            "Gamma is rate of delta change",
            "Vega is volatility sensitivity"
        ])
        
        assert len(ids) == 3
        assert len(store.documents) == 3
    
    def test_keyword_search_fallback(self):
        """Test keyword-based search when FAISS not available."""
        from financial_dashboard.services.fingpt_rag_service import DocumentStore
        
        store = DocumentStore()
        store.add_documents([
            "Stock price increased by 10%",
            "Market volatility is high",
            "Earnings beat expectations"
        ])
        
        results = store._keyword_search("stock price", k=2)
        
        assert len(results) <= 2
        # First result should contain "stock price"
        if results:
            assert results[0]["score"] > 0
    
    def test_clear_documents(self):
        """Test clearing documents."""
        from financial_dashboard.services.fingpt_rag_service import DocumentStore
        
        store = DocumentStore()
        store.add_document("Test document")
        assert len(store.documents) == 1
        
        store.clear()
        assert len(store.documents) == 0


class TestRAGService:
    """Test RAG service functionality."""
    
    def test_rag_service_initialization(self):
        """Test RAG service initializes."""
        from financial_dashboard.services.fingpt_rag_service import RAGService
        
        service = RAGService()
        assert service is not None
    
    def test_initialize_financial_knowledge(self):
        """Test loading financial knowledge base."""
        from financial_dashboard.services.fingpt_rag_service import RAGService
        
        service = RAGService()
        service.initialize_with_financial_knowledge()
        
        assert service._initialized
        assert len(service.document_store.documents) > 0
    
    def test_retrieve_context_delta(self):
        """Test retrieving context for delta question."""
        from financial_dashboard.services.fingpt_rag_service import RAGService
        
        service = RAGService()
        service.initialize_with_financial_knowledge()
        
        context = service.retrieve_context("What is delta in options?")
        
        assert "delta" in context.lower() or "Delta" in context
    
    def test_retrieve_context_sharpe(self):
        """Test retrieving context for Sharpe ratio."""
        from financial_dashboard.services.fingpt_rag_service import RAGService
        
        service = RAGService()
        service.initialize_with_financial_knowledge()
        
        context = service.retrieve_context("How do I calculate Sharpe ratio?")
        
        assert "Sharpe" in context or "risk-adjusted" in context
    
    def test_get_augmented_prompt(self):
        """Test prompt augmentation."""
        from financial_dashboard.services.fingpt_rag_service import RAGService
        
        service = RAGService()
        service.initialize_with_financial_knowledge()
        
        augmented, docs = service.get_augmented_prompt("What is theta?")
        
        assert "theta" in augmented.lower() or "Theta" in augmented
        assert len(docs) > 0


class TestRAGSingleton:
    """Test RAG service singleton."""
    
    def test_singleton_pattern(self):
        """Test get_rag_service returns same instance."""
        from financial_dashboard.services.fingpt_rag_service import get_rag_service
        
        service1 = get_rag_service()
        service2 = get_rag_service()
        
        assert service1 is service2
    
    def test_convenience_function(self):
        """Test retrieve_context_for_query function."""
        from financial_dashboard.services.fingpt_rag_service import retrieve_context_for_query
        
        context = retrieve_context_for_query("What is RSI?")
        
        # Should return some context
        assert isinstance(context, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
