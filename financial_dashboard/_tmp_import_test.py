import sys
import traceback
import os
proj_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, proj_root)

try:
    print('Imported market_forecast OK')
except Exception:
    print('market_forecast import failed')
    traceback.print_exc()
try:
    print('Imported market_trends OK')
except Exception:
    print('market_trends import failed')
    traceback.print_exc()
