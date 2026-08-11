-- assert_weekly_revenue_reconciles_to_orders.sql
-- Fails if gold's total diverges from silver's total -- would mean the
-- week-bucketing GROUP BY silently dropped or duplicated rows.
SELECT 1 AS mismatch
FROM (
    SELECT
        (SELECT SUM(total_revenue) FROM {{ ref('fact_weekly_revenue') }}) AS gold_total,
        (SELECT SUM(amount_usd) FROM {{ ref('stg_orders') }}) AS silver_total
)
WHERE ABS(gold_total - silver_total) > 0.10