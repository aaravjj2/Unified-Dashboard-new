"""Data cleaning and transformation assets and pure functions

We expose pure functions (clean_picks_df_impl, clean_financial_df_impl) so unit
tests can call them directly without needing a Dagster context. The asset
wrappers call the pure functions and provide Dagster logging.
"""
import pandas as pd
from dagster import asset, AssetIn


def clean_picks_df_impl(df: pd.DataFrame) -> pd.DataFrame:
    """Pure function performing cleaning logic for picks DataFrame.

    - Trim column names
    - Normalize date column to datetime
    - Replace common NA markers with pandas.NA
    - Drop rows missing ticker or date
    - Convert numeric columns
    - Uppercase and trim ticker
    - Fill remaining text NAs with '' and numeric NAs with 0
    """
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.replace(["N/A", "NA", "nan", ""], pd.NA)

    # Date handling: try common names
    date_col = None
    for candidate in ["date", "trade_date", "timestamp"]:
        if candidate in df.columns:
            date_col = candidate
            break
    if date_col:
        df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # Ensure ticker present
    if "ticker" in df.columns:
        df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()

    # Numeric conversions
    for col in ["price", "qty", "quantity"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows missing critical fields
    required = [c for c in ["ticker", date_col] if c]
    if required:
        df = df.dropna(subset=required)

    # Fill remaining NA: for object columns fill '', for numeric fill 0
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].fillna("")
    for col in df.select_dtypes(include=["number"]).columns:
        df[col] = df[col].fillna(0)

    return df


def clean_financial_df_impl(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    df = df.copy()
    df = df.replace(["N/A", "NA", "nan", ""], pd.NA)

    # Timestamp handling
    for candidate in ["timestamp", "ts", "date"]:
        if candidate in df.columns:
            df[candidate] = pd.to_datetime(df[candidate], errors="coerce")

    df = df.drop_duplicates()
    # Fill NA: text -> '', numeric -> 0
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].fillna("")
    for col in df.select_dtypes(include=["number"]).columns:
        df[col] = df[col].fillna(0)

    return df


@asset(ins={"reads_picks": AssetIn()})
def clean_picks_df(context, reads_picks: pd.DataFrame) -> pd.DataFrame:
    df = clean_picks_df_impl(reads_picks)
    context.log.info("Cleaned picks dataframe: rows=%d", len(df))
    return df


@asset(ins={"reads_parquet": AssetIn()})
def clean_financial_df(context, reads_parquet: pd.DataFrame) -> pd.DataFrame:
    df = clean_financial_df_impl(reads_parquet)
    context.log.info("Cleaned financial dataframe: rows=%d", len(df))
    return df
