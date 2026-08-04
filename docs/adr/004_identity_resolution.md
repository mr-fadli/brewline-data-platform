# ADR-004 : Identity resolution

## Status
Accepted

## Context
Currently, there's no shared customer ID to point out across Shopify (email) and Square (phone, often walk-in)

## Decision
We will choose to separate the online and offline customer into 3 bucket. online will be using email, offline will be separated into 'loyalty' customer who signed up their phone number and 'walk-in' customer that is a synthetic frome store+date key.

## Alternative Considerations
Probabilistic matching - Rejected. too complex for v1. we will treat the walk-in customers as unidentifiable person and excluding them from the customer score.

## Consequences
loses some of the aggregate revenue visibility, but we can still track our 'best customer' under the online and loyalty tag. 