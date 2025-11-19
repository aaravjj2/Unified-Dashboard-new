"""
Data Ingestion Package

This package provides modular data ingestion clients for multiple market data sources:
- Finnhub
- Alpaca Markets

Production-grade APIs with better reliability, rate limits, and data quality.
Note: yfinance used as fallback only.
"""

__version__ = "1.0.0"

# Import clients
from data_ingestion.source_clients import FinnhubClient, AlpacaClient
from data_ingestion.ingest_market_data import fetch_market_data

__all__ = [
    "FinnhubClient",
    "AlpacaClient",
    "fetch_market_data",
]
