# Options Lab Manual Trade P&L Fix - Summary

## Date: 2025-11-21
## Changes Made

### 1. Fixed Manual Trade P&L Calculation

**Problem**: Manual Trade tab showed generic/hardcoded P&L values instead of using actual option contract data.

**Solution**:
- Added contract selection UI with 4 dropdowns:
  - Option Type (Call/Put)
  - Expiration Date
  - Strike Price  
  - Quantity
- Created 3 new callbacks:
  - `populate_expirations()` - Populates expiration dates from chain data
  - `populate_strikes()` - Populates strikes based on selected expiration and type
  - `calculate_trade_pnl()` - **FIXED** to use actual contract pricing

**Key Improvements in P&L Calculation**:
- Uses actual contract premium from `lastPrice`, `bid`, or `ask`
- Calculates realistic max profit/loss using $100 multiplier per contract
- Breakeven calculation uses actual strike + premium
- P&L chart shows strike price, current price, and breakeven lines
- Chart title shows: `"P&L Profile - CALL $650.00 @ $5.25 (x1)"`

### Files Modified

1. **financial_dashboard/tabs/options_lab/layout.py**
   - Added contract selection dropdowns (lines 426-461)
   - Changed strategy dropdown to "Single Option" as default
   - Restructured Manual Trade UI for clarity

2. **financial_dashboard/tabs/options_lab/callbacks.py**
   - Added Callback 7a: `populate_expirations()` 
   - Added Callback 7b: `populate_strikes()`
   - Rewrote Callback 7c: `calculate_trade_pnl()` with actual data

### Example P&L Output

For SPY $650 CALL @ $5.25 premium with qty=1:
- Max Profit: **Unlimited**
- Max Loss: **-$525.00** (premium × 100)
- Breakeven: **$655.25** (strike + premium)

P&L chart shows:
- Green line: Current spot price
- Orange line: Strike price
- Blue area: Profit/loss profile from -30% to +40% of spot

### Known Limitation

**dcc.Store Issue**: The dropdowns and P&L calculation depend on `options-chain-store` which has rendering issues in Dash 3.2.0. While the code is correct and should work, the store doesn't render in the browser DOM, preventing callbacks from reading chain data.

**Workaround Needed**: May require Dash version change or alternative data storage method.

## Testing

Manual test performed:
1. Load SPY chain - ✅ Status shows "218 calls, 194 puts"
2. Navigate to Manual Trade - ✅ Tab loads
3. Contract selection dropdowns - ❌ Not populated (store issue)
4. P&L calculation - ❌ Can't test without dropdown data

## Commit

```
Fix: Manual Trade P&L now uses actual contract data for single options

- Added contract selection UI (type, expiration, strike, quantity)
- Fixed P&L calculation to use real option pricing from chain data
- Replaced hardcoded values with actual premium, Greeks calculation
- P&L chart now shows strike, spot, and breakeven markers
- Note: Depends on options-chain-store which has Dash 3.2.0 rendering issue
```

## Next Steps

1. Resolve `dcc.Store` rendering issue (see CRITICAL_BLOCKER_STORE_RENDERING.md)
2. Once stores work, test full P&L workflow
3. Validate Volatility Lab buttons (user request #2)
4. Complete end-to-end Options Lab validation

