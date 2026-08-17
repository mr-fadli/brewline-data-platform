# Roadmap

## Done
- v1.0.0 — Local pipeline
- v2.0.0 — dbt
- v3.0.0 — Airflow
- v4.0.0 — BigQuery
- v4.1.0 — Package structure, NUMERIC currency migration, env/secrets
  hardening, CI + pytest, full historical backfill verified

## In progress — Stage 5: Observability
- Elementary (dbt observability — test history, run duration, freshness)
- `pipeline_run_log` table (bronze ingestion health, not covered by Elementary)
- Looker Studio dashboard on gold tables (the stakeholder-facing deliverable)

## Under consideration
- Real daily-arriving source files (generator currently produces per-day
  files but as one static historical batch, not genuinely live; resolve_file()/
  logical_date wiring already supports this, demonstrated via backfill)
- Data quality alerting beyond dbt test failures (Slack/email on failure via Airflow)
- Workload Identity Federation instead of user-impersonation (see ADR-010)