# ADR-015 : Floating-point currency precision

## Status
Accepted → Implemented

## Context
Reconciliation tests using exact equality failed on mathematically-correct data due to `DOUBLE` floating-point representation limits.

## Decision
The schema used for the quantity will be in `DECIMAL` for duckdb and `NUMERIC` for bigquery database.

## Consequences
Implemented across bronze schemas.py, dbt models, and the exchange_rates seed. Two non-obvious issues surfaced during implementation, worth recording for anyone hitting them again:

1. PyArrow's decimal128 construction rejects raw Python float directly requires explicit Decimal(str(value)) conversion (not Decimal(value), which preserves float's binary imprecision artifacts rather than eliminating them). Validation logic also needed a new branch, since pa.types.is_decimal() wasn't handled by the original type-checking code at all -- decimal values were silently passing validation unchecked.

2. dbt-bigquery's seed column_types config rejected explicit precision/ scale syntax (NUMERIC(10,6)) with an opaque "not a valid value" error; resolved by using plain NUMERIC (default precision) instead.

Post-migration, the weekly revenue reconciliation test's tolerance was NOT reduced to exact equality as originally planned. A small tolerance (~$0.10) remains, but the *reason* changed: it now accounts for legitimate rounding at the gold layer (ROUND(SUM(...), 2) applied once per week, summed across ~15 weeks) rather than floating-point imprecision. NUMERIC eliminated the representation-error class of discrepancy entirely; it does not eliminate intentional rounding differences between two different aggregation shapes.