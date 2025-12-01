"""
Financial Knowledge Base for RAG System
Pre-defined knowledge chunks for the chatbot
"""

import logging
from typing import List, Dict, Any
import hashlib

logger = logging.getLogger(__name__)


# Financial knowledge organized by topic
FINANCIAL_KNOWLEDGE = {
    "options_basics": [
        {
            "topic": "Options Fundamentals",
            "content": """Options are financial derivatives that give the buyer the right, but not the obligation, 
to buy (call) or sell (put) an underlying asset at a predetermined price (strike price) before or on 
a specific date (expiration date). Key terms:
- Call Option: Right to BUY at strike price
- Put Option: Right to SELL at strike price
- Premium: Price paid for the option
- In-the-Money (ITM): Option has intrinsic value
- At-the-Money (ATM): Strike equals current price
- Out-of-the-Money (OTM): No intrinsic value"""
        },
        {
            "topic": "The Greeks - Delta",
            "content": """Delta (Δ) measures an option's price sensitivity to a $1 change in the underlying asset.
- Call Delta: Ranges from 0 to 1 (ATM ≈ 0.50)
- Put Delta: Ranges from -1 to 0 (ATM ≈ -0.50)
- Delta also approximates probability of expiring ITM
- Deep ITM options have delta near 1 (calls) or -1 (puts)
- OTM options have delta near 0
- Used for hedging: 100 delta-neutral shares = 2 ATM calls"""
        },
        {
            "topic": "The Greeks - Gamma",
            "content": """Gamma (Γ) measures the rate of change in Delta for a $1 move in the underlying.
- Highest for ATM options near expiration
- Indicates how quickly Delta changes
- Long options have positive gamma
- Short options have negative gamma (gamma risk)
- High gamma = potential for rapid delta changes
- Gamma exposure can amplify profits or losses"""
        },
        {
            "topic": "The Greeks - Theta",
            "content": """Theta (Θ) measures time decay - how much value an option loses per day.
- Always negative for long options (you lose value)
- Accelerates as expiration approaches (theta curve)
- ATM options have highest theta near expiration
- Theta benefits option sellers (positive theta)
- Weekend decay: Fri to Mon = 3 days of theta
- Strategies: Theta farming, calendar spreads"""
        },
        {
            "topic": "The Greeks - Vega",
            "content": """Vega (ν) measures sensitivity to changes in implied volatility (IV).
- Higher IV = higher option premiums
- Long options have positive vega
- Short options have negative vega
- ATM options have highest vega
- IV typically increases before earnings
- IV crush: Sharp drop in IV after events
- Strategies: Straddles before earnings, iron condors after"""
        },
        {
            "topic": "Implied Volatility",
            "content": """Implied Volatility (IV) is the market's expectation of future price movement.
- Derived from option prices using Black-Scholes
- IV Rank: Current IV vs 52-week range (0-100%)
- IV Percentile: % of days IV was lower
- High IV: Expensive options, favor selling
- Low IV: Cheap options, favor buying
- VIX: S&P 500 volatility index (fear gauge)
- IV Skew: Different IVs for different strikes"""
        }
    ],
    "trading_strategies": [
        {
            "topic": "Momentum Strategy",
            "content": """Momentum trading capitalizes on price trends continuing in the same direction.
Key indicators:
- RSI (Relative Strength Index): >70 overbought, <30 oversold
- MACD (Moving Average Convergence Divergence): Signal line crossovers
- Moving Averages: 50-day and 200-day crossovers (Golden/Death Cross)
Entry signals: Break above resistance, increasing volume
Exit signals: RSI divergence, trend line break
Risk management: Stop-loss at recent support, position sizing"""
        },
        {
            "topic": "Mean Reversion Strategy",
            "content": """Mean reversion assumes prices return to their historical average.
Key indicators:
- Bollinger Bands: Buy at lower band, sell at upper band
- Z-Score: Measures standard deviations from mean
- Pairs Trading: Trade relative value between correlated assets
Entry: When price deviates 2+ standard deviations from mean
Exit: When price returns to mean
Risk: Strong trends can invalidate mean reversion
Works best in range-bound markets"""
        },
        {
            "topic": "Options Spread Strategies",
            "content": """Common options spread strategies:
- Bull Call Spread: Buy lower strike call, sell higher strike call (bullish, limited risk)
- Bear Put Spread: Buy higher strike put, sell lower strike put (bearish, limited risk)
- Iron Condor: Sell OTM call and put spreads (neutral, profit from time decay)
- Iron Butterfly: ATM version of iron condor (neutral, tighter range)
- Calendar Spread: Sell near-term, buy far-term (profit from time decay differential)
- Straddle: Buy ATM call and put (profit from large moves, any direction)
- Strangle: Buy OTM call and put (cheaper straddle, needs bigger move)"""
        }
    ],
    "portfolio_management": [
        {
            "topic": "Portfolio Diversification",
            "content": """Diversification reduces portfolio risk by spreading investments across:
- Asset Classes: Stocks, bonds, commodities, real estate
- Sectors: Technology, Healthcare, Finance, Energy, etc.
- Geography: US, International, Emerging Markets
- Market Cap: Large, Mid, Small cap stocks
- Correlation: Combine assets that move independently
- Rebalancing: Periodically adjust to target allocation
Modern Portfolio Theory: Maximize return for given risk level"""
        },
        {
            "topic": "Risk Metrics",
            "content": """Key portfolio risk metrics:
- Sharpe Ratio: (Return - Risk-free rate) / Volatility (higher is better)
- Sortino Ratio: Like Sharpe but only penalizes downside volatility
- Beta: Sensitivity to market movements (1.0 = market)
- Alpha: Excess return over benchmark
- Max Drawdown: Largest peak-to-trough decline
- VaR (Value at Risk): Maximum expected loss at confidence level
- Standard Deviation: Measure of return volatility"""
        },
        {
            "topic": "Position Sizing",
            "content": """Position sizing strategies to manage risk:
- Fixed Percentage: Risk same % of portfolio per trade (e.g., 2%)
- Kelly Criterion: Optimize position size based on win rate and payoff
- Volatility-Based: Scale position inversely with volatility
- ATR (Average True Range): Set stops based on ATR multiples
Rules of thumb:
- Never risk more than 2% of portfolio on single trade
- Reduce position size for higher volatility assets
- Consider correlation between positions"""
        }
    ],
    "market_analysis": [
        {
            "topic": "Technical Analysis Basics",
            "content": """Technical analysis studies price patterns and trends:
Chart Patterns:
- Head and Shoulders: Reversal pattern (bearish after uptrend)
- Double Top/Bottom: Reversal patterns at key levels
- Triangle: Consolidation (ascending=bullish, descending=bearish)
- Cup and Handle: Bullish continuation pattern
Support/Resistance:
- Support: Price level where buying prevents further decline
- Resistance: Price level where selling prevents further rise
- Breakout: Price moving through support/resistance with volume"""
        },
        {
            "topic": "Fundamental Analysis",
            "content": """Fundamental analysis evaluates a company's intrinsic value:
Key Metrics:
- P/E Ratio: Price to Earnings (compare to industry average)
- P/S Ratio: Price to Sales (useful for unprofitable companies)
- P/B Ratio: Price to Book Value
- EPS Growth: Earnings per share growth rate
- ROE: Return on Equity (profitability measure)
- Debt/Equity: Financial leverage ratio
- Free Cash Flow: Cash generated after capital expenditures
Quality indicators: Moat, management quality, competitive advantage"""
        },
        {
            "topic": "Market Indicators",
            "content": """Broader market health indicators:
- VIX: Volatility index (fear gauge) - above 20 = elevated fear
- Put/Call Ratio: High = bearish sentiment, Low = bullish
- Advance/Decline Line: Market breadth indicator
- 52-Week Highs/Lows: Market strength measure
- Sector Rotation: Money flowing between sectors
- Yield Curve: Bond yields at different maturities (inverted = recession risk)
- Credit Spreads: High-yield vs Treasury yields (widening = risk-off)"""
        }
    ],
    "dashboard_features": [
        {
            "topic": "Volatility Lab Features",
            "content": """The Volatility Lab provides comprehensive volatility analysis:
- IV Surface: 3D visualization of implied volatility across strikes and expirations
- Term Structure: IV across different expiration dates
- Volatility Smile/Skew: IV variation across strike prices
- Historical vs Implied: Compare realized vs expected volatility
- Volatility Cones: Historical percentile ranges
- Regime Detection: Identify high/low volatility environments
Use: Find mispriced options, timing entries, volatility trading"""
        },
        {
            "topic": "Strategy Lab Features",
            "content": """The Strategy Lab enables backtesting trading strategies:
Available Strategies:
- Momentum: Follow trends using RSI and moving averages
- Mean Reversion: Trade against extreme moves
- Pairs Trading: Trade relative value between correlated stocks
- Bollinger Bands: Trade around volatility bands
- MACD: Trade signal line crossovers
Features:
- Custom parameters for each strategy
- Historical backtesting with real data
- Performance metrics: Returns, Sharpe, Win Rate, Max Drawdown
- Compare against benchmark (SPY)"""
        },
        {
            "topic": "Portfolio Analytics",
            "content": """Portfolio Analytics provides investment tracking:
- Real-time position values and P&L
- Historical performance tracking
- Risk metrics (Beta, Sharpe, Volatility)
- Sector allocation breakdown
- Factor exposure analysis
- Dividend tracking
- Paper trading integration with Alpaca
- Order management and execution"""
        }
    ]
}


