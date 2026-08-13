# Makefile (repo root)
.PHONY: generate ingest dbt-local dbt-bigquery build-images airflow-up airflow-down test ci

generate:
	python generator/generate_data.py
	python generator/generate_exchange_rates.py

ingest:
	python -m brewline.pipelines.bronze.ingest

dbt-local:
	cd brewline_dbt && dbt seed && dbt run && dbt test

dbt-bigquery:
	cd brewline_dbt && dbt seed --target bigquery && dbt run --target bigquery && dbt test --target bigquery

build-images:
	docker build -f Dockerfile.bronze --target gcp -t brewline-bronze:latest .
	docker build -f Dockerfile.dbt -t brewline-dbt:latest .

airflow-up:
	cd airflow && ./compose.ps1 up -d

airflow-down:
	cd airflow && ./compose.ps1 down

test:
	pytest tests/ -v

ci: generate ingest dbt-local test