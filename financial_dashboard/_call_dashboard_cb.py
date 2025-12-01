from importlib.machinery import SourceFileLoader
import os
proj_root = os.path.abspath(os.path.dirname(__file__))
md=SourceFileLoader('market_dashboard', os.path.join(proj_root, 'market_dashboard.py')).load_module()
print('Imported:', hasattr(md,'_run_trends_from_dashboard'))
print(md._run_trends_from_dashboard(1))