def get_all_knowledge_chunks() -> List[Dict[str, Any]]:
    """
    Get all knowledge chunks formatted for RAG ingestion
    
    Returns:
        List of chunk dicts with chunk_id, text, and metadata
    """
    chunks = []
    
    for category, topics in FINANCIAL_KNOWLEDGE.items():
        for topic_data in topics:
            topic_title = topic_data["topic"]
            content = topic_data["content"].strip()
            
            # Generate unique chunk ID
            chunk_id = hashlib.md5(f"{category}:{topic_title}".encode()).hexdigest()[:12]
            
            chunks.append({
                "chunk_id": f"kb_{chunk_id}",
                "text": f"{topic_title}\n\n{content}",
                "metadata": {
                    "source": "knowledge_base",
                    "category": category,
                    "topic": topic_title,
                    "type": "educational"
                }
            })
    
    logger.info(f"Generated {len(chunks)} knowledge chunks")
    return chunks


def ingest_knowledge_to_index():
    """
    Ingest all knowledge chunks into the FAISS index
    """
    from financial_dashboard.services.chat.faiss_index import get_index
    from financial_dashboard.services.chat.embed import get_embedder
    
    chunks = get_all_knowledge_chunks()
    embedder = get_embedder()
    index = get_index()
    
    # Check if knowledge is already ingested
    if index.size() > 0:
        logger.info(f"Index already has {index.size()} entries, skipping ingestion")
        return index.size()
    
    # Generate embeddings
    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedder.embed_batch(texts)
    
    # Add to index
    count = index.add(chunks, embeddings)
    index.save()
    
    logger.info(f"Ingested {count} knowledge chunks into index")
    return count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    count = ingest_knowledge_to_index()
    print(f"Ingested {count} knowledge chunks")
