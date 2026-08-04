# ADR-008 : Bronze Schema Enforcement

## Status
Accepted

## Context
While developing the stage 4, the ingestion pipeline kept failing due to Inference-based typing (pandas/pyarrow/BigQuery autodetect) silently guessed wrong on edge-case days (all-empty nested columns, blank CSV cells surviving as float NaN). This occured because there's a date where there're no refunds at all and causing this bug.

## Decision
We create one canonical schema per source (schemas.py) to explicitly do a validation before any write; this can help use to normalize the overall schema and deal with zero inference anywhere in the load path. 

I think this is something worth narrating here since the actual debugging sequence took a lot of time to do correctly.