# Dashboard Testing Instructions

## Current Status
✅ Dashboard is running on **http://localhost:8051**  
✅ Using `.venv_wsl2` environment  
✅ Tab label fix applied (`fix_tab_labels.js`)  
✅ Market Forecast adapter implemented  

## Testing Checklist

### 1. Dashboard Load Verification
- [ ] Navigate to http://localhost:8051 in your browser
- [ ] Verify "Financial Dashboard" title appears
- [ ] Wait 3-5 seconds for JavaScript to load
- [ ] Check that tab labels show proper names (not "Tab 1", "Tab 2")
- [ ] Expected tabs:
  - 🎯 Command Center
  - 🔬 Research Lab
  - 📊 Attribution Lab
  - ⚡ Strategy Lab
  - Weekly Picks
  - Monthly Picks
  - Market Trends
  - **Market Forecast** ← Primary test target
  - ⚡ Volatility Lab
  - Portfolio
  - 💹 Options Lab

### 2. Market Forecast Tab Testing

#### Step 1: Navigate to Market Forecast
- [ ] Click on "Market Forecast" tab
- [ ] Verify the tab content loads (inputs panel should appear)
- [ ] Check for these elements:
  - Ticker dropdown (should show AAPL, MSFT, GOOGL, NVDA)
  - Horizon selector (7, 14, 30, 60, 90 days)
  - Confidence level selector
  - Model selector
  - "▶ Run Forecast" button

#### Step 2: Run a Forecast
- [ ] Select ticker: **AAPL** (default)
- [ ] Select horizon: **30 days** (default)
- [ ] Click "▶ Run Forecast" button
- [ ] Wait 5-10 seconds for forecast to complete

#### Step 3: Verify Results
- [ ] Check that forecast chart appears (should replace placeholder)
- [ ] Verify chart shows:
  - Historical price data (blue line)
  - Forecast predictions (orange/red line)
  - Confidence intervals (shaded area)
- [ ] Check forecast table appears below chart
- [ ] Verify table shows:
  - Date column
  - Predicted Price column
  - Lower/Upper Bound columns
- [ ] Check status banner (should show success message)

#### Step 4: Test Different Parameters
- [ ] Try different ticker (e.g., MSFT)
- [ ] Try different horizon (e.g., 60 days)
- [ ] Verify forecast updates correctly

### 3. AI Chatbot Testing

#### Step 1: Open Chatbot
- [ ] Look for chatbot icon (usually bottom-right corner)
- [ ] Click to open chatbot interface
- [ ] Verify chatbot UI appears

#### Step 2: Send Test Messages
- [ ] Send message: "What is the current price of AAPL?"
- [ ] Verify chatbot responds
- [ ] Send message: "Show me market trends"
- [ ] Verify chatbot provides relevant information

#### Step 3: Test RAG Features
- [ ] Ask about specific stocks or strategies
- [ ] Verify chatbot uses context from dashboard data
- [ ] Check response quality and relevance

## Expected Behavior

### Market Forecast
- **Forecast execution time**: 5-10 seconds
- **ML model**: Should load automatically from `models/forecast_model.pkl`
- **Data source**: yfinance (historical data)
- **Prediction**: Should show realistic price predictions with confidence intervals

### Chatbot
- **Response time**: 2-5 seconds
- **Context awareness**: Should reference dashboard data
- **Error handling**: Should gracefully handle unknown queries

## Troubleshooting

### If tabs show "Tab 1", "Tab 2":
- Refresh the page (Ctrl+R)
- Wait 5 seconds for JavaScript fix to apply
- Check browser console for errors (F12)

### If Market Forecast doesn't run:
- Check browser console for errors
- Verify dashboard logs: `tail -f /tmp/dashboard_wsl2.log`
- Look for "Forecast complete" message in logs

### If Chatbot doesn't respond:
- Check if chatbot icon is visible
- Verify API endpoint is accessible
- Check dashboard logs for chatbot errors

## Dashboard Logs
Monitor logs in real-time:
```bash
tail -f /tmp/dashboard_wsl2.log
```

Look for these success indicators:
- `✅ ML Runner initialized for forecast adapter`
- `✅ Forecast complete for [TICKER]`
- `✅ Chatbot callbacks registered successfully`

## Report Issues
If you encounter any issues, please note:
1. Which tab/feature failed
2. Error messages (from browser console or logs)
3. Screenshots if applicable
4. Steps to reproduce
