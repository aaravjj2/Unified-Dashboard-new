"""Trace exactly where the import hangs."""
import sys
import os

os.chdir('/mnt/c/Aarav/fin_env/unified-dashboard')
sys.path.insert(0, 'financial_dashboard')

print("Step 1: About to import app...")
try:
    from app import create_app
    print("✅ Step 1 complete: app.create_app imported")
except Exception as e:
    print(f"❌ Step 1 failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("Step 2: About to call create_app()...")
try:
    app_instance = create_app()
    print(f"✅ Step 2 complete: app created: {type(app_instance)}")
except Exception as e:
    print(f"❌ Step 2 failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("Step 3: About to import index module...")
try:
    import index
    print("✅ Step 3 complete: index imported")
except Exception as e:
    print(f"❌ Step 3 failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("✅ All steps completed!")
