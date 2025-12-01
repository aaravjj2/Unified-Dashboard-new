"""
Research Ingestion Pipeline

Handles document ingestion for RAG:
- PDF, text, web pages, Finnhub news
- Text splitting and chunking
- Embedding computation (local model or mock)
- FAISS index management

Environment variables:
- RL_DETERMINISTIC=1: Use mock embeddings and fixtures
- EMBED_MODEL: Embedding model to use (default: mock)
"""

import os
import json
import logging
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Paths
DATA_DIR = Path(__file__).parent.parent / "data" / "rag"
FAISS_INDEX_PATH = DATA_DIR / "faiss_index"
METADATA_PATH = DATA_DIR / "faiss_index" / "metadata.json"
DOCUMENTS_PATH = DATA_DIR / "documents.json"
FIXTURES_DIR = Path(__file__).parent.parent / "reports" / "research_lab" / "fixtures"


@dataclass
class Document:
    """Represents an ingested document."""
    doc_id: str
    title: str
    content: str
    source_type: str  # pdf, text, url, news
    source_url: Optional[str]
    metadata: Dict[str, Any]
    chunks: List[str]
    chunk_embeddings: Optional[List[List[float]]]
    ingested_at: str
    

def is_deterministic() -> bool:
    """Check if running in deterministic test mode."""
    return os.getenv("RL_DETERMINISTIC", "0") == "1"


