# ADR-013 : Local Vs Cloud data flow

## Status
Accepted

## Context
to improve the system's maintainability, we need to ensure that we separate the dev environment with prod environment with dev not depending on live cloud infra (can be run fully local).

## Decision
1. **dev environment** will reads from local dated files inside the repository and store it in local DuckDB.
2. **prod environment** will reads from a GCS bucket raw landing zone, process the file into a parquet file and stores it inside the GCS bronze within the same bucket with Hive-partitioned strategy, and then BigQuery will act as the compute engine to execute the query from dbt. 

Both environment will use the same `SOURCES`/`load_strategy` config drives. 