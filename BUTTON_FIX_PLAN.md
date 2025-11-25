# Market Trends Button Fix Plan

## Current State Analysis

Based on code inspection, here's what exists and what needs fixing:

### Button 1: Run Full Analysis (`run-btn`)
- **Status**: Partially working but complex
- **Issues**: Job scheduling, polling, result rendering
- **Fix**: Simplify job flow, add error handling

### Button 2: Reload Model (`reload-model`)
- **Status**: Exists at line 2064
- **Issues**: May not properly reload from disk cache
- **Fix**: Use CacheManager.load_from_disk()

### Button 3: Refresh Cached Display (`refresh-cached`)
- **Status**: Exists at line 2078
- **Issues**: Uses reload-trigger intermediate store
- **Fix**: Direct cache reload and table re-render

### Button 4: Backtest Trend Signals (`backtest-btn`)
- **Status**: Exists at line 2250
- **Issues**: Complex modal logic, may not execute backtest
- **Fix**: Simplify backtest execution, fix modal display

### Button 5: Debug Logs (`debug-logs-btn`)
- **Status**: Exists at line 2402
- **Issues**: May not read logs correctly
- **Fix**: Ensure log file reading works

### Button 6: Toggle Full Brief (`toggle-brief`)
- **Status**: Exists at line 2089
- **Issues**: May not toggle visibility correctly
- **Fix**: Simple show/hide toggle

### Button 7: Download CSV (`mt-download-btn`)
- **Status**: Exists at line 2038
- **Issues**: May not generate CSV correctly
- **Fix**: Use dcc.Download, proper CSV generation

## Implementation Approach

Since the file is 2519 lines, I'll:
1. Create helper functions for each button
2. Update callbacks to use helpers
3. Add comprehensive error handling
4. Integrate CacheManager and NewsManager
5. Test each button individually

## Critical Fixes Needed

1. **Error Handling**: Wrap all callbacks with try/except
2. **Cache Integration**: Use CacheManager instead of direct file I/O
3. **News Integration**: Use NewsManager for news refresh
4. **Logging**: Add detailed logging for debugging
5. **User Feedback**: Clear status messages for all operations
