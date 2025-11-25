#!/usr/bin/env python3
"""Quick Phase 4 Validation Test

Tests all major components of the hybrid infrastructure.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 60)
print("Phase 4 Quick Validation Test")
print("=" * 60)

# Test 1: Contract Definitions
print("\n[1/7] Testing Contract Definitions...")
try:
    from phase4_hybrid_stubs.azure_contracts import (
        ContractInputSpec,
        ContractOutputSpec,
        ModelType,
        ForecastHorizon,
        create_mock_input,
        validate_contract
    )
    
    input_spec = create_mock_input('AAPL')
    is_valid, errors = validate_contract(input_spec)
    assert is_valid, f"Contract validation failed: {errors}"
    print("  ✅ Contract definitions working")
except Exception as e:
    print(f"  ❌ Error: {e}")
    sys.exit(1)

# Test 2: I/O Schemas
print("\n[2/7] Testing I/O Schemas...")
try:
    from phase4_hybrid_stubs.azure_contracts import load_schema, validate_payload
    
    schema = load_schema(version='0.1', schema_type='prediction_input')
    assert schema is not None
    assert 'schema_version' in schema
    print("  ✅ I/O schemas working")
except Exception as e:
    print(f"  ❌ Error: {e}")
    sys.exit(1)

# Test 3: Stub Clients (sync version)
print("\n[3/7] Testing Stub Clients...")
try:
    import asyncio
    from phase4_hybrid_stubs.azure_contracts import AzureMLStubClient, create_mock_input
    
    async def test_ml_client():
        client = AzureMLStubClient()
        input_spec = create_mock_input('AAPL')
        result = await client.submit_job(input_spec)
        assert result.status == 'completed'
        assert len(result.predictions) == 30
        return result
    
    result = asyncio.run(test_ml_client())
    print(f"  ✅ Stub clients working (job_uuid: {result.job_uuid[:8]}...)")
except Exception as e:
    print(f"  ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Hybrid Interface
print("\n[4/7] Testing Hybrid Interface...")
try:
    from phase4_hybrid_stubs.local_hybrid_bridge import run_analytics
    
    result = run_analytics(
        job_type='forecast',
        payload={
            'ticker': 'MSFT',
            'features': {'momentum_20d': 0.05},
            'date_range': ('2025-01-01', '2025-12-31')
        }
    )
    assert 'predictions' in result
    assert 'confidence' in result
    print(f"  ✅ Hybrid interface working ({len(result['predictions'])} predictions)")
except Exception as e:
    print(f"  ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Compute Router
print("\n[5/7] Testing Compute Router...")
try:
    from phase4_hybrid_stubs.local_hybrid_bridge import get_router
    
    router = get_router()
    
    # Test dispatch
    result = router.dispatch(
        task_type='forecast',
        payload={
            'ticker': 'GOOGL',
            'features': {'momentum_20d': 0.03},
            'date_range': ('2025-01-01', '2025-12-31')
        }
    )
    
    # Test cache
    result2 = router.dispatch(
        task_type='forecast',
        payload={
            'ticker': 'GOOGL',
            'features': {'momentum_20d': 0.03},
            'date_range': ('2025-01-01', '2025-12-31')
        }
    )
    
    assert result2['_from_cache'], "Cache should be hit on second call"
    
    stats = router.get_cache_stats()
    print(f"  ✅ Compute router working (cache: {stats['total_cached_items']} items)")
except Exception as e:
    print(f"  ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 6: Telemetry Proxy
print("\n[6/7] Testing Telemetry Proxy...")
try:
    from phase4_hybrid_stubs.local_hybrid_bridge import get_telemetry
    
    telemetry = get_telemetry()
    
    # Track test event
    telemetry.track_event(
        'test_event',
        properties={'test': 'value'},
        measurements={'count': 1}
    )
    
    # Track metric
    telemetry.track_metric('test_metric', 42.5)
    
    # Get summary
    summary = telemetry.get_summary()
    assert summary['total_events'] >= 2
    
    print(f"  ✅ Telemetry proxy working ({summary['total_events']} events)")
except Exception as e:
    print(f"  ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: End-to-End Integration
print("\n[7/7] Testing E2E Integration...")
try:
    from phase4_hybrid_stubs.local_hybrid_bridge import run_forecast
    
    result = run_forecast(
        ticker='AMZN',
        features={
            'momentum_20d': 0.08,
            'volatility_20d': 0.25,
            'sharpe_20d': 1.8
        },
        date_range=('2025-01-01', '2025-12-31'),
        horizon='monthly'
    )
    
    assert len(result['predictions']) == 30
    assert len(result['confidence']) == 30
    assert all(0 <= c <= 1 for c in result['confidence'])
    
    print(f"  ✅ E2E integration working (avg confidence: {sum(result['confidence'])/len(result['confidence']):.2%})")
except Exception as e:
    print(f"  ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("🎉 All Phase 4 tests PASSED!")
print("=" * 60)
print("\nSummary:")
print("  • Contract definitions: ✅")
print("  • I/O schemas: ✅")
print("  • Stub clients: ✅")
print("  • Hybrid interface: ✅")
print("  • Compute router: ✅")
print("  • Telemetry proxy: ✅")
print("  • E2E integration: ✅")
print("\n✅ Phase 4 hybrid infrastructure is OPERATIONAL")
