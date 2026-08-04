# ADR-007 : Refund Policy Window

## Status
Accepted

## Context
Sarah stated that the policy for refund is stays true within 30 days from delivery, but the actual enforced behavior from the customer side speaks differently. some refunds even occured before the delivery is even confirmed.

## Decision
we will use `within_policy_window` as an informational flag, not enforcement; this can separate those who do refunds within the policy and those who don't; the usage of NULL vs. FALSE is deliberately distinguished (unknown due to missing delivery record vs. confirmed not-early).