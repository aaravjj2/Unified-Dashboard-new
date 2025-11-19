import importlib.util
spec = importlib.util.spec_from_file_location('market_dashboard', 'c:/Aarav/fin_env/Dash/market_dashboard.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
print('Imported market_dashboard OK')
print('Has app:', hasattr(mod, 'app'))
