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