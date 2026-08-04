# ADR-009 : BigQuery Partitioning and Load Strategy

## Status
Accepted

## Context
Loading a table from a parquet file straight to a partitioned table in Bigquery using paritition-decorator can caused a bug due to the parquet's file physical layout for the deeply nested list level getting read wrong (even when the schema is identical). The other issue we have is the different fundamental between schema sources force us to develop a different strategies for both event-stream source and full-state-snapshot.

## Decision
we devide the load_strategy into 2 separations based on their config field.
1. **the "append" sources** - to bypass the bug, first we load the parquet content into the bigquery via staging table, then we use DML `DELETE + INSERT` into the designated staging table scoped to _run_date for idempotency and history-safe. finally we delete the staging table to clean up the dataset.
2. **the "snapshot" source** - we do a full `WRITE_TRUNCATE` partitioned on _run_date (logical date), not _ingested_at (wall-clock), to support correct backfilling.
