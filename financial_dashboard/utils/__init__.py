"""
Financial Dashboard Utilities Package

SUPER-AGENT FIX: Centralized utilities for key management, cache persistence, and price fetching.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import for type checkers only
	from . import price_fetch as price_fetch
	from . import keys_manager as keys_manager
	from . import cache_persistence as cache_persistence
	from . import price_fetcher as price_fetcher

__all__ = [
	'price_fetch',
	'keys_manager',
	'cache_persistence',
	'price_fetcher'
]


def __getattr__(name):  # pragma: no cover - delegation helper
	if name == 'price_fetch':
		from . import price_fetch as _price_fetch
		return _price_fetch
	if name == 'keys_manager':
		from . import keys_manager as _keys_manager
		return _keys_manager
	if name == 'cache_persistence':
		from . import cache_persistence as _cache_persistence
		return _cache_persistence
	if name == 'price_fetcher':
		from . import price_fetcher as _price_fetcher
		return _price_fetcher
	raise AttributeError(f"module 'financial_dashboard.utils' has no attribute {name!r}")

