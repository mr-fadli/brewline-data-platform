-- tests/assert_refund_alerts_conserves_all_refunds.sql
-- Fails if the spine's daily_refunds don't sum to the true total refund
-- count -- would mean a refund's date fell outside the calendar spine.
SELECT 1 AS mismatch
FROM (
    SELECT
        (SELECT SUM(daily_refunds) FROM {{ ref('fact_refund_alerts') }}) AS spine_total,
        (SELECT COUNT(*) FROM {{ ref('stg_refunds') }}) AS true_total
)
WHERE spine_total != true_total