"""
Local LLM Connector

Provides abstraction for local LLM inference:
- GPT4All (local)
- Ollama (local server)
- Mock (for testing)

Environment variables:
- LLM_PROVIDER: gpt4all|ollama|mock (default: mock)
- OLLAMA_HOST: Ollama server URL (default: http://localhost:11434)
- GPT4ALL_MODEL: GPT4All model name (default: orca-mini-3b-gguf2-q4_0.gguf)
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import hashlib

logger = logging.getLogger(__name__)


class LLMConnector(ABC):
    """Abstract base class for LLM connectors."""
    
    @abstractmethod
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate text from prompt."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the LLM is available."""
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get connector name."""
        pass


class MockLLMConnector(LLMConnector):
    """
    Mock LLM for testing and fallback.
    
    Generates deterministic responses based on prompt hash.
    """
    
    def __init__(self):
        self._available = True
    
    @property
    def name(self) -> str:
        return "mock"
    
    def is_available(self) -> bool:
        return self._available
    
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate deterministic mock response."""
        # Extract query from prompt if present
        query = ""
        if "Question:" in prompt:
            parts = prompt.split("Question:")
            if len(parts) > 1:
                query = parts[1].split("\n")[0].strip()[:100]
        elif "Query:" in prompt:
            parts = prompt.split("Query:")
            if len(parts) > 1:
                query = parts[1].split("\n")[0].strip()[:100]
        else:
            query = prompt[:100]
        
        # Generate deterministic response based on query
        seed = int(hashlib.md5(query.encode()).hexdigest()[:8], 16)
        
        responses = [
            f"Based on the provided context, {query.lower()} relates to market momentum factors and sector analysis. The research indicates positive signals in technology stocks with strong momentum characteristics.",
            f"Analyzing the documents for '{query}': The data suggests focusing on factor exposures, particularly momentum and value metrics. Historical analysis shows these factors have predictive power.",
            f"In response to your query about {query.lower()}: The research briefs indicate this topic connects to current market trends and sector rotation patterns. Consider both fundamental and technical indicators.",
            f"The research documents provide insights on {query.lower()}. Key findings include momentum persistence in trending markets and value opportunities in oversold sectors.",
            f"Based on indexed research, {query.lower()} is addressed across multiple documents. The consensus suggests careful analysis of factor exposures and market conditions."
        ]
        
        return responses[seed % len(responses)]


