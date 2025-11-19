"""DB resource for Dagster.

This resource creates and returns a SQLAlchemy Engine based on environment
variables. It can be referenced by name as a required resource in your jobs
or asset definitions.

Configuration options:
- Preferred: set DATABASE_URL env var to a full SQLAlchemy URL (e.g. postgresql+psycopg2://user:pw@host:5432/db)
- Fallback: set POSTGRES_USER/PASSWORD/HOST/PORT/DB environment variables.
"""
from dagster import resource, Field, String
import os
import time
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError


@resource(config_schema={"db_url": Field(String, is_required=False, default_value="")})
def postgres_resource(context):
  """Return a SQLAlchemy engine.

  Priority for DB connection string:
  1. resource config `db_url`
  2. env var `DATABASE_URL`
  3. constructed from POSTGRES_* environment variables
  """
  # 1: resource config
  db_url = None
  try:
    db_url = context.resource_config.get("db_url")
  except Exception:
    db_url = None

  # 2: environment variable
  if not db_url:
    db_url = os.getenv("DATABASE_URL")

  # 3: construct from separate env vars as a fallback
  if not db_url:
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "postgres_db")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "market_data")
    db_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"

  context.log.info("Using DB URL host: %s", db_url.split("@")[1] if "@" in db_url else db_url)
  max_retries = 3
  delay_seconds = 2
  last_exc = None
  for attempt in range(1, max_retries + 1):
    try:
      engine = create_engine(db_url, pool_pre_ping=True)
      # quick connection test
      with engine.connect() as conn:
        conn.execute("SELECT 1")
      context.log.info("Successfully connected to database on attempt %d", attempt)
      return engine
    except (OperationalError, SQLAlchemyError) as exc:
      last_exc = exc
      context.log.warning(
        "Database connection attempt %d/%d failed: %s", attempt, max_retries, str(exc)
      )
      if attempt < max_retries:
        time.sleep(delay_seconds)

  # if we reach here, all retries failed
  context.log.error("Unable to connect to the database after %d attempts: %s", max_retries, str(last_exc))
  raise last_exc
