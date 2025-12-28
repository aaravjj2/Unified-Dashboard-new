"""
Generate mock market trends cache with improvements data
"""
import json
from datetime import datetime

# Create complete mock response with all improvements
mock_data = {
    "detailed": [
        {
            "ticker": "AAPL",
            "price": 195.71,
            "change_pct": 2.34,
            "rsi": 65.2,
            "macd": "Bullish",
            "volume": "125.4M",
            "sentiment": 0.72
        },
        {
            "ticker": "MSFT",
            "price": 378.91,
            "change_pct": 1.87,
            "rsi": 58.9,
            "macd": "Bullish",
            "volume": "89.2M",
            "sentiment": 0.68
        },
        {
            "ticker": "NVDA",
            "price": 495.22,
            "change_pct": -0.92,
            "rsi": 48.3,
            "macd": "Bearish",
            "volume": "156.7M",
            "sentiment": 0.45
        }
    ],
    "market_trend": {
        "label": "Bull Market",
        "color": "#10b981",
        "confidence": 0.78
    },
    "multi_timeframe": {
        "timeframes": {
            "1D": {
                "trend": "Neutral",
                "avg_change": 0.82,
                "signal": "HOLD",
                "sample_size": 3
            },
            "1W": {
                "trend": "Bull",
                "avg_change": 2.15,
                "signal": "BUY",
                "sample_size": 3
            },
            "1M": {
                "trend": "Strong Bull",
                "avg_change": 5.43,
                "signal": "BUY",
                "sample_size": 3
            }
        },
        "alignment": "STRONG BUY",
        "alignment_strength": "GOOD"
    },
    "risk_metrics": {
        "sharpe_ratio": 1.85,
        "sortino_ratio": 2.34,
        "max_drawdown_pct": -8.45,
        "calmar_ratio": 1.23,
        "annual_volatility_pct": 18.7,
        "value_at_risk_95_pct": -2.1
    },
    "momentum_indicators": {
        "overall_signal": "BUY",
        "rsi": {
            "value": 57.5,
            "signal": "Neutral"
        },
        "macd": {
            "bullish_pct": 66.7,
            "signal": "Bullish"
        },
        "stochastic": {
            "value": 62.3,
            "signal": "Neutral"
        },
        "williams_r": {
            "value": -35.8,
            "signal": "Neutral"
        }
    },
    "news": {
        "headlines": [
            {
                "title": "Tech Stocks Rally on Strong Earnings",
                "source": "Reuters",
                "sentiment": 0.8,
                "url": "https://example.com/1"
            },
            {
                "title": "Market Sees Continued Growth in AI Sector",
                "source": "Bloomberg",
                "sentiment": 0.7,
                "url": "https://example.com/2"
            }
        ],
        "summary": "Positive sentiment across major tech stocks"
    },
    "generated_at": datetime.now().isoformat(),
    "price_provider_summary": "Alpaca (3/3)",
    "tickers": ["AAPL", "MSFT", "NVDA"],
    "period": "1y",
    "success_count": 3,
    "total_count": 3
}

# Save to cache
import os
os.makedirs('cache', exist_ok=True)
with open('cache/market_trends.json', 'w') as f:
    json.dump(mock_data, f, indent=2)

print("✅ Created cache/market_trends.json with all improvements data")
print(f"   - {len(mock_data['detailed'])} tickers")
print(f"   - Multi-timeframe: {list(mock_data['multi_timeframe']['timeframes'].keys())}")
print(f"   - Risk metrics: {list(mock_data['risk_metrics'].keys())[:4]}...")
print(f"   - Momentum: {mock_data['momentum_indicators']['overall_signal']}")
