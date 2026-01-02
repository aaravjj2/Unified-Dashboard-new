"""Package initializer for financial_dashboard.callbacks

This file makes the `financial_dashboard.callbacks` directory importable
as a Python package. It's intentionally minimal to avoid side-effects on
import; callback modules are imported explicitly where needed.
"""

import importlib.util
import os

# Attempt to load the legacy `financial_dashboard/callbacks.py` module and
# re-export its `register_all_callbacks` symbol so code that expects
# `financial_dashboard.callbacks.register_all_callbacks` continues to work
# even though `financial_dashboard.callbacks` is now a package directory.
_impl_path = os.path.join(os.path.dirname(__file__), '..', 'callbacks.py')
_impl_module = None
if os.path.exists(_impl_path):
	try:
		spec = importlib.util.spec_from_file_location('financial_dashboard._callbacks_impl', os.path.abspath(_impl_path))
		_impl_module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(_impl_module)
	except Exception:
		_impl_module = None

if _impl_module and hasattr(_impl_module, 'register_all_callbacks'):
	register_all_callbacks = _impl_module.register_all_callbacks
else:
    # Fallback to callback_registry if callbacks.py is missing
    try:
        from financial_dashboard.callback_registry import register_all_callbacks
    except ImportError:
        pass

__all__ = [
	"chatbot_callbacks",
	"register_all_callbacks",
]
