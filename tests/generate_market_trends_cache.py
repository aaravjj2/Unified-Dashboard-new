"""
Generate cached market trends data for testing.
This script creates synthetic but realistic cache data to test UI rendering.
"""
import json
import os
from pathlib import Path

# Define cache path
OUTPUT_DIR = Path(__file__).parent.parent / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)
CACHE_FILE = OUTPUT_DIR / "market_brief.json"

# Generate realistic test data
test_data = {
    "detailed": [
        {
            "ticker": "TSLA",
            "name": "Tesla Inc",
            "sector": "Consumer Cyclical",
            "price": 242.84,
            "change_pct": 2.45,
            "volume": 95234567,
            "market_cap": 771000000000,
            "pe_ratio": 65.32,
            "sentiment_score": 0.75
        },
        {
            "ticker": "AAPL",
            "name": "Apple Inc",
            "sector": "Technology",
            "price": 178.52,
            "change_pct": 1.23,
            "volume": 58234123,
            "market_cap": 2800000000000,
            "pe_ratio": 28.45,
            "sentiment_score": 0.82
        },
        {
            "ticker": "NVDA",
            "name": "NVIDIA Corporation",
            "sector": "Technology",
            "price": 495.22,
            "change_pct": 3.15,
            "volume": 42156789,
            "market_cap": 1220000000000,
            "pe_ratio": 72.18,
            "sentiment_score": 0.89
        },
        {
            "ticker": "MSFT",
            "name": "Microsoft Corporation",
            "sector": "Technology",
            "price": 378.91,
            "change_pct": 0.98,
            "volume": 25678901,
            "market_cap": 2820000000000,
            "pe_ratio": 35.67,
            "sentiment_score": 0.78
        },
        {
            "ticker": "GOOG",
            "name": "Alphabet Inc",
            "sector": "Communication Services",
            "price": 139.47,
            "change_pct": 1.56,
            "volume": 32145678,
            "market_cap": 1760000000000,
            "pe_ratio": 25.89,
            "sentiment_score": 0.71
        }
    ],
    "tidy": [],  # Optional simplified format
    "timestamp": "2025-10-23T00:50:00Z",
    "source": "test_generator"
}

# Write cache file
with open(CACHE_FILE, 'w') as f:
    json.dump(test_data, f, indent=2)

print(f"✅ Generated test cache at: {CACHE_FILE}")
print(f"   Contains {len(test_data['detailed'])} ticker records")
print(f"   Tickers: {', '.join([d['ticker'] for d in test_data['detailed']])}")
