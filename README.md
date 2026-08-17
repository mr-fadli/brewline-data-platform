# Brewline Coffee Co. — Data Platform

A production-style ETL pipeline built to satisfy a fictional business requirement from Brewline Coffee Co., a coffee subscription + retail company needing unified revenue, churn, and refund-alert reporting across 5 disconnected source systems (Shopify, Square POS, Recharge, Zendesk, ShipStation).

This project was built as a portfolio piece simulating a real engineering engagement: a stakeholder persona (played by Claude, Anthropic's AI) supplied an intentionally incomplete business requirement, and the project was built by asking clarifying questions, making — and documenting — real design decisions under ambiguity, and iterating through four stages of increasing production-readiness. See `docs/business_requirement.md` and `docs/stakeholder_discussion_log.md` for the original requirement-gathering process this pipeline was built to satisfy, and `docs/design_decisions_log.md` for the synthesis and design review that followed.

## Architecture

Medallion architecture (bronze → silver → gold), built in four stages:

| Stage | What | Stack |
|---|---|---|
| 1 | Local pipeline, hand-orchestrated | Python, DuckDB, SQL |
| 2 | Silver/gold transformations + tests | dbt-duckdb |
| 3 | Scheduled orchestration | Airflow, Docker (task-isolated containers) |
| 4 | Cloud data warehouse | GCS (data lake) + BigQuery, dbt-bigquery |

Both `dev` (local DuckDB) and `bigquery` dbt targets are fully supported and tested — every model runs unmodified against both engines via adapter-dispatch macros (see `docs/adr/011_cross_engine_dbt_macros.md`).

## Project structure
brewline/ -- installable Python package (bronze layer)
├── data/raw/ -- generated synthetic source files (gitignored, reproducible)
├── pipelines/bronze/ -- ingestion: local DuckDB + BigQuery variants, schema enforcement
├── pipelines/legacy/ -- v1 hand-orchestrated silver/gold (see its own README)
├── config.py, db.py, extractors.py, logging_config.py
brewline_dbt/ -- silver/gold transformations, tests, seeds, macros
airflow/ -- DAGs, Airflow's own Dockerfile + docker-compose
Dockerfile.bronze, Dockerfile.dbt -- task images, built from repo root (COPY project source directly)
generator/ -- synthetic data + exchange rate generation
docs/ -- business requirements, ADRs, design/discussion logs
tests/ -- pytest: extractor + config unit tests

`pipelines/legacy/` preserves the original hand-orchestrated silver/gold implementation (Stage 1) alongside the dbt-based version (Stage 2+), to show the migration rather than hide it — see `brewline/pipelines/legacy/README.md`.

## Dependencies

All dependencies are declared in `pyproject.toml` — no separate `requirements.txt`.

```bash
pip install -e .          # base: pandas, duckdb, pyarrow, faker
pip install -e ".[gcp]"   # + google-cloud-bigquery, google-cloud-storage, google-auth, python-dotenv
pip install -e ".[dev]"   # + pytest
```

## Running locally (dev)

```bash
python generator/generate_data.py
python generator/generate_exchange_rates.py
python -m brewline.pipelines.bronze.ingest
cd brewline_dbt && dbt seed && dbt run && dbt test
```

Or, using the Makefile shortcuts:
```bash
make generate
make ingest
make dbt-local
```

## Running against BigQuery (prod-like)

Requires a GCP project with two least-privilege service accounts (ingestion, transform), accessed via impersonation — see `docs/adr/010_service_account_design.md`.

```bash
gcloud auth application-default login
python -m brewline.pipelines.bronze.upload_raw_to_gcs
python -m brewline.pipelines.bronze.ingest_bigquery 2026-07-08
cd brewline_dbt && dbt seed --target bigquery && dbt run --target bigquery && dbt test --target bigquery
```

Or: `make dbt-bigquery`

## Running via Airflow

```bash
docker build -f Dockerfile.bronze --target gcp -t brewline-bronze:latest .
docker build -f Dockerfile.dbt -t brewline-dbt:latest .
cd airflow && ./compose.ps1 up -d   # (or ./compose.sh on Mac/Linux)
```

Trigger `brewline_pipeline` (local DuckDB) or `brewline_pipeline_bigquery` (BigQuery) at http://localhost:8080.

**Always invoke Compose via `compose.ps1`/`compose.sh`, never a bare `docker compose` command** — Airflow's environment is split across two `.env` files (root: shared GCP config; `airflow/`: Docker-specific paths), and the wrapper scripts apply both automatically. See `docs/adr/017_environment_secrets.md`.

**After editing code under `brewline/`, rebuild `brewline-bronze`/`brewline-dbt` images before rerunning tasks** — the package is installed at Docker build time, not picked up live from the bind mount.

## Testing

- **dbt**: 52+ tests (generic + singular) across both targets — identity, currency conversion, timezone handling, churn edge cases, reconciliation invariants. `cd brewline_dbt && dbt test` / `dbt test --target bigquery`
- **pytest**: extractor type-safety and config structural invariants — `pytest tests/ -v`
- **CI**: runs the full local pipeline + pytest suite on every push/PR (DuckDB only — see `docs/adr/018_CI_scopes.md` for why BigQuery isn't automated in CI)

## Documentation

- `docs/business_requirement.md` — the original stakeholder memo
- `docs/stakeholder_discussion_log.md` — full requirement-gathering Q&A
- `docs/design_decisions_log.md` — the design synthesis and mentor review
- `docs/gcp_setup_guide.md` — setup guidance for using it on GCS / Bigquery
- `docs/adr/` — 19 numbered ADRs, each with rejected alternatives and consequences
- `CHANGELOG.md` / `ROADMAP.md`

## Roadmap

Stages 1–4 complete and verified end-to-end (local, dbt, Airflow, BigQuery, including a full historical backfill). Stage 5 (observability — Elementary, pipeline run logging, Looker Studio dashboard) in progress. See `ROADMAP.md`.