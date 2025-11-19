"""
Dagster Project - Data Pipeline Orchestration
==============================================
Centralized data ingestion, transformation, and quality monitoring
for the Financial Dashboard.

Pipelines:
- historical_data_pipeline: Load picks and price data into PostgreSQL
- feature_engineering_pipeline: Generate ML features from raw data
- model_training_pipeline: Train and evaluate ML models with MLflow tracking
"""

from dagster import Definitions, load_assets_from_modules
from . import pipelines

# Load all assets from pipeline modules
all_assets = load_assets_from_modules([pipelines.historical_data_pipeline])

defs = Definitions(
    assets=all_assets,
)
