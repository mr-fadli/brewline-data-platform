# ADR-010 : Service Account Design

## Status
Accepted

## Context
the latest Bigquery policy for service account usage is highly stricting the use of service-account-Key.

## Decision
we create two function-scoped accounts for ingestion and transformation based on the principle of least privilege for the IAM Role given to each accounts in the dataset-level. this will be accessed via impersonation from user's ADC credentials.