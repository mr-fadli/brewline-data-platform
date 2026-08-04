# ADR-006 : Subscription Churn Definition

## Status
Accepted

## Context
The subscription teams said that there are a couple cases where someone deactivate and reactivate their subscription within 48-hours, making the currently flagged 'Cancelled' customer in the recharge subscription conflates the voluntary churn customer (those who actually churn) and payment-failure-then-reactivation customer (those who cancel by mistake or simply wanted to dodge the charge date)

## Decision
using the query `ROW_NUMBER() OVER (PARTITION BY customer_key ORDER BY subscription_created_at DESC)` in the gold fact_subscription_churn resolve each customer's current status from potentially multiple historical rows; voluntary vs. involuntary churn kept as separate values, never merged into one boolean

## Consequence
a singular dbt test needed to explicitly guards the reactivation edge case.