"""Compatibility shim for ``utils.db_utils``.

The application expects a small set of functions under ``utils.db_utils``.
This shim tries to delegate to the newer implementations inside
``financial_dashboard.utils`` when available. If not, it exposes safe
no-op fallbacks so the app can continue running in reduced mode.

Keep imports and runtime behavior defensive to avoid raising at import
time inside the running container.
"""
from typing import Any, Dict, List

__all__ = [
    "save_daily_snapshot",
    "get_snapshot_history",
    "get_recent_snapshots",
    "initialize_database",
    "execute_pg_query",
    "execute_pg_many",
    "initialize_pg_pool",
    "initialize_postgres_pool",
]


def _load_impl() -> Dict[str, Any]:
    mod_new = None
    mod_sqlite = None
    try:
        mod_new = __import__("financial_dashboard.utils.db_utils_new", fromlist=["*"])
    except Exception:
        mod_new = None

    try:
        mod_sqlite = __import__("financial_dashboard.utils.db_utils_sqlite_backup", fromlist=["*"])
    except Exception:
        mod_sqlite = None

    def _pick(name: str, default=None):
        if mod_new and hasattr(mod_new, name):
            return getattr(mod_new, name)
        if mod_sqlite and hasattr(mod_sqlite, name):
            return getattr(mod_sqlite, name)
        return default

    impl: Dict[str, Any] = {
        "save_daily_snapshot": _pick("save_daily_snapshot"),
        "get_snapshot_history": _pick("get_snapshot_history"),
        "get_recent_snapshots": _pick("get_recent_snapshots"),
        "initialize_database": _pick("initialize_database"),
        "execute_pg_query": _pick("execute_pg_query"),
        "execute_pg_many": _pick("execute_pg_many"),
        "initialize_postgres_pool": _pick("initialize_postgres_pool") or _pick("initialize_pg_pool"),
    }

    # Provide safe fallbacks when implementations are missing
    if not impl["save_daily_snapshot"]:
        def _save_daily_snapshot(account_info: Dict[str, Any], positions_data: List[Dict[str, Any]]) -> bool:
            return False

        impl["save_daily_snapshot"] = _save_daily_snapshot

    if not impl["get_snapshot_history"]:
        def _get_snapshot_history(days: int = 90) -> Dict[str, List[Any]]:
            return {"timestamps": [], "values": []}

        impl["get_snapshot_history"] = _get_snapshot_history

    if not impl["get_recent_snapshots"]:
        def _get_recent_snapshots(days: int = 30) -> List[Dict[str, Any]]:
            return []

        impl["get_recent_snapshots"] = _get_recent_snapshots

    if not impl["initialize_database"]:
        def _initialize_database() -> bool:
            return False

        impl["initialize_database"] = _initialize_database

    if not impl["execute_pg_query"]:
        impl["execute_pg_query"] = lambda *a, **k: None

    if not impl["execute_pg_many"]:
        impl["execute_pg_many"] = lambda *a, **k: None

    if not impl["initialize_postgres_pool"]:
        impl["initialize_postgres_pool"] = lambda *a, **k: False

    return impl


_IMPL = _load_impl()


def save_daily_snapshot(account_info: Dict[str, Any], positions_data: List[Dict[str, Any]]) -> bool:
    return _IMPL["save_daily_snapshot"](account_info, positions_data)


def get_snapshot_history(days: int = 90) -> Dict[str, List[Any]]:
    return _IMPL["get_snapshot_history"](days=days)


def get_recent_snapshots(days: int = 30) -> List[Dict[str, Any]]:
    return _IMPL["get_recent_snapshots"](days=days)


def initialize_database() -> bool:
    return _IMPL["initialize_database"]()


def execute_pg_query(query, params=None, fetch=True):
    return _IMPL["execute_pg_query"](query, params, fetch=fetch)


def execute_pg_many(query, params_list):
    return _IMPL["execute_pg_many"](query, params_list)


def initialize_pg_pool(*args, **kwargs):
    return _IMPL["initialize_postgres_pool"](*args, **kwargs)


def initialize_postgres_pool(*args, **kwargs):
    return _IMPL["initialize_postgres_pool"](*args, **kwargs)
"""
Compatibility shim for utils.db_utils

This module provides the small set of functions previously expected at
`utils.db_utils` by runtime code. It delegates to the newer
implementations under `financial_dashboard.utils` when available:

- Prefer `financial_dashboard.utils.db_utils_new` (Postgres + SQLite fallback)
- Fall back to `financial_dashboard.utils.db_utils_sqlite_backup`
- If neither is importable, provide safe no-op / empty-return fallbacks

The file is intentionally small and defensive so it can be dropped into
the repo root and picked up by the running container via the bind-mount.
"""
from typing import Any, Dict, List

__all__ = [
    "save_daily_snapshot",
    "get_snapshot_history",
    "get_recent_snapshots",
    "initialize_database",
    "execute_pg_query",
    "execute_pg_many",
    "initialize_pg_pool",
    "initialize_postgres_pool",
]


