from dagster import Definitions
from dagster_project.resources.db_resources import postgres_resource
from dagster_project.assets.file_discovery import discovered_picks, discovered_parquet
from dagster_project.assets.readers import reads_picks, reads_parquet
from dagster_project.assets.transforms import clean_picks_df, clean_financial_df
from dagster_project.assets.loaders import load_to_db
from dagster_project.jobs.market_trends_job import market_trends_pipeline


defs = Definitions(
    assets=[
        discovered_picks,
        discovered_parquet,
        reads_picks,
        reads_parquet,
        clean_picks_df,
        clean_financial_df,
        load_to_db,
    ],
    jobs=[
        market_trends_pipeline,
    ],
    resources={"pg": postgres_resource},
)
