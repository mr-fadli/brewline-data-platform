# ADR-011 : Cross Engine Dbt Macros

## Status
Accepted

## Context
Since we're using dbt for two different environment databases (DuckDB for development and BigQuery for production), we need to ensure that the query written inside the models could adapt based on which database are we targeting to.

## Decision
we create **adapter-dispact macros** for every dialect divergence, (timezone conversion, date truncation, and date-spine generation).`dbt_utils` then used for already-solved portability problems using (`type_string(), datediff()`) rather than hand-rolling everything.