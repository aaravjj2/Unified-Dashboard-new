"""Test just importing index to see where it hangs."""
import sys
import os
import signal

# Set timeout
def timeout_handler(signum, frame):
    print("❌ TIMEOUT: Import hung")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(15)

os.chdir('/mnt/c/Aarav/fin_env/unified-dashboard')
sys.path.insert(0, 'financial_dashboard')

print("Starting import...")
try:
    import index
    print(f"✅ Import successful!")
    print(f"✅ ENABLED_TABS exists: {hasattr(index, 'ENABLED_TABS')}")
    if hasattr(index, 'ENABLED_TABS'):
        print(f"✅ ENABLED_TABS = {index.ENABLED_TABS}")
    print(f"✅ loaded_tabs keys: {list(index.loaded_tabs.keys())}")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()

signal.alarm(0)
print("✅ Done")
