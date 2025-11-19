"""Schedules for ingestion pipeline

Example schedule that triggers nightly ingestion at 02:00 UTC.
"""
from dagster import schedule
from dagster_project.jobs.ingestion_job import ingestion_job


@schedule(cron_schedule="0 2 * * *", job=ingestion_job)
def nightly_ingest(_context):
    return {}
