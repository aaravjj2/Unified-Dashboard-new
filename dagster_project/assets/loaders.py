"""Loaders for writing DataFrames to Postgres
"""
import pandas as pd
from dagster import asset, AssetIn
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from typing import Optional
import time


@asset(required_resource_keys={"pg"}, ins={"clean_picks_df": AssetIn(), "clean_financial_df": AssetIn()})
def load_to_db(context, clean_picks_df: pd.DataFrame, clean_financial_df: pd.DataFrame):
    """Write cleaned DataFrames to Postgres using the postgres_resource.

    For simplicity this asset replaces the target tables on each run.
    """
    engine = context.resources.pg

    results = {}
    try:
        # Helper to retry a write
        def _retry_write(df, table_name):
            max_retries = 3
            delay_seconds = 2
            last_exc = None
            for attempt in range(1, max_retries + 1):
                try:
                    df.to_sql(name=table_name, con=engine, if_exists="replace", index=False, method="multi", chunksize=1000)
                    context.log.info("Wrote %d rows to %s (attempt %d)", len(df), table_name, attempt)
                    return len(df)
                except (OperationalError, SQLAlchemyError) as exc:
                    last_exc = exc
                    context.log.warning("Write attempt %d/%d to %s failed: %s", attempt, max_retries, table_name, str(exc))
                    if attempt < max_retries:
                        time.sleep(delay_seconds)
            # if we get here, all attempts failed
            context.log.error("Failed writing to %s after %d attempts: %s", table_name, max_retries, str(last_exc))
            raise last_exc

        if clean_picks_df is not None and not clean_picks_df.empty:
            results["picks"] = _retry_write(clean_picks_df, "picks")
        else:
            context.log.info("No picks data to write")

        if clean_financial_df is not None and not clean_financial_df.empty:
            results["financial_features"] = _retry_write(clean_financial_df, "financial_features")
        else:
            context.log.info("No financial features to write")

        return results
    except SQLAlchemyError as exc:
        context.log.error("Error writing to DB after retries: %s", str(exc))
        raise
