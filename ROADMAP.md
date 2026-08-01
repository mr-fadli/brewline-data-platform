# Roadmap

## Done
- v1.0.0 — Local pipeline
- v2.0.0 — dbt
- v3.0.0 — Airflow
- v4.0.0 — BigQuery

## Under consideration
- Real daily-arriving source files (current generator produces one static
  historical batch; resolve_file()/logical_date wiring already supports
  per-day files, demonstrated via backfill testing in ingest_bigquery.py)
- Data quality alerting beyond dbt test failures (e.g. Slack/email on
  pipeline failure via Airflow)
- DECIMAL/NUMERIC currency types instead of DOUBLE (see ADR-015)