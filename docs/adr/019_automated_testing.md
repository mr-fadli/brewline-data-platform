# ADR-019 : Two-tier Automated Testing

## Status
Accepted

## Context
SQL transformation correctness and Python orchestration correctness are different kinds of risk.

## Decision
dbt tests (generic + singular) own all data/business-logic correctness; `pytest` owns Python-layer contracts (extractor type-safety, config structural invariants) that dbt tests can't reach, since they run before any SQL exists.

## Consequences
two separate test suites, two separate CI steps, deliberately not merged into one framework.