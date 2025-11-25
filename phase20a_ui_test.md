# Phase 20A UI Test Instructions

## ✅ Completed Steps

1. **Database Schema Initialized** ✅
   - 4 tables created: `ml_prediction_runs`, `ml_predictions`, `ml_model_metrics`, `ml_insights`
   - Current data: 1 test run from validation harness

2. **Callbacks Wired Up** ✅
   - Line 238: Now calls `call_azure_ml_endpoint()` instead of `generate_mock_predictions()`
   - Error handling: Returns alert if predictions fail
   - Database persistence: Calls `save_prediction_run()` on success
   - File copied to container and dash_app restarted

## 🧪 Manual UI Test Steps

### Test 1: Run Prediction Button
1. Open browser to dashboard (usually http://localhost:8050)
2. Navigate to **Azure ML Lab** tab
3. Click **"Run Prediction"** button
4. **Expected outcome:**
   - Predictions table appears with tickers and confidence scores
   - Success message shows number of predictions
   - Check console logs for "✅ Saved prediction run to database (run_id: X)"

### Test 2: Verify Database Persistence
After clicking Run Prediction, run this command:
```bash
docker exec dash_app python3 -c "
import psycopg2
conn = psycopg2.connect('postgresql://postgres:postgres@postgres_db:5432/market_data')
cur = conn.cursor()
cur.execute('SELECT run_id, model_type, horizon_days, num_predictions, source, created_at FROM ml_prediction_runs ORDER BY created_at DESC LIMIT 3;')
rows = cur.fetchall()
print(f'📊 Recent prediction runs:')
for row in rows:
    print(f'  • run_id={row[0]}, model={row[1]}, horizon={row[2]}d, count={row[3]}, source={row[4]}, created={row[5]}')
conn.close()
"
```

**Expected:** You should see a NEW row with source='azure_ml' (not 'phase20a_validation')

### Test 3: Check Observability Metrics
Check the dash_app logs for metrics emission:
```bash
docker logs dash_app --tail 50 | grep -E "(ml\.|✅|📡|🚀)"
```

**Expected output:**
- `🚀 PHASE 20A: Running prediction with REAL Azure ML endpoint...`
- `📡 Calling Azure ML endpoint...`
- `✅ Saved prediction run to database (run_id: X)`
- Metrics emissions like `ml.endpoint.call.count`, `ml.endpoint.latency.ms`

## 🔍 Troubleshooting

### If predictions fail:
- Check if Azure ML endpoint is reachable (should gracefully fallback to mock)
- Check environment variable: `AZURE_ML_USE_MOCK=true` (means fallback active)
- Look for error message in red alert box

### If database save fails:
- Check PostgreSQL connection: `docker exec dash_app env | grep POSTGRES`
- Verify tables exist: Run verification command in Test 2
- Check logs for "⚠️ Failed to save to database"

### If no observability metrics:
- Check if `ml_observability.py` imported correctly
- Verify `ML_OBSERVABILITY_AVAILABLE=True` in logs
- Check Sentry/Datadog configuration

## 📈 Success Criteria

- ✅ Run Prediction button works without errors
- ✅ Predictions appear in UI table
- ✅ Database has new row in ml_prediction_runs with source='azure_ml'
- ✅ Logs show "✅ Saved prediction run to database"
- ✅ Observability metrics emitted (at least ml.endpoint.call.count)
- ✅ Graceful fallback works if Azure ML unavailable

## 🚀 Next Steps After UI Test

If all tests pass:
1. **Wire up update_predictions_table callback** - Read from PostgreSQL instead of JSON cache
2. **Test Insights button** - Verify ml_insights table persistence
3. **Test Metrics button** - Verify ml_model_metrics table persistence
4. **Full E2E validation** - Run complete workflow and verify all observability
