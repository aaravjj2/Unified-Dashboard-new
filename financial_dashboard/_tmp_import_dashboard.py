import sys
import traceback
import os
proj_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, proj_root)
try:
    print('Imported market_dashboard OK')
except Exception:
    print('market_dashboard import failed')
    traceback.print_exc()
