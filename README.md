# Brewline Coffee Co — Data Pipeline

A production-style ETL pipeline built to satisfy a fictional business requirement
from Brewline Coffee Co., a coffee subscription + retail company needing unified
revenue, churn, and refund-alert reporting across 5 disconnected source systems
(Shopify, Square POS, Recharge, Zendesk, ShipStation).

This project was built as a portfolio piece simulating a real engineering
engagement: a stakeholder persona (played by Claude, Anthropic's AI) supplied
an intentionally incomplete business requirement, and the project was built
by asking clarifying questions, making — and documenting — real design
decisions under ambiguity, and iterating through four stages of increasing
production-readiness. See `docs/business_requirements.md` and
`docs/stakeholder_discussion_log.md` for the original requirement-gathering
process this pipeline was built to satisfy.

## Architecture

Medallion architecture (bronze → silver → gold), built in four stages:

| Stage | What | Stack |
|---|---|---|
| 1 | Local pipeline, hand-orchestrated | Python, DuckDB, SQL |
| 2 | Silver/gold transformations + tests | dbt-duckdb |
| 3 | Scheduled orchestration | Airflow, Docker (task-isolated containers) |
| 4 | Cloud data warehouse | GCS (data lake) + BigQuery, dbt-bigquery |

Both `dev` (local DuckDB) and `bigquery` dbt targets are fully supported and
tested — see `docs/adr/013-local-vs-cloud-data-flow.md`.

## Project structure
pipelines/bronze/ -- extraction + loading (local DuckDB and BigQuery variants)
brewline_dbt/ -- silver/gold transformations, tests, seeds, macros
airflow/ -- DAG, Dockerfiles, docker-compose
docs/ -- business requirements, ADRs, design decision log

## Running locally (dev)

```bash
python generate.py                    # generates 30 days of synthetic source data
python pipelines/bronze/ingest.py     # loads bronze into local DuckDB
cd brewline_dbt && dbt seed && dbt run && dbt test
```

## Running against BigQuery (prod-like)

```bash
gcloud auth application-default login
python pipelines/bronze/upload_raw_to_gcs.py
python pipelines/bronze/ingest_bigquery.py 2026-06-08
cd brewline_dbt && dbt run --target bigquery && dbt test --target bigquery
```

## Running via Airflow

```bash
cd airflow && docker compose up -d
# trigger `brewline_pipeline` DAG at http://localhost:8080
```

## Documentation

- `docs/business_requirements.md` — the original stakeholder memo
- `docs/stakeholder_discussion_log.md` — full requirement-gathering Q&A
- `docs/design_decisions_log.md` — the design synthesis and mentor review this project was scoped against
- `docs/adr/` — every individually numbered architectural decision, with rejected alternatives and consequences
- `CHANGELOG.md` / `ROADMAP.md`