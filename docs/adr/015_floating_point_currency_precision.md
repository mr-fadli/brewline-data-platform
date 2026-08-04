# ADR-015 : Floating-point currency precision

## Status
Accepted

## Context
Reconciliation tests using exact equality failed on mathematically-correct data due to `DOUBLE` floating-point representation limits.

## Decision
Airflow's image stays minimal (orchestration + Docker provider only); every actual task (bronze ingest, dbt seed/run/test) runs in its own purpose-built, short-lived container via `DockerOperator`.
