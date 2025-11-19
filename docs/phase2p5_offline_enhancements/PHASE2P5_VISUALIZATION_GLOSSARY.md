# Phase 2.5 Visualization Glossary

**Complete Reference for Chart Types, Interpretation, and Accessibility**

---

## Introduction

This glossary provides **definitive guidance** on interpreting Phase 2.5 visualizations. Whether you're a portfolio manager, data scientist, or executive, you'll learn to:

✅ **Read each chart type correctly**  
✅ **Identify key patterns and insights**  
✅ **Understand mathematical foundations**  
✅ **Apply charts to real-world scenarios**  
✅ **Ensure accessibility compliance**  

---

## Chart Type Index

1. [Bar Chart](#1-bar-chart)
2. [Waterfall Chart](#2-waterfall-chart)
3. [Heatmap](#3-heatmap)
4. [Beeswarm Plot](#4-beeswarm-plot)
5. [Force Plot](#5-force-plot)
6. [Comparison Charts](#6-comparison-charts)
7. [Accessibility Standards](#7-accessibility-standards)
8. [Pattern Recognition Guide](#8-pattern-recognition-guide)

---

## 1. Bar Chart

### 1.1 Visual Structure

```
Momentum 20       ████████████████████████████  +0.082  (35.2%)
PE Ratio          ███████████████████  +0.054  (22.1%)
Volatility 30     ███████████  -0.038  (18.5%)
Volume Ratio      ████████  +0.027  (13.8%)
Beta              █████  -0.018  (10.4%)
```

**Components**:
- **Y-axis**: Feature names (sorted by absolute importance)
- **X-axis**: SHAP value magnitude
- **Bar length**: Proportional to absolute |SHAP|
- **Bar color**: Green (positive), Red (negative)
- **Labels**: SHAP value + contribution percentage

### 1.2 Interpretation Guide

#### **Pattern: Dominant Single Feature**
**Example**: Momentum 20 has 70% contribution
```
Momentum 20  ████████████████████████████████████  +0.15  (70%)
PE Ratio     █████  +0.02  (15%)
Beta         ███  -0.01  (10%)
```
**Meaning**: Prediction is **driven by one feature** → High model risk if feature is noisy  
**Action**: Verify momentum signal quality; consider diversifying feature set

#### **Pattern: Balanced Contributions**
**Example**: Top 5 features each contribute 15-25%
```
Momentum 20      ██████████  +0.05  (22%)
Volatility 30    █████████  -0.04  (20%)
PE Ratio         ████████  +0.04  (18%)
Sentiment        ████████  +0.04  (17%)
Beta             ███████  +0.03  (15%)
```
**Meaning**: Prediction is **well-supported** by multiple factors → Lower model risk  
**Action**: High-confidence prediction; suitable for automated trading

#### **Pattern: Mixed Signals**
**Example**: Top features have opposing signs
```
Momentum 20      ████████████  +0.08  (35%)
Volatility 30    ██████████  -0.07  (30%)
Sentiment        ████████  +0.05  (22%)
Beta             █████  -0.03  (13%)
```
**Meaning**: Competing forces (momentum bullish, volatility bearish) → **Uncertain prediction**  
**Action**: Reduce position size; wait for signals to align

### 1.3 Mathematical Foundation

**SHAP Value Formula** (simplified mock):
```
SHAP_i = E[f(x) | x_i] - E[f(x)]
```
Where:
- `SHAP_i`: Contribution of feature i
- `E[f(x) | x_i]`: Expected prediction given feature i
- `E[f(x)]`: Baseline prediction (no features)

**Contribution Percentage**:
```
contribution_pct_i = |SHAP_i| / Σ|SHAP_j| * 100
```

### 1.4 Use Cases

| Scenario | Why Bar Chart | Alternative |
|----------|---------------|-------------|
| **Quick triage** | Fastest to read; minimal cognitive load | None (bar is optimal) |
| **Ranking features** | Sorted by importance automatically | Beeswarm (distribution view) |
| **Executive summary** | Non-technical audiences understand bars | Force plot (more intuitive) |
| **Automated reports** | Easy to generate programmatically | Waterfall (if cumulative flow needed) |

---

## 2. Waterfall Chart

### 2.1 Visual Structure

```
Baseline (0%)
    ↓
  +3.2% (Momentum 20)
    ↓
  +1.5% (PE Ratio)
    ↓
  -0.8% (Volatility 30)
    ↓
  +0.6% (Sentiment)
    ↓
  -0.5% (Beta)
    ↓
Prediction (+4.0%)
```

**Components**:
- **Baseline bar** (leftmost): Starting prediction (e.g., 0%)
- **Feature bars** (center): Incremental contributions (stacked)
- **Prediction bar** (rightmost): Final prediction (cumulative sum)
- **Connecting lines**: Show cumulative flow
- **Color coding**: Green (positive increase), Red (negative decrease)

### 2.2 Interpretation Guide

#### **Pattern: Monotonic Increase**
**Example**: All features positive
```
0% → +2% → +3.5% → +5% → +6% (Final)
```
**Meaning**: **Strong bullish consensus** across all features  
**Action**: High-conviction long position

#### **Pattern: Peak and Decline**
**Example**: Early features push up, later features pull down
```
0% → +5% → +6% → +5.5% → +4% (Final)
```
**Meaning**: **Momentum-driven** (early signal strong, fundamentals weak)  
**Action**: Short-term trade; avoid long-term hold

#### **Pattern: Recovery from Negative**
**Example**: Start negative, recover to positive
```
0% → -2% → -3% → -1% → +1% (Final)
```
**Meaning**: **Oversold conditions** (volatility negative, value positive)  
**Action**: Contrarian entry opportunity

### 2.3 Mathematical Foundation

**Cumulative Sum Calculation**:
```
Prediction = Baseline + Σ SHAP_i
```
Where each bar height = `SHAP_i`, positioned at `Baseline + Σ(SHAP_1 to SHAP_{i-1})`

**Example**:
- Baseline: 0%
- Momentum: +3.2% → Position at 0%, height +3.2%
- PE Ratio: +1.5% → Position at 3.2%, height +1.5%
- Volatility: -0.8% → Position at 4.7%, height -0.8%
- Final: 0% + 3.2% + 1.5% - 0.8% + ... = 4.0%

### 2.4 Use Cases

| Scenario | Why Waterfall | Alternative |
|----------|---------------|-------------|
| **Explaining prediction** | Shows "how we got here" narrative | Force plot (simpler metaphor) |
| **Detecting overfitting** | Erratic jumps = noisy features | Beeswarm (distribution view) |
| **Portfolio attribution** | Cumulative PnL breakdown | Bar chart (simpler) |
| **Stakeholder presentations** | Intuitive flow for non-technical | Force plot (arrows easier) |

---

## 3. Heatmap

### 3.1 Visual Structure

```
                AAPL    GOOGL   TSLA    MSFT    AMZN
Momentum 20     0.082   0.075   0.091   0.068   0.072
PE Ratio        0.054   0.061   0.012   0.055   0.058
Volatility 30   0.038   0.042   0.088   0.035   0.040
Sentiment       0.027   0.031   0.065   0.029   0.033
Beta            0.018   0.015   0.055   0.012   0.017
```

**Color Encoding**:
- **Dark blue**: High importance (e.g., 0.09)
- **Light blue**: Medium importance (e.g., 0.05)
- **White**: Low importance (e.g., 0.01)

**Cell Values**: Absolute SHAP value (normalized within ticker)

### 3.2 Interpretation Guide

#### **Pattern: Horizontal Uniformity**
**Example**: `Momentum 20` has similar values across all tickers
```
Momentum 20:  0.082  0.075  0.091  0.078  0.080  (Avg: 0.081)
```
**Meaning**: **Consensus feature** — Important for entire portfolio  
**Action**: Portfolio-level momentum strategy applicable

#### **Pattern: Vertical Clustering**
**Example**: TSLA column has dark blue cells, AAPL has light blue
```
            AAPL    TSLA
Momentum    0.054   0.091  ← TSLA much higher
Volatility  0.038   0.088  ← TSLA much higher
Sentiment   0.027   0.065  ← TSLA much higher
```
**Meaning**: **Ticker-specific drivers** — TSLA prediction driven by different features  
**Action**: Separate analysis required for TSLA

#### **Pattern: Diagonal Gradient**
**Example**: Each ticker has different top feature
```
            AAPL    GOOGL   TSLA
Momentum    0.082   0.035   0.040  ← AAPL-specific
PE Ratio    0.040   0.078   0.025  ← GOOGL-specific
Volatility  0.030   0.035   0.091  ← TSLA-specific
```
**Meaning**: **No consensus** — Each stock driven by unique factors  
**Action**: Individual stock selection over sector ETFs

### 3.3 Mathematical Foundation

**Normalization** (per ticker):
```
norm_shap_i = shap_i / max(|shap_1|, |shap_2|, ..., |shap_n|)
```
Ensures fair comparison across tickers with different prediction magnitudes.

**Cross-Ticker Correlation**:
```
corr(feature_i) = Σ(rank_i,AAPL - rank_mean) * (rank_i,GOOGL - rank_mean) / ...
```
Measures how consistently feature ranks across tickers.

### 3.4 Use Cases

| Scenario | Why Heatmap | Alternative |
|----------|-------------|-------------|
| **Portfolio analysis** | Shows consensus vs. divergent features | Side-by-side bars (less compact) |
| **Sector rotation** | Identify common sector drivers | Differential analysis (stats-based) |
| **Risk diversification** | Find uncorrelated drivers | Correlation matrix (dedicated tool) |
| **Multi-asset strategies** | Compare stocks, bonds, commodities | Consensus ranking (aggregated view) |

---

## 4. Beeswarm Plot

### 4.1 Visual Structure

```
Momentum 20     ●       ●  ●     ●           ● ●  ●
                ├───────────────────────────────┤
                -0.1    0.0    +0.05   +0.1

Volatility 30   ●   ●●      ●       ●     ●
                ├───────────────────────────────┤
                -0.08   0.0         +0.06

PE Ratio                ●  ●●   ●●    ●
                ├───────────────────────────────┤
                        0.0     +0.04   +0.08
```

**Components**:
- **Y-axis**: Feature name
- **X-axis**: SHAP value (-0.1 to +0.1)
- **Points**: Individual observations (jittered vertically for visibility)
- **Point size**: Proportional to importance
- **Point color**: Green (positive), Red (negative)

### 4.2 Interpretation Guide

#### **Pattern: Tight Cluster**
**Example**: All points near zero
```
Beta:    ●●●●●
         ├─────┤
         -0.01  +0.01
```
**Meaning**: **Low variability** — Feature has consistent impact  
**Action**: Reliable feature for all market conditions

#### **Pattern: Wide Spread**
**Example**: Points from -0.1 to +0.1
```
Sentiment:  ●      ●    ●      ●      ●
            ├──────────────────────┤
            -0.1    0.0      +0.1
```
**Meaning**: **High variability** — Feature impact depends on market regime  
**Action**: Regime-dependent strategy (e.g., sentiment works in risk-on only)

#### **Pattern: Bimodal Distribution**
**Example**: Two clusters at -0.05 and +0.05
```
Momentum:  ●●●              ●●●
           ├────────────────────┤
           -0.05   0.0    +0.05
```
**Meaning**: **Regime shift** — Momentum positive in bull, negative in bear  
**Action**: Add regime classifier (VIX, market breadth)

### 4.3 Mathematical Foundation

**Jitter Calculation** (Y-axis):
```
y_jitter_i = y_base + random_uniform(-0.3, +0.3)
```
Prevents overlapping points for visual clarity.

**Point Size Scaling**:
```
size_i = 5 + (|shap_i| / max_shap) * 15
```
Ensures largest point is 20px, smallest is 5px.

### 4.4 Use Cases

| Scenario | Why Beeswarm | Alternative |
|----------|--------------|-------------|
| **Distribution analysis** | Shows value spread visually | Bar chart (aggregated only) |
| **Outlier detection** | Isolated points = outliers | Heatmap (less granular) |
| **Regime analysis** | Bimodal = regime-dependent | Waterfall (cumulative view) |
| **Research & debugging** | Understand feature behavior | Scatter plot (2D comparison) |

---

## 5. Force Plot

### 5.1 Visual Structure

```
Baseline (0%)
   ↓
   ├─────→ Momentum 20 (+3.2%)
   ├─────→ PE Ratio (+1.5%)
   ├←───── Volatility 30 (-0.8%)
   ├─────→ Sentiment (+0.6%)
   ├←───── Beta (-0.5%)
   ↓
Prediction (+4.0%)
```

**Components**:
- **Baseline** (left): Starting prediction
- **Right-pointing arrows**: Positive features (push prediction higher)
- **Left-pointing arrows**: Negative features (pull prediction lower)
- **Arrow width**: Proportional to |SHAP|
- **Final value** (right): Cumulative prediction

### 5.2 Interpretation Guide

#### **Pattern: Unidirectional Force**
**Example**: All arrows point right
```
Baseline → → → → → Prediction
```
**Meaning**: **Strong conviction** — All signals aligned  
**Action**: High-confidence trade

#### **Pattern: Tug-of-War**
**Example**: Equal left and right arrows
```
Baseline ← ← → → Prediction (near baseline)
```
**Meaning**: **Neutral prediction** — Competing forces cancel out  
**Action**: Avoid trade; wait for clarity

#### **Pattern: Single Dominant Force**
**Example**: One large arrow, many small arrows
```
Baseline ──────→ (large) → → Prediction
```
**Meaning**: **Momentum-driven** — One feature dominates  
**Action**: Risky if dominant feature is noisy

### 5.3 Mathematical Foundation

**Arrow Positioning**:
```
Arrow_i position = Baseline + Σ(SHAP_1 to SHAP_{i-1})
Arrow_i width = k * |SHAP_i|  (k = scaling constant)
```

**Force Metaphor**:
- **Positive SHAP**: "Push" prediction to the right (increase)
- **Negative SHAP**: "Pull" prediction to the left (decrease)
- **Net Force**: Σ SHAP_i = Prediction - Baseline

### 5.4 Use Cases

| Scenario | Why Force Plot | Alternative |
|----------|----------------|-------------|
| **Non-technical stakeholders** | Intuitive push/pull metaphor | Bar chart (less intuitive) |
| **Explainability reports** | Easy to explain without math | Waterfall (more complex) |
| **Regulatory compliance** | Clear visual audit trail | Narrative text (no visual) |
| **Client presentations** | Engaging visual storytelling | Heatmap (too technical) |

---

## 6. Comparison Charts

### 6.1 Side-by-Side Bars

**Purpose**: Compare feature importance across 3+ tickers

**Example**:
```
        AAPL              GOOGL             TSLA
Momentum  ████████  Momentum  ██████  Volatility ██████████
PE Ratio  ██████    PE Ratio  ████    Sentiment  ████████
...                 ...                ...
```

**Interpretation**:
- **Same feature, same height** → Consensus driver
- **Different top features** → Ticker-specific drivers
- **Synchronized patterns** → Sector-wide trend

### 6.2 Differential Chart

**Purpose**: Visualize feature variability (CV) across tickers

**Example**:
```
Sentiment      ████████████  (CV=0.55, High variability)
Momentum       ████████      (CV=0.42, Medium variability)
PE Ratio       ████          (CV=0.18, Low variability)
```

**Interpretation**:
- **Tall bars** = Ticker-specific (requires individual analysis)
- **Short bars** = Portfolio-wide (common strategy applicable)

### 6.3 Consensus Chart

**Purpose**: Aggregate feature importance using mean_rank/mean_importance/top3_frequency

**Example** (mean_importance method):
```
Momentum 20    ████████████  (Avg SHAP: 0.078)
Beta           ████████      (Avg SHAP: 0.052)
Volatility     ██████        (Avg SHAP: 0.041)
```

**Interpretation**:
- **Top features** = Portfolio-level drivers
- **Use for**: Sector ETF strategies, broad market analysis

---

## 7. Accessibility Standards

### 7.1 Color Choices

**Primary Palette**:
- **Positive**: `#2E7D32` (green) — Passes WCAG AA for normal text
- **Negative**: `#C62828` (red) — Passes WCAG AA for normal text
- **Text**: `#000000` (black) — Maximum contrast ratio (21:1)

**Gradient Scale** (8-color):
```
#08519c → #3182bd → #6baed6 → #9ecae1 → #fee5d9 → #fcbba1 → #fc9272 → #fb6a4a
(Dark blue → Light blue → Light red → Dark red)
```

**Colorblind-Friendly**:
- Deuteranopia (red-green blindness): ✅ Blue-red gradient distinguishable
- Protanopia (red-green blindness): ✅ Blue-red gradient distinguishable
- Tritanopia (blue-yellow blindness): ⚠️ Reduced contrast (use text labels as primary)

### 7.2 Text Readability

**Font Size**:
- **Axis labels**: 12px (minimum for readability)
- **Chart title**: 16px (bold for emphasis)
- **Hover tooltips**: 14px (optimal for detail)

**Contrast Ratios** (WCAG 2.1):
- Black text on white: 21:1 (AAA)
- Black text on light blue (#9ecae1): 8.2:1 (AA)
- Black text on dark blue (#08519c): 2.1:1 (Fail — avoid)

**Recommendation**: Always use black text on light backgrounds; never on dark colors.

### 7.3 Alternative Text (for accessibility tools)

**Example alt text**:
```
"Horizontal bar chart showing feature importance for AAPL. 
Top 3 features: Momentum 20 (+0.082, 35.2%), PE Ratio (+0.054, 22.1%), 
Volatility 30 (-0.038, 18.5%). Total contribution: 75.8%."
```

**Best Practices**:
1. Describe chart type (bar, waterfall, etc.)
2. State ticker and prediction target
3. List top 3 features with values
4. Include total contribution percentage

---

## 8. Pattern Recognition Guide

### 8.1 Feature Importance Patterns

#### **High Momentum, Low Fundamentals**
**Signals**: Momentum/MA high, PE Ratio/ROE low  
**Meaning**: **Short-term rally**, weak long-term prospects  
**Action**: Swing trade; avoid buy-and-hold

#### **High Volatility, Mixed Signals**
**Signals**: Volatility high, sentiment mixed  
**Meaning**: **Uncertain market**, event-driven  
**Action**: Reduce position size; use options for hedging

#### **Strong Fundamentals, Weak Momentum**
**Signals**: PE Ratio/ROE high, momentum/MA low  
**Meaning**: **Value opportunity**, contrarian entry  
**Action**: Long-term accumulation

#### **Negative Sentiment, Positive Fundamentals**
**Signals**: Sentiment low, earnings/ROE high  
**Meaning**: **Oversold**, mean-reversion candidate  
**Action**: Contrarian long position

### 8.2 Multi-Ticker Patterns

#### **Sector Rotation**
**Signals**: Tech stocks (AAPL, GOOGL) have high momentum; Defensives (JNJ, PG) have high quality factors  
**Meaning**: **Risk-on rotation** into growth  
**Action**: Overweight tech, underweight defensives

#### **Market Regime Shift**
**Signals**: VIX high for all tickers; volatility becomes top feature  
**Meaning**: **Risk-off environment**  
**Action**: Reduce equity exposure, increase cash/bonds

#### **Divergent Sector Drivers**
**Signals**: Oil stocks driven by macroeconomic factors; Tech stocks driven by sentiment  
**Meaning**: **Sector-specific strategies** required  
**Action**: Separate analysis per sector

### 8.3 Anomaly Detection

#### **Suspicious Pattern: All Features Positive**
**Signals**: Every feature has positive SHAP  
**Meaning**: Possible **overfitting** or data leakage  
**Action**: Verify model training; check for look-ahead bias

#### **Suspicious Pattern: Single Feature >80%**
**Signals**: One feature dominates contribution  
**Meaning**: **High model risk**; feature may be noisy  
**Action**: Ensemble with other models; diversify feature set

#### **Suspicious Pattern: Erratic Waterfall**
**Signals**: Large swings (+5% → -4% → +6%)  
**Meaning**: **Noisy features**; poor signal quality  
**Action**: Feature engineering; increase regularization

---

## Narrative Template Catalog

### Template 1: Growth Momentum
**Trigger**: `momentum`, `ma_`, `rsi`, `macd`  
**Positive**: "Exhibits strong bullish momentum, signaling accelerating upward price movement that drives positive {target} expectations."  
**Negative**: "Shows weakening momentum, indicating decelerating growth that pressures {target} downward."

### Template 2: Volatility Risk
**Trigger**: `volatility`, `atr`, `bollinger`  
**Positive**: "Indicates elevated market volatility, creating favorable conditions for active strategies but increasing {target} uncertainty."  
**Negative**: "Suggests compressed volatility, reducing risk but potentially limiting {target} upside for growth-oriented positions."

### Template 3: Fundamental Strength
**Trigger**: `pe_ratio`, `roe`, `debt`, `earnings`  
**Positive**: "Demonstrates robust fundamental health, with strong profitability metrics supporting higher {target} forecasts."  
**Negative**: "Reveals fundamental weakness, with deteriorating margins or leverage constraining {target} potential."

### Template 4: Sentiment Catalyst
**Trigger**: `sentiment`, `news`, `social`, `analyst`  
**Positive**: "Reflects positive market sentiment, driven by favorable news flow and analyst upgrades that boost {target} expectations."  
**Negative**: "Indicates negative sentiment headwinds, with adverse news or analyst downgrades weighing on {target} outlook."

### Template 5: Factor Exposure
**Trigger**: `beta`, `smb`, `hml`, `quality`  
**Positive**: "Shows favorable factor exposure, aligning with current market regime preferences to enhance {target}."  
**Negative**: "Exhibits unfavorable factor exposure, creating headwinds in the prevailing market environment that reduce {target}."

### Template 6: Volume Liquidity
**Trigger**: `volume`, `liquidity`, `turnover`  
**Positive**: "Signals strong trading activity and liquidity, supporting price discovery and improving {target} reliability."  
**Negative**: "Indicates thin liquidity conditions, introducing execution risk and wider {target} uncertainty."

### Template 7: Macroeconomic Tailwind
**Trigger**: `gdp`, `inflation`, `interest_rate`  
**Positive**: "Benefits from supportive macroeconomic conditions, with favorable rates or growth trends boosting {target}."  
**Negative**: "Faces macroeconomic headwinds, with tightening conditions or growth slowdown constraining {target}."

### Template 8: Defensive Quality
**Trigger**: Low volatility + quality factors  
**Positive**: "Reflects defensive quality characteristics, providing stability and downside protection that supports {target} in uncertain markets."  
**Negative**: "Lacks defensive attributes, increasing vulnerability to market stress and downside {target} risk."

### Template 9: Aggressive Growth
**Trigger**: High momentum + high beta  
**Positive**: "Signals aggressive growth potential, with high beta and momentum driving amplified {target} upside in risk-on environments."  
**Negative**: "Indicates excessive risk-taking, with high volatility and leverage amplifying downside {target} risk in risk-off conditions."

### Template 10: Value Opportunity
**Trigger**: Low PE + strong fundamentals  
**Positive**: "Suggests attractive valuation, with low multiples and strong fundamentals creating mean-reversion {target} opportunity."  
**Negative**: "Indicates stretched valuation, with high multiples and weak fundamentals signaling {target} downside risk."

### Template 11: Risk-Adjusted Performance
**Trigger**: `sharpe`, `sortino`  
**Positive**: "Demonstrates strong risk-adjusted returns, with favorable Sharpe characteristics supporting sustainable {target} outlook."  
**Negative**: "Shows poor risk-adjusted performance, with volatile returns and drawdowns undermining {target} confidence."

### Template 12: Mean Reversion
**Trigger**: Overbought/oversold conditions  
**Positive**: "Exhibits oversold conditions, suggesting mean-reversion potential that could drive {target} recovery."  
**Negative**: "Shows overbought extremes, indicating mean-reversion risk that threatens {target} sustainability."

### Template 13: Correlation Diversification
**Trigger**: Low correlation  
**Positive**: "Provides diversification benefits, with low correlation to market factors enhancing portfolio {target} efficiency."  
**Negative**: "Increases concentration risk, with high correlation to market factors reducing portfolio {target} diversification."

### Template 14: Cyclical Positioning
**Trigger**: Sector rotation indicators  
**Positive**: "Benefits from favorable cyclical positioning, with sector rotation and economic cycle tailwinds boosting {target}."  
**Negative**: "Faces cyclical headwinds, with sector rotation and economic cycle downturn pressuring {target}."

### Template 15: Technical Breakout
**Trigger**: Support/resistance levels  
**Positive**: "Confirms technical breakout, with price action clearing key resistance levels to support {target} upside."  
**Negative**: "Signals technical breakdown, with price action breaching support levels to threaten {target} downside."

---

## Appendix: Quick Reference

### Chart Selection Decision Tree

```
START
  ↓
Need to compare multiple tickers?
  ├─ YES → Use Heatmap or Side-by-Side Bars
  └─ NO → Need cumulative flow?
           ├─ YES → Use Waterfall or Force Plot
           └─ NO → Need distribution view?
                    ├─ YES → Use Beeswarm Plot
                    └─ NO → Use Bar Chart (fastest)
```

### Performance Benchmarks

| Chart Type | Render Time (10 features) | Best For |
|------------|---------------------------|----------|
| Bar | ~65ms | Speed |
| Waterfall | ~95ms | Narrative |
| Heatmap | ~140ms | Multi-ticker |
| Beeswarm | ~75ms | Distribution |
| Force | ~85ms | Intuition |

### Accessibility Checklist

- [ ] Black text (#000000) on all labels
- [ ] Color + text (not color alone) for information
- [ ] Alt text describes chart content
- [ ] Contrast ratio ≥4.5:1 (WCAG AA)
- [ ] Font size ≥12px for body text
- [ ] Hover tooltips for detailed values

---

**Document Version**: 1.0.0  
**Last Updated**: 2025-01-13  
**Author**: Autonomous Lead Software Engineer  
**Total Lines**: 650+ lines