class ResearchIngestionPipeline:
    """
    Main ingestion pipeline for research documents.
    
    Supports:
    - PDF documents
    - Plain text
    - Web pages (basic)
    - Finnhub news articles
    """
    
    def __init__(self, embedding_model: str = "mock"):
        self.embedding_model = embedding_model
        self.embedding_dim = 384  # Standard for small models
        self.chunk_size = 500  # tokens
        self.chunk_overlap = 50
        
        # Ensure directories exist
        FAISS_INDEX_PATH.mkdir(parents=True, exist_ok=True)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        
        # Load existing documents
        self.documents: Dict[str, Document] = self._load_documents()
        
        # Initialize FAISS index
        self.index = None
        self._init_index()
    
    def _init_index(self):
        """Initialize or load FAISS index."""
        try:
            import faiss
            index_file = FAISS_INDEX_PATH / "index.faiss"
            
            if index_file.exists():
                self.index = faiss.read_index(str(index_file))
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            else:
                # Create new index
                self.index = faiss.IndexFlatL2(self.embedding_dim)
                logger.info("Created new FAISS index")
        except ImportError:
            logger.warning("FAISS not available, using mock index")
            self.index = MockFAISSIndex(self.embedding_dim)
        except Exception as e:
            logger.error(f"Failed to init FAISS: {e}")
            self.index = MockFAISSIndex(self.embedding_dim)
    
    def _load_documents(self) -> Dict[str, Document]:
        """Load documents from storage."""
        docs = {}
        if DOCUMENTS_PATH.exists():
            try:
                with open(DOCUMENTS_PATH, 'r') as f:
                    data = json.load(f)
                    for doc_data in data:
                        doc = Document(**doc_data)
                        docs[doc.doc_id] = doc
            except Exception as e:
                logger.error(f"Failed to load documents: {e}")
        return docs
    
    def _save_documents(self):
        """Persist documents to storage."""
        try:
            data = [asdict(doc) for doc in self.documents.values()]
            with open(DOCUMENTS_PATH, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save documents: {e}")
    
    def _save_index(self):
        """Persist FAISS index to disk."""
        try:
            import faiss
            if self.index and not isinstance(self.index, MockFAISSIndex):
                faiss.write_index(self.index, str(FAISS_INDEX_PATH / "index.faiss"))
            
            # Save metadata
            metadata = {
                "doc_count": len(self.documents),
                "vector_count": self.index.ntotal if self.index else 0,
                "embedding_dim": self.embedding_dim,
                "last_updated": datetime.now().isoformat()
            }
            with open(METADATA_PATH, 'w') as f:
                json.dump(metadata, f, indent=2)
                
        except ImportError:
            logger.warning("FAISS not available for saving")
        except Exception as e:
            logger.error(f"Failed to save index: {e}")
    
    def ingest_text(self, text: str, title: str, metadata: Optional[Dict] = None) -> Document:
        """
        Ingest plain text content.
        
        Args:
            text: The text content to ingest
            title: Document title
            metadata: Optional metadata dict
            
        Returns:
            Ingested Document object
        """
        doc_id = self._generate_doc_id(text)
        
        # Check if already exists
        if doc_id in self.documents:
            logger.info(f"Document {doc_id} already exists, skipping")
            return self.documents[doc_id]
        
        # Split into chunks
        chunks = self._split_text(text)
        
        # Compute embeddings
        embeddings = self._compute_embeddings(chunks)
        
        # Create document
        doc = Document(
            doc_id=doc_id,
            title=title,
            content=text,
            source_type="text",
            source_url=None,
            metadata=metadata or {},
            chunks=chunks,
            chunk_embeddings=embeddings,
            ingested_at=datetime.now().isoformat()
        )
        
        # Add to index
        self._add_to_index(doc)
        
        # Store
        self.documents[doc_id] = doc
        self._save_documents()
        self._save_index()
        
        logger.info(f"Ingested document {doc_id}: {title} ({len(chunks)} chunks)")
        return doc
    
    def ingest_pdf(self, pdf_path: str, metadata: Optional[Dict] = None) -> Optional[Document]:
        """
        Ingest PDF document.
        
        Args:
            pdf_path: Path to PDF file
            metadata: Optional metadata dict
            
        Returns:
            Ingested Document object or None if failed
        """
        try:
            # Try to extract text from PDF
            text = self._extract_pdf_text(pdf_path)
            if not text:
                logger.warning(f"No text extracted from PDF: {pdf_path}")
                return None
            
            title = Path(pdf_path).stem
            doc = self.ingest_text(text, title, {
                **(metadata or {}),
                "source_path": pdf_path
            })
            doc.source_type = "pdf"
            return doc
            
        except Exception as e:
            logger.error(f"Failed to ingest PDF {pdf_path}: {e}")
            return None
    
    def ingest_news(self, articles: List[Dict]) -> List[Document]:
        """
        Ingest news articles (e.g., from Finnhub).
        
        Args:
            articles: List of article dicts with 'headline', 'summary', 'url'
            
        Returns:
            List of ingested Document objects
        """
        docs = []
        for article in articles:
            text = f"{article.get('headline', '')}\n\n{article.get('summary', '')}"
            title = article.get('headline', 'Untitled News')
            
            doc = self.ingest_text(text, title, {
                "source": article.get('source', 'unknown'),
                "datetime": article.get('datetime'),
                "url": article.get('url'),
                "ticker": article.get('related', article.get('ticker'))
            })
            doc.source_type = "news"
            doc.source_url = article.get('url')
            docs.append(doc)
        
        return docs
    
    def _generate_doc_id(self, content: str) -> str:
        """Generate unique document ID from content hash."""
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _split_text(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
        # Simple word-based splitting
        words = text.split()
        chunks = []
        
        i = 0
        while i < len(words):
            chunk_words = words[i:i + self.chunk_size]
            chunks.append(' '.join(chunk_words))
            i += self.chunk_size - self.chunk_overlap
        
        return chunks if chunks else [text]
    
    def _compute_embeddings(self, chunks: List[str]) -> List[List[float]]:
        """Compute embeddings for text chunks."""
        if is_deterministic() or self.embedding_model == "mock":
            return self._mock_embeddings(chunks)
        
        try:
            # Try sentence-transformers
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            embeddings = model.encode(chunks)
            return embeddings.tolist()
        except ImportError:
            logger.warning("sentence-transformers not available, using mock")
            return self._mock_embeddings(chunks)
        except Exception as e:
            logger.error(f"Embedding failed: {e}, using mock")
            return self._mock_embeddings(chunks)
    
    def _mock_embeddings(self, chunks: List[str]) -> List[List[float]]:
        """Generate deterministic mock embeddings."""
        embeddings = []
        for chunk in chunks:
            # Use hash for deterministic values
            seed = int(hashlib.md5(chunk.encode()).hexdigest()[:8], 16)
            import random
            random.seed(seed)
            embedding = [random.gauss(0, 1) for _ in range(self.embedding_dim)]
            # Normalize
            norm = sum(x*x for x in embedding) ** 0.5
            embedding = [x/norm for x in embedding]
            embeddings.append(embedding)
        return embeddings
    
    def _add_to_index(self, doc: Document):
        """Add document embeddings to FAISS index."""
        if not doc.chunk_embeddings or not self.index:
            return
        
        try:
            import numpy as np
            embeddings = np.array(doc.chunk_embeddings, dtype='float32')
            self.index.add(embeddings)
        except Exception as e:
            logger.error(f"Failed to add to index: {e}")
    
    def _extract_pdf_text(self, pdf_path: str) -> Optional[str]:
        """Extract text from PDF file."""
        try:
            import PyPDF2
            with open(pdf_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text.strip()
        except ImportError:
            logger.warning("PyPDF2 not available, PDF extraction disabled")
            return None
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            return None
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search the index for relevant documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of matching document chunks with scores
        """
        if not self.index or self.index.ntotal == 0:
            return []
        
        # Compute query embedding
        query_embedding = self._compute_embeddings([query])[0]
        
        try:
            import numpy as np
            query_vec = np.array([query_embedding], dtype='float32')
            
            distances, indices = self.index.search(query_vec, min(top_k, self.index.ntotal))
            
            results = []
            # Map indices back to documents (simplified - assumes sequential chunk storage)
            chunk_idx = 0
            doc_chunk_map = []
            for doc_id, doc in self.documents.items():
                for i, chunk in enumerate(doc.chunks):
                    doc_chunk_map.append((doc_id, i, chunk))
            
            for idx, dist in zip(indices[0], distances[0]):
                if idx < len(doc_chunk_map):
                    doc_id, chunk_idx, chunk = doc_chunk_map[idx]
                    doc = self.documents.get(doc_id)
                    results.append({
                        "doc_id": doc_id,
                        "title": doc.title if doc else "Unknown",
                        "snippet": chunk[:300],
                        "score": float(1 / (1 + dist)),  # Convert distance to similarity
                        "chunk_index": chunk_idx
                    })
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    def get_document(self, doc_id: str) -> Optional[Document]:
        """Get document by ID."""
        return self.documents.get(doc_id)
    
    def get_stats(self) -> Dict:
        """Get index statistics."""
        return {
            "doc_count": len(self.documents),
            "vector_count": self.index.ntotal if self.index else 0,
            "embedding_dim": self.embedding_dim,
            "embedding_model": self.embedding_model
        }
    
    def rebuild_index(self):
        """Rebuild the entire FAISS index from stored documents."""
        try:
            import faiss
            self.index = faiss.IndexFlatL2(self.embedding_dim)
        except ImportError:
            self.index = MockFAISSIndex(self.embedding_dim)
        
        for doc in self.documents.values():
            if doc.chunk_embeddings:
                self._add_to_index(doc)
        
        self._save_index()
        logger.info(f"Rebuilt index with {self.index.ntotal} vectors")


class MockFAISSIndex:
    """Mock FAISS index for when FAISS is not available."""
    
    def __init__(self, dim: int):
        self.dim = dim
        self.vectors = []
        self.ntotal = 0
    
    def add(self, vectors):
        """Add vectors to mock index."""
        for v in vectors:
            self.vectors.append(v)
        self.ntotal = len(self.vectors)
    
    def search(self, query, k):
        """Simple brute-force search."""
        import numpy as np
        
        if not self.vectors:
            return np.array([[]]), np.array([[]])
        
        query = np.array(query)
        vectors = np.array(self.vectors)
        
        # Compute L2 distances
        distances = np.sum((vectors - query) ** 2, axis=1)
        
        # Get top-k
        k = min(k, len(distances))
        indices = np.argsort(distances)[:k]
        
        return np.array([distances[indices]]), np.array([indices])


# Singleton instance
_pipeline = None


def get_pipeline() -> ResearchIngestionPipeline:
    """Get or create the ingestion pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        model = os.getenv("EMBED_MODEL", "mock")
        _pipeline = ResearchIngestionPipeline(embedding_model=model)
    return _pipeline


def ingest_fixture_documents():
    """Load and ingest fixture documents for testing."""
    pipeline = get_pipeline()
    
    fixture_file = FIXTURES_DIR / "sample_documents.json"
    if fixture_file.exists():
        try:
            with open(fixture_file, 'r') as f:
                docs = json.load(f)
                for doc in docs:
                    pipeline.ingest_text(
                        doc.get("content", ""),
                        doc.get("title", "Untitled"),
                        doc.get("metadata", {})
                    )
            logger.info(f"Ingested {len(docs)} fixture documents")
        except Exception as e:
            logger.error(f"Failed to ingest fixtures: {e}")
    else:
        # Create sample fixtures
        sample_docs = [
            {
                "title": "Momentum Strategy Overview",
                "content": "Momentum investing is a strategy that aims to capitalize on the continuance of existing trends in the market. "
                          "Key factors include price momentum over 3-12 months, earnings momentum, and relative strength indicators. "
                          "Tech sector has shown strong momentum characteristics in recent periods."
            },
            {
                "title": "Value Investing Principles",
                "content": "Value investing focuses on identifying undervalued securities based on fundamental analysis. "
                          "Key metrics include P/E ratio, P/B ratio, dividend yield, and free cash flow. "
                          "Warren Buffett's approach emphasizes margin of safety and long-term holding periods."
            },
            {
                "title": "Market Trends Q4 2024",
                "content": "Current market conditions show rotation from growth to value sectors. "
                          "Interest rate expectations are driving bond yields higher. "
                          "Technology remains strong but valuations are stretched. "
                          "Healthcare showing defensive characteristics."
            }
        ]
        
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        with open(fixture_file, 'w') as f:
            json.dump(sample_docs, f, indent=2)
        
        for doc in sample_docs:
            pipeline.ingest_text(doc["content"], doc["title"])
        
        logger.info(f"Created and ingested {len(sample_docs)} sample fixture documents")
