# ADR-005 : Timezone Normalization

## Status
Accepted

## Context
The current 5 source systems all have mix offset-aware and naive-local timestamps. the situation make working with the databases used an issue without normalization first.

## Decision
normalize every timestamp recorded into naive UTC in silver first, then we can convert it again into a local timezone using a dbt var reporting_timezone in gold. this will be implemented via adapter-dispatch macros `(parse_and_convert_to_utc, convert_naive_to_utc, convert_utc_to_local)` so one model file runs unmodified on both engines.

## Consequence
a real historical bug (session-timezone-dependent date extraction) caught and fixed during the development of stage 2 and 4.
