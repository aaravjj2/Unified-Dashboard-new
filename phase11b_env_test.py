#!/usr/bin/env python3
"""Phase 11B: Environment Variable Validation Test"""
import os
import json
from pathlib import Path

print("🔍 Phase 11B: Environment + Dashboard Validation")
print("=" * 70)

# Count loaded environment variables
all_env_vars = len(os.environ)
api_keys = [k for k in os.environ.keys() if 'API' in k or 'KEY' in k or 'SECRET' in k]
print(f"\n📊 Environment Status:")
print(f"   Total variables: {all_env_vars}")
print(f"   API/Key variables: {len(api_keys)}")

# Check critical variables
critical_vars = [
    'TIINGO_API_KEY',
    'OPENAI_API_KEY',
    'APCA_API_KEY_ID',
    'APCA_API_SECRET_KEY',
    'POLYGON_API_KEY',
    'FINNHUB_API_KEY',
    'AZURE_TENANT_ID'
]

loaded_critical = []
missing_critical = []

for var in critical_vars:
    if os.getenv(var):
        loaded_critical.append(var)
    else:
        missing_critical.append(var)

print(f"\n✅ Critical vars loaded: {len(loaded_critical)}/{len(critical_vars)}")
if missing_critical:
    print(f"⚠️  Missing critical vars: {', '.join(missing_critical)}")

# Test dashboard import
print("\n🚀 Testing dashboard import...")
try:
    from financial_dashboard.app import create_app
    print("   ✅ Module imported successfully")
    
    app = create_app()
    print("   ✅ App created successfully")
    print(f"   App type: {type(app).__name__}")
    print(f"   Has server: {hasattr(app, 'server')}")
    
    dashboard_ready = True
except Exception as e:
    print(f"   ❌ Dashboard import failed: {e}")
    dashboard_ready = False

# Save results
results = {
    'env_vars_total': all_env_vars,
    'api_key_vars': len(api_keys),
    'critical_vars_loaded': len(loaded_critical),
    'critical_vars_total': len(critical_vars),
    'missing_critical': missing_critical,
    'dashboard_ready': dashboard_ready,
    'env_load_percentage': round((len(loaded_critical) / len(critical_vars)) * 100, 1)
}

output_path = Path('phase11b_env_dashboard_status.json')
with open(output_path, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n📊 Environment Load: {results['env_load_percentage']}%")
print(f"📊 Dashboard Ready: {dashboard_ready}")
print(f"✅ Results saved to: {output_path}")

# Return exit code based on success
exit(0 if dashboard_ready and not missing_critical else 1)
