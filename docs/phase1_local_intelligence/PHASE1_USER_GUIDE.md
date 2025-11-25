# PHASE 1 - MODEL INSIGHT EXPLORER USER GUIDE

**Unified Financial Dashboard - Azure ML Lab**  
**Feature:** Model Insight Explorer (Explainability)  
**Version:** 1.0 (Phase 1 - Mock Mode)  
**Last Updated:** October 29, 2025

---

## 📖 Table of Contents

1. [What is Model Explainability?](#what-is-model-explainability)
2. [Why Should I Care?](#why-should-i-care)
3. [How to Access Model Insight Explorer](#how-to-access)
4. [Generating Your First Explanation](#generating-your-first-explanation)
5. [Understanding the Results](#understanding-the-results)
6. [Interpreting Feature Importance](#interpreting-feature-importance)
7. [Common Questions (FAQ)](#faq)
8. [Troubleshooting](#troubleshooting)
9. [Advanced Tips](#advanced-tips)

---

## 🧠 What is Model Explainability? {#what-is-model-explainability}

Machine learning models can feel like **"black boxes"** - they make predictions, but it's hard to understand *why*. 

**Model Explainability** solves this by showing you:
- **Which factors** influenced the prediction
- **How much** each factor contributed
- **Whether** the factors make logical sense

Think of it like getting a "receipt" for the model's decision:

```
🧾 Prediction Receipt for AAPL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Predicted Return: +5.2%

Top Contributing Factors:
  1. Strong momentum (20-day avg) → +1.2%
  2. Low volatility (stable price) → +0.9%
  3. Positive news sentiment    → +0.7%
  
Total explained: 87% of prediction
```

---

## 🎯 Why Should I Care? {#why-should-i-care}

### For Beginners

Explainability helps you **learn** by showing you what professional traders look at:

- Is the model focusing on momentum? → You're in a trending market
- Is it using sentiment? → News/social media matters for this stock
- Is it ignoring fundamentals? → Market might be overheated

### For Experienced Traders

Explainability helps you **validate** the model's reasoning:

- Does the prediction align with your thesis?
- Are there unexpected factors you missed?
- Is the model picking up regime changes?

### For Risk Management

Explainability helps you **spot issues** before they cost you money:

- ⚠️ Model predicts high return but top factor is "social sentiment" → Risky (meme stock behavior)
- ✅ Model predicts high return and top factors are "earnings growth" + "momentum" → Safer bet

---

## 🚀 How to Access Model Insight Explorer {#how-to-access}

### Step-by-Step Navigation

1. **Open the Dashboard**
   - Start the application: `python financial_dashboard/app.py`
   - Navigate to `http://localhost:8050` in your browser

2. **Click "Azure ML Lab" Tab**
   - Located in the top navigation bar
   - Icon: 🤖 (brain emoji)

3. **Scroll to "3️⃣ Insights & Metrics" Section**

4. **Click "🧠 Model Insights" Tab**
   - This is the 5th tab in the Insights section
   - Located after: Predictions, Performance, Feature Importance, Risk Analysis

**Visual Guide:**

```
┌─────────────────────────────────────────────────────┐
│  Home  │  Portfolio  │  Volatility  │  🤖 Azure ML  │
└─────────────────────────────────────────────────────┘
          ↑ Click here

                    ↓ Scroll down

┌─────────────────────────────────────────────────────┐
│  3️⃣ Insights & Metrics                              │
├─────────────────────────────────────────────────────┤
│  📊 Predictions  │  📈 Performance  │  🔍 Feature    │
│                  │                  │  Importance    │
│  ⚠️ Risk Analysis │  🧠 Model Insights  ← YOU ARE HERE
└─────────────────────────────────────────────────────┘
```

---

## 📝 Generating Your First Explanation {#generating-your-first-explanation}

### Quick Start (30 seconds)

1. **Expand the Beginner's Guide** (optional, recommended for first-time users)
   - Click the accordion: **"📖 Beginner's Guide: Understanding Model Predictions"**
   - Read the overview to understand key terms

2. **Select a Ticker**
   - Use the dropdown: **"Select Ticker"**
   - Choose from: AAPL, TSLA, NVDA, MSFT, GOOGL
   - Example: Select **AAPL - Apple Inc.**

3. **Choose Number of Features** (optional)
   - Use the slider: **"Top Features"**
   - Default: 10 (recommended for beginners)
   - Range: 5-20 features
   - Tip: Start with 10, increase if you want more detail

4. **Generate Explanation**
   - Click the button: **"💡 Generate Explanation"**
   - Wait 1-2 seconds for results

5. **Review Results**
   - See "Understanding the Results" section below

---

## 📊 Understanding the Results {#understanding-the-results}

### What You'll See

After clicking "Generate Explanation", the results container updates with:

#### 1. **Prediction Summary** (Top Section)

```markdown
**Prediction for AAPL:** Higher expected return of +5.23%.
```

- **Ticker**: Which stock this explains
- **Direction**: "Higher" or "Lower"
- **Target**: "expected return" (price movement) or "volatility" (risk level)
- **Value**: The predicted percentage

#### 2. **Feature Importance Chart** (Interactive Plotly)

```
Green bars → Increased prediction (positive SHAP)
Red bars   → Decreased prediction (negative SHAP)
Longer bar → Stronger influence
```

**How to Read:**
- Hover over any bar to see:
  - Feature name (e.g., "Momentum 20D")
  - SHAP value (impact size)
  - Contribution percentage

**Example:**
```
Momentum 20D ▓▓▓▓▓▓▓▓▓▓ 18.3%  (Green bar = positive impact)
Volatility 20D ▓▓▓▓▓ 13.1%     (Red bar = negative impact)
```

#### 3. **Key Contributing Factors** (Textual Explanation)

```markdown
**Key Contributing Factors:**

1. **Momentum 20D** (18.3% importance): strongly increases predicted expected return
2. **Volatility 20D** (13.1% importance): moderately decreases predicted expected return
3. **Market Beta** (11.1% importance): moderately increases predicted expected return
...

_These 10 factors account for 86.9% of the prediction._
```

**What Each Line Means:**
- **Number**: Ranking (1 = most important)
- **Feature Name**: What the model looked at (see "Feature Glossary" below)
- **Importance %**: How much this factor contributed
- **Description**: Plain English explanation of impact

---

## 🔍 Interpreting Feature Importance {#interpreting-feature-importance}

### Feature Glossary (Beginner-Friendly)

| Feature | What It Means | Example Interpretation |
|---------|---------------|------------------------|
| **Momentum 20D** | Price trend over last 20 days | High momentum = stock has been rising recently |
| **Volatility 20D** | Price stability over last 20 days | High volatility = price swings a lot (risky) |
| **Sharpe 20D** | Risk-adjusted return | Higher Sharpe = better return for the risk taken |
| **RSI 14D** | Overbought/oversold indicator | RSI > 70 = overbought, RSI < 30 = oversold |
| **Market Beta** | Sensitivity to overall market | Beta > 1 = moves more than market, Beta < 1 = more stable |
| **PE Ratio** | Price-to-earnings ratio | High P/E = expensive relative to earnings |
| **News Sentiment** | Recent news tone (positive/negative) | Positive sentiment = good news coverage |
| **Social Sentiment** | Social media chatter tone | High social sentiment = trending on Twitter/Reddit |
| **Volume Spike** | Unusual trading activity | High volume = lots of buying/selling |

### SHAP Value Interpretation

**SHAP Values** measure how much each feature pushed the prediction up (+) or down (−).

| SHAP Value | Meaning | Color |
|------------|---------|-------|
| +0.15 | Strong positive influence | Dark Green |
| +0.08 | Moderate positive influence | Light Green |
| +0.03 | Slight positive influence | Pale Green |
| 0.00 | No influence | Gray |
| −0.03 | Slight negative influence | Pale Red |
| −0.08 | Moderate negative influence | Light Red |
| −0.15 | Strong negative influence | Dark Red |

**Example:**

```
Feature: Momentum 20D
SHAP Value: +0.12 (green bar)
Interpretation: This stock's recent price trend is strong, 
                adding +1.2% to the predicted return.
```

---

## ❓ Common Questions (FAQ) {#faq}

### Q1: Why do I see "Mock Mode" in the badge?

**A:** Phase 1 uses **simulated** explanations for testing. The logic is correct, but SHAP values are synthetic (not from a real trained model). 

- **Phase 1 (Current):** Mock SHAP values for demonstration
- **Phase 2 (Coming Soon):** Real SHAP values from deployed Azure ML model

**What this means for you:** Use explanations to *learn the interface*, but don't make real trades based on Phase 1 results.

### Q2: Can I explain tickers not in the dropdown?

**A:** Currently, only 5 tickers are available (AAPL, TSLA, NVDA, MSFT, GOOGL). 

**Phase 2 will support:**
- All tickers in your current portfolio
- Top 20 Weekly Picks
- Custom ticker entry

### Q3: What does "contribution percentage" mean?

**A:** It's the portion of the total prediction explained by that feature.

**Example:**
- Prediction: +5% return
- Momentum 20D contribution: 18.3%
- Math: 18.3% of 5% = ~0.92% attributed to momentum

**All top 10 features combined** might explain 80-90% of the prediction.

### Q4: Why are some features negative (red bars)?

**A:** A **negative SHAP value** means that feature *reduced* the prediction.

**Example:**
- High volatility (risky) → Model predicts *lower* return
- SHAP value: −0.09 (red bar)
- Interpretation: Without this volatility, the prediction would be higher

**This is normal!** Models weigh both positive and negative factors.

### Q5: How do I know if the model is making sense?

**Sanity checks:**

✅ **Good signs:**
- Top features align with what you know about the stock
- Positive momentum + good news → High predicted return (logical)
- High volatility → Lower predicted return (risk-averse model)

⚠️ **Warning signs:**
- Unexpected features dominate (e.g., "Social Sentiment" for blue-chip stocks)
- Features contradict each other (e.g., high momentum + negative prediction)
- Top feature has very low contribution (<5%) → Model is uncertain

### Q6: What's the difference between "Feature Importance" tab and "Model Insights" tab?

| Tab | Focus | Content |
|-----|-------|---------|
| **Feature Importance** | Global model behavior | Which features matter *across all stocks* |
| **Model Insights** | Individual prediction | Why the model predicted *this specific value* for *this ticker* |

**Analogy:**
- Feature Importance = "What does a chef generally use in recipes?" (flour, eggs, salt)
- Model Insights = "Why does this cake taste chocolatey?" (used 3 cups of cocoa)

---

## 🛠️ Troubleshooting {#troubleshooting}

### Issue 1: "No explanation generated"

**Cause:** Button clicked but results don't appear

**Fix:**
1. Check browser console for errors (F12 → Console tab)
2. Verify dashboard is running (`python app.py`)
3. Ensure you selected a ticker from the dropdown
4. Wait 2-3 seconds (explanation generation takes time)

### Issue 2: Plot not rendering

**Cause:** Plotly chart shows blank/white space

**Fix:**
1. Check if `plotly` library is installed: `pip list | grep plotly`
2. Try refreshing the browser (Ctrl+F5)
3. Switch to another tab and back
4. Restart the dashboard

### Issue 3: "Mock Mode" badge won't go away

**Cause:** You're in Phase 1 (mock explainability)

**Fix:**
- This is expected! Phase 2 will introduce real SHAP values.
- To test real mode early (advanced users only):
  - Set `AZURE_ML_USE_MOCK=false` in `.env`
  - Deploy Azure ML SHAP endpoint (see deployment guide)

### Issue 4: Explanation takes too long (>5 seconds)

**Cause:** Slow matplotlib rendering or file I/O

**Fix:**
1. Reduce top_n features (use slider: 5 instead of 20)
2. Clear plot cache: Delete `outputs/phase1_reports/explainability_plots/` folder
3. Restart dashboard

---

## 💡 Advanced Tips {#advanced-tips}

### Tip 1: Compare Multiple Tickers

**Workflow:**
1. Generate explanation for AAPL
2. Screenshot or note top 5 features
3. Switch to TSLA, generate explanation
4. Compare: Are the same features important?

**Insight:** If AAPL and TSLA have different top features, they respond to different market forces (tech fundamentals vs. social sentiment).

### Tip 2: Track Feature Importance Over Time

**Workflow:**
1. Generate explanation for AAPL today
2. Note top feature (e.g., "Momentum 20D")
3. Re-run tomorrow after price updates
4. Check if top feature changed

**Insight:** Feature importance shift = regime change (e.g., market switching from momentum-driven to volatility-driven).

### Tip 3: Validate Model Against Your Thesis

**Example:**
- **Your thesis:** TSLA will rise due to strong earnings
- **Model's top features:** Social Sentiment (65%), News Sentiment (20%), Earnings Growth (5%)

**Conclusion:** Model disagrees! It thinks TSLA is driven by hype, not fundamentals. Proceed with caution.

### Tip 4: Use Explanations for Risk Assessment

**High-Risk Patterns:**
- Top feature is "Volume Spike" → Speculative trading
- Top feature is "Social Sentiment" → Meme stock behavior
- Many features near 0 SHAP → Model is uncertain

**Low-Risk Patterns:**
- Top features are "Earnings Growth" + "Momentum" → Fundamentals + technicals align
- High contribution % (>80% explained) → Model is confident
- Negative volatility SHAP → Model prefers stable stocks

### Tip 5: Export Explanations (Phase 2 Feature)

**Coming Soon:**
- CSV export of feature importance table
- PDF report with charts + rationale
- Batch explanations for entire portfolio

---

## 📚 Additional Resources

### Related Documentation

- **Implementation Report:** `docs/phase1_local_intelligence/PHASE1_IMPLEMENTATION_REPORT.md`
- **Diagnostic Report:** `outputs/phase1_reports/phase1_diagnostic_report.md`
- **Azure ML Deployment Guide:** `docs/AZURE_ML_DEPLOYMENT_GUIDE.md`

### External Learning

- **What is SHAP?** [SHAP Documentation](https://shap.readthedocs.io/)
- **Interpreting ML Models:** [Interpretable ML Book](https://christophm.github.io/interpretable-ml-book/)
- **Feature Engineering:** [Kaggle Learn](https://www.kaggle.com/learn/feature-engineering)

### Support

- **Issues:** Report bugs via GitHub Issues
- **Questions:** Ask in project Discord/Slack
- **Feature Requests:** Submit via project roadmap

---

## 🎓 Learning Path (Recommended)

### Week 1: Exploration
1. Read "What is Model Explainability?" section
2. Generate 5 explanations (one per ticker)
3. Compare top features across tickers

### Week 2: Interpretation
1. Read "Interpreting Feature Importance" section
2. Generate explanation for your best-performing stock
3. Check if top features match your success thesis

### Week 3: Validation
1. Read "Advanced Tips" section
2. Run explanations before/after major news events
3. Track feature importance shifts

### Week 4: Integration
1. Use explanations as part of your weekly review
2. Build a "red flag" checklist (e.g., "Social Sentiment" in top 3 = caution)
3. Share learnings with team

---

## 🚀 What's Next? (Phase 2 Roadmap)

### Upcoming Features

1. **Real SHAP Integration**
   - Replace mock values with actual Azure ML SHAP outputs
   - Toggle: `AZURE_ML_USE_MOCK=false`

2. **Interactive Callbacks**
   - Click "Generate Explanation" → Updates results in real-time
   - No page refresh needed

3. **Batch Explanations**
   - "Explain All Portfolio" button
   - Generate 20+ explanations at once
   - Export to CSV

4. **Enhanced Visualizations**
   - SHAP summary plot (beeswarm chart)
   - SHAP dependence plot (feature interactions)
   - Force plot (waterfall chart)

5. **Historical Tracking**
   - Store explanations over time
   - Chart feature importance evolution
   - Alert on regime changes

---

## ✅ Quick Reference Card

**Navigation:** Azure ML Lab → Insights & Metrics → 🧠 Model Insights

**Workflow:**
1. Select ticker (dropdown)
2. Choose top N features (slider, default 10)
3. Click "💡 Generate Explanation"
4. Review chart + textual rationale

**Key Metrics:**
- **SHAP Value:** Impact size (+ or −)
- **Contribution %:** Portion of prediction explained
- **Green Bar:** Positive influence
- **Red Bar:** Negative influence

**Sanity Checks:**
- ✅ Top features make logical sense
- ✅ Contribution % > 5% for top features
- ✅ Total explained > 70%

**Red Flags:**
- ⚠️ Social Sentiment dominates (meme stock risk)
- ⚠️ Top feature < 5% contribution (model uncertain)
- ⚠️ Features contradict each other

---

**User Guide Version:** 1.0  
**Last Updated:** October 29, 2025  
**Phase:** 1 - Mock Mode  
**Next Update:** Phase 2 (Real SHAP Integration)
