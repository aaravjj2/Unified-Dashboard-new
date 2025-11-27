"""
Research Lab - Data Module

Provides lazy data loaders and deterministic fixtures for testing.
No network calls or expensive operations at module import time.

Environment variables:
- RL_DETERMINISTIC=1: Use deterministic fixtures instead of live data
"""

import os
import json
import logging
from pathlib import Path
from functools import lru_cache
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

# Fixture paths
FIXTURES_DIR = Path(__file__).parent.parent.parent.parent / "reports" / "research_lab" / "fixtures"
FAISS_INDEX_DIR = Path(__file__).parent.parent.parent.parent / "data" / "rag" / "faiss_index"

# Deterministic mode flag
def is_deterministic() -> bool:
    """Check if running in deterministic test mode."""
    return os.getenv("RL_DETERMINISTIC", "0") == "1"


# ============================================================================
# LAZY DATA LOADERS (no network calls at import)
# ============================================================================

@lru_cache(maxsize=1)
def get_sample_tickers() -> List[str]:
    """Get list of sample tickers for demos."""
    return ["AAPL", "MSFT", "GOOGL", "NVDA", "AMZN", "META", "TSLA", "AMD", "INTC", "NFLX"]


@lru_cache(maxsize=1)
def get_factor_definitions() -> Dict[str, Dict]:
    """Get factor definitions for factor analysis."""
    return {
        "momentum": {
            "name": "Momentum",
            "description": "Price momentum based on trailing returns",
            "calculation": "12-month return minus 1-month return"
        },
        "value": {
            "name": "Value",
            "description": "Value factor based on book-to-market ratio",
            "calculation": "Book value / Market cap"
        },
        "growth": {
            "name": "Growth",
            "description": "Growth factor based on earnings growth",
            "calculation": "5-year EPS growth rate"
        },
        "volatility": {
            "name": "Volatility",
            "description": "Price volatility risk factor",
            "calculation": "60-day rolling standard deviation of returns"
        },
        "quality": {
            "name": "Quality",
            "description": "Quality factor based on profitability metrics",
            "calculation": "ROE + gross margin stability"
        },
        "size": {
            "name": "Size",
            "description": "Market capitalization factor",
            "calculation": "Log of market cap"
        }
    }


def load_factor_exposures(tickers: List[str], period: str = "3M") -> Dict[str, Dict[str, float]]:
    """
    Lazy loader for factor exposures.
    
    In deterministic mode, returns fixture data.
    Otherwise, would fetch from data service.
    """
    if is_deterministic():
        return _load_fixture("factor_exposures.json", default=_generate_mock_factor_exposures(tickers))
    
    # TODO: Implement live data fetch from data service
    return _generate_mock_factor_exposures(tickers)


def load_correlation_matrix(tickers: List[str], window: int = 60) -> Dict[str, Dict[str, float]]:
    """
    Lazy loader for correlation matrix.
    
    In deterministic mode, returns fixture data.
    Otherwise, would compute from price data.
    """
    if is_deterministic():
        return _load_fixture("correlation_matrix.json", default=_generate_mock_correlation(tickers))
    
    # TODO: Implement live correlation computation
    return _generate_mock_correlation(tickers)


def load_screen_results(filters: Dict) -> Dict[str, Any]:
    """
    Lazy loader for screening results.
    
    Returns sample data in deterministic mode.
    """
    if is_deterministic():
        return _load_fixture("screen_results.json", default=_generate_mock_screen_results())
    
    # TODO: Implement live screening
    return _generate_mock_screen_results()


def load_briefs() -> List[Dict]:
    """
    Lazy loader for research briefs.
    
    In deterministic mode, loads from fixtures.
    Otherwise, would fetch from database.
    """
    if is_deterministic():
        return _load_fixture("briefs.json", default=_get_demo_briefs())
    
    # Default demo briefs when no database available
    return _get_demo_briefs()


def load_experiments() -> List[Dict]:
    """
    Lazy loader for experiment records.
    
    In deterministic mode, loads from fixtures.
    """
    if is_deterministic():
        return _load_fixture("experiments.json", default=_get_demo_experiments())
    
    return _get_demo_experiments()


# ============================================================================
# FIXTURE HELPERS
# ============================================================================

def _load_fixture(filename: str, default: Any = None) -> Any:
    """Load fixture from file, return default if not found."""
    fixture_path = FIXTURES_DIR / filename
    try:
        if fixture_path.exists():
            with open(fixture_path, "r") as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load fixture {filename}: {e}")
    return default if default is not None else {}


def save_fixture(filename: str, data: Any) -> bool:
    """Save data to fixture file."""
    fixture_path = FIXTURES_DIR / filename
    try:
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)
        with open(fixture_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"Could not save fixture {filename}: {e}")
        return False


# ============================================================================
# MOCK DATA GENERATORS
# ============================================================================

def _generate_mock_factor_exposures(tickers: List[str]) -> Dict[str, Dict[str, float]]:
    """Generate deterministic mock factor exposures."""
    import hashlib
    
    factors = ["momentum", "value", "growth", "volatility", "quality", "size"]
    exposures = {}
    
    for ticker in tickers:
        # Use hash for deterministic but varied values
        seed = int(hashlib.md5(ticker.encode()).hexdigest()[:8], 16)
        exposures[ticker] = {}
        for i, factor in enumerate(factors):
            # Generate value between -1 and 1
            val = ((seed + i * 1000) % 200 - 100) / 100
            exposures[ticker][factor] = round(val, 3)
    
    return exposures


