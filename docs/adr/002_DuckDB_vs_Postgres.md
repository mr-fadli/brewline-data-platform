# ADR-002 : DuckDB VS Postgres

## Status
Accepted

## Context
The data produced by the pipeline needs to be stored in database, to get querried in order to get the gold layer.

## Decision
We will choose DuckDB because this was an OLAP based database and match the assignment with the current system design.

## Alternative Considerations
- PostgreSQL as the database - Rejected. PostgreSQL doesn't fit with the data model logic since it was OLTP based and not OLAP based.

## Consequences
Need more time to get used to it.