"""Dagster job that wires the ingestion ops together.

This job discovers files, reads CSV and parquet, cleans them, and writes to Postgres.
"""
from dagster import graph, job
from dagster_project.assets.file_discovery import discover_files
from dagster_project.assets.readers import read_csv_list, read_parquet_list
from dagster_project.assets.transforms import clean_picks_df, clean_financial_df
from dagster_project.assets.loaders import write_df_to_sql
from dagster_project.resources.db_resources import postgres_resource


@graph
def ingestion_graph():
    files = discover_files()

    picks_paths = files["picks"]
    parquet_paths = files["parquet"]

    picks_df = read_csv_list(picks_paths)
    cleaned_picks = clean_picks_df(picks_df)
    write_df_to_sql(cleaned_picks, "picks")

    fin_df = read_parquet_list(parquet_paths)
    cleaned_fin = clean_financial_df(fin_df)
    write_df_to_sql(cleaned_fin, "financial_features")


ingestion_job = ingestion_graph.to_job(resource_defs={"pg": postgres_resource})
