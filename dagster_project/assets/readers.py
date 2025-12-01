"""Asset readers for CSV and Parquet files

These assets take lists of file paths (discovered by discovery assets) and
return a single concatenated pandas DataFrame.
"""
import pandas as pd
from dagster import asset, AssetIn
from typing import List


@asset(ins={"discovered_picks": AssetIn()})
def reads_picks(context, discovered_picks: List[str]) -> pd.DataFrame:
	if not discovered_picks:
		context.log.info("No picks files discovered")
		return pd.DataFrame()
	context.log.info("Reading %d picks CSV files", len(discovered_picks))
	dfs = []
	for p in discovered_picks:
		try:
			df = pd.read_csv(p)
			dfs.append(df)
		except Exception as e:
			context.log.warning("Failed to read CSV %s: %s", p, str(e))
			continue
	if dfs:
		return pd.concat(dfs, ignore_index=True)
	return pd.DataFrame()


@asset(ins={"discovered_parquet": AssetIn()})
def reads_parquet(context, discovered_parquet: List[str]) -> pd.DataFrame:
	if not discovered_parquet:
		context.log.info("No parquet files discovered")
		return pd.DataFrame()
	context.log.info("Reading %d parquet files", len(discovered_parquet))
	dfs = []
	for p in discovered_parquet:
		try:
			df = pd.read_parquet(p)
			dfs.append(df)
		except Exception as e:
			context.log.warning("Failed to read Parquet %s: %s", p, str(e))
			continue
	if dfs:
		return pd.concat(dfs, ignore_index=True)
	return pd.DataFrame()
