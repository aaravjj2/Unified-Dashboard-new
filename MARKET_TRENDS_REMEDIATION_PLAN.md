# Market Trends Data Unavailable - Root Cause & Fix Plan

## 🔍 **Root Causes Identified**

### 1. **Missing Price Fields in Cache** ❌
**Issue**: Cache has prices but missing `week_start_price`, `month_start_price`, `daily_change`, `profit_loss`

**Evidence from logs**:
```
WARNING - AAPL: missing week_start_price, month_start_price
WARNING - TSLA: missing week_start_price, month_start_price
```

**Why**: 
- Tab activation callback (line 1182-1183) adds these fields temporarily
- But they're NOT saved to the persisted cache file
- When page reloads, only basic prices exist in cache

### 2. **Cache Not Persisting After Analysis** ❌
**Issue**: After "Run Full Analysis", results are stored in memory but not written to disk

**Code Location**: `market_trends.py` line 1765
```python
SH.RESULTS_CACHE['results'] = sanitized  # Memory only!
SH.RESULTS_CACHE['loaded_at'] = time.time()
```

**Missing**: No call to save cache to JSON file on disk

### 3. **Docker Command Error in Debug Logs** ❌
**Issue**: Debug logs show "Docker command not found"

**Likely Cause**: Code trying to run `docker` command from within Docker container

### 4. **Old "Recent Critical Events" Placeholders** ❌
**Issue**: Events showing old/placeholder data

**Location**: `market_trends.py` line 881 - `create_events_panel()`

---

## 🔧 **Fix Implementation**

### Fix 1: **Enrich Cache with All Price Fields**

**File**: `financial_dashboard/tabs/market_trends.py`
**Lines**: Around 1765 (where results are saved)

**Add**:
```python
# After job completes, enrich with price fields
for row in detailed_data:
    ticker = row.get('Ticker') or row.get('ticker')
    if ticker and ticker in cache_prices:
        # Ensure all price fields are present
        price_entry = cache_prices[ticker]
        row['current_price'] = price_entry.get('current_price')
        row['week_start_price'] = price_entry.get('week_start_price')
        row['month_start_price'] = price_entry.get('month_start_price')
        row['daily_change'] = price_entry.get('daily_change')
        row['profit_loss'] = price_entry.get('profit_loss')
        row['data_source'] = price_entry.get('source', 'cached')
```

### Fix 2: **Persist Cache to Disk After Analysis**

**File**: `financial_dashboard/tabs/market_trends.py`
**Location**: After line 1767

**Add**:
```python
# CRITICAL: Persist to disk so reload shows fresh data
try:
    import json
    cache_file = os.path.join(SH.OUT_ROOT, 'market_trends_cache.json')
    with open(cache_file, 'w') as f:
        json.dump(sanitized, f, indent=2, default=str)
    logger.info(f"✅ Persisted cache to {cache_file}")
except Exception as e:
    logger.error(f"❌ Failed to persist cache: {e}")
```

### Fix 3: **Remove Docker Command from Debug Logs**

**File**: Find where debug logs try to run `docker` command
**Action**: Remove or guard with `if not running_in_docker()`

### Fix 4: **Fix Recent Critical Events**

**File**: `financial_dashboard/tabs/market_trends.py`
**Function**: `create_events_panel()`

**Action**: 
- Remove placeholder events
- Fetch real events from database/API
- Or hide panel if no real data

---

## 📋 **Execution Order**

1. ✅ Fix price field enrichment
2. ✅ Add cache persistence after analysis
3. ✅ Load enriched cache on page load
4. ✅ Remove Docker command from debug
5. ✅ Fix Recent Critical Events

---

## ✅ **Success Criteria**

- [ ] After "Run Full Analysis", all price columns show values (no "Data Unavailable")
- [ ] After page reload (F5), price data persists (loaded from cache file)
- [ ] Debug logs show no "Docker command not found" error
- [ ] Recent Critical Events show real data or are hidden

