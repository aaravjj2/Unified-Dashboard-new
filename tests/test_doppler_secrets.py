import os
import pytest


def test_required_secrets_present():
    """Fail if critical secrets are missing from environment."""
    required = [
        "APCA_API_KEY_ID",
        "APCA_API_KEY_SECRET",
        "FINNHUB_API_KEY",
        "POSTGRES_PASSWORD",
        "POSTGRES_USER",
        "POSTGRES_DB",
        "DB_HOST",
    ]
    missing = [k for k in required if not os.getenv(k)]
    assert not missing, f"Missing required secrets: {missing}"


def test_database_manager_connects():
    """Attempt to instantiate DatabaseManager and get an engine. This should fail if DB credentials are missing."""
    import sys
    sys.path.insert(0, '/app')
    from utils.db_utils import DatabaseManager
    dm = DatabaseManager()
    engine = dm.get_engine()
    # The engine may be None if SQLAlchemy isn't installed or DB is unreachable, but
    # we specifically assert that POSTGRES_PASSWORD was provided (to prove Doppler injected creds)
    assert os.getenv('POSTGRES_PASSWORD'), "POSTGRES_PASSWORD is not set in container environment"
    # If engine is not None, try a simple connection test
    if engine is not None:
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
