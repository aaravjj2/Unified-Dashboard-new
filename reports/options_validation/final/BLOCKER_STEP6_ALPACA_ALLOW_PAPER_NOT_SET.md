# BLOCKER: STEP 6 - ALPACA_ALLOW_PAPER Environment Variable Not Set

**Status:** BLOCKED  
**Severity:** CRITICAL  
**Timestamp:** 2025-01-20T21:24:00Z

---

## Summary

Paper order testing cannot proceed because required environment variable `ALPACA_ALLOW_PAPER` is not set. Per super-prompt strict policy:

> STEP 6: Paper orders handling (ALPACA) - strict policy with BLOCKER if env not set

---

## Environment Check

```bash
$ env | grep -i alpaca
NO ALPACA ENV VARS SET
```

**Required Variables:**
- `ALPACA_ALLOW_PAPER=true` (MISSING)
- `ALPACA_API_KEY` (not checked - first blocker takes precedence)
- `ALPACA_API_SECRET` (not checked - first blocker takes precedence)

---

## Impact

**Cannot Test:**
- Paper order placement via Alpaca API
- Order fill polling
- Order persistence to database
- Paper order audit trail

**Blocked Operations:**
- POST /api/options/admin/orders/place (paper order submission)
- GET /api/options/admin/orders/audit (order history retrieval)
- Order fill status verification

---

## Remediation Steps

**To Enable Paper Trading:**

1. **Set environment variable:**
   ```bash
   export ALPACA_ALLOW_PAPER=true
   ```

2. **Set Alpaca credentials (if not already set):**
   ```bash
   export ALPACA_API_KEY="your_paper_api_key"
   export ALPACA_API_SECRET="your_paper_api_secret"
   ```

3. **Verify credentials with Account GET:**
   ```bash
   curl -X GET "https://paper-api.alpaca.markets/v2/account" \
     -H "APCA-API-KEY-ID: $ALPACA_API_KEY" \
     -H "APCA-API-SECRET-KEY: $ALPACA_API_SECRET"
   ```

4. **Restart dashboard:**
   ```bash
   python financial_dashboard/app.py
   ```

5. **Re-run STEP 6 validation**

---

## Alternative: Skip Paper Trading

If paper trading is not required for this validation cycle:

**Option A:** Document BLOCKER and skip STEP 6  
**Option B:** Test with mock orders (if mock endpoint exists)  
**Option C:** Manual verification via Alpaca web dashboard

**Recommendation:** Set environment variables per remediation steps above.

---

## Super-Prompt Compliance

Per super-prompt STEP 6 requirements:
> "ALPACA disabled: block and log all attempts"
> "No live trading: paper orders only with explicit env var"
> "STEP 6: Paper orders (ALPACA) - strict policy with BLOCKER if env not set"

**Status:** ✅ BLOCKER created as required  
**Next:** Proceed to STEP 7 - Smoke test other tabs

---

