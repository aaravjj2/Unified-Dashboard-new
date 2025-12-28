"""
FinGPT data ingestion utilities.
Converts various financial data sources into documents for RAG indexing.
"""
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def chunk_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 128,
    separator: str = "\n\n"
) -> List[str]:
    """
    Split text into overlapping chunks.
    
    Args:
        text: Text to chunk
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
        separator: Primary separator to respect
        
    Returns:
        List of text chunks
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    
    # Split by separator first
    parts = text.split(separator)
    
    current_chunk = ""
    for part in parts:
        if len(current_chunk) + len(part) + len(separator) <= chunk_size:
            current_chunk += part + separator
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = part + separator
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    # Add overlap between chunks
    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped = []
        for i, chunk in enumerate(chunks):
            if i > 0:
                # Add end of previous chunk to start of current
                prev_end = chunks[i-1][-chunk_overlap:] if len(chunks[i-1]) > chunk_overlap else chunks[i-1]
                chunk = prev_end + " [...] " + chunk
            overlapped.append(chunk)
        chunks = overlapped
    
    return chunks


def ingest_documents(
    source_paths: List[Path],
    chunk_size: int = 800,
    chunk_overlap: int = 128
) -> List[Dict[str, Any]]:
    """
    Ingest documents from various sources and prepare for indexing.
    
    Args:
        source_paths: List of file/directory paths
        chunk_size: Target chunk size
        chunk_overlap: Overlap size
        
    Returns:
        List of document dicts ready for indexing
    """
    documents = []
    doc_id = 0
    
    for source_path in source_paths:
        path = Path(source_path)
        
        if not path.exists():
            logger.warning(f"Source path does not exist: {path}")
            continue
        
        if path.is_file():
            docs = _ingest_file(path, doc_id, chunk_size, chunk_overlap)
            documents.extend(docs)
            doc_id += len(docs)
        elif path.is_dir():
            for file_path in path.rglob("*.txt"):
                docs = _ingest_file(file_path, doc_id, chunk_size, chunk_overlap)
                documents.extend(docs)
                doc_id += len(docs)
            for file_path in path.rglob("*.md"):
                docs = _ingest_file(file_path, doc_id, chunk_size, chunk_overlap)
                documents.extend(docs)
                doc_id += len(docs)
    
    logger.info(f"Ingested {len(documents)} document chunks from {len(source_paths)} sources")
    return documents


def _ingest_file(
    file_path: Path,
    start_id: int,
    chunk_size: int,
    chunk_overlap: int
) -> List[Dict[str, Any]]:
    """Ingest a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Get file metadata
        stat = file_path.stat()
        file_date = datetime.fromtimestamp(stat.st_mtime).isoformat()
        
        # Chunk the content
        chunks = chunk_text(content, chunk_size, chunk_overlap)
        
        # Create document entries
        documents = []
        for i, chunk in enumerate(chunks):
            documents.append({
                'id': f"doc_{start_id + i}",
                'text': chunk,
                'metadata': {
                    'source': str(file_path),
                    'filename': file_path.name,
                    'date': file_date,
                    'chunk_index': i,
                    'total_chunks': len(chunks)
                }
            })
        
        return documents
        
    except Exception as e:
        logger.error(f"Failed to ingest file {file_path}: {e}")
        return []


def ingest_news_json(json_path: Path) -> List[Dict[str, Any]]:
    """
    Ingest financial news from JSON format.
    
    Expected format: [{"title": str, "content": str, "date": str, "source": str}, ...]
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            news_items = json.load(f)
        
        documents = []
        for i, item in enumerate(news_items):
            text = f"{item.get('title', 'No title')}\n\n{item.get('content', '')}"
            
            documents.append({
                'id': f"news_{i}",
                'text': text,
                'metadata': {
                    'source': item.get('source', 'unknown'),
                    'date': item.get('date', 'unknown'),
                    'type': 'news',
                    'title': item.get('title', '')
                }
            })
        
        logger.info(f"Ingested {len(documents)} news items from {json_path}")
        return documents
        
    except Exception as e:
        logger.error(f"Failed to ingest news JSON: {e}")
        return []


def create_sample_financial_data() -> List[Dict[str, Any]]:
    """Create sample financial documents for testing."""
    sample_docs = [
        {
            'id': 'sample_1',
            'text': """Apple Inc. Reports Q4 Earnings Beat
            
