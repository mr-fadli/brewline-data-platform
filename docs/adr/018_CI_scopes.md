# ADR-018 : CI Scopes DuckDB only, Bigquery excluded

## Status
Accepted

## Context
every push/PR needs fast, free, secret-free feedback.

## Decision
CI runs the full local pipeline (generate → ingest → dbt seed/run/test) against DuckDB exclusively; BigQuery validation stays manual/local, not automated on every push.

## Alternative Rejected
running both targets in CI — rejected due to real query cost and the need to manage service-account credentials as CI secrets for a portfolio project where that risk/cost isn't justified.

## Consequences
a bug that only manifests on BigQuery's dialect won't be caught until a manual BigQuery run, not on every commit.