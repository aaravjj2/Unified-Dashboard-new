"""
Secrets Injection Integration Test
===================================

This test validates that Doppler (or equivalent secrets manager) correctly
injects API keys and sensitive credentials as environment variables into
running containers.

CRITICAL DEPENDENCIES:
- FINNHUB_API_KEY: Required for market data fetching
- APCA_API_KEY_ID: Required for Alpaca trading/portfolio integration
- APCA_API_SECRET_KEY: Required for Alpaca trading/portfolio integration
- POLYGON_API_KEY: Required for Polygon.io market data (optional but recommended)

This test MUST PASS before enabling tabs that depend on external APIs:
- Market Trends
- Market Forecast
- Options Lab
- Portfolio Analytics
- Dashboard Home (watchlist, market overview)
"""

import os
import pytest


def test_finnhub_api_key_injection():
    """
    CRITICAL: Verify FINNHUB_API_KEY is injected via Doppler.
    
    This test WILL FAIL if:
    - Doppler is not configured correctly
    - Secrets are not being injected at container runtime
    - The key is not set in Doppler cloud configuration
    
    This test WILL PASS when:
    - Doppler CLI is installed and configured in the container
    - docker-compose.yml correctly integrates with Doppler
    - FINNHUB_API_KEY is set in Doppler project/config
    """
    finnhub_key = os.getenv("FINNHUB_API_KEY")
    
    assert finnhub_key is not None, \
        "FAILURE: FINNHUB_API_KEY is not set. " \
        "This proves Doppler secrets are not being injected. " \
        "Check docker-compose.yml for Doppler integration."
    
    assert finnhub_key != "", \
        "FAILURE: FINNHUB_API_KEY is empty string. " \
        "Key exists but has no value in Doppler configuration."
    
    # Additional validation: key should look like a valid API key (alphanumeric, reasonable length)
    assert len(finnhub_key) >= 10, \
        f"FAILURE: FINNHUB_API_KEY appears invalid (too short: {len(finnhub_key)} chars). " \
        f"Expected a valid API key from Doppler."


def test_alpaca_api_keys_injection():
    """
    CRITICAL: Verify Alpaca API keys are injected via Doppler.
    
    Alpaca requires both APCA_API_KEY_ID and APCA_API_SECRET_KEY.
    """
    apca_key_id = os.getenv("APCA_API_KEY_ID")
    apca_secret = os.getenv("APCA_API_SECRET_KEY")
    
    assert apca_key_id is not None, \
        "FAILURE: APCA_API_KEY_ID is not set. " \
        "Alpaca integration requires this key from Doppler."
    
    assert apca_key_id != "", \
        "FAILURE: APCA_API_KEY_ID is empty string."
    
    assert apca_secret is not None, \
        "FAILURE: APCA_API_SECRET_KEY is not set. " \
        "Alpaca integration requires this key from Doppler."
    
    assert apca_secret != "", \
        "FAILURE: APCA_API_SECRET_KEY is empty string."
    
    # Validate key format (Alpaca keys have specific patterns)
    assert len(apca_key_id) >= 10, \
        f"FAILURE: APCA_API_KEY_ID appears invalid (length: {len(apca_key_id)})."
    
    assert len(apca_secret) >= 10, \
        f"FAILURE: APCA_API_SECRET_KEY appears invalid (length: {len(apca_secret)})."


def test_postgres_credentials_injection():
    """
    Verify database credentials are correctly injected.
    
    While not from Doppler necessarily, these should be set correctly
    in the container environment.
    """
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")
    db_name = os.getenv("POSTGRES_DB")
    
    assert db_user is not None and db_user != "", \
        "FAILURE: POSTGRES_USER not set in container environment."
    
    assert db_password is not None and db_password != "", \
        "FAILURE: POSTGRES_PASSWORD not set in container environment."
    
    assert db_name is not None and db_name != "", \
        "FAILURE: POSTGRES_DB not set in container environment."


def test_database_connectivity_with_injected_credentials():
    """
    Integration test: Use injected credentials to connect to postgres_db.
    
    This validates that not only are credentials present, but they're also valid.
    """
    import psycopg2
    
    db_host = os.getenv("DB_HOST", "postgres_db")
    db_user = os.getenv("POSTGRES_USER")
    db_password = os.getenv("POSTGRES_PASSWORD")
    db_name = os.getenv("POSTGRES_DB")
    
    try:
        conn = psycopg2.connect(
            host=db_host,
            port=5432,
            database=db_name,
            user=db_user,
            password=db_password,
            connect_timeout=5
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        assert result == (1,), "Database query did not return expected result."
        
    except psycopg2.OperationalError as e:
        pytest.fail(
            f"FAILURE: Cannot connect to postgres_db with injected credentials. "
            f"Error: {str(e)}"
        )


def test_optional_api_keys_present():
    """
    Validate additional API keys that are highly recommended.
    
    POLYGON_API_KEY is used for enhanced market data coverage.
    This test now enforces its presence with Zero-Tolerance protocol.
    """
    polygon_key = os.getenv("POLYGON_API_KEY")
    
    assert polygon_key is not None, \
        "FAILURE: POLYGON_API_KEY is not set. " \
        "This key is required for comprehensive market data coverage."
    
    assert polygon_key != "", \
        "FAILURE: POLYGON_API_KEY is empty string."
    
    assert len(polygon_key) >= 10, \
        f"FAILURE: POLYGON_API_KEY appears invalid (length: {len(polygon_key)})."
