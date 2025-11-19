# Phase 4 - Hybrid Readiness Diagnostic Report
**Generated:** 2025-10-29T03:34:37.320349
**Agent:** Agent 1B - Lead Engineer

---

## Summary
- **Total Tests:** 7
- **Passed:** 6 ✅
- **Failed:** 1 ❌
- **Duration:** 2382ms

## Test Results

| Test | Status | Duration (ms) | Details |
|------|--------|---------------|----------|
| Contract Definitions | ✅ PASS | 119 | input_fields=11, output_fields=11 |
| I/O Schemas | ❌ FAIL | 6 |  |
| Stub Clients | ✅ PASS | 674 | ml_predictions_generated=30, blob_operations_tested=3 |
| Hybrid Interface | ✅ PASS | 460 | offline_mode=True, workspace_config_keys=['subscription_id', 'resource_group', 'workspace_name', 'blob_container'] |
| Compute Router | ✅ PASS | 582 | dispatched_tasks=1, cached_items=1 |
| Telemetry Proxy | ✅ PASS | 16 | events_tracked=3, events_read=8 |
| End-to-End Integration | ✅ PASS | 523 | workflow_steps_completed=3, predictions_generated=30 |

## Detailed Test Results

### Contract Definitions
**Status:** ✅ PASS
**Duration:** 119ms

**Details:**
- input_fields: 11
- output_fields: 11
- model_types_tested: 2
- horizons_tested: 2

### I/O Schemas
**Status:** ❌ FAIL
**Duration:** 6ms

**Error:** Payload validation failed: ["Missing required field: 'job_uuid'", "Field 'date_range' expected type 'array', got 'tuple'"]

### Stub Clients
**Status:** ✅ PASS
**Duration:** 674ms

**Details:**
- ml_predictions_generated: 30
- blob_operations_tested: 3
- telemetry_events_tracked: 3
- ml_latency_ms: 336.60740328406575

### Hybrid Interface
**Status:** ✅ PASS
**Duration:** 460ms

**Details:**
- offline_mode: True
- workspace_config_keys: ['subscription_id', 'resource_group', 'workspace_name', 'blob_container']
- analytics_predictions: 30
- analytics_latency_ms: 275.8240252570543

### Compute Router
**Status:** ✅ PASS
**Duration:** 582ms

**Details:**
- dispatched_tasks: 1
- cached_items: 1
- avg_latency_ms: 582.0236850013316
- cache_hit_verified: True

### Telemetry Proxy
**Status:** ✅ PASS
**Duration:** 16ms

**Details:**
- events_tracked: 3
- events_read: 8
- total_telemetry_events: 8
- event_types: ['customEvent', 'metric', 'request', 'unknown']

### End-to-End Integration
**Status:** ✅ PASS
**Duration:** 523ms

**Details:**
- workflow_steps_completed: 3
- predictions_generated: 30
- telemetry_events_total: 10
- end_to_end_latency_ms: 510.8021439991717
