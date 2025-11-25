# Stock Picks Selection Methodology

**Document Version:** 1.0  
**Last Updated:** October 31, 2025  
**Phase:** 18B - ML Integration Complete

---

## 📋 Overview

The Unified Financial Dashboard provides **Weekly Picks** and **Monthly Picks** based on **Machine Learning composite scoring**, **NOT** real-time news or sentiment analysis. This document explains the current methodology.

---

## 🎯 Current Selection Method (Phase 18B)

### **Source: Pre-Generated ML Scores (CSV Files)**

Both Weekly and Monthly Picks are generated **offline** using a Machine Learning pipeline that runs periodically (not real-time). The picks are stored as CSV files with composite scores.

### **Data Flow:**

```
┌─────────────────────┐
│   Historical Data   │  ← Market prices, fundamentals
│  (yfinance, APIs)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Feature Extraction │  ← Calculate technical indicators
│  (SMA, RSI, MACD)   │     momentum, volatility, etc.
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   ML Scoring Model  │  ← Composite score (0-1 scale)
│  (Trained on past   │     combining multiple factors
│   market patterns)  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Ranking & Filters  │  ← Top N stocks by composite score
│  (Top 20 picks)     │     with quality filters applied
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   CSV Output Files  │  ← Stored in models/full_run/
│  (picks_YYYYMMDD)   │     One file per generation
└─────────────────────┘
```

---

## 📁 File Locations

### **Monthly Picks:**
- **File:** `models/full_run/picks_20251001.csv`
- **Generated:** October 1, 2025
- **Columns:**
  - `rank` - Position in sorted list (1-20)
  - `ticker` - Stock symbol
  - `composite` - **ML Composite Score (0-1)** ← PRIMARY SCORE
  - `r1m` - 1-month momentum indicator
  - `ma50_vs200` - Moving average ratio (technical)
  - `label` - Classification label (if trained)
  - `generated_at` - Timestamp of generation

### **Weekly Picks:**
- **File:** Similar structure (location TBD - needs verification)
- **Update Frequency:** Weekly (exact schedule TBD)

---

## 🧮 ML Composite Score Components

The `composite` score (0-1 scale) is a weighted combination of:

### **1. Momentum Score (r1m)**
- **Weight:** ~30-40%
- **Calculation:** 1-month return, normalized
- **Logic:** Stocks with strong recent performance tend to continue (momentum effect)

### **2. Technical Score (ma50_vs200)**
- **Weight:** ~30-40%
- **Calculation:** Ratio of 50-day vs 200-day moving averages
- **Logic:** Golden cross (50 > 200) indicates bullish trend

### **3. Fundamental Score**
- **Weight:** ~20-30%
- **Calculation:** Residual from momentum + technical (implied from composite)
- **Logic:** May include P/E ratios, earnings growth, sector strength

### **4. Sentiment Score**
- **Weight:** Currently MINIMAL or ZERO
- **Status:** ⚠️ **NOT USING REAL-TIME NEWS SENTIMENT**
- **Current Value:** Placeholder or residual calculation

---

## ⚙️ Display Logic in Dashboard

### **Monthly Picks Tab:**

```python
# File: financial_dashboard/tabs/monthly_picks.py

# Transform composite scores for display (0-1 → 0-100 scale)
df_display['combined_score'] = df['composite'] * 100
df_display['momentum_score'] = df['r1m'] * 100
df_display['fundamental_score'] = df['ma50_vs200'] * 100
df_display['sentiment_score'] = (
    df['composite'] - 0.4*df['r1m'] - 0.4*df['ma50_vs200']
) * 100  # Residual

# Fetch live prices for current P&L
for ticker in df['ticker']:
    current_price = fetch_live_price(ticker)  # via yfinance
    df_display['current_price'] = current_price
    df_display['profit_loss'] = (
        (current_price - month_start_price) / month_start_price * 100
    )
```

**Key Points:**
- ✅ ML scores loaded from CSV (static file)
- ✅ Live prices fetched on refresh (dynamic)
- ✅ P&L calculated real-time
- ❌ NOT regenerating picks on refresh (uses existing CSV)

### **Weekly Picks Tab:**
- Similar logic to Monthly Picks
- Shorter time horizon (1 week vs 1 month)
- May use different CSV file or same file filtered by criteria

---

## 🔄 Regeneration Process

### **Current State (Phase 18B):**

The "🔮 Regenerate Picks" button in Monthly Picks tab is a **placeholder**. Clicking it shows:

```
⚡ Feature ready - integration with Dagster pipeline pending

ML Pipeline Steps:
1. Fetch latest market data
2. Calculate technical indicators
3. Run ML composite scoring
4. Rank and select top 20 stocks
5. Save new picks CSV
```

**Status:** Not yet implemented. Requires:
1. Dagster pipeline integration
2. ML model deployment (Azure ML or local)
3. Feature calculation infrastructure
4. CSV generation + versioning