def _generate_mock_correlation(tickers: List[str]) -> Dict[str, Dict[str, float]]:
    """Generate deterministic mock correlation matrix."""
    import hashlib
    
    matrix = {}
    for t1 in tickers:
        matrix[t1] = {}
        for t2 in tickers:
            if t1 == t2:
                matrix[t1][t2] = 1.0
            else:
                # Use sorted pair for symmetric matrix
                pair = tuple(sorted([t1, t2]))
                seed = int(hashlib.md5(str(pair).encode()).hexdigest()[:8], 16)
                val = (seed % 50 + 30) / 100  # 0.30 to 0.80
                matrix[t1][t2] = round(val, 2)
    
    return matrix


def _generate_mock_screen_results() -> Dict[str, Any]:
    """Generate mock screening results."""
    return {
        "tickers": [
            {"symbol": "NVDA", "score": 0.92, "sector": "Technology", "momentum": 0.85},
            {"symbol": "AMD", "score": 0.88, "sector": "Technology", "momentum": 0.78},
            {"symbol": "AAPL", "score": 0.82, "sector": "Technology", "momentum": 0.65},
            {"symbol": "MSFT", "score": 0.79, "sector": "Technology", "momentum": 0.62},
            {"symbol": "GOOGL", "score": 0.75, "sector": "Technology", "momentum": 0.58}
        ],
        "summary": {
            "total_matches": 5,
            "avg_score": 0.83,
            "type": "momentum",
            "filters_applied": ["sector=Technology", "momentum>0.5"]
        },
        "generated_at": datetime.now().isoformat()
    }


def _get_demo_briefs() -> List[Dict]:
    """Get demo research briefs."""
    return [
        {
            "id": "demo-momentum-1",
            "title": "Momentum Strategy Analysis Q4 2024",
            "summary": "Analysis of momentum factors across tech sector with backtest results.",
            "tags": ["momentum", "tech", "backtest"],
            "created_at": "2024-10-15",
            "last_updated": "2024-11-20",
            "body": "# Momentum Strategy Analysis\n\nThis brief covers momentum factor analysis...",
            "notes": "",
            "version": 1,
            "status": "published"
        },
        {
            "id": "demo-value-2",
            "title": "Value Investing in AI Sector",
            "summary": "Identifying undervalued AI companies using fundamental analysis.",
            "tags": ["value", "AI", "fundamental"],
            "created_at": "2024-11-01",
            "last_updated": "2024-11-25",
            "body": "# Value Investing in AI\n\nDespite high valuations...",
            "notes": "",
            "version": 2,
            "status": "draft"
        }
    ]


def _get_demo_experiments() -> List[Dict]:
    """Get demo experiment records."""
    return [
        {
            "id": "exp-001",
            "name": "Momentum 20-day Backtest",
            "strategy": "momentum",
            "parameters": {"lookback": 20, "top_n": 5},
            "created_at": "2024-11-15",
            "status": "completed",
            "metrics": {
                "total_return": 0.234,
                "sharpe_ratio": 1.42,
                "max_drawdown": -0.087,
                "win_rate": 0.64
            }
        },
        {
            "id": "exp-002",
            "name": "Mean Reversion Test",
            "strategy": "mean_reversion",
            "parameters": {"lookback": 10, "threshold": 2.0},
            "created_at": "2024-11-20",
            "status": "running",
            "metrics": None
        }
    ]


# ============================================================================
# RAG / VECTOR INDEX HELPERS
# ============================================================================

def get_faiss_index_path() -> Path:
    """Get path to FAISS index directory."""
    FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    return FAISS_INDEX_DIR


def get_index_health() -> Dict[str, Any]:
    """Get health status of the RAG index."""
    index_path = get_faiss_index_path()
    index_file = index_path / "index.faiss"
    metadata_file = index_path / "metadata.json"
    
    health = {
        "status": "unknown",
        "index_exists": index_file.exists(),
        "metadata_exists": metadata_file.exists(),
        "index_size": 0,
        "doc_count": 0,
        "last_updated": None,
        "errors": []
    }
    
    if index_file.exists():
        health["index_size"] = index_file.stat().st_size
        health["status"] = "ok"
    else:
        health["status"] = "empty"
        health["errors"].append("No index file found")
    
    if metadata_file.exists():
        try:
            with open(metadata_file, "r") as f:
                meta = json.load(f)
                health["doc_count"] = meta.get("doc_count", 0)
                health["last_updated"] = meta.get("last_updated")
        except Exception as e:
            health["errors"].append(f"Metadata read error: {e}")
    
    return health


# ============================================================================
# NEWS / SCAN DATA
# ============================================================================

def get_news_sources() -> List[Dict]:
    """Get available news sources configuration."""
    return [
        {"id": "finnhub", "name": "Finnhub", "enabled": True, "priority": 1},
        {"id": "cache", "name": "Cached News", "enabled": True, "priority": 2},
        {"id": "mock", "name": "Mock Data", "enabled": is_deterministic(), "priority": 3}
    ]


def load_news_feed(tickers: List[str], source: str = "auto") -> List[Dict]:
    """
    Lazy loader for news feed.
    
    In deterministic mode, returns mock news.
    Otherwise, would fetch from Finnhub or cached source.
    """
    if is_deterministic():
        return _generate_mock_news(tickers)
    
    # TODO: Implement Finnhub news fetch with fallback
    return _generate_mock_news(tickers)


def _generate_mock_news(tickers: List[str]) -> List[Dict]:
    """Generate mock news items."""
    news = []
    for i, ticker in enumerate(tickers[:5]):
        news.append({
            "id": f"news-{i+1}",
            "ticker": ticker,
            "headline": f"Sample news headline for {ticker}",
            "summary": f"This is a mock news summary for {ticker} demonstrating the news feed.",
            "source": "Mock Source",
            "datetime": datetime.now().isoformat(),
            "url": f"https://example.com/news/{ticker.lower()}"
        })
    return news