class GPT4AllConnector(LLMConnector):
    """
    GPT4All local LLM connector.
    
    Uses GPT4All Python bindings for local inference.
    """
    
    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or os.getenv("GPT4ALL_MODEL", "orca-mini-3b-gguf2-q4_0.gguf")
        self._model = None
        self._available = None
    
    @property
    def name(self) -> str:
        return "gpt4all"
    
    def is_available(self) -> bool:
        if self._available is None:
            try:
                from gpt4all import GPT4All
                self._available = True
            except ImportError:
                logger.warning("gpt4all package not installed")
                self._available = False
        return self._available
    
    def _load_model(self):
        """Lazy load the GPT4All model."""
        if self._model is None and self.is_available():
            try:
                from gpt4all import GPT4All
                self._model = GPT4All(self.model_name)
                logger.info(f"Loaded GPT4All model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to load GPT4All model: {e}")
                self._available = False
    
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate text using GPT4All."""
        self._load_model()
        
        if self._model is None:
            raise RuntimeError("GPT4All model not available")
        
        try:
            response = self._model.generate(
                prompt,
                max_tokens=max_tokens,
                temp=temperature
            )
            return response
        except Exception as e:
            logger.error(f"GPT4All generation failed: {e}")
            raise


class OllamaConnector(LLMConnector):
    """
    Ollama local LLM server connector.
    
    Connects to Ollama API for local inference.
    """
    
    def __init__(self, host: Optional[str] = None, model: str = "llama2"):
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.model = model
        self._available = None
    
    @property
    def name(self) -> str:
        return "ollama"
    
    def is_available(self) -> bool:
        if self._available is None:
            try:
                import requests
                response = requests.get(f"{self.host}/api/tags", timeout=2)
                self._available = response.status_code == 200
            except Exception:
                self._available = False
        return self._available
    
    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.7) -> str:
        """Generate text using Ollama API."""
        if not self.is_available():
            raise RuntimeError("Ollama server not available")
        
        try:
            import requests
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature
                    }
                },
                timeout=60
            )
            
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                raise RuntimeError(f"Ollama API error: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            raise


def get_llm_connector(provider: Optional[str] = None) -> LLMConnector:
    """
    Get an LLM connector based on provider setting.
    
    Falls back to mock if specified provider is unavailable.
    
    Args:
        provider: LLM provider name (gpt4all, ollama, mock)
        
    Returns:
        LLMConnector instance
    """
    provider = provider or os.getenv("LLM_PROVIDER", "mock")
    
    # In deterministic mode, always use mock
    if os.getenv("RL_DETERMINISTIC", "0") == "1":
        logger.info("Deterministic mode: using mock LLM")
        return MockLLMConnector()
    
    if provider == "gpt4all":
        connector = GPT4AllConnector()
        if connector.is_available():
            return connector
        logger.warning("GPT4All not available, falling back to mock")
        return MockLLMConnector()
    
    elif provider == "ollama":
        connector = OllamaConnector()
        if connector.is_available():
            return connector
        logger.warning("Ollama not available, falling back to mock")
        return MockLLMConnector()
    
    else:
        return MockLLMConnector()


class RAGQueryEngine:
    """
    RAG Query Engine that combines vector search with LLM generation.
    """
    
    def __init__(self, llm_connector: Optional[LLMConnector] = None):
        self.llm = llm_connector or get_llm_connector()
        self._pipeline = None
    
    @property
    def pipeline(self):
        """Lazy load ingestion pipeline."""
        if self._pipeline is None:
            from background.research_ingest import get_pipeline
            self._pipeline = get_pipeline()
        return self._pipeline
    
    def query(self, question: str, top_k: int = 5, sources: str = "all") -> Dict[str, Any]:
        """
        Execute a RAG query.
        
        Args:
            question: The question to answer
            top_k: Number of source documents to retrieve
            sources: Source filter (all, briefs, news, docs)
            
        Returns:
            Dict with answer, sources, and metadata
        """
        # Retrieve relevant documents
        search_results = self.pipeline.search(question, top_k=top_k)
        
        # Filter by source type if specified
        if sources and sources != "all":
            search_results = [
                r for r in search_results 
                if self._matches_source_filter(r, sources)
            ]
        
        # Build context from retrieved documents
        context = self._build_context(search_results)
        
        # Generate prompt
        prompt = self._build_prompt(question, context)
        
        # Generate answer
        try:
            answer = self.llm.generate(prompt, max_tokens=512)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            answer = f"Unable to generate answer: {str(e)}"
        
        # Create answer ID for tracking
        answer_id = hashlib.md5(f"{question}{answer}".encode()).hexdigest()[:12]
        
        return {
            "answer_id": answer_id,
            "answer": answer,
            "sources": search_results,
            "llm_provider": self.llm.name,
            "top_k": top_k,
            "query": question
        }
    
    def explain(self, answer_id: str) -> Dict[str, Any]:
        """
        Get explanation for a previous answer.
        
        Args:
            answer_id: ID of the answer to explain
            
        Returns:
            Explanation dict
        """
        # In a full implementation, we would store answers and their provenance
        # For now, return a generic explanation
        return {
            "answer_id": answer_id,
            "method": "Vector similarity search + LLM generation",
            "retrieval_method": "FAISS L2 distance",
            "llm_provider": self.llm.name,
            "explanation": "Retrieved top-k documents by vector similarity, "
                          "constructed context window, and generated response using LLM."
        }
    
    def _matches_source_filter(self, result: Dict, source_filter: str) -> bool:
        """Check if result matches source filter."""
        doc = self.pipeline.get_document(result.get("doc_id"))
        if not doc:
            return True
        
        source_type = doc.source_type
        
        if source_filter == "briefs":
            return source_type in ("brief", "text")
        elif source_filter == "news":
            return source_type == "news"
        elif source_filter == "docs":
            return source_type in ("pdf", "url")
        
        return True
    
    def _build_context(self, results: List[Dict]) -> str:
        """Build context string from search results."""
        if not results:
            return "No relevant documents found."
        
        context_parts = []
        for i, result in enumerate(results, 1):
            context_parts.append(
                f"[Document {i}: {result.get('title', 'Untitled')}]\n"
                f"{result.get('snippet', '')}\n"
            )
        
        return "\n".join(context_parts)
    
    def _build_prompt(self, question: str, context: str) -> str:
        """Build the LLM prompt."""
        return f"""You are a research assistant analyzing financial documents. 
Answer the question based on the provided context. Be concise and cite specific sources when possible.

Context:
{context}

Question: {question}

Answer:"""


# Singleton engine
_query_engine = None


def get_query_engine() -> RAGQueryEngine:
    """Get or create the query engine singleton."""
    global _query_engine
    if _query_engine is None:
        _query_engine = RAGQueryEngine()
    return _query_engine