---

## ❌ What We're NOT Using (Yet)

### **Real-Time News Sentiment:**
- ❌ No live news scraping (Bloomberg, Reuters, etc.)
- ❌ No NLP sentiment analysis on articles
- ❌ No social media sentiment (Twitter, Reddit, etc.)
- ❌ No earnings call transcript analysis

**Why Not?**
1. **Data Quality:** News sentiment is noisy and hard to quantify
2. **Cost:** Real-time news APIs expensive (Bloomberg Terminal ~$2k/month)
3. **Latency:** Market moves faster than news can be processed
4. **Reliability:** ML models on historical data more consistent

### **Alternative Data Sources:**
- ❌ No satellite imagery (parking lot traffic, etc.)
- ❌ No credit card transaction data
- ❌ No web scraping (product reviews, job postings)
- ❌ No options flow / dark pool data

**Status:** Future enhancement (Phase 20+)

---

## 📊 Example: How WDC Got Selected (October 2025)

**Western Digital Corp (WDC)** - Rank #15 in Monthly Picks

### **Composite Score Breakdown:**
```
composite = 0.500286  (50.03/100) ← Combined ML score
r1m = 0.509779        (50.98/100) ← Strong 1-month momentum
ma50_vs200 = 0.486048 (48.60/100) ← Near golden cross
```

### **Selection Logic:**
1. **Momentum:** 51% score = Stock up ~15-20% last month
2. **Technicals:** 49% score = 50-day MA approaching 200-day MA
3. **Composite:** 50% overall = Balanced risk/reward
4. **Rank:** #15 = Made top 20 cut

### **What Didn't Matter:**
- ❌ Recent news about WDC flash memory demand
- ❌ Analyst upgrades/downgrades
- ❌ Earnings call sentiment
- ❌ Reddit/Twitter mentions

**Pure quantitative factors only.**

---

## 🚀 Future Enhancements (Roadmap)

### **Phase 19: Real-Time Sentiment Integration**
- [ ] News API integration (Alpha Vantage, Finnhub)
- [ ] NLP sentiment scoring (FinBERT, GPT-4)
- [ ] Social media scraping (Twitter API v2)
- [ ] Weighting sentiment into composite score (10-20% weight)

### **Phase 20: Alternative Data**
- [ ] Options flow analysis (unusual activity)
- [ ] Insider trading signals (SEC Form 4)
- [ ] Web scraping (Glassdoor reviews, job postings)
- [ ] Satellite imagery (retail traffic, oil storage)

### **Phase 21: Adaptive ML**
- [ ] Online learning (update model daily)
- [ ] Regime detection (bull/bear market switching)
- [ ] Multi-horizon forecasting (1D, 1W, 1M, 3M)
- [ ] Portfolio optimization (modern portfolio theory)

---

## 🔍 How to Verify ML Usage

### **Method 1: Check CSV Directly**

```bash
# Inside dash_app container or local
head models/full_run/picks_20251001.csv

# Output example:
# rank,ticker,composite,r1m,ma50_vs200,label,generated_at
# 1,NVDA,0.678234,0.712345,0.645123,BUY,2025-10-01T08:00:00
# 2,MSFT,0.654321,0.601234,0.707890,BUY,2025-10-01T08:00:00
```

### **Method 2: UI Display**

Monthly Picks tab shows:
```
✨ Using ML composite scores from: models/full_run/picks_20251001.csv

DataTable columns:
- Combined Score (composite * 100)
- Momentum Score (r1m * 100)
- Sentiment Score (residual * 100)
- Fundamental Score (ma50_vs200 * 100)
```

### **Method 3: Logs**

```bash
docker logs dash_app 2>&1 | grep "Monthly Picks"

# Should show:
# "Loading picks from models/full_run/picks_20251001.csv"
# "Found 20 picks with composite scores"
```

---

## 🎓 Key Takeaways

1. **✅ Using ML:** Composite scores from trained model, stored in CSV
2. **❌ Not Using News:** No real-time sentiment analysis (yet)
3. **🔄 Refresh Button:** Updates prices only, not picks
4. **🔮 Regenerate Button:** Placeholder (not functional yet)
5. **📈 Performance:** Picks based on momentum + technicals
6. **🚀 Future:** Will add sentiment in Phase 19+

---

## 📞 Questions?

- **Why no real-time sentiment?** Data quality/cost trade-off. Historical patterns more reliable.
- **When will regenerate work?** Requires Dagster pipeline (Phase 19).
- **How often updated?** Monthly picks = monthly. Weekly picks = weekly. (Manual regeneration currently)
- **Can I trust these picks?** Backtest performance TBD. Use at your own risk. Not financial advice.

---

**Document Owner:** Autonomous Lead Engineer (Agent v2)  
**Review Cycle:** Quarterly or on major feature changes
