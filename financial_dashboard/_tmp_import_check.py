import sys
import os
import importlib.util
p='c:/Aarav/fin_env/Dash/tabs/market_forecast.py'
proj = os.path.abspath(os.path.join(os.path.dirname(p), '..'))
if proj not in sys.path:
    sys.path.insert(0, proj)
spec=importlib.util.spec_from_file_location('mtf',p)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('Imported', mod.__name__)