Apple reported fourth-quarter earnings that exceeded analyst expectations, with revenue 
of $123.5 billion and EPS of $2.15. iPhone sales remained strong despite macroeconomic 
headwinds, and services revenue grew 8% year-over-year. The company also announced a 
new $90 billion share buyback program and raised its quarterly dividend by 4%.

Key highlights:
- Revenue: $123.5B (vs $121.2B expected)
- EPS: $2.15 (vs $2.10 expected)
- iPhone revenue: $51.3B
- Services revenue: $23.1B
- Gross margin: 45.2%

Management commentary emphasized the strength of the ecosystem and ongoing investments 
in AI and spatial computing technologies.""",
            'metadata': {
                'source': 'financial_news',
                'date': '2024-11-02',
                'ticker': 'AAPL',
                'type': 'earnings',
                'sentiment': 'positive'
            }
        },
        {
            'id': 'sample_2',
            'text': """Federal Reserve Holds Rates Steady, Signals Cautious Approach
            
The Federal Open Market Committee voted unanimously to maintain the federal funds rate 
target range at 5.25%-5.50%. In the accompanying statement, the Fed acknowledged recent 
progress on inflation but emphasized the need for sustained evidence before considering 
rate cuts.

Chair Powell's press conference highlighted:
- Inflation has moderated but remains above the 2% target
- The labor market remains resilient but is gradually cooling
- Economic growth has been stronger than expected
- Rate cuts are not imminent and will depend on data

Market reaction was mixed, with Treasury yields rising slightly and equities trading flat.""",
            'metadata': {
                'source': 'economic_news',
                'date': '2024-12-18',
                'type': 'monetary_policy',
                'category': 'macro'
            }
        },
        {
            'id': 'sample_3',
            'text': """NVIDIA Announces Next-Generation AI Chip Architecture
            
NVIDIA unveiled its Blackwell GPU architecture, promising 4x the training performance 
and 30x the inference performance compared to previous generation chips. The announcement 
sent NVIDIA shares up 7% in after-hours trading.

Technical specifications:
- 208 billion transistors
- 20 petaflops of FP4 performance
- 192GB HBM3e memory
- Second-generation Transformer Engine
- Support for trillion-parameter models

CEO Jensen Huang stated that Blackwell represents "the beginning of a new era in AI 
computing" and announced partnerships with major cloud providers including AWS, Google 
Cloud, and Microsoft Azure.""",
            'metadata': {
                'source': 'tech_news',
                'date': '2024-03-18',
                'ticker': 'NVDA',
                'type': 'product_announcement',
                'sentiment': 'very_positive'
            }
        },
        {
            'id': 'sample_4',
            'text': """Understanding Portfolio Beta and Market Sensitivity
            
Beta is a measure of a stock's volatility relative to the overall market. A beta of 1.0 
indicates that the stock moves in line with the market, while a beta greater than 1.0 
suggests higher volatility, and less than 1.0 indicates lower volatility.

Practical applications:
- Portfolio construction: Use high-beta stocks for aggressive growth strategies
- Risk management: Balance high-beta positions with low-beta defensive stocks
- Market timing: Adjust beta exposure based on market outlook

Calculation: Beta is computed as the covariance of the stock's returns with market 
returns divided by the variance of market returns. Most financial platforms calculate 
beta using 3-5 years of historical data.

Limitations: Beta is backward-looking and may not predict future volatility. It also 
assumes linear relationships and may be less reliable during market regime changes.""",
            'metadata': {
                'source': 'educational',
                'date': '2024-01-15',
                'type': 'tutorial',
                'category': 'risk_management',
                'topic': 'beta'
            }
        },
        {
            'id': 'sample_5',
            'text': """Oil Prices Surge on Middle East Supply Concerns
            
Crude oil prices jumped 5% on Monday following reports of escalating tensions in the 
Middle East. WTI crude settled at $89.23 per barrel, while Brent crude reached $93.87.

Market drivers:
- Geopolitical risks in key oil-producing regions
- OPEC+ production cuts remain in effect
- Strong demand from China and India
- Lower-than-expected US inventory builds

Energy stocks rallied across the board, with major oil companies posting gains of 3-6%. 
Analysts note that sustained prices above $90 could reignite inflation concerns and 
complicate the Federal Reserve's policy decisions.

Forward curves suggest markets expect elevated prices to persist through Q1 2025.""",
            'metadata': {
                'source': 'commodities_news',
                'date': '2024-10-07',
                'type': 'market_update',
                'category': 'energy',
                'commodities': 'WTI,BRENT'
            }
        }
    ]
    
    return sample_docs
