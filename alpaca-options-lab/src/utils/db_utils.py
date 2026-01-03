import os
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

"""Database utilities used by the app.

This module exposes a small set of functions the codebase expects at
``utils.db_utils``. It's intentionally defensive so the app can run in
environments without a reachable Postgres instance.
"""
import os
from typing import Any, Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv

load_dotenv()


class DatabaseManager:
    def __init__(self) -> None:
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_user = os.getenv("POSTGRES_USER", "user")
        self.db_password = os.getenv("POSTGRES_PASSWORD", "password")
        self.db_name = os.getenv("POSTGRES_DB", "financial_db")
        self.postgres_uri = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:5432/{self.db_name}"
        self._engine = None

    def get_engine(self):
        # Lazy import of SQLAlchemy to avoid import-time errors when the
        # package or DB isn't available in lightweight dev environments.
        if self._engine is None:
            try:
                from sqlalchemy import create_engine
                # Try Postgres first
                try:
                    self._engine = create_engine(self.postgres_uri)
                except Exception:
                    # Fall back to lightweight SQLite file for local dev/tests
                    sqlite_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'dev_data.db')
                    sqlite_path = os.path.abspath(sqlite_path)
                    sqlite_uri = f"sqlite:///{sqlite_path}"
                    try:
                        self._engine = create_engine(sqlite_uri)
                    except Exception:
                        self._engine = None
            except Exception:
                # Keep engine as None; callers will fallback to no-op.
                self._engine = None
        return self._engine


# module-level manager
_DB = DatabaseManager()


def initialize_database() -> bool:
    """Attempt to initialize/connect to the database. Returns True on success."""
    engine = _DB.get_engine()
    return engine is not None


def save_daily_snapshot(account_info: Dict[str, Any], positions_data: List[Dict[str, Any]]) -> bool:
    """Persist a daily snapshot. Returns True if saved, False otherwise."""
    engine = _DB.get_engine()
    try:
        if engine is None:
            return False
        # Prepare a small DataFrame and write to table 'daily_snapshots'
        df = pd.DataFrame(positions_data)
        # include account metadata columns if present
        df['account'] = account_info.get('account_id') if isinstance(account_info, dict) else None
        df.to_sql('daily_snapshots', engine, if_exists='append', index=False)
        return True
    except Exception:
        return False


def get_snapshot_history(days: int = 90) -> Dict[str, List[Any]]:
    """Return historical snapshot data or an empty structure on failure."""
    engine = _DB.get_engine()
    if engine is None:
        return {"timestamps": [], "values": []}
    try:
        query = f"SELECT timestamp, value FROM daily_snapshot_history ORDER BY timestamp DESC LIMIT {days}"
        df = pd.read_sql(query, engine)
        return {"timestamps": df['timestamp'].tolist(), "values": df['value'].tolist()}
    except Exception:
        return {"timestamps": [], "values": []}


def get_recent_snapshots(days: int = 30) -> List[Dict[str, Any]]:
    engine = _DB.get_engine()
    if engine is None:
        return []
    try:
        query = f"SELECT * FROM daily_snapshots WHERE timestamp >= now() - interval '{days} days' ORDER BY timestamp DESC"
        df = pd.read_sql(query, engine)
        return df.to_dict(orient='records')
    except Exception:
        return []


def execute_pg_query(query: str, params: Optional[Dict[str, Any]] = None, fetch: bool = True):
    """Execute a query against Postgres. Returns rows (DataFrame) when fetch is True."""
    engine = _DB.get_engine()
    if engine is None:
        return None
    try:
        if fetch:
            return pd.read_sql_query(query, engine, params=params)
        else:
            with engine.begin() as conn:
                conn.execute(query, params or {})
            # Return True to indicate successful non-fetch execution
            return True
    except Exception:
        return None


def execute_pg_many(query: str, params_list: List[Dict[str, Any]]):
    engine = _DB.get_engine()
    if engine is None:
        return None
    try:
        with engine.begin() as conn:
            conn.execute(query, params_list)
        return True
    except Exception:
        return None


# Backwards compatible aliases
def initialize_pg_pool(*args, **kwargs):
    return initialize_database()


def initialize_postgres_pool(*args, **kwargs):
    return initialize_database()
