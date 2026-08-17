# Changelog

## v1.0.0 — Local pipeline (Stage 1)
- Synthetic data generator: 5 sources, 30 days, deliberately injected edge cases
  (CAD currency, payment-failure-then-reactivation, mislabeled-batch refund spike)
- Bronze ingestion: Python + DuckDB + parquet, lineage-stamped
- Silver: identity resolution, currency conversion, timezone normalization,
  grain reconciliation (Square line-item → order level)
- Gold: fact_weekly_revenue, fact_subscription_churn, fact_customer_health,
  fact_refund_alerts, fact_customer_rfm
- Structured logging added across all orchestrators

## v2.0.0 — dbt (Stage 2)
- All silver/gold models ported to dbt, with generic + singular tests per model
- Reconciliation invariant tests (revenue totals, refund conservation) using
  tolerance-based comparisons, not exact equality (floating-point precision)

## v3.0.0 — Airflow (Stage 3)
- Task-isolated Docker architecture: Airflow orchestrates only, each task
  (bronze ingest, dbt seed/run/test) runs in its own purpose-built container
  via DockerOperator, avoiding Airflow/dbt dependency conflicts
- Full DAG verified end-to-end via the Airflow UI

## v4.0.0 — BigQuery (Stage 4)
- GCS data lake (Hive-partitioned raw + bronze zones) feeding BigQuery
- Two-service-account IAM design (ingestion vs. transform), accessed via
  impersonation — no static service account keys
- Explicit, canonical bronze schemas (schemas.py) — eliminated inference-driven
  schema drift across daily loads
- Idempotent append-strategy loading via staging table + scoped DML swap
  (sidesteps a BigQuery limitation with nested/repeated fields in
  partition-decorator loads)
- Cross-engine dbt macros (adapter dispatch) — every model runs unmodified
  against both DuckDB and BigQuery
- Per-model incremental materialization judgment: applied only where safe
  (append-only, order-independent); ranking/window-based gold models remain
  full-refresh by design

## v4.1.0 — Stage 4 hardening
- Restructured into an installable `brewline` package (`pyproject.toml`,
  `pip install -e .`) — removed manual `sys.path.append()` hacks throughout
- Currency columns migrated from FLOAT64/DOUBLE to NUMERIC/DECIMAL across
  bronze schemas, dbt models, and the exchange rate seed — eliminates
  floating-point representation drift (see ADR-015)
- Environment/secrets split across root `.env` (shared GCP config) and
  `airflow/.env` (Docker-specific paths), invoked via `compose.ps1`/`.sh`
  wrapper scripts (see ADR-017)
- CI scoped explicitly to DuckDB only, with a new dedicated pytest suite
  (extractor type-safety, config structural invariants) running alongside
  dbt tests (see ADR-018, ADR-019)
- Full historical backfill (July–September 2026) verified end-to-end via
  Airflow against BigQuery, surfacing and fixing real production-shaped
  issues: BigQuery partition-decorator schema conflicts with nested/
  repeated fields, `accepted_values` test quoting on numeric BigQuery
  columns, and Airflow backfill state-resumption interacting with a
  mid-backfill schema migration
- Legacy v1 (hand-orchestrated silver/gold) and pre-dbt reference data
  preserved under `pipelines/legacy/`, documented rather than deleted