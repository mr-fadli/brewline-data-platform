# ADR-012 : Incremental Materialization Strategy

## Status
Accepted

## Context
In order to create the most efficient data platform both in terms of cost and performance, I want to ensure that every materialized table inside the data warehouse is handled using the best strategy. The challenge here is that not every model can safely be incremental nor partitioned. so I need to define a clear rule on which table should apply which strategy.

## Decision
1. **Incremental** will only applied to a table where a new row can never change an existing row's correct value (event-grain staging models). This can save the compute power cost by reducing the amount of data processed within every run (instead of full-refreshing the whole table from every time, we will only process the newly added data).
2. **Full-refresh** for anything rank/window-dependent (RFM scoring table, customer health, refund alerts) or full-state-snapshot-sourced (`stg_subscriptions`). This is needed for every table where's the data is constantly changes as the time move on in order to keep the data quality trusted and reliable.