def _load_impl():
    """Attempt to import the preferred implementations and return a dict of callables."""
    # Prefer importing the modern module but be defensive about missing names.
    try:
        mod_new = __import__('financial_dashboard.utils.db_utils_new', fromlist=['*'])
    except Exception:
        mod_new = None

    try:
        mod_sqlite = __import__('financial_dashboard.utils.db_utils_sqlite_backup', fromlist=['*'])
    except Exception:
        mod_sqlite = None

    # Helper to pick attribute from modules in preferred order
    def _pick_attr(name, default=None):
        if mod_new and hasattr(mod_new, name):
            return getattr(mod_new, name)
        if mod_sqlite and hasattr(mod_sqlite, name):
            return getattr(mod_sqlite, name)
        return default

    save_daily_snapshot = _pick_attr('save_daily_snapshot')
    """utils.db_utils compatibility shim.

    Provides a small set of functions that the running app expects at
    ``utils.db_utils``. The shim tries to delegate to the newer
    implementations under ``financial_dashboard.utils`` when available, and
    otherwise exposes safe no-op fallbacks so the application can continue
    running in environments without Postgres or the full stack.

    This file intentionally avoids raising at import time.
    """
    from typing import Any, Dict, List

    __all__ = [
        "save_daily_snapshot",
        "get_snapshot_history",
        "get_recent_snapshots",
        "initialize_database",
        "execute_pg_query",
        "execute_pg_many",
        "initialize_pg_pool",
        "initialize_postgres_pool",
    ]


    def _load_impl() -> Dict[str, Any]:
        """Return a dict mapping the exported function names to callables.

        Preference order:
          1. financial_dashboard.utils.db_utils_new
          2. financial_dashboard.utils.db_utils_sqlite_backup
          3. lightweight local stubs
        """
        mod_new = None
        mod_sqlite = None
        try:
            mod_new = __import__("financial_dashboard.utils.db_utils_new", fromlist=["*"])
        except Exception:
            mod_new = None

        try:
            mod_sqlite = __import__("financial_dashboard.utils.db_utils_sqlite_backup", fromlist=["*"])
        except Exception:
            mod_sqlite = None

        def _pick(name, default=None):
            if mod_new and hasattr(mod_new, name):
                return getattr(mod_new, name)
            if mod_sqlite and hasattr(mod_sqlite, name):
                return getattr(mod_sqlite, name)
            return default

        # Try to pick from implementations
        impl = {
            "save_daily_snapshot": _pick("save_daily_snapshot"),
            "get_snapshot_history": _pick("get_snapshot_history"),
            "get_recent_snapshots": _pick("get_recent_snapshots"),
            "initialize_database": _pick("initialize_database"),
            "execute_pg_query": _pick("execute_pg_query"),
            "execute_pg_many": _pick("execute_pg_many"),
            "initialize_postgres_pool": _pick("initialize_postgres_pool") or _pick("initialize_pg_pool"),
        }

        # If any required pieces are missing, supply lightweight fallbacks.
        if not impl["save_daily_snapshot"]:
            def _save_daily_snapshot(account_info: Dict[str, Any], positions_data: List[Dict[str, Any]]) -> bool:
                # No persistence available in this environment.
                return False

            impl["save_daily_snapshot"] = _save_daily_snapshot

        if not impl["get_snapshot_history"]:
            def _get_snapshot_history(days: int = 90) -> Dict[str, List[Any]]:
                return {"timestamps": [], "values": []}

            impl["get_snapshot_history"] = _get_snapshot_history

        if not impl["get_recent_snapshots"]:
            def _get_recent_snapshots(days: int = 30) -> List[Dict[str, Any]]:
                return []

            impl["get_recent_snapshots"] = _get_recent_snapshots

        if not impl["initialize_database"]:
            def _initialize_database() -> bool:
                return False

            impl["initialize_database"] = _initialize_database

        if not impl["execute_pg_query"]:
            impl["execute_pg_query"] = lambda *a, **k: None

        if not impl["execute_pg_many"]:
            impl["execute_pg_many"] = lambda *a, **k: None

        if not impl["initialize_postgres_pool"]:
            impl["initialize_postgres_pool"] = lambda *a, **k: False

        return impl


    _IMPL = _load_impl()


    def save_daily_snapshot(account_info: Dict[str, Any], positions_data: List[Dict[str, Any]]) -> bool:
        return _IMPL["save_daily_snapshot"](account_info, positions_data)


    def get_snapshot_history(days: int = 90) -> Dict[str, List[Any]]:
        return _IMPL["get_snapshot_history"](days=days)


    def get_recent_snapshots(days: int = 30) -> List[Dict[str, Any]]:
        return _IMPL["get_recent_snapshots"](days=days)


    def initialize_database() -> bool:
        return _IMPL["initialize_database"]()


    def execute_pg_query(query, params=None, fetch=True):
        return _IMPL["execute_pg_query"](query, params, fetch=fetch)


    def execute_pg_many(query, params_list):
        return _IMPL["execute_pg_many"](query, params_list)


    def initialize_pg_pool(*args, **kwargs):
        # backward-compatible alias
        return _IMPL["initialize_postgres_pool"](*args, **kwargs)


    def initialize_postgres_pool(*args, **kwargs):
        return _IMPL["initialize_postgres_pool"](*args, **kwargs)
