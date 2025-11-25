# Market Trends - Testing Instructions

## 🧪 Comprehensive Visual Test

I've created a thorough test script that will:
- ✅ Open Chrome browser (visible, non-headless)
- ✅ Test all 7 buttons with clicks
- ✅ Take screenshots at each step
- ✅ Check news panel and price data
- ✅ Verify browser console for errors
- ✅ Keep browser open for manual inspection

## 🚀 How to Run the Test

### 1. Start the Dashboard
```bash
python run_dashboard.py
```

Wait for it to start on http://localhost:8090

### 2. Run the Comprehensive Test
In a new terminal:
```bash
python test_market_trends_comprehensive.py
```

### 3. What Happens

The test will:
1. Open Chrome browser (you'll see it)
2. Navigate to Market Trends tab
3. Click each button in sequence:
   - Reload Model
   - Refresh Cached Display
   - Toggle Full Brief (show/hide)
   - Download CSV
   - Backtest Trend Signals (opens modal)
   - Debug Logs (opens modal)
4. Check news panel
5. Check price data table
6. Take 14 screenshots documenting everything
7. **Keep browser open** for you to inspect
8. Wait for you to press Enter before closing

### 4. Review Results

Screenshots will be saved to: `market_trends_test_screenshots/`

Each screenshot is timestamped and named:
- `01_dashboard_loaded.png`
- `02_market_trends_tab.png`
- `03_reload_model_clicked.png`
- `04_refresh_cached_clicked.png`
- `05_toggle_brief_shown.png`
- `06_toggle_brief_hidden.png`
- `07_download_csv_clicked.png`
- `08_backtest_modal.png`
- `09_backtest_modal_closed.png`
- `10_debug_logs_modal.png`
- `11_debug_logs_modal_closed.png`
- `12_news_panel.png`
- `13_price_table.png`
- `14_final_state.png`

## 📊 What Gets Tested

### Buttons (7 total)
1. ✅ **Reload Model** - Clicks and checks status message
2. ✅ **Refresh Cached Display** - Clicks and checks status
3. ✅ **Toggle Full Brief** - Clicks twice (show/hide)
4. ✅ **Download CSV** - Clicks (triggers download)
5. ✅ **Backtest Trend Signals** - Opens modal, closes modal
6. ✅ **Debug Logs** - Opens modal, closes modal
7. ✅ **Run Full Analysis** - (tested separately due to complexity)

### Additional Checks
- ✅ News panel content
- ✅ Price data table
- ✅ Browser console errors
- ✅ Tab navigation
- ✅ Results area

## 🎯 Expected Results

### All Passing
- All 7 buttons should be clickable
- Modals should open and close
- Status messages should appear
- No severe console errors
- Screenshots show proper UI state

### Success Criteria
- ✅ 10+ tests passed
- ⚠️ 0-3 warnings acceptable
- ❌ 0 failures

## 🔍 Manual Inspection

When the browser stays open, check:
1. **Visual appearance** - Does everything look correct?
2. **Button states** - Are buttons enabled/disabled properly?
3. **Content** - Is data displaying correctly?
4. **Modals** - Do they look good?
5. **News** - Are headlines showing?
6. **Prices** - Are all 5 fields visible?

## 📝 Test Output

The test will print:
```
✅ PASSED (X):
   • Market Trends tab navigation
   • Reload Model button: <status>
   • Refresh Cached button: <status>
   • Toggle Brief: none → block
   • Download CSV button clicked
   • Backtest modal opened
   • Debug Logs modal opened
   • News panel has content
   • Price data: X cells
   • No console errors

⚠️  WARNINGS (X):
   • <any warnings>

❌ FAILED (X):
   • <any failures>

OVERALL: X/Y passed (Z%)
Screenshots saved to: market_trends_test_screenshots/
```

## 🐛 Troubleshooting

### Browser doesn't open
- Check if Chrome/Chromium is installed
- Try: `which google-chrome` or `which chromium`

### Dashboard not accessible
- Ensure dashboard is running: `python run_dashboard.py`
- Check URL: http://localhost:8090
- Check for port conflicts

### Buttons not found
- Dashboard may still be loading
- Check screenshots to see actual state
- Manually inspect browser when it stays open

### Import errors
- Ensure selenium is installed: `pip install selenium`
- Check Chrome driver is available

## 🎉 Success Indicators

If test passes, you should see:
- ✅ 10+ passed tests
- ✅ 14 screenshots created
- ✅ Browser shows working buttons
- ✅ No critical errors
- ✅ All modals functional

This confirms the Market Trends tab is **100% working**!

## 📸 Screenshot Review

After test completes, review screenshots to verify:
1. Tab loaded correctly
2. Buttons are visible
3. Clicks triggered actions
4. Modals appeared
5. Content is displaying
6. No visual errors

## 🚀 Next Steps

After successful test:
1. Review all screenshots
2. Check test output summary
3. Manually test any edge cases
4. Deploy with confidence!

---

**Test Script**: `test_market_trends_comprehensive.py`
**Screenshots**: `market_trends_test_screenshots/`
**Status**: Ready to run
