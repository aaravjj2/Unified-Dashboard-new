from importlib.machinery import SourceFileLoader
import os
proj_root = os.path.abspath(os.path.dirname(__file__))
md = SourceFileLoader('market_dashboard', os.path.join(proj_root, 'market_dashboard.py')).load_module()
print('has_cb', hasattr(md, '_run_trends_from_dashboard'))
res = md._run_trends_from_dashboard(1)
print('callback_result:', res)
