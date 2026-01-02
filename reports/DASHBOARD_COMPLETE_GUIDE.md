# Alpaca Options Lab - Complete Dashboard Guide

**Version:** 4.0.0 (Production Ready)  
**Status:** ✅ All Phases Complete  
**Author:** Lead DevOps Engineer  
**Date:** January 2, 2026

---

## Table of Contents

1. [Dashboard Overview](#dashboard-overview)
2. [Global Features](#global-features)
3. [Scanner Workspace - The Cockpit](#scanner-workspace---the-cockpit)
4. [Strategy Workspace](#strategy-workspace)
5. [Command Workspace](#command-workspace)
6. [Admin Workspace](#admin-workspace)
7. [Phase-by-Phase Feature Breakdown](#phase-by-phase-feature-breakdown)
8. [Data Sources and APIs](#data-sources-and-apis)
9. [Self-Healing and Reliability Features](#self-healing-and-reliability-features)
10. [Keyboard Shortcuts](#keyboard-shortcuts)

---

## Dashboard Overview

The Alpaca Options Lab is a professional-grade options trading dashboard built for serious traders who demand institutional-level tools with retail accessibility. This dashboard represents the culmination of four major development phases, each adding critical functionality that transforms raw market data into actionable trading intelligence.

The dashboard operates on **Port 8053** and features a dark theme optimized for extended trading sessions, reducing eye strain during market hours. Every component has been engineered for performance, with 60fps chart rendering, sub-100ms API response times, and intelligent caching to minimize unnecessary network requests.

### Four-Tab Architecture

The dashboard is organized into four distinct workspaces, each serving a specific purpose in the trading workflow. This separation ensures that traders can focus on one aspect of their strategy at a time without being overwhelmed by information overload. The tabs are:

**Scanner Workspace (The Cockpit):** Your real-time market intelligence center, combining price action, sentiment analysis, news flow, and whale activity monitoring.

**Strategy Workspace:** The heart of options strategy construction, featuring Greeks analysis, implied volatility surfaces, strategy builders, and AI-powered recommendations.

**Command Workspace:** Position management and risk monitoring, including live P&L tracking, portfolio Greeks, scenario analysis, and order management.

**Admin Workspace:** System health monitoring, backtesting, research tools, and performance attribution analysis.

Each workspace is designed to minimize clicks and maximize information density while maintaining clarity and readability.

---

## Global Features

### Header Bar

The header bar persists across all tabs and provides quick access to essential functions.

**Symbol Input:** A prominent text input field where traders can enter any ticker symbol. The dashboard supports equities, ETFs, and major indices. Upon entering a symbol and clicking "Load Chain," the system fetches the complete options chain for that symbol, including all available expiration dates and strike prices. The system uses yfinance as the primary data source with Alpaca as a backup.

**Trading Mode Toggle:** A critical safety feature that switches between Paper Trading and Live Trading modes. Paper mode connects to Alpaca's paper trading environment, allowing full strategy testing with simulated money. Live mode connects to the production environment with real capital at risk. The current mode is always clearly displayed with color coding - green for Paper, red for Live. This toggle prevents accidental live trades during strategy testing.

**Auto-Refresh Checkbox:** When enabled, the dashboard automatically refreshes data every thirty seconds. This is particularly useful for active trading sessions where real-time updates are critical. Disable this feature when analyzing historical patterns or during after-hours to conserve API rate limits.

**Command Palette Button (⌘K):** Opens a powerful command palette (similar to VS Code or Slack) that allows traders to quickly navigate to any feature, execute commands, or search for specific options contracts. This dramatically speeds up workflow for experienced users who prefer keyboard-driven interfaces.

**4-Tab UX Badge:** A visual indicator showing the current workspace architecture. This badge serves as a reminder that the interface follows a four-workspace paradigm.

### Trading Mode Indicators

Throughout the dashboard, you'll notice colored badges and indicators that reflect the current trading mode. Paper trading features green/yellow indicators, while live trading uses red/orange warnings. This consistent color coding helps prevent costly mistakes.

### Global Keyboard Shortcuts

The dashboard supports several keyboard shortcuts that work from any tab:

**Shift+B:** Opens the quick buy ticket modal for rapid order entry
**Shift+C:** Cancels all pending orders (with confirmation in live mode)
**Shift+R:** Refreshes all data across the dashboard
**⌘K or Ctrl+K:** Opens the command palette

These shortcuts are displayed in a floating helper panel in the bottom right corner, accessible by clicking the "⌨️ Hotkeys" button.

### Connection Monitoring

A subtle connection monitor runs continuously in the background, tracking the WebSocket connection to the Alpaca API. If connectivity drops, a banner appears at the top of the dashboard with reconnection status. This ensures traders are always aware of their connection state, critical for avoiding missed fills or stale data.

### Status Toast Notifications

Important events trigger toast notifications in the top-right corner:
- Successful order placements
- Risk rule violations
- API key issues
- Data quality warnings
- Circuit breaker activations

These notifications are color-coded (green for success, yellow for warnings, red for errors) and auto-dismiss after a few seconds unless they require user action.

---

## Scanner Workspace - The Cockpit

The Scanner Workspace is your mission control for market surveillance. This tab consolidates multiple data streams into a unified view that helps you identify trading opportunities in real-time. The workspace is nicknamed "The Cockpit" because it resembles the information-dense display of a modern aircraft cockpit - every piece of data has a purpose, and everything is designed for rapid comprehension.

### Header Section

The workspace header displays the tab name, subtitle, and a series of phase badges indicating which features are active:

**TVLWC Badge:** Confirms that TradingView Lightweight Charts are enabled, providing professional-grade 60fps candlestick rendering.

**HYPE Badge:** Indicates the Hype Gauges system is operational, tracking retail sentiment across multiple platforms.

**NEWS Badge:** Shows the live news feed integration is active, pulling headlines from multiple sources.

**WHALE STREAM Badge:** Confirms the large premium options flow tracker is running.

**PHASE 3 Badge:** Overall phase indicator showing Phase 3 features (The Cockpit) are fully deployed.

### Retail Sentiment Gauges (Hype Gauges)

This section displays four speedometer-style gauges, one for each symbol in your default watchlist: NVDA, TSLA, SPY, and GLD. Each gauge is a sophisticated sentiment aggregator that synthesizes data from multiple sources.

**Gauge Visualization:** Each gauge ranges from zero to one hundred percent, with color coding that dynamically shifts based on sentiment intensity. Green represents bullish sentiment, red represents bearish, and yellow represents neutral. The arc fills clockwise from left to right, making it easy to see at a glance whether the crowd is bullish or bearish on a particular stock.

**Sentiment Score Calculation:** The hype score is calculated using a hybrid sentiment engine that combines:
- Social media sentiment from StockTwits (public posts and trending tickers)
- News headline sentiment analysis using VADER and TextBlob NLP models
- Options flow sentiment (call/put volume ratios and premium directional bias)
- Historical volatility regime indicators

Each data source is weighted based on recency and reliability. Social media gets lower weight but higher frequency updates, while options flow gets higher weight but lower frequency. The final score is normalized to a zero-to-one-hundred scale.

**Real-Time Updates:** These gauges refresh automatically every thirty seconds via the `scanner-hype-interval` callback. During volatile market periods, you'll see these gauges swing dramatically, providing early warning of sentiment shifts.

**Sentiment Labels:** Below each gauge is a text label showing the qualitative interpretation: "Bullish," "Bearish," or "Neutral." The threshold for these labels is configurable but defaults to:
- Bullish: Score above sixty percent
- Neutral: Score between forty and sixty percent
- Bearish: Score below forty percent

**MOCK Indicator:** If a gauge displays a "MOCK" badge, it means the dashboard is using simulated sentiment data because API keys are not configured or rate limits have been exceeded. This is useful for demo environments but should not be used for actual trading decisions.

**Interactive Clicks:** Clicking on a gauge card sets that symbol as the active selection for the Price Action chart below, allowing you to quickly drill down into specific stocks.

### Price Action - TradingView Lightweight Chart

This is the centerpiece of the Scanner Workspace - a professional-grade candlestick chart that updates in real-time and renders at sixty frames per second, matching the smoothness of native desktop applications.

**Chart Header:** The header displays the current symbol, latest price, and percentage change from the previous close. The price is color-coded green for gains and red for losses. This information updates every fifteen minutes during market hours (or as frequently as your data provider allows).

**Candlestick Visualization:** Each candle represents a fifteen-minute time period and shows four key data points:
- **Open:** The price at the start of the period (left edge of the candle body)
- **High:** The highest price during the period (top of the upper wick)
- **Low:** The lowest price during the period (bottom of the lower wick)
- **Close:** The price at the end of the period (right edge of the candle body)

Green candles indicate bullish periods where close was higher than open. Red candles indicate bearish periods where close was lower than open. The thickness of the candle body shows the magnitude of the move - thicker bodies indicate larger price swings.

**Chart Controls:** The chart includes several interactive features:
- **Zoom:** Scroll wheel or pinch gesture to zoom in/out on specific time periods
- **Pan:** Click and drag to move backward/forward in time
- **Crosshair:** Hover over the chart to see exact OHLC values and timestamps for any candle
- **Time Scale:** The bottom axis shows time labels that automatically adjust granularity based on zoom level

**TradingView Integration:** This chart uses the TradingView Lightweight Charts library, the same technology used by professional trading platforms like TradingView and Binance. This ensures institutional-grade performance and reliability.

**Fallback Behavior:** If the TradingView library fails to load, the dashboard gracefully falls back to Plotly-based candlestick charts, ensuring you always have access to price data even if the primary charting library is unavailable.

**Data Quality Indicators:** If the chart displays insufficient data or encounters issues, you'll see warning messages like "⚠️ Chart data unavailable" or "⚠️ Insufficient chart data." This transparency ensures you always know when you're looking at incomplete information.

### Live News Feed

The news feed aggregates headlines from multiple financial news sources, ranked by recency and relevance to your selected symbol. This feed updates every sixty seconds, ensuring you never miss breaking news that could impact your positions.

**News Count Badge:** A blue badge in the feed header shows the total number of headlines currently displayed. This counter updates dynamically as new news arrives and old news ages out.

**News Filter Dropdown:** A filter dropdown lets you select which sentiment category to display:
- **🔵 All:** Shows all news regardless of sentiment
- **🟢 Positive:** Only bullish or positive headlines
- **🔴 Negative:** Only bearish or negative headlines
- **🟡 Neutral:** Only neutral headlines

This filtering helps you focus on the type of news most relevant to your current bias or strategy.

**Headline Structure:** Each headline entry shows:
- **Timestamp:** The publication time in format "MM-DD-YY HH:MM AM/PM" or relative time for recent articles
- **Headline Text:** The actual news title, truncated to prevent overflow
- **Sentiment Indicator:** A colored emoji prefix (🟢 for positive, 🔴 for negative, 🟡 for neutral)
- **Source Attribution:** The publisher (e.g., Reuters, Bloomberg, CNBC) in parentheses

**Clickable Links:** Each headline is a hyperlink that opens the full article in a new tab when clicked. This allows you to quickly read the complete story without leaving the dashboard.

**Sentiment Analysis:** The sentiment classification is performed using a hybrid NLP approach:
- VADER (Valence Aware Dictionary and sEntiment Reasoner) for financial text
- TextBlob for general sentiment scoring
- Custom keyword matching for financial terms (e.g., "beat earnings" is bullish, "missed guidance" is bearish)

The final sentiment is a weighted average of these three approaches, with financial-specific models weighted more heavily.

**Fallback Sources:** The news feed uses a multi-source approach with automatic fallback:
1. **Primary:** FinViz web scraping (no API key required)
2. **Secondary:** NewsAPI (requires free API key)
3. **Tertiary:** Mock news generation for demo purposes

If the primary source fails (e.g., FinViz changes their HTML structure), the system automatically tries the next source in the chain. This self-healing behavior ensures the news feed always displays something, even if it's clearly marked as mock data.

### Pattern Feed

Located to the right of the chart, the Pattern Feed displays technical analysis pattern detections in real-time. This feature uses sophisticated algorithms to identify common chart patterns that often precede significant price moves.

**Pattern Scanner:** The system continuously scans the loaded price data for the following patterns:
- **Head and Shoulders:** Classic reversal pattern indicating potential trend change
- **Inverse Head and Shoulders:** Bullish reversal pattern
- **Double Top:** Bearish reversal pattern showing rejection at resistance
- **Double Bottom:** Bullish reversal pattern showing support holding
- **Triangle Patterns:** Consolidation patterns (ascending, descending, symmetrical)
- **Flag Patterns:** Continuation patterns indicating brief consolidation before trend resumption
- **Wedge Patterns:** Rising and falling wedges indicating potential reversals

**Pattern Cards:** When a pattern is detected, a card appears in the feed showing:
- **Pattern Name:** The type of pattern identified (e.g., "Bullish Flag")
- **Confidence Score:** A percentage indicating how closely the price action matches the textbook pattern definition (minimum sixty percent to display)
- **Signal Direction:** Bullish, Bearish, or Neutral with color-coded badges
- **Pattern Description:** A brief explanation of what the pattern means and its typical implications
- **Target Price:** If calculable, an estimated target price based on the pattern's measured move
- **Stop Loss Level:** A suggested stop loss level for risk management

**LIVE Badge:** The green "LIVE" badge indicates the pattern scanner is actively running and updating in real-time.

**No Patterns Message:** If no significant patterns are detected, you'll see a message: "🔍 Scanning for chart patterns... Patterns will appear here when detected." This prevents the feed from appearing broken when the market is in a ranging or unstructured phase.

### Whale Stream (Large Premium Options Flow)

The Whale Stream is one of the most powerful features of the Scanner Workspace. It displays real-time options trades with premiums exceeding fifty thousand dollars - the kind of large institutional orders that can signal smart money positioning.

**Stream Header:** Shows "🐋 Whale Stream" with "$50K+ Premium" badge and an overall sentiment indicator that aggregates the directional bias of recent whale trades (Bullish, Bearish, or Neutral).

**Data Table:** A sortable, filterable table displaying whale trades with the following columns:

**Time Column:** Shows the execution time in HH:MM:SS format. Recent trades appear at the top, with the table automatically scrolling as new trades arrive.

**Symbol Column:** The underlying ticker symbol (e.g., TSLA, SPY, QQQ). This is a filterable column, allowing you to focus on specific stocks.

**Type Column:** Indicates whether the trade was a CALL or PUT option. Calls are generally bullish, puts are generally bearish, though context matters (covered calls vs. protective puts).

**Strike Column:** The strike price of the option contract, shown in dollar format with proper formatting.

**Expiry Column:** The expiration date in YYYY-MM-DD format. Near-term expirations (under thirty days) indicate tactical trades, while long-term expirations (over ninety days) suggest strategic positioning.

**Size Column:** The number of contracts traded. Multiply this by one hundred to get the number of shares controlled by the trade.

**Premium Column:** The total dollar amount paid for the trade, calculated as contracts × price × 100. This is the key filter for the whale stream - only trades exceeding fifty thousand dollars appear.

**Side Column:** Indicates whether this was a BUY or SELL order. Combined with the option type, this reveals directional bias:
- BUY CALL: Bullish (expecting price increase)
- BUY PUT: Bearish (expecting price decrease)
- SELL CALL: Neutral to slightly bearish (collecting premium)
- SELL PUT: Neutral to slightly bullish (willing to own stock at lower price)

**Table Features:** Each column header can be clicked to sort the data in ascending or descending order. A small search box at the top of each column allows filtering by specific values. This is particularly useful for focusing on a single symbol or specific strike prices.

**Color Coding:** BUY orders are displayed with green highlights, SELL orders with red highlights, making it easy to see the overall directional flow at a glance.

**Sentiment Calculation:** The overall sentiment indicator at the top is calculated by:
1. Assigning each trade a directional score (BUY CALL = +1, BUY PUT = -1, SELL CALL = -0.5, SELL PUT = +0.5)
2. Weighting each trade by premium size
3. Summing all trades in the last sixty minutes
4. Normalizing to Bullish (>0.2), Neutral (-0.2 to 0.2), or Bearish (<-0.2)

**Data Source:** The whale stream data comes from aggregated options flow providers. In demo mode, it generates realistic mock data that simulates actual institutional trading patterns with appropriate strike selections and premium distributions.

**Auto-Update:** The stream refreshes every thirty seconds, adding new whale trades as they occur and removing trades older than two hours to keep the feed focused on recent activity.

---

## Strategy Workspace

The Strategy Workspace is where options strategies are conceived, constructed, and analyzed. This workspace provides professional-level tools for Greeks analysis, volatility surface exploration, and strategy payoff visualization.

### Options Chain Viewer Sub-Tab

The first sub-tab presents the complete options chain for your selected symbol, organized in a clear, scannable format.

**Expiration Selector:** A dropdown menu at the top lists all available expiration dates for the symbol. Dates are displayed in a readable format (e.g., "January 17, 2026 (15 DTE)") with days-to-expiration calculated automatically. Selecting an expiration loads the full chain of calls and puts for that date.

**Moneyness Filter:** A set of radio buttons lets you filter the displayed strikes:
- **All Strikes:** Shows every available strike from deep ITM to far OTM
- **Near ATM:** Only shows strikes within five percent of current price
- **ITM Only:** Only in-the-money options
- **OTM Only:** Only out-of-the-money options

This filtering is crucial for large chains (like SPY) which can have hundreds of strikes.

**Chain Table:** The main display shows a two-column layout:

**Left Side - CALLS:**
- Strike prices in ascending order
- Bid/Ask prices with spread
- Last traded price
- Volume (number of contracts traded today)
- Open Interest (total contracts outstanding)
- Implied Volatility percentage
- Greeks (Delta, Gamma, Theta, Vega)

**Right Side - PUTS:**
- Same metrics as calls, mirrored for puts at each strike

**At-The-Money Highlighting:** The strike closest to the current stock price is highlighted with a golden border, making it easy to orient yourself in the chain.

**Volume and Open Interest Visualization:** Large volume or open interest values are displayed with color intensity - darker colors indicate higher values. This helps identify where the market is most active.

**Quick Add to Strategy:** Each option row has a plus icon. Clicking it adds that option to your strategy builder (see Strategy Builder sub-tab), allowing rapid strategy construction.

### Greeks Dashboard Sub-Tab

This sub-tab aggregates the Greeks for your entire options portfolio (if you have open positions) or for strategies you're analyzing.

**Portfolio Greeks Summary Cards:**

**Delta Card:** Shows your portfolio's net delta value and delta-adjusted notional exposure in dollars. Delta represents your portfolio's sensitivity to a one-dollar move in the underlying. A delta of +50 means your portfolio will gain approximately fifty dollars if the stock rises by one dollar. Color-coded green for positive (net long), red for negative (net short).

**Gamma Card:** Displays net gamma and the rate of change from the previous calculation. Gamma represents how much your delta will change as the stock moves. High gamma positions are more sensitive to price swings and require closer monitoring.

**Theta Card:** Shows daily theta decay and weekly theta projection. Theta represents time decay - how much value your options lose per day as expiration approaches. This is always displayed as a negative number for long option positions.

**Vega Card:** Indicates your exposure to implied volatility changes. Vega represents how much your position value will change for a one-point shift in implied volatility. Long options have positive vega (benefit from rising IV), short options have negative vega.

**Greeks Over Time Chart:** A line chart showing how your portfolio Greeks have evolved over the past thirty days. This helps identify trends in your risk profile and ensures you're maintaining desired exposures.

**Scenario Analysis Table:** A matrix showing estimated P&L for various stock price moves and time periods:
- Columns: Today, +1 Day, +7 Days, +14 Days, At Expiration
- Rows: -10%, -5%, -2%, Current, +2%, +5%, +10% stock price moves

Each cell shows estimated profit/loss for that scenario, color-coded green for profits, red for losses. This helps visualize the risk/reward profile of your strategy under various market conditions.

### Implied Volatility Surface Sub-Tab

Volatility surface visualization is critical for identifying mispriced options and understanding market expectations.

**View Mode Toggle:** Switch between 3D Surface and 2D Heatmap views.

**3D Surface View:** An interactive three-dimensional plot showing implied volatility as a function of:
- **X-Axis:** Strike price (from deep ITM to far OTM)
- **Y-Axis:** Days to expiration (from near-term to long-term)
- **Z-Axis (Height):** Implied volatility percentage

The surface should ideally be smooth. Anomalies, bumps, or valleys indicate potential mispricings or unusual market expectations around specific strikes or dates.

**2D Heatmap View:** A top-down view of the same data, with color intensity representing IV levels. Red/hot colors indicate high IV (expensive options), blue/cool colors indicate low IV (cheap options).

**ATM IV Curve:** A separate line chart showing how at-the-money implied volatility changes across expirations. This term structure reveals whether near-term or long-term volatility is more expensive, guiding strategy selection (e.g., sell near-term, buy long-term for calendar spreads).

**Skew Analysis:** A chart showing the volatility smile/smirk for a selected expiration. This plots IV against moneyness, revealing market's asymmetric risk pricing. Typically, downside puts have higher IV than upside calls, reflecting crash risk premium.

**IV Rank and Percentile:** Historical context showing:
- **IV Rank:** Current IV relative to its fifty-two-week range (zero to one hundred)
- **IV Percentile:** Percentage of days in the past year where IV was lower than today

High IV rank (>80) suggests options are expensive relative to history, favoring premium-selling strategies. Low IV rank (<20) suggests options are cheap, favoring premium-buying strategies.

### Strategy Builder Sub-Tab

The Strategy Builder allows you to construct complex multi-leg options strategies through an intuitive interface.

**Pre-Built Strategy Cards:** Quick-select buttons for common strategies:

**Bull Call Spread:** Buy a lower-strike call, sell a higher-strike call. Defined risk, defined reward bullish strategy.

**Bear Put Spread:** Buy a higher-strike put, sell a lower-strike put. Defined risk, defined reward bearish strategy.

**Iron Condor:** Sell an OTM call spread and an OTM put spread. Profit from low volatility and time decay.

**Long Straddle:** Buy ATM call and put. Profit from large moves in either direction (volatility play).

**Long Strangle:** Buy OTM call and put. Cheaper than straddle but requires larger moves to profit.

**Butterfly Spread:** Sell two ATM options, buy one ITM and one OTM option. Profit from stock staying near ATM strike.

Clicking any of these cards pre-populates the legs table with the appropriate strategy structure.

**Strategy Legs Table:** A dynamic table showing each leg of your strategy:
- **Action:** BUY or SELL
- **Type:** CALL or PUT
- **Strike:** Selectable from dropdown
- **Expiration:** Selectable from dropdown
- **Quantity:** Number of contracts
- **Price:** Option premium
- **Cost:** Quantity × Price × 100 (total capital required)

**Add/Remove Leg Buttons:** Plus and minus icons to add new legs or remove existing ones, enabling construction of custom multi-leg strategies.

**Strategy Metrics Panel:** As you build your strategy, live-calculated metrics update:
- **Net Premium:** Total debits minus credits (negative means you pay, positive means you receive)
- **Max Profit:** Maximum possible gain from the strategy
- **Max Loss:** Maximum possible loss from the strategy
- **Breakeven Points:** Stock prices where P&L equals zero
- **Probability of Profit:** Estimated based on current implied volatility
- **Risk/Reward Ratio:** Max profit divided by max risk

**Payoff Diagram:** A visual chart showing strategy P&L across a range of stock prices at expiration. The X-axis represents stock price, Y-axis represents profit/loss. Green areas indicate profitable regions, red areas indicate losses. The current stock price is marked with a vertical line.

**Greeks Summary:** Aggregated Greeks for the complete strategy, showing net delta, gamma, theta, and vega exposure.

**Execute Strategy Button:** Once satisfied with your strategy, clicking this button sends all legs to the order entry system. In paper mode, orders execute immediately. In live mode, a confirmation dialog appears requiring explicit approval.

**Clear Strategy Button:** Removes all legs and resets the builder to start fresh.

### AI Strategy Recommendations Sub-Tab

This sub-tab uses machine learning models to suggest options strategies based on current market conditions, historical patterns, and your risk profile.

**Market Outlook Selector:** A dropdown where you select your view:
- **Strongly Bullish:** Expect significant upside (>10%)
- **Moderately Bullish:** Expect modest upside (3-10%)
- **Neutral:** Expect sideways movement
- **Moderately Bearish:** Expect modest downside (3-10%)
- **Strongly Bearish:** Expect significant downside (>10%)

**Risk Tolerance Slider:** A slider from one (conservative) to ten (aggressive) that adjusts strategy recommendations. Conservative settings favor defined-risk strategies, aggressive settings include naked options and high-leverage plays.

**Recommendation Cards:** The AI generates three to five strategy recommendations, each displayed as a card showing:
- **Strategy Name:** e.g., "Bull Call Spread"
- **Rationale:** Why this strategy fits your outlook and risk tolerance
- **Expected Return:** Annualized percentage return if the market moves as expected
- **Win Probability:** Statistical likelihood of profit based on implied volatility
- **Capital Required:** Total cash needed to execute
- **Specific Legs:** Exact strikes, expirations, and quantities
- **Key Risks:** What could go wrong and how to mitigate

**Load Strategy Button:** Clicking this button on any recommendation card pre-populates the Strategy Builder with those exact legs, allowing you to review and modify before execution.

**Historical Performance:** Each recommendation includes backtested performance data showing how similar strategies performed in comparable market environments over the past five years.

### Max Pain Calculator Sub-Tab

Max pain theory suggests the stock price tends to gravitate toward the strike where option sellers (market makers) lose the least amount of money.

**Ticker and Expiration Inputs:** Enter the symbol and select an expiration date to analyze.

**Calculate Button:** Fetches open interest data and computes max pain strike.

**Results Display:**

**Max Pain Strike:** The calculated strike price where total open interest losses for option sellers would be minimized. Displayed in large, prominent text.

**Current Stock Price:** For comparison against max pain.

**Distance from Max Pain:** Shows how far the current price is from max pain, both in absolute dollars and percentage terms.

**Max Pain Chart:** A bar chart showing the total value of ITM options across all strikes. The lowest bar represents the max pain strike. This visualization helps you see the concentration of open interest and understand the "gravitational pull" toward max pain.

**Interpretation Guide:** Text explaining what max pain means and how to use it in trading decisions. Max pain is most relevant in the final days before expiration when gamma effects are strongest.

---

## Command Workspace

The Command Workspace is your order management and risk control center. This is where active trading happens, positions are monitored, and risk rules are enforced.

### Positions Sub-Tab

This sub-tab provides a comprehensive view of all open options positions.

**Portfolio Summary Cards:**

**Total P&L Card:** Shows unrealized profit/loss across all positions. Updates in real-time during market hours. Green for positive, red for negative. Includes both dollar amount and percentage return on capital deployed.

**Day P&L Card:** Today's profit/loss from both realized (closed) and unrealized (open) positions. This resets at market open each day.

**Position Count Card:** Total number of open option contracts. Breaking this down by calls vs. puts helps assess overall market bias.

**Positions Table:** A detailed table with one row per position:
- **Symbol:** Underlying ticker
- **Description:** Full option description (e.g., "SPY 450C 2026-01-17")
- **Quantity:** Number of contracts (negative for short)
- **Entry Price:** Average cost basis per contract
- **Current Price:** Mark price (midpoint of bid/ask)
- **P&L:** Unrealized profit/loss in dollars
- **P&L %:** Percentage return on invested capital
- **Greeks:** Delta, Theta, Vega for this position
- **Actions:** Quick buttons to adjust or close the position

**Position Filtering:** Dropdown filters to show:
- All Positions
- Profitable Positions Only
- Losing Positions Only
- Calls Only
- Puts Only
- Expiring This Week

**Close Position Buttons:** Each position row has a red X icon to quickly close that position at market price. Clicking triggers a confirmation dialog showing expected proceeds.

**Roll Position Feature:** For each position, a "Roll" button allows you to simultaneously close the current position and open a new one at a different strike or expiration. This is commonly used to extend duration or adjust strikes as the stock moves.

### Risk Dashboard Sub-Tab

Real-time risk monitoring with hard limits to protect capital.

**Portfolio Risk Metrics Cards:**

**Net Delta Card:** Your overall directional exposure. Displayed as both delta value and equivalent shares (delta × 100). A delta of +300 means you're long the equivalent of three hundred shares.

**Max Loss Card:** The maximum amount you could lose if all positions went to zero (for long options) or unlimited (for uncovered short options). This is your true risk exposure.

**Margin Used Card:** For accounts with margin, shows how much buying power is currently tied up in positions. Displayed as dollars used and percentage of total margin available.

**Risk Score Card:** A proprietary score from one to one hundred rating your portfolio's overall riskiness. Factors include:
- Concentration (are you over-allocated to a single stock?)
- Leverage (what percentage of capital is at risk?)
- Volatility (are you trading high-volatility instruments?)
- Time decay (how much theta are you short?)

Scores above seventy indicate elevated risk and trigger warning notifications.

**Scenario Analysis Chart:** An interactive chart showing estimated P&L under various market scenarios:
- Major crash (-20%)
- Correction (-10%)
- Minor pullback (-5%)
- Sideways (0%)
- Rally (+5%, +10%, +20%)

Each scenario bar is color-coded to show whether you'd profit or lose under that scenario.

**Stress Test Results:** Shows how your portfolio would perform in historical scenarios:
- Black Monday 1987 (one-day crash)
- Dot-com bubble burst (slow grind lower)
- 2008 Financial Crisis (high volatility collapse)
- COVID-19 crash (rapid drawdown with quick recovery)

This historical context helps you understand your exposure to tail risks.

**Risk Limits Panel:** Configurable risk rules that prevent dangerous trading:
- **Max Position Size:** Maximum capital in any single position
- **Max Portfolio Delta:** Maximum net delta allowed
- **Max Daily Loss:** Circuit breaker that blocks new trades if you lose more than X dollars in one day
- **Max Concentration:** Maximum percentage of portfolio in one underlying

These rules are enforced in real-time. Attempts to place orders that would violate limits are automatically rejected with clear error messages.

### Options Flow Sub-Tab

Market-wide options flow analysis, similar to the Whale Stream but with more analytical tools.

**Flow Metrics Cards:**

**Put/Call Ratio (Volume):** Total put volume divided by call volume today. Above one-point-zero is bearish (more put buying), below one-point-zero is bullish (more call buying).

**Put/Call Ratio (Open Interest):** Same ratio but using total open interest instead of daily volume. This shows longer-term positioning versus today's flow.

**Flow Sentiment Card:** Aggregated sentiment derived from all options trades, weighted by premium and adjusted for buy vs. sell side. Displayed as Bullish, Neutral, or Bearish with a color-coded badge.

**Max Pain Level:** Current max pain strike for the front-month expiration, updated hourly.

**Distance from Max Pain:** How far the stock is from max pain in percentage terms.

**Options Flow Heatmap:** A visual heatmap showing trading activity across strikes and expirations. Hot colors (red/orange) indicate high activity, cool colors (blue/purple) indicate low activity. This reveals where smart money is positioning.

**Unusual Activity Table:** A table of the day's most unusual options trades, flagged by:
- **Volume surge:** Trades at 10x average daily volume
- **Large premium:** Single trades over $100K
- **Unusual expiration:** Heavy activity in far-dated options
- **Smart money indicators:** Trades executed at ask price (aggressive buying) or bid price (aggressive selling)

Each entry shows the symbol, strike, expiration, volume, premium, and why it was flagged as unusual.

### Trade Operations Sub-Tab

Order management and execution interface.

**Active Orders Table:** Shows all pending orders (not yet filled):
- **Order ID:** Unique identifier
- **Symbol:** Option description
- **Action:** BUY or SELL
- **Quantity:** Contracts
- **Order Type:** MARKET, LIMIT, STOP
- **Limit Price:** For limit orders, the maximum buy or minimum sell price
- **Status:** PENDING, PARTIALLY_FILLED, FILLED, CANCELLED
- **Time Placed:** When the order was submitted

**Cancel Order Buttons:** Each row has a cancel button. Clicking it sends a cancellation request to the broker. If the order has already filled, you'll get an error message.

**Cancel All Orders Button:** A prominent red button at the top that cancels every pending order in one click. This is an emergency "kill switch" for when you need to exit all pending trades immediately.

**Refresh Orders Button:** Manually refresh the orders table. The table also auto-refreshes every five seconds.

**Order Entry Testing Panel:** A testing section (primarily for demo and paper trading) with quick buttons to:
- **Submit Test Market Order:** Places a fake order to test order flow
- **Trigger Risk Violation:** Intentionally violates risk rules to see how system responds
- **Simulate IV Spike:** Injects a simulated volatility spike to test P&L calculations

**Alerts Feed:** A scrolling feed of trading alerts:
- Order fills (with fill price and timestamp)
- Risk rule violations
- Margin calls
- API errors
- Circuit breaker activations

Each alert is timestamped and color-coded by severity.

---

## Admin Workspace

The Admin Workspace provides system monitoring, backtesting, research tools, and performance analysis.

### System Status Sub-Tab

Real-time monitoring of dashboard health and performance.

**System Health Metrics Cards:**

**API Status Card:** Shows connection status to Alpaca API. Green badge for "Online," red badge for "Disconnected." Includes average response latency.

**Data Feed Card:** Indicates whether market data is flowing. Shows "Live" during market hours, "Delayed" if using free data, "Offline" after hours.

**Models Loaded Card:** Confirms that AI/ML models have loaded successfully. Shows "3/3 Loaded" when all models (sentiment analyzer, volatility forecaster, strategy recommender) are operational.

**Cache Hit Rate Card:** Performance metric showing what percentage of requests are served from cache versus fetching fresh data. Higher is better (less API load, faster response). Target is above eighty percent.

**System Health Check Panel (Phase 4):** A comprehensive health dashboard with three sections:

**API Status Overview:** Individual status cards for each integrated API:
- **Finnhub:** Social sentiment data
  - Status indicator: 🟢 Operational, 🟡 Degraded (using fallback), 🔴 Circuit Breaker Open, ⚪ Not Configured
  - Circuit breaker state: CLOSED, OPEN, or HALF-OPEN
  - If degraded or open, shows time until next retry
  
- **FinViz:** News scraping
  - Similar status indicators and circuit breaker state
  
- **NewsAPI:** Backup news source
  - Shows "Not Configured" if API key not provided
  
- **StockTwits:** Social media sentiment
  - Status and circuit breaker information

Each API card updates every thirty seconds, reflecting real-time health of data integrations.

**Math Integrity Check:** Shows results of "Golden Vector" tests - mathematical verification that core pricing models (Black-Scholes) are calculating correctly. Displays a badge:
- **Green "PASS" Badge:** All six golden vector tests passed, math is verified correct
- **Red "FAIL" Badge:** One or more tests failed, indicating a critical calculation error

The golden vectors test:
- ATM call and put pricing
- ITM and OTM call pricing
- Put-call parity relationship
- Zero-volatility edge cases

If math integrity fails, the dashboard should not be used for real trading decisions. This is a safety check to catch bugs in pricing calculations.

**Recent System Log:** A monospace text box showing the last ten lines from `reports/logs/system.log`. This provides real-time visibility into:
- API call traces with timing
- Error messages
- Warning flags
- Circuit breaker state changes
- Cache hits/misses

The log auto-refreshes every thirty seconds. If you see repeated errors or warnings, it indicates a system issue requiring attention.

### Backtesting Lab Sub-Tab

Historical strategy testing to validate approaches before risking real capital.

**Backtest Configuration Panel:** Input fields for backtest parameters:

**Start Date Picker:** Select the beginning of your backtest period. The further back you go, the more historical scenarios you test, but data quality may degrade for very old dates.

**End Date Picker:** Select the end date. Typically set to yesterday or last market close.

**Starting Capital Input:** How much virtual money to allocate to the backtest. This affects position sizing and overall returns.

**Symbol Input:** Which underlying to backtest. Can be a single stock or an ETF.

**Strategy Selector:** Dropdown of predefined strategies to test:
- Buy/Hold
- Covered Call Writing
- Cash-Secured Puts
- Iron Condor
- Straddle/Strangle
- Custom (define your own rules)

**Position Sizing Rule:** How much capital to allocate per trade:
- Fixed dollar amount
- Fixed percentage of portfolio
- Kelly Criterion (optimal sizing based on edge)

**DTE Range:** Only enter positions with X days until expiration. E.g., "30-45 DTE" means only trade options expiring in 30-45 days.

**Exit Rules:**
- **Profit Target:** Close position when profit reaches X percent (e.g., fifty percent of max profit)
- **Stop Loss:** Close position when loss reaches X percent (e.g., two hundred percent of credit received)
- **Time Stop:** Close position when X days remaining until expiration (e.g., close at seven DTE)

**Run Backtest Button:** Initiates the backtest with your specified parameters. A progress bar appears showing percentage completion.

**Cancel Backtest Button:** Stops a running backtest if it's taking too long or you want to adjust parameters.

**Backtest Results Panel:** After completion, displays comprehensive statistics:

**Summary Metrics:**
- **Total Return:** Overall percentage gain/loss
- **CAGR:** Compound annual growth rate (annualized return)
- **Sharpe Ratio:** Risk-adjusted return (higher is better, above one-point-five is good)
- **Max Drawdown:** Largest peak-to-trough decline (how much you could have lost)
- **Win Rate:** Percentage of trades that were profitable
- **Profit Factor:** Gross profits divided by gross losses (above two-point-zero is good)
- **Average Win/Loss:** Expected value per trade

**Equity Curve Chart:** A line chart showing your account value over time throughout the backtest period. This reveals:
- Consistency of returns (smooth curve is good)
- Drawdown periods (where the curve drops)
- Recovery speed (how quickly the curve recovers after drawdowns)

**Monthly Returns Heatmap:** A color-coded table showing returns for each month in the backtest period. Green for positive months, red for negative. This helps identify seasonal patterns or problematic periods.

**Trade Log Table:** A detailed list of every trade executed during the backtest:
- Entry date and price
- Exit date and price
- Profit/loss
- Holding period
- Market conditions at entry

This log is downloadable as CSV for further analysis in Excel or Python.

**Strategy Comparison:** If you've run multiple backtests, a comparison table shows all strategies side-by-side, making it easy to see which performed best under various metrics.

### Research Lab Sub-Tab

Advanced analytics and custom studies for quantitative traders.

**Correlation Matrix:** A heatmap showing correlations between different symbols in your watchlist. Values range from negative one (perfectly inversely correlated) to positive one (perfectly correlated). This helps with:
- Portfolio diversification (find uncorrelated assets)
- Pairs trading opportunities (find correlated pairs that diverge temporarily)
- Risk management (avoid concentrating in highly correlated positions)

**Volatility Studies:**
- **Historical Volatility Calculator:** Enter a symbol and date range to calculate realized volatility over that period
- **IV vs. HV Comparison:** Chart overlaying implied volatility (what options are pricing in) versus historical volatility (what actually happened). Large divergences suggest potential mispricings.
- **Volatility Percentile Ranking:** Where current volatility sits relative to one-year, two-year, and five-year history

**Options Greeks Simulator:** An interactive tool that lets you adjust various inputs and see real-time impact on option prices and Greeks:
- Adjust stock price with a slider
- Adjust implied volatility
- Fast-forward time to see theta decay
- Change interest rates
- Modify dividends

This educational tool helps build intuition about how options respond to different factors.

**Black-Scholes Calculator:** A standalone calculator for pricing European options:
- Input: Stock price, strike, time to expiration, risk-free rate, volatility, dividend yield
- Output: Theoretical option price, delta, gamma, theta, vega, rho
- Shows how your broker's prices compare to theoretical fair value

**Custom Screener:** Build custom filters to scan the market for opportunities:
- Filter by market cap, sector, volume
- Options criteria: IV rank, volume, open interest
- Price action: Moving average crosses, RSI, MACD
- Options flow: Unusual volume, large premium trades

Results are displayed in a sortable table with the ability to export to CSV.

**Economic Calendar:** A calendar view showing upcoming events that may impact volatility:
- Earnings announcements
- Federal Reserve meetings
- GDP/employment reports
- Dividend ex-dates

This helps plan trades around known volatility catalysts.

### Performance Attribution Sub-Tab

Detailed analysis of your trading performance to identify strengths and weaknesses.

**Portfolio Selection:** Dropdown to select which portfolio or time period to analyze.

**Date Range Picker:** Specify the analysis period (last month, last quarter, year-to-date, custom range).

**Performance Overview Section:**

**Total Return Card:** Your absolute return percentage and alpha (return above benchmark).

**Excess Return Card:** Return above S&P 500 or another chosen benchmark.

**Sharpe Ratio Card:** Risk-adjusted return metric.

**Information Ratio Card:** Consistency of excess returns.

**Cumulative Return Chart:** Line chart comparing your portfolio performance to the benchmark over time. This quickly shows whether you're adding value or underperforming.

**Monthly Returns Chart:** Bar chart of monthly returns, making it easy to spot your best and worst months.

**Performance Attribution Analysis:**

**Strategy Attribution Table:** Breaks down your returns by strategy type:
- How much return came from Bull Call Spreads?
- How much from Iron Condors?
- How much from single options?

This reveals which strategies work best for you and which need improvement.

**Symbol Attribution Table:** Returns broken down by underlying symbol. Shows if you have particular expertise in certain stocks or sectors.

**Time Attribution Table:** Returns by time period (morning vs. afternoon, Monday vs. Friday, first-half month vs. second-half). This can reveal if you have better timing during certain periods.

**Factor Attribution:** Statistical decomposition showing how much of your return came from:
- **Market beta:** Overall market direction (you were long during a bull market)
- **Volatility exposure:** Benefiting from volatility changes
- **Theta capture:** Collecting time decay premium
- **Alpha:** True skill-based returns that can't be explained by systematic factors

**Risk Metrics:**
- **Tracking Error:** How much your returns deviate from benchmark
- **Downside Deviation:** Volatility of negative returns (you want this low)
- **Value at Risk (VaR):** Maximum expected loss at ninety-five percent confidence
- **Conditional VaR (CVaR):** Average loss in worst five percent of outcomes

**Trade Quality Metrics:**
- **Average Win vs. Average Loss:** Are your wins bigger than your losses?
- **Profit Factor:** Gross profit divided by gross loss
- **Expectancy:** Expected value per dollar risked
- **Kelly Percentage:** Optimal position sizing based on your historical win rate and payoff ratio

**Areas for Improvement:** The system automatically highlights areas where your performance could be enhanced:
- "You're cutting winners too early - consider wider profit targets"
- "Losses are growing too large - tighten stop losses"
- "You're overtrading after losses - implement cool-down period"
- "Win rate is good but average wins are small - let winners run longer"

These insights are derived from statistical analysis of your trading history.

---

## Phase-by-Phase Feature Breakdown

The dashboard was built across four major development phases, each adding critical capabilities.

### Phase 1: Hype Gauges and News Engine

**Mission:** Build a hybrid sentiment engine to identify retail enthusiasm and news-driven volatility.

**Features Delivered:**
- Retail sentiment gauges for four watchlist symbols (NVDA, TSLA, SPY, GLD)
- Live news feed from FinViz with fallback to NewsAPI
- NLP-based sentiment classification using VADER and TextBlob
- Pattern detection system for technical analysis
- Scanner workspace as the primary trading cockpit

**Impact:** Traders can now see real-time sentiment alongside price action, helping identify when crowd psychology is reaching extremes that often precede reversals.

### Phase 2: AI Sentiment and Local Forecast

**Mission:** Add machine learning forecasting and intelligent strategy recommendations.

**Features Delivered:**
- Enhanced sentiment analyzer with multi-source aggregation
- Local volatility forecasting models predicting near-term IV changes
- AI-powered strategy recommender based on market conditions and risk tolerance
- Greeks rollup showing portfolio-wide risk exposures
- ML-based options strike recommendations

**Impact:** Traders get data-driven strategy suggestions rather than relying solely on intuition. The volatility forecasts help time entries and exits in premium-selling strategies.

### Phase 3: TradingView Charts and Whale Stream

**Mission:** Upgrade to professional-grade visualization and add large money flow tracking.

**Features Delivered:**
- TradingView Lightweight Charts integration for 60fps performance
- Whale Stream showing options trades with $50K+ premiums
- Pattern feed with real-time technical analysis
- Consolidated four-workspace architecture
- Enhanced UI with badge systems and phase indicators

**Impact:** Chart performance improved dramatically, making intraday analysis much smoother. Whale Stream reveals institutional positioning that retail traders normally can't see.

### Phase 4: Reliability and Self-Healing

**Mission:** Make the system production-ready with enterprise-grade reliability.

**Features Delivered:**
- Comprehensive system logging to `reports/logs/system.log`
- Golden Vector math tests to verify pricing calculations
- Circuit breakers that automatically stop calling failed APIs
- Fallback chains (FinViz → NewsAPI → Mock data)
- System health check panel in Admin tab showing API status and math integrity

**Circuit Breaker Logic:**
- If an API times out three times within one minute, circuit opens
- Circuit stays open for five minutes (no calls to that API)
- During open period, system uses mock data with "degraded" warning
- After five minutes, circuit transitions to half-open (try one request)
- If that request succeeds, circuit closes fully
- If it fails, circuit re-opens for another five minutes

**Fallback Chain Example (News):**
1. Try FinViz (primary source, free, reliable)
2. If FinViz fails, try NewsAPI (secondary source, requires key)
3. If NewsAPI fails, generate mock news with clear "MOCK" labels
4. Never show an empty/broken news feed

**Golden Vector Tests:**
The system tests six mathematical scenarios on startup:
1. ATM call pricing (Black-Scholes)
2. ATM put pricing
3. ITM call pricing
4. OTM call pricing
5. Put-call parity verification
6. Zero-volatility edge case

If any test fails, the dashboard displays a red "FAIL" badge and should not be used for live trading until the issue is fixed.

**Impact:** The dashboard now gracefully handles API failures, network issues, and data provider problems without crashing or showing broken interfaces. Traders can trust the system even during volatile market periods when APIs may be stressed.

---

## Data Sources and APIs

### Alpaca Markets API

**Purpose:** Order execution, account data, and paper trading sandbox.

**Endpoints Used:**
- `/v2/account`: Fetch account balance, buying power, margin
- `/v2/positions`: Get all open positions
- `/v2/orders`: Submit, cancel, and query orders
- `/v2/portfolio/history`: Historical account value

**Rate Limits:** 200 requests per minute.

**Authentication:** API key and secret in environment variables `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`.

**Paper vs. Live:** Toggle changes the base URL between paper-api and api (production). Paper trading is strongly recommended for strategy testing.

### Yahoo Finance (yfinance)

**Purpose:** Free options chain data, historical prices, and fundamental data.

**Data Fetched:**
- Complete options chains (all strikes, all expirations)
- Historical OHLCV data for candlestick charts
- Current stock prices and basic stats

**Rate Limits:** None officially, but excessive scraping may lead to temporary IP blocks. The dashboard caches data aggressively to minimize requests.

**Reliability:** Generally reliable but data can lag by 15-20 minutes for free tier. Occasionally, options chain data may be incomplete for illiquid symbols.

### Finnhub

**Purpose:** Social sentiment from StockTwits and Reddit aggregation.

**Data Fetched:**
- `/api/v1/stock/social-sentiment`: Aggregated social media scores

**Rate Limits:** 60 requests per minute on free tier.

**Authentication:** API key in environment variable `FINNHUB_API_KEY`.

**Circuit Breaker Protection:** Yes, opens after three failures in one minute.

### FinViz

**Purpose:** Financial news headlines via web scraping.

**Data Fetched:**
- News table from stock quote pages
- Headlines, timestamps, and links

**Rate Limits:** No official API, but scraping too aggressively may result in temporary blocks. Dashboard respects a 3-second minimum between requests.

**Authentication:** None required (public website scraping).

**Circuit Breaker Protection:** Yes, opens after three failures in one minute.

**Fallback:** If scraping fails (HTML structure changed), system falls back to NewsAPI.

### NewsAPI

**Purpose:** Backup news source if FinViz fails.

**Data Fetched:**
- `/v2/everything`: News articles matching ticker symbol

**Rate Limits:** 100 requests per day on free tier.

**Authentication:** API key in environment variable `NEWSAPI_KEY`.

**Circuit Breaker Protection:** Yes.

### Mock Data Generation

When APIs fail or keys are not configured, the dashboard generates realistic mock data:
- **Sentiment:** Random scores between 40-60% (neutral bias) with some outliers
- **News:** Template headlines with symbol injection and random sentiment
- **Options:** Theoretical prices using Black-Scholes with randomized IV
- **Whale Trades:** Simulated large orders with realistic strikes and premiums

All mock data is clearly labeled with "MOCK" badges so users never confuse simulated data with real market information.

---

## Self-Healing and Reliability Features

### Circuit Breakers

Circuit breakers prevent cascading failures when external APIs become unresponsive or unstable.

**States:**
- **CLOSED:** Normal operation, all requests allowed
- **OPEN:** Too many failures, blocking all requests for recovery period
- **HALF-OPEN:** Testing if service has recovered, allow one request

**Thresholds (configurable per API):**
- Failure count: 3 (how many failures to trigger open)
- Time window: 60 seconds (failures counted within this window)
- Recovery timeout: 300 seconds (how long to stay open before trying again)

**Failure Conditions:**
- Network timeout (request takes >5 seconds)
- HTTP error status (401, 429, 500, 503)
- Invalid response format (JSON parse error)
- Rate limit exceeded

**User Notifications:** When a circuit breaker opens, a warning notification appears: "⚠️ Finnhub circuit breaker OPEN - using fallback data for 5 minutes"

### Fallback Chains

Every critical data source has at least one fallback to ensure the UI never breaks.

**News Feed Fallback Chain:**
1. FinViz scraping (primary)
2. NewsAPI (secondary, requires key)
3. Mock news (tertiary, always works)

**Sentiment Data Fallback Chain:**
1. Finnhub social sentiment (primary)
2. VADER analysis of recent news (secondary)
3. Mock neutral sentiment (tertiary)

**Options Data Fallback Chain:**
1. Yahoo Finance (primary)
2. Alpaca options API (secondary, if available)
3. Black-Scholes theoretical prices (tertiary)

**Why This Matters:** During major market events (earnings, FOMC announcements, market crashes), APIs often slow down or fail due to high load. Fallback chains ensure traders still have data to work with, even if it's slightly degraded or theoretical.

### Comprehensive Logging

All API calls, errors, and state changes are logged to `reports/logs/system.log`.

**Log Format:**

**Log Levels:**
- **DEBUG:** Detailed trace of all API calls with timing
- **INFO:** System events (server start, cache hits, circuit breaker state changes)
- **WARNING:** Non-critical issues (API timeouts, data quality problems)
- **ERROR:** Critical failures (authentication errors, calculation failures)

**Log Rotation:** The log file automatically rotates when it reaches 10 MB, keeping the last five files. This prevents disk space issues while maintaining sufficient history.

**Admin Panel Integration:** The last ten log lines are displayed live in the Admin tab's health check panel, allowing real-time monitoring without SSHing into the server.

### Golden Vector Math Verification

Before allowing any trading operations, the system verifies that core pricing models are calculating correctly.

**Test Cases:**
1. **ATM Call:** Black-Scholes(S=100, K=100, T=1, r=0.05, σ=0.2) should equal $10.4506
2. **ATM Put:** Same parameters for put should equal $5.5735
3. **ITM Call:** Black-Scholes(S=110, K=100, T=1, r=0.05, σ=0.2) should equal $17.6630
4. **OTM Call:** Black-Scholes(S=90, K=100, T=1, r=0.05, σ=0.2) should equal $5.0912
5. **Put-Call Parity:** C - P should equal S - K*e^(-rT) within tolerance
6. **Zero Volatility:** Options with σ=0 should behave like forward contracts

**Tolerance:** Each test allows 0.0001 difference (0.01 cent) to account for floating-point precision.

**Failure Action:** If any test fails, the dashboard:
- Displays red "FAIL" badge in Admin health check panel
- Logs detailed error showing which test failed and by how much
- Optionally blocks startup (configurable)

**Why This Matters:** A bug in pricing calculations could cause catastrophically bad trades (paying 10x fair value for an option, for example). Golden vectors catch these bugs before they reach production.

### Data Quality Warnings

The dashboard actively monitors data quality and warns when issues are detected:

**Chart Data Warnings:**
- "⚠️ Insufficient chart data" - Less than 2 valid candles available
- "⚠️ Chart data unavailable" - No data for selected symbol/period
- Candles with NaN values are skipped and logged

**Options Chain Warnings:**
- "⚠️ Stale data (>15 minutes old)" - Options chain hasn't updated recently
- "⚠️ Illiquid options" - Bid/ask spread exceeds 20% of mid price
- "⚠️ Missing strikes" - Expected strikes not in returned data

**Sentiment Warnings:**
- "⚠️ Using mock sentiment" - No API keys configured
- "⚠️ Sentiment data degraded" - Circuit breaker is open, using fallbacks

These warnings ensure traders never unknowingly make decisions based on bad data.

---

## Keyboard Shortcuts

Power users can navigate the entire dashboard without touching the mouse.

### Global Shortcuts (Work from any tab)

**⌘K (Mac) / Ctrl+K (Windows/Linux):** Open command palette. Type to search for features, symbols, or actions.

**Shift+R:** Refresh all data. Forces new API calls and cache invalidation.

**Shift+B:** Open quick buy ticket. Modal appears with symbol input and strategy selector.

**Shift+C:** Cancel all pending orders. Shows confirmation dialog with count of orders to be cancelled.

**Esc:** Close any open modal or dialog.

**Tab / Shift+Tab:** Navigate forward/backward through form fields and buttons.

### Scanner Workspace Shortcuts

**1/2/3/4:** Jump to Hype Gauge symbol (1=NVDA, 2=TSLA, 3=SPY, 4=GLD) and update chart.

**N:** Focus news filter dropdown.

**C:** Focus chart timeframe selector.

**F:** Toggle news sentiment filter (cycle through All/Positive/Negative/Neutral).

### Strategy Workspace Shortcuts

**Ctrl+N:** Add new leg to strategy builder.

**Ctrl+Backspace:** Remove last leg from strategy.

**Ctrl+Enter:** Execute current strategy (if valid).

**Ctrl+Shift+C:** Clear all legs and reset builder.

**I:** Toggle IV surface view mode (3D vs. 2D heatmap).

### Command Workspace Shortcuts

**P:** Jump to Positions tab.

**O:** Jump to Orders tab.

**R:** Jump to Risk Dashboard.

**Delete:** Close selected position (requires confirmation).

### Admin Workspace Shortcuts

**B:** Jump to Backtesting Lab.

**H:** Jump to System Health panel.

**L:** Download system log file.

**Ctrl+Shift+T:** Run Golden Vector tests manually.

### Pro Tips

**Command Palette Power User Tricks:**
- Type symbol directly (e.g., "AAPL") to load that options chain
- Type command names (e.g., "backtest", "risk", "flow")
- Type strategy names (e.g., "iron condor", "straddle")
- Recent commands appear at the top for quick access

**Hotkeys Helper:** Click the "⌨️ Hotkeys" button in the bottom-right corner to see a cheat sheet of all shortcuts. This panel can be pinned open while learning the system.

---

## Best Practices and Tips

### For Active Traders

**Morning Routine:**
1. Open Admin tab, check System Health panel - verify all APIs are operational
2. Review overnight news and whale trades in Scanner tab
3. Check positions and adjust stop losses in Command tab
4. Update watchlist based on morning volatility patterns

**During Trading Hours:**
1. Keep Scanner tab open for real-time flow and sentiment
2. Set alerts for unusual whale activity in your positions
3. Monitor portfolio Greeks in Command/Risk tab every 30 minutes
4. Check risk score after each trade entry

**End of Day:**
1. Review P&L and attribution in Admin/Performance tab
2. Analyze what worked and what didn't
3. Update trading journal with lessons learned
4. Set alerts for overnight earnings or events

### For Strategy Development

**Backtesting Workflow:**
1. Start with simple strategy on liquid underlyings (SPY, QQQ)
2. Run 2+ years of backtests to capture different market regimes
3. Check performance in both trending and choppy markets
4. Ensure Sharpe ratio >1.0 and max drawdown <20% before paper trading
5. Paper trade for 30 days minimum before going live

**Parameter Optimization:**
- Never over-optimize on historical data (curve fitting)
- Use walk-forward testing (optimize on Period 1, test on Period 2)
- Add transaction costs and slippage to backtests (0.5% of premium minimum)
- Test how strategy performs in worst historical scenarios (2008, 2020)

### For Risk Management

**Position Sizing Rules:**
- Never risk more than 2% of account on a single trade
- Limit any one underlying to 20% of portfolio
- Keep portfolio delta between -100 and +100 for $100K accounts (adjust proportionally)
- Maintain at least 50% cash for opportunities and margin buffer

**Stop Loss Discipline:**
- Set stops at strategy entry, not after losses appear
- Typical stops: 2x credit received for credit spreads, 50% of debit for debit spreads
- Don't move stops to "give it more room" - take the loss and move on
- Use time stops (close at 7 DTE) in addition to price stops

**Avoid Common Pitfalls:**
- Don't over-allocate to earnings plays (IV crush risk)
- Don't sell naked options without sufficient margin buffer
- Don't revenge trade after losses (take a break instead)
- Don't ignore risk warnings - the system is trying to protect you

### System Maintenance

**Daily Tasks:**
- Check system log for errors each morning
- Verify API key expirations (Alpaca keys expire after 90 days)
- Monitor cache hit rate (should be >80%)

**Weekly Tasks:**
- Review circuit breaker activations - investigate if any API is frequently failing
- Archive old logs if disk space is limited
- Update watchlist symbols based on current market focus

**Monthly Tasks:**
- Review performance attribution to ensure strategies are working
- Run Golden Vector tests manually to verify math integrity
- Check for dashboard updates or bug fixes
- Backup trading journal and strategy notes

---

**End of Guide**

This comprehensive documentation covers every feature, button, tab, and component of the Alpaca Options Lab dashboard. For technical implementation details, see the codebase documentation. For API integration guides, see the respective provider documentation.

**Version:** 4.0.0  
**Last Updated:** January 2, 2026  
**Status:** ✅ Production Ready

