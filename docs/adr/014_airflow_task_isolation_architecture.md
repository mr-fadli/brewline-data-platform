# ADR-014 : Airflow task isolation architecture

## Status
Accepted

## Context
Installing dbt's dependencies alongside Airflow's own caused a protobuf version conflict with Airflow's Google provider packages.

## Decision
Airflow's image stays minimal (orchestration + Docker provider only); every actual task (bronze ingest, dbt seed/run/test) runs in its own purpose-built, short-lived container via `DockerOperator`.

## Consequence
zero shared dependency surface between Airflow and any task's tooling, ever again.