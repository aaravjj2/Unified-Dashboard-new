#!/usr/bin/env python3
"""Dependency checker script - runs inside dash_app container"""

print("="*70)
print("Market Trends Dependency Check")
print("="*70)

missing_modules = []

# Test pyarrow import
try:
    import pyarrow
    print("✅ pyarrow: FOUND (version", pyarrow.__version__, ")")
except ImportError as e:
    print("❌ pyarrow: MISSING")
    missing_modules.append(f"pyarrow: {str(e)}")

# Test fastparquet import
try:
    import fastparquet
    print("✅ fastparquet: FOUND (version", fastparquet.__version__, ")")
except ImportError as e:
    print("❌ fastparquet: MISSING")
    missing_modules.append(f"fastparquet: {str(e)}")

print("="*70)

if missing_modules:
    print("\n🔥 DEPENDENCY CHECK FAILED")
    print("\nMissing libraries:")
    for m in missing_modules:
        print(f"  • {m}")
    print("\nFix: Add to requirements.txt:")
    print("  pyarrow>=11.0.0")
    print("  fastparquet>=2023.0.0")
    print("\nThen rebuild: docker-compose build dash_app")
    exit(1)
else:
    print("\n✅ DEPENDENCY CHECK PASSED")
    exit(0)
