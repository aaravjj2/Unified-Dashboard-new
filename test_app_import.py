"""Test just importing app module without calling create_app."""
import sys
import os
import signal

# Set timeout
def timeout_handler(signum, frame):
    print("❌ TIMEOUT: Import hung")
    sys.exit(1)

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(10)

os.chdir('/mnt/c/Aarav/fin_env/unified-dashboard')
sys.path.insert(0, 'financial_dashboard')

print("Importing app module...")
try:
    import app
    print(f"✅ app module imported successfully")
    print(f"✅ Has create_app: {hasattr(app, 'create_app')}")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()

signal.alarm(0)
print("✅ Done")